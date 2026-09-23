"""건축 BOM(자재·단가·조립체) SQLite 데이터베이스 구축과 도면/BIM/시방서 연계.

DB 위치: 환경변수 ARCHAI_BOM_DB, 없으면 ./data/processed/bom/arch-bom.sqlite

스키마:
  items        자재/품목 마스터 (code, name, spec, unit, category, kcs_ref)
  prices       단가 이력 (item_code, unit_price, source, region, price_date) — 출처 필수
  assemblies   조립체(공종) 정의: 벽체 타입 W1 = 여러 품목 × 소요량/단위면적
  assembly_items
  mappings     IFC 클래스/타입명 패턴 → 조립체 코드 (BIM 물량 → BOM 변환 규칙)
  spec_links   품목 ↔ 시방서 절(KCS 코드/프로젝트 시방서 절 번호)

사용법:
  python -m archai.bom init                                    # 스키마 + 기본 품목(단가 없음) 적재
  python -m archai.bom import items.csv --table items          # CSV 적재 (헤더 = 컬럼명)
  python -m archai.bom search 콘크리트
  python -m archai.bom price-add CON-24 98000 --source "조달청 가격정보" --date 2026-09-01
  python -m archai.bom assembly-add W1 "철근콘크리트 벽 200" m2 CON-24:0.2 REB-D13:0.018 FRM-EURO:2.0
  python -m archai.bom map-add IfcWall "%RC%200%" W1 --qty NetSideArea
  python -m archai.bom cost takeoff.csv                        # ifc_tools takeoff 결과로 BOM/비용 산출
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

SEED = Path(__file__).parent / "seed" / "items.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, spec TEXT, unit TEXT NOT NULL,
  category TEXT, kcs_ref TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_code TEXT NOT NULL REFERENCES items(code),
  unit_price REAL NOT NULL, currency TEXT DEFAULT 'KRW', price_type TEXT DEFAULT 'material',
  source TEXT NOT NULL, region TEXT, price_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assemblies (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, unit TEXT NOT NULL, description TEXT
);
CREATE TABLE IF NOT EXISTS assembly_items (
  assembly_code TEXT NOT NULL REFERENCES assemblies(code), item_code TEXT NOT NULL REFERENCES items(code),
  qty_per_unit REAL NOT NULL, loss_rate REAL DEFAULT 0, PRIMARY KEY (assembly_code, item_code)
);
CREATE TABLE IF NOT EXISTS mappings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ifc_class TEXT NOT NULL, name_pattern TEXT DEFAULT '%',
  assembly_code TEXT NOT NULL REFERENCES assemblies(code), qty_field TEXT NOT NULL, priority INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS spec_links (
  item_code TEXT NOT NULL REFERENCES items(code), spec_ref TEXT NOT NULL, section_title TEXT,
  PRIMARY KEY (item_code, spec_ref)
);
CREATE VIEW IF NOT EXISTS latest_prices AS
  SELECT p.* FROM prices p
  JOIN (SELECT item_code, price_type, MAX(price_date) d FROM prices GROUP BY item_code, price_type) x
    ON p.item_code = x.item_code AND p.price_type = x.price_type AND p.price_date = x.d;
"""


def db_path() -> str:
    return os.environ.get("ARCHAI_BOM_DB", "data/processed/bom/arch-bom.sqlite")


def connect(path: str | None = None) -> sqlite3.Connection:
    path = path or db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init(path: str | None = None, seed: bool = True) -> dict:
    con = connect(path)
    con.executescript(SCHEMA)
    n = 0
    if seed and SEED.exists():
        n = import_csv(str(SEED), "items", con=con)
    con.commit()
    return {"db": path or db_path(), "seeded_items": n}


def import_csv(csv_path: str, table: str, con: sqlite3.Connection | None = None) -> int:
    own = con is None
    con = con or connect()
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0
    cols = list(rows[0].keys())
    sql = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
    con.executemany(sql, [[r[c] if r[c] != "" else None for c in cols] for r in rows])
    if own:
        con.commit()
    return len(rows)


def search(keyword: str, limit: int = 50) -> list[dict]:
    con = connect()
    q = f"%{keyword}%"
    rows = con.execute(
        """SELECT i.*, lp.unit_price, lp.source, lp.price_date FROM items i
           LEFT JOIN latest_prices lp ON lp.item_code = i.code AND lp.price_type = 'material'
           WHERE i.code LIKE ? OR i.name LIKE ? OR i.spec LIKE ? OR i.category LIKE ? LIMIT ?""",
        (q, q, q, q, limit)).fetchall()
    return [dict(r) for r in rows]


def price_add(code: str, price: float, source: str, date: str, region: str | None = None,
              price_type: str = "material") -> dict:
    con = connect()
    con.execute("INSERT INTO prices (item_code, unit_price, source, price_date, region, price_type) VALUES (?,?,?,?,?,?)",
                (code, price, source, date, region, price_type))
    con.commit()
    return {"item_code": code, "unit_price": price, "source": source, "price_date": date}


def assembly_add(code: str, name: str, unit: str, components: list[str], description: str = "") -> dict:
    """components: ['ITEM:qty' 또는 'ITEM:qty:loss_rate']"""
    con = connect()
    con.execute("INSERT OR REPLACE INTO assemblies VALUES (?,?,?,?)", (code, name, unit, description))
    con.execute("DELETE FROM assembly_items WHERE assembly_code = ?", (code,))
    for comp in components:
        parts = comp.split(":")
        loss = float(parts[2]) if len(parts) > 2 else 0.0
        con.execute("INSERT INTO assembly_items VALUES (?,?,?,?)", (code, parts[0], float(parts[1]), loss))
    con.commit()
    return {"assembly": code, "components": len(components)}


def map_add(ifc_class: str, name_pattern: str, assembly_code: str, qty_field: str, priority: int = 0) -> dict:
    con = connect()
    con.execute("INSERT INTO mappings (ifc_class, name_pattern, assembly_code, qty_field, priority) VALUES (?,?,?,?,?)",
                (ifc_class, name_pattern, assembly_code, qty_field, priority))
    con.commit()
    return {"ifc_class": ifc_class, "name_pattern": name_pattern, "assembly": assembly_code, "qty_field": qty_field}


def cost_from_takeoff(takeoff_csv: str) -> dict:
    """ifc_tools.takeoff CSV → 조립체 매핑 → 품목별 소요량/금액. 매핑·단가 누락은 별도 보고."""
    con = connect()
    with open(takeoff_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    bom: dict[str, dict] = {}
    unmapped, no_price = [], set()
    for r in rows:
        label = f"{r['type_name']} {r.get('materials', '')}"
        m = con.execute(
            """SELECT * FROM mappings WHERE ifc_class = ? AND ? LIKE name_pattern
               ORDER BY priority DESC, LENGTH(name_pattern) DESC LIMIT 1""",
            (r["ifc_class"], label)).fetchone()
        if not m:
            unmapped.append({"ifc_class": r["ifc_class"], "type_name": r["type_name"], "materials": r.get("materials")})
            continue
        qty = float(r.get(m["qty_field"]) or 0)
        for ai in con.execute("SELECT * FROM assembly_items WHERE assembly_code = ?", (m["assembly_code"],)):
            need = qty * ai["qty_per_unit"] * (1 + (ai["loss_rate"] or 0))
            it = con.execute("SELECT * FROM items WHERE code = ?", (ai["item_code"],)).fetchone()
            pr = con.execute("SELECT unit_price, source, price_date FROM latest_prices WHERE item_code = ? AND price_type='material'",
                             (ai["item_code"],)).fetchone()
            e = bom.setdefault(ai["item_code"], {"code": it["code"], "name": it["name"], "spec": it["spec"],
                                                 "unit": it["unit"], "qty": 0.0, "unit_price": None,
                                                 "price_source": None, "kcs_ref": it["kcs_ref"]})
            e["qty"] += need
            if pr:
                e["unit_price"], e["price_source"] = pr["unit_price"], f"{pr['source']} ({pr['price_date']})"
            else:
                no_price.add(it["code"])
    lines = []
    total = 0.0
    for e in bom.values():
        e["qty"] = round(e["qty"], 3)
        e["amount"] = round(e["qty"] * e["unit_price"], 0) if e["unit_price"] is not None else None
        total += e["amount"] or 0
        lines.append(e)
    return {"lines": sorted(lines, key=lambda x: x["code"]), "material_total_krw": total,
            "unmapped_rows": unmapped, "items_without_price": sorted(no_price),
            "note": "단가 없는 품목은 합계에서 제외됨. 노무비·경비·간접비 미포함."}


def main(argv=None):
    p = argparse.ArgumentParser(description="건축 BOM DB")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("--no-seed", action="store_true")
    im = sub.add_parser("import"); im.add_argument("csv"); im.add_argument("--table", required=True,
                                                                            choices=["items", "prices", "assemblies", "assembly_items", "mappings", "spec_links"])
    s = sub.add_parser("search"); s.add_argument("keyword")
    pa = sub.add_parser("price-add"); pa.add_argument("code"); pa.add_argument("price", type=float)
    pa.add_argument("--source", required=True); pa.add_argument("--date", required=True); pa.add_argument("--region")
    pa.add_argument("--type", default="material", choices=["material", "labor", "expense"])
    aa = sub.add_parser("assembly-add"); aa.add_argument("code"); aa.add_argument("name"); aa.add_argument("unit")
    aa.add_argument("components", nargs="+")
    ma = sub.add_parser("map-add"); ma.add_argument("ifc_class"); ma.add_argument("name_pattern"); ma.add_argument("assembly")
    ma.add_argument("--qty", required=True); ma.add_argument("--priority", type=int, default=0)
    c = sub.add_parser("cost"); c.add_argument("takeoff_csv")
    a = p.parse_args(argv)
    if a.cmd == "init":
        res = init(seed=not a.no_seed)
    elif a.cmd == "import":
        res = {"imported": import_csv(a.csv, a.table)}
    elif a.cmd == "search":
        res = search(a.keyword)
    elif a.cmd == "price-add":
        res = price_add(a.code, a.price, a.source, a.date, a.region, a.type)
    elif a.cmd == "assembly-add":
        res = assembly_add(a.code, a.name, a.unit, a.components)
    elif a.cmd == "map-add":
        res = map_add(a.ifc_class, a.name_pattern, a.assembly, a.qty, a.priority)
    else:
        res = cost_from_takeoff(a.takeoff_csv)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
