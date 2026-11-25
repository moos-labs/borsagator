#!/usr/bin/env python3
"""Tests for the #593 band calibration layer (INS-PUSH T3).

Pins the triage procedure end to end: the clean-row filter
(matured, non-gap-flagged per D-79-1), the centre correction
b = median residual clamped to the median half-width, the width
factor k = 80th percentile of |residual - b| / half clamped to
[0.5, 2.0], shrinkage toward the horizon pool (prior weight 10),
the n<10 fallbacks (cell -> pool -> uncalibrated k=1, b=0), the
trailing W=30 window, the centre-formula basis filter, and the
guard alert predicate (n >= 30 outside 0.75-0.85).

Also pins the layer against the in-repo forward ledger — the
triage's own evidence base (48 matured, 12 gap-flagged, 36
clean): day as-published coverage 0.476 with median bias about
-8.5 pp, week 1.000 with bias about -22 pp, month n=0 — and the
calibrated in-window coverage landing in the 0.75-0.85 launch
tolerance. Finally pins the ensemble wiring: the layer is
formula-matched (no v2-594 rows yet, so nothing applies) and is
forbidden in 2-family backtest mode (#436 future-leak rule).

Standalone: `python3 scripts/test_band_calibration_593.py`
(stdlib only, no network).
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
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


bc = load_module(os.path.join(HERE, "band_calibration.py"), "bc_593")


def row(ticker="AAA", horizon="day", resid=-5.0, half=10.0, expected=0.0,
        status="matured", gap=None, formula=None, as_of="2026-11-10",
        sweep="sweeps/x"):
    return {"ticker": ticker, "horizon": horizon, "status": status,
            "dividend_gap": gap, "formula": formula,
            "as_of": as_of, "sweep": sweep,
            "expected_move_pct": expected,
            "realized_move_pct": expected + resid,
            "range_low_pct": expected - half,
            "range_high_pct": expected + half}


def rows(n, **kw):
    return [row(as_of="2026-11-%02d" % (i % 28 + 1),
                sweep="sweeps/%03d" % i, **kw) for i in range(n)]


def test_filter():
    check("matured clean row is clean", bc.is_clean_matured(row()))
    check("pending row excluded",
          not bc.is_clean_matured(row(status="pending")))
    check("gap-flagged row excluded (D-79-1)",
          not bc.is_clean_matured(row(gap="spans ex-date")))
    check("zero-half row excluded",
          not bc.is_clean_matured(row(half=0.0)))
    check("missing realised excluded",
          not bc.is_clean_matured({"status": "matured",
                                   "range_low_pct": -1.0,
                                   "range_high_pct": 1.0,
                                   "expected_move_pct": 0.0,
                                   "realized_move_pct": None}))


def test_centre_and_width():
    # 20 rows, residuals tightly around -8 with half 10: the raw
    # band covers everything (|resid| <= 10) but the centre is
    # biased; after recentering, z is small and k clamps low.
    rs = []
    for i, res in enumerate([-9, -8, -7, -9, -8, -7, -9, -8, -7, -8] * 2):
        rs.append(row(resid=float(res), half=10.0,
                      as_of="2026-11-%02d" % (i + 1), sweep="s%02d" % i))
    cal = bc.compute_calibration(rs)
    e = cal["cells"][("AAA", "day")]
    check("cell applies at n=20", e["calibrated"] and e["basis"] == "cell",
          repr(e))
    check("b is the median bias (-8)", abs(e["b"] - (-8.0)) < 1e-9,
          repr(e["b"]))
    check("k clamps to the 0.5 floor", abs(e["k"] - 0.5) < 1e-9,
          repr(e["k"]))
    check("calibrated coverage is 1.0 in-window",
          e["coverage_calibrated"] == 1.0, repr(e["coverage_calibrated"]))


def test_clamps():
    # Residuals far beyond the band: b clamps to the median half,
    # k clamps to the 2.0 ceiling.
    rs = rows(12, resid=-50.0, half=10.0)
    cal = bc.compute_calibration(rs)
    e = cal["cells"][("AAA", "day")]
    check("b clamped to median half-width", e["b"] == -10.0, repr(e["b"]))
    check("k clamped to 2.0 ceiling", e["k"] == 2.0, repr(e["k"]))


def test_shrinkage():
    # Ticker AAA day: 10 rows resid -20 (half 10, so b clamps -10,
    # z = 1.0, k = 1.0). Ticker BBB day: 20 rows resid 0 (b 0,
    # k -> 0.5 floor). Pool (30 rows): median resid is 0-heavy...
    a = [row(ticker="AAA", resid=-20.0, half=10.0,
             as_of="2026-11-%02d" % (i + 1), sweep="a%02d" % i)
         for i in range(10)]
    b = [row(ticker="BBB", resid=0.0, half=10.0,
             as_of="2026-11-%02d" % (i + 1), sweep="b%02d" % i)
         for i in range(20)]
    cal = bc.compute_calibration(a + b)
    pool = cal["pools"]["day"]
    ea = cal["cells"][("AAA", "day")]
    check("pool calibrated at n=30", pool["calibrated"] and pool["n"] == 30,
          repr(pool))
    want_b = (10 * -10.0 + 10 * pool["b"]) / 20.0
    check("cell b shrunk toward pool by prior weight 10",
          abs(ea["b"] - want_b) < 1e-9,
          "%r vs %r" % (ea["b"], want_b))
    check("shrunk b strictly between cell and pool fits",
          min(-10.0, pool["b"]) < ea["b"] < max(-10.0, pool["b"]),
          repr(ea["b"]))


def test_fallbacks():
    # Cell n=5 with a qualifying pool (BBB n=15): basis "pool".
    a = rows(5, ticker="AAA", resid=-4.0, half=10.0)
    b = rows(15, ticker="BBB", resid=-4.0, half=10.0)
    cal = bc.compute_calibration(a + b)
    ea = cal["cells"][("AAA", "day")]
    check("small cell falls back to pool",
          ea["basis"] == "pool" and ea["calibrated"], repr(ea))
    check("pool fallback carries pool b/k",
          ea["b"] == cal["pools"]["day"]["b"]
          and ea["k"] == cal["pools"]["day"]["k"], repr(ea))
    # Nothing qualifies anywhere: uncalibrated k=1, b=0.
    cal2 = bc.compute_calibration(rows(6, ticker="CCC", horizon="month",
                                       resid=-4.0, half=10.0))
    em = cal2["cells"][("CCC", "month")]
    check("thin pool falls back to uncalibrated",
          not em["calibrated"] and em["basis"] == "none"
          and em["k"] == 1.0 and em["b"] == 0.0, repr(em))
    # Empty input: no cells, pools report n=0 uncalibrated.
    cal3 = bc.compute_calibration([])
    check("empty input has no cells", cal3["cells"] == {})
    check("empty pool is uncalibrated",
          cal3["pools"]["day"] == {"n": 0, "b": 0.0, "k": 1.0,
                                   "calibrated": False},
          repr(cal3["pools"]["day"]))


def test_window():
    # 40 rows: the oldest 10 are wild, the trailing 30 are tame.
    # The fit must see only the trailing W=30.
    old = [row(resid=90.0, half=10.0, as_of="2026-10-%02d" % (i + 1),
               sweep="old%02d" % i) for i in range(10)]
    new = [row(resid=-2.0, half=10.0, as_of="2026-11-%02d" % (i + 1),
               sweep="new%02d" % i) for i in range(30)]
    cal = bc.compute_calibration(old + new)
    e = cal["cells"][("AAA", "day")]
    check("window caps the cell at W=30", e["n"] == 30, repr(e["n"]))
    check("window drops the wild old rows", e["b"] == -2.0, repr(e["b"]))


def test_formula_basis():
    v1 = rows(15, resid=-9.0, half=10.0, formula="v1")
    v2 = rows(15, resid=-1.0, half=10.0, formula="v2-594")
    cal = bc.compute_calibration(v1 + v2, formula="v2-594")
    e = cal["cells"][("AAA", "day")]
    check("formula fit uses only same-formula rows",
          e["n"] == 15 and abs(e["b"] - (-1.0)) < 1e-9, repr(e))
    cal_all = bc.compute_calibration(v1 + v2)
    check("no formula filter pools all rows",
          cal_all["cells"][("AAA", "day")]["n"] == 30,
          repr(cal_all["cells"][("AAA", "day")]["n"]))


def test_apply_and_alerts():
    entry = {"calibrated": True, "b": -8.0, "k": 0.5}
    c, h, applied = bc.apply_calibration(0.0, 20.0, entry)
    check("apply recentres and rescales",
          applied and c == -8.0 and h == 10.0, repr((c, h, applied)))
    c, h, applied = bc.apply_calibration(0.0, 20.0,
                                         {"calibrated": False,
                                          "b": -8.0, "k": 0.5})
    check("uncalibrated entry leaves the band unchanged",
          not applied and c == 0.0 and h == 20.0, repr((c, h, applied)))
    c, h, applied = bc.apply_calibration(1.0, 2.0, None)
    check("missing entry leaves the band unchanged",
          not applied and (c, h) == (1.0, 2.0), repr((c, h, applied)))
    # Alert predicate: n >= 30 and as-published coverage outside
    # [0.75, 0.85].
    def cell(ticker, n, cov):
        return {"ticker": ticker, "horizon": "day", "n": n,
                "coverage_before": cov}
    cal = {"cells": {("AAA", "day"): cell("AAA", 30, 0.50),
                     ("BBB", "day"): cell("BBB", 29, 0.50),
                     ("CCC", "day"): cell("CCC", 30, 0.80),
                     ("DDD", "day"): cell("DDD", 30, 0.90)}}
    alerts = bc.alert_cells(cal)
    check("alerts fire only for n>=30 outside tolerance",
          [a["ticker"] for a in alerts] == ["AAA", "DDD"], repr(alerts))
    table = bc.calibration_table(
        bc.compute_calibration(rows(12, resid=-5.0, half=10.0)))
    check("table has header + one row per cell",
          len(table) == 3 and "Coverage" in table[0]
          and table[2].startswith("| AAA | day | 12 |"), repr(table))


def test_real_ledger():
    path = os.path.join(ROOT, "ledger", "ledger.json")
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    cal = bc.compute_calibration(doc["forecasts_detail"])
    day_n = sum(e["n"] for (t, h), e in cal["cells"].items() if h == "day")
    week_n = sum(e["n"] for (t, h), e in cal["cells"].items() if h == "week")
    check("ledger clean day n=21 (triage evidence base)",
          day_n == 21, repr(day_n))
    check("ledger clean week n=15", week_n == 15, repr(week_n))
    check("ledger month has no cells (n=0)",
          all(h != "month" for (t, h) in cal["cells"]))
    poul_day = cal["cells"].get(("POUL.CA", "day"))
    check("POUL day cell exists", poul_day is not None)
    if poul_day:
        check("POUL day as-published coverage is the triage's ~0.476",
              poul_day["coverage_before"] is not None
              and poul_day["coverage_before"] < 0.60,
              repr(poul_day["coverage_before"]))
        check("POUL day bias is negative (bands centred too high)",
              poul_day["b"] < 0, repr(poul_day["b"]))
        check("POUL day calibrated coverage lands in 0.75-0.85",
              poul_day["coverage_calibrated"] is not None
              and 0.75 <= poul_day["coverage_calibrated"] <= 0.85,
              repr(poul_day["coverage_calibrated"]))
    poul_week = cal["cells"].get(("POUL.CA", "week"))
    check("POUL week cell exists", poul_week is not None)
    if poul_week:
        check("POUL week calibrated coverage lands in 0.75-0.85",
              poul_week["coverage_calibrated"] is not None
              and 0.75 <= poul_week["coverage_calibrated"] <= 0.85,
              repr(poul_week["coverage_calibrated"]))
        check("POUL week width shrinks (k < 1: bands were too wide)",
              poul_week["k"] < 1.0, repr(poul_week["k"]))


def test_ensemble_wiring():
    ens = load_module(os.path.join(HERE, "ensemble.py"), "ens_593")
    check("ensemble carries the v2-594 formula tag",
          ens.FORMULA_TAG == "v2-594", repr(ens.FORMULA_TAG))
    # The committed ledger predates the tag (all rows are the
    # retired centre's), so the layer must apply NOTHING today.
    check("no same-formula rows yet: calibration applies nothing",
          ens._load_band_calibration() == {},
          repr(ens._load_band_calibration()))
    # Backtest mode forbids the layer outright (#436 leak rule).
    os.environ["BORSAGATOR_BACKTEST_TWO_FAMILY"] = "1"
    try:
        check("backtest mode disables the calibration layer",
              ens._load_band_calibration() == {})
    finally:
        del os.environ["BORSAGATOR_BACKTEST_TWO_FAMILY"]


if __name__ == "__main__":
    test_filter()
    test_centre_and_width()
    test_clamps()
    test_shrinkage()
    test_fallbacks()
    test_window()
    test_formula_basis()
    test_apply_and_alerts()
    test_real_ledger()
    test_ensemble_wiring()
    print("PASS band-calibration-593: %s" % CHECKS)
    print("CHECKS pass=%d fail=%d" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
