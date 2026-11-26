#!/usr/bin/env python3
"""Tests for benchmarks/score_tilt_technicals_594.py (INS-IMPROVE-001).
Standalone, stdlib only: python3 scripts/test_tilt_technicals_594.py
"""
import importlib.util
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
    "tiltt", os.path.join(ROOT, "benchmarks",
                          "score_tilt_technicals_594.py"))
T = importlib.util.module_from_spec(spec)
sys.modules["tiltt"] = T
spec.loader.exec_module(T)


def cell(n, tickers, cutoffs, lo, cov):
    return {"n": n, "tickers": tickers, "cutoffs": cutoffs,
            "skill_ci_cutoff": [lo, 0.1], "coverage": cov}


def test_constants():
    check("min rows 30", T.MIN_ROWS == 30)
    check("min tickers 5", T.MIN_TICKERS == 5)
    check("min cutoffs 2", T.MIN_CUTOFFS == 2)
    check("coverage band", (T.COV_LO, T.COV_HI) == (0.75, 0.85))


def test_rule():
    check("n<30 insufficient",
          T.tilt_rule(cell(6, 6, 1, 0.1, 0.8)).startswith("INSUFFICIENT"))
    check("one cutoff insufficient",
          T.tilt_rule(cell(36, 6, 1, 0.1, 0.8)).startswith("INSUFFICIENT"))
    check("few tickers insufficient",
          T.tilt_rule(cell(36, 4, 3, 0.1, 0.8)).startswith("INSUFFICIENT"))
    check("keep", T.tilt_rule(cell(36, 6, 3, 0.01, 0.8)).startswith("KEEP"))
    check("ci lower 0 rejects",
          T.tilt_rule(cell(36, 6, 3, 0.0, 0.8)).startswith("REJECT"))
    check("coverage low rejects",
          T.tilt_rule(cell(36, 6, 3, 0.05, 0.74)).startswith("REJECT"))
    check("coverage high rejects",
          T.tilt_rule(cell(36, 6, 3, 0.05, 0.86)).startswith("REJECT"))
    check("coverage edges keep",
          T.tilt_rule(cell(36, 6, 3, 0.05, 0.75)).startswith("KEEP")
          and T.tilt_rule(cell(36, 6, 3, 0.05, 0.85)).startswith("KEEP"))


def test_evaluate():
    pairs = [{"ticker": "T%d" % (i % 3), "as_of": "2026-0%d-01" % (i % 2 + 1),
              "horizon": "week", "is_naive": 2.0, "is_tilt": 1.0,
              "in_tilt": True} for i in range(6)]
    r = T.evaluate(pairs, reps=200)
    check("skill 0.5", abs(r["week"]["range_skill"] - 0.5) < 1e-9)
    check("coverage 1", r["week"]["coverage"] == 1.0)
    check("empty horizon", r["day"]["n"] == 0
          and r["day"]["range_skill"] is None)
    one = [dict(p, as_of="2026-08-14") for p in pairs]
    r1 = T.evaluate(one, reps=200)
    check("one cutoff gives no cutoff CI",
          r1["week"]["skill_ci_cutoff"] == [None, None])


def test_no_frozen_edit():
    ens = T.bs  # scoring module imported, ensemble untouched
    check("module loads", ens is not None)
    import ensemble
    check("v2 k frozen exact", ensemble.V2_BAND_K ==
          {"day": 1.15, "week": 1.28, "month": 1.20},
          str(ensemble.V2_BAND_K))

if __name__ == "__main__":
    for fn in (test_constants, test_rule, test_evaluate, test_no_frozen_edit):
        fn()
    print("%d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
