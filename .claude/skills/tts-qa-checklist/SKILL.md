---
name: tts-qa-checklist
description: "TTS 프로젝트 모듈 간 경계면 정합성 검증 체크리스트 — 엔진↔서비스, 옵션 단위 변환, AudioChunk 포맷↔디코딩, 캐시 키 완전성, CLI 옵션↔SynthesisOptions↔config.yaml, 오류 계층↔재시도 정책을 양쪽 코드를 함께 읽어 교차 비교한다. 모듈 구현 직후 검증, 'QA 해줘', '정합성 점검', '모듈끼리 잘 맞물리는지 봐줘', '머지 전에 검토' 요청 시 반드시 사용할 것. 개별 함수 단위 테스트 작성은 tts-testing이 담당한다."
---

# TTS 경계면 QA 체크리스트

각 모듈은 혼자서는 맞게 보이지만 연결 지점에서 어긋나는 경우가 많다. 이 체크리스트는 "X가 있는가?"가 아니라 **"X가 내보내는 모양과 Y가 기대하는 모양이 같은가?"**를 확인한다. 모든 항목은 양쪽 파일을 동시에 열고 대조한다.

기준 문서: `tts-architecture/references/contracts.md`. 코드가 계약과 다르면 코드 쪽 결함으로 보고하되, 계약 자체가 비현실적이면(예: SDK가 그 기능을 지원하지 않음) "계약 변경 제안"으로 따로 분류한다.

## 1. 엔진 ↔ 서비스·오디오

| 확인 | 방법 |
|---|---|
| 모든 엔진의 `synthesize`가 `AudioChunk`를 반환하고 `bytes`를 반환하지 않는다 | `engines/*.py`의 return 문 전수 확인 |
| `AudioChunk.format`이 엔진의 실제 출력과 같다 | edge는 `"mp3"` 고정이어야 함. `opts.format`을 복사하는 코드가 있으면 결함 |
| AudioProcessor가 `chunk.format`으로 디코딩한다 | `processor.py`에서 `from_file`/`from_mp3`/`from_wav` 호출부의 format 인자 출처 추적 |
| `max_chars`를 chunker가 실제로 받는다 | `service.py`에서 `chunker.split(..., max_chars=self.engine.max_chars)` 확인 (상수 하드코딩이면 결함) |
| 동기 SDK 호출이 이벤트 루프를 막지 않는다 | `async def` 안의 블로킹 호출(`requests`, `runAndWait`, `time.sleep`) grep |

## 2. 옵션 단위 변환

| 확인 | 방법 |
|---|---|
| CLI 옵션 → SynthesisOptions 필드명·타입·기본값 일치 | `cli.py` 옵션 선언과 `models.py` 대조. 예: CLI `--rate`가 `"+10%"` 문자열을 받으면 결함 |
| config.yaml 키 ↔ Settings 필드 ↔ CLI 기본값 연결 | Settings 기본값과 config.yaml 예시 값이 다르면 어느 쪽이 우선인지 코드로 확인 |
| 엔진 변환 함수가 중립 단위를 엔진 단위로 바꾼다 | edge: 1.0 → `"+0%"`(부호 필수), pitch → `"Hz"` 접미사. 실제로 `python -c`로 경계값 호출해 출력 확인 |
| SynthesisOptions 범위 검증과 엔진 clamp가 충돌하지 않는다 | 모델이 허용하는 범위 안의 값을 엔진이 거부하지 않는지 |

## 3. 캐시

| 확인 | 방법 |
|---|---|
| 키에 engine, voice, rate, pitch, volume, text, CACHE_VERSION이 모두 들어간다 | `cache.key` 구현을 SynthesisOptions 필드 목록과 1:1 대조. **새 필드가 모델에 추가됐는데 키에 없으면 결함** (다른 설정의 오디오가 재사용됨) |
| `opts.format`은 키에 없다 | 있으면 같은 청크를 포맷마다 중복 합성 |
| 저장 파일 확장자·메타가 `chunk.format`을 보존해서 `get`이 같은 format의 AudioChunk를 돌려준다 | `put` → `get` 왕복 코드 경로 |
| 정규화 규칙이 바뀌면 다른 텍스트가 되어 자연히 키가 바뀐다 | 서비스가 정규화 **후** 텍스트로 키를 만드는지 |
| 쓰기가 원자적이다 | 임시 파일 + `os.replace` |

## 4. 오류·재시도

| 확인 | 방법 |
|---|---|
| 엔진 밖으로 나가는 예외가 errors.py 계층뿐이다 | 각 엔진의 `except` 블록과 `_map_error`. SDK 예외가 그대로 새는 경로 탐색 |
| 서비스 재시도가 `RetryableError`만 잡는다 | `except Exception`/`except EngineError`로 넓게 잡아 `AuthError`까지 재시도하면 결함 |
| `RateLimitError.retry_after`가 실제로 쓰인다 | 서비스 백오프 코드 |
| CLI가 `TTSError`를 잡아 종료 코드 1 + 메시지, 그 외 예외는 그대로 | `cli.py` |

## 5. 순서·동시성

- `asyncio.gather` 결과(입력 순서 보존) 또는 인덱스 정렬을 쓰는지. `as_completed` 결과를 그대로 이어 붙이면 결함.
- 세마포어가 엔진 호출만 감싸고 캐시 조회는 감싸지 않는지(캐시 적중이 동시성 슬롯을 낭비하지 않도록).
- 엔진 `aclose()`가 서비스 종료 시 호출되는지.

## 6. 패키징·환경

- `pyproject.toml`의 콘솔 스크립트(`tts = "tts.cli:app"`)가 실제 객체를 가리키는지
- 선택 의존성 없이 `python -c "import tts; import tts.cli"` 성공
- 파일 읽기·쓰기에 `encoding="utf-8"`, 한글 경로 처리
- ffmpeg 부재 시 `ConfigError` 메시지

## 실행 가능한 확인

정적 대조만으로 끝내지 말고 가능한 것은 실행한다.
```
python -c "import tts, tts.cli"
pytest -q
python -m tts.cli say "안녕하세요. 테스트입니다." -o _workspace/qa_smoke.mp3   # 네트워크 가능 시
python .claude/skills/tts-testing/scripts/verify_audio.py _workspace/qa_smoke.mp3
```

## 보고 형식

`_workspace/03_tts-qa-inspector_report.md`:
```
## 판정: PASS | FIX_REQUIRED
## 결함 (심각도순)
- [높음] 파일:줄 — 무엇과 무엇이 어긋나는지 (양쪽 근거 인용), 재현, 담당 에이전트, 수정 제안
## 계약 변경 제안
## 확인했으나 문제 없음 (항목 번호만)
```
심각도: 높음 = 잘못된 오디오·크래시·잘못된 캐시 재사용, 중간 = 오류 메시지/재시도 정책 이탈, 낮음 = 일관성·스타일.
