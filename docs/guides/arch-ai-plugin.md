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
      "source": { "source": "github", "repo": "constructors-toolset/connect-architect" }
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
/plugin marketplace add constructors-toolset/connect-architect
/plugin install arch-ai@connect-architect
```

## 3. 무료 API 키 설정

| 환경변수 | 발급처 | 쓰는 도구 |
|---|---|---|
| `LAW_OC` | https://open.law.go.kr → Open API 사용 신청 (발급 계정 ID가 OC) | 법령(arch-ai `law_*`, korean-law) |
| `KCSC_API_KEY` | https://www.kcsc.re.kr → Open API 인증키 신청 | KDS·KCS·전문시방서 원문(`kcsc_*`) |
| `DATA_GO_KR_KEY` | https://www.data.go.kr → "조달청_나라장터 가격정보현황서비스" 활용신청, **Decoding 키** 사용 | 조달청 가격(`price_*`) |

- 로컬: 셸 프로필에 `export LAW_OC=...` 등
- Claude Code on the web: 환경 설정의 환경변수(secrets)에 추가
- 키는 어떤 파일에도 커밋하지 않습니다. 키가 없으면 해당 도구만 오류 안내를 내고 나머지는 동작합니다.

## 4. (선택) docling — 도면·시방서 PDF 표 추출

설치 용량이 약 6GB(OCR·레이아웃 모델 포함)라 기본으로 켜지 않습니다. 필요할 때 한 번 등록합니다(uv 필요).
```bash
claude mcp add docling -- <허브 저장소>/tools/claude-plugin/arch-ai/bin/archai docling
```
처음 실행 때 모델을 내려받느라 몇 분 걸립니다. 먼저 터미널에서 `bin/archai docling --help`를 한 번 실행해 두면 좋습니다.

## 5. 서브 프로젝트 CLAUDE.md에 추가할 내용 (권장)

```markdown
## 건축 전문 스킬
이 프로젝트는 허브 저장소(constructors-toolset/connect-architect)의 arch-ai 플러그인을 사용한다.
건축 관련 작업은 arch-expert-team 스킬에서 시작하고, 분야별 스킬(arch-drawing-read, arch-drawing-draft,
arch-building-code, arch-structural-review, arch-bim-ifc, arch-specification, arch-bom-cost)의 절차를 따른다.
이 저장소는 허브 저장소의 repo/<이 프로젝트>/ 에 서브모듈로 연결되어 있다. 진행 상황은 허브 repo/README.md 에 기록한다.
```

## 6. 동작 확인

- `/plugin` → `arch-ai` 가 enabled 인지 확인
- `/mcp` → `arch-ai`, `ifc-openshell`, `korean-law` 가 connected 인지 확인 (첫 실행 시 패키지 설치로 1~2분 걸릴 수 있음)
- "건축법 제55조 조회해줘" → 조문이 나오면 법령 도구 정상

## 7. 업데이트

허브 저장소에서 플러그인 버전을 올린 뒤, 서브 프로젝트에서 `/plugin marketplace update connect-architect`.

## 요구 사항

- Python 3.10 이상, `python3 -m venv` 사용 가능 환경
- Node.js 18 이상 (`npx`, korean-law MCP)
- (docling 사용 시) uv
- 인터넷(첫 실행 시 PyPI에서 mcp, ezdxf, ifcopenshell 설치, 법령 API 호출)
