#!/usr/bin/env python3
"""Tests for benchmarks/score_day_k_challenger_594.py (INS-IMPROVE-001 P1).
Standalone, stdlib only: python3 scripts/test_day_k_challenger_594.py
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
    "dayk", os.path.join(ROOT, "benchmarks",
                         "score_day_k_challenger_594.py"))
D = importlib.util.module_from_spec(spec)
sys.modules["dayk"] = D
spec.loader.exec_module(D)


def test_k_table():
    k = D.challenger_k()
    check("day is naive k", k["day"] == D.ens_mod.V2_NAIVE_K)
    check("week/month stay frozen",
          k["week"] == D.ens_mod.V2_BAND_K["week"]
          and k["month"] == D.ens_mod.V2_BAND_K["month"])
    check("override applies", D.challenger_k({"day": 1.3})["day"] == 1.3)
    check("frozen table untouched",
          D.ens_mod.V2_BAND_K == {"day": 1.15, "week": 1.28,
                                  "month": 1.20})


def test_half_pct():
    ens = {"sigma60_daily": 0.02, "risk": {"level": "none"}}
    check("day half", abs(D.half_pct(ens, "day", 1.0) - 2.0) < 1e-9)
    check("week half", abs(D.half_pct(ens, "week", 1.0)
                           - 2.0 * math.sqrt(5)) < 1e-9)
    ens["risk"] = {"level": "shock"}
    check("risk mult applied",
          abs(D.half_pct(ens, "day", 1.0) - 3.0) < 1e-9)
    check("no sigma gives None", D.half_pct({}, "day", 1.0) is None)


def _cell(n, cov, delta):
    return {"n": n, "ch": {"coverage": cov},
            "ch_minus_v2_skill": {"point": delta}}


def test_rule():
    check("insufficient below 30",
          D.day_rule(_cell(29, 0.9, 0.1)).startswith("INSUFFICIENT"))
    check("keep", D.day_rule(_cell(30, 0.75, 0.0)).startswith("KEEP"))
    check("reject on coverage",
          D.day_rule(_cell(30, 0.74, 0.1)).startswith("REJECT"))
    check("reject on worsening",
          D.day_rule(_cell(30, 0.8, -0.01)).startswith("REJECT"))


if __name__ == "__main__":
    test_k_table()
    test_half_pct()
    test_rule()
    print("test_day_k_challenger_594: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
