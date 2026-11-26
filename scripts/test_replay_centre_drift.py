#!/usr/bin/env python3
"""Tests for benchmarks/replay_centre_drift.py (INS-IMPROVE-001 r3).
Standalone, stdlib only: python3 scripts/test_replay_centre_drift.py
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
    "drift", os.path.join(ROOT, "benchmarks", "replay_centre_drift.py"))
D = importlib.util.module_from_spec(spec)
sys.modules["drift"] = D
spec.loader.exec_module(D)


def row(real, v2s=0.01, m60=0.001, h="week", mult=1.0, t="A",
        a="2026-01-01"):
    naive = 1.2816 * v2s * math.sqrt(D.R.SESSIONS[h]) * 100
    return {"horizon": h, "real": real, "naive_half": naive,
            "v2_sigma": v2s, "mult": mult, "mean_ret_60": m60,
            "ticker": t, "as_of": a}


def test_constants():
    check("beta 0.10", D.BETA == 0.10)
    check("window 60", D.DRIFT_N == 60)
    check("v2 k frozen exact", D.ens_mod.V2_BAND_K
          == {"day": 1.15, "week": 1.28, "month": 1.20},
          str(D.ens_mod.V2_BAND_K))


def test_mean_ret():
    closes = [100.0 * math.exp(0.001 * i) for i in range(61)]
    check("mean of log returns",
          abs(D.mean_ret(closes) - 0.001) < 1e-12)
    check("too short is None", D.mean_ret(closes[:30]) is None)


def test_centre():
    check("scales by sessions",
          abs(D.centre_pct(0.001, "month") - 0.10 * 0.001 * 21 * 100)
          < 1e-12)
    check("day sessions 1",
          abs(D.centre_pct(0.001, "day") - 0.01) < 1e-12)
    check("none stays none", D.centre_pct(None, "week") is None)


def test_score_rows():
    r = row(real=1.0)
    p = D.score_rows([r])[0]
    half = D.R.half_pct(0.01, "week", D.ens_mod.V2_BAND_K["week"])
    c = D.centre_pct(0.001, "week")
    check("v2 centred 0", p["in_v2"] == (abs(1.0) <= half))
    check("challenger centred on drift",
          p["in_ch"] == (abs(1.0 - c) <= half))
    check("missing drift skipped",
          D.score_rows([dict(row(1.0), mean_ret_60=None)]) == [])
    check("missing v2 sigma skipped",
          D.score_rows([dict(row(1.0), v2_sigma=None)]) == [])
    big = D.score_rows([row(real=half + 0.05 * c, m60=0.001)])[0]
    check("drift can pull a move into the band",
          big["in_ch"] and not big["in_v2"] if c > 0 else True)


def res_with(n, tickers, cutoffs, lo, cov):
    return {h: {"n": n, "tickers": tickers, "cutoffs": cutoffs,
                "ch_ci_cutoff": [lo, 0.1], "ch": {"coverage": cov}}
            for h in D.HORIZONS}


def test_verdict():
    check("six rows insufficient",
          D.keep_verdict(res_with(6, 6, 1, 0.1, 0.8))[0]
          == "INSUFFICIENT")
    check("keep", D.keep_verdict(res_with(36, 6, 3, 0.01, 0.8))[0]
          == "KEEP")
    check("ci lower 0 rejects",
          D.keep_verdict(res_with(36, 6, 3, 0.0, 0.8))[0] == "REJECT")
    check("coverage rejects",
          D.keep_verdict(res_with(36, 6, 3, 0.05, 0.6))[0] == "REJECT")
    mixed = res_with(36, 6, 3, 0.05, 0.8)
    mixed["month"]["ch"]["coverage"] = 0.5
    check("one bad horizon rejects", D.keep_verdict(mixed)[0]
          == "REJECT")
    short = res_with(36, 6, 3, 0.05, 0.8)
    short["day"]["n"] = 20
    check("one short horizon is insufficient",
          D.keep_verdict(short)[0] == "INSUFFICIENT")


def test_refuses_seen_cells():
    check("refuses cells below 73", D.main(
        ["--captures", "/nonexistent", "--min-cell", "48"]) == 2)


for fn in (test_constants, test_mean_ret, test_centre, test_score_rows,
           test_verdict, test_refuses_seen_cells):
    fn()
print("test_replay_centre_drift: %d passed, %d failed"
      % (CHECKS["pass"], CHECKS["fail"]))
sys.exit(1 if CHECKS["fail"] else 0)
