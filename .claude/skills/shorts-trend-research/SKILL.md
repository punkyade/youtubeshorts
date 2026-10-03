---
name: shorts-trend-research
description: "유튜브 쇼츠·인스타그램 릴스의 최신 숏폼 트렌드(뜨는 포맷, 주제, 훅 패턴, 음원)를 웹 검색과 YouTube Data API로 조사해 출처·날짜가 붙은 구조화 보고서로 만드는 방법. '쇼츠 트렌드 조사', '릴스 요즘 뭐 떠', '숏폼 트렌드 분석', '인기 쇼츠 찾아줘', '트렌드 업데이트' 요청이나 trend-researcher 에이전트 작업 시 반드시 사용할 것. 기획안 작성은 shorts-planning, 일반 사업 시장조사는 이 스킬 대상이 아니다."
---

# 숏폼 트렌드 조사

목표는 "요즘 뜬다"는 막연한 말이 아니라, **날짜와 출처가 붙은 관찰**을 모으는 것이다. 기획자는 이 보고서만 보고 판단하므로, 근거 없는 주장은 기획 전체를 틀어지게 한다.

출력 형식: `shorts-orchestrator/references/schemas.md`의 `01_trends_{platform}.json`.

## 조사 순서

1. **프로필 읽기** — `content/creator_profile.md`의 분야를 확인한다. 조사는 "플랫폼 전반 트렌드"와 "이 분야 안의 트렌드"를 둘 다 다룬다. 전반 트렌드만 보면 기획에 쓸 게 없고, 분야만 보면 형식의 흐름을 놓친다.
2. **데이터 수집** — 아래 플랫폼별 방법.
3. **패턴 추출** — 개별 영상이 아니라 반복되는 **포맷**(찍는 방식), **주제**, **훅**(첫 1~3초), **음원**을 뽑는다. 사례가 2개 이상 독립 출처에서 보여야 포맷으로 인정한다.
4. **신호 판정** — `signal`: 최근 30일 언급·사례가 늘면 rising, 꾸준하면 steady, 피로감·하락 언급이 있으면 fading. `evidence`: 수치 있는 출처 2개 이상 high, 사례만 여러 개 medium, 단일 출처 low.
5. **JSON 작성** — 모든 포맷·주제에 `source_ids`. 조사 한계는 `caveats`에.

## 플랫폼별 방법

### YouTube Shorts
- **API 사용 가능 시**(`YOUTUBE_API_KEY`):
  ```
  python .claude/skills/shorts-trend-research/scripts/fetch_youtube_shorts.py --chart --region KR --out _workspace_shorts/raw_yt_chart.json
  python .claude/skills/shorts-trend-research/scripts/fetch_youtube_shorts.py --q "<분야 키워드>" --days 14 --region KR --out _workspace_shorts/raw_yt_search.json
  ```
  `--chart`(인기 차트, 할당량 1단위)를 먼저 쓰고, 검색(`--q`, 호출당 100단위)은 분야 키워드 2~3개로 제한한다. 출력의 `summary`를 `metrics`에 넣고, 상위 영상을 `examples`에 쓴다. 조회수/일, 참여율(좋아요+댓글/조회수)로 비교한다 — 누적 조회수는 오래된 영상이 유리해서 "요즘"을 왜곡한다.
- **웹 조사**: WebSearch로 `"유튜브 쇼츠 트렌드 {YYYY년 M월}"`, `"YouTube Shorts trends {Month YYYY}"`, `"{분야} 쇼츠 인기"`, 유튜브 공식 블로그/Culture & Trends 리포트, 마케팅 매체(예: 오픈애즈, 메조미디어, 디지털 인사이트), 영문 매체(Social Media Today, TubeFilter) 등을 검색하고 WebFetch로 본문을 확인한다.

### Instagram Reels
- 공개 트렌드 API가 없다. `caveats`에 반드시 "조회수 등은 2차 출처 인용값"이라 적는다.
- WebSearch: `"인스타 릴스 트렌드 {YYYY년 M월}"`, `"Instagram Reels trends {Month YYYY}"`, `"trending reels audio this week"`, Instagram 공식 @creators 관련 기사, Later·Hootsuite·Sprout Social 등의 주간/월간 트렌드 글.
- 릴스는 **음원 트렌드**가 포맷을 끌고 가는 경우가 많으므로 `audio`를 꼭 채운다. 음원은 저작권·상업 계정 사용 제한 가능성을 `note`에 적는다.

## 신선도 규칙

- 오늘 날짜를 기준으로 30일 이내 자료를 우선, 90일 초과 자료는 배경 설명에만 쓰고 `caveats`에 표시한다.
- 출처의 게시일을 확인할 수 없으면 `date: null`로 두고 evidence를 한 단계 낮춘다.
- 날짜가 연도 없이 "이번 주"로만 된 글은 게시일로 환산한다.

## 하지 않을 것

- 조회수·성장률을 추정해서 만들어 내지 않는다. 모르면 `null`.
- 한 영상의 성공을 포맷 트렌드로 일반화하지 않는다.
- 로그인이 필요한 페이지나 플랫폼 이용약관상 스크래핑이 금지된 페이지를 긁지 않는다. 공개 기사·리포트·공식 API만 쓴다.

## 품질 기준 (완료 전 확인)

- [ ] formats 4~8개, topics 5~10개, hooks 3개 이상, (instagram) audio 3개 이상
- [ ] 모든 formats/topics에 source_ids, 모든 sources에 url
- [ ] 분야 특화 항목이 최소 2개 (프로필 분야와 연결)
- [ ] summary가 "그래서 지금 무엇을 찍어야 하나"에 답한다
