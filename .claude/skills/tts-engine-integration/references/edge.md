# edge-tts (기본 엔진)

무료이고 API 키가 필요 없다. Microsoft Edge 읽어주기 서비스를 사용하는 비공식 라이브러리라서 간헐적 실패와 프로토콜 변경 가능성이 있으므로 재시도와 오류 매핑이 특히 중요하다.

## 설치·import

```
pip install edge-tts
```
```python
import edge_tts
```

## 합성

```python
communicate = edge_tts.Communicate(text, voice, rate="+10%", volume="+0%", pitch="+0Hz")
buf = bytearray()
async for chunk in communicate.stream():
    if chunk["type"] == "audio":
        buf.extend(chunk["data"])
# 결과: mp3 (24kHz, 48kbps mono). AudioChunk(data=bytes(buf), format="mp3")
```

`communicate.save(path)`도 있지만 파일을 거치지 말고 `stream()`으로 메모리에 받는다 — 캐시와 병합이 bytes를 기준으로 동작한다.

## 옵션 변환

edge의 rate·volume·pitch는 **부호가 반드시 붙은 문자열**이다. `"10%"`처럼 부호가 없으면 거부된다.

| SynthesisOptions | edge 파라미터 | 변환 | 예 |
|---|---|---|---|
| `rate=1.0` | `rate` | `f"{round((r-1)*100):+d}%"` | 1.0→`"+0%"`, 1.25→`"+25%"`, 0.5→`"-50%"` |
| `volume=1.0` | `volume` | 같은 식 | 0.8→`"-20%"` |
| `pitch=0` | `pitch` | `f"{p:+d}Hz"` | 0→`"+0Hz"`, -10→`"-10Hz"` |

`round()`가 `-0`을 만들지 않는지 확인한다 (`f"{0:+d}"`는 `"+0"`).

## 목소리

```python
voices = await edge_tts.list_voices()   # list[dict]: ShortName, Locale, Gender, ...
```
한국어 대표 목소리: `ko-KR-SunHiNeural`(여), `ko-KR-InJoonNeural`(남), `ko-KR-HyunsuMultilingualNeural`(남, 다국어). 목록은 서버에서 바뀔 수 있으므로 하드코딩하지 말고 `list_voices`로 조회한다. 같은 실행 안에서는 결과를 인스턴스에 캐시한다.

## 제한·오류

- `max_chars`: 실제 한계는 더 크지만 긴 요청일수록 실패율이 올라가므로 **3000**으로 둔다.
- 예외: `edge_tts.exceptions.NoAudioReceived` → `RetryableError`, `aiohttp.ClientError`/`asyncio.TimeoutError` → `RetryableError`, `aiohttp.WSServerHandshakeError` status 403 → `RetryableError` (인증 키가 없는 서비스라 403은 일시적 차단인 경우가 많다; 3회 실패 후에는 라이브러리 업데이트를 안내하는 메시지와 함께 `EngineError`)
- 알 수 없는 voice는 `ValueError`나 `NoAudioReceived`로 나타날 수 있다. 합성 전에 voice 형식(`xx-XX-NameNeural`)을 가볍게 검사하면 메시지가 친절해진다.
- 동시 요청이 너무 많으면 차단될 수 있으므로 `concurrency` 기본값 4를 넘기지 않도록 권장한다.
