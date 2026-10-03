"""대본(script.json) + 장면별 소스(assets/)로 9:16 숏폼 초안 영상(mp4)을 조립한다.

사용법:
  python assemble_video.py OUTPUT_DIR [--voice ko-KR-SunHiNeural] [--rate +12%]
                           [--style THUMBNAIL_SPEC.json] [--out video.mp4] [--keep-temp]

OUTPUT_DIR 안에서 읽는 것:
  script.json            beats[].narration / caption / visual / t_start / t_end
  assets/beatNN.(png|jpg|jpeg|webp|mp4|mov)   장면 NN(1부터)의 화면 소스. 없으면 자리 표시 카드
쓰는 것:
  video.mp4              1080x1920, 30fps, H.264 + AAC
  video_report.json      장면별 길이·소스·경고

동작:
  - 장면마다 내레이션을 edge-tts로 따로 합성해 실제 음성 길이로 장면 길이를 정한다(싱크가 어긋나지 않음)
  - 이미지: 흐린 배경 + 원본 비율 유지 배치 + 느린 확대. 영상: 화면 채우기로 잘라 장면 길이만큼 사용
  - 자막(caption)은 Pillow로 그린 투명 PNG를 덮는다(한글 폰트·경로 문제 회피)
필요: ffmpeg/ffprobe(PATH), Pillow, edge-tts, 네트워크
종료 코드: 0 성공(경고 있을 수 있음), 1 실패, 2 사용법·도구 오류
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
VID_EXT = (".mp4", ".mov", ".m4v", ".webm")
TAIL_SEC = 0.15     # 문장 끝 여운 (edge-tts 출력에 앞뒤 무음이 조금 있어 짧게)
MIN_SCENE = 1.5
CAPTION_BOX = (80, 1180, 920, 300)   # 하단 UI(1536~)와 우측 버튼(950~) 피함
FONT_CANDIDATES = ["C:/Windows/Fonts/malgunbd.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                   "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", "C:/Windows/Fonts/NanumGothic.ttf"]


def fail(msg: str, code: int) -> int:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    return code


def font(size: int) -> ImageFont.FreeTypeFont:
    for c in FONT_CANDIDATES:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    raise SystemExit(fail("한글 폰트를 찾을 수 없습니다", 2))


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} 실패: {p.stderr.strip().splitlines()[-1] if p.stderr.strip() else p.returncode}")


def duration(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(p.stdout.strip() or 0)


# ---------- 스타일 (썸네일 spec과 같은 배경을 카드에 사용) ----------

def style_background(style: dict | None, base: Path | None) -> Image.Image:
    bg = (style or {}).get("background") or {"type": "gradient", "colors": ["#14503A", "#0A2219"], "angle": 165}
    if bg.get("type") == "image" and base and (base / bg["path"]).exists():
        src = Image.open(base / bg["path"]).convert("RGB")
        s = max(W / src.width, H / src.height)
        src = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
        l, t = (src.width - W) // 2, (src.height - H) // 2
        img = src.crop((l, t, l + W, t + H))
        return Image.blend(img, Image.new("RGB", (W, H), "black"), float(bg.get("darken", 0.3)))
    colors = bg.get("colors") or [bg.get("color", "#111111")] * 2
    c1, c2 = (tuple(int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for c in colors[:2])
    diag = int((W * W + H * H) ** 0.5) + 2
    mask = Image.linear_gradient("L").resize((diag, diag)).rotate(180 - float(bg.get("angle", 180)))
    l, t = (diag - W) // 2, (diag - H) // 2
    return Image.composite(Image.new("RGB", (W, H), c2), Image.new("RGB", (W, H), c1), mask.crop((l, t, l + W, t + H)))


def wrap(text: str, f: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = f"{cur} {word}".strip()
            if f.getlength(cand) <= max_w or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return [l for l in lines if l]


def caption_layer(text: str) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not text.strip():
        return layer
    x, y, bw, bh = CAPTION_BOX
    size = 72
    while True:
        f = font(size)
        lines = wrap(text, f, bw - 64)
        lh = round(size * 1.25)
        if lh * len(lines) + 48 <= bh or size <= 44:
            break
        size -= 4
    widest = max(f.getlength(l) for l in lines)
    block_h = lh * len(lines)
    top = y + bh - block_h - 24          # 박스 아래쪽에 붙임
    d = ImageDraw.Draw(layer)
    px0 = x + (bw - widest) / 2 - 32
    d.rounded_rectangle((px0, top - 24, px0 + widest + 64, top + block_h + 24), radius=22, fill=(0, 0, 0, 165))
    for i, line in enumerate(lines):
        lw = f.getlength(line)
        d.text((x + (bw - lw) / 2, top + i * lh + (lh - size) / 2), line, font=f, fill=(255, 255, 255))
    return layer


def placeholder(style_bg: Image.Image, beat_no: int, visual: str) -> Image.Image:
    img = style_bg.copy()
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((90, 300, 990, 1080), radius=28, outline=(255, 216, 77, 230), width=6, fill=(0, 0, 0, 90))
    f1, f2 = font(56), font(40)
    t1 = f"장면 {beat_no} 화면 소스 자리"
    d.text(((W - f1.getlength(t1)) / 2, 380), t1, font=f1, fill=(255, 216, 77))
    t2 = f"assets/beat{beat_no:02d}.png 또는 .mp4"
    d.text(((W - f2.getlength(t2)) / 2, 470), t2, font=f2, fill=(230, 230, 230))
    for i, line in enumerate(wrap(visual, f2, 780)[:9]):
        d.text((150, 580 + i * 54), line, font=f2, fill=(255, 255, 255))
    return img


def image_frame(src_path: Path) -> Image.Image:
    src = Image.open(src_path).convert("RGB")
    s = max(W / src.width, H / src.height)
    bg = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), "black"), 0.45)
    # 원본 비율 유지: 가로 1000 이내, 세로는 자막 위(1120)까지
    s = min(1000 / src.width, 860 / src.height)
    fg = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    bg.paste(fg, ((W - fg.width) // 2, 220 + (860 - fg.height) // 2))
    return bg


# ---------- 음성 ----------

async def synth(text: str, voice: str, rate: str, out: Path) -> None:
    import edge_tts  # noqa: PLC0415
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


# ---------- 장면 렌더 ----------

def render_scene(i: int, beat: dict, media: Path | None, style_bg: Image.Image, audio: Path | None,
                 dur: float, tmp: Path) -> Path:
    cap = tmp / f"cap{i:02d}.png"
    caption_layer(beat.get("caption", "")).save(cap)
    out = tmp / f"seg{i:02d}.mp4"
    frames = max(1, round(dur * FPS))
    a_in = ["-i", str(audio)] if audio else ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", f"{dur:.3f}", "-shortest"]
    if media and media.suffix.lower() in VID_EXT:
        vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}[b];"
              f"[b][1:v]overlay=0:0[v];[2:a]apad[a]")
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(media), "-i", str(cap), *a_in,
               "-filter_complex", vf, "-map", "[v]", "-map", "[a]", *enc, str(out)]
    else:
        frame = image_frame(media) if media else placeholder(style_bg, i, beat.get("visual", ""))
        fpath = tmp / f"frame{i:02d}.png"
        frame.save(fpath)
        zoom = "1.0" if not media else f"1+0.06*on/{frames}"   # 소스 이미지에만 느린 확대
        vf = (f"[0:v]scale={W * 2}:{H * 2},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={W}x{H}:fps={FPS},setsar=1[b];[b][1:v]overlay=0:0[v];[2:a]apad[a]")
        # 이미지 1장 → zoompan이 d=frames 만큼 프레임을 만든다 (-loop 1을 주면 프레임마다 다시 늘어남)
        cmd = ["ffmpeg", "-y", "-i", str(fpath), "-i", str(cap), *a_in,
               "-filter_complex", vf, "-map", "[v]", "-map", "[a]", *enc, str(out)]
    run(cmd)
    return out


def find_media(assets: Path, n: int) -> Path | None:
    for ext in IMG_EXT + VID_EXT:
        for name in (f"beat{n:02d}{ext}", f"beat{n}{ext}"):
            if (assets / name).exists():
                return assets / name
    return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("output_dir", type=Path)
    ap.add_argument("--voice", default="ko-KR-SunHiNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--style", type=Path, help="썸네일 spec — 자리 표시 카드에 같은 배경 사용")
    ap.add_argument("--out", default="video.mp4")
    ap.add_argument("--keep-temp", action="store_true")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            return fail(f"{tool}가 없습니다. '환경 점검해줘'로 설치하세요", 2)
    d = a.output_dir
    sp = d / "script.json"
    if not sp.exists():
        return fail(f"script.json이 없습니다: {sp}", 2)
    script = json.loads(sp.read_text(encoding="utf-8"))
    beats = script.get("beats", [])
    if not beats:
        return fail("script.json에 beats가 없습니다", 2)

    style = json.loads(a.style.read_text(encoding="utf-8")) if a.style and a.style.exists() else None
    style_bg = style_background(style, a.style.parent if a.style else None)
    assets = d / "assets"
    tmp = Path(tempfile.mkdtemp(prefix="shorts_video_"))
    report = {"ok": True, "out": str(d / a.out), "voice": a.voice, "rate": a.rate, "scenes": [], "warnings": []}

    try:
        segs = []
        for i, beat in enumerate(beats, 1):
            text = (beat.get("narration") or "").strip()
            audio = None
            if text:
                audio = tmp / f"vo{i:02d}.mp3"
                asyncio.run(synth(text, a.voice, a.rate, audio))
                dur = max(MIN_SCENE, duration(audio) + TAIL_SEC)
            else:
                dur = max(MIN_SCENE, float(beat.get("t_end", 0)) - float(beat.get("t_start", 0)))
            media = find_media(assets, i)
            if not media:
                report["warnings"].append(f"장면 {i}: assets/beat{i:02d}.(png|jpg|mp4) 없음 → 자리 표시 카드")
            segs.append(render_scene(i, beat, media, style_bg, audio, dur, tmp))
            report["scenes"].append({"beat": i, "seconds": round(dur, 2), "source": media.name if media else "placeholder",
                                     "caption": beat.get("caption", "")})
            print(f"장면 {i}/{len(beats)} 완료 ({dur:.1f}s, {media.name if media else '자리 표시'})", file=sys.stderr)

        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{s.name}'\n" for s in segs), encoding="utf-8")
        final = tmp / "final.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(final)])
        shutil.copy(final, d / a.out)
        total = duration(d / a.out)
        report["seconds"] = round(total, 2)
        planned = float(beats[-1].get("t_end", 0))
        if planned and total > planned + 2:
            report["warnings"].append(f"영상 {total:.1f}s가 대본 계획 {planned:.0f}s보다 깁니다 — 대본 축약 또는 속도 조정 고려")
        if total > 180:
            report["warnings"].append("3분 초과 — 쇼츠로 인식되지 않습니다")
    except Exception as exc:
        return fail(f"조립 실패: {exc}", 1)
    finally:
        if not a.keep_temp:
            shutil.rmtree(tmp, ignore_errors=True)

    (d / "video_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
