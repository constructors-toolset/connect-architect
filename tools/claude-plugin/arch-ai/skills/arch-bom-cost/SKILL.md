---
name: arch-bom-cost
description: 건축 자재·품목 BOM 데이터베이스(SQLite)를 수집·구축하고, 공종 조립체(벽체·바닥 타입 등)와 단가(출처 포함)를 관리하며, BIM/도면 물량을 BOM에 연결해 소요량과 재료비를 산출하고 시방서와 연계한다. BOM 구성, 자재 DB 구축, 물량산출, 개략 공사비, 도면·시방서에 자재 적용 요청에 사용한다.
---

# 건축 BOM 데이터베이스와 물량·비용

## 데이터 모델

```
items(품목) ──< prices(단가 이력: 출처·일자·지역 필수)
   │
   ├──< assembly_items >── assemblies(조립체: 예 W1 = RC벽 200, 단위 m²)
   │                          ▲
   │                    mappings(IFC 클래스 + 타입명 패턴 → 조립체, 수량 필드)
   └──< spec_links(품목 ↔ 시방서 절)
```
- **품목(items)**: code(예: `CON-24`), 품명, 규격, 단위, 분류, kcs_ref.
- **조립체(assemblies)**: 도면의 벽체·바닥·지붕·천장 타입을 품목 조합으로 표현. 단위수량당 소요량 + 할증률.
- **매핑(mappings)**: BIM 요소를 조립체로 바꾸는 규칙. 예: `IfcWall` + `%RC%200%` → `W1`, 수량 필드 `NetSideArea`.

DB 경로: `ARCHAI_BOM_DB` 환경변수, 없으면 `./data/processed/bom/arch-bom.sqlite`.

## 도구

| 목적 | MCP | CLI (`archai bom ...`) |
|---|---|---|
| DB 생성 + 기본 품목 | `bom_init()` | `init` |
| CSV 적재 | — | `import file.csv --table items` |
| 품목 검색 | `bom_search(keyword)` | `search 단열` |
| 단가 등록 | `bom_price_add(code, price, source, date)` | `price-add CON-24 98000 --source ... --date ...` |
| 조립체 정의 | `bom_assembly_add(code, name, unit, ["CON-24:0.2:0.02", ...])` | `assembly-add ...` |
| 매핑 규칙 | `bom_map_add(ifc_class, pattern, assembly, qty_field)` | `map-add ...` |
| 물량 → BOM·재료비 | `ifc_takeoff` → `bom_cost(takeoff_csv)` | `cost takeoff.csv` |

## 데이터 수집 원칙 (중요)

- **단가를 만들어내지 않는다.** 단가는 반드시 출처(source)와 기준일(price_date)이 있는 값만 넣는다.
  수집 출처 예: 조달청 가격정보(나라장터 가격정보), 표준시장단가·표준품셈(국토교통부 고시), 물가정보지(물가자료·거래가격), 견적서.
  출처를 확인할 수 없는 값은 넣지 말고 "단가 없음"으로 남긴다.
- 원본 수집 파일은 `data/raw/`(수정 금지), 정제한 CSV는 `data/processed/bom/`, AI가 만든 매핑·조립체 초안은 `data/generated/bom/`(+`.meta.md`).
- 소요량(단위당 수량)과 할증률은 표준품셈 등 근거를 note에 남긴다. 근거 없는 가정값이면 "가정"으로 표시한다.
- 기본 품목(seed)의 `kcs_ref`는 출발점 예시다. 시방서에 연결하기 전에 현행 KCS 코드를 확인한다.

## 작업 절차

1. **DB 준비**: `bom_init` (처음 한 번).
2. **품목·단가 수집**: 출처별 CSV로 정리 → `import`. 단가는 `prices` 테이블에 출처와 함께.
3. **조립체 정의**: 도면 벽체·바닥 타입 상세(arch-drawing-read)를 보고 층별 구성 재료 × 두께/소요량으로 조립체를 만든다.
   예) RC벽 200: 콘크리트 0.2 m³/m² (+할증), 철근 t/m², 거푸집 2.0 m²/m²(양면).
4. **매핑**: BIM 타입명·재료명 패턴으로 조립체를 연결한다.
5. **산출**: `ifc_takeoff` → `bom_cost`. 결과의 `unmapped_rows`, `items_without_price`는 반드시 보고한다.
6. **시방서 연계**: 품목 ↔ 시방서 절을 `spec_links`에 기록하고, 시방서 자재 표에 BOM 코드를 적는다(arch-specification).
7. **도면 연계**: 도면 마감표·일람표의 재료 표기 옆에 BOM 코드를 붙이는 표를 만든다.

## 보고 형식

| 코드 | 품명 | 규격 | 단위 | 수량 | 단가 (출처, 기준일) | 금액 | 산출 근거 |
|---|---|---|---|---|---|---|---|

맨 아래에 **제외 사항**(노무비·경비·간접비·부가세 미포함, 단가 없는 품목, 매핑 안 된 요소)을 적는다.
이 결과는 개략 재료비이며 공식 내역서(표준품셈·일위대가 기반 적산)를 대체하지 않는다.
