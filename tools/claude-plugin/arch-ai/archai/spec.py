"""시방서 작성·검토 도구 — KCS 3부 구성(일반사항/자재/시공) 골격 생성과 시방서-BOM 교차검토.

사용법:
  python -m archai.spec skeleton "철근콘크리트공사" --kcs "KCS 14 20 00" > docs/design/spec-rc.md
  python -m archai.spec check docs/design/spec-rc.md           # BOM 품목과 교차검토
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from . import bom

SKELETON = """---
title: {title} 공사시방서
created: {{날짜}}
author: ai
sources: [{kcs}]
status: draft
---

# {title} 공사시방서

> 기준: {kcs} (국가건설기준센터 kcsc.re.kr 최신본 확인). 표준시방서 내용 중 본 공사에 해당하지 않는
> 항목은 삭제하고, 공사 특기사항은 "특기시방"으로 표시한다.

## 1. 일반사항
### 1.1 적용범위
### 1.2 참조 표준 (KS, KDS, KCS)
### 1.3 용어의 정의
### 1.4 제출물 (시공계획서, 자재승인, 시험성적서, 시공상세도)
### 1.5 품질보증 (시험·검사 기준, 허용오차)
### 1.6 운반·보관·취급
### 1.7 현장 조건 (기상, 환경, 안전)

## 2. 자재
### 2.1 재료 (품명 / 규격 / KS 번호 / BOM 코드)
| 품명 | 규격 | 관련 표준 | BOM 코드 |
|---|---|---|---|
|  |  |  |  |
### 2.2 배합·제작
### 2.3 재료 품질관리 (시험 항목·빈도)

## 3. 시공
### 3.1 시공 준비 (검토·확인 사항)
### 3.2 시공 기준 (순서, 방법, 허용오차)
### 3.3 현장 품질관리 (검사 항목·빈도·판정 기준)
### 3.4 보양 및 양생
### 3.5 보수 및 재시공 기준
"""

KS_RE = re.compile(r"KS\s?[A-Z]\s?\d{3,5}(?:-\d+)?")
KCS_RE = re.compile(r"KCS\s?\d{2}\s?\d{2}\s?\d{2}")
CODE_RE = re.compile(r"\b[A-Z]{3}-[A-Z0-9:\-]+\b")


def skeleton(title: str, kcs: str = "KCS 00 00 00") -> str:
    return SKELETON.format(title=title, kcs=kcs)


def check(spec_path: str) -> dict:
    """시방서에 적힌 BOM 코드가 DB에 있는지, 참조 표준 목록과 필수 절이 있는지 검토."""
    text = open(spec_path, encoding="utf-8").read()
    codes = sorted(set(CODE_RE.findall(text)))
    con = bom.connect()
    known = {r["code"] for r in con.execute("SELECT code FROM items")}
    missing_sections = [s for s in ("일반사항", "자재", "시공") if s not in text]
    return {
        "bom_codes_in_spec": codes,
        "unknown_bom_codes": [c for c in codes if c not in known],
        "ks_refs": sorted(set(KS_RE.findall(text))),
        "kcs_refs": sorted(set(KCS_RE.findall(text))),
        "missing_sections": missing_sections,
        "todo_markers": len(re.findall(r"\{\{|TODO|확인 필요", text)),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="시방서 도구")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("skeleton"); s.add_argument("title"); s.add_argument("--kcs", default="KCS 00 00 00")
    c = sub.add_parser("check"); c.add_argument("spec")
    a = p.parse_args(argv)
    if a.cmd == "skeleton":
        print(skeleton(a.title, a.kcs))
    else:
        print(json.dumps(check(a.spec), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
