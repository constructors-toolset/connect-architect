# 서브 프로젝트 저장소 (`repo/`)

건축 AI 서브 프로젝트 저장소를 **git 서브모듈**로 연결하는 폴더입니다.
코드는 각 서브 프로젝트 저장소에 있고, 허브는 각 서브 프로젝트의 어느 커밋을 쓰는지만 기록합니다.

## 서브 프로젝트 목록

새 서브 프로젝트를 연결하거나 상태가 바뀌면 이 표를 함께 갱신합니다.

| 프로젝트 | 경로 | 저장소 | 분야 | 상태 | 최종 갱신 | 설명 |
|---|---|---|---|---|---|---|
| spec-ai | [`repo/spec-ai`](spec-ai) | [constructors-toolset/spec-ai](https://github.com/constructors-toolset/spec-ai) | 시방서 | 기획 | 2026-09-23 | 도면·BIM·표준시방서·법규·자재 DB를 근거로 공사시방서 초안 자동 작성, 문장별 근거 추적, 불일치 경고 |

**상태 값:** `기획` · `진행중` · `보류` · `완료`

## 새 서브 프로젝트 연결

```bash
git submodule add https://github.com/constructors-toolset/<저장소>.git repo/<프로젝트-이름>
git commit -m "Add <프로젝트-이름> sub-project"
```

연결한 뒤 서브 프로젝트 저장소에 공통 스킬(arch-ai 플러그인) 설정을 넣습니다 → [`docs/guides/arch-ai-plugin.md`](../docs/guides/arch-ai-plugin.md)

## 허브 저장소 받기 / 갱신

```bash
git clone --recurse-submodules https://github.com/constructors-toolset/connect-architect.git
git submodule update --init --recursive     # 이미 받은 저장소에서 서브모듈 받기
git submodule update --remote repo/<이름>    # 서브 프로젝트 최신 커밋으로 올리기 (그 뒤 허브에 커밋)
```

## 진행 기록

서브 프로젝트별 주요 변경을 날짜순으로 누적합니다(덮어쓰지 않음).

| 날짜 | 프로젝트 | 내용 |
|---|---|---|
| 2026-09-23 | spec-ai | 저장소 생성, 서브모듈 연결. 제품 비전·아키텍처 초안·작업 규칙 작성 (기획 단계) |
