"""IFC(BIM) 모델 조회·검증·수정·물량 추출 (ifcopenshell 사용).

사용법:
  python -m archai.ifc_tools summary model.ifc
  python -m archai.ifc_tools elements model.ifc IfcWall [--limit 50]
  python -m archai.ifc_tools element model.ifc <GlobalId>
  python -m archai.ifc_tools validate model.ifc
  python -m archai.ifc_tools takeoff model.ifc takeoff.csv
  python -m archai.ifc_tools set-prop model.ifc <GlobalId> Pset_WallCommon FireRating 2HR out.ifc

수정 명령은 항상 새 파일(out)로 저장하며 원본을 덮어쓰지 않는다.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict

import ifcopenshell
import ifcopenshell.util.element as uel

BUILDING_TYPES = [
    "IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcFooting", "IfcPile", "IfcRoof",
    "IfcStair", "IfcStairFlight", "IfcRamp", "IfcRailing", "IfcDoor", "IfcWindow",
    "IfcCurtainWall", "IfcPlate", "IfcMember", "IfcCovering", "IfcSpace",
    "IfcBuildingElementProxy", "IfcFurnishingElement", "IfcFlowTerminal", "IfcFlowSegment",
]

# 물량 추출 시 요소별 우선 수량 (Qto 기본 수량 세트 이름)
QTO_KEYS = {
    "IfcWall": ["NetSideArea", "GrossSideArea", "NetVolume", "GrossVolume", "Length"],
    "IfcSlab": ["NetArea", "GrossArea", "NetVolume", "GrossVolume"],
    "IfcBeam": ["Length", "NetVolume", "GrossVolume"],
    "IfcColumn": ["Length", "NetVolume", "GrossVolume"],
    "IfcFooting": ["NetVolume", "GrossVolume"],
    "IfcDoor": ["Area", "Width", "Height"],
    "IfcWindow": ["Area", "Width", "Height"],
    "IfcCovering": ["NetArea", "GrossArea"],
    "IfcSpace": ["NetFloorArea", "GrossFloorArea", "NetVolume"],
    "IfcRoof": ["NetArea", "GrossArea"],
}


def open_model(path: str):
    return ifcopenshell.open(path)


def _storey(el):
    c = uel.get_container(el)
    while c is not None and not c.is_a("IfcBuildingStorey"):
        c = uel.get_container(c) if hasattr(c, "ContainedInStructure") else None
    return c.Name if c is not None else None


def _materials(el) -> list[str]:
    mat = uel.get_material(el, should_skip_usage=True)
    if mat is None:
        return []
    if mat.is_a("IfcMaterial"):
        return [mat.Name]
    names = []
    for attr in ("MaterialLayers", "MaterialConstituents", "MaterialProfiles", "Materials"):
        for item in getattr(mat, attr, None) or []:
            m = getattr(item, "Material", item)
            if m is not None and getattr(m, "Name", None):
                thick = getattr(item, "LayerThickness", None)
                names.append(f"{m.Name}({thick:g})" if thick else m.Name)
    return names


def _quantities(el) -> dict:
    out = {}
    for qset, vals in uel.get_psets(el, qtos_only=True).items():
        for k, v in vals.items():
            if k != "id" and isinstance(v, (int, float)):
                out[k] = v
    return out


def summary(path: str) -> dict:
    m = open_model(path)
    project = m.by_type("IfcProject")
    storeys = sorted(m.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation or 0)
    counts = {t: len(m.by_type(t)) for t in BUILDING_TYPES}
    unit = None
    for u in m.by_type("IfcSIUnit"):
        if u.UnitType == "LENGTHUNIT":
            unit = f"{u.Prefix or ''}{u.Name}"
    return {
        "file": path,
        "schema": m.schema,
        "project": project[0].Name if project else None,
        "length_unit": unit,
        "sites": [s.Name for s in m.by_type("IfcSite")],
        "buildings": [b.Name for b in m.by_type("IfcBuilding")],
        "storeys": [{"name": s.Name, "elevation": s.Elevation,
                     "elements": len(uel.get_decomposition(s))} for s in storeys],
        "element_counts": {k: v for k, v in counts.items() if v},
        "type_objects": len(m.by_type("IfcTypeObject")),
        "total_products": len(m.by_type("IfcProduct")),
    }


def elements(path: str, ifc_type: str, limit: int = 100) -> list[dict]:
    m = open_model(path)
    out = []
    for el in m.by_type(ifc_type)[:limit]:
        t = uel.get_type(el)
        out.append({
            "GlobalId": el.GlobalId,
            "Name": el.Name,
            "type": el.is_a(),
            "type_name": t.Name if t else None,
            "storey": _storey(el),
            "materials": _materials(el),
            "quantities": _quantities(el),
        })
    return out


def element(path: str, guid: str) -> dict:
    m = open_model(path)
    el = m.by_guid(guid)
    t = uel.get_type(el)
    return {
        "GlobalId": el.GlobalId,
        "class": el.is_a(),
        "Name": el.Name,
        "Description": getattr(el, "Description", None),
        "ObjectType": getattr(el, "ObjectType", None),
        "PredefinedType": getattr(el, "PredefinedType", None),
        "type": {"class": t.is_a(), "Name": t.Name} if t else None,
        "storey": _storey(el),
        "materials": _materials(el),
        "psets": {k: {kk: vv for kk, vv in v.items() if kk != "id"} for k, v in uel.get_psets(el).items()},
    }


def validate(path: str) -> dict:
    """BIM 품질 기본 검토: 층 미배정, 재료 누락, 이름 누락, GUID 중복, 수량 누락, 공간 누락."""
    m = open_model(path)
    issues = defaultdict(list)
    guids = Counter(p.GlobalId for p in m.by_type("IfcRoot"))
    for g, c in guids.items():
        if c > 1:
            issues["duplicate_guid"].append(g)
    for t in BUILDING_TYPES:
        if t in ("IfcSpace",):
            continue
        for el in m.by_type(t):
            ref = f"{el.is_a()} {el.GlobalId} '{el.Name}'"
            if _storey(el) is None:
                issues["no_storey"].append(ref)
            if not el.Name:
                issues["no_name"].append(ref)
            if t in QTO_KEYS and not _quantities(el):
                issues["no_quantities"].append(ref)
            if t in ("IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcFooting") and not _materials(el):
                issues["no_material"].append(ref)
    if not m.by_type("IfcSpace"):
        issues["no_spaces"].append("모델에 IfcSpace가 없음 (실 면적·용도 검토 불가)")
    for w in m.by_type("IfcWall"):
        ps = uel.get_psets(w).get("Pset_WallCommon", {})
        if "IsExternal" not in ps:
            issues["wall_isexternal_missing"].append(f"{w.GlobalId} '{w.Name}'")
    return {
        "file": path,
        "issue_counts": {k: len(v) for k, v in issues.items()},
        "issues": {k: v[:50] for k, v in issues.items()},
    }


def takeoff(path: str, out_csv: str | None = None) -> list[dict]:
    """요소별 수량을 (타입, 이름, 재료) 단위로 집계한다. BOM 연계 입력으로 사용."""
    m = open_model(path)
    rows = defaultdict(lambda: {"count": 0, "qty": defaultdict(float)})
    for t, keys in QTO_KEYS.items():
        for el in m.by_type(t):
            ty = uel.get_type(el)
            key = (el.is_a(), ty.Name if ty else (el.ObjectType or el.Name or ""), " / ".join(_materials(el)),
                   _storey(el) or "")
            r = rows[key]
            r["count"] += 1
            q = _quantities(el)
            for k in keys:
                if k in q:
                    r["qty"][k] += q[k]
    out = []
    for (cls, tname, mats, storey), r in sorted(rows.items()):
        out.append({"ifc_class": cls, "type_name": tname, "materials": mats, "storey": storey,
                    "count": r["count"], **{k: round(v, 4) for k, v in r["qty"].items()}})
    if out_csv:
        head = ["ifc_class", "type_name", "materials", "storey", "count"]
        fields = head + sorted({k for row in out for k in row} - set(head))
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(out)
    return out


def set_property(path: str, guid: str, pset: str, prop: str, value, out_path: str) -> dict:
    """요소의 속성 세트 값을 추가/수정하여 새 파일로 저장한다."""
    import ifcopenshell.api
    if out_path == path:
        raise ValueError("원본 보호: out_path는 입력 파일과 달라야 합니다")
    m = open_model(path)
    el = m.by_guid(guid)
    existing = uel.get_psets(el).get(pset)
    if existing:
        ps = m.by_id(existing["id"])
    else:
        ps = ifcopenshell.api.run("pset.add_pset", m, product=el, name=pset)
    ifcopenshell.api.run("pset.edit_pset", m, pset=ps, properties={prop: value})
    m.write(out_path)
    return {"output": out_path, "GlobalId": guid, "pset": pset, prop: value}


def main(argv=None):
    p = argparse.ArgumentParser(description="IFC(BIM) 도구")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary"); s.add_argument("path")
    e = sub.add_parser("elements"); e.add_argument("path"); e.add_argument("ifc_type"); e.add_argument("--limit", type=int, default=100)
    g = sub.add_parser("element"); g.add_argument("path"); g.add_argument("guid")
    v = sub.add_parser("validate"); v.add_argument("path")
    t = sub.add_parser("takeoff"); t.add_argument("path"); t.add_argument("out_csv", nargs="?")
    sp = sub.add_parser("set-prop")
    for a in ("path", "guid", "pset", "prop", "value", "out"):
        sp.add_argument(a)
    args = p.parse_args(argv)
    if args.cmd == "summary":
        res = summary(args.path)
    elif args.cmd == "elements":
        res = elements(args.path, args.ifc_type, args.limit)
    elif args.cmd == "element":
        res = element(args.path, args.guid)
    elif args.cmd == "validate":
        res = validate(args.path)
    elif args.cmd == "takeoff":
        res = takeoff(args.path, args.out_csv)
    else:
        val = args.value
        try:
            val = json.loads(val)
        except json.JSONDecodeError:
            pass
        res = set_property(args.path, args.guid, args.pset, args.prop, val, args.out)
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    sys.exit(main())
