# arch-ai — 건축 AI 공통 플러그인

모든 건축 AI 서브 프로젝트에서 같이 쓰는 **스킬 + 도구 + MCP 서버** 묶음(Claude Code 플러그인)입니다.

## 구성

```
arch-ai/
├── .claude-plugin/plugin.json   # 플러그인 정의
├── .mcp.json                    # MCP 서버 3개 등록: arch-ai, ifc-openshell, korean-law
├── hooks/hooks.json             # 세션 시작 시 Python 환경 자동 준비
├── bin/archai                   # 실행기 (전용 venv 자동 생성: ~/.cache/arch-ai/venv)
├── requirements.txt             # mcp(1.x), ezdxf, ifcopenshell, ifcopenshell-mcp
├── archai/                      # 도구 코드 (CLI + MCP 공용)
│   ├── law.py        국가법령정보센터 법령·조례·고시·판례·해석례 검색, 조문 조회
│   ├── dxf_tools.py  DXF 도면 해석(레이어·치수·문자·면적) / 평면도 작도
│   ├── ifc_tools.py  IFC 요약·요소 조회·품질 검증·물량 집계·속성 수정
│   ├── structure.py  하중조합, 보 해석, RC 보 휨·전단, 최소두께
│   ├── bom.py        BOM SQLite DB (품목·단가·조립체·IFC 매핑) + 물량→재료비
│   ├── spec.py       KCS 3부 구성 시방서 골격, 시방서-BOM 교차검토
│   ├── kcsc.py       국가건설기준센터 API: KDS·KCS·LHCS 등 원문 검색·조항 조회
│   ├── price.py      조달청 가격정보 API: 자재·시장시공가격·표준시장단가 → BOM 단가
│   ├── mcp_server.py 위 기능을 MCP 도구 30개로 노출
│   └── seed/items.csv 기본 품목 32종 (단가 없음)
└── skills/
    ├── arch-expert-team        총괄: 분야 분해 → 분야별 스킬 → 교차 검토 → 종합 보고
    ├── arch-drawing-read       도면 판독·해석 (+ references/conventions.md 표기 규약)
    ├── arch-drawing-draft      도면 작도 (DXF)
    ├── arch-building-code      법규 검색·검토 (+ references/checklist.md 조문 체크리스트)
    ├── arch-structural-review  구조 검토·오류 정정 (+ references/rules-of-thumb.md)
    ├── arch-bim-ifc            BIM(IFC) 읽기·검증·수정
    ├── arch-specification      시방서 작성·검토
    └── arch-bom-cost           BOM DB 구축, 물량·재료비, 도면·시방서 연계
```

## MCP 서버

| 서버 | 출처 | 역할 |
|---|---|---|
| `arch-ai` | 이 플러그인 (`archai/`) | 아래 도구 30개 |
| `ifc-openshell` | IfcOpenShell 공식 [ifcopenshell-mcp](https://docs.ifcopenshell.org/ifcmcp.html) (LGPL-3.0) | IFC 세션 편집, 간섭검토(`ifc_clash`), 수량 계산, 도면·렌더 등 25개 |
| `korean-law` | [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp) (MIT, npx) | 법령·별표·조례 비교·판례·해석례·인용 검증 10개 |
| `docling` (선택) | [docling-mcp](https://github.com/docling-project/docling-mcp) (MIT) | PDF 표·레이아웃 추출. 약 6GB라 기본 등록하지 않음 → `docs/guides/arch-ai-plugin.md` |

## arch-ai 도구 목록

| 분야 | 도구 |
|---|---|
| 법령 | `law_search`, `law_article`, `law_core_list` |
| 도면 | `dxf_inspect`, `dxf_draw` |
| BIM | `ifc_summary`, `ifc_elements`, `ifc_element`, `ifc_validate`, `ifc_takeoff`, `ifc_set_property` |
| 구조 | `struct_load_combinations`, `struct_beam`, `struct_rc_beam`, `struct_min_depth` |
| BOM | `bom_init`, `bom_search`, `bom_price_add`, `bom_assembly_add`, `bom_map_add`, `bom_cost` |
| 시방서 | `spec_skeleton`, `spec_check` |
| 국가건설기준 | `kcsc_search`, `kcsc_get`, `kcsc_toc`, `kcsc_grep` |
| 조달청 가격 | `price_categories`, `price_search`, `price_link_to_bom` |

## 환경변수

| 이름 | 용도 |
|---|---|
| `LAW_OC` | 국가법령정보센터 Open API 계정(OC). open.law.go.kr에서 무료 신청. arch-ai `law_*`와 korean-law가 사용 |
| `KCSC_API_KEY` | 국가건설기준센터 Open API 키. kcsc.re.kr에서 신청. `kcsc_*`가 사용 |
| `DATA_GO_KR_KEY` | 공공데이터포털 인증키(Decoding). "조달청_나라장터 가격정보현황서비스" 활용신청. `price_*`가 사용 |
| `ARCHAI_BOM_DB` | BOM DB 경로 (기본 `data/processed/bom/arch-bom.sqlite`, 작업 디렉터리 기준) |
| `ARCHAI_VENV` | Python 가상환경 위치 (기본 `~/.cache/arch-ai/venv`) |

## 설치·사용

서브 프로젝트에 붙이는 방법은 [`docs/guides/arch-ai-plugin.md`](../../../docs/guides/arch-ai-plugin.md)를 봅니다.

CLI로 직접 쓰기:
```bash
tools/claude-plugin/arch-ai/bin/archai law article 건축법 55
tools/claude-plugin/arch-ai/bin/archai dxf inspect plan.dxf
tools/claude-plugin/arch-ai/bin/archai ifc validate model.ifc
tools/claude-plugin/arch-ai/bin/archai structure rc-beam --b 400 --d 540 --fck 24 --fy 400 --As 1548 --Mu 250
```

## 한계

- 구조 도구는 단일 부재 예비 검토용이다(골조 해석·내진 해석 아님).
- 도면 작도는 초안 수준(벽 접합 정리·해치·입단면 자동 생성 없음).
- 법규·시방 기준 수치는 스킬에 고정하지 않고 도구로 현행 원문을 조회하도록 설계했다.
- KCSC 원문은 재배포 허용 여부가 확인되지 않아 저장하지 않고 조회만 한다. 수식·그림은 텍스트가 없어 자리표로 표시된다.
- 조달청 가격 API의 검색 파라미터(`prdctClsfcNoNm`, `krnPrdctNm`)는 명세의 응답 필드명을 기준으로 했다. 실제 키로 첫 호출 때 확인하고, 서버가 필터를 무시해도 클라이언트에서 다시 거른다.
- 외부 MCP 실행에 Node.js(npx, korean-law)가 필요하다.
- 모든 결과는 전문가(건축사·구조기술사) 확인 대상이다.

## 변경 시

도구를 고치거나 추가하면 `plugin.json`과 `.claude-plugin/marketplace.json`의 `version`을 올린다
(서브 프로젝트가 새 버전을 받으려면 `/plugin marketplace update connect-architect`).
