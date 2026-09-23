"""구조 검토 계산 도구 — 하중조합, 단순 보 해석, RC 보 휨·전단 검토, 최소두께 검토.

기준: KDS 41 10 15(건축구조기준 설계하중 조합), KDS 14 20 20(콘크리트 휨·압축),
      KDS 14 20 22(전단), KDS 14 20 30(사용성: 처짐 최소두께).
      단위는 N, mm, MPa (하중은 kN, kN/m, 모멘트 kN·m로 입출력).

주의: 예비 검토·오류 탐지용이다. 최종 구조계산서는 반드시 구조기술사 검토와
      최신 KDS 원문 확인을 거친다. 계수·표는 기준 개정 시 갱신해야 한다.

사용법:
  python -m archai.structure combos --D 5 --L 3 --W 1.2 --E 0.8
  python -m archai.structure beam --span 6000 --w 25 --support simple
  python -m archai.structure rc-beam --b 400 --h 600 --d 540 --fck 24 --fy 400 --As 1548 --Mu 250 --Vu 180 --Av 142.7 --s 200
  python -m archai.structure min-depth --member beam --span 7000 --support one_end_continuous --fy 400
"""

from __future__ import annotations

import argparse
import json
import math
import sys

# KDS 14 20 20: 등가직사각형 응력블록 계수 (fck 이하 → η, β1, εcu)
STRESS_BLOCK = [
    (40, 1.00, 0.80, 0.0033),
    (50, 0.97, 0.80, 0.0032),
    (60, 0.95, 0.76, 0.0031),
    (70, 0.91, 0.74, 0.0030),
    (80, 0.87, 0.72, 0.0029),
    (90, 0.84, 0.70, 0.0028),
]
ES = 200_000.0  # 철근 탄성계수 MPa


def stress_block(fck: float):
    for lim, eta, beta1, ecu in STRESS_BLOCK:
        if fck <= lim:
            return eta, beta1, ecu
    return STRESS_BLOCK[-1][1:]


# ------------------------------------------------------------ 하중조합

def load_combinations(D=0.0, L=0.0, Lr=0.0, S=0.0, R=0.0, W=0.0, E=0.0, H=0.0, F=0.0, T=0.0) -> dict:
    """KDS 41 10 15 강도설계 하중조합 (주요식). 결과: 각 조합의 계수하중과 지배 조합."""
    roof = max(Lr, S, R)
    combos = {
        "1.4(D+F)": 1.4 * (D + F),
        "1.2(D+F+T)+1.6(L+H)+0.5(Lr|S|R)": 1.2 * (D + F + T) + 1.6 * (L + H) + 0.5 * roof,
        "1.2D+1.6(Lr|S|R)+(1.0L|0.65W)": 1.2 * D + 1.6 * roof + max(1.0 * L, 0.65 * W),
        "1.2D+1.3W+1.0L+0.5(Lr|S|R)": 1.2 * D + 1.3 * W + 1.0 * L + 0.5 * roof,
        "1.2(D+H+F)+1.0E+1.0L+0.2S": 1.2 * (D + H + F) + 1.0 * E + 1.0 * L + 0.2 * S,
        "0.9D+1.3W+1.6H": 0.9 * D + 1.3 * W + 1.6 * H,
        "0.9(D+H+F)+1.0E": 0.9 * (D + H + F) + 1.0 * E,
    }
    gov = max(combos, key=combos.get)
    return {"combinations": {k: round(v, 3) for k, v in combos.items()}, "governing": gov,
            "note": "풍하중 계수(1.3 vs 1.0)는 적용 기준판 확인. 활하중 저감·지진 특별조합은 별도 검토."}


def service_combination(D=0.0, L=0.0) -> float:
    return D + L


# ------------------------------------------------------------ 보 해석

def beam_analysis(span: float, w: float = 0.0, P: float = 0.0, a: float | None = None,
                  support: str = "simple", E: float = 25_000.0, I: float | None = None) -> dict:
    """등분포(w, kN/m)와 집중하중(P, kN at a mm) 보 해석. span mm.
    support: simple | cantilever | fixed | propped(일단고정 타단단순, 등분포만)
    E MPa, I mm^4 입력 시 최대처짐(mm) 계산 (등분포 기준 + 집중하중 중앙 가정)."""
    L = span
    wN = w  # kN/m == N/mm
    PN = P * 1000.0
    a = L / 2 if a is None else a
    Lm = L / 1000.0
    res = {}
    if support == "simple":
        M_w = w * Lm ** 2 / 8
        V_w = w * Lm / 2
        b_ = L - a
        M_p = P * (a / 1000) * (b_ / 1000) / Lm
        V_p = P * max(a, b_) / L
        res.update(M_max=M_w + M_p, V_max=V_w + V_p, M_neg=0.0)
        if I:
            d = 5 * wN * L ** 4 / (384 * E * I) + PN * L ** 3 / (48 * E * I)
            res["deflection"] = d
    elif support == "cantilever":
        res.update(M_neg=w * Lm ** 2 / 2 + P * a / 1000, V_max=w * Lm + P, M_max=0.0)
        if I:
            res["deflection"] = wN * L ** 4 / (8 * E * I) + PN * a ** 2 * (3 * L - a) / (6 * E * I)
    elif support == "fixed":
        res.update(M_neg=w * Lm ** 2 / 12 + P * Lm / 8, M_max=w * Lm ** 2 / 24 + P * Lm / 8,
                   V_max=w * Lm / 2 + P / 2)
        if I:
            res["deflection"] = wN * L ** 4 / (384 * E * I) + PN * L ** 3 / (192 * E * I)
    elif support == "propped":
        res.update(M_neg=w * Lm ** 2 / 8, M_max=9 * w * Lm ** 2 / 128, V_max=5 * w * Lm / 8)
        if I:
            res["deflection"] = wN * L ** 4 / (185 * E * I)
    else:
        raise ValueError("support: simple | cantilever | fixed | propped")
    out = {k: round(v, 3) for k, v in res.items()}
    out["units"] = "M: kN·m, V: kN, deflection: mm"
    if "deflection" in out:
        out["L/deflection"] = round(L / out["deflection"], 0) if out["deflection"] else None
    return out


# ------------------------------------------------------------ RC 보

def rc_beam_flexure(b: float, d: float, fck: float, fy: float, As: float, h: float | None = None,
                    Mu: float | None = None) -> dict:
    """단철근 직사각형 보 휨강도 (KDS 14 20 20). Mu kN·m."""
    eta, beta1, ecu = stress_block(fck)
    a = As * fy / (eta * 0.85 * fck * b)
    c = a / beta1
    et = ecu * (d - c) / c
    ey = fy / ES
    et_tc = max(0.005, 2.5 * ey)            # 인장지배 한계
    et_min = max(0.004, 2.0 * ey)           # 휨부재 최소 허용변형률
    if et >= et_tc:
        phi = 0.85
    elif et <= ey:
        phi = 0.65
    else:
        phi = 0.65 + 0.20 * (et - ey) / (et_tc - ey)
    Mn = As * fy * (d - a / 2) / 1e6
    phiMn = phi * Mn
    rho = As / (b * d)
    As_min = max(0.25 * math.sqrt(fck) / fy, 1.4 / fy) * b * d
    checks = {
        "As>=As_min": As >= As_min,
        "εt>=최소허용변형률": et >= et_min,
    }
    if Mu is not None:
        checks["φMn>=Mu"] = phiMn >= Mu
        # 최소철근 예외: 해석상 필요 철근보다 1/3 이상 많으면 최소철근 불필요
    return {
        "a_mm": round(a, 1), "c_mm": round(c, 1), "εt": round(et, 5), "εt_tension_controlled": et_tc,
        "phi": round(phi, 3), "Mn_kNm": round(Mn, 1), "phiMn_kNm": round(phiMn, 1),
        "rho": round(rho, 5), "As_min_mm2": round(As_min, 0),
        "ratio_Mu/phiMn": round(Mu / phiMn, 3) if Mu else None,
        "checks": checks, "ok": all(checks.values()),
    }


def rc_beam_shear(b: float, d: float, fck: float, fyt: float, Vu: float, Av: float = 0.0,
                  s: float | None = None, lam: float = 1.0) -> dict:
    """RC 보 전단 검토 (KDS 14 20 22). Vu kN, Av 스터럽 전체 단면적 mm², s 간격 mm."""
    phi = 0.75
    sq = min(math.sqrt(fck), 8.36)  # √fck 상한 (fck 70MPa 상당)
    Vc = lam * sq * b * d / 6 / 1000
    Vs = Av * fyt * d / s / 1000 if (Av and s) else 0.0
    Vs_max = 2 / 3 * sq * b * d / 1000
    Vs_lim = 1 / 3 * sq * b * d / 1000
    s_max = min(d / 4, 300) if Vs > Vs_lim else min(d / 2, 600)
    Av_min = max(0.0625 * sq * b * (s or 1) / fyt, 0.35 * b * (s or 1) / fyt)
    phiVn = phi * (Vc + min(Vs, Vs_max))
    checks = {"φVn>=Vu": phiVn >= Vu, "Vs<=Vs_max(단면 확대 필요 여부)": Vs <= Vs_max}
    if Vu > phi * Vc / 2:
        checks["최소전단철근 필요 → Av>=Av_min"] = bool(Av) and Av >= Av_min
        if s:
            checks["s<=s_max"] = s <= s_max
    return {
        "phiVc_kN": round(phi * Vc, 1), "Vs_kN": round(Vs, 1), "Vs_max_kN": round(Vs_max, 1),
        "phiVn_kN": round(phiVn, 1), "s_max_mm": round(s_max, 0), "Av_min_mm2": round(Av_min, 1),
        "ratio_Vu/phiVn": round(Vu / phiVn, 3) if phiVn else None,
        "checks": checks, "ok": all(checks.values()),
    }


# 처짐을 계산하지 않는 경우의 최소두께 (KDS 14 20 30, 보통중량콘크리트, fy=400 기준)
MIN_DEPTH_DIV = {
    "slab": {"simple": 20, "one_end_continuous": 24, "both_ends_continuous": 28, "cantilever": 10},
    "beam": {"simple": 16, "one_end_continuous": 18.5, "both_ends_continuous": 21, "cantilever": 8},
}


def min_depth(member: str, span: float, support: str, fy: float = 400.0, h: float | None = None) -> dict:
    """1방향 슬래브·보 최소두께. fy≠400이면 (0.43 + fy/700) 보정."""
    div = MIN_DEPTH_DIV[member][support]
    hmin = span / div * (0.43 + fy / 700)
    out = {"h_min_mm": round(hmin, 0), "rule": f"L/{div} × (0.43+fy/700)"}
    if h is not None:
        out["h_mm"] = h
        out["ok"] = h >= hmin
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="구조 검토 계산")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("combos")
    for k in ("D", "L", "Lr", "S", "R", "W", "E", "H", "F", "T"):
        c.add_argument(f"--{k}", type=float, default=0.0)
    bm = sub.add_parser("beam")
    bm.add_argument("--span", type=float, required=True)
    bm.add_argument("--w", type=float, default=0.0)
    bm.add_argument("--P", type=float, default=0.0)
    bm.add_argument("--a", type=float)
    bm.add_argument("--support", default="simple")
    bm.add_argument("--E", type=float, default=25_000.0)
    bm.add_argument("--I", type=float)
    rc = sub.add_parser("rc-beam")
    for k in ("b", "d", "fck", "fy", "As"):
        rc.add_argument(f"--{k}", type=float, required=True)
    for k in ("h", "Mu", "Vu", "Av", "s"):
        rc.add_argument(f"--{k}", type=float)
    rc.add_argument("--fyt", type=float)
    md = sub.add_parser("min-depth")
    md.add_argument("--member", choices=["slab", "beam"], required=True)
    md.add_argument("--span", type=float, required=True)
    md.add_argument("--support", choices=list(MIN_DEPTH_DIV["beam"]), required=True)
    md.add_argument("--fy", type=float, default=400.0)
    md.add_argument("--h", type=float)
    a = p.parse_args(argv)
    if a.cmd == "combos":
        res = load_combinations(**{k: getattr(a, k) for k in ("D", "L", "Lr", "S", "R", "W", "E", "H", "F", "T")})
    elif a.cmd == "beam":
        res = beam_analysis(a.span, a.w, a.P, a.a, a.support, a.E, a.I)
    elif a.cmd == "rc-beam":
        res = {"flexure": rc_beam_flexure(a.b, a.d, a.fck, a.fy, a.As, a.h, a.Mu)}
        if a.Vu is not None:
            res["shear"] = rc_beam_shear(a.b, a.d, a.fck, a.fyt or a.fy, a.Vu, a.Av or 0.0, a.s)
    else:
        res = min_depth(a.member, a.span, a.support, a.fy, a.h)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
