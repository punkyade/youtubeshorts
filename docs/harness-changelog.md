# 하네스 상세 변경 이력

`CLAUDE.md`의 변경 이력은 요약만 둔다. 하네스를 진화시킬 때(`harness:evolve` 등) 맥락이 필요하면 이 파일을 읽는다.

| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-10-03 | TTS 하네스 초기 구성 (4 에이전트, 6 스킬, 서브 에이전트 모드, 기본 엔진 edge-tts) | 전체 | - |
| 2026-10-03 | 숏폼 콘텐츠 하네스 추가 (5 에이전트, 5 스킬, 작업 폴더 `_workspace_shorts/`, 썸네일 로컬 Pillow 템플릿, 데이터 웹+YouTube API 선택, 결과 대시보드 Artifact) | agents/trend-researcher·content-planner·script-writer·thumbnail-designer·content-reviewer, skills/shorts-* · thumbnail-design | 트렌드 분석 + 맞춤 기획·대본·썸네일 요청 |
| 2026-10-03 | 썸네일 렌더러를 줄 단위로 그리도록 수정, 대시보드에 짧은 페이지 제목 인자 추가 | thumbnail-design/scripts/render_thumbnail.py, shorts-orchestrator/scripts/build_dashboard.py·SKILL.md | 첫 실행: 어간 문의, 업로드 제목이 탭 제목으로 길게 들어감 |
| 2026-10-03 | '다음 회차' 실행 모드 추가 (트렌드 7일 내 재사용, 회차 주제 후보 3개, `content/episodes.md` 회차 기록) | shorts-orchestrator/SKILL.md | 매일 업로드 시리즈인데 "2화" 요청 시 트렌드 조사부터 다시 하던 공백 |
| 2026-10-03 | 내레이션 음성 자동 생성 연결 (프로필 음성, TTS 패키지 없으면 edge-tts CLI), 대본 음절 예산을 프로필 실측값 우선으로 | shorts-orchestrator/SKILL.md Phase 6, shorts-scriptwriting/SKILL.md | 음성 4종 비교 후 선택. 기본 속도로는 30초 초과 |
| 2026-10-03 | 팀 공유판 정리: 하드코딩 경로 제거, 개인 데이터 `.gitignore`, 플러그인 설정을 `settings.local.json`으로 분리, 예시 프로필·README·requirements 추가, 음성 미설정·회차 기록 없음(첫 실행) 처리 | tts-orchestrator/SKILL.md, shorts-orchestrator/SKILL.md, 루트 파일 | 다른 팀과 공유 |
| 2026-10-03 | 환경 점검·설치·인증 안내 스킬 `shorts-setup` 추가 (`check_env.py`: 필수/선택 항목 점검, 승인 후 설치, 로그인·API 키는 사용자가 직접), 오케스트레이터 Phase 0에 자동 점검 연결 | skills/shorts-setup, shorts-orchestrator/SKILL.md, README.md | 팀원 PC마다 도구·인증 상태가 다름. Codex 썸네일 연동 준비 |
