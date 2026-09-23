# tools

| 폴더 | 내용 |
|---|---|
| `scripts/` | 데이터 처리, 변환, 분석용 스크립트와 유틸리티 |
| `prompts/` | 재사용할 프롬프트 템플릿 (`.md`) |
| `agents/` | AI 에이전트, 자동화 워크플로 정의 |
| `claude-plugin/` | 모든 서브 프로젝트가 공유하는 Claude Code 플러그인 (스킬 + MCP 서버) |

각 도구는 파일 상단에 목적과 사용법을 적고, 아래 목록에 한 줄을 추가합니다.

## 도구 목록

| 경로 | 설명 | 작성 | 추가일 |
|---|---|---|---|
| `claude-plugin/arch-ai/` | 건축 전문 스킬 8종 + MCP 서버 3개(arch-ai 도구 30개, IfcOpenShell 공식, 한국 법령): 법령·도면·BIM·구조·BOM·시방서·KDS/KCS·조달청 가격 — [README](claude-plugin/arch-ai/README.md) | ai | 2026-09-23 |
