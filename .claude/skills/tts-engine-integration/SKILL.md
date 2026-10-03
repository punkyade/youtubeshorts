---
name: tts-engine-integration
description: "TTS 엔진 백엔드(edge-tts, OpenAI TTS, Google Cloud TTS, pyttsx3 오프라인 등)를 TTSEngine 인터페이스에 맞춰 구현·추가·수정하는 방법 — 옵션 단위 변환, 오류 매핑, 출력 포맷 보고, 레지스트리 등록. engines/ 아래 코드를 다룰 때, '새 엔진 추가', 'OpenAI로도 되게', '목소리 목록', '속도/음높이가 안 먹어', '429 에러', 'API 키 오류' 같은 요청에 반드시 사용할 것. 문장 분리나 오디오 병합 문제는 다른 스킬 영역이다."
---

# TTS 엔진 통합

엔진마다 SDK 모양, 옵션 단위, 출력 포맷, 오류 형태가 전부 다르다. 이 스킬의 목적은 그 차이를 **엔진 모듈 안에 가두는 것**이다. 서비스·캐시·오디오 모듈은 어떤 엔진이 쓰이는지 몰라야 한다.

인터페이스 정의는 `tts-architecture/references/contracts.md`의 `engines/base.py`, `errors.py` 절을 따른다.

## 엔진 구현 절차

1. 해당 엔진의 레퍼런스를 읽는다 — `references/edge.md`(기본), 그 외 엔진은 `references/other-engines.md`.
2. `engines/<name>.py`에 `@register("<name>")` 클래스를 만든다. `name`, `max_chars`를 클래스 변수로 선언한다.
3. **옵션 변환 함수를 분리한다.** `_to_engine_params(opts) -> dict`처럼 순수 함수로 두면 네트워크 없이 단위 테스트할 수 있다.
4. **오류 매핑을 한 곳에서.** SDK 예외를 잡아 `AuthError` / `RateLimitError` / `RetryableError` / `EngineError`로 변환하는 `_map_error(exc)`를 둔다. 원인 예외는 `raise ... from exc`로 보존한다.
5. **출력 포맷을 정직하게 보고한다.** `AudioChunk.format`에 엔진이 실제로 준 인코딩을 쓴다. 사용자가 요청한 `opts.format`을 그대로 복사하면 AudioProcessor가 mp3를 wav로 디코딩하려다 깨진다.
6. 선택 의존성 SDK는 메서드 안이나 모듈 상단 `try` 블록에서 지연 import한다.
7. `list_voices(language)`는 `Voice(engine=self.name, ...)`로 정규화해서 반환한다.

## 옵션 단위 변환 원칙

SynthesisOptions는 엔진 중립 단위(rate 배수, pitch Hz 오프셋, volume 배수)를 쓴다. 엔진이 해당 옵션을 지원하지 않으면:
- 기본값(1.0 / 0 / 1.0)이면 조용히 무시
- 기본값이 아니면 `logging.warning`으로 한 번 알리고 무시 — 사용자는 속도를 바꿨는데 왜 안 바뀌는지 알아야 한다
- 엔진 허용 범위를 넘으면 범위 안으로 자르고(clamp) 경고

## 오류 매핑 기준

| 원인 | 매핑 |
|---|---|
| HTTP 401/403, 키 누락·무효 | `AuthError` (키가 없으면 생성자에서 `ConfigError`) |
| HTTP 429 | `RateLimitError(retry_after=헤더값)` |
| HTTP 5xx, 연결 실패, 타임아웃 | `RetryableError` |
| 알 수 없는 voice ID | `EngineError` — 메시지에 `tts voices` 명령 안내 |
| 응답은 왔는데 오디오가 0바이트 | `RetryableError` (edge-tts에서 간헐적으로 발생) |

## 엔진 체크리스트 (완료 보고 전)

- [ ] `name`, `max_chars` 선언, `@register` 등록, `engines/__init__.py`에서 import
- [ ] `_to_engine_params` 단위 변환이 경계값(rate 0.5/2.0, pitch ±50)에서 올바른 문자열·숫자를 만든다
- [ ] `AudioChunk.format`이 실제 인코딩과 일치
- [ ] SDK 예외가 errors.py 계층으로만 밖에 나간다
- [ ] 선택 의존성 없이 `import tts`가 성공한다
- [ ] 동기 SDK는 `asyncio.to_thread` 사용
