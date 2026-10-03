# 썸네일 spec 형식 (render_thumbnail.py)

좌표는 픽셀, 원점은 왼쪽 위. `box`는 `[x, y, 너비, 높이]`.

```json
{
  "preset": "shorts",
  "out": "03_thumbnail.png",
  "background": {"type": "gradient", "colors": ["#1E2A78", "#0B0F2E"], "angle": 160},
  "shapes": [
    {"type": "rect", "box": [80, 520, 860, 12], "fill": "#FFE14D", "opacity": 1, "radius": 6},
    {"type": "circle", "center": [900, 300], "r": 160, "fill": "#FFFFFF", "opacity": 0.08}
  ],
  "texts": [
    {
      "text": "3천원으로\n카페 라떼 만들기",
      "box": [80, 600, 860, 520],
      "weight": "bold",
      "max_size": 170, "min_size": 80, "line_spacing": 1.12,
      "color": "#FFFFFF", "stroke_width": 0,
      "align": "left", "valign": "top",
      "highlight": {"words": ["3천원으로"], "color": "#FFE14D"}
    },
    {
      "text": "편의점 재료만",
      "box": [80, 1180, 860, 120],
      "weight": "regular", "max_size": 64, "min_size": 40,
      "color": "#FFFFFF", "align": "left",
      "plate": {"color": "#000000", "opacity": 0.45, "padding": 20, "radius": 16}
    }
  ]
}
```

| 키 | 값 | 기본 |
|---|---|---|
| `preset` | `shorts`(1080×1920) / `youtube`(1280×720) / `square`(1080×1080) | shorts |
| `size` | `[w, h]` — preset 대신 직접 지정 | — |
| `background.type` | `solid`(color) / `gradient`(colors 2개, angle CSS식 180=위→아래) / `image`(path는 spec 기준 상대 경로, darken 0~1) | solid #111111 |
| `shapes[].type` | `rect`(box, radius) / `circle`(center, r). fill, opacity | — |
| `texts[].weight` | `bold`(맑은 고딕 Bold) / `regular`. `font`에 .ttf 경로를 주면 우선 | bold |
| `texts[].max_size`/`min_size` | 박스에 맞을 때까지 4px씩 줄인다 | 160 / 48 |
| `texts[].highlight.words` | 공백으로 나뉜 **단어 단위**로 일치하면 색을 바꾼다 | — |
| `texts[].plate` | 글자 뒤 반투명 판 | 없음 |
| `stroke_width`/`stroke_color` | 외곽선 | 0 / #000000 |

줄바꿈은 `\n`으로 직접 지정하는 것이 가장 좋다 — 자동 줄바꿈은 공백 단위이고, 공백 없는 긴 단어는 글자 단위로 끊긴다.

## 리포트 (`--report`)

```json
{"ok": true, "out": "...", "size": [1080, 1920],
 "texts": [{"text": "...", "font_size": 150, "lines": ["3천원으로", "카페 라떼 만들기"], "fits": true}],
 "warnings": ["'편의점 재료만' 텍스트 박스가 하단 제목·캡션 영역과 겹침"]}
```
경고 종류: 플랫폼 UI 겹침(safe area), 대비 4.5:1 미만, 최소 크기에서도 넘침. 경고가 0이 될 때까지 spec을 고친다.

## 안전 영역 (shorts 1080×1920)

- 상단 0~154px: 상태바·검색
- 하단 1536~1920px: 제목·채널명·캡션이 덮음
- 오른쪽 950px~ (세로 864px 아래): 좋아요·댓글·공유 버튼
- 핵심 문구는 y 250~1450, x 80~930 안에 둔다
- 인스타그램 프로필 그리드는 커버를 3:4(가운데)로 잘라 보여주므로 핵심 문구를 세로 중앙 1440px(y 240~1680) 안에 둔다
