# Architecture AI — 통합 레포지토리

건축 AI 관련 서브 프로젝트들을 한곳에서 관리하는 **메인 레포지토리**입니다.
각 서브 프로젝트는 별도 레포지토리로 개발하고, 이곳에는 진행 보고서와 공통 문서·데이터·도구를 모읍니다.

## 폴더 구조

```
.
├── CLAUDE.md          # AI 작업 규칙 (산출물 저장 위치, 명명 규칙)
├── report/            # 서브 프로젝트별 보고서 + 전체 현황 인덱스
├── docs/
│   ├── research/      # 조사·리서치
│   ├── design/        # 설계 문서
│   ├── decisions/     # 의사결정 기록 (ADR)
│   ├── guides/        # 가이드·매뉴얼
│   └── references/    # 외부 참고자료
├── data/
│   ├── raw/           # 원본 데이터 (수정 금지)
│   ├── external/      # 외부 공개 데이터셋
│   ├── processed/     # 정제·가공 데이터
│   └── generated/     # AI가 생성한 데이터
└── tools/
    ├── scripts/       # 스크립트·유틸리티
    ├── prompts/       # 프롬프트 템플릿
    ├── agents/        # AI 에이전트·워크플로
    └── claude-plugin/arch-ai/  # 공통 건축 전문 스킬 + MCP 서버 (서브 프로젝트 공용)
```

## 시작하기

- 서브 프로젝트 현황 → [`report/README.md`](report/README.md)
- 새 서브 프로젝트 보고서 → [`report/_template.md`](report/_template.md)를 복사
- AI와 작업할 때의 규칙 → [`CLAUDE.md`](CLAUDE.md)
- 건축 전문 스킬·도구(arch-ai 플러그인) → [`tools/claude-plugin/arch-ai/README.md`](tools/claude-plugin/arch-ai/README.md)
- 서브 프로젝트에서 공통 스킬 쓰기 → [`docs/guides/arch-ai-plugin.md`](docs/guides/arch-ai-plugin.md)
