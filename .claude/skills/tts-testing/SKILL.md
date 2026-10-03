---
name: tts-testing
description: "TTS 프로젝트의 pytest 테스트 작성·실행 가이드 — FakeEngine으로 네트워크 없이 파이프라인 검증, chunker 경계 사례, 캐시·재시도·순서 보존 테스트, 생성된 오디오 파일 검증 스크립트. tests/ 아래 코드를 작성·수정할 때, '테스트 작성', '테스트 돌려줘', '커버리지', '테스트 실패 고쳐줘', '실제로 소리 나는지 확인' 같은 요청에 반드시 사용할 것. 모듈 간 계약 불일치 점검은 tts-qa-checklist가 담당한다."
---

# TTS 테스트

TTS의 실제 출력(소리)은 자동으로 '맞다'고 판정하기 어렵다. 그래서 테스트는 두 층으로 나눈다.

1. **결정적 단위·통합 테스트 (기본)** — 네트워크 없이 항상 돌아간다. FakeEngine으로 파이프라인의 배선을 검증한다.
2. **네트워크 스모크 테스트 (`@pytest.mark.network`)** — 실제 엔진으로 짧은 문장을 합성하고, 결과 파일이 '재생 가능한 오디오인지'만 확인한다. 기본 실행에서는 제외한다.

## 실행

```
pip install -e ".[dev]"
pytest                       # network 제외 (pyproject의 addopts: -m "not network")
pytest -m network            # 실제 edge-tts 호출
python .claude/skills/tts-testing/scripts/verify_audio.py out.mp3 --min-sec 0.5
```

## FakeEngine (tests/conftest.py)

실제 엔진처럼 계약을 지키되 결정적이어야 한다.

```python
class FakeEngine(TTSEngine):
    name = "fake"
    max_chars = 50          # 작게 잡아 분할 경로를 항상 타게 한다

    def __init__(self, fail_times: int = 0, error: type[Exception] = RetryableError, delay: float = 0.0):
        self.calls: list[str] = []
        ...

    async def synthesize(self, text, opts):
        self.calls.append(text)
        # 실패 주입 → delay(역순 완료 유도 가능) → 글자 수 × 10ms 무음 wav 반환
        return AudioChunk(data=_silent_wav(len(text) * 10), format="wav")
```

`_silent_wav`는 표준 라이브러리 `wave`로 만든다 — ffmpeg 없이도 핵심 테스트가 돌도록. 단, mp3 경로를 검증하는 테스트는 `pytest.importorskip`과 `shutil.which("ffmpeg")` 체크로 건너뛸 수 있게 한다.

## 반드시 있어야 할 테스트

| 영역 | 테스트 |
|---|---|
| chunker | `korean-text-processing` 스킬의 "테스트해야 할 경계 사례" 전체 + 속성 기반 검사 |
| normalizer | 각 규칙 단독, 적용 순서(URL 안의 `&`가 `symbols`에 먹히지 않음) |
| cache | 같은 입력 = 같은 키, rate/pitch/volume/voice/engine/text 중 하나만 바꿔도 키가 다름, **format만 바꾸면 키가 같음**, 원자적 쓰기, `enabled=False`면 저장 안 함 |
| service | 청크 순서 보존(FakeEngine `delay`를 역순으로 줘서 늦게 끝난 청크가 앞에 있어도 순서 유지), 캐시 적중 시 엔진 미호출, `RetryableError` n회 후 성공, `AuthError`는 재시도 0회, 빈 입력 `ValueError`, 출력 길이 ≈ 청크 오디오 합 + gap |
| engines/edge | `_to_engine_params` 경계값(rate 0.5/1.0/2.0 → `-50%`/`+0%`/`+100%`, pitch 0/-10 → `+0Hz`/`-10Hz`), 예외 매핑(SDK 예외를 가짜로 던져 errors.py 타입 확인) |
| cli | `typer.testing.CliRunner`로 say/file/voices, `TTSError` 시 종료 코드 1이고 트레이스백 없음, 한글 경로·한글 텍스트 파일 |
| registry | 알 수 없는 엔진 → `ConfigError`, 선택 의존성 없을 때 `import tts` 성공 |

## 작성 원칙

- **비동기**: `pytest-asyncio`의 `asyncio_mode = "auto"`. 재시도 백오프는 `asyncio.sleep`을 monkeypatch해서 테스트가 느려지지 않게 한다.
- **격리**: 캐시는 항상 `tmp_path`. 사용자 홈 캐시를 건드리지 않는다.
- **결과로 검증**: "함수가 호출됐다"보다 "출력 오디오 길이가 기대값이다", "엔진 호출 횟수가 n이다"처럼 관찰 가능한 결과를 단언한다.
- 실패한 테스트를 통과시키려고 단언을 약하게 바꾸지 않는다. 구현 버그로 보이면 담당 개발자(core-developer/engine-developer)에게 넘길 보고에 적는다.

## 보고 형식

`_workspace/03_test-engineer_report.md`:
```
## 결과: 통과 N / 실패 M / 건너뜀 K
## 실패 목록
- tests/test_x.py::test_y — 원인 추정, 담당: core-developer | engine-developer, 재현 명령
## 추가한 테스트
## 건너뛴 이유 (ffmpeg 없음 등)
```
