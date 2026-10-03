# youtube-shorts 플러그인 저장소

이 저장소는 Claude Code 플러그인 마켓플레이스(`youtubeshorts`)이자 `youtube-shorts` 플러그인 소스다. 저장소 루트가 곧 플러그인 루트다(`marketplace.json`의 `source: "./"`).

```
.claude-plugin/marketplace.json   마켓플레이스 목록
.claude-plugin/plugin.json        플러그인 정보·버전
agents/                           에이전트 정의 (호출 이름: youtube-shorts:<이름>)
skills/                           스킬 (shorts-orchestrator가 진입점)
```

## 하네스: 숏폼 콘텐츠 기획

**목표:** 유튜브 쇼츠·인스타그램 릴스 트렌드를 조사해 대시보드로 보여주고, 크리에이터 프로필(`content/creator_profile.md`)에 맞는 기획 → 대본 → 썸네일 → 내레이션 음성을 만든다.

**트리거:** 숏폼 트렌드 조사, 영상 기획·대본·썸네일·음성 요청(재실행, 부분 수정, 다음 회차 포함) 시 `shorts-orchestrator` 스킬을 사용하라. 설치·환경 점검·로그인/API 키 연결 요청은 `shorts-setup` 스킬.

## 플러그인을 고칠 때 지킬 것

- **경로:** 스킬 안의 경로는 `{PLUGIN}`(플러그인 루트) 표기를 쓴다. `.claude/skills/...` 같은 고정 경로를 쓰지 않는다 — 설치되면 플러그인은 사용자 캐시 폴더에 있다.
- **사용자 데이터:** `content/`, `_workspace_shorts/`, `output/`은 사용자가 Claude Code를 연 폴더에 쓴다. 플러그인 폴더에 쓰지 않는다.
- **버전:** 변경을 배포할 때 `.claude-plugin/plugin.json`과 `marketplace.json`의 `version`을 같이 올린다. 버전이 같으면 사용자의 `/plugin update`에 반영되지 않는다.
- **검증:** 커밋 전 `claude plugin validate .` 실행. 설치 없이 시험하려면 `claude --plugin-dir .`.
- **기록:** 변경은 `docs/harness-changelog.md`에 한 줄 추가한다.

**변경 이력:** (상세: `docs/harness-changelog.md`)
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-10-03 | 숏폼 하네스 초기 구성 및 첫 실행 피드백 반영 | 전체 | - |
| 2026-10-03 | 플러그인 마켓플레이스 구조로 전환 (v1.0.0), TTS 개발 하네스 분리 | 전체 | 마켓플레이스 설치 배포 |
