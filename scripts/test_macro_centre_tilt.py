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


def oil_rowset(last, ref):
    # Brent as stored: published = observed + 3 days, so at cutoff 2026-01-01
    # the usable last observation is 2025-12-29 (published 2026-01-01).
    return [(D("2025-10-26"), D("2025-10-29"), ref), (D("2025-12-29"), D("2026-01-01"), last)]


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
    series = {"oil": oil_rowset(94.0, 100.0), "fx": rowset(120.0, 100.0), "tbill": rowset(18.0, 20.0)}
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
             "mult": 1.0, "v2_sigma": 0},
            {"ticker": "M", "as_of": "2026-01-01", "horizon": "week", "real": 0.0, "naive_half": 5.0,
             "mult": 1.0, "v2_sigma": 0.01}]
    saved = (T.load_series, T.A.find_captures, T.R.build_rows, T.evaluate)
    T.load_series = lambda path: []
    calls = []
    def fake_find(a, b=None, c=None, rejects=None):
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
    check("scored missing-signal rows have their own heading, not the exclusions",
          "MISSING-SIGNAL ROWS (scored with the signal set to 0, not exclusions)" in out
          and "missing signal row M 2026-01-01 week" in out
          and "missing signal row" not in out.split("EXCLUSIONS (every one listed")[1].split("DESCRIPTIVE ONLY")[0]
          and "excluded: gap one" in out
          and out.index("MISSING-SIGNAL ROWS") < out.index("EXCLUSIONS (every one listed"), out[-900:])
    check("real sigma rejection stays in the exclusions", "Z 2026-01-01 week" in out.split("EXCLUSIONS (every one listed")[1])
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


def test_non_finite_values_rejected():
    import tempfile
    lines = ["observed_date,published_date,value",
             "2025-01-01,2025-01-02,100", "2025-02-01,2025-02-02,105",
             "2025-03-01,2025-03-02,nan", "2025-03-05,2025-03-06,inf",
             "2025-03-07,2025-03-08,-inf", "2025-03-09,2025-03-10,NaN"]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.csv")
        with open(p, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        rows = T.load_series(p)
        check("nan and inf rows are skipped, finite rows kept", [r[2] for r in rows] == [100.0, 105.0], str(rows))
        x, why = T.signal(rows, "2025-03-31", 0.01, "rel", window=20)
        check("a non-finite latest value no longer yields a zero signal without a reason, "
              "the last finite value is used", why is None and x == 1, str((x, why)))
        only_bad = os.path.join(d, "b.csv")
        with open(only_bad, "w") as fh:
            fh.write("observed_date,published_date,value\n2025-03-01,2025-03-02,nan\n2025-03-05,2025-03-06,inf\n")
        rows = T.load_series(only_bad)
        x, why = T.signal(rows, "2025-03-31", 0.01, "rel")
        check("only non-finite values: empty history, 'no usable value' reason", rows == [] and x == 0 and why == "no usable value", str((rows, x, why)))
        one = os.path.join(d, "o.csv")
        with open(one, "w") as fh:
            fh.write("observed_date,published_date,value\n2025-03-01,2025-03-02,100\n2025-03-20,2025-03-21,inf\n")
        rows = T.load_series(one)
        x, why = T.signal(rows, "2025-03-31", 0.01, "rel", window=60)
        check("inf latest is dropped, never a false +1", x == 0 and why is not None and "no usable value" in why, str((x, why)))


def test_zero_reference_relative_vs_absolute():
    """Fixed synthetic series: reference value 0 (finite), latest 5."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "z.csv")
        with open(p, "w") as fh:
            fh.write("observed_date,published_date,value\n2025-01-01,2025-01-02,0\n2025-03-01,2025-03-02,5\n")
        rows = T.load_series(p)
        check("a finite zero reference is kept by load_series", [r[2] for r in rows] == [0.0, 5.0], str(rows))
        try:
            x, why = T.signal(rows, "2025-03-31", 0.01, "rel", window=20)
            err = None
        except ZeroDivisionError as e:
            x, why, err = None, None, e
        check("relative change with a zero reference: no exception, (0, reason)",
              err is None and x == 0 and isinstance(why, str) and "zero reference" in why, str((x, why, err)))
        x, why = T.signal(rows, "2025-03-31", 0.01, "abs", window=20)
        check("absolute change with a zero reference stays valid (+5 > theta gives +1, no reason)", x == 1 and why is None, str((x, why)))
        x, why = T.signal(rows, "2025-03-31", 10.0, "abs", window=20)
        check("absolute change below theta is 0 with no reason", x == 0 and why is None, str((x, why)))


def test_seed_refused():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = T.main(["describe", "--captures", "/nonexistent", "--series-dir", "/nonexistent", "--seed", "1"])
    check("a non-registered seed is refused before loading inputs", rc == 2 and "refusing: --seed must be the registered 20261125, got 1" in buf.getvalue(), buf.getvalue())


def test_counts():
    pairs = [{"ticker": "A", "as_of": "d1", "horizon": "day"}, {"ticker": "B", "as_of": "d1", "horizon": "day"},
             {"ticker": "A", "as_of": "d2", "horizon": "day"}]
    L = T.count_lines(pairs)
    check("day counts", L[0] == "day: rows=3 cutoff clusters=2 tickers=2 rows all signals usable=3 rows with missing signals=0", L[0])
    check("week empty", L[1] == "week: rows=0 cutoff clusters=0 tickers=0 rows all signals usable=0 rows with missing signals=0")
    mp = [dict(p, missing=(i == 0)) for i, p in enumerate(pairs)]
    check("missing split", T.count_lines(mp)[0].endswith("usable=2 rows with missing signals=1"), T.count_lines(mp)[0])


def test_958l_short_row_coverage_and_gaps():
    import tempfile
    # 1: a CSV row that omits the value column is skipped, not a crash
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.csv")
        with open(p, "w") as fh:
            fh.write("observed_date,published_date,value\n2025-01-01,2025-01-02,100\n2025-02-01,2025-02-02\n2025-03-01,2025-03-02,110\n")
        try:
            rows = T.load_series(p)
            ok = [r[2] for r in rows] == [100.0, 110.0]
        except TypeError:
            ok = False
        check("a row with a missing value column is skipped and finite rows are kept", ok)
    # 2: coverage draws survive an undefined RangeSkill (zero naive IS)
    pairs = [{"as_of": "d%d" % i, "is_naive": 0.0, "is_ch": 1.0, "is_v2": 1.0, "in_ch": i % 2 == 0, "in_v2": True}
             for i in range(4)]
    sk, cov, dl = T.boot(pairs, 50, 7)
    check("coverage draws are kept when RangeSkill is undefined", len(cov) == 50 and sk == [] and dl == [], str((len(cov), sk, dl)))
    ev = T.evaluate([dict(p, horizon="day", ticker="A", m=0) for p in pairs], 50, 7)
    check("evaluate returns a coverage interval even with undefined RangeSkill",
          ev["day"]["cov_tilt_ci_cutoff"][0] is not None, str(ev["day"]["cov_tilt_ci_cutoff"]))
    pairs2 = [dict(p, is_naive=1.0) for p in pairs]
    sk2, cov2, dl2 = T.boot(pairs2, 50, 7)
    check("defined RangeSkill still fills all three lists", len(sk2) == len(cov2) == len(dl2) == 50)
    # 3: dropped naive-range horizons carry a reason
    R = T.R
    saved = (R.bs.score_capture, R.A._stage, R._extend_realised, R.price_reference, R.read_ohlc, R.sigmas, R.A._sigma60, R.bs.load_json)
    scored = [{"entrant": "naive-range", "ticker": "AAA.CA", "as_of": "2026-01-01", "horizon": "month", "status": "pending", "sessions_available": 7},
              {"entrant": "naive-range", "ticker": "AAA.CA", "as_of": "2026-01-01", "horizon": "week", "status": "matured", "dividend_gap": "split 2:1"},
              {"entrant": "naive-range", "ticker": "AAA.CA", "as_of": "2026-01-01", "horizon": "day", "status": "matured", "realized_move_pct": 0.5,
               "range_high_pct": 1.0, "range_low_pct": -1.0},
              {"entrant": "other", "ticker": "AAA.CA", "as_of": "2026-01-01", "horizon": "day", "status": "pending"}]
    R.bs.score_capture = lambda staged: (scored, [])
    R.A._stage = lambda cap, variant, tmp: cap
    R.price_reference = lambda dirs: {}
    R._extend_realised = lambda staged, px: False
    R.read_ohlc = lambda cap, d: []
    R.sigmas = lambda ohlc: {"s60": 0.01}
    R.A._sigma60 = lambda ens: 0.02
    R.bs.load_json = lambda path: {}
    try:
        rows, gaps = R.build_rows(["/x/cell60/2026-01-01/AAA.CA"], None)
    finally:
        (R.bs.score_capture, R.A._stage, R._extend_realised, R.price_reference, R.read_ohlc, R.sigmas, R.A._sigma60, R.bs.load_json) = saved
    check("rows membership unchanged: only the matured non-gap naive row", [r["horizon"] for r in rows] == ["day"], str(rows))
    check("pending horizon gets a reason with its sessions", "AAA.CA 2026-01-01 month: no matured row (pending, 7 sessions available)" in gaps, str(gaps))
    check("dividend-gap horizon gets a reason", "AAA.CA 2026-01-01 week: no matured row (dividend_gap split 2:1)" in gaps, str(gaps))
    check("other entrants and kept rows add no gap", len(gaps) == 2, str(gaps))


def test_958n_brent_lag_and_incomplete_captures():
    import tempfile
    # F2: the observed date of a Brent row must be <= cutoff - 3 days, even if published <= cutoff
    base = (D("2025-02-01"), D("2025-02-01"), 100.0)
    ok = (D("2025-03-28"), D("2025-03-28"), 110.0)
    late = (D("2025-03-29"), D("2025-03-29"), 100.0)
    x, why = T.signal([base, ok, late], "2025-03-31", 0.05, "rel", window=20, obs_lag_days=3)
    check("lag 3: row observed cutoff-3 is usable, cutoff-2 is not (last = 110, +10%)", x == 1 and why is None, str((x, why)))
    x, why = T.signal([base, ok, late], "2025-03-31", 0.05, "rel", window=20)
    check("lag 0 default keeps the old published-only rule (last = 100, 0%)", x == 0 and why is None, str((x, why)))
    x, why = T.signal([base, (D("2025-03-28"), D("2025-04-01"), 110.0)], "2025-03-31", 0.05, "rel", window=20, obs_lag_days=3)
    check("publication check is retained next to the lag", x == 0 and why is not None, str((x, why)))
    # tilt_rows applies the lag to oil only: an oil row observed 1 day before the cutoff but published early is ignored
    early_oil = [(D("2025-10-26"), D("2025-10-26"), 100.0), (D("2025-12-31"), D("2025-12-31"), 94.0)]
    series = {"oil": early_oil, "fx": rowset(120.0, 100.0), "tbill": rowset(18.0, 20.0)}
    row = {"ticker": "A", "as_of": "2026-01-01", "horizon": "week", "real": 0.0,
           "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02}
    pairs, listed, _x = T.tilt_rows([row], series)
    check("tilt_rows enforces the Brent lag: oil observed 12-31 is unusable at 01-01", len(listed) == 1 and "oil" in listed[0], str(listed))
    series["fx"] = [(D("2025-10-29"), D("2025-10-29"), 100.0), (D("2025-12-31"), D("2025-12-31"), 120.0)]
    pairs, listed, _x = T.tilt_rows([row], series)
    check("the other series are not lagged: fx observed 12-31 is usable", not any("fx" in l for l in listed), str(listed))
    # F1: incomplete captures reach the exclusion report, selection and dedup unchanged
    with tempfile.TemporaryDirectory() as d:
        def mk(cell, cutoff, tk, files):
            dp = os.path.join(d, "cell%d" % cell, cutoff, tk)
            os.makedirs(os.path.join(dp, "digest"), exist_ok=True)
            for f in files:
                path = os.path.join(dp, f)
                open(path, "w").write("{}")
            return dp
        full = ["manifest.json", "realised.json", "digest/ensemble.json"]
        good = mk(50, "2026-01-01", "AAA.CA", full)
        mk(50, "2026-01-01", "BBB.CA", ["manifest.json", "digest/ensemble.json"])
        mk(51, "2026-01-01", "CCC.CA", ["manifest.json", "realised.json"])
        mk(60, "2026-01-01", "DDD.CA", ["manifest.json", "digest/ensemble.json"])
        mk(56, "2026-01-01", "MANI.CA", ["manifest.json"])  # manifest only: not a capture attempt
        mk(10, "2026-01-01", "EEE.CA", ["manifest.json", "realised.json"])
        runlvl = os.path.join(d, "cell55-run")  # run-level manifest, not capture-shaped
        os.makedirs(runlvl)
        open(os.path.join(runlvl, "manifest.json"), "w").write("{}")
        for cell, tk in ((47, "H1.CA"), (48, "H2.CA"), (90, "H3.CA"), (91, "H4.CA")):
            mk(cell, "2026-01-01", tk, ["manifest.json", "realised.json"])
        rej = []
        caps = T.A.find_captures([d], 48, 90, rejects=rej)
        check("eligible selection unchanged", caps == [good], str(caps))
        check("incomplete in-window captures listed with the missing file",
              sorted(r.split("cell")[1][:2] + (" realised" if "missing realised.json" in r and "ensemble" not in r else " ensemble" if "missing digest/ensemble.json" in r and "realised" not in r else " both") for r in rej) == ["48 ensemble", "50 realised", "51 ensemble", "60 realised", "90 ensemble"], str(rej))
        check("out-of-window cell 10 is not listed", not any("cell55" in r or "cell56" in r for r in rej) and not any("cell10" in r or "cell47" in r or "cell91" in r for r in rej))
        check("no rejects list gives the same selection", T.A.find_captures([d], 48, 90) == [good])
        for nm, v in T.SERIES.items():
            with open(os.path.join(d, v[0]), "w") as fh:
                fh.write("observed_date,published_date,value\n")
        saved = (T.A.find_captures, T.R.build_rows)
        def fake_find(a, b=None, c=None, rejects=None):
            if rejects is not None:
                rejects.append("incomplete capture /x/cell50/2026-01-01/BBB.CA: missing realised.json")
            return []
        T.A.find_captures = fake_find
        T.R.build_rows = lambda caps, allc, repairs, info: ([], [])
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                T.main(["describe", "--captures", d, "--series-dir", d])
        finally:
            T.A.find_captures, T.R.build_rows = saved
        out = buf.getvalue()
        check("describe lists the incomplete capture under EXCLUSIONS and counts it",
              "excluded: incomplete capture /x/cell50/2026-01-01/BBB.CA: missing realised.json" in out.split("EXCLUSIONS")[1]
              and "1 incomplete captures" in out, out[:600])


def run_all():
    for fn in (test_constants, test_signal_boundaries, test_point_in_time_and_missing,
               test_composite_and_centre, test_refusal, test_reps_and_order, test_build_rows_gaps_and_repairs, test_seed_refused, test_non_finite_values_rejected, test_counts, test_958l_short_row_coverage_and_gaps, test_zero_reference_relative_vs_absolute, test_958n_brent_lag_and_incomplete_captures):
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
