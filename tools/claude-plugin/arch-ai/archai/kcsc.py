"""국가건설기준센터(KCSC) Open API — KDS 설계기준·KCS 표준시방서·기관별 전문시방서 조회.

사전 준비:
  https://www.kcsc.re.kr 에서 Open API 인증키를 신청하고 환경변수 KCSC_API_KEY 로 설정한다.

원문 취급 원칙:
  재배포 허용 여부가 확인되지 않았으므로 원문을 파일로 저장하거나 저장소에 커밋하지 않는다.
  조회 결과는 그때그때 인용 근거로만 쓰고, 인용 시 코드·버전·조항번호를 함께 적는다.
  (카탈로그 목록만 프로세스 메모리에 캐시한다.)

사용법:
  python -m archai.kcsc search 방수                     # 기준명 검색 (코드 종류 9가지)
  python -m archai.kcsc search 콘크리트 --type KCS
  python -m archai.kcsc get KCS "41 40 06"               # 본문 전체 (Markdown)
  python -m archai.kcsc get KCS 414006 --clause 3.2      # 특정 조항만
  python -m archai.kcsc toc KCS 414006                   # 조항 목차
  python -m archai.kcsc grep KCS 414006 담수시험          # 본문 검색

코드 종류: KDS(설계기준) KCS(표준시방서) SMCS(서울시) LHCS(LH) EXCS(도로공사) KRCCS(철도) KWCS(수자원) NHCS KRACS
API 동작 참고: https://github.com/lhs1152-lgtm/kcsc-design-mcp/blob/main/docs/KCSC_API.md (실측 문서)
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BASE = "https://kcsc.re.kr/OpenApi"
CODE_TYPES = ["KDS", "KCS", "SMCS", "LHCS", "EXCS", "KRCCS", "KWCS", "NHCS", "KRACS"]
_PRIORITY = {t: i for i, t in enumerate(CODE_TYPES)}  # 6자리 코드 충돌 시 국가기준 우선

_catalog_cache: list[dict] | None = None


class KcscError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get("KCSC_API_KEY", "").strip()
    if not k:
        raise KcscError("환경변수 KCSC_API_KEY 가 없습니다. kcsc.re.kr 에서 Open API 인증키를 신청하세요.")
    return k


def _get(path: str):
    url = f"{BASE}/{path}{'&' if '?' in path else '?'}key={urllib.parse.quote(_key())}"
    req = urllib.request.Request(url, headers={"User-Agent": "archai/0.2"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            break
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt == 3:
                raise KcscError(f"kcsc.re.kr 연결 실패: {e}") from e
            time.sleep(2 ** attempt)
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise KcscError(f"JSON이 아닌 응답: {body[:200]}") from e


def _reject_null_sentinel(data):
    """인증키가 틀려도 HTTP 200 + 필드가 전부 null인 1건이 온다 → 오류로 바꾼다."""
    rows = data if isinstance(data, list) else [data]
    if len(rows) == 1 and isinstance(rows[0], dict) and rows[0].get("codeType") is None and rows[0].get("code") is None:
        raise KcscError("KCSC가 빈 응답을 반환했습니다. KCSC_API_KEY 가 올바른지 확인하세요.")
    return rows


def normalize_code(code: str) -> str:
    """'KCS 41 40 06' / '41 40 06' / '414006' → '414006'"""
    c = re.sub(r"^[A-Z]+", "", code.strip().upper())
    c = re.sub(r"[^0-9]", "", c)
    if len(c) not in (6, 8):
        raise ValueError(f"코드는 숫자 6자리 또는 8자리여야 합니다: {code!r}")
    return c


def catalog(refresh: bool = False) -> list[dict]:
    global _catalog_cache
    if _catalog_cache is None or refresh:
        rows = _reject_null_sentinel(_get("CodeList"))
        _catalog_cache = [{
            "type": r.get("codeType"), "code": r.get("code"), "name": r.get("name"),
            "version": r.get("version"), "updated": (r.get("updateDate") or "")[:10],
            "path": " > ".join(p.get("name") or "" for p in (r.get("listParentCodes") or [])),
        } for r in rows if r.get("code")]
    return _catalog_cache


def search(keyword: str, code_type: str | None = None, limit: int = 30) -> list[dict]:
    """기준명·상위분류명으로 검색. 본문 검색은 grep을 쓴다."""
    kw = keyword.strip()
    out = [c for c in catalog()
           if (not code_type or c["type"] == code_type.upper())
           and (kw in (c["name"] or "") or kw in c["path"] or kw.replace(" ", "") in (c["code"] or ""))]
    out.sort(key=lambda c: (_PRIORITY.get(c["type"], 99), c["code"]))
    return [{**c, "cite": f"{c['type']} {_fmt(c['code'])}"} for c in out[:limit]]


def _fmt(code: str) -> str:
    return " ".join(code[i:i + 2] for i in range(0, len(code), 2))


def resolve(code_type: str | None, code: str) -> tuple[str, str, list[str]]:
    """코드 종류가 없으면 국가기준 우선으로 고르고, 다른 후보를 함께 돌려준다."""
    c = normalize_code(code)
    prefix = re.match(r"\s*([A-Za-z]+)", code)
    if not code_type and prefix and prefix.group(1).upper() in CODE_TYPES:
        code_type = prefix.group(1)  # 'KCS 41 40 06'처럼 종류가 코드에 붙어 온 경우
    if code_type:
        return code_type.upper(), c, []
    cands = sorted({r["type"] for r in catalog() if r["code"] == c}, key=lambda t: _PRIORITY.get(t, 99))
    if not cands:
        raise KcscError(f"카탈로그에 코드 {c}가 없습니다")
    return cands[0], c, cands[1:]


# ------------------------------------------------------------ HTML → Markdown

class _Html2Md(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out: list[str] = []
        self.table: list[list[str]] | None = None
        self.cell: list[str] | None = None
        self.images = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.table.append([])
        elif tag in ("td", "th") and self.table is not None:
            self.cell = []
        elif tag == "img":
            self.images += 1
            self._emit(f"[수식/그림 {self.images}]")
        elif tag in ("br", "p", "div", "li") and self.cell is None:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.table is not None and self.cell is not None:
            if not self.table:
                self.table.append([])
            self.table[-1].append(" ".join("".join(self.cell).split()).replace("|", "\\|"))
            self.cell = None
        elif tag == "table" and self.table is not None:
            rows = [r for r in self.table if r]
            if rows:
                w = max(len(r) for r in rows)
                rows = [r + [""] * (w - len(r)) for r in rows]
                md = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w]
                md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
                self.out.append("\n" + "\n".join(md) + "\n")
            self.table = None

    def handle_data(self, data):
        self._emit(data)

    def _emit(self, s):
        (self.cell if self.cell is not None else self.out).append(s)


def html_to_md(fragment: str) -> tuple[str, int]:
    p = _Html2Md()
    p.feed(html.unescape(fragment or ""))
    text = re.sub(r"\n{3,}", "\n\n", "".join(p.out)).strip()
    return text, p.images


# ------------------------------------------------------------ 본문

def _items(code_type: str, code: str) -> tuple[dict, list[dict]]:
    data = _reject_null_sentinel(_get(f"CodeViewer/{code_type}/{code}"))
    doc = data[0]
    return doc, doc.get("list") or []


def _clause_no(title: str | None) -> str:
    m = re.match(r"\s*(\d+(?:\.\d+)*)", title or "")
    return m.group(1) if m else ""


def get(code_type: str | None, code: str, clause: str | None = None, max_chars: int = 60000) -> dict:
    """기준 본문을 Markdown으로. clause='3.2'면 3.2와 하위 조항만."""
    t, c, others = resolve(code_type, code)
    doc, items = _items(t, c)
    if not items:
        raise KcscError(f"{t} {_fmt(c)} 본문이 없습니다 (상위 분류 코드일 수 있음)")
    parts, last_title, images = [], None, 0
    for it in sorted(items, key=lambda x: x.get("sort") or 0):
        title = it.get("title") or ""
        no = _clause_no(title)
        if clause and not (no == clause or no.startswith(clause + ".")):
            continue
        if title != last_title:
            parts.append(f"\n### {title}\n")
            last_title = title
        body, n = html_to_md(it.get("contents") or "")
        images += n
        label = it.get("label") or ""
        if label and label not in ("본문",) and not title.startswith(label):
            body = f"{label} {body}"
        if body:
            parts.append(body)
    text = "\n".join(parts).strip()
    truncated = len(text) > max_chars
    return {
        "cite": f"{t} {_fmt(c)} ({doc.get('version')})",
        "name": doc.get("name"), "type": t, "code": c, "version": doc.get("version"),
        "updated": (doc.get("updateDate") or "")[:10],
        "other_types_with_same_code": others,
        "clause": clause, "formula_images": images,
        "text": text[:max_chars], "truncated": truncated,
        "note": "수식·그림은 [수식/그림 N] 자리표로 표시됨 — 값이 필요하면 kcsc.re.kr 뷰어에서 확인. 원문 저장·재배포 금지.",
    }


def toc(code_type: str | None, code: str) -> dict:
    t, c, others = resolve(code_type, code)
    doc, items = _items(t, c)
    seen, out = set(), []
    for it in sorted(items, key=lambda x: x.get("sort") or 0):
        title = it.get("title") or ""
        if title and title not in seen:
            seen.add(title)
            out.append(title)
    return {"cite": f"{t} {_fmt(c)} ({doc.get('version')})", "name": doc.get("name"),
            "other_types_with_same_code": others, "clauses": out}


def grep(code_type: str | None, code: str, pattern: str, context: int = 120) -> dict:
    t, c, others = resolve(code_type, code)
    doc, items = _items(t, c)
    hits = []
    for it in sorted(items, key=lambda x: x.get("sort") or 0):
        body, _ = html_to_md(it.get("contents") or "")
        for m in re.finditer(re.escape(pattern), body):
            s = max(0, m.start() - context)
            hits.append({"clause": it.get("title"), "snippet": body[s:m.end() + context].replace("\n", " ")})
    return {"cite": f"{t} {_fmt(c)} ({doc.get('version')})", "pattern": pattern, "hits": hits[:50],
            "hit_count": len(hits)}


def main(argv=None):
    p = argparse.ArgumentParser(description="국가건설기준센터 KDS/KCS 조회")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("keyword"); s.add_argument("--type")
    for name in ("get", "toc", "grep"):
        g = sub.add_parser(name)
        g.add_argument("code_type", help="KDS/KCS/LHCS… 또는 '-'(자동)")
        g.add_argument("code")
        if name == "get":
            g.add_argument("--clause")
        if name == "grep":
            g.add_argument("pattern")
    a = p.parse_args(argv)
    ct = None if getattr(a, "code_type", "-") == "-" else getattr(a, "code_type", None)
    try:
        if a.cmd == "search":
            res = search(a.keyword, a.type)
        elif a.cmd == "get":
            res = get(ct, a.code, a.clause)
            print(f"# {res['cite']} {res['name']}\n\n{res['text']}")
            return 0
        elif a.cmd == "toc":
            res = toc(ct, a.code)
        else:
            res = grep(ct, a.code, a.pattern)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except KcscError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
