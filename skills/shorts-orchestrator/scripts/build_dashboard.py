"""_workspace_shorts/ 의 JSON 산출물로 숏폼 대시보드 HTML을 만든다 (Artifact 공개용).

사용법: python build_dashboard.py WORKSPACE_DIR OUT.html [PAGE_TITLE]
PAGE_TITLE: 브라우저 탭·갤러리용 짧은 이름 (예: "업무 꿀팁 1화"). 없으면 대본 제목.
있는 파일만으로 만든다 — 트렌드만 있으면 트렌드 보드, 대본·썸네일까지 있으면 전체 보드.
데이터 형식: ../references/schemas.md
"""
from __future__ import annotations

import base64
import json
import sys
from html import escape
from pathlib import Path


def load(ws: Path, name: str):
    p = ws / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"경고: {name} 읽기 실패 — {exc}", file=sys.stderr)
        return None


def e(v) -> str:
    return escape("" if v is None else str(v))


def fmt_num(n) -> str:
    if n is None:
        return "—"
    n = float(n)
    if n >= 1e8:
        return f"{n / 1e8:.1f}억"
    if n >= 1e4:
        return f"{n / 1e4:.1f}만"
    return f"{int(n):,}"


SIGNAL = {"rising": ("상승", "rising"), "steady": ("유지", "steady"), "fading": ("하락", "fading")}
EVIDENCE = {"high": "근거 강함", "medium": "근거 보통", "low": "근거 약함"}
PLATFORM = {"youtube": "YouTube Shorts", "instagram": "Instagram Reels"}
SEVERITY = {"high": "높음", "medium": "중간", "low": "낮음"}


def trend_panel(t: dict | None, platform: str) -> str:
    name = PLATFORM[platform]
    if not t:
        return f'<section class="panel"><h3>{name}</h3><p class="muted">이번 실행에서 수집하지 못했습니다.</p></section>'

    topics = sorted(t.get("topics", []), key=lambda x: -(x.get("momentum") or 0))[:8]
    bars = "".join(
        f'<div class="bar-row"><span class="bar-label">{e(tp["keyword"])}</span>'
        f'<span class="track"><span class="fill" style="width:{max(0, min(100, tp.get("momentum") or 0))}%"></span></span>'
        f'<span class="num">{e(tp.get("momentum"))}</span></div>'
        for tp in topics
    )
    chart = (
        '<div class="bars" role="img" aria-label="주제별 상대 모멘텀 0~100">'
        '<div class="bar-row axis"><span></span><span class="ticks"><i style="left:0">0</i><i style="left:50%">50</i>'
        '<i style="left:100%">100</i></span><span></span></div>' + bars + "</div>"
        if topics else ""
    )

    formats = "".join(
        '<li class="fmt">'
        f'<div class="fmt-head"><strong>{e(f["name"])}</strong>'
        f'<span class="pill {SIGNAL.get(f.get("signal"), ("", "steady"))[1]}">{SIGNAL.get(f.get("signal"), (e(f.get("signal")), ""))[0]}</span>'
        f'<span class="tag">{EVIDENCE.get(f.get("evidence"), "")}</span></div>'
        f'<p>{e(f.get("description"))}</p>'
        + (
            '<ul class="examples">' + "".join(
                f'<li><a href="{e(x.get("url"))}" target="_blank" rel="noopener">{e(x.get("title"))}</a>'
                f'<span class="num">{fmt_num(x.get("views"))}</span></li>'
                for x in f.get("examples", [])[:2] if x.get("url")
            ) + "</ul>" if f.get("examples") else ""
        )
        + "</li>"
        for f in t.get("formats", [])
    )
    hooks = "".join(f'<li><strong>{e(h["pattern"])}</strong> <span class="muted">{e(h.get("example"))}</span></li>' for h in t.get("hooks", []))
    audio = "".join(f'<li><strong>{e(a["name"])}</strong> <span class="muted">{e(a.get("note"))}</span></li>' for a in t.get("audio", []))
    metrics = t.get("metrics") or {}
    metric_line = (
        f'<p class="metrics">API 표본 {e(metrics.get("count"))}개 · 조회수 중앙값 <b>{fmt_num(metrics.get("median_views"))}</b>'
        f' · 하루 조회수 중앙값 <b>{fmt_num(metrics.get("median_views_per_day"))}</b>'
        f' · 평균 길이 <b>{e(metrics.get("median_duration_sec"))}초</b></p>'
        if metrics.get("count") else ""
    )
    caveats = "".join(f"<li>{e(c)}</li>" for c in t.get("caveats", []))

    return (
        f'<section class="panel" id="trend-{platform}"><div class="panel-head"><h3>{name}</h3>'
        f'<span class="tag">{e(t.get("period"))} · {"웹+API" if t.get("data_basis") == "web+api" else "웹 자료"}</span></div>'
        f'<p class="lede">{e(t.get("summary"))}</p>{metric_line}'
        f'<h4>뜨는 주제 <span class="muted small">상대 점수</span></h4>{chart}'
        f'<h4>포맷</h4><ul class="fmts">{formats}</ul>'
        + (f"<h4>훅 패턴</h4><ul class='plain'>{hooks}</ul>" if hooks else "")
        + (f"<h4>음원</h4><ul class='plain'>{audio}</ul>" if audio else "")
        + (f"<details><summary>조사 한계</summary><ul class='plain'>{caveats}</ul></details>" if caveats else "")
        + "</section>"
    )


def concept_cards(c: dict | None) -> str:
    if not c:
        return ""
    sel = c.get("selected_id")
    labels = {"trend": "트렌드", "fit": "적합도", "feasibility": "제작 용이", "differentiation": "차별성"}
    cards = []
    for k in c.get("concepts", []):
        scores = "".join(
            f'<div class="score"><span>{labels[key]}</span><span class="dots" aria-label="{v}/5">'
            + "".join(f'<i class="{"on" if i < v else ""}"></i>' for i in range(5))
            + "</span></div>"
            for key, v in (k.get("scores") or {}).items() if key in labels
        )
        chosen = k.get("id") == sel
        cards.append(
            f'<article class="concept{" chosen" if chosen else ""}">'
            + ('<span class="chosen-label">선택한 기획</span>' if chosen else "")
            + f'<h3>{e(k.get("title"))}</h3><p class="logline">{e(k.get("logline"))}</p>'
            f'<p class="meta"><span class="tag">{e(k.get("format_ref"))}</span><span class="tag">{e(k.get("length_sec"))}초</span>'
            f'<span class="num total">{e(k.get("total"))}<small>/20</small></span></p>'
            f'{scores}<p class="why">{e(k.get("why_fit"))}</p>'
            + (f'<p class="risk">주의: {e(", ".join(k.get("risks", [])))}</p>' if k.get("risks") else "")
            + "</article>"
        )
    return (
        f'<section id="concepts"><h2>기획안</h2><p class="muted">{e(c.get("profile_summary"))}</p>'
        f'<div class="concepts">{"".join(cards)}</div></section>'
    )


def production(s: dict | None, ws: Path) -> str:
    png = ws / "03_thumbnail.png"
    if not s and not png.exists():
        return ""
    thumb = ""
    if png.exists():
        b64 = base64.b64encode(png.read_bytes()).decode()
        thumb = (
            '<figure class="phone"><img src="data:image/png;base64,' + b64 + '" alt="썸네일 미리보기" width="1080" height="1920">'
            "<figcaption>썸네일 · 1080×1920</figcaption></figure>"
        )
    script = ""
    if s:
        rows = "".join(
            f'<li class="beat"><span class="tc">{e(b.get("t_start"))}–{e(b.get("t_end"))}s</span>'
            f'<div class="beat-body"><p class="visual">{e(b.get("visual"))}</p>'
            f'<p class="narr">{e(b.get("narration"))}</p>'
            + (f'<span class="cap">{e(b.get("caption"))}</span>' if b.get("caption") else "")
            + (f'<span class="sfx">♪ {e(b.get("sfx"))}</span>' if b.get("sfx") else "")
            + "</div></li>"
            for b in s.get("beats", [])
        )
        tags_yt = " ".join(e(t) for t in (s.get("hashtags") or {}).get("youtube", []))
        tags_ig = " ".join(e(t) for t in (s.get("hashtags") or {}).get("instagram", []))
        hook = s.get("hook") or {}
        script = (
            f'<div class="script"><p class="eyebrow">{e(s.get("length_sec"))}초 대본</p>'
            f'<h3>{e(s.get("title"))}</h3>'
            f'<blockquote class="hook">{e(hook.get("line"))}</blockquote>'
            f'<ol class="timeline">{rows}</ol>'
            f'<p class="cta"><b>CTA</b> {e(s.get("cta"))}</p>'
            '<div class="copy-grid">'
            f'<div><h4>YouTube 설명</h4><p>{e((s.get("description") or {}).get("youtube"))}</p><p class="tags">{tags_yt}</p></div>'
            f'<div><h4>Instagram 캡션</h4><p>{e((s.get("description") or {}).get("instagram"))}</p><p class="tags">{tags_ig}</p></div>'
            "</div>"
            f'<details><summary>TTS 내레이션 원고</summary><pre class="narration">{e(s.get("narration_text"))}</pre></details>'
            "</div>"
        )
    return f'<section id="production"><h2>제작</h2><div class="prod">{thumb}{script}</div></section>'


def review(r: dict | None) -> str:
    if not r or not r.get("issues"):
        return ""
    items = "".join(
        f'<li class="issue sev-{e(i.get("severity"))}"><span class="sev">{SEVERITY.get(i.get("severity"), "")}</span>'
        f'<div><p>{e(i.get("problem"))}</p><p class="muted">수정 제안: {e(i.get("fix"))}</p></div></li>'
        for i in r["issues"]
    )
    return f'<section id="review"><h2>검토 메모</h2><ul class="issues">{items}</ul></section>'


def sources(trends: list[tuple[str, dict]]) -> str:
    blocks = []
    for platform, t in trends:
        lis = "".join(
            f'<li><a href="{e(s.get("url"))}" target="_blank" rel="noopener">{e(s.get("title"))}</a>'
            f' <span class="muted">{e(s.get("publisher"))} · {e(s.get("date") or "날짜 미상")}</span></li>'
            for s in t.get("sources", [])
        )
        blocks.append(f"<div><h4>{PLATFORM[platform]}</h4><ol class='sources'>{lis}</ol></div>")
    return f'<section id="sources"><h2>출처</h2><div class="src-grid">{"".join(blocks)}</div></section>' if blocks else ""


CSS = """
:root{--bg:#F3F5F2;--surface:#FFFFFF;--ink:#181B19;--muted:#5D655F;--line:#DCE1DB;--accent:#4B3BFF;--accent-soft:#E7E4FF;
--hl:#FFD43B;--rising:#17945A;--steady:#B77B06;--fading:#868C88;--high:#D23B3B;--medium:#B77B06;--low:#868C88;
--display:"Black Han Sans","Malgun Gothic",sans-serif;--body:"IBM Plex Sans KR","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
--mono:"IBM Plex Mono",ui-monospace,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111412;--surface:#1A1E1B;--ink:#EBEFEB;--muted:#9BA39D;
--line:#2C322E;--accent:#9A90FF;--accent-soft:#25214D;--hl:#FFD43B;--rising:#3CC283;--steady:#E0A93A;--fading:#8D948F;
--high:#F06A6A;--medium:#E0A93A;--low:#8D948F;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111412;--surface:#1A1E1B;--ink:#EBEFEB;--muted:#9BA39D;--line:#2C322E;--accent:#9A90FF;
--accent-soft:#25214D;--hl:#FFD43B;--rising:#3CC283;--steady:#E0A93A;--fading:#8D948F;--high:#F06A6A;--medium:#E0A93A;--low:#8D948F;color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:15px/1.6 var(--body);margin:0}
.wrap{max-width:1120px;margin:0 auto;padding-inline:16px;padding-block:28px 64px;display:grid;gap:44px}
h1,h2,h3{font-family:var(--display);font-weight:400;letter-spacing:.01em;text-wrap:balance;margin:0}
h1{font-size:clamp(1.9rem,4.5vw,2.8rem);line-height:1.15}
h2{font-size:1.6rem;margin-bottom:14px}
h3{font-size:1.2rem}
h4{font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:22px 0 8px}
p{margin:0}
a{color:var(--accent)}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.muted{color:var(--muted)}.small{font-size:.8em;text-transform:none;letter-spacing:0}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
header{display:grid;gap:12px}
.eyebrow{font-family:var(--mono);font-size:.78rem;color:var(--muted);letter-spacing:.04em}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.tag{display:inline-block;font-size:.75rem;padding:2px 8px;border-radius:4px;background:var(--bg);border:1px solid var(--line);color:var(--muted);white-space:nowrap}
nav{position:sticky;top:env(safe-area-inset-top,0px);z-index:2;background:var(--bg);border-bottom:1px solid var(--line);
display:flex;gap:18px;overflow-x:auto;padding-block:10px;margin-top:-24px}
nav a{color:var(--ink);text-decoration:none;font-size:.9rem;white-space:nowrap}
nav a:hover{color:var(--accent)}
.trends{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:20px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:22px;min-width:0}
.panel-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
.lede{margin-top:10px;font-size:1.02rem}
.metrics{margin-top:8px;font-size:.85rem;color:var(--muted)}
.bars{display:grid;gap:7px}
.bar-row{display:grid;grid-template-columns:minmax(5.5rem,9rem) 1fr 2.2rem;gap:10px;align-items:center;font-size:.88rem}
.bar-label{overflow-wrap:anywhere}
.track{height:10px;background:var(--bg);border-radius:5px;position:relative;overflow:hidden}
.fill{position:absolute;inset:0 auto 0 0;background:var(--accent);border-radius:5px}
.axis{font-size:.7rem;color:var(--muted)}
.ticks{position:relative;height:1em}
.ticks i{position:absolute;font-style:normal;font-family:var(--mono);transform:translateX(-50%)}
.ticks i:first-child{transform:none}.ticks i:last-child{transform:translateX(-100%)}
.fmts,.plain,.examples,.issues,.sources,.timeline{list-style:none;margin:0;padding:0}
.fmts{display:grid;gap:12px}
.fmt{border-top:1px solid var(--line);padding-top:12px}
.fmt-head{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:4px}
.pill{font-size:.72rem;font-weight:700;padding:1px 8px;border-radius:999px;color:#fff}
.pill.rising{background:var(--rising)}.pill.steady{background:var(--steady)}.pill.fading{background:var(--fading)}
.examples li{display:flex;justify-content:space-between;gap:12px;font-size:.84rem;margin-top:4px}
.examples a{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.plain li{margin-bottom:6px}
details{margin-top:16px;font-size:.88rem}
summary{cursor:pointer;color:var(--muted)}
.concepts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:16px}
.concept{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px;display:grid;gap:8px;align-content:start;position:relative}
.concept.chosen{border:2px solid var(--accent);box-shadow:0 6px 24px -12px var(--accent)}
.chosen-label{justify-self:start;font-size:.72rem;font-weight:700;color:var(--accent);background:var(--accent-soft);padding:2px 8px;border-radius:4px}
.logline{font-size:.95rem}
.meta{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.total{margin-left:auto;font-size:1.3rem;font-weight:600}.total small{font-size:.7rem;color:var(--muted)}
.score{display:flex;justify-content:space-between;font-size:.82rem;color:var(--muted)}
.dots{display:flex;gap:3px}.dots i{width:14px;height:6px;border-radius:2px;background:var(--line)}.dots i.on{background:var(--accent)}
.why{font-size:.88rem;border-top:1px solid var(--line);padding-top:8px}
.risk{font-size:.82rem;color:var(--steady)}
.prod{display:grid;grid-template-columns:minmax(0,300px) minmax(0,1fr);gap:28px;align-items:start}
.phone{margin:0;position:sticky;top:calc(env(safe-area-inset-top,0px) + 60px)}
.phone img{display:block;width:100%;height:auto;aspect-ratio:9/16;border-radius:22px;border:6px solid var(--ink);background:var(--ink)}
.phone figcaption{font-size:.78rem;color:var(--muted);text-align:center;margin-top:8px;font-family:var(--mono)}
.script{display:grid;gap:14px;min-width:0}
.hook{margin:0;font-family:var(--display);font-size:1.5rem;line-height:1.3;background:linear-gradient(transparent 62%,var(--hl) 62%);
color:var(--ink);justify-self:start;padding-inline:2px}
:root[data-theme="dark"] .hook{background:none;color:var(--hl)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .hook{background:none;color:var(--hl)}}
.timeline{display:grid;border-left:2px solid var(--line);margin-left:6px}
.beat{display:grid;grid-template-columns:5.2rem 1fr;gap:12px;padding:10px 0 10px 14px;position:relative}
.beat::before{content:"";position:absolute;left:-7px;top:16px;width:12px;height:12px;border-radius:50%;background:var(--surface);border:2px solid var(--accent)}
.tc{font-family:var(--mono);font-size:.82rem;color:var(--accent);padding-top:2px}
.beat-body{display:grid;gap:4px;min-width:0}
.visual{font-size:.84rem;color:var(--muted)}
.narr{font-size:1rem}
.cap{justify-self:start;font-size:.8rem;font-weight:700;background:var(--ink);color:var(--bg);padding:1px 8px;border-radius:3px}
.sfx{font-size:.78rem;color:var(--muted)}
.cta{font-size:.95rem}
.copy-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:16px;font-size:.88rem}
.copy-grid h4{margin-top:0}
.tags{color:var(--accent);margin-top:6px;overflow-wrap:anywhere}
.narration{white-space:pre-wrap;font-family:var(--body);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px;margin:10px 0 0}
.issues{display:grid;gap:10px}
.issue{display:grid;grid-template-columns:3.2rem 1fr;gap:12px;background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--low);border-radius:6px;padding:12px 14px}
.issue.sev-high{border-left-color:var(--high)}.issue.sev-medium{border-left-color:var(--medium)}
.sev{font-size:.78rem;font-weight:700;color:var(--muted)}
.src-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:20px;font-size:.86rem}
.sources{padding-left:1.2em;list-style:decimal}.sources li{margin-bottom:6px;overflow-wrap:anywhere}
footer{font-size:.8rem;color:var(--muted)}
@media (max-width:720px){.prod{grid-template-columns:1fr}.phone{position:static;max-width:260px;justify-self:center}.beat{grid-template-columns:1fr;gap:2px}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
"""


def build(ws: Path, page_title: str | None = None) -> str:
    trends = [(p, t) for p in ("youtube", "instagram") if (t := load(ws, f"01_trends_{p}.json"))]
    concepts = load(ws, "02_concepts.json")
    script = load(ws, "03_script.json")
    rev = load(ws, "04_review.json")
    tmap = dict(trends)

    collected = next((t.get("collected_at") for _, t in trends if t.get("collected_at")), "")
    title = (script or {}).get("title") or f"숏폼 트렌드 보드 {collected}".strip()
    selected = next((k for k in (concepts or {}).get("concepts", []) if k.get("id") == (concepts or {}).get("selected_id")), None)

    nav = [("trends", "트렌드")]
    if concepts:
        nav.append(("concepts", "기획안"))
    if script or (ws / "03_thumbnail.png").exists():
        nav.append(("production", "제작"))
    if rev and rev.get("issues"):
        nav.append(("review", "검토 메모"))
    if trends:
        nav.append(("sources", "출처"))

    chips = [f'<span class="tag">조사일 {e(collected)}</span>'] if collected else []
    if selected:
        chips.append(f'<span class="tag">{e(selected.get("format_ref"))}</span>')
    if rev:
        chips.append(f'<span class="tag">검토 {"통과" if rev.get("verdict") == "PASS" else "수정 필요"}</span>')

    return (
        f"<title>{e(page_title or title)}</title>\n"
        '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=IBM+Plex+Mono:wght@400;600'
        '&family=IBM+Plex+Sans+KR:wght@400;600;700&display=swap">\n'
        f"<style>{CSS}</style>\n"
        '<div class="wrap">'
        f'<header><p class="eyebrow">SHORTS · REELS 기획 보드</p><h1>{e(title)}</h1>'
        + (f'<p class="lede">{e(selected.get("logline"))}</p>' if selected else "")
        + f'<div class="chips">{"".join(chips)}</div></header>'
        + '<nav aria-label="섹션">' + "".join(f'<a href="#{i}">{l}</a>' for i, l in nav) + "</nav>"
        + '<section id="trends"><h2>요즘 숏폼 트렌드</h2><div class="trends">'
        + trend_panel(tmap.get("youtube"), "youtube") + trend_panel(tmap.get("instagram"), "instagram")
        + "</div></section>"
        + concept_cards(concepts)
        + production(script, ws)
        + review(rev)
        + sources(trends)
        + '<footer>주제 점수는 보고서 안에서의 상대 비교값입니다. 조회수는 확인된 값만 표시하며, 인스타그램 수치는 2차 출처 인용값입니다.</footer>'
        + "</div>\n"
    )


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        return 2
    ws, out = Path(sys.argv[1]), Path(sys.argv[2])
    if not ws.is_dir():
        print(f"작업 폴더가 없습니다: {ws}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(ws, sys.argv[3] if len(sys.argv) == 4 else None), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
