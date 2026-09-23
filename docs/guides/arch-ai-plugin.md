---
title: arch-ai 공통 플러그인을 서브 프로젝트에서 사용하는 방법
created: 2026-09-23
author: ai
sources: [tools/claude-plugin/arch-ai]
status: draft
---

# arch-ai 공통 플러그인 사용 가이드

건축 전문 스킬·도구·MCP 서버는 이 허브 저장소의 `tools/claude-plugin/arch-ai`에 **한 번만** 정의되어 있고,
각 서브 프로젝트는 이 저장소를 플러그인 마켓플레이스로 등록해서 가져다 씁니다.
스킬이나 도구를 고칠 때는 서브 프로젝트가 아니라 **이 저장소에서** 고칩니다.

## 1. 서브 프로젝트에 설정하기 (권장: 자동 등록)

서브 프로젝트 저장소에 `.claude/settings.json`을 만들고 아래 내용을 넣은 뒤 커밋합니다.
Claude Code로 그 저장소를 열면 마켓플레이스 등록과 플러그인 설치를 안내합니다.

```json
{
  "extraKnownMarketplaces": {
    "connect-architect": {
      "source": { "source": "github", "repo": "lonycell/connect-architect" }
    }
  },
  "enabledPlugins": {
    "arch-ai@connect-architect": true
  }
}
```

> 마켓플레이스는 GitHub 저장소의 **기본 브랜치**를 읽습니다. 이 설정을 넣은 PR이 `master`에 머지된 뒤부터 동작합니다.
> 비공개 저장소라면 해당 환경에서 GitHub 인증이 되어 있어야 합니다.

## 2. 직접 설치하기 (개인 환경)

Claude Code에서:
```
/plugin marketplace add lonycell/connect-architect
/plugin install arch-ai@connect-architect
```

## 3. 법령 API 키 설정

1. https://open.law.go.kr 에서 Open API 사용을 신청합니다.
2. 발급받은 계정(OC)을 환경변수 `LAW_OC`로 설정합니다.
   - 로컬: 셸 프로필에 `export LAW_OC=...`
   - Claude Code on the web: 환경 설정의 환경변수(secrets)에 `LAW_OC` 추가
3. 키는 어떤 파일에도 커밋하지 않습니다.

## 4. 서브 프로젝트 CLAUDE.md에 추가할 내용 (권장)

```markdown
## 건축 전문 스킬
이 프로젝트는 허브 저장소(lonycell/connect-architect)의 arch-ai 플러그인을 사용한다.
건축 관련 작업은 arch-expert-team 스킬에서 시작하고, 분야별 스킬(arch-drawing-read, arch-drawing-draft,
arch-building-code, arch-structural-review, arch-bim-ifc, arch-specification, arch-bom-cost)의 절차를 따른다.
진행 상황은 허브 저장소 report/<이 프로젝트>.md 에 보고한다.
```

## 5. 동작 확인

- `/plugin` → `arch-ai` 가 enabled 인지 확인
- `/mcp` → `arch-ai` 서버가 connected 인지 확인 (첫 실행 시 Python 패키지 설치로 1~2분 걸릴 수 있음)
- "건축법 제55조 조회해줘" → 조문이 나오면 법령 도구 정상

## 6. 업데이트

허브 저장소에서 플러그인 버전을 올린 뒤, 서브 프로젝트에서 `/plugin marketplace update connect-architect`.

## 요구 사항

- Python 3.10 이상, `python3 -m venv` 사용 가능 환경
- 인터넷(첫 실행 시 PyPI에서 mcp, ezdxf, ifcopenshell 설치, 법령 API 호출)
