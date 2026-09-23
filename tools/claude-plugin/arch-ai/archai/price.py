"""조달청 나라장터 가격정보현황서비스(공공데이터포털 15129415) 조회와 BOM DB 단가 연계.

제공 자료(무료, 이용허락 제한 없음, 연 2회 정기 갱신):
  시설공통자재(건축·토목·기계설비·전기정보통신·종합), 시장시공가격(건축·토목·기계설비),
  표준시장단가 및 시장시공가격, 공종분류 및 세부공종, 자원분류 및 순수자원.
  ※ 조달청이 시설공사 원가계산에 쓰는 참고가격이다. 수량·난이도·수급에 따라 달라질 수 있다.

사전 준비:
  data.go.kr 에서 "조달청_나라장터 가격정보현황서비스" 활용신청 후 받은 인증키(Decoding 키)를
  환경변수 DATA_GO_KR_KEY 로 설정한다.

사용법:
  python -m archai.price search 레디믹스트 --category bildng
  python -m archai.price search "이형철근" --spec SD400 --category total
  python -m archai.price search 방수 --category mrkt_bildng          # 시장시공가격(건축)
  python -m archai.price link CON-24 --category bildng --name 레디믹스트 --spec "25-24-150"
                                                                    # 검색 결과 1건을 BOM 단가로 등록
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://apis.data.go.kr/1230000/ao/PriceInfoService"
CATEGORIES = {
    "bildng": ("getPriceInfoListFcltyCmmnMtrilBildng", "시설공통자재(건축)"),
    "engrk": ("getPriceInfoListFcltyCmmnMtrilEngrk", "시설공통자재(토목)"),
    "mchn": ("getPriceInfoListFcltyCmmnMtrilMchnEqp", "시설공통자재(기계설비)"),
    "elcty": ("getPriceInfoListFcltyCmmnMtrilElctyIrmc", "시설공통자재(전기·정보통신)"),
    "total": ("getPriceInfoListFcltyCmmnMtrilTotal", "시설공통자재(종합)"),
    "mrkt_bildng": ("getPriceInfoListMrktCnstrctPcBildng", "시장시공가격(건축)"),
    "mrkt_engrk": ("getPriceInfoListMrktCnstrctPcEngrk", "시장시공가격(토목)"),
    "mrkt_mchn": ("getPriceInfoListMrktCnstrctPcMchnEqp", "시장시공가격(기계설비)"),
    "std": ("getStdMarkUprcinfoList", "표준시장단가 및 시장시공가격"),
    "cnstty": ("getCnsttyClsfcInfoList", "공종분류 및 세부공종"),
    "rsce": ("getNetRsceinfoList", "자원분류 및 순수자원"),
}

# 응답 필드 → 공통 이름 (명세의 item 필드 기준. 서비스마다 일부만 존재)
FIELDS = {
    "name": ["prdctClsfcNoNm", "rsceNm", "cnsttyNm", "dtilCnsttyNm"],
    "spec": ["krnPrdctNm", "rsceSpecNm", "specNm"],
    "unit": ["unit"],
    "price": ["prce", "uprc"],
    "material": ["mtrlcst"], "labor": ["lbrcst"], "expense": ["gnrlexpns"],
    "posted": ["nticeDt"],
    "region": ["splyJrsdctRgnNm"],
    "delivery": ["dlvryCndtnNm"],
    "vat": ["vatYnNm"],
    "id": ["prdctIdntNo", "netRsceCd", "prceNticeNo"],
    "class_no": ["prdctClsfcNo"],
}


class PriceApiError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not k:
        raise PriceApiError("환경변수 DATA_GO_KR_KEY 가 없습니다. data.go.kr 에서 "
                            "'조달청_나라장터 가격정보현황서비스' 활용신청 후 Decoding 인증키를 설정하세요.")
    return k


def _call(operation: str, params: dict) -> dict:
    q = {"serviceKey": _key(), "type": "json", **params}
    url = f"{BASE}/{operation}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"User-Agent": "archai/0.2"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            break
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt == 3:
                raise PriceApiError(f"apis.data.go.kr 연결 실패: {e}") from e
            time.sleep(2 ** attempt)
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        # 인증 오류 등은 XML(OpenAPI_ServiceResponse)로 오는 경우가 많다
        raise PriceApiError(f"JSON이 아닌 응답(인증키·활용신청 확인): {body[:300]}") from e
    resp = data.get("response", data)
    header = resp.get("header", {})
    if str(header.get("resultCode", "00")) not in ("00", "0"):
        raise PriceApiError(f"API 오류 {header.get('resultCode')}: {header.get('resultMsg')}")
    return resp.get("body", {})


def _pick(item: dict, names: list[str]):
    for n in names:
        v = item.get(n)
        if v not in (None, ""):
            return v
    return None


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def normalize(item: dict, category: str) -> dict:
    row = {k: _pick(item, v) for k, v in FIELDS.items()}
    for k in ("price", "material", "labor", "expense"):
        row[k] = _num(row[k])
    row["category"] = CATEGORIES[category][1]
    row["raw"] = item
    return row


def fetch(category: str = "bildng", page: int = 1, rows: int = 100, **filters) -> dict:
    """한 페이지 조회. filters는 API 요청 파라미터로 그대로 전달(예: prdctClsfcNoNm=품명, krnPrdctNm=규격명)."""
    if category not in CATEGORIES:
        raise ValueError(f"category는 {list(CATEGORIES)} 중 하나")
    body = _call(CATEGORIES[category][0], {"pageNo": page, "numOfRows": rows,
                                           **{k: v for k, v in filters.items() if v}})
    items = body.get("items") or []
    if isinstance(items, dict):
        items = items.get("item") or []
    if isinstance(items, dict):
        items = [items]
    return {"total": int(body.get("totalCount") or 0), "page": page,
            "items": [normalize(i, category) for i in items]}


def search(keyword: str, category: str = "bildng", spec: str | None = None,
           max_pages: int = 5, rows: int = 100, limit: int = 50) -> list[dict]:
    """품명(+규격) 검색. 서버측 필터(prdctClsfcNoNm/krnPrdctNm)를 먼저 쓰고,
    서버가 필터를 무시하는 서비스에 대비해 클라이언트측에서도 한 번 더 거른다."""
    found = []
    for page in range(1, max_pages + 1):
        res = fetch(category, page, rows, prdctClsfcNoNm=keyword, krnPrdctNm=spec)
        for r in res["items"]:
            hay = f"{r['name'] or ''}{r['spec'] or ''}".replace(" ", "")
            if keyword.replace(" ", "") in hay and (not spec or spec.replace(" ", "") in hay):
                found.append(r)
        if len(found) >= limit or page * rows >= res["total"]:
            break
    return [{k: v for k, v in r.items() if k != "raw"} for r in found[:limit]]


def link_to_bom(item_code: str, category: str, name: str, spec: str | None = None, index: int = 0,
                force: bool = False) -> dict:
    """검색 결과 중 index번째 항목을 BOM prices에 출처와 함께 등록한다.
    BOM 품목 단위와 조달청 단위가 다르면 등록하지 않는다(force=True면 등록)."""
    from . import bom
    row = bom.connect().execute("SELECT unit FROM items WHERE code = ?", (item_code,)).fetchone()
    if not row:
        raise PriceApiError(f"BOM에 품목 {item_code}가 없습니다")
    hits = search(name, category, spec, limit=index + 1)
    if len(hits) <= index:
        raise PriceApiError(f"'{name} {spec or ''}' 검색 결과가 없습니다")
    h = hits[index]
    if h["price"] is None:
        raise PriceApiError(f"가격 필드가 없는 항목입니다: {h}")
    matched = {k: h[k] for k in ("name", "spec", "unit", "price", "delivery", "vat")}
    if (h["unit"] or "").lower() != (row["unit"] or "").lower() and not force:
        return {"registered": False, "matched": matched,
                "reason": f"단위 불일치: BOM '{row['unit']}' ↔ 조달청 '{h['unit']}'. 환산한 값을 bom price-add로 넣거나 force로 등록"}
    date = (h["posted"] or "")[:10] or time.strftime("%Y-%m-%d")
    source = f"조달청 가격정보 {h['category']} [{h['name']} / {h['spec']}] id={h['id']}"
    res = bom.price_add(item_code, h["price"], source, date, h["region"], "material")
    for kind in ("labor", "expense"):
        if h[kind]:
            bom.price_add(item_code, h[kind], source, date, h["region"], kind)
    return {"registered": True, **res, "matched": matched}


def main(argv=None):
    p = argparse.ArgumentParser(description="조달청 가격정보 조회/BOM 연계")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("keyword"); s.add_argument("--spec")
    s.add_argument("--category", default="bildng", choices=list(CATEGORIES))
    r = sub.add_parser("raw"); r.add_argument("--category", default="bildng", choices=list(CATEGORIES))
    r.add_argument("--page", type=int, default=1); r.add_argument("--rows", type=int, default=10)
    lk = sub.add_parser("link"); lk.add_argument("item_code"); lk.add_argument("--name", required=True)
    lk.add_argument("--spec"); lk.add_argument("--category", default="bildng", choices=list(CATEGORIES))
    lk.add_argument("--index", type=int, default=0); lk.add_argument("--force", action="store_true")
    sub.add_parser("categories")
    a = p.parse_args(argv)
    try:
        if a.cmd == "categories":
            res = {k: v[1] for k, v in CATEGORIES.items()}
        elif a.cmd == "search":
            res = search(a.keyword, a.category, a.spec)
        elif a.cmd == "raw":
            res = fetch(a.category, a.page, a.rows)
        else:
            res = link_to_bom(a.item_code, a.category, a.name, a.spec, a.index, a.force)
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    except PriceApiError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
