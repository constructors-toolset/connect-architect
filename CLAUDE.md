# CLAUDE.md — AI 작업 규칙

이 저장소는 **건축 AI(Architecture AI) 통합 레포지토리**입니다.
여러 서브 프로젝트(별도 레포지토리)의 진행 상황을 모으고, 공통 문서·데이터·도구를 관리합니다.
AI(Claude 등)가 이 저장소에서 작업할 때는 아래 규칙을 **항상** 따릅니다.

## 1. 산출물 저장 위치 (필수)

AI가 만드는 모든 산출물은 아래 폴더 중 하나에 저장합니다. 저장소 루트나 임의의 새 최상위 폴더에 파일을 만들지 않습니다.

| 산출물 종류 | 위치 |
|---|---|
| 서브 프로젝트 보고서 / 진행 현황 | `report/<프로젝트-이름>.md` + `report/README.md` 인덱스 갱신 |
| 조사·리서치 문서 (논문, 기술 동향, 사례 분석) | `docs/research/` |
| 설계 문서 (아키텍처, 시스템 구조, 스펙) | `docs/design/` |
| 의사결정 기록 (ADR) | `docs/decisions/NNNN-제목.md` |
| 사용 가이드 / 매뉴얼 / 튜토리얼 | `docs/guides/` |
| 외부 참고자료 요약·링크 모음 | `docs/references/` |
| 원본 데이터 (수집한 그대로, 수정 금지) | `data/raw/` |
| 외부 공개 데이터셋 | `data/external/` |
| 정제·가공된 데이터 | `data/processed/` |
| **AI가 생성한 데이터** (합성 데이터, 추출 결과, 분석 결과 등) | `data/generated/` |
| 스크립트 / 유틸리티 코드 | `tools/scripts/` |
| 프롬프트 템플릿 | `tools/prompts/` |
| AI 에이전트 / 자동화 워크플로 정의 | `tools/agents/` |

어디에 넣을지 애매하면 위 표에서 가장 가까운 곳을 고르고, 커밋 메시지에 이유를 적습니다. 새 하위 폴더가 필요하면 해당 폴더의 `README.md`에 설명을 추가합니다.

## 2. 파일 이름 규칙

- 소문자 + 하이픈(kebab-case): `floor-plan-dataset-survey.md`
- 날짜가 의미 있는 문서는 앞에 날짜: `2026-09-23-bim-llm-survey.md`
- 데이터 파일은 `<출처>-<내용>-<버전>.<확장자>`: `seoul-building-permits-v1.csv`
- 공백, 한글 파일명은 피합니다 (내용은 한글 사용 가능).

## 3. AI 생성물 표시

AI가 만든 **문서**는 맨 위에 아래 front matter를 붙입니다.

```yaml
---
title: 문서 제목
created: 2026-09-23
author: ai            # ai | human | ai+human
sources: []           # 참고한 자료 / 입력 데이터 경로
status: draft         # draft | review | final
---
```

AI가 만든 **데이터**(`data/generated/`)에는 같은 이름의 `.meta.md` 파일(또는 폴더별 `README.md`)을 두어 생성 방법, 입력 데이터, 사용한 모델/도구, 생성일을 기록합니다.

AI가 만든 **도구**(`tools/`)는 파일 상단 주석에 목적·사용법을 적고, 해당 폴더 `README.md`의 목록에 한 줄을 추가합니다.

## 4. 서브 프로젝트 보고서 (`report/`)

- 서브 프로젝트 하나당 파일 하나: `report/<프로젝트-이름>.md` (`report/_template.md` 복사해서 시작)
- 새 보고서를 만들거나 갱신하면 **반드시** `report/README.md`의 프로젝트 목록 표를 함께 갱신합니다 (상태, 최종 갱신일).
- 기존 보고서는 덮어쓰지 않고 "변경 이력" 섹션에 날짜별로 누적합니다.

## 5. 금지 사항

- `data/raw/`의 원본 파일 수정 금지 (가공 결과는 `data/processed/`로).
- 대용량 파일(> 50MB)은 커밋하지 않습니다. `data/` 안에 위치·다운로드 방법만 문서화합니다.
- API 키, 비밀번호, 개인정보는 어떤 파일에도 저장하지 않습니다.
