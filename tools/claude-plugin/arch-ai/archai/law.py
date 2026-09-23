"""국가법령정보센터(law.go.kr) Open API로 건축 관련 법령을 검색하고 조문을 조회한다.

사전 준비:
  https://open.law.go.kr 에서 Open API 사용 신청 후 받은 OC(신청 계정 ID)를
  환경변수 LAW_OC 로 설정한다. (예: export LAW_OC=myid)

사용법:
  python -m archai.law search 건축법
  python -m archai.law search 주차장 --target ordin          # 자치법규(조례)
  python -m archai.law search 건축선 --target prec           # 판례
  python -m archai.law search 건폐율 --target expc           # 법령해석례
  python -m archai.law article 건축법 44                      # 건축법 제44조
  python -m archai.law article "건축법 시행령" 119 --mst 123456

target 값:
  law(법령) · admrul(행정규칙: 고시·훈령·예규) · ordin(자치법규) · prec(판례) · expc(법령해석례)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.law.go.kr/DRF"
TARGETS = {
    "law": "법령",
    "admrul": "행정규칙",
    "ordin": "자치법규",
    "prec": "판례",
    "expc": "법령해석례",
}

# 건축 실무에서 자주 검토하는 법령 (검색 출발점)
CORE_LAWS = [
    "건축법", "건축법 시행령", "건축법 시행규칙",
    "국토의 계획 및 이용에 관한 법률", "국토의 계획 및 이용에 관한 법률 시행령",
    "주차장법", "주차장법 시행령", "주차장법 시행규칙",
    "건축물의 피난ㆍ방화구조 등의 기준에 관한 규칙",
    "건축물의 설비기준 등에 관한 규칙",
    "건축물의 구조기준 등에 관한 규칙",
    "장애인ㆍ노인ㆍ임산부 등의 편의증진 보장에 관한 법률",
    "녹색건축물 조성 지원법",
    "소방시설 설치 및 관리에 관한 법률",
    "주택법", "주택건설기준 등에 관한 규정",
    "건축물관리법", "건설기술 진흥법",
]


class LawApiError(RuntimeError):
    pass


def _oc() -> str:
    oc = os.environ.get("LAW_OC", "").strip()
    if not oc:
        raise LawApiError(
            "환경변수 LAW_OC 가 없습니다. open.law.go.kr 에서 Open API를 신청하고 "
            "발급 계정(OC)을 LAW_OC 로 설정하세요."
        )
    return oc


def _get(endpoint: str, params: dict) -> dict:
    params = {"OC": _oc(), "type": "JSON", **params}
    url = f"{BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "archai/0.2", "Referer": "https://www.law.go.kr/"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            break
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt == 3:
                raise LawApiError(f"law.go.kr 연결 실패: {e}") from e
            time.sleep(2 ** attempt)
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise LawApiError(f"JSON이 아닌 응답입니다 (OC 승인/도메인 등록 확인): {body[:300]}") from e


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def search(query: str, target: str = "law", display: int = 20, page: int = 1) -> list[dict]:
    """법령/행정규칙/자치법규/판례/해석례 목록 검색."""
    if target not in TARGETS:
        raise ValueError(f"target은 {list(TARGETS)} 중 하나여야 합니다")
    data = _get("lawSearch.do", {"target": target, "query": query, "display": display, "page": page})
    root = next(iter(data.values())) if data else {}
    # 응답 루트 아래 목록 키는 target 이름과 같다 (law, admrul, ordin, prec, expc)
    items = _as_list(root.get(target))
    return items


def get_law(name: str | None = None, mst: str | None = None, law_id: str | None = None) -> dict:
    """법령 본문 전체(JSON). mst(법령일련번호)나 law_id가 없으면 이름으로 검색해 첫 결과를 쓴다."""
    if not (mst or law_id):
        if not name:
            raise ValueError("name, mst, law_id 중 하나는 필요합니다")
        hits = search(name, "law", display=10)
        exact = [h for h in hits if h.get("법령명한글") == name] or hits
        if not exact:
            raise LawApiError(f"'{name}' 법령을 찾지 못했습니다")
        mst = exact[0].get("법령일련번호")
    params = {"target": "law"}
    if mst:
        params["MST"] = mst
    else:
        params["ID"] = law_id
    return _get("lawService.do", params)


def _walk_articles(node):
    if isinstance(node, dict):
        if "조문번호" in node and ("조문내용" in node or "항" in node):
            yield node
        for v in node.values():
            yield from _walk_articles(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_articles(v)


def _flatten_text(node) -> str:
    """조문 JSON(조문내용/항/호/목)을 읽기 좋은 문자열로 편다."""
    out = []

    def rec(n):
        if isinstance(n, dict):
            for key in ("조문내용", "항내용", "호내용", "목내용"):
                if key in n and n[key]:
                    t = n[key]
                    out.append("".join(t) if isinstance(t, list) else str(t))
            for key in ("항", "호", "목"):
                if key in n:
                    rec(n[key])
        elif isinstance(n, list):
            for x in n:
                rec(x)

    rec(node)
    return "\n".join(s.strip() for s in out if s and str(s).strip())


def get_article(name: str, number: str | int, mst: str | None = None) -> list[dict]:
    """특정 조문 조회. number 예: 44, '44의2'"""
    m = re.fullmatch(r"(\d+)(?:의(\d+))?", str(number).replace("제", "").replace("조", ""))
    if not m:
        raise ValueError("조문번호 형식 예: 44, 44의2")
    main, sub = m.group(1), m.group(2)
    data = get_law(name=name, mst=mst)
    results = []
    for art in _walk_articles(data):
        if str(art.get("조문번호")) != main:
            continue
        if str(art.get("조문가지번호") or "") != (sub or ""):
            continue
        if art.get("조문여부") == "전문":  # 장·절 제목 행 제외
            continue
        results.append({
            "조문번호": main + (f"의{sub}" if sub else ""),
            "조문제목": art.get("조문제목"),
            "시행일자": art.get("조문시행일자"),
            "내용": _flatten_text(art),
        })
    return results


def _summarize(item: dict, target: str) -> str:
    keys = {
        "law": ["법령명한글", "법령구분명", "시행일자", "법령일련번호"],
        "admrul": ["행정규칙명", "행정규칙종류", "발령일자", "행정규칙일련번호"],
        "ordin": ["자치법규명", "지자체기관명", "시행일자", "자치법규일련번호"],
        "prec": ["사건명", "사건번호", "선고일자", "판례일련번호"],
        "expc": ["안건명", "안건번호", "회신일자", "법령해석례일련번호"],
    }[target]
    return " | ".join(str(item.get(k, "")) for k in keys)


def main(argv=None):
    p = argparse.ArgumentParser(description="국가법령정보센터 법령 검색/조문 조회")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="목록 검색")
    s.add_argument("query")
    s.add_argument("--target", default="law", choices=list(TARGETS))
    s.add_argument("--display", type=int, default=20)
    s.add_argument("--json", action="store_true")
    a = sub.add_parser("article", help="조문 조회")
    a.add_argument("law_name")
    a.add_argument("number")
    a.add_argument("--mst")
    sub.add_parser("core", help="건축 핵심 법령 목록 출력")
    args = p.parse_args(argv)

    try:
        if args.cmd == "core":
            print("\n".join(CORE_LAWS))
        elif args.cmd == "search":
            items = search(args.query, args.target, args.display)
            if args.json:
                print(json.dumps(items, ensure_ascii=False, indent=2))
            else:
                for it in items:
                    print(_summarize(it, args.target))
        elif args.cmd == "article":
            for art in get_article(args.law_name, args.number, args.mst):
                print(f"■ 제{art['조문번호']}조({art['조문제목']}) 시행 {art['시행일자']}\n{art['내용']}\n")
    except LawApiError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
