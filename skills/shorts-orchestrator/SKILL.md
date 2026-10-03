---
name: shorts-orchestrator
description: "유튜브 쇼츠·인스타그램 릴스 숏폼 트렌드를 조사해 대시보드로 보여주고, 크리에이터 프로필에 맞는 영상 기획 → 대본 → 썸네일까지 만드는 에이전트들을 조율하는 오케스트레이터. '쇼츠 트렌드', '릴스 트렌드', '요즘 뭐가 떠', '숏폼 기획', '영상 아이디어', '대본 써줘', '썸네일 만들어줘', '콘텐츠 기획' 요청 시 반드시 이 스킬을 사용. 후속 작업: 다시 실행, 트렌드 업데이트, '대본만 다시', '썸네일만 다시', '다른 기획안으로', 수정, 보완, 이전 결과 기반으로 개선, 프로필 바꾸기 요청 시에도 이 스킬을 사용."
---

# Shorts Orchestrator

> **경로:** `{PLUGIN}` = youtube-shorts 플러그인 루트. 이 스킬이 로딩될 때 주어지는 "Base directory for this skill"의 두 단계 위 폴더다(`…/skills/<스킬 이름>` → 상위의 상위). 서브 에이전트는 오케스트레이터가 프롬프트로 준 절대 경로를 쓴다. Mac·Linux에서 `python`이 없으면 `python3`.

숏폼 트렌드 조사 → 맞춤 기획 → 대본·썸네일 제작 → 검토 → 대시보드 공개를 조율한다. 영상 조립은 끝난 뒤 `shorts-video` 스킬이 맡는다.

## 실행 모드: 서브 에이전트

`TeamCreate`가 없는 환경이므로 `Agent` 도구로 커스텀 에이전트를 호출하고 `_workspace_shorts/` 파일로 데이터를 넘긴다. 모든 `Agent` 호출에 `model: "opus"`를 명시한다. 사용자 확인(프로필, 기획안 선택)은 리더(이 세션)가 `AskUserQuestion`으로 직접 한다 — 서브 에이전트는 사용자에게 묻지 못한다.

데이터 형식: `references/schemas.md` (반드시 읽고, 에이전트 프롬프트에 해당 절을 지목한다).

## 플러그인 실행 규칙

이 하네스는 `youtube-shorts` 플러그인으로 설치되어, 플러그인 파일(설치 캐시)과 사용자 데이터(작업 폴더)가 서로 다른 곳에 있다.

- **두 경로를 먼저 정한다.** `{PLUGIN}` = 위 경로 안내대로 구한 플러그인 루트 절대 경로. `{PROJECT}` = 사용자가 Claude Code를 연 현재 작업 디렉터리. 사용자 데이터(`content/`, `_workspace_shorts/`, `output/`)는 모두 `{PROJECT}` 기준이며 플러그인 폴더에는 절대 쓰지 않는다 — 플러그인을 업데이트하면 그 폴더는 교체된다.
- **에이전트 이름에는 플러그인 접두사를 붙인다:** `subagent_type="youtube-shorts:<에이전트 이름>"`.
- **모든 에이전트 프롬프트에 두 절대 경로를 넣는다.** 서브 에이전트는 스킬 경로를 스스로 알 수 없다. 형식: `플러그인 루트: <{PLUGIN}>. 프로젝트 루트: <{PROJECT}>. 먼저 <{PLUGIN}>/skills/<스킬>/SKILL.md 를 읽어라.` 프롬프트 안의 `{PLUGIN}` 표기도 실제 경로로 바꿔 보낸다.
- **첫 실행 때 한 번:** `{PROJECT}`가 git 저장소이고 `.gitignore`에 `content/creator_profile.md`, `content/episodes.md`, `_workspace_shorts*/`, `output/`이 없으면, 개인 데이터가 커밋되지 않도록 추가할지 사용자에게 묻는다.

## 에이전트 구성

| 에이전트 (`subagent_type`) | 역할 | 스킬 | 출력 |
|---|---|---|---|
| `youtube-shorts:trend-researcher` ×2 | 플랫폼별 트렌드 조사 (youtube / instagram 각각 호출) | shorts-trend-research | `01_trends_{platform}.json` |
| `youtube-shorts:content-planner` | 트렌드 × 프로필 → 기획안 3개 | shorts-planning | `02_concepts.json` |
| `youtube-shorts:script-writer` | 선택된 기획 → 초 단위 대본 | shorts-scriptwriting | `03_script.json`, `03_narration.txt` |
| `youtube-shorts:thumbnail-designer` | 썸네일 spec 작성·렌더 | thumbnail-design | `03_thumbnail_spec.json`, `03_thumbnail.png` |
| `youtube-shorts:content-reviewer` | 근거·적합성·플랫폼 규칙 검토 | (에이전트 정의에 인라인) | `04_review.json` |

## 워크플로우

### Phase 0: 컨텍스트 확인

0. 환경 점검: `python {PLUGIN}/skills/shorts-setup/scripts/check_env.py --json` (몇 초, 읽기 전용).
   - 필수 항목이 하나라도 `ok: false`면 제작을 시작하지 말고 `shorts-setup` 스킬로 넘어가 설치·인증을 끝낸 뒤 돌아온다.
   - 첫 실행(프로필 없음)이면 선택 항목 중 빠진 것과 그 대체 동작을 한 줄로 알린다(예: "YouTube API 키가 없어 웹 자료로만 조사합니다. 설정하려면 '환경 점검해줘'"). 이후 실행에서는 반복하지 않는다.
1. `content/creator_profile.md`, `_workspace_shorts/` 존재 여부 확인.
2. 실행 모드:
   - **초기/새 실행**: `_workspace_shorts/`가 없거나 사용자가 새 주제·새 트렌드 조사를 원함 → 기존 폴더를 `_workspace_shorts_{YYYYMMDD_HHMMSS}/`로 옮기고 Phase 1부터
   - **부분 재실행**: "대본만 다시" → Phase 4의 script-writer만(+ Phase 5), "썸네일만 다시" → thumbnail-designer만, "다른 기획안으로" → Phase 3의 선택 단계부터
   - **트렌드만 업데이트**: Phase 2만 다시 하고 대시보드 갱신
   - **다음 회차** ("2화 만들어줘", "{시리즈명} 다음 편"): 프로필의 시리즈 규칙과 이전 회차 산출물(`output/shorts/` 최신 폴더의 `script.md`·`thumbnail_spec.json`·`thumbnail_notes.md`)을 기준으로 삼는다.
     1. 트렌드 파일이 7일 이내면 재사용하고(기존 `_workspace_shorts/`의 01_* 파일을 새 작업 폴더로 복사), 아니면 Phase 2를 다시 한다.
     2. 기획안 3개 대신 **회차 주제 후보 3개**를 리더가 제안해 `AskUserQuestion`으로 고르게 한다. `content/episodes.md`에 기록된 이전 회차 주제와 겹치지 않게 하고, 프로필의 화면 소스·출연 방식 제약으로 만들 수 있는 주제만 고른다.
     3. 선택한 주제와 정확한 절차를 `00_request.md`에 고정한 뒤 Phase 4(대본·썸네일 병렬) → Phase 5 → Phase 6. 대본은 이전 회차의 비트 구조와 고정 비트("맥락 한 줄"), 썸네일은 고정 요소 규칙을 그대로 따르게 프롬프트에 명시한다.
     4. 끝나면 `content/episodes.md`에 회차 번호, 날짜, 주제, 출력 폴더를 한 줄 추가한다(파일이 없으면 `| 회차 | 날짜 | 주제 | 출력 폴더 |` 표로 새로 만든다). 첫 회차를 마칠 때도 1화 줄을 기록한다.
3. 트렌드 파일이 7일보다 오래됐으면 기획 전에 다시 조사할지 사용자에게 묻는다. 숏폼 트렌드는 주 단위로 바뀐다.

### Phase 1: 크리에이터 프로필 (리더)

`content/creator_profile.md`가 없거나 사용자가 바꾸길 원하면 `AskUserQuestion`으로 모은다(한 번에 최대 4문항, 2회 이내):
- 분야·주제(요리, IT, 육아, 자기계발…)와 목표(구독자 성장, 판매, 브랜딩)
- 타깃 시청자(나이대, 관심사)
- 출연 방식: 얼굴 출연 / 손·목소리만 / 얼굴·목소리 없이(자막+TTS 내레이션)
- 제작 여건: 주당 가능 편수, 장비(폰/카메라), 편집 숙련도
- 말투·톤, 우선 플랫폼, 피하고 싶은 것

`content/creator_profile.md`에 저장한다(다음 실행에서 재사용). 형식은 `{PLUGIN}/skills/shorts-orchestrator/references/profile-example.md`를 따른다. 이번 실행에서 다루고 싶은 주제 힌트가 있으면 `_workspace_shorts/00_request.md`에 적는다.

### Phase 2: 트렌드 조사 (병렬)

한 메시지에서 trend-researcher를 두 번 호출한다(`run_in_background: true`):
```
Agent(subagent_type="youtube-shorts:trend-researcher", model="opus", run_in_background=true,
      description="유튜브 쇼츠 트렌드 조사",
      prompt="platform=youtube. 플러그인 루트: <{PLUGIN} 절대 경로>. 프로젝트 루트: <{PROJECT} 절대 경로>.
              먼저 {PLUGIN}/skills/shorts-trend-research/SKILL.md 를 읽어라. content/creator_profile.md와 _workspace_shorts/00_request.md를 읽고
              shorts-trend-research 스킬대로 조사해 _workspace_shorts/01_trends_youtube.json을
              {PLUGIN}/skills/shorts-orchestrator/references/schemas.md 형식으로 작성하라. 오늘 날짜: <YYYY-MM-DD>.")
Agent(... platform=instagram ... 01_trends_instagram.json)
```
`YOUTUBE_API_KEY` 환경변수가 있으면 youtube 프롬프트에 API 사용을 명시한다.

### Phase 3: 기획 + 선택

1. content-planner 호출 → `02_concepts.json` (기획안 3개).
2. 리더가 `AskUserQuestion`으로 3개 중 하나를 고르게 한다. 각 옵션 preview에 로그라인, 근거 트렌드, 점수, 제작 난이도를 넣는다. 사용자가 "알아서"라고 했으면 `total`이 가장 높은 안을 고르고 그 이유를 알린다.
3. `selected_id`를 기록한다.

### Phase 4: 제작 (병렬)

script-writer와 thumbnail-designer를 한 메시지에서 동시에 호출한다. 둘 다 `02_concepts.json`의 선택안을 입력으로 받는다. 썸네일 문구가 대본 훅과 어긋나지 않도록 thumbnail-designer는 선택안의 `logline`·`title`을 기준으로 하고, Phase 5에서 맞춘다.

### Phase 5: 검토 + 수정 (최대 1회)

1. content-reviewer 호출 → `04_review.json`.
2. `FIX_REQUIRED`면 `owner`별로 해당 에이전트를 이슈 목록과 함께 재호출 → 다시 검토는 하지 않고 수정 결과만 확인한다(리더가 이슈 항목을 대조). 남은 이슈는 대시보드의 "검토 메모"에 표시한다.

### Phase 6: 전달

1. 최종물을 `output/shorts/{YYYYMMDD}_{slug}/`로 복사: `script.md`(사람이 읽는 대본), `script.json`, `narration.txt`, `thumbnail.png`, `thumbnail_spec.json`(영상 카드 배경에도 사용), `trends.json`(두 플랫폼 병합). 시리즈 회차라면 `content/episodes.md`에 기록한다(없으면 새로 만든다).
2. 대시보드 생성:
   ```
   python {PLUGIN}/skills/shorts-orchestrator/scripts/build_dashboard.py _workspace_shorts output/shorts/{폴더}/dashboard.html "{시리즈명} {N}화"
   ```
   세 번째 인자는 페이지 이름(탭·갤러리용, 2~4단어). 긴 업로드 제목은 페이지 본문 제목으로만 쓴다.
3. `Artifact` 도구로 `dashboard.html`을 공개한다(첫 공개는 `icon: "video"`, description 한 문장). 같은 실행에서 고치면 같은 경로로 재공개해 URL을 유지한다.
4. 내레이션 음성 생성 (자동): 프로필의 "음성 (TTS)" 절에 있는 목소리·속도로 `output/shorts/{폴더}/narration.mp3`를 만든다.
   - 프로필에 음성 설정이 없으면(첫 실행) `ko-KR-SunHiNeural`·`ko-KR-InJoonNeural` 두 목소리를 기본 속도로 만들고, 길이가 `length_sec`를 넘으면 맞춘 속도 버전도 함께 만들어 사용자에게 고르게 한다. 고른 목소리·속도와 실측 초당 음절 수(음절 수 ÷ 길이)를 프로필 "음성 (TTS)" 절에 기록하고, 나머지 파일은 지운다.
   - edge-tts CLI: `python -m edge_tts --file .../narration.txt --voice {voice} --rate={+N%} --write-media .../narration.mp3` (`pip install edge-tts` 필요)
   - 길이 확인: edge-tts mp3는 48kbps 고정이라 `파일크기(byte) × 8 / 48000`초. 대본 `length_sec`보다 2초 이상 길면 사용자에게 알리고 대본 축약(script-writer 재호출) 또는 영상 길이 연장 중 고르게 한다.
5. 영상 조립 안내: "`output/shorts/{폴더}/assets/`에 체크리스트의 `beatNN` 파일을 넣고 '영상 만들어줘'라고 하면 초안 mp4를 조립한다"고 알린다. 사용자가 지금 원하면(소스 없이 구성만 보기 포함) `shorts-video` 스킬로 진행한다.
6. 사용자에게 요약(트렌드 핵심 3줄, 선택 기획, 대시보드 링크, 파일 위치)과 피드백 질문.

## 데이터 흐름

```
profile.md ─┬─► trend-researcher(youtube) ─► 01_trends_youtube.json ─┐
            └─► trend-researcher(instagram) ► 01_trends_instagram.json ┤
                                                                       ▼
                              content-planner ─► 02_concepts.json ─► [사용자 선택]
                                                                       │
                         ┌─────────────────────────────────────────────┤
                         ▼                                             ▼
                  script-writer ─► 03_script.json          thumbnail-designer ─► 03_thumbnail.png
                         └──────────────► content-reviewer ◄───────────┘
                                                │ 04_review.json
                                                ▼
                         build_dashboard.py ─► dashboard.html ─► Artifact
```

## 에러 핸들링

| 상황 | 전략 |
|---|---|
| 트렌드 조사 1개 플랫폼 실패 | 1회 재호출. 재실패 시 다른 플랫폼만으로 진행하고 대시보드에 "미수집" 표시 |
| 웹 자료가 오래됨(90일 초과)뿐 | 그대로 쓰되 `caveats`에 명시, 사용자에게 신뢰도 낮음을 알림 |
| YouTube API 키 없음/할당량 초과 | 웹 조사로 대체(`data_basis: "web"`) |
| 썸네일 렌더 실패(폰트 없음 등) | 리포트 오류를 보고 spec 수정 후 1회 재시도, 실패 시 spec만 전달 |
| 기획안이 프로필과 안 맞는다는 사용자 피드백 | 피드백을 `00_request.md`에 추가하고 Phase 3 재실행 |
| Artifact 공개 실패 | 로컬 `dashboard.html` 경로를 안내 |

## 테스트 시나리오

### 정상 흐름
1. "요즘 쇼츠 트렌드 보고 나한테 맞는 영상 기획해줘" → 프로필 없음 → 질문 2회로 프로필 저장
2. 두 플랫폼 병렬 조사 → 기획안 3개 → 사용자가 c2 선택
3. 대본(30초, 6비트)과 썸네일(9:16) 병렬 생성 → 검토 PASS
4. `output/shorts/20261003_.../`에 파일 저장, 대시보드 링크 전달, TTS 음성 생성 제안

### 에러 흐름
1. "썸네일만 다시, 글자가 너무 작아" → 부분 재실행: thumbnail-designer만 호출(피드백 + 이전 spec 경로)
2. 렌더 리포트에 safe-area 경고 → 디자이너가 텍스트 박스를 위로 옮겨 재렌더
3. 대시보드를 같은 경로로 재생성·재공개(URL 유지)
