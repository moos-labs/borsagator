"""Tests for benchmarks/score_macro_centre_tilt.py: fixed synthetic inputs."""
import contextlib
import datetime
import importlib.util
import io
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "score_macro_centre_tilt", os.path.join(HERE, "..", "benchmarks", "score_macro_centre_tilt.py"))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def D(s):
    return datetime.date.fromisoformat(s)


def rowset(last, ref, pub_last="2026-01-01", pub_ref="2025-10-01"):
    # last observed 2026-01-01, ref observed 63 days earlier (2025-10-30)
    return [(D("2025-10-30"), D(pub_ref), ref), (D("2026-01-01"), D(pub_last), last)]


def test_constants():
    check("S", T.S == 0.10)
    check("window", T.WINDOW_DAYS == 63)
    check("thetas", (T.SERIES["oil"][1], T.SERIES["fx"][1], T.SERIES["tbill"][1]) == (0.05, 0.02, 1.0))
    check("signs", (T.SERIES["oil"][3], T.SERIES["fx"][3], T.SERIES["tbill"][3]) == (-1, 1, -1))


def test_signal_boundaries():
    s = T.signal
    check("rel just above theta is +1", s(rowset(105.01, 100.0), "2026-01-01", 0.05, "rel")[0] == 1)
    check("rel exactly theta is 0", s(rowset(105.0, 100.0), "2026-01-01", 0.05, "rel")[0] == 0)
    check("rel just below -theta is -1", s(rowset(94.99, 100.0), "2026-01-01", 0.05, "rel")[0] == -1)
    check("rel exactly -theta is 0", s(rowset(95.0, 100.0), "2026-01-01", 0.05, "rel")[0] == 0)
    check("abs just above 1.0 is +1", s(rowset(21.01, 20.0), "2026-01-01", 1.0, "abs")[0] == 1)
    check("abs exactly 1.0 is 0", s(rowset(21.0, 20.0), "2026-01-01", 1.0, "abs")[0] == 0)
    check("abs below -1.0 is -1", s(rowset(18.99, 20.0), "2026-01-01", 1.0, "abs")[0] == -1)


def test_point_in_time_and_missing():
    s = T.signal
    # latest row published after the cutoff is not usable: only the older row is usable, no 63-day reference
    x, why = s(rowset(120.0, 100.0, pub_last="2026-01-02"), "2026-01-01", 0.05, "rel")
    check("unpublished latest row not used, missing listed", x == 0 and why is not None, why)
    x, why = s(rowset(120.0, 100.0, pub_last="2026-01-01"), "2026-01-01", 0.05, "rel")
    check("published on cutoff day is usable", x == 1 and why is None)
    x, why = s([], "2026-01-01", 0.05, "rel")
    check("no rows is missing", x == 0 and why == "no usable value")
    # reference exactly 63 days before is usable, 62 days is not
    rows62 = [(D("2025-10-31"), D("2025-10-31"), 100.0), (D("2026-01-01"), D("2026-01-01"), 120.0)]
    x, why = s(rows62, "2026-01-01", 0.05, "rel")
    check("62 days is not enough history", x == 0 and why is not None)
    rows63 = [(D("2025-10-30"), D("2025-10-30"), 100.0), (D("2026-01-01"), D("2026-01-01"), 120.0)]
    check("63 days is enough", s(rows63, "2026-01-01", 0.05, "rel")[0] == 1)


def test_composite_and_centre():
    dirs = [v[3] for v in T.SERIES.values()]
    check("all up: -1 +1 -1 = -1/3", abs(T.composite([1, 1, 1], dirs) - (-1 / 3.0)) < 1e-12)
    check("oil down, fx up, tbill down = 1", abs(T.composite([-1, 1, -1], dirs) - 1.0) < 1e-12)
    check("all zero is 0", T.composite([0, 0, 0], dirs) == 0)
    # tilt_rows: centre = S x m x v2 half, width equals v2
    series = {"oil": rowset(94.0, 100.0), "fx": rowset(120.0, 100.0), "tbill": rowset(18.0, 20.0)}
    row = {"ticker": "A", "as_of": "2026-01-01", "horizon": "week", "real": 0.0,
           "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02}
    pairs, listed, _x = T.tilt_rows([row], series)
    p = pairs[0]
    v2h = T.R.half_pct(0.02, "week", T.ens_mod.V2_BAND_K["week"], 1.0)
    check("m is 1", abs(p["m"] - 1.0) < 1e-12 and not listed)
    check("centre is 0.10 x v2 half", abs(p["centre"] - 0.10 * v2h) < 1e-12, str(p["centre"]))
    edge = dict(row, real=0.10 * v2h + v2h)
    check("edge of tilted band inclusive", T.tilt_rows([edge], series)[0][0]["in_ch"])
    out = dict(row, real=0.10 * v2h + v2h + 1e-6)
    check("just outside tilted band misses", not T.tilt_rows([out], series)[0][0]["in_ch"])
    want = T.bs.winkler_is(edge["real"], p["centre"] - v2h, p["centre"] + v2h)
    check("interval score uses the tilted band", T.tilt_rows([edge], series)[0][0]["is_ch"] == want
          and want != T.R.row_is(edge, v2h))
    check("v2 band stays centred on 0", T.tilt_rows([edge], series)[0][0]["in_v2"] is False)
    miss = {"oil": [], "fx": series["fx"], "tbill": series["tbill"]}
    pairs, listed, _x = T.tilt_rows([row], miss)
    check("missing signal set to 0 and listed", len(listed) == 1 and "oil" in listed[0]
          and abs(pairs[0]["m"] - 2 / 3.0) < 1e-12, str(listed))
    zp, zl, zd = T.tilt_rows([dict(row, v2_sigma=0), dict(row, ticker="B", v2_sigma=None)], series)
    check("zero/missing v2 sigma rows dropped from pairs", zp == [])
    check("v2 sigma exclusions listed with ticker cutoff horizon reason",
          len(zd) == 2 and "A 2026-01-01 week" in zd[0] and "v2_sigma" in zd[0] and "B 2026-01-01 week" in zd[1], str(zd))
    check("v2 sigma exclusions are not missing-signal rows", zl == [])
    check("usable row not flagged missing", pairs[0]["missing"] is True and
          T.tilt_rows([row], series)[0][0]["missing"] is False)


def test_refusal():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc1 = T.main(["describe", "--captures", "x", "--min-cell", "47"])
        rc2 = T.main(["describe", "--captures", "x", "--max-cell", "91"])
    check("refuses cells outside 48-90", rc1 == 2 and rc2 == 2 and buf.getvalue().count("refusing") == 2)


def test_reps_and_order():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = T.main(["describe", "--captures", "/nonexistent", "--series-dir", "/nonexistent", "--reps", "4999"])
    check("non-5000 reps refused before loading inputs", rc == 2 and "refusing" in buf.getvalue())
    buf3 = io.StringIO()
    with contextlib.redirect_stdout(buf3):
        rc3 = T.main(["describe", "--captures", "/nonexistent", "--series-dir", "/nonexistent", "--reps", "5001"])
    check("5001 reps also refused", rc3 == 2 and "refusing" in buf3.getvalue())
    rows = [{"ticker": "Z", "as_of": "2026-01-01", "horizon": "week", "real": 0.0, "naive_half": 5.0,
             "mult": 1.0, "v2_sigma": 0}]
    saved = (T.load_series, T.A.find_captures, T.R.build_rows, T.evaluate)
    T.load_series = lambda path: []
    calls = []
    def fake_find(a, b=None, c=None):
        calls.append((b, c))
        return []
    T.A.find_captures = fake_find
    def fake_build(caps, allc, repairs=None, info=None):
        info.append("y: tilt-technicals day: skipped note")
        repairs.append("x: realised window rebuilt to 21 sessions from price.csv")
        return rows, ["gap one"]
    T.R.build_rows = fake_build
    seen = []

    def fake_eval(pairs, reps, seed):
        seen.append(buf2.getvalue())
        return saved[3](pairs, 5, seed)
    T.evaluate = fake_eval
    buf2 = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf2):
            rc = T.main(["describe", "--captures", "x"])
    finally:
        T.load_series, T.A.find_captures, T.R.build_rows, T.evaluate = saved
    out = buf2.getvalue()
    check("main ok", rc == 0, out[:200])
    check("exclusions printed before evaluate", seen and "Z 2026-01-01 week" in seen[0] and "excluded: gap one" in seen[0])
    check("cell bounds passed to the dedup step, unbounded call kept for references",
          (None, None) in calls and (T.MIN_CELL, T.MAX_CELL) in calls, str(calls))
    check("repair notice is listed as repaired, not as an exclusion",
          "REPAIRED (scored, not excluded)" in out and "x: realised window rebuilt" in out
          and "excluded: x: realised window rebuilt" not in out and "excluded: gap one" in out)
    check("informational lines are printed under INFO, never as excluded:",
          "INFO (per-capture notes" in out and "y: tilt-technicals day: skipped note" in out
          and "excluded: y: tilt-technicals" not in out)
    check("counts split usable vs missing", "rows all signals usable=0 rows with missing signals=0" in out and "1 v2_sigma exclusions" in out)


def test_build_rows_gaps_and_repairs():
    R = T.R
    saved = (R.bs.score_capture, R.A._stage, R._extend_realised, R.price_reference, R.read_ohlc, R.sigmas)
    R.bs.score_capture = lambda staged: ([], ["cap-rejected: manifest ticker/cutoff differs from cell path"])
    R.A._stage = lambda cap, variant, tmp: cap
    R.price_reference = lambda dirs: {}
    R._extend_realised = lambda staged, px: staged.endswith("fixed")
    R.read_ohlc = lambda cap, d: []
    R.sigmas = lambda ohlc: {"s60": None}
    try:
        reps = []
        rows, gaps = R.build_rows(["/x/cell60/2026-01-01/AAA.CA", "/x/cell61/2026-01-01/BBB.CA.fixed"], None, reps)
        check("score_capture rejection reasons reach the gap list", gaps.count("cap-rejected: manifest ticker/cutoff differs from cell path") == 2, str(gaps))
        check("repair goes to the repairs list, once", len(reps) == 1 and "rebuilt to 21 sessions" in reps[0] and "BBB.CA.fixed" in reps[0], str(reps))
        check("repair is not among the exclusions", not any("rebuilt to 21" in g for g in gaps))
        # scored capture (rows returned): its lines are info, not exclusions
        R.bs.score_capture = lambda staged: ([{"entrant": "other"}], ["note: per-entrant skip"])
        inf, reps3 = [], []
        rows3, gaps3 = R.build_rows(["/x/cell60/2026-01-01/AAA.CA"], None, reps3, inf)
        check("scored capture's lines go to info, not to gaps", gaps3 == [x for x in gaps3 if "per-entrant" not in x] and inf == ["note: per-entrant skip"], str((gaps3, inf)))
        buf_n = io.StringIO()
        with contextlib.redirect_stdout(buf_n):
            rows4, gaps4 = R.build_rows(["/x/cell60/2026-01-01/AAA.CA"], None)
        check("without an info list the scored capture's lines are dropped, not excluded", not any("per-entrant" in x for x in gaps4))
        check("the drop is visible as exactly one count line", buf_n.getvalue().count("note: 1 informational score_capture lines dropped") == 1 and buf_n.getvalue().count("\n") == 1, buf_n.getvalue())
        buf_p = io.StringIO()
        with contextlib.redirect_stdout(buf_p):
            R.build_rows(["/x/cell60/2026-01-01/AAA.CA"], None, [], [])
        check("no count line when an info list is passed", buf_p.getvalue() == "", buf_p.getvalue())
        R.bs.score_capture = lambda staged: ([{"entrant": "other"}], [])
        buf_z = io.StringIO()
        with contextlib.redirect_stdout(buf_z):
            R.build_rows(["/x/cell60/2026-01-01/AAA.CA"], None)
        check("no count line when nothing was dropped", buf_z.getvalue() == "")
        R.bs.score_capture = lambda staged: ([{"entrant": "other"}], ["note: per-entrant skip"])
        R.bs.score_capture = lambda staged: ([], ["cap-rejected: manifest ticker/cutoff differs from cell path"])
        rows, gaps2 = R.build_rows(["/x/cell61/2026-01-01/BBB.CA.fixed"], None)
        check("callers that pass no repairs list still see the notice in gaps (unchanged)", any("rebuilt to 21" in g for g in gaps2))
    finally:
        (R.bs.score_capture, R.A._stage, R._extend_realised, R.price_reference, R.read_ohlc, R.sigmas) = saved


def test_counts():
    pairs = [{"ticker": "A", "as_of": "d1", "horizon": "day"}, {"ticker": "B", "as_of": "d1", "horizon": "day"},
             {"ticker": "A", "as_of": "d2", "horizon": "day"}]
    L = T.count_lines(pairs)
    check("day counts", L[0] == "day: rows=3 cutoff clusters=2 tickers=2 rows all signals usable=3 rows with missing signals=0", L[0])
    check("week empty", L[1] == "week: rows=0 cutoff clusters=0 tickers=0 rows all signals usable=0 rows with missing signals=0")
    mp = [dict(p, missing=(i == 0)) for i, p in enumerate(pairs)]
    check("missing split", T.count_lines(mp)[0].endswith("usable=2 rows with missing signals=1"), T.count_lines(mp)[0])


def run_all():
    for fn in (test_constants, test_signal_boundaries, test_point_in_time_and_missing,
               test_composite_and_centre, test_refusal, test_reps_and_order, test_build_rows_gaps_and_repairs, test_counts):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_macro_centre_tilt: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
