"""Tests for benchmarks/score_regime_macro_tilt.py: fixed synthetic inputs."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "score_regime_macro_tilt", os.path.join(HERE, "..", "benchmarks", "score_regime_macro_tilt.py"))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def dec(d, bps):
    return {"published_date": d, "change_bps": bps, "source_url": "https://x/%s" % d, "source_name": "s"}


DECS = [dec("2024-03-06", 600.0), dec("2024-05-23", 0.0), dec("2025-04-17", -225.0)]


def mk(reg, h, base, real, half=2.0):
    return {"regime": reg, "horizon": h, "base": base, "ticker": "A.CA", "real": real, "half": half,
            "naive_half": 3.0, "key": "A.CA %s %s" % (base, h)}


def test_bands_and_counts():
    check("band edges", [T.band_of(x) for x in (0, 1, 47, 48, 90, 91, 102, None)]
          == [None, "train 1-47", "train 1-47", "descriptive 48-90", "descriptive 48-90", "untouched 91+", "untouched 91+", None])
    caps = ["/r/a-cell5/2024-03-31/A.CA", "/r/a-cell5/2024-03-31/B.CA", "/r/a-cell6/2024-06-30/A.CA",
            "/r/a-cell95/2025-06-30/A.CA", "/r/a-cell7/2023-12-29/A.CA", "/r/nocell/2024-06-30/A.CA"]
    o = T.capture_counts(caps, DECS)
    check("train: 4 captures, 3 with a regime, 1 without (no decision before 2023-12-29)",
          o["train 1-47"]["captures"] == 4 and o["train 1-47"]["with_regime"] == 3 and o["train 1-47"]["without_regime"] == 1, str(o))
    check("tightening 2 captures in 1 cluster; hold 1 in 1", o["train 1-47"]["by_regime"]["tightening"] == {"captures": 2, "cutoff_clusters": 1}
          and o["train 1-47"]["by_regime"]["hold"] == {"captures": 1, "cutoff_clusters": 1})
    check("untouched counted by path only, easing at 2025-06-30", o["untouched 91+"]["by_regime"] == {"easing": {"captures": 1, "cutoff_clusters": 1}})
    check("an unnumbered capture is in no band", sum(b["captures"] for b in o.values()) == 5)


def test_regime_rows_point_in_time():
    r = {"ticker": "A.CA", "as_of": "2024-03-06", "horizon": "day", "real": 0.1, "naive_half": 3.0, "mult": 1.0, "v2_sigma": 0.02}
    out, ex = T.regime_rows([r], DECS)
    check("a decision dated the cutoff does not count (next session)", not out and "no usable regime" in ex[0], str(ex))
    out, ex = T.regime_rows([dict(r, as_of="2024-03-07")], DECS)
    check("the next day it counts: tightening", len(out) == 1 and out[0]["regime"] == "tightening")
    out, ex = T.regime_rows([dict(r, as_of="2024-06-01")], DECS)
    check("a later hold flips the regime", out[0]["regime"] == "hold")
    out, ex = T.regime_rows([dict(r, as_of="2025-05-01")], DECS)
    check("a cut gives easing", out[0]["regime"] == "easing")
    out, ex = T.regime_rows([dict(r, v2_sigma=0, as_of="2024-06-01")], DECS)
    check("zero sigma excluded with a reason", not out and "v2_sigma" in ex[0])
    out, ex = T.regime_rows([dict(r, as_of="2024-06-01")], [])
    check("no decisions: excluded, never guessed", not out and "no usable regime" in ex[0])


def test_fit_grid_ties_and_independence():
    narrow = [mk("hold", "day", "d%d" % i, 0.1) for i in range(5)]       # tiny moves: narrower band scores better
    wide = [mk("easing", "day", "e%d" % i, 2.15) for i in range(5)]      # real just outside the v2 edge: 1.1 captures them
    tie = [mk("tightening", "day", "t%d" % i, 0.0, half=0.0) for i in range(3)]  # zero width: every multiplier scores the same
    w = T.fit_weights(narrow + wide + tie)
    check("narrower wins where moves are small", w["hold"] == 0.9, str(w))
    check("wider wins where moves exceed the band", w["easing"] == 1.1, str(w))
    check("an exact tie goes to 1.0", w["tightening"] == 1.0, str(w))
    check("a regime without rows is 1.0", T.fit_weights(narrow)["easing"] == 1.0)
    check("regimes are fitted independently", T.fit_weights(narrow + wide)["hold"] == 0.9 and T.fit_weights(wide)["hold"] == 1.0)
    check("grid and registered constants", T.GRID == (0.9, 1.0, 1.1) and T.TRAIN_CELLS == (1, 47) and T.DESC_CELLS == (48, 90) and T.MIN_CLUSTERS == 10)


def test_evaluate_identity_and_loop_bar():
    rows = [mk("hold", "week", "d%d" % (i % 4), 0.5 + 0.3 * i) for i in range(8)]
    res = T.evaluate(rows, {"hold": 1.0}, 50, 7)
    c = res["week"]
    check("multiplier 1.0 reproduces frozen v2 exactly", c["rs_ch"] == c["rs_v2"] and c["cov_ch"] == c["cov_v2"]
          and c["delta_ci_cutoff"] == [0.0, 0.0], str(c))
    res = T.evaluate(rows, {"hold": 0.9}, 50, 7)
    check("a narrower multiplier changes the band (coverage not above v2)", res["week"]["cov_ch"] <= res["week"]["cov_v2"])
    check("horizons without rows say so", res["day"] == {"n": 0})
    ok_cov = (0.70, 0.80)
    check("fewer than 10 clusters: counts only (None), whatever the CI", T.loop_bar(9, (0.5, 0.9), ok_cov) is None)
    check("10 clusters, all three conditions met", T.loop_bar(10, (0.01, 0.9), ok_cov) is True)
    check("lower bound exactly 0 is not above 0", T.loop_bar(10, (0.0, 0.9), ok_cov) is False)
    check("coverage CI must overlap [0.75, 0.85]", T.loop_bar(10, (0.1, 0.9), (0.86, 0.90)) is False and T.loop_bar(10, (0.1, 0.9), (0.60, 0.74)) is False)
    check("coverage CI touching 0.75 or 0.85 overlaps", T.loop_bar(10, (0.1, 0.9), (0.65, 0.75)) is True and T.loop_bar(10, (0.1, 0.9), (0.85, 0.95)) is True)
    check("coverage CI width must be at most 0.15", T.loop_bar(10, (0.1, 0.9), (0.70, 0.85)) is True and T.loop_bar(10, (0.1, 0.9), (0.70, 0.86)) is False)


def test_modes_and_verified_decisions():
    seen = {}
    saved = (T.A.find_captures, T.R.build_rows, T.M.load_decisions)
    T.A.find_captures = lambda roots, mn: ["/r/c-cell%d/2024-06-30/A.CA" % n for n in (1, 47, 48, 90, 91, 102)]
    def fake_build(caps, *a, **k):
        seen["caps"] = list(caps)
        return [], []
    T.R.build_rows = fake_build
    T.M.load_decisions = lambda p: (DECS, 0)
    try:
        for mode, expect in (("fit", ["/r/c-cell1/2024-06-30/A.CA", "/r/c-cell47/2024-06-30/A.CA"]),):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                T.main([mode, "--captures", "x"])
            check("fit reads cells 1-47 only", seen["caps"] == expect, str(seen))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = T.main(["describe", "--captures", "x"])
        check("describe without weights is refused", rc == 2 and "needs --weights" in buf.getvalue())
        seen.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            T.main(["counts", "--captures", "x"])
        check("counts never builds rows (no outcome loaded for any band)", "caps" not in seen)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = T.main(["fit", "--captures", "x", "--seed", "1"])
        check("a non-registered seed is refused", rc == 2 and "refusing" in buf.getvalue())
    finally:
        T.A.find_captures, T.R.build_rows, T.M.load_decisions = saved
    ds, n_rej = T.M.load_decisions(T.DECISIONS)
    dates = [d["published_date"] for d in ds]
    check("verified decisions file: 36 usable, none rejected", len(ds) == 36 and n_rej == 0)
    check("the two decisions absent from the calendar are not in the verified file", "2022-08-18" not in dates and "2023-02-02" not in dates)


def run_all():
    for fn in (test_bands_and_counts, test_regime_rows_point_in_time, test_fit_grid_ties_and_independence,
               test_evaluate_identity_and_loop_bar, test_modes_and_verified_decisions):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_score_regime_macro_tilt: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
