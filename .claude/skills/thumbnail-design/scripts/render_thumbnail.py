"""JSON spec으로 숏폼 썸네일(커버) PNG를 렌더링한다. Pillow만 사용.

사용법: python render_thumbnail.py SPEC.json [--out OUT.png] [--report REPORT.json]
종료 코드: 0 성공(경고 있을 수 있음), 1 렌더 실패, 2 사용법/폰트 오류
spec 형식: ../references/spec.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PRESETS = {"shorts": (1080, 1920), "youtube": (1280, 720), "square": (1080, 1080)}

# 플랫폼 UI(제목·버튼·진행바)가 덮는 영역: (x0, y0, x1, y1) 비율
UNSAFE = {
    "shorts": [(0, 0, 1, 0.08, "상단 상태바·검색"), (0, 0.80, 1, 1, "하단 제목·캡션"), (0.88, 0.45, 1, 1, "우측 좋아요·댓글 버튼")],
    "youtube": [(0.82, 0.85, 1, 1, "우측 하단 재생시간")],
    "square": [],
}

FONT_CANDIDATES = {
    "bold": ["C:/Windows/Fonts/malgunbd.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
             "/System/Library/Fonts/AppleSDGothicNeo.ttc"],
    "regular": ["C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/NanumGothic.ttf",
                "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc"],
}


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def find_font(weight: str, path: str | None) -> str:
    for c in ([path] if path else []) + FONT_CANDIDATES.get(weight, FONT_CANDIDATES["bold"]):
        if c and Path(c).exists():
            return c
    raise SystemExit(_err(f"한글 폰트를 찾을 수 없습니다 (weight={weight}). spec의 font에 .ttf 경로를 지정하세요.", 2))


def _err(msg: str, code: int) -> int:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    return code


# ---------- 배경 ----------

def make_background(size: tuple[int, int], bg: dict, base_dir: Path) -> Image.Image:
    w, h = size
    kind = bg.get("type", "solid")
    if kind == "solid":
        return Image.new("RGBA", size, hex_rgb(bg.get("color", "#111111")) + (255,))
    if kind == "gradient":
        c1, c2 = (hex_rgb(c) for c in bg["colors"][:2])
        angle = float(bg.get("angle", 180))  # CSS 방식: 180 = 위→아래
        diag = int((w * w + h * h) ** 0.5) + 2
        mask = Image.linear_gradient("L").resize((diag, diag)).rotate(180 - angle)
        left, top = (diag - w) // 2, (diag - h) // 2
        mask = mask.crop((left, top, left + w, top + h))
        return Image.composite(Image.new("RGBA", size, c2 + (255,)), Image.new("RGBA", size, c1 + (255,)), mask)
    if kind == "image":
        src = Image.open(base_dir / bg["path"]).convert("RGBA")
        scale = max(w / src.width, h / src.height)
        src = src.resize((round(src.width * scale), round(src.height * scale)), Image.LANCZOS)
        left, top = (src.width - w) // 2, (src.height - h) // 2
        img = src.crop((left, top, left + w, top + h))
        if bg.get("darken"):
            img = Image.alpha_composite(img, Image.new("RGBA", size, (0, 0, 0, int(255 * float(bg["darken"])))))
        return img
    raise SystemExit(_err(f"알 수 없는 background.type: {kind}", 2))


def draw_shapes(img: Image.Image, shapes: list[dict]) -> Image.Image:
    for s in shapes:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        fill = hex_rgb(s.get("fill", "#000000")) + (int(255 * float(s.get("opacity", 1))),)
        if s["type"] == "rect":
            x, y, bw, bh = s["box"]
            d.rounded_rectangle((x, y, x + bw, y + bh), radius=s.get("radius", 0), fill=fill)
        elif s["type"] == "circle":
            cx, cy = s["center"]
            r = s["r"]
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
        else:
            raise SystemExit(_err(f"알 수 없는 shape.type: {s['type']}", 2))
        img = Image.alpha_composite(img, layer)
    return img


# ---------- 텍스트 ----------

def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = f"{cur} {word}".strip()
            if font.getlength(cand) <= max_w:
                cur = cand
                continue
            if cur:
                lines.append(cur)
            cur = ""
            # 한 단어가 너비보다 길면 글자 단위로 나눈다
            for ch in word:
                if font.getlength(cur + ch) <= max_w:
                    cur += ch
                else:
                    lines.append(cur)
                    cur = ch
        lines.append(cur)
    return lines


def fit_text(t: dict, font_path: str) -> tuple[ImageFont.FreeTypeFont, list[str], int, bool]:
    _, _, bw, bh = t["box"]
    spacing = float(t.get("line_spacing", 1.15))
    size = int(t.get("max_size", 160))
    min_size = int(t.get("min_size", 48))
    while True:
        font = ImageFont.truetype(font_path, size)
        lines = wrap(t["text"], font, bw)
        line_h = round(size * spacing)
        widest = max((font.getlength(l) for l in lines), default=0)
        if (line_h * len(lines) <= bh and widest <= bw) or size <= min_size:
            fits = line_h * len(lines) <= bh and widest <= bw
            return font, lines, line_h, fits
        size = max(min_size, size - 4)


def _tokens(line: str) -> list[str]:
    return re.split(r"( )", line)


def luminance(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def draw_text(img: Image.Image, t: dict, warnings: list[str]) -> tuple[Image.Image, dict]:
    font_path = find_font(t.get("weight", "bold"), t.get("font"))
    font, lines, line_h, fits = fit_text(t, font_path)
    x, y, bw, bh = t["box"]
    block_h = line_h * len(lines)
    valign = t.get("valign", "middle")
    top = y + {"top": 0, "middle": (bh - block_h) // 2, "bottom": bh - block_h}[valign]
    color = hex_rgb(t.get("color", "#FFFFFF"))
    stroke_w = int(t.get("stroke_width", 0))
    stroke_c = hex_rgb(t.get("stroke_color", "#000000"))
    hl = t.get("highlight") or {}
    hl_words = set(hl.get("words", []))
    hl_color = hex_rgb(hl.get("color", "#FFE14D"))
    align = t.get("align", "center")

    # 대비 검사: 판 없이 외곽선도 없으면 배경 평균색과 비교
    plate = t.get("plate")
    if not plate and stroke_w == 0:
        region = img.crop((x, top, x + bw, top + block_h)).convert("RGB").resize((1, 1), Image.BOX)
        bg_avg = region.getpixel((0, 0))
        ratio = contrast(color, bg_avg)
        if ratio < 4.5:
            warnings.append(f"'{t['text'][:12]}' 대비 {ratio:.1f}:1 (<4.5) — stroke나 plate를 추가하세요")

    if plate:
        pad = int(plate.get("padding", 24))
        widest = max(font.getlength(l) for l in lines)
        px0 = {"left": x, "center": x + (bw - widest) / 2, "right": x + bw - widest}[align] - pad
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle(
            (px0, top - pad, px0 + widest + 2 * pad, top + block_h + pad),
            radius=int(plate.get("radius", 24)),
            fill=hex_rgb(plate.get("color", "#000000")) + (int(255 * float(plate.get("opacity", 0.6))),),
        )
        img = Image.alpha_composite(img, layer)

    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        lw = font.getlength(line)
        cx = {"left": x, "center": x + (bw - lw) / 2, "right": x + bw - lw}[align]
        cy = top + i * line_h + (line_h - font.size) / 2
        # 줄 전체를 한 번에 그려 자간·어간을 폰트 기본값으로 유지하고,
        # 강조 단어만 같은 위치에 덧그린다 (단어별로 따로 그리면 어간이 벌어진다)
        d.text((cx, cy), line, font=font, fill=color, stroke_width=stroke_w, stroke_fill=stroke_c)
        offset = 0
        for tok in _tokens(line):
            if tok and tok.strip(".,!?~\"'") in hl_words:
                d.text((cx + font.getlength(line[:offset]), cy), tok, font=font, fill=hl_color,
                       stroke_width=stroke_w, stroke_fill=stroke_c)
            offset += len(tok)

    if not fits:
        warnings.append(f"'{t['text'][:12]}' 최소 크기({font.size}px)에서도 박스를 넘침 — 문구를 줄이세요")
    return img, {"text": t["text"], "font_size": font.size, "lines": lines, "fits": fits}


def check_safe_area(preset: str, size: tuple[int, int], texts: list[dict], warnings: list[str]) -> None:
    w, h = size
    for t in texts:
        x, y, bw, bh = t["box"]
        for fx0, fy0, fx1, fy1, label in UNSAFE.get(preset, []):
            ux0, uy0, ux1, uy1 = fx0 * w, fy0 * h, fx1 * w, fy1 * h
            if x < ux1 and x + bw > ux0 and y < uy1 and y + bh > uy0:
                warnings.append(f"'{t['text'][:12]}' 텍스트 박스가 {label} 영역과 겹침")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("spec", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--report", type=Path)
    a = p.parse_args()

    try:
        spec = json.loads(a.spec.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _err(f"spec을 읽을 수 없습니다(UTF-8 JSON이어야 함): {exc}", 2)
    preset = spec.get("preset", "shorts")
    size = tuple(spec.get("size") or PRESETS[preset])
    out = a.out or (a.spec.parent / spec.get("out", "thumbnail.png"))
    warnings: list[str] = []

    try:
        img = make_background(size, spec.get("background", {}), a.spec.parent)
        img = draw_shapes(img, spec.get("shapes", []))
        text_reports = []
        for t in spec.get("texts", []):
            img, rep = draw_text(img, t, warnings)
            text_reports.append(rep)
        check_safe_area(preset, size, spec.get("texts", []), warnings)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(out, "PNG", optimize=True)
    except SystemExit:
        raise
    except Exception as exc:
        return _err(f"렌더 실패: {exc}", 1)

    report = {"ok": True, "out": str(out), "size": list(size), "texts": text_reports, "warnings": warnings}
    if a.report:
        a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
