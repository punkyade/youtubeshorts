---
name: thumbnail-design
description: "쇼츠·릴스 썸네일(커버 이미지)을 기획하고 로컬 Pillow 템플릿으로 PNG를 렌더링하는 방법 — 문구 작성, 구도, 색, 플랫폼 UI 안전 영역, 대비 검사. '썸네일 만들어줘', '커버 이미지', '썸네일 문구', '썸네일만 다시', '글자가 작아', '더 눈에 띄게' 요청이나 thumbnail-designer 작업 시 반드시 사용할 것. AI 이미지 생성이나 영상 편집은 이 스킬 범위가 아니다."
---

# 숏폼 썸네일

숏폼 썸네일은 피드에서 자동 재생 전에, 그리고 채널·프로필 그리드에서 보인다. 그리드에서는 **엄지손톱 크기**로 보이므로, 작게 줄여도 읽히는 3~8글자 핵심 문구가 전부다.

입력: `02_concepts.json`의 선택안(title, logline, format_ref), `content/creator_profile.md`(톤, 분야)
출력: `_workspace_shorts/03_thumbnail_spec.json`, `03_thumbnail.png`, `03_thumbnail_report.json`

## 절차

1. **문구 3안 작성** — 메인 문구(3~8자, 최대 2줄) + 보조 문구(선택, 10자 이내). 유형:
   - 결과형: "3천원 라떼", "10kg 감량 식단"
   - 궁금증형: "이거 왜 됨?", "아무도 안 알려줌"
   - 대비형: "1만원 vs 10만원"
   제목·대본 훅과 **같은 말을 반복하지 않고 보완**한다. 숫자·고유명사가 있으면 앞에 둔다.
2. **구도 선택** (`references/layouts.md`의 4가지 중) — 포맷에 맞춰 고른다.
3. **색** — 배경과 강조색 2~3개만. 분야 관습을 참고하되(요리=따뜻한 색, IT=어두운 배경+형광 강조) 프로필 톤이 우선. 강조색은 메인 문구의 핵심어 1개에만.
4. **spec 작성** — 형식은 `references/spec.md`. 메인 문구는 `max_size` 140~180, 보조는 56~72. 줄바꿈은 `\n`으로 직접 지정.
5. **렌더**
   ```
   python .claude/skills/thumbnail-design/scripts/render_thumbnail.py _workspace_shorts/03_thumbnail_spec.json --report _workspace_shorts/03_thumbnail_report.json
   ```
6. **경고 0개가 될 때까지 수정** — safe area 겹침은 박스 이동, 대비 부족은 `stroke_width`(8~12) 또는 `plate` 추가, 넘침은 문구를 줄인다(글자 크기를 `min_size` 아래로 내리는 것보다 낫다).
7. **눈으로 확인** — Read 도구로 PNG를 열어 본다. 360×640으로 줄여서도 메인 문구가 읽히는지 확인한다(`python -c "from PIL import Image; Image.open('...').resize((180,320)).save('..._small.png')"`).
8. (선택) 유튜브 롱폼 겸용이 필요하면 `preset: "youtube"`로 16:9 버전 `03_thumbnail_16x9.png`도 만든다.

## 판단 기준

- 한 화면에 요소 3개 이하(메인 문구, 보조 문구, 도형/강조 1개). 많을수록 엄지손톱 크기에서 뭉개진다.
- 메인 문구는 화면 너비의 70% 이상을 차지할 만큼 크게.
- 얼굴·제품 사진이 있으면 `background.type: "image"` + `darken` 0.3~0.5로 문구 대비를 확보한다. 사진은 사용자가 준 파일만 쓴다(인터넷 이미지 무단 사용 금지).
- 과장 문구("무조건", "100%")나 내용과 다른 낚시 문구는 쓰지 않는다 — 시청 지속률이 떨어지고 플랫폼 정책 위반 소지가 있다.

## 리포트에 남길 것

`03_thumbnail_report.json`(스크립트 출력)에 더해, 선택하지 않은 문구 2안과 선택 이유를 `03_thumbnail_notes.md`에 짧게 적는다. 사용자가 "썸네일만 다시"를 요청하면 이 노트에서 다른 안을 바로 시도할 수 있다.

## 이전 결과가 있을 때

기존 spec을 읽고 피드백 부분만 바꿔 다시 렌더한다. 이전 PNG는 `03_thumbnail_prev.png`로 보존한다.
