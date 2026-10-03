"""숏폼 하네스 실행 환경을 점검한다. 아무것도 설치하거나 바꾸지 않는다.

사용법: python check_env.py [--json] [--online]
  --json    사람이 읽는 표 대신 JSON 출력 (에이전트용)
  --online  edge-tts로 짧은 문장을 실제 합성해 네트워크까지 확인 (약 3초)
종료 코드: 0 필수 항목 모두 충족, 1 필수 항목 누락
비밀값(API 키)은 존재 여부만 확인하고 값은 출력하지 않는다.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OS = {"Windows": "windows", "Darwin": "mac"}.get(platform.system(), "linux")

FONT_CANDIDATES = {
    "windows": ["C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"],
    "mac": ["/System/Library/Fonts/AppleSDGothicNeo.ttc"],
    "linux": ["/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"],
}

# 설치 명령 — 사용자 승인 후 실행. needs_user=True 는 비밀번호·브라우저가 필요해 사용자가 직접 실행
INSTALL = {
    # 플러그인으로 설치되면 requirements.txt가 사용자 폴더에 없으므로 패키지 이름을 직접 쓴다
    "pillow": {"cmd": f'"{sys.executable}" -m pip install "pillow>=10" "edge-tts>=7"', "needs_user": False},
    "edge_tts": {"cmd": f'"{sys.executable}" -m pip install "pillow>=10" "edge-tts>=7"', "needs_user": False},
    "korean_font": {
        "windows": {"cmd": "(Windows 기본 맑은 고딕이 없음 — 설정 > 글꼴에서 '맑은 고딕' 복구)", "needs_user": True},
        "mac": {"cmd": "(macOS 기본 Apple SD 산돌고딕 Neo가 없음 — 서체 관리자에서 복구)", "needs_user": True},
        "linux": {"cmd": "sudo apt install -y fonts-nanum", "needs_user": True},
    },
    "ffmpeg": {
        "windows": {"cmd": "winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements", "needs_user": False},
        "mac": {"cmd": "brew install ffmpeg", "needs_user": False},
        "linux": {"cmd": "sudo apt install -y ffmpeg", "needs_user": True},
    },
    "codex": {"cmd": "npm install -g @openai/codex", "needs_user": False},
    "codex_login": {"cmd": "codex login", "needs_user": True},
    "node": {
        "windows": {"cmd": "winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements", "needs_user": False},
        "mac": {"cmd": "brew install node", "needs_user": False},
        "linux": {"cmd": "sudo apt install -y nodejs npm", "needs_user": True},
    },
}


def _install(key: str) -> dict:
    v = INSTALL.get(key, {})
    return v.get(OS, v) if OS in v else v


def _run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    exe = shutil.which(cmd[0])
    if not exe:
        return 127, ""
    try:
        p = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout + p.stderr).strip()
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, str(exc)


def item(key: str, label: str, level: str, ok: bool, detail: str, purpose: str, fix: dict | None = None) -> dict:
    return {"key": key, "label": label, "level": level, "ok": ok, "detail": detail, "purpose": purpose,
            "fix": None if ok else (fix or _install(key) or None)}


def check(online: bool) -> list[dict]:
    out = []
    py_ok = sys.version_info >= (3, 11)
    out.append(item("python", "Python 3.11+", "required", py_ok, platform.python_version(),
                    "하네스 스크립트 실행", {"cmd": "https://www.python.org/downloads/ 에서 3.11 이상 설치", "needs_user": True}))

    for mod, label, purpose in [("PIL", "Pillow", "썸네일 렌더링"), ("edge_tts", "edge-tts", "내레이션 음성 생성")]:
        spec = importlib.util.find_spec(mod)
        out.append(item("pillow" if mod == "PIL" else "edge_tts", label, "required", spec is not None,
                        "설치됨" if spec else "없음", purpose))

    font = next((f for f in FONT_CANDIDATES[OS] if Path(f).exists()), None)
    out.append(item("korean_font", "한글 폰트", "required", font is not None, font or "없음", "썸네일 한글 문구"))

    ff = shutil.which("ffmpeg")
    out.append(item("ffmpeg", "ffmpeg", "optional", ff is not None, ff or "없음", "영상 자동 조립(필수), mp3 길이·품질 검사"))

    yt = bool(os.environ.get("YOUTUBE_API_KEY"))
    out.append(item("youtube_key", "YouTube API 키", "optional", yt, "설정됨" if yt else "없음",
                    "유튜브 실제 조회수 데이터 (없으면 웹 자료로만 조사)",
                    {"cmd": "아래 '인증 안내' 참고 — 키는 사용자가 직접 환경변수로 설정", "needs_user": True}))

    node = shutil.which("npm")
    codex = shutil.which("codex")
    if not codex:
        out.append(item("codex", "Codex CLI", "optional", False, "없음" + ("" if node else " (npm도 없음 → Node.js 먼저 설치)"),
                        "썸네일 AI 배경 이미지 (연동 예정 — 지금은 그라데이션 배경)"))
        if not node:
            out.append(item("node", "Node.js / npm", "optional", False, "없음", "Codex CLI 설치에 필요"))
    else:
        _, ver = _run(["codex", "--version"])
        out.append(item("codex", "Codex CLI", "optional", True, ver.splitlines()[0] if ver else codex,
                        "썸네일 AI 배경 이미지 (연동 예정)"))
        rc, st = _run(["codex", "login", "status"])
        logged = rc == 0 and "logged in" in st.lower()
        out.append(item("codex_login", "Codex 로그인", "optional", logged, st.splitlines()[0] if st else "확인 실패",
                        "Codex 사용 인증 (ChatGPT 계정 또는 API 키)"))
        rc, feats = _run(["codex", "features", "list"])
        img = any(l.split()[:1] == ["image_generation"] and l.split()[-1] == "true" for l in feats.splitlines())
        out.append(item("codex_image", "Codex 이미지 생성", "optional", img, "켜짐" if img else "꺼짐 또는 미지원",
                        "AI 배경 생성 기능", {"cmd": "codex update  (최신 버전에서 image_generation 기능 제공)", "needs_user": False}))

    if online and importlib.util.find_spec("edge_tts"):
        out.append(_online_tts())
    return out


def _online_tts() -> dict:
    import edge_tts  # noqa: PLC0415

    async def go(path: str) -> None:
        await edge_tts.Communicate("테스트입니다.", "ko-KR-SunHiNeural").save(path)

    try:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.mp3")
            asyncio.run(asyncio.wait_for(go(p), 20))
            ok = os.path.getsize(p) > 1000
        return item("edge_tts_online", "edge-tts 온라인 합성", "required", ok, "성공" if ok else "빈 오디오", "음성 서버 접속",
                    {"cmd": "네트워크·방화벽 확인 후 재시도, 계속 실패하면 pip install -U edge-tts", "needs_user": True})
    except Exception as exc:
        return item("edge_tts_online", "edge-tts 온라인 합성", "required", False, f"실패: {exc}"[:120], "음성 서버 접속",
                    {"cmd": "네트워크·방화벽 확인 후 재시도, 계속 실패하면 pip install -U edge-tts", "needs_user": True})


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--online", action="store_true")
    a = ap.parse_args()
    items = check(a.online)
    missing_required = [i for i in items if i["level"] == "required" and not i["ok"]]
    if a.json:
        print(json.dumps({"os": OS, "ok": not missing_required, "items": items}, ensure_ascii=False, indent=2))
    else:
        for i in items:
            mark = "OK " if i["ok"] else ("!! " if i["level"] == "required" else "-- ")
            print(f"{mark}[{'필수' if i['level'] == 'required' else '선택'}] {i['label']}: {i['detail']}  ({i['purpose']})")
            if i["fix"]:
                who = "사용자가 직접 실행" if i["fix"].get("needs_user") else "승인 후 Claude가 실행 가능"
                print(f"      → {i['fix']['cmd']}  [{who}]")
        print("\n필수 항목 모두 충족" if not missing_required else f"\n필수 항목 {len(missing_required)}개 누락")
    return 0 if not missing_required else 1


if __name__ == "__main__":
    sys.exit(main())
