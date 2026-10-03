# 숏폼 하네스 데이터 형식

에이전트들은 이 형식의 JSON 파일로 결과를 주고받는다. `build_dashboard.py`도 이 형식을 읽으므로, 필드를 바꾸면 스크립트도 같이 고친다. 모든 파일은 UTF-8, `ensure_ascii=False`.

경로 기준: `_workspace_shorts/` (실행 중간물), `content/creator_profile.md` (실행 간 유지), `output/shorts/{YYYYMMDD}_{slug}/` (최종물).

## 01_trends_{platform}.json — trend-researcher

```json
{
  "platform": "youtube | instagram",
  "collected_at": "2026-10-03",
  "region": "KR",
  "period": "최근 30일",
  "data_basis": "web | web+api",
  "summary": "한두 문장 핵심 요약",
  "formats": [
    {
      "name": "POV 상황극",
      "description": "무엇을 어떻게 찍는 형식인지",
      "signal": "rising | steady | fading",
      "evidence": "high | medium | low",
      "examples": [{"title": "", "url": "", "views": 1200000, "published": "2026-09-20", "channel": ""}],
      "source_ids": ["s1", "s3"]
    }
  ],
  "topics": [
    {"keyword": "가을 루틴", "momentum": 82, "note": "왜 뜨는지", "source_ids": ["s2"]}
  ],
  "hooks": [{"pattern": "결과 먼저 보여주기", "example": "\"이거 3천원으로 만든 거예요\""}],
  "audio": [{"name": "", "note": "", "source_ids": []}],
  "metrics": null,
  "sources": [{"id": "s1", "title": "", "publisher": "", "url": "", "date": "2026-09-28"}],
  "caveats": ["인스타그램은 공개 API가 없어 조회수는 기사·리포트 인용값"]
}
```

- `momentum`: 0~100 **상대 점수**(이 보고서 안에서의 비교용). 절대 수치처럼 쓰지 않는다.
- `metrics`: YouTube API를 썼을 때만 `fetch_youtube_shorts.py` 출력의 `summary` 객체를 그대로 넣는다.
- `examples[].views`는 확인된 값만. 모르면 `null`.

## 02_concepts.json — content-planner

```json
{
  "profile_summary": "프로필 한 줄 요약",
  "concepts": [
    {
      "id": "c1",
      "title": "작업 제목",
      "logline": "한 문장 요약",
      "format_ref": "POV 상황극",
      "trend_refs": ["youtube:formats[0]", "instagram:topics[2]"],
      "why_fit": "이 크리에이터에게 맞는 이유",
      "length_sec": 30,
      "platforms": ["youtube", "instagram"],
      "production": "촬영·편집 난이도와 필요한 것",
      "scores": {"trend": 4, "fit": 5, "feasibility": 4, "differentiation": 3},
      "total": 16,
      "risks": ["저작권 음원 의존"]
    }
  ],
  "selected_id": null
}
```
점수는 1~5. `selected_id`는 사용자가 고른 뒤 오케스트레이터가 채운다.

## 03_script.json — script-writer

```json
{
  "concept_id": "c1",
  "title": "업로드 제목",
  "length_sec": 30,
  "hook": {"visual": "", "line": "", "on_screen_text": ""},
  "beats": [
    {"t_start": 0, "t_end": 3, "visual": "", "narration": "", "caption": "", "sfx": ""}
  ],
  "cta": "",
  "description": {"youtube": "", "instagram": ""},
  "hashtags": {"youtube": ["#shorts"], "instagram": []},
  "narration_text": "TTS용 내레이션 전체 (beats의 narration을 이은 것, 읽는 말로 정리)",
  "word_count": 0
}
```
`beats`는 시간이 0부터 `length_sec`까지 빈틈·겹침 없이 이어져야 한다.

## 03_thumbnail_spec.json / 03_thumbnail.png — thumbnail-designer

spec 형식은 `{PLUGIN}/skills/thumbnail-design/references/spec.md`. 렌더 결과는 `03_thumbnail.png`(9:16), 선택적으로 `03_thumbnail_16x9.png`. 렌더 리포트는 `03_thumbnail_report.json`.

## 04_review.json — content-reviewer

```json
{
  "verdict": "PASS | FIX_REQUIRED",
  "issues": [
    {"target": "script | thumbnail | concept", "severity": "high | medium | low",
     "problem": "", "evidence": "", "fix": "", "owner": "script-writer | thumbnail-designer"}
  ],
  "strengths": []
}
```
