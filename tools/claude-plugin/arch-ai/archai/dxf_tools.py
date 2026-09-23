"""DXF 도면 해석과 평면도 작도 (ezdxf 사용).

사용법:
  python -m archai.dxf_tools inspect plan.dxf              # 요약(JSON)
  python -m archai.dxf_tools inspect plan.dxf --texts      # 문자 전체 포함
  python -m archai.dxf_tools draw spec.json out.dxf        # JSON 스펙으로 평면도 작도

DWG는 먼저 ODA File Converter 등으로 DXF로 변환한다.

draw 스펙(JSON, 단위 mm) 예시:
{
  "title": "1층 평면도", "scale": "1/100",
  "grids": {"x": [0, 6000, 12000], "y": [0, 5000], "labels_x": ["X1","X2","X3"], "labels_y": ["Y1","Y2"]},
  "walls": [{"path": [[0,0],[12000,0],[12000,5000],[0,5000],[0,0]], "thickness": 200}],
  "doors": [{"at": [3000, 0], "width": 900, "angle": 0, "swing": "in"}],
  "windows": [{"at": [9000, 0], "width": 1800, "angle": 0}],
  "rooms": [{"name": "거실", "boundary": [[0,0],[6000,0],[6000,5000],[0,5000]]}],
  "dims": [{"p1": [0,0], "p2": [6000,0], "offset": -1200}]
}
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict

import ezdxf
from ezdxf import units as dxf_units

# 건축 도면 레이어 표준 (AIA/NCS 체계 기반, 국내 실무에서 널리 쓰는 형태)
LAYERS = {
    "S-GRID": {"color": 8, "linetype": "CENTER"},
    "A-WALL": {"color": 7},
    "A-DOOR": {"color": 3},
    "A-GLAZ": {"color": 4},
    "A-AREA-IDEN": {"color": 2},
    "A-ANNO-DIMS": {"color": 1},
    "A-ANNO-TEXT": {"color": 7},
    "A-ANNO-TTLB": {"color": 7},
}

# 레이어 이름 → 분야/요소 추정 (도면 해석 보조)
LAYER_HINTS = [
    ("GRID", "통심선/그리드"), ("WALL", "벽"), ("벽", "벽"), ("COL", "기둥"), ("기둥", "기둥"),
    ("DOOR", "문"), ("문", "문"), ("WIN", "창"), ("GLAZ", "창/유리"), ("창", "창"),
    ("TTLB", "도곽"), ("DIM", "치수"), ("치수", "치수"), ("TEXT", "문자"), ("ANNO", "주석"), ("HATCH", "해치"),
    ("STAIR", "계단"), ("계단", "계단"), ("FURN", "가구"), ("EQPM", "설비기구"),
    ("SLAB", "슬래브"), ("BEAM", "보"), ("보", "보"), ("ROOM", "실명/면적"), ("AREA", "실명/면적"),
    ("ELEV", "입면"), ("SECT", "단면"), ("도곽", "도곽"),
]


def _layer_hint(name: str) -> str | None:
    up = name.upper()
    for key, hint in LAYER_HINTS:
        if key in up:
            return hint
    return None


def _poly_area(pts) -> float:
    a = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def inspect(path: str, include_texts: bool = False, max_texts: int = 200) -> dict:
    """DXF 도면을 읽어 해석에 필요한 요약을 반환한다."""
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    insunits = doc.header.get("$INSUNITS", 0)
    unit_name = dxf_units.unit_name(insunits) if insunits else "unitless"

    ent_by_layer: dict[str, Counter] = defaultdict(Counter)
    line_len: Counter = Counter()
    closed_areas: dict[str, list[float]] = defaultdict(list)
    texts, dims = [], []
    block_refs: Counter = Counter()

    for e in msp:
        layer = e.dxf.get("layer", "0")
        t = e.dxftype()
        ent_by_layer[layer][t] += 1
        if t == "LINE":
            line_len[layer] += e.dxf.start.distance(e.dxf.end)
        elif t == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            for a, b in zip(pts, pts[1:] + (pts[:1] if e.closed else [])):
                line_len[layer] += math.dist(a, b)
            if e.closed and len(pts) >= 3:
                closed_areas[layer].append(_poly_area(pts))
        elif t in ("TEXT", "MTEXT"):
            txt = e.plain_text() if t == "MTEXT" else e.dxf.text
            ins = e.dxf.insert
            texts.append({"layer": layer, "text": txt, "x": round(ins.x, 1), "y": round(ins.y, 1)})
        elif t == "DIMENSION":
            try:
                meas = e.get_measurement()
                meas = round(meas, 2) if isinstance(meas, (int, float)) else str(meas)
            except Exception:
                meas = None
            dims.append({"layer": layer, "measurement": meas, "text_override": e.dxf.get("text", "")})
        elif t == "INSERT":
            block_refs[e.dxf.name] += 1

    extmin, extmax = doc.header.get("$EXTMIN"), doc.header.get("$EXTMAX")
    layers = []
    for layer in doc.layers:
        name = layer.dxf.name
        counts = ent_by_layer.get(name, Counter())
        layers.append({
            "name": name,
            "hint": _layer_hint(name),
            "entities": dict(counts),
            "line_length": round(line_len.get(name, 0.0), 1),
            "closed_polylines": len(closed_areas.get(name, [])),
            "closed_area_sum": round(sum(closed_areas.get(name, [])), 1),
            "off": layer.is_off(),
            "frozen": layer.is_frozen(),
        })

    return {
        "file": path,
        "dxf_version": doc.dxfversion,
        "units": unit_name,
        "extents": {"min": list(extmin)[:2] if extmin else None, "max": list(extmax)[:2] if extmax else None},
        "entity_total": sum(sum(c.values()) for c in ent_by_layer.values()),
        "layers": sorted(layers, key=lambda l: -sum(l["entities"].values())),
        "blocks_used": dict(block_refs.most_common()),
        "dimensions": dims[:max_texts],
        "texts": texts if include_texts else texts[:max_texts // 4],
        "text_count": len(texts),
        "layouts": [l.name for l in doc.layouts if l.name != "Model"],
    }


# ----------------------------------------------------------------- 작도

def _setup(doc):
    for lt in ("CENTER", "DASHED", "HIDDEN"):
        if lt not in doc.linetypes:
            try:
                doc.linetypes.add(lt, pattern=[20.0, 12.0, -3.0, 2.0, -3.0] if lt == "CENTER" else [6.0, 3.0, -3.0])
            except Exception:
                pass
    for name, attrs in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, **attrs)
    if "KOR" not in doc.styles:
        doc.styles.add("KOR", font="malgun.ttf")


def _offset_segment(p1, p2, d):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * d, dx / L * d
    return (p1[0] + nx, p1[1] + ny), (p2[0] + nx, p2[1] + ny)


def draw(spec: dict, out_path: str) -> dict:
    """JSON 스펙으로 평면도(DXF, mm 단위)를 작도한다. 초안용 — 벽 접합부 정리는 하지 않는다."""
    doc = ezdxf.new("R2018", setup=True)
    doc.units = dxf_units.MM
    _setup(doc)
    msp = doc.modelspace()
    text_h = spec.get("text_height", 250)
    counts = Counter()

    grids = spec.get("grids")
    if grids:
        xs, ys = grids.get("x", []), grids.get("y", [])
        ext = 1500
        ymin, ymax = (min(ys) - ext, max(ys) + ext) if ys else (-ext, ext)
        xmin, xmax = (min(xs) - ext, max(xs) + ext) if xs else (-ext, ext)
        for i, x in enumerate(xs):
            msp.add_line((x, ymin), (x, ymax), dxfattribs={"layer": "S-GRID"})
            label = (grids.get("labels_x") or [f"X{i+1}" for i in range(len(xs))])[i]
            msp.add_circle((x, ymin - 400), 400, dxfattribs={"layer": "S-GRID"})
            msp.add_text(label, height=300, dxfattribs={"layer": "S-GRID", "style": "KOR"}).set_placement(
                (x, ymin - 400), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        for i, y in enumerate(ys):
            msp.add_line((xmin, y), (xmax, y), dxfattribs={"layer": "S-GRID"})
            label = (grids.get("labels_y") or [f"Y{i+1}" for i in range(len(ys))])[i]
            msp.add_circle((xmin - 400, y), 400, dxfattribs={"layer": "S-GRID"})
            msp.add_text(label, height=300, dxfattribs={"layer": "S-GRID", "style": "KOR"}).set_placement(
                (xmin - 400, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        counts["grids"] = len(xs) + len(ys)

    for w in spec.get("walls", []):
        t = w.get("thickness", 200) / 2
        pts = w["path"]
        for p1, p2 in zip(pts, pts[1:]):
            for d in (t, -t):
                a, b = _offset_segment(p1, p2, d)
                msp.add_line(a, b, dxfattribs={"layer": "A-WALL"})
        counts["walls"] += 1

    for d in spec.get("doors", []):
        x, y = d["at"]
        w = d.get("width", 900)
        ang = math.radians(d.get("angle", 0))
        sgn = 1 if d.get("swing", "in") == "in" else -1
        hinge = (x - w / 2 * math.cos(ang), y - w / 2 * math.sin(ang))
        leaf_end = (hinge[0] - sgn * w * math.sin(ang), hinge[1] + sgn * w * math.cos(ang))
        msp.add_line(hinge, leaf_end, dxfattribs={"layer": "A-DOOR"})
        start = math.degrees(ang)
        a0, a1 = (start, start + 90) if sgn > 0 else (start - 90, start)
        msp.add_arc(hinge, w, a0, a1, dxfattribs={"layer": "A-DOOR"})
        counts["doors"] += 1

    for win in spec.get("windows", []):
        x, y = win["at"]
        w = win.get("width", 1200)
        ang = math.radians(win.get("angle", 0))
        p1 = (x - w / 2 * math.cos(ang), y - w / 2 * math.sin(ang))
        p2 = (x + w / 2 * math.cos(ang), y + w / 2 * math.sin(ang))
        for off in (-50, 0, 50):
            a, b = _offset_segment(p1, p2, off)
            msp.add_line(a, b, dxfattribs={"layer": "A-GLAZ"})
        counts["windows"] += 1

    rooms_out = []
    for r in spec.get("rooms", []):
        pts = [tuple(p) for p in r["boundary"]]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-AREA-IDEN"})
        area_m2 = _poly_area(pts) / 1e6
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        label = f"{r['name']}\\P{area_m2:.2f}㎡"
        mt = msp.add_mtext(label, dxfattribs={"layer": "A-ANNO-TEXT", "char_height": text_h, "style": "KOR"})
        mt.set_location((cx, cy), attachment_point=5)
        rooms_out.append({"name": r["name"], "area_m2": round(area_m2, 2)})
        counts["rooms"] += 1

    for dm in spec.get("dims", []):
        dim = msp.add_aligned_dim(p1=dm["p1"], p2=dm["p2"], distance=dm.get("offset", 800),
                                  dimstyle="EZDXF", dxfattribs={"layer": "A-ANNO-DIMS"},
                                  override={"dimtxt": text_h, "dimasz": text_h * 0.8, "dimexe": 100, "dimexo": 100})
        dim.render()
        counts["dims"] += 1

    if spec.get("title"):
        ext = [p for w in spec.get("walls", []) for p in w["path"]] or [(0, 0)]
        x0 = min(p[0] for p in ext)
        y0 = min(p[1] for p in ext) - 3500
        msp.add_text(f"{spec['title']}  SCALE {spec.get('scale', '1/100')}", height=text_h * 2,
                     dxfattribs={"layer": "A-ANNO-TTLB", "style": "KOR"}).set_placement((x0, y0))

    doc.saveas(out_path)
    return {"output": out_path, "counts": dict(counts), "rooms": rooms_out}


def main(argv=None):
    p = argparse.ArgumentParser(description="DXF 도면 해석/작도")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inspect")
    i.add_argument("path")
    i.add_argument("--texts", action="store_true", help="문자 전체 출력")
    d = sub.add_parser("draw")
    d.add_argument("spec")
    d.add_argument("out")
    args = p.parse_args(argv)
    if args.cmd == "inspect":
        res = inspect(args.path, include_texts=args.texts)
    else:
        with open(args.spec, encoding="utf-8") as f:
            res = draw(json.load(f), args.out)
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    sys.exit(main())
