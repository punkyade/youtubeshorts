# 모듈 간 계약 (상세)

이 파일이 바뀌면 오케스트레이터는 CLAUDE.md 변경 이력에 기록하고, 영향받는 모듈 담당 에이전트를 재호출한다.

## models.py

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Voice:
    id: str                 # 엔진 고유 ID, 예: "ko-KR-SunHiNeural"
    language: str           # BCP-47, 예: "ko-KR"
    gender: str | None = None
    engine: str = ""

@dataclass(frozen=True)
class SynthesisOptions:
    voice: str
    rate: float = 1.0       # 배수. 0.5~2.0 허용
    pitch: int = 0          # Hz 오프셋. -50~+50 허용
    volume: float = 1.0     # 배수. 0.0~2.0 허용
    format: str = "mp3"     # 최종 출력 포맷: "mp3" | "wav"
    # 범위를 벗어나면 __post_init__에서 ValueError

@dataclass(frozen=True)
class AudioChunk:
    data: bytes
    format: str             # 실제 인코딩: "mp3" | "wav" | "pcm_s16le"
    sample_rate: int | None = None   # pcm일 때 필수
```

## engines/base.py

```python
class TTSEngine(ABC):
    name: ClassVar[str]          # 레지스트리 키, 예: "edge"
    max_chars: ClassVar[int]     # 요청 1회 최대 글자 수 (chunker가 사용)
    supports_ssml: ClassVar[bool] = False

    @abstractmethod
    async def synthesize(self, text: str, opts: SynthesisOptions) -> AudioChunk: ...

    @abstractmethod
    async def list_voices(self, language: str | None = None) -> list[Voice]: ...

    async def aclose(self) -> None:   # 세션 정리가 필요한 엔진만 오버라이드
        return None
```

- 동기 SDK(pyttsx3 등)는 `asyncio.to_thread`로 감싼다. 이벤트 루프를 막으면 병렬 합성이 직렬이 된다.
- 빈 문자열이나 공백만 있는 text는 엔진에 오지 않는다 (chunker가 걸러냄). 그래도 오면 `ValueError`.

## engines/registry.py

```python
def register(name: str) -> Callable[[type[TTSEngine]], type[TTSEngine]]
def get_engine(name: str, settings: Settings) -> TTSEngine   # 없으면 ConfigError
def available_engines() -> list[str]
```

엔진 모듈은 `engines/__init__.py`에서 import 시도하되, 선택 의존성 ImportError는 삼키고 해당 엔진만 미등록으로 둔다.

## errors.py

```
TTSError
├── ConfigError          # 설정/키/ffmpeg 누락, 알 수 없는 엔진
├── TextTooLongError     # chunker가 max_chars 안으로 못 자름 (공백 없는 초장문)
└── EngineError          # 엔진 호출 실패 (engine 이름, 원인 예외 보존)
    ├── AuthError        # 401/403 — 재시도 금지
    └── RetryableError   # 네트워크, 타임아웃, 5xx
        └── RateLimitError  # 429. retry_after: float | None
```

## text/

```python
class Normalizer:
    def __init__(self, rules: Sequence[str] = ()) -> None   # 빈 튜플 = 공백 정리만
    def normalize(self, text: str) -> str

class Chunker:
    def split(self, text: str, max_chars: int) -> list[str]
    # 보장: 모든 청크 1 <= len <= max_chars, 공백만인 청크 없음,
    #       "".join 시 원문 의미 보존(공백 차이 외 문자 손실 없음)
```

## cache.py

```python
CACHE_VERSION = 1

class AudioCache:
    def __init__(self, root: Path, enabled: bool = True) -> None
    def key(self, engine: str, text: str, opts: SynthesisOptions) -> str   # sha256 hex
    def get(self, key: str) -> AudioChunk | None
    def put(self, key: str, chunk: AudioChunk) -> None
```

- 키 입력: `json.dumps({"v": CACHE_VERSION, "engine", "voice", "rate", "pitch", "volume", "text"}, sort_keys=True, ensure_ascii=False)`. `opts.format`은 제외.
- 저장: `root/<key[:2]>/<key>.<chunk.format>` + 포맷 메타. 쓰기는 임시 파일 → `os.replace`로 원자적으로 (병렬 합성 중 반쯤 쓴 파일을 읽지 않도록).

## audio/processor.py

```python
class AudioProcessor:
    def concat(self, chunks: Sequence[AudioChunk], gap_ms: int = 150) -> AudioSegment
    def export(self, audio: AudioSegment, fmt: str) -> bytes
    def to_file(self, audio: AudioSegment, path: Path) -> Path   # 확장자로 포맷 결정
```

- 디코딩은 반드시 `chunk.format`을 기준으로 한다 (`opts.format` 아님).
- ffmpeg가 없으면 `ConfigError("ffmpeg가 필요합니다: ...설치 안내...")`.

## service.py

```python
class TTSService:
    def __init__(self, engine, normalizer, chunker, cache, audio, concurrency: int = 4, retries: int = 3)
    async def synthesize(self, text: str, opts: SynthesisOptions) -> bytes     # opts.format으로 인코딩
    async def synthesize_to_file(self, text: str, path: Path, opts: SynthesisOptions) -> Path
    @classmethod
    def from_settings(cls, settings: Settings, engine_name: str | None = None) -> "TTSService"
```

- 재시도: `RetryableError`에만 지수 백오프(0.5s, 1s, 2s). `RateLimitError.retry_after`가 있으면 그 값을 우선.
- 빈 입력(정규화 후 공백만) → `ValueError("변환할 텍스트가 없습니다")`.

## cli.py

| 명령 | 인자/옵션 | 매핑 |
|---|---|---|
| `tts say TEXT` | `--out/-o`, `--play`, 공통 옵션 | `synthesize_to_file` 또는 재생 |
| `tts file PATH` | `--out/-o` (기본: 입력명.mp3), 공통 옵션 | 파일을 utf-8로 읽어 `synthesize_to_file` |
| `tts voices` | `--lang`, `--engine` | `engine.list_voices` |

공통 옵션: `--engine`, `--voice`, `--rate`, `--pitch`, `--volume`, `--format`, `--no-cache`. CLI 옵션 이름은 SynthesisOptions 필드명과 일치시킨다.

종료 코드: 0 성공, 1 `TTSError`(메시지만 출력, 트레이스백 없음), 2 사용법 오류(typer 기본).

## config.yaml 키

```yaml
engine: edge
voice: ko-KR-SunHiNeural
rate: 1.0
pitch: 0
volume: 1.0
format: mp3
concurrency: 4
cache:
  enabled: true
  dir: ~/.cache/tts
chunk_gap_ms: 150
normalizer_rules: []
```

Settings 필드명은 위 키와 1:1로 대응한다 (중첩은 `cache_enabled`가 아니라 `cache.enabled` 모델로).
