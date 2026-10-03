# youtube-shorts — 숏폼 콘텐츠 하네스

Claude Code 플러그인입니다. 설치한 뒤 "요즘 쇼츠 트렌드 보고 나한테 맞는 영상 기획해줘"라고 말하면, 여러 AI 에이전트가 나눠서 일해 아래 결과물을 만들어 줍니다.

- **트렌드 리포트** — 유튜브 쇼츠·인스타그램 릴스에서 지금 뜨는 포맷·주제·훅·음원 (출처·날짜 포함)
- **기획안 3개** — 내 채널 프로필에 맞춰 점수를 매긴 아이디어 중 하나를 고른다
- **대본** — 초 단위 장면표(화면·내레이션·자막·효과음), 제목·설명·해시태그, 촬영 체크리스트
- **썸네일** — 9:16 PNG (시리즈 디자인 자동 유지)
- **내레이션 음성** — TTS mp3 (얼굴·목소리 없는 채널용)
- **대시보드** — 위 내용을 한 페이지로 모은 링크

## 설치

먼저 두 가지를 직접 설치하세요.

1. [Claude Code](https://claude.com/claude-code)
2. [Python 3.11 이상](https://www.python.org/downloads/) — Windows는 설치 화면에서 "Add python.exe to PATH"를 체크하세요

그다음 Claude Code에서 플러그인을 설치합니다.

```
/plugin marketplace add punkyade/youtubeshorts
/plugin install youtube-shorts@youtubeshorts
/reload-plugins
```

터미널에서 한 번에 하려면:

```
claude plugin marketplace add punkyade/youtubeshorts
claude plugin install youtube-shorts@youtubeshorts
```

설치는 사용자 단위라 어느 폴더에서든 쓸 수 있습니다. 콘텐츠용 폴더를 하나 만들어 그 안에서 Claude Code를 여는 것을 권장합니다. 프로필과 결과물이 그 폴더에 쌓입니다.

```
mkdir my-shorts && cd my-shorts
claude
> 환경 점검해줘
```

### 업데이트

```
/plugin marketplace update youtubeshorts
/plugin update youtube-shorts@youtubeshorts
```

## 환경 점검

처음에는 **"환경 점검해줘"**라고 말하세요. 숏폼 작업을 시작할 때도 자동으로 점검하고, 필수 항목이 빠져 있으면 제작보다 설치 안내를 먼저 합니다.

1. **점검** — 필요한 도구를 몇 초 만에 확인합니다. 점검만 하고 아무것도 바꾸지 않습니다
2. **보고** — 무엇이 없고, 어디에 필요하고, 없으면 어떻게 되는지 표로 알려 줍니다
3. **승인 후 설치** — 설치할 항목을 고르면 실행할 명령을 미리 보여 주고, 고른 것만 하나씩 설치합니다
4. **인증 안내** — 로그인·API 키처럼 본인이 해야 하는 일은 단계별로 안내합니다
5. **재점검** — 새로 해결된 것과 남은 것만 알려 줍니다

### 점검 항목

| 항목 | 수준 | 용도 | 없으면 | 설치 |
|---|---|---|---|---|
| Python 3.11+ | 필수 | 스크립트 실행 | 동작 안 함 | 직접 설치 (위 링크) |
| Pillow, edge-tts | 필수 | 썸네일 렌더링, 음성 생성 | 동작 안 함 | 승인 후 Claude가 `pip install` |
| 한글 폰트 | 필수 | 썸네일 한글 문구 | 동작 안 함 | Windows 맑은 고딕, Mac Apple SD 산돌고딕은 기본 내장. Linux는 `sudo apt install fonts-nanum` (직접) |
| 음성 서버 접속 | 필수 | edge-tts 음성 합성 | 동작 안 함 | 네트워크·방화벽 확인 |
| ffmpeg | 선택 | mp3 품질 검사, (예정) 영상 자동 조립 | 음성 길이는 파일 크기로 추정 | 승인 후 Claude가 설치 (Windows `winget`, Mac `brew`). Linux는 `sudo apt install ffmpeg` (직접) |
| YouTube API 키 | 선택 | 유튜브 실제 조회수 데이터 | 웹 자료로만 조사 | 아래 인증 안내 (직접) |
| Node.js → Codex CLI | 선택 | (연동 예정) 썸네일 AI 배경 이미지 | 그라데이션 배경 | 승인 후 Claude가 `npm install -g @openai/codex` |
| Codex 로그인 | 선택 | Codex 사용 인증 | 위와 같음 | 아래 인증 안내 (직접) |

Mac·Linux 설치 명령은 넣어 두었지만 아직 실제로 실행해 보지 않았습니다. 막히면 Claude에게 오류 메시지를 보여 주세요.

### 인증 안내 (본인이 직접)

**비밀번호나 API 키는 대화창에 붙여 넣지 마세요.** 대화 기록에 남습니다. Claude는 키가 "설정됐는지"만 확인합니다.

**Codex 로그인**
1. Claude Code 프롬프트에 `! codex login` 입력
2. 브라우저가 열리면 ChatGPT 계정으로 로그인 (안 열리면 별도 터미널에서 `codex login`)
3. "다 했어"라고 말하면 다시 점검합니다

ChatGPT 구독의 사용량을 씁니다. 회사 정책상 개인 계정 사용이 문제되면 팀 계정이나 API 키를 쓰세요.

**YouTube Data API 키**
1. [Google Cloud 콘솔](https://console.cloud.google.com/)에서 프로젝트를 만들거나 선택
2. "API 및 서비스" → "라이브러리" → **YouTube Data API v3** → 사용 설정
3. "사용자 인증 정보" → "사용자 인증 정보 만들기" → **API 키**. 키의 "API 제한사항"을 YouTube Data API v3로 제한하는 것을 권장
4. 환경변수 `YOUTUBE_API_KEY`로 저장
   - Windows: 시작 메뉴 "시스템 환경 변수 편집" → 환경 변수 → 사용자 변수 "새로 만들기". 또는 별도 PowerShell에서 `setx YOUTUBE_API_KEY "키"`
   - Mac/Linux: `~/.zshrc`(또는 `~/.bashrc`)에 `export YOUTUBE_API_KEY="키"` 추가
5. Claude Code를 완전히 종료한 뒤 다시 열고 "환경 점검해줘"

무료 한도는 하루 10,000단위입니다. 하네스는 인기 차트(1단위) 위주로 쓰고, 검색(100단위)은 2~3회로 제한합니다.

## 사용법

| 이렇게 말하면 | 이렇게 진행돼요 |
|---|---|
| "환경 점검해줘", "설치해줘", "codex 연결해줘" | 점검 → 승인 후 설치 → 인증 안내 → 재점검 |
| "요즘 쇼츠 트렌드 보고 나한테 맞는 영상 기획해줘" | (첫 실행) 프로필 질문 → 트렌드 조사 → 기획안 3개 중 선택 → 대본·썸네일 → 검토 → 음성 선택 → 대시보드 |
| "클로드 코드 활용법 영상 만들어줘" | 주제를 정해 기획안 → 대본·썸네일·음성 |
| "2화 만들어줘" | 시리즈 규칙 유지, 회차 주제 후보 3개 중 선택 → 대본·썸네일·음성 (트렌드는 7일 내면 재사용) |
| "대본만 다시, 훅 더 세게" / "썸네일만 다시" | 해당 부분만 다시 |
| "요즘 트렌드 다시 봐줘" | 트렌드만 새로 조사하고 대시보드 갱신 |
| "프로필 바꿀래" / "목소리 바꿔줘" | 프로필 질문을 다시 |

진행 중에 Claude가 몇 번 질문합니다 — 첫 실행의 프로필(분야·타깃·출연 방식·제작 여건·말투), 기획안 선택, 목소리 선택. "알아서 해"라고 하면 점수가 가장 높은 안으로 진행합니다.

## 결과물 위치

Claude Code를 연 폴더에 아래 구조로 쌓입니다.

```
content/
├── creator_profile.md    내 채널 프로필 (다음 실행에 재사용)
└── episodes.md           시리즈 회차 기록
output/shorts/{날짜}_{주제}/
├── dashboard.html        대시보드 (claude.ai 비공개 링크로도 공개됨)
├── script.md             사람이 읽는 대본 + 촬영 체크리스트
├── script.json           대본 데이터
├── narration.txt         TTS 원고
├── narration.mp3         내레이션 음성
├── thumbnail.png         썸네일
└── trends.json           트렌드 조사 원본
_workspace_shorts/        작업 중간물 (부분 재실행에 사용)
```

이 폴더가 git 저장소라면, 첫 실행 때 개인 데이터를 `.gitignore`에 넣을지 물어봅니다.

## 알아둘 점

- **사람이 할 일**: 대본 체크리스트에 있는 스크린샷 촬영, 스톡 영상 준비, 영상 편집은 직접 해야 합니다. (영상 자동 조립은 아직 없음)
- **Codex 썸네일**: 점검·설치·로그인 안내는 준비됐지만, 썸네일 단계는 아직 Codex를 쓰지 않습니다(연동 예정). 지금 썸네일은 로컬 템플릿으로만 만듭니다.
- **비용**: 에이전트는 Opus 모델을 사용합니다. 첫 실행 1회에 에이전트가 7~9번 호출되고, 트렌드 조사에 웹 검색을 많이 씁니다.
- **웹 검색**: Claude Code에서 웹 검색(WebSearch/WebFetch)이 허용되어 있어야 트렌드 조사가 됩니다.
- **대시보드 링크**: claude.ai 아티팩트 기능을 쓸 수 없는 계정이면 링크 대신 로컬 `dashboard.html`을 브라우저로 여세요.
- **인스타그램 수치**: 공개 API가 없어 조회수 등은 기사·리포트 인용값입니다.
- **플랫폼 정책**: AI 음성 + 같은 템플릿 대량 생산은 수익화 제외·중복 콘텐츠 판정 위험이 있습니다. 하네스는 회차마다 직접 만든 예시와 "내 경험 한 줄" 장면을 넣도록 설계되어 있으니 이 부분을 빼지 마세요.

## 구성 (고치고 싶은 사람용)

```
.claude-plugin/
├── marketplace.json        마켓플레이스 목록 (이름: youtubeshorts)
└── plugin.json             플러그인 정보·버전 (이름: youtube-shorts)
agents/                     에이전트 정의 — 누가 하는가 (호출 이름: youtube-shorts:<이름>)
├── trend-researcher.md     플랫폼별 트렌드 조사
├── content-planner.md      기획안 3개 + 점수
├── script-writer.md        초 단위 대본
├── thumbnail-designer.md   썸네일 렌더
└── content-reviewer.md     근거·정확성·정책 검토
skills/                     스킬 — 어떻게 하는가
├── shorts-setup/           환경 점검·설치·인증 안내 (+ 점검 스크립트)
├── shorts-orchestrator/    전체 흐름 조율 (+ 대시보드 생성, 오디오 검사 스크립트, 예시 프로필)
├── shorts-trend-research/  조사 방법 (+ YouTube API 스크립트)
├── shorts-planning/        기획·점수 기준
├── shorts-scriptwriting/   대본 작성법
└── thumbnail-design/       썸네일 규칙 (+ Pillow 렌더 스크립트)
docs/harness-changelog.md   변경 이력
```

**고친 뒤 시험·배포하는 법**
1. `claude plugin validate .` — 구조 검증
2. `claude --plugin-dir .` — 설치 없이 이 폴더의 플러그인으로 Claude Code 실행
3. `.claude-plugin/plugin.json`과 `marketplace.json`의 `version`을 올리고 커밋·푸시 — 버전이 같으면 사용자의 업데이트에 반영되지 않습니다

결과가 아쉬우면 Claude에게 그대로 말하세요 ("기획안이 너무 어려워", "썸네일 글자가 작아"). 반복되는 피드백은 스킬에 반영해 하네스를 고칠 수 있습니다.
