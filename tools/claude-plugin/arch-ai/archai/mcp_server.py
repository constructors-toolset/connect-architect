"""arch-ai MCP 서버 — archai 도구를 MCP 도구로 노출한다 (stdio).

실행: python -m archai.mcp_server
필요 패키지: mcp, ezdxf, ifcopenshell  (requirements.txt)
환경변수: LAW_OC(법령 API), ARCHAI_BOM_DB(BOM DB 경로, 선택)
"""

from __future__ import annotations

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import bom, law, spec, structure

server = _Server(
    "arch-ai",
    instructions=(
        "건축 전문 도구: 법령 검색(law_*), DXF 도면 해석·작도(dxf_*), IFC/BIM 조회·검증·수정(ifc_*), "
        "구조 검토 계산(struct_*), BOM DB·물량·비용(bom_*), 시방서(spec_*). "
        "계산·법령 결과는 근거(조문/기준)와 함께 보고하고, 최종 판단은 전문가 검토 대상임을 밝힌다."
    ),
)


# ---------------------------------------------------------------- 법령
@server.tool()
def law_search(query: str, target: str = "law", display: int = 20) -> list[dict]:
    """국가법령정보센터 검색. target: law(법령)|admrul(행정규칙)|ordin(자치법규/조례)|prec(판례)|expc(법령해석례)"""
    return law.search(query, target, display)


@server.tool()
def law_article(law_name: str, number: str) -> list[dict]:
    """법령 조문 조회. 예: law_name='건축법', number='44' 또는 '53의2'"""
    return law.get_article(law_name, number)


@server.tool()
def law_core_list() -> list[str]:
    """건축 검토 시 기본으로 확인할 핵심 법령 목록"""
    return law.CORE_LAWS


# ---------------------------------------------------------------- 도면
@server.tool()
def dxf_inspect(path: str, include_texts: bool = False) -> dict:
    """DXF 도면 요약: 단위, 범위, 레이어별 요소/길이/폐합면적, 블록, 치수, 문자"""
    from . import dxf_tools
    return dxf_tools.inspect(path, include_texts)


@server.tool()
def dxf_draw(spec_json: dict, out_path: str) -> dict:
    """JSON 스펙(grids, walls, doors, windows, rooms, dims, title; mm)으로 평면도 DXF 작도"""
    from . import dxf_tools
    return dxf_tools.draw(spec_json, out_path)


# ---------------------------------------------------------------- BIM
@server.tool()
def ifc_summary(path: str) -> dict:
    """IFC 모델 개요: 스키마, 층, 요소 개수, 단위"""
    from . import ifc_tools
    return ifc_tools.summary(path)


@server.tool()
def ifc_elements(path: str, ifc_type: str, limit: int = 100) -> list[dict]:
    """IFC 클래스별 요소 목록(GlobalId, 이름, 타입, 층, 재료, 수량)"""
    from . import ifc_tools
    return ifc_tools.elements(path, ifc_type, limit)


@server.tool()
def ifc_element(path: str, guid: str) -> dict:
    """요소 1개의 전체 속성 세트(Pset/Qto), 재료, 타입"""
    from . import ifc_tools
    return ifc_tools.element(path, guid)


@server.tool()
def ifc_validate(path: str) -> dict:
    """BIM 품질 검토: 층 미배정, 이름/재료/수량 누락, GUID 중복, IfcSpace 부재"""
    from . import ifc_tools
    return ifc_tools.validate(path)


@server.tool()
def ifc_takeoff(path: str, out_csv: str | None = None) -> list[dict]:
    """IFC 물량 집계(클래스·타입·재료·층별). out_csv 지정 시 BOM 연계용 CSV 저장"""
    from . import ifc_tools
    return ifc_tools.takeoff(path, out_csv)


@server.tool()
def ifc_set_property(path: str, guid: str, pset: str, prop: str, value: str | float | bool, out_path: str) -> dict:
    """요소 속성값 추가/수정 후 새 IFC 파일로 저장(원본 보존)"""
    from . import ifc_tools
    return ifc_tools.set_property(path, guid, pset, prop, value, out_path)


# ---------------------------------------------------------------- 구조
@server.tool()
def struct_load_combinations(D: float = 0, L: float = 0, Lr: float = 0, S: float = 0, R: float = 0,
                             W: float = 0, E: float = 0, H: float = 0, F: float = 0, T: float = 0) -> dict:
    """KDS 41 10 15 강도설계 하중조합과 지배 조합"""
    return structure.load_combinations(D, L, Lr, S, R, W, E, H, F, T)


@server.tool()
def struct_beam(span: float, w: float = 0, P: float = 0, a: float | None = None, support: str = "simple",
                E: float = 25000, I: float | None = None) -> dict:
    """보 해석(span mm, w kN/m, P kN). support: simple|cantilever|fixed|propped. E MPa, I mm^4 입력 시 처짐"""
    return structure.beam_analysis(span, w, P, a, support, E, I)


@server.tool()
def struct_rc_beam(b: float, d: float, fck: float, fy: float, As: float, Mu: float | None = None,
                   Vu: float | None = None, Av: float = 0, s: float | None = None, fyt: float | None = None) -> dict:
    """RC 직사각형 보 휨(KDS 14 20 20)·전단(KDS 14 20 22) 검토. mm, MPa, kN, kN·m"""
    res = {"flexure": structure.rc_beam_flexure(b, d, fck, fy, As, None, Mu)}
    if Vu is not None:
        res["shear"] = structure.rc_beam_shear(b, d, fck, fyt or fy, Vu, Av, s)
    return res


@server.tool()
def struct_min_depth(member: str, span: float, support: str, fy: float = 400, h: float | None = None) -> dict:
    """처짐 미계산 시 최소두께(KDS 14 20 30). member: slab|beam, support: simple|one_end_continuous|both_ends_continuous|cantilever"""
    return structure.min_depth(member, span, support, fy, h)


# ---------------------------------------------------------------- BOM
@server.tool()
def bom_init() -> dict:
    """BOM DB 스키마 생성 + 기본 품목 적재(단가 없음)"""
    return bom.init()


@server.tool()
def bom_search(keyword: str) -> list[dict]:
    """품목 검색(코드/품명/규격/분류) + 최신 자재단가"""
    return bom.search(keyword)


@server.tool()
def bom_price_add(code: str, price: float, source: str, date: str, region: str | None = None,
                  price_type: str = "material") -> dict:
    """단가 등록. source(출처)와 date(YYYY-MM-DD)는 필수. price_type: material|labor|expense"""
    return bom.price_add(code, price, source, date, region, price_type)


@server.tool()
def bom_assembly_add(code: str, name: str, unit: str, components: list[str]) -> dict:
    """조립체(공종) 정의. components: ['CON-24:0.2', 'REB-D13:0.018:0.03'] (품목:단위당소요량[:할증률])"""
    return bom.assembly_add(code, name, unit, components)


@server.tool()
def bom_map_add(ifc_class: str, name_pattern: str, assembly_code: str, qty_field: str, priority: int = 0) -> dict:
    """IFC 타입 → 조립체 매핑 규칙. name_pattern은 SQL LIKE(예: '%RC%200%'), qty_field 예: NetSideArea"""
    return bom.map_add(ifc_class, name_pattern, assembly_code, qty_field, priority)


@server.tool()
def bom_cost(takeoff_csv: str) -> dict:
    """ifc_takeoff CSV → 품목별 소요량·재료비. 매핑 누락/단가 누락 목록 포함"""
    return bom.cost_from_takeoff(takeoff_csv)


# ---------------------------------------------------------------- 시방서
@server.tool()
def spec_skeleton(title: str, kcs: str = "KCS 00 00 00") -> str:
    """KCS 3부 구성(일반사항/자재/시공) 공사시방서 골격 Markdown"""
    return spec.skeleton(title, kcs)


@server.tool()
def spec_check(spec_path: str) -> dict:
    """시방서 교차검토: BOM 코드 존재 여부, KS/KCS 참조, 필수 절 누락, 미작성 표시"""
    return spec.check(spec_path)


def main():
    server.run()


if __name__ == "__main__":
    main()
