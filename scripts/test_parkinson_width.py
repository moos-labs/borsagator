#!/usr/bin/env python3
"""Tests for benchmarks/replay_parkinson_width.py (INS-IMPROVE-006 A).
Standalone, stdlib only.
"""
import importlib.util
import math
import os
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
    "pkw", os.path.join(ROOT, "benchmarks", "replay_parkinson_width.py"))
P = importlib.util.module_from_spec(spec)
sys.modules["pkw"] = P
spec.loader.exec_module(P)


def row(real=1.0, sp=0.02, s60=0.02, h="week", t="A", a="d1"):
    return {"ticker": t, "as_of": a, "horizon": h, "real": real,
            "naive_half": P.R.half_pct(s60, h, 1.2816, 1.0),
            "mult": 1.0, "v2_sigma": s60,
            "sig": {"s60": s60, "park60": sp}}


def test_constants():
    check("v2 pinned", P.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("rule minimums", (P.MIN_ROWS, P.MIN_TICKERS, P.MIN_CUTOFFS)
          == (30, 5, 2))
    check("clean cells start at 91", P.CLEAN_MIN_CELL == 91)


def test_estimator():
    bars = [(10, 10.5, 9.5, 10)] * 60
    sp = P.R.sigmas(bars)["park60"]
    want = math.sqrt(math.log(10.5 / 9.5) ** 2 / (4 * math.log(2)))
    check("parkinson formula", sp is not None and abs(sp - want) < 1e-9,
          (sp, want))


def test_score_rows():
    p = P.score_rows([row(sp=0.04, s60=0.02)])[0]
    half = P.R.half_pct(0.04, "week", 1.28, 1.0)
    half_v2 = P.R.half_pct(0.02, "week", 1.28, 1.0)
    check("wider sigma widens band", half > half_v2)
    check("k not refitted: equal sigma equals v2",
          abs(P.score_rows([row(sp=0.02, s60=0.02)])[0]["is_ch"]
              - P.score_rows([row(sp=0.02, s60=0.02)])[0]["is_v2"]) < 1e-9)
    check("missing park skipped", P.score_rows([row(sp=None)]) == [])
    check("coverage flag", P.score_rows([row(real=0.0)])[0]["in_ch"])


def test_verdict():
    res = {h: {"n": 5, "tickers": 2, "cutoffs": 1,
               "ch_ci_cutoff": [0.1, 0.2], "ch": {"coverage": 0.8}}
           for h in P.HORIZONS}
    check("small insufficient", P.keep_verdict(res)[0] == "INSUFFICIENT")
    for h in P.HORIZONS:
        res[h].update(n=40, tickers=6, cutoffs=3)
    check("keep", P.keep_verdict(res)[0] == "KEEP")
    res["day"]["ch_ci_cutoff"] = [-0.01, 0.2]
    check("ci spans zero rejects", P.keep_verdict(res)[0] == "REJECT")
    res["day"]["ch_ci_cutoff"] = [0.1, 0.2]
    res["week"]["ch"]["coverage"] = 0.7
    check("coverage rejects", P.keep_verdict(res)[0] == "REJECT")


def test_refusal():
    rc = P.main(["score", "--captures", "/nonexistent", "--min-cell", "73"])
    check("refuses seen cells", rc == 2)


def main():
    for fn in (test_constants, test_estimator, test_score_rows,
               test_verdict, test_refusal):
        fn()
    print("test_parkinson_width: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
