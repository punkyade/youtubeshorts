---
name: shorts-setup
description: "숏폼 하네스 실행 환경을 점검하고, 빠진 도구를 사용자에게 알린 뒤 승인을 받아 설치하고, 로그인·API 키 같은 인증을 단계별로 안내한다. '환경 점검', '설치해줘', '세팅', '처음 사용', '뭐가 필요해', '연결 안 돼', 'codex 연결', 'YouTube API 키 설정', 'ffmpeg 설치', '썸네일이 안 만들어져', '음성이 안 나와' 요청 시 반드시 사용할 것. shorts-orchestrator가 실행 전 점검에서 필수 항목 누락을 발견해도 이 스킬로 넘어온다."
---

# 숏폼 하네스 환경 설정

> **경로:** `{PLUGIN}` = youtube-shorts 플러그인 루트. 이 스킬이 로딩될 때 주어지는 "Base directory for this skill"의 두 단계 위 폴더다(`…/skills/<스킬 이름>` → 상위의 상위). 서브 에이전트는 오케스트레이터가 프롬프트로 준 절대 경로를 쓴다. Mac·Linux에서 `python`이 없으면 `python3`.

팀원마다 PC 상태가 다르다. 목표는 사용자가 "무엇이 없고, 왜 필요하고, 어떻게 채우는지"를 이해한 상태에서, **승인한 것만** 설치하고 인증은 사용자가 직접 끝내게 하는 것이다. 몰래 설치하거나, 비밀값을 대화로 받거나, 실패를 성공처럼 보고하지 않는다.

## 1. 점검

```
python {PLUGIN}/skills/shorts-setup/scripts/check_env.py --json --online
```
아무것도 바꾸지 않는 읽기 전용 점검이다. 결과의 각 항목: `level`(required/optional), `ok`, `detail`, `purpose`, `fix.cmd`, `fix.needs_user`.

Python 자체가 없으면 이 스크립트가 돌지 않는다 — 그때는 python.org 설치 안내부터 한다(Windows는 설치 시 "Add python.exe to PATH" 체크).

## 2. 보고

사용자에게 표 하나로 보여준다. 항목마다 상태, 용도, 없을 때 어떻게 되는지를 쓴다.

| 수준 | 없을 때 |
|---|---|
| 필수 (Python, Pillow, edge-tts, 한글 폰트, 음성 서버 접속) | 하네스가 동작하지 않는다 — 채우기 전에는 제작을 시작하지 않는다 |
| 선택 (ffmpeg, YouTube API 키, Codex) | 대체 동작으로 계속한다: ffmpeg 없음 → mp3 길이는 파일 크기로 추정 / API 키 없음 → 웹 자료만 / Codex 없음 → 그라데이션 배경 |

선택 항목은 강요하지 않는다. "지금은 건너뛰기"를 항상 선택지에 둔다.

## 3. 설치 승인

`AskUserQuestion`(multiSelect)으로 설치할 항목을 고르게 한다. 각 옵션 설명에 **실행될 명령 그대로**와 소요 시간·용량 감을 적는다. 고르지 않은 것은 설치하지 않는다.

설치 순서 (의존 관계):
1. `pip install -r requirements.txt` — Pillow, edge-tts
2. Node.js → Codex CLI (`npm install -g @openai/codex`) — npm이 없으면 Node.js 먼저
3. ffmpeg

실행 규칙:
- `fix.needs_user: false` 항목만 Claude가 실행한다. 한 항목씩 실행하고 결과를 확인한 뒤 다음으로 간다.
- `fix.needs_user: true`(sudo 비밀번호, 브라우저 로그인, OS 설정)는 실행하지 않고, 사용자가 프롬프트에 `! <명령>`으로 직접 실행하도록 안내한다.
- Windows `winget` 설치 직후에는 현재 셸의 PATH가 갱신되지 않아 "없음"으로 보일 수 있다. 실패로 단정하지 말고 "Claude Code를 다시 시작한 뒤 재점검"을 안내한다.
- 설치가 실패하면 오류 메시지 핵심 한 줄과 다음 시도(관리자 권한, 회사 프록시, 수동 설치 링크)를 알리고 다음 항목으로 넘어간다.

## 4. 인증 (사용자가 직접)

비밀값(API 키, 비밀번호)은 대화창에 붙여 넣게 하지 않는다 — 대화 기록에 남는다. 사용자가 자기 터미널이나 OS 설정에서 넣게 하고, Claude는 "설정됨/없음"만 확인한다.

### Codex 로그인
1. 프롬프트에 `! codex login` 입력 → 브라우저가 열리면 ChatGPT 계정으로 로그인
2. 브라우저가 안 열리거나 회사 PC에서 막히면 별도 터미널에서 `codex login` 실행 (옵션은 `codex login --help`)
3. 끝나면 "다 했어"라고 말하게 하고 재점검. `Codex 로그인`이 OK인지 확인
- ChatGPT 구독의 사용량을 쓴다는 점을 알린다. 회사 정책상 개인 계정 사용이 문제되면 팀 계정/API 키 사용 여부를 사용자가 판단하게 한다.

### YouTube Data API 키
1. https://console.cloud.google.com/ 접속 → 프로젝트 만들기(또는 선택)
2. "API 및 서비스" → "라이브러리" → **YouTube Data API v3** → 사용 설정
3. "사용자 인증 정보" → "사용자 인증 정보 만들기" → **API 키** → 생성된 키에서 "API 제한사항"을 YouTube Data API v3로 제한(권장)
4. 환경변수로 저장 — 사용자가 직접:
   - Windows: 시작 메뉴 "시스템 환경 변수 편집" → 환경 변수 → 사용자 변수 "새로 만들기" → 이름 `YOUTUBE_API_KEY`, 값 = 키. 또는 별도 PowerShell에서 `setx YOUTUBE_API_KEY "키"`
   - Mac/Linux: `~/.zshrc`(또는 `~/.bashrc`)에 `export YOUTUBE_API_KEY="키"` 추가
5. Claude Code를 완전히 종료 후 다시 열기(환경변수는 새로 시작한 프로세스에만 반영) → 재점검
- 무료 한도 하루 10,000단위. 하네스는 인기 차트(1단위) 위주로 쓰고 검색(100단위)은 2~3회로 제한한다.

## 5. 재점검과 마무리

같은 점검 명령을 다시 돌려 변화만 보고한다: "새로 OK: ffmpeg, Codex 로그인 / 여전히 없음: YouTube API 키(건너뜀)". 필수 항목이 모두 OK면 "이제 '쇼츠 기획해줘'로 시작할 수 있다"고 안내한다. 필수 항목이 남았으면 무엇 때문에 막혔는지와 다음 행동 하나만 말한다.

설치 결과를 파일로 기록하지 않는다 — 점검은 몇 초면 끝나므로 매번 실제 상태를 본다.
