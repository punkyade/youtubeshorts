---
name: tts-orchestrator
description: "TTS(텍스트 음성 변환) 프로젝트의 구현·검증 에이전트를 조율하는 오케스트레이터. 'TTS 구현해줘', '코드 만들어줘', '기능 추가', '새 엔진 추가(OpenAI/Google/오프라인)', 'CLI 옵션 추가', '버그 고쳐줘', '음성 변환이 안 돼' 등 tts 프로젝트 코드를 만들거나 바꾸는 요청에 반드시 이 스킬을 사용. 후속 작업: 다시 실행, 재실행, 업데이트, 수정, 보완, '테스트만 다시', 'QA만 다시', '엔진 부분만 다시', 이전 결과 기반으로 개선, 실패한 테스트 고치기 요청 시에도 이 스킬을 사용. 설계 질문이나 단순 설명 요청은 직접 응답 가능."
---

# TTS Orchestrator

설계 계약(`tts-architecture`)을 기준으로 코어·엔진을 병렬 구현하고, 테스트와 경계면 QA로 검증한 뒤 결함을 수정하는 루프를 조율한다.

## 실행 모드: 서브 에이전트

이 환경에는 `TeamCreate`/`TaskCreate`가 없으므로 `Agent` 도구로 커스텀 에이전트를 호출하고, 에이전트 간 데이터는 `_workspace/` 파일로 전달한다(반환값은 요약 확인용). 병렬 구간은 한 메시지에서 여러 `Agent` 호출을 보낸다. 팀 도구가 생기면 Phase 2·3을 에이전트 팀으로 바꿀 수 있다 — 두 개발자가 계약 변경을 직접 협의할 수 있어 이득이 크다.

모든 `Agent` 호출에 `model: "opus"`를 명시한다.

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 스킬 | 출력 |
|---|---|---|---|---|
| core-developer | `core-developer` | text/cache/audio/service/config/cli/pyproject | tts-architecture, korean-text-processing | `src/tts/**`(engines 제외), `_workspace/02_core-developer_summary.md` |
| engine-developer | `engine-developer` | engines/ (base, registry, edge…) | tts-architecture, tts-engine-integration | `src/tts/engines/**`, `_workspace/02_engine-developer_summary.md` |
| test-engineer | `test-engineer` | pytest 작성·실행 | tts-testing | `tests/**`, `_workspace/03_test-engineer_report.md` |
| tts-qa-inspector | `tts-qa-inspector` | 경계면 교차 비교 | tts-qa-checklist | `_workspace/03_tts-qa-inspector_report.md` |

경로는 모두 프로젝트 루트(이 `CLAUDE.md`가 있는 폴더) 기준이다. 에이전트 프롬프트에는 현재 작업 디렉터리의 절대 경로를 넣는다.

## 워크플로우

### Phase 0: 컨텍스트 확인

1. `_workspace/`와 `src/tts/` 존재 여부를 확인한다.
2. 실행 모드를 정한다.
   - **초기 실행**: `_workspace/` 없음 → Phase 1부터 전체
   - **부분 재실행**: `_workspace/` 있음 + 특정 부분 요청("테스트만 다시", "엔진만 고쳐줘", "QA 다시") → 해당 에이전트만 호출. 예: 테스트만 → Phase 3의 test-engineer만, 엔진 수정 → Phase 2의 engine-developer → Phase 3 전체
   - **새 작업**: `_workspace/` 있음 + 새 기능/엔진 요청 → 기존 `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 옮기고 Phase 1부터. 이미 있는 코드는 유지하며 증분 개발한다.
3. 부분 재실행 시에는 이전 보고서 경로를 에이전트 프롬프트에 넣는다.

### Phase 1: 준비 (리더 직접 수행)

1. 요청을 정리해 `_workspace/00_input/request.md`에 저장한다: 목표, 범위(어떤 모듈·엔진), 완료 기준, 사용자 제약.
2. 요청이 계약 변경을 필요로 하면(새 옵션 필드, 새 명령 등) **먼저** `tts-architecture/references/contracts.md`를 고치고 CLAUDE.md 변경 이력에 기록한다.
3. 초기 실행이면 `src/tts/__init__.py`, `src/tts/models.py`, `src/tts/errors.py`를 계약 문서의 정의 그대로 작성한다. 두 개발자가 병렬로 이 파일에 의존하기 때문에 리더가 먼저 고정한다.

### Phase 2: 병렬 구현

한 메시지에서 두 에이전트를 동시에 호출한다(`run_in_background: true`). 범위에 한쪽만 해당하면 그쪽만 호출한다.

```
Agent(subagent_type="core-developer", model="opus", run_in_background=true,
      description="TTS 코어 구현",
      prompt="프로젝트 루트: <경로>. _workspace/00_input/request.md를 읽고 범위 내 코어를 구현하라.
              tts-architecture, korean-text-processing 스킬을 먼저 읽을 것.
              [수정 단계라면] 다음 보고서에서 담당=core-developer인 항목을 수정하라: <경로들>.
              완료 시 _workspace/02_core-developer_summary.md 작성.")
Agent(subagent_type="engine-developer", model="opus", run_in_background=true,
      description="TTS 엔진 구현", prompt="...동일 구조, 엔진 범위...")
```

두 결과를 기다린 뒤 summary를 읽는다. 둘 중 하나라도 **계약 변경 제안**을 냈다면 리더가 판단한다: 채택하면 contracts.md 갱신 + 반대편 에이전트 재호출, 기각하면 이유를 기록하고 원래 계약대로 수정 지시.

### Phase 3: 병렬 검증

한 메시지에서 test-engineer와 tts-qa-inspector를 동시에 호출한다(`run_in_background: true`). 프롬프트에 `_workspace/02_*_summary.md` 경로를 포함한다.

점진적 QA: 큰 작업에서 Phase 2를 여러 단계로 나눴다면(예: models→text→cache→service→cli), 각 단계 끝마다 tts-qa-inspector를 해당 범위로 호출한다. 결함이 쌓이기 전에 잡는 편이 수정 비용이 훨씬 적다.

### Phase 4: 수정 루프 (최대 2회)

1. 두 보고서를 읽고 결함을 병합한다(같은 원인은 하나로, 출처 둘 다 표기). 결과를 `_workspace/04_fix_round{N}.md`에 담당자별로 정리한다.
2. 판정이 모두 PASS이고 실패 테스트가 없으면 Phase 5로.
3. 아니면 담당 에이전트(core/engine/test)를 해당 항목만 수정하도록 재호출 → Phase 3 재실행.
4. 2회 후에도 남은 결함은 고치지 말고 최종 보고에 남긴다 — 무한 루프보다 사용자의 판단이 낫다.

### Phase 5: 보고

1. 사용자에게 요약: 구현된 기능, 테스트 결과(통과/실패/건너뜀 수), 남은 결함, 실행 방법(`pip install -e ".[dev]"`, `tts say ...`), 필요한 외부 도구(ffmpeg).
2. `_workspace/`는 보존한다(사후 추적용).
3. 피드백을 묻는다: "결과에서 개선할 점이나 워크플로우에서 바꾸고 싶은 점이 있나요?" 피드백은 `harness:evolve`로 반영할 수 있다.

## 데이터 흐름

```
[리더] Phase1: request.md, contracts.md, models.py/errors.py
   │
   ├─► core-developer ──► src/tts/**  + 02_core-developer_summary.md ─┐
   └─► engine-developer ► engines/** + 02_engine-developer_summary.md ┤
                                                                       ▼
   ┌─◄ test-engineer ◄──── (summary + 코드) ────► tts-qa-inspector ─┐
   ▼                                                                  ▼
03_test-engineer_report.md                     03_tts-qa-inspector_report.md
   └──────────────► [리더] 04_fix_round{N}.md ──► 담당자 재호출 (≤2회)
```

## 에러 핸들링

| 상황 | 전략 |
|---|---|
| 에이전트 1개 실패/빈 결과 | 1회 재호출. 재실패 시 그 범위 없이 진행하고 보고에 누락 명시 |
| pip 설치 불가(오프라인·권한) | 코드 작성은 계속, 실행 검증은 "미확인"으로 표기하고 사용자에게 설치 명령 안내 |
| ffmpeg 없음 | mp3 관련 테스트 skip, 보고에 설치 안내(`winget install ffmpeg`) |
| 네트워크 불가로 edge-tts 실호출 실패 | 네트워크 테스트만 미확인 처리, 나머지 진행 |
| 개발자 간 계약 해석 충돌 | contracts.md를 기준으로 리더가 판정, 필요하면 계약을 명확히 고친 뒤 양쪽 재호출 |
| 수정 루프 2회 초과 | 중단하고 남은 결함을 사용자에게 보고 |

## 테스트 시나리오

### 정상 흐름
1. 사용자: "설계대로 TTS 구현해줘"
2. Phase 0: `_workspace/` 없음 → 초기 실행
3. Phase 1: request.md 작성, models.py/errors.py 생성
4. Phase 2: core-developer와 engine-developer 병렬 → summary 2개
5. Phase 3: test-engineer(예: 40개 통과, ffmpeg 없어 2개 skip), QA(FIX_REQUIRED: 캐시 키에 volume 누락)
6. Phase 4: core-developer 수정 → Phase 3 재실행 → 모두 PASS
7. Phase 5: `tts say "안녕하세요" -o hello.mp3` 사용법과 함께 보고

### 에러 흐름
1. 사용자: "엔진 부분만 다시 해줘, 속도 옵션이 안 먹어"
2. Phase 0: `_workspace/` 있음 + 부분 요청 → engine-developer만 호출(이전 QA 보고서 경로 포함)
3. engine-developer가 `_to_engine_params`에서 부호 누락(`"10%"`) 수정
4. Phase 3에서 test-engineer가 백그라운드 오류로 빈 결과 반환 → 1회 재호출 → 성공
5. QA PASS → 보고에 "test-engineer 1회 재시도" 명시
