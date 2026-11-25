#!/usr/bin/env python3
"""Tests for the #594 ensemble v2 (INS-PUSH T1 recalibration).

Freezes the v2 contract so a later refactor cannot silently move
it: the frozen constants, the band sessions pinned to the ledger's
scoring sessions, the Winkler interval score and the RangeSkill
gate (including the T1 baseline anchors on the 41 scored #436
cells), the paired-bootstrap CI, and the sigma60 4-tuple from
realized_sigma. The adoption test itself (cells 48-72 + forward
sweeps) scores these frozen parameters; this file only pins them.

Standalone: `python3 scripts/test_ensemble_v2_594.py` (stdlib only,
no network, no model).
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL %s %s" % (name, detail))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_constants():
    ens = load_module(os.path.join(HERE, "ensemble.py"), "ens_v2")
    led = load_module(os.path.join(HERE, "ledger.py"), "led_v2")
    # Frozen band k, sessions and naive k.
    check("V2_BAND_K frozen",
          ens.V2_BAND_K == {"day": 1.15, "week": 1.28, "month": 1.20},
          repr(ens.V2_BAND_K))
    check("V2_NAIVE_K is the 80% z",
          ens.V2_NAIVE_K == 1.2816, repr(ens.V2_NAIVE_K))
    # Band sessions are the ledger's scoring sessions — the
    # published range is the scored range.
    check("V2_SESSIONS == ledger.DEFAULT_SESSIONS",
          ens.V2_SESSIONS == led.DEFAULT_SESSIONS,
          "%r vs %r" % (ens.V2_SESSIONS, led.DEFAULT_SESSIONS))
    # Kronos weight 0 at every horizon; technicals 0 on day and a
    # capped 0.2 tilt on week/month.
    check("Kronos weight 0 everywhere",
          all(ens.W["price-forecast"][h] == 0.0
              for h in ("day", "week", "month")))
    check("technicals day 0, week/month 0.20",
          ens.W["technicals"] == {"day": 0.0, "week": 0.20, "month": 0.20},
          repr(ens.W["technicals"]))
    check("tilt table frozen",
          ens.W["sentiment"] == {"day": 0.15, "week": 0.15, "month": 0.05}
          and ens.W["agent"] == {"day": 0.10, "week": 0.20, "month": 0.30}
          and ens.W["fundamentals"] == {"day": 0.0, "week": 0.0,
                                        "month": 0.25},
          repr(ens.W))
    # No measured-weights feedback: every factor is 1.0 and the
    # source is frozen-v2, whatever the ledger file says.
    w, src, info = ens._apply_measured_weights(
        {"price-forecast": {"day": 0.0, "week": 0.0, "month": 0.0},
         "technicals": {"day": 0.0, "week": 0.2, "month": 0.2}})
    check("weights_source frozen-v2", src == "frozen-v2", repr(src))
    check("all factors 1.0",
          all(v == 1.0 for v in info["factors"].values()),
          repr(info["factors"]))
    check("weights table returned unchanged", w == {
        "price-forecast": {"day": 0.0, "week": 0.0, "month": 0.0},
        "technicals": {"day": 0.0, "week": 0.2, "month": 0.2}})
    # expected_move() is the RETIRED v1 combine, kept verbatim —
    # the frozen backtest mirrors build their reference entrants
    # with it. It must NOT follow the v2 rule.
    check("expected_move() kept verbatim (v1 combine)",
          abs(ens.expected_move(0.1, 0.5, 0.02)
              - (0.6 * 0.1 + 0.4 * 0.5 * (1.28 * 0.02))) < 1e-12)


def test_winkler():
    sc = load_module(os.path.join(HERE, "backtest_score.py"), "bs_v2")
    # Inside the interval: score is the width.
    check("winkler inside is the width",
          sc.winkler_is(0.5, -1.0, 1.0) == 2.0)
    # Outside: width + 10x the distance (alpha 0.2).
    check("winkler below adds 10x distance",
          sc.winkler_is(-2.0, -1.0, 1.0) == 12.0)
    check("winkler above adds 10x distance",
          sc.winkler_is(3.0, -1.0, 1.0) == 22.0)
    # On the edge: no penalty.
    check("winkler on the edge is the width",
          sc.winkler_is(1.0, -1.0, 1.0) == 2.0)
    # A narrower band that still covers scores better; a narrower
    # band that misses scores much worse.
    check("winkler rewards a covering narrow band",
          sc.winkler_is(0.5, -0.5, 0.5) < sc.winkler_is(0.5, -1.0, 1.0))
    check("winkler punishes a missing narrow band",
          sc.winkler_is(2.0, -0.5, 0.5) > sc.winkler_is(2.0, -1.0, 1.0))


def test_range_skill_anchors():
    """T1's baseline numbers on the 41 scored #436 cells:
    ensemble IS 16.9 / 59.9 / 106.8 vs naive 8.2 / 23.1 / 30.7
    (day / week / month) give RangeSkill -1.06 / -1.59 / -2.48.
    The gate must call all three FAIL (and v2's centre-0 design
    target is about 0)."""
    sc = load_module(os.path.join(HERE, "backtest_score.py"), "bs_v2b")
    for h, ens_is, naive_is, want in (
            ("day", 16.9, 8.2, -1.06),
            ("week", 59.9, 23.1, -1.59),
            ("month", 106.8, 30.7, -2.48)):
        got = round(1 - ens_is / naive_is, 2)
        check("T1 RangeSkill anchor %s" % h, got == want,
              "got %r want %r" % (got, want))
        cell = {"n": 41, "range_skill": got,
                "range_skill_gap_ci": [-5.0, -1.0],
                "range_coverage": 0.80}
        check("T1 gate %s is FAIL" % h,
              sc.range_gate_decision(cell) == "FAIL",
              repr(cell))
    # The gate's own table: PASS needs skill > 0, CI low > 0,
    # coverage 75-85% at n >= 30.
    check("gate PASS at n=30, skill>0, CI>0, cov 0.80",
          sc.range_gate_decision(
              {"n": 30, "range_skill": 0.10,
               "range_skill_gap_ci": [0.02, 0.18],
               "range_coverage": 0.80}) == "PASS")
    check("gate FAIL when CI low <= 0",
          sc.range_gate_decision(
              {"n": 40, "range_skill": 0.10,
               "range_skill_gap_ci": [-0.01, 0.21],
               "range_coverage": 0.80}) == "FAIL")
    check("gate FAIL when coverage 0.90",
          sc.range_gate_decision(
              {"n": 40, "range_skill": 0.10,
               "range_skill_gap_ci": [0.02, 0.18],
               "range_coverage": 0.90}) == "FAIL")
    check("gate n<30 at n=29",
          sc.range_gate_decision(
              {"n": 29, "range_skill": 0.10,
               "range_skill_gap_ci": [0.02, 0.18],
               "range_coverage": 0.80}) == "n<30")
    check("gate FAIL when skill is None",
          sc.range_gate_decision(
              {"n": 40, "range_skill": None,
               "range_skill_gap_ci": [None, None],
               "range_coverage": 0.80}) == "FAIL")


def test_bootstrap_ci():
    sc = load_module(os.path.join(HERE, "backtest_score.py"), "bs_v2c")
    # Deterministic: the same inputs give the same CI.
    a = sc.bootstrap_gap_ci([8.0, 9.0, 7.0, 10.0], [9.0, 10.0, 8.0, 11.0])
    b = sc.bootstrap_gap_ci([8.0, 9.0, 7.0, 10.0], [9.0, 10.0, 8.0, 11.0])
    check("bootstrap CI deterministic", a == b, "%r vs %r" % (a, b))
    # A uniform +1 gap (naive IS 1 above the ensemble's) has a CI
    # entirely above 0.
    lo, hi = sc.bootstrap_gap_ci([9.0] * 30, [8.0] * 30)
    check("bootstrap CI above 0 for a uniform +1 gap",
          lo is not None and lo > 0, repr((lo, hi)))
    # A uniform -1 gap has a CI entirely below 0.
    lo, hi = sc.bootstrap_gap_ci([8.0] * 30, [9.0] * 30)
    check("bootstrap CI below 0 for a uniform -1 gap",
          hi is not None and hi < 0, repr((lo, hi)))
    # Empty inputs give (None, None), never a crash.
    check("bootstrap CI empty is (None, None)",
          sc.bootstrap_gap_ci([], []) == (None, None))
    check("bootstrap CI mismatched lengths is (None, None)",
          sc.bootstrap_gap_ci([1.0], [1.0, 2.0]) == (None, None))


def test_sigma60_tuple():
    ens = load_module(os.path.join(HERE, "ensemble.py"), "ens_v2d")
    # The default fallback returns a 4-tuple with sigma60 == sigma.
    got = ens.realized_sigma("NOPE.CA", base=100.0, ok={})
    check("default fallback sigma60 == sigma",
          isinstance(got, tuple) and len(got) == 4
          and got[0] == got[1] == 0.02,
          repr(got))


if __name__ == "__main__":
    test_constants()
    test_winkler()
    test_range_skill_anchors()
    test_bootstrap_ci()
    test_sigma60_tuple()
    print("PASS ensemble-v2-594: %s" % CHECKS)
    print("CHECKS pass=%d fail=%d" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
