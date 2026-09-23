---
name: arch-bim-ifc
description: BIM 모델(IFC 2x3/IFC4)을 읽고 구조(프로젝트-대지-건물-층-요소)·속성(Pset/Qto)·재료·타입을 해석하며, 모델 품질을 검증하고 속성을 수정하며 물량을 추출한다. IFC 파일 분석, BIM 데이터 검증, 모델 수정, BIM 기반 물량산출/법규·구조 대조 요청에 사용한다. (Revit RVT 등 원본 포맷은 IFC로 내보낸 뒤 사용)
---

# BIM(IFC) 읽기·해석·수정

## 도구

| 목적 | MCP | CLI (`archai ifc ...`) |
|---|---|---|
| 모델 개요 (스키마, 단위, 층, 요소 수) | `ifc_summary(path)` | `summary model.ifc` |
| 클래스별 요소 목록 | `ifc_elements(path, "IfcWall")` | `elements model.ifc IfcWall` |
| 요소 상세 (전체 Pset/Qto) | `ifc_element(path, guid)` | `element model.ifc <GUID>` |
| 품질 검증 | `ifc_validate(path)` | `validate model.ifc` |
| 물량 집계 → CSV | `ifc_takeoff(path, out_csv)` | `takeoff model.ifc out.csv` |
| 속성 수정 (새 파일로 저장) | `ifc_set_property(path, guid, pset, prop, value, out)` | `set-prop ...` |

### IfcOpenShell 공식 MCP (`ifc-openshell` 서버) — 함께 설치됨

모델을 메모리에 올려 두고 여러 번 조회·편집할 때, 그리고 아래 기능이 필요할 때 쓴다.
| 기능 | 도구 |
|---|---|
| 로드/저장/신규 | `ifc_load(path)`, `ifc_save`, `ifc_new` |
| 구조·관계 탐색 | `ifc_tree`, `ifc_select`(선택자 쿼리), `ifc_relations`, `ifc_info` |
| **간섭검토** | `ifc_clash` |
| 스키마 검증 | `ifc_validate` (공식 서버 쪽 — 스키마·규칙 검증) |
| 편집 (ifcopenshell.api) | `ifc_docs`로 API 확인 → `ifc_edit` |
| 수량 계산 | `ifc_quantify` (Qto 없는 모델에 수량 생성) |
| 형상·도면 | `ifc_shape`, `ifc_plot`(2D 도면), `ifc_render` |
| 공정·비용 | `ifc_schedule`, `ifc_cost` |

두 서버에 같은 이름의 도구가 있다(`ifc_summary`, `ifc_validate`). **arch-ai 쪽은 파일 경로를 받아 한 번에 답하고(BIM 품질 체크리스트·BOM 연계용 takeoff), ifc-openshell 쪽은 `ifc_load` 후 세션으로 작업한다.**
Qto가 없는 모델은 `ifc_quantify` → `ifc_save`로 수량을 채운 새 파일을 만든 뒤 arch-ai `ifc_takeoff`로 BOM에 넘긴다.

그래도 안 되는 작업은 ifcopenshell API로 스크립트를 쓴다:
```python
import ifcopenshell, ifcopenshell.api as api
m = ifcopenshell.open("in.ifc")
api.run("attribute.edit_attributes", m, product=m.by_guid(g), attributes={"Name": "W-201"})
api.run("spatial.assign_container", m, relating_structure=storey, products=[el])
m.write("out.ifc")  # 원본은 절대 덮어쓰지 않는다
```
형상 계산(면적·체적을 Qto 없이 직접 계산)은 `ifcopenshell.geom` + `ifcopenshell.util.shape`를 쓴다.

## 해석 절차

1. `ifc_summary` → 스키마(IFC2X3/IFC4), **길이 단위**(mm/m), 층 구성, 요소 분포를 파악한다.
2. `ifc_validate` → 품질 문제를 먼저 본다. 품질이 낮으면 이후 물량·법규 대조 결과를 신뢰할 수 없다고 보고한다.
3. 목적별로 요소를 조회한다(아래 표).
4. 도면·구조계산서·시방서와 대조한다(arch-expert-team 교차 검토표).

## 목적별 조회 요령

| 목적 | 볼 것 |
|---|---|
| 면적·실 구성 | IfcSpace + Qto_SpaceBaseQuantities(NetFloorArea), Pset_SpaceCommon |
| 방화·피난 | Pset_WallCommon.FireRating, Pset_DoorCommon.FireRating/FireExit, IsExternal |
| 단열·에너지 | Pset_WallCommon.ThermalTransmittance, 재료 레이어(IfcMaterialLayerSet) 두께 |
| 구조 | IfcBeam/IfcColumn/IfcSlab의 LoadBearing, 재료명(강도), 프로파일(IfcProfileDef) |
| 물량 | Qto_*BaseQuantities (Wall: NetSideArea/NetVolume, Slab: NetArea/NetVolume, Beam/Column: Length/NetVolume) |
| 분류 코드 | IfcClassificationReference (Uniclass, OmniClass, 조달청 분류 등) |

## 품질 기준 (BIM 납품 검토 관점)

- 모든 건축 요소가 층(IfcBuildingStorey)에 배정되어 있다.
- 주요 구조·외피 요소에 재료가 있다. 이름·타입 명명 규칙이 일관된다.
- 벽 `IsExternal`, 문 `FireRating` 등 법규 검토 필수 속성이 채워져 있다.
- IfcSpace가 있고 실명·면적이 도면 면적표와 일치한다.
- Qto가 있다(없으면 물량은 형상 계산으로 대체하고 그 사실을 적는다).
- GUID가 중복되지 않는다.
- 국내 발주처 BIM 적용 지침(조달청 시설사업 BIM 적용 기본지침서, 국토부 건축 BIM 활용 가이드 등) 요구 속성이 있으면 추가 확인.

## 수정 작업 원칙

- 원본 IFC는 절대 덮어쓰지 않는다. 수정본은 `<원본>-rev<N>.ifc`로 저장하고 변경 목록(GUID, 속성, 이전값→새값)을 남긴다.
- 대량 수정 전에 한두 요소로 시험하고 결과를 `ifc_element`로 확인한다.
- 수정한 IFC는 저작도구(Revit 등)로 다시 가져갈 때 손실이 있을 수 있음을 알린다.
