---
name: tts-architecture
description: "TTS(텍스트 음성 변환) 프로젝트의 설계 계약 — 디렉터리 구조, 모듈 간 인터페이스(TTSEngine, SynthesisOptions, AudioChunk), 오류 타입, 캐시 키, 설정 우선순위, 코딩 규칙. tts 프로젝트의 코드를 작성·수정·리뷰하기 전, 모듈 경계를 바꾸거나 새 모듈을 추가할 때, '구조가 어떻게 돼', '인터페이스 바꿔줘', '설계 수정' 같은 요청이 오면 반드시 이 스킬을 먼저 읽을 것. 엔진 백엔드 구현 세부는 tts-engine-integration, 한국어 문장 분리 규칙은 korean-text-processing이 담당한다."
---

# TTS 설계 계약

이 프로젝트의 모든 에이전트(core-developer, engine-developer, test-engineer, tts-qa-inspector)가 공유하는 **단일 진실 원천**이다. 모듈은 병렬로 구현되므로, 경계면의 모양이 여기서 고정되어 있어야 각자 만든 코드가 합쳐졌을 때 맞물린다.

계약을 바꿔야 할 때는 코드를 먼저 고치지 말고 `references/contracts.md`를 먼저 고친 뒤, 그 변경이 닿는 모든 모듈을 같이 수정한다. 한쪽만 바뀐 계약이 이 프로젝트에서 가장 흔한 버그 원인이 된다.

## 기술 스택

- Python 3.11+, `src/` 레이아웃, `pyproject.toml` (setuptools 또는 hatchling)
- CLI: `typer` / 설정: `pydantic-settings` + `config.yaml` / 오디오: `pydub` (ffmpeg 필요)
- 기본 엔진: `edge-tts` (비동기, mp3 출력). 다른 엔진은 선택 의존성(`[openai]`, `[google]`, `[offline]`)
- 테스트: `pytest`, `pytest-asyncio`. 네트워크가 필요한 테스트는 `@pytest.mark.network`로 분리
- 실행 환경: Windows가 1차 대상. 파일 입출력은 항상 `encoding="utf-8"`, 경로는 `pathlib.Path`

## 디렉터리 구조

```
src/tts/
├── cli.py            # typer 앱. 얇게 유지 — 로직은 service에
├── service.py        # TTSService: 전처리 → 캐시 → 합성 → 후처리 조립
├── config.py         # Settings (pydantic-settings)
├── errors.py         # 오류 계층 (아래 참조)
├── models.py         # SynthesisOptions, AudioChunk, Voice (dataclass)
├── text/normalizer.py, text/chunker.py
├── engines/base.py, engines/registry.py, engines/edge.py, ...
├── audio/processor.py
└── cache.py
tests/
├── conftest.py       # FakeEngine, tmp 캐시 fixture
└── test_*.py
```

담당 범위: `engines/`는 engine-developer, 나머지 `src/tts/`는 core-developer, `tests/`는 test-engineer. `models.py`와 `errors.py`는 **공유 계약 파일**이라 core-developer가 만들고, 변경이 필요하면 오케스트레이터를 거친다.

## 핵심 계약 (요약)

상세 시그니처와 필드는 `references/contracts.md`에 있다. 코드를 쓰기 전에 반드시 읽는다.

1. **엔진은 자기가 실제로 만든 포맷을 알려준다.** `synthesize()`는 `bytes`가 아니라 `AudioChunk(data, format, sample_rate)`를 반환한다. edge-tts는 사용자가 wav를 원해도 mp3를 준다. 변환은 AudioProcessor 몫이다.
2. **SynthesisOptions는 엔진 중립 단위를 쓴다.** `rate`는 배수(1.0 = 기본), `pitch`는 Hz 오프셋, `volume`은 배수. 각 엔진이 자기 형식(예: edge의 `"+10%"`)으로 바꾼다.
3. **캐시 키는 합성 결과에 영향을 주는 모든 값을 포함한다.** engine, voice, rate, pitch, volume, 청크 텍스트, `CACHE_VERSION`. 출력 포맷(`opts.format`)은 포함하지 않는다 — 캐시에는 엔진 원본 포맷이 저장되기 때문이다.
4. **재시도는 `RetryableError`만.** `AuthError`, `ConfigError`, `TextTooLongError`는 즉시 실패.
5. **서비스는 순서를 보존한다.** 청크를 병렬로 합성해도 결과는 원문 순서대로 이어 붙인다.

## 설정 우선순위

`config.yaml` < 환경변수(`TTS_` 접두사, API 키는 `OPENAI_API_KEY` 등 표준 이름) < CLI 옵션. API 키는 설정 파일에 저장하지 않는다.

## 코딩 규칙

- 공개 함수에는 타입 힌트. `Any`로 계약을 우회하지 않는다 — 경계면 버그를 정적으로 못 잡게 된다.
- 엔진 SDK import는 해당 엔진 모듈 안에서만, 지연 import로. 선택 의존성이 없을 때 다른 엔진까지 import 실패하면 안 된다.
- 외부 도구(ffmpeg) 부재는 실행 시점에 `ConfigError`로 알기 쉽게 알린다.
- 주석은 '왜'를 설명할 때만.
