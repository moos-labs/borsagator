#!/usr/bin/env python3
"""Tests for benchmarks/replay_band_candidates.py (INS-IMPROVE-001 P2/P3).
Standalone, stdlib only: python3 scripts/test_replay_band_candidates.py
"""
import importlib.util
import math
import os
import random
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location(
    "replay", os.path.join(ROOT, "benchmarks",
                           "replay_band_candidates.py"))
R = importlib.util.module_from_spec(spec)
sys.modules["replay"] = R
spec.loader.exec_module(R)


def _bars(n, daily=0.01, seed=3):
    rng = random.Random(seed)
    out, c = [], 100.0
    for _ in range(n):
        o = c
        c = o * math.exp(rng.gauss(0, daily))
        hi = max(o, c) * 1.002
        lo = min(o, c) * 0.998
        out.append((o, hi, lo, c))
    return out


def test_estimators():
    s = R.sigmas(_bars(200))
    check("all candidates present",
          all(s[c] is not None for c in R.CANDIDATES), repr(s))
    check("s60 near truth", 0.006 < s["s60"] < 0.016, str(s["s60"]))
    flat = R.sigmas([(100.0, 100.0, 100.0, 100.0)] * 100)
    check("flat series has zero close vol", flat["s60"] == 0.0)
    check("short history gives None", R.sigmas(_bars(3))["s60"] is None)
    # Parkinson on a constant 1% high-low range: sqrt(ln(1.01)^2/(4 ln2))
    pk = R.sigmas([(100.0, 101.0, 100.0, 100.5)] * 80)["park60"]
    check("parkinson closed form",
          abs(pk - math.log(1.01) / math.sqrt(4 * math.log(2))) < 1e-9)


def _row(real, sigma, h="day", cut="c1"):
    return {"cell": 1, "mult": 1.0, "ticker": "T", "as_of": cut, "horizon": h,
            "real": real, "naive_half": 1.2816 * sigma * 100,
            "v2_sigma": sigma, "sig": {"s60": sigma}}


def test_fit_k():
    rng = random.Random(1)
    rows = [_row(rng.gauss(0, 2.0), 0.02, cut="c%d" % (i % 4))
            for i in range(400)]
    k = R.fit_k(rows, "s60", "day")
    # true sd 2pp = 1.0 x sigma*100, Winkler optimum near 1.28
    check("fit k near the 80% quantile", 1.0 < k < 1.6, str(k))
    check("no rows gives None", R.fit_k([], "s60", "day") is None)
    cv = R.loco_cv(rows, "s60")
    check("loco ratio near 1 or below",
          cv["day"] is not None and 0.8 < cv["day"] < 1.1, str(cv))
    check("single cutoff gives None",
          R.loco_cv([_row(1.0, 0.02)] * 5, "s60")["day"] is None)


def _res(n, sk, cov, v2, cci=None):
    return {h: {"n": n, "ch": {"range_skill": sk, "coverage": cov},
                "ch_cov_ci_cutoff": cci or [cov - 0.03, cov + 0.03],
                "v2": {"range_skill": v2}} for h in R.HORIZONS}


def test_keep_rule():
    check("insufficient", R.keep_verdict(_res(29, .2, .8, 0))[0]
          == "INSUFFICIENT")
    check("keep", R.keep_verdict(_res(30, .06, .8, .0))[0] == "KEEP")
    check("reject on skill", R.keep_verdict(_res(30, .04, .8, .0))[0]
          == "REJECT")
    check("reject on coverage", R.keep_verdict(_res(30, .1, .9, .0))[0]
          == "REJECT")
    check("point outside band but coverage CI overlaps: keep",
          R.keep_verdict(_res(30, .06, .72, .0, [.66, .80]))[0] == "KEEP")
    check("coverage CI touching 0.85 overlaps",
          R.keep_verdict(_res(30, .06, .90, .0, [.85, .95]))[0] == "KEEP")
    check("coverage CI entirely below rejects",
          R.keep_verdict(_res(30, .06, .6, .0, [.5, .7]))[0] == "REJECT")
    check("undefined coverage CI rejects",
          R.keep_verdict(_res(30, .06, .8, .0, [None, None]))[0]
          == "REJECT")
    check("coverage_ci_ok helper",
          R.coverage_ci_ok([.7, .76]) and not R.coverage_ci_ok([.86, .9])
          and not R.coverage_ci_ok(None))
    import inspect
    check("#594 verdict takes no coverage input (unchanged by the "
          "coverage rule)",
          list(inspect.signature(R.A.verdict).parameters)
          == ["n", "n_tickers", "ci_lo"])
    check("#594 DO NOT ADOPT stands: day CI lower -0.055, month -0.033",
          R.A.verdict(31, 6, -0.055) == "DO NOT ADOPT"
          and R.A.verdict(31, 6, -0.033) == "DO NOT ADOPT")
    check("reject when worse than v2",
          R.keep_verdict(_res(30, .06, .8, .08))[0] == "REJECT")


def test_risk_mult_carried():
    check("half_pct applies mult",
          abs(R.half_pct(0.02, "day", 1.0, 1.3) - 2.6) < 1e-9)
    check("default mult is 1",
          abs(R.half_pct(0.02, "day", 1.0) - 2.0) < 1e-9)
    frozen = {"candidate": "s60", "k": {"day": 1.0, "week": 1.0,
                                        "month": 1.0}}
    row = _row(2.5, 0.02)
    row["mult"] = 1.0
    plain = R.score_rows([row], frozen)[0]
    row2 = dict(row)
    row2["mult"] = 1.3
    wide = R.score_rows([row2], frozen)[0]
    check("candidate band widens with mult",
          not plain["in_ch"] and wide["in_ch"])
    check("v2 band widens with mult",
          not plain["in_v2"] or wide["in_v2"])
    check("v2 uses frozen k and mult",
          abs(R.half_pct(0.02, "day", R.ens_mod.V2_BAND_K["day"], 1.3)
              - 1.15 * 2.0 * 1.3) < 1e-9)


def test_refuses_seen_cells():
    rc = R.main(["score", "--frozen", __file__, "--captures", "/nonexistent",
                 "--min-cell", "72"])
    check("refuses cells below 73", rc == 2)


if __name__ == "__main__":
    test_estimators()
    test_fit_k()
    test_keep_rule()
    test_risk_mult_carried()
    test_refuses_seen_cells()
    print("test_replay_band_candidates: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
