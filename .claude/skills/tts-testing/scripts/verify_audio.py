"""생성된 오디오 파일이 재생 가능한지 확인한다.

사용법: python verify_audio.py FILE [--min-sec 0.5] [--max-silence-ratio 0.9]
종료 코드: 0 정상, 1 검증 실패, 2 도구 없음/사용법 오류
wav는 표준 라이브러리로, 그 외 포맷은 pydub(+ffmpeg)로 검사한다.
"""
from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path


def _wav_stats(path: Path) -> dict:
    with wave.open(str(path), "rb") as w:
        frames = w.readframes(w.getnframes())
        width = w.getsampwidth()
        rate = w.getframerate()
        duration = w.getnframes() / rate if rate else 0.0
    return {"duration": duration, "silence_ratio": _silence_ratio(frames, width), "sample_rate": rate}


def _silence_ratio(frames: bytes, width: int, threshold: int = 200) -> float:
    if width != 2 or not frames:
        return 0.0
    import array

    samples = array.array("h", frames[: len(frames) // 2 * 2])
    quiet = sum(1 for s in samples if abs(s) < threshold)
    return quiet / len(samples)


def _pydub_stats(path: Path) -> dict:
    try:
        from pydub import AudioSegment
    except ImportError:
        print("pydub가 설치되어 있지 않습니다: pip install pydub", file=sys.stderr)
        sys.exit(2)
    import shutil

    if not shutil.which("ffmpeg"):
        print("ffmpeg가 PATH에 없습니다 (mp3 검사에 필요)", file=sys.stderr)
        sys.exit(2)
    seg = AudioSegment.from_file(path)
    raw = seg.set_sample_width(2).set_channels(1).raw_data
    return {"duration": len(seg) / 1000, "silence_ratio": _silence_ratio(raw, 2), "sample_rate": seg.frame_rate}


def main() -> int:
    # Windows 콘솔 기본 인코딩(cp949)에서 한글 JSON이 깨지지 않도록
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("file", type=Path)
    p.add_argument("--min-sec", type=float, default=0.3)
    p.add_argument("--max-silence-ratio", type=float, default=0.95)
    a = p.parse_args()

    if not a.file.exists() or a.file.stat().st_size == 0:
        print(json.dumps({"ok": False, "reason": "파일이 없거나 0바이트"}, ensure_ascii=False))
        return 1

    try:
        stats = _wav_stats(a.file) if a.file.suffix.lower() == ".wav" else _pydub_stats(a.file)
    except Exception as exc:  # 디코딩 실패 자체가 검증 실패 신호
        print(json.dumps({"ok": False, "reason": f"디코딩 실패: {exc}"}, ensure_ascii=False))
        return 1

    problems = []
    if stats["duration"] < a.min_sec:
        problems.append(f"길이 {stats['duration']:.2f}s < {a.min_sec}s")
    if stats["silence_ratio"] > a.max_silence_ratio:
        problems.append(f"무음 비율 {stats['silence_ratio']:.0%} > {a.max_silence_ratio:.0%}")

    print(json.dumps({"ok": not problems, "problems": problems, **stats}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
