---
title: 건축(AEC) MCP 생태계 조사 — 무료 도구 전제 분석
created: 2026-09-23
author: ai
sources:
  - 병렬 리서치 에이전트 3개 (상용 AEC MCP 검증 / 무료·오픈소스 MCP / 국내 무료 데이터원)
  - 외부 AI가 작성한 "건축 분야 MCP 생태계" 설명문 (검증 대상)
status: review
---

# 건축(AEC) MCP 생태계 조사 — 무료 도구 전제

**전제:** 호스트 소프트웨어, API, 데이터 모두 무료로 쓸 수 있어야 한다.
MCP 서버가 오픈소스여도 유료 호스트(Revit, AutoCAD, Rhino 등)가 필요하면 제외한다.

검증 표시는 세 가지다.
- **V**: 원문 페이지나 GitHub/PyPI에서 직접 확인했다.
- **△**: 검색 요약이나 2차 자료로만 확인했다.
- **?**: 확인하지 못했다.

## 1. 외부 설명문의 주장 검증

| 주장 | 조사 결과 | 판정 |
|---|---|---|
| Autodesk 공식 Revit MCP가 있다 | 있다. 다만 **Tech Preview**이고 **Revit 2027 전용**이다. 도구는 7개로 요소 검색, 파라미터 조회와 일괄 수정, 뷰 스냅샷 정도이며 **벽·바닥 같은 요소 생성은 안 된다**. ([Autodesk Help](https://help.autodesk.com/view/ADSKMCP/ENU/)) V | 부분 사실. 설명문의 "벽/바닥/문/창 생성" 예시는 커뮤니티 MCP의 기능이다 |
| Model Data Explorer MCP | "공개 MCP를 만든다"는 언급만 찾았고, 실제로 출시됐는지는 확인하지 못했다 △ | 미확인 |
| 커뮤니티 Revit MCP로 벽·룸·시트·스케줄을 만든다 | 실제로 있다. 예: [mcp-servers-for-revit](https://github.com/mcp-servers-for-revit/mcp-servers-for-revit) ★341(MIT). 원조 저장소는 보관(archived) 상태다 V | 사실. 다만 **Revit이 유료**(약 $3,000/년)다 |
| ScanBIM MCP (Revit, ACC, Navisworks, Twinmotion 허브) | 존재한다. 그러나 ★6에 신생 프로젝트이고 클라우드(APS)를 거치는 방식이다. Revit/Navisworks 기능은 월 $149 요금제에서만 된다 V | 과장. 신뢰도가 낮다 |
| Navisworks MCP로 간섭검토를 한다 | 성숙한 전용 프로젝트는 없다 V | 과장 |
| Rhino/Grasshopper MCP | [rhinomcp](https://github.com/jingcheng-chen/rhinomcp) ★1.1k로 활발하다. Rhino는 유료($995)다 V | 사실이지만 유료 |
| 출처 "ChatForest" | AI가 문서를 분석해 만드는 리뷰 사이트다. **직접 설치해 테스트하지 않는다**고 스스로 밝히고, 운영자도 공개하지 않는다 V | 1차 출처가 아니다 |
| "MCP 6개 + Agent" 구조가 좋다 | 방향이 타당하다. 현재 arch-ai 플러그인 구조와 같은 방향이다 | 채택 |

**결론:** 설명문 1·2·5장에 나온 상용 MCP(Revit, AutoCAD, Navisworks, Tekla, ETABS, Archicad, Rhino, Procore, ACC)는 무료 전제에서 모두 제외된다.
무료로 쓸 수 있는 예외는 두 가지다.
- Autodesk Product Help MCP: 문서 검색만 한다.
- ezdxf를 백엔드로 쓰는 AutoCAD 계열 MCP: AutoCAD 없이 DXF를 다룬다.
  - [puran-water/autocad-mcp](https://github.com/puran-water/autocad-mcp) ★530, MIT
  - [U-C4N/Autocad-MCP](https://github.com/U-C4N/Autocad-MCP) ★98, MIT

## 2. 무료 대안 MCP·도구

| 분야 | 후보 | 호스트·라이선스 | 활동 | 적합도 | 검증 |
|---|---|---|---|---|---|
| IFC | **IfcMCP**: IfcOpenShell 공식. 조회, 편집, 검증, **간섭검토(ifc_clash)**, 렌더링 ([docs](https://docs.ifcopenshell.org/ifcmcp.html), [PyPI ifcopenshell-mcp](https://pypi.org/project/ifcopenshell-mcp/)) | Python, LGPL-3.0 | 0.8.5 (2026-04) | 상 | V (설치명 `ifcmcp`와 PyPI명 `ifcopenshell-mcp`가 달라 설치 전 확인 필요) |
| IFC 규칙검증 | **ifc-ids-mcp**: IfcTester 기반으로 IDS를 생성하고 검증 ([GitHub](https://github.com/vinnividivicci/ifc-ids-mcp)) | Python, MIT | ★27 | 상 | V |
| BIM 저작 | **Bonsai_mcp**: Blender와 Bonsai로 IFC를 수정하고 물량·BOM을 내보냄 ([GitHub](https://github.com/JotaDeRodriguez/Bonsai_mcp)) | Blender(무료), MIT | ★64 | 상 | V |
| BIM 저작 | ifc-bonsai-mcp (도구 50개 이상, 후속 bonsai-mcp) ([GitHub](https://github.com/Show2Instruct/ifc-bonsai-mcp)) | Blender, MIT | ★63 | 중~상 | V |
| CAD·FEM | **freecad-mcp**: 모델링과 FEM 해석 ([GitHub](https://github.com/neka-nat/freecad-mcp)) | FreeCAD(무료), MIT | ★2.5k | 상 | V |
| 구조해석 | **PyNite**: 3D 프레임 FEA ([PyPI](https://pypi.org/project/PyNiteFEA/)) | MIT | 3.2.0 (2026-09) | 상 (자체 MCP 도구로 래핑) | V |
| 구조해석 | anaStruct (2D 골조) | GPL-3.0 | 1.7.0 | 중 | V |
| 구조해석 | OpenSeesPy | **비상업·내부용만 무료** | 3.8.0 | 주의 | V |
| DWG | **LibreDWG** dwg2dxf | GPLv3 | – | 상 | △ |
| DWG | ODA File Converter | "60일 체험" 표기가 있어 계속 무료인지 불명 | – | 보류 | △ |
| 문서·PDF | **docling-mcp**: 레이아웃·표 인식, OCR ([GitHub](https://github.com/docling-project/docling-mcp)) | MIT | ★749, 3.2.0 | 상 (시방서·도면 PDF) | V |
| 에너지 | EnergyPlus-MCP (LBNL), openstudio-mcp, ladybug-tools-mcp (Rhino 불필요) | 무료. 앞의 둘은 Docker 필요 | – | 중 (나중에) | V |
| 간섭검토 | BIMcollab Zoom | 간섭검토가 유료(연 €225) | – | 제외 | △ |

## 3. 국내 무료 데이터원

| 데이터 | 접근 | 비용·조건 | 검증 |
|---|---|---|---|
| 법령·자치법규·해석례·판례 | law.go.kr DRF API (`target=ordin` 포함) | 무료, OC 등록 | V |
| 기존 법령 MCP | [chrisryugj/korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp) | MIT, ★약 2.6k, API 42개를 도구 10개로 묶음 | V |
| KDS 설계기준·KCS 표준시방서 + LHCS·SMCS 등 전문시방서 | 국가건설기준센터 Open API (`/OpenApi/CodeList`, `/OpenApi/CodeViewer`) | 인증키 필요. 비용 ?(무료 추정). **원문 저장·재배포 허용 여부 ?**. 수식은 이미지로 옴 | V(API) / ?(라이선스) |
| 조달청 시방서(GUIDE 시방서 60공종) | pps.go.kr 게시판 파일 | API 없음, 수작업 수집 | △ |
| KS 표준 원문 | e-나라표준인증 | **열람만 무료**. 다운로드는 유료, API 없음 | △ |
| 조달청 가격정보 (시설공통자재, 시장시공가격, 표준시장단가) | data.go.kr 15129415 REST | **무료**, 자동승인, 이용 제한 없음, 연 2회 갱신 | V |
| 표준품셈·표준시장단가 원문 | KICT, 대한건설협회 PDF | API 없음, 재사용 조건 ? | △ |
| 시중 물가지 (물가자료 등) | 상업 서비스 | **유료** | △ |
| 건축물대장·인허가·건물에너지 (건축HUB) | data.go.kr | 무료, 이용 제한 없음 | V |
| 토지이용계획 (용도지역·지구) | data.go.kr 15123973 (WMS/WFS), VWorld 키 | 무료 | V |
| 자재 성능 DB (열관류율, 인증자재) | 공개 API를 찾지 못함 | – | ? |

## 4. 외부 설명문의 "MCP 6개" 구조 판정

| MCP | 무료로 구축 가능? | 현재 arch-ai 대비 조치 |
|---|---|---|
| ① 법규 | **완결 가능** | 보유 중(`law_*`). korean-law-mcp 병용을 검토할 것. 토지이용계획·건축물대장 API 도구를 추가할 것 |
| ② 표준시방서 | **대부분 가능** | 신규로 KCSC API 조회 도구를 만든다. 라이선스를 확인하기 전까지는 조회만 하고 원문을 저장·재배포하지 않는다 |
| ③ 프로젝트 문서 | 가능 | docling-mcp를 도입한다 |
| ④ BIM | 가능 | IfcMCP(검증·간섭)와 ifc-ids-mcp를 도입한다. 기존 `ifc_*`는 BOM 연계용으로 유지한다. 저작이 필요하면 Bonsai_mcp를 쓴다 |
| ⑤ 자재·공법 DB | **부분 가능, 공백이 크다** | 조달청 가격정보 API로 BOM 단가를 채운다. KS 원문, 시중 물가, 자재 성능 DB는 공백이다 |
| ⑥ 시방서 생성 | 조건부 가능 | ②와 ⑤에 의존한다. KS는 번호와 명칭만 인용한다. 문장마다 근거(KCS 절, 법령 조문, BIM 요소, BOM 코드)를 추적한다 |
| (추가) 구조 | 가능 | PyNite 프레임 해석을 래핑한다. FEM이 필요하면 freecad-mcp를 쓴다 |
| (추가) DWG | 가능 | LibreDWG로 변환한 뒤 기존 ezdxf 도구로 처리한다 |

## 5. 남은 확인 사항

1. KCSC Open API 이용약관: 비용, 캐시·RAG 인덱싱 허용 여부. 확인 전에는 조회 전용으로 운영한다.
2. IfcMCP의 정확한 설치 패키지 이름.
3. 표준품셈 PDF의 재사용 조건.
4. ODA File Converter를 계속 무료로 쓸 수 있는지.
5. MCP 클라이언트(LLM)는 무료 전제의 범위 밖이다. 도구와 데이터만 무료 전제에 해당한다.
