# 추가 엔진 (선택 의존성)

기본 구현 범위는 edge-tts뿐이다. 아래 엔진은 사용자가 요청할 때 추가한다. 각 SDK의 최신 API는 구현 시점에 공식 문서로 확인한다 — 아래는 설계 방향과 함정만 정리한 것이다.

## OpenAI TTS (`[openai]`)

- 키: `OPENAI_API_KEY` 환경변수. 없으면 생성자에서 `ConfigError`.
- 출력 포맷을 요청할 수 있다(`response_format`: mp3, wav, opus 등). 서비스의 최종 포맷과 맞춰 요청하면 변환을 줄일 수 있지만, 캐시 키에 format이 빠져 있으므로 **항상 mp3로 고정 요청**하고 변환은 AudioProcessor에 맡긴다.
- `rate` → `speed`(배수, 대략 0.25~4.0) 그대로 사용. `pitch`, `volume` 미지원 → 경고 후 무시.
- voice는 고정 목록(alloy 등). `list_voices`는 상수 목록을 `language=None`으로 반환하고, 언어 필터가 주어지면 전체를 반환한다(다국어 voice).
- `max_chars`: 입력 한도(문서 확인) 이하로, 보수적으로 4000.
- 오류: SDK의 `AuthenticationError`→`AuthError`, `RateLimitError`→`RateLimitError`, `APIConnectionError`/`APITimeoutError`/`InternalServerError`→`RetryableError`.

## Google Cloud TTS (`[google]`)

- 인증: `GOOGLE_APPLICATION_CREDENTIALS` 서비스 계정 파일.
- `audio_encoding=MP3`, `speaking_rate`(배수), `pitch`(반음 단위 — Hz가 아니다. 근사 변환하거나 경고), `volume_gain_db`(배수→dB: `20*log10(v)`, v=0이면 최소값으로 clamp).
- 입력 한도는 바이트 기준이라 한국어(UTF-8 3바이트)는 글자 수가 훨씬 적다. `max_chars`는 바이트 한도 / 3 이하로 잡는다.
- SSML 지원 → `supports_ssml = True`.
- 동기 클라이언트를 쓴다면 `asyncio.to_thread`.

## pyttsx3 오프라인 (`[offline]`)

- Windows SAPI5 음성을 쓴다. 한국어 음성은 Windows에 한국어 음성 팩이 설치되어 있어야 한다 — `list_voices`에서 없으면 안내 메시지.
- 메모리 출력이 없어서 `save_to_file(text, tmp.wav)` → `runAndWait()` → 파일 읽기 → 삭제. 출력은 `format="wav"`.
- `runAndWait()`는 동기이며 **스레드 안전하지 않다**. `asyncio.to_thread`로 감싸되 엔진 내부 `threading.Lock`으로 직렬화한다 (서비스 concurrency와 무관하게).
- `rate`: 기본 WPM(약 200) × 배수. `volume`: 0.0~1.0으로 clamp. `pitch` 미지원.
- `max_chars`: 제한은 사실상 없지만 진행 표시와 캐시 효율을 위해 1000.
