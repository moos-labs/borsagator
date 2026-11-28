"""Tests for benchmarks/score_shrinkage_challenger.py: fixed synthetic inputs."""
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
    "score_shrinkage_challenger", os.path.join(HERE, "..", "benchmarks", "score_shrinkage_challenger.py"))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def series(n, start="2024-01-01", step=1.0, c0=100.0):
    d0 = datetime.date.fromisoformat(start)
    return [((d0 + datetime.timedelta(days=i)).isoformat(), c0 + step * i) for i in range(n)]


def test_constants():
    check("window", T.WINDOW == 250 and T.MIN_MOVES == 125)
    check("quantiles", (T.Q_LO, T.Q_HI) == (0.10, 0.90))
    check("grid", len(T.GRID) == 21 and T.GRID[0] == 0 and T.GRID[-1] == 1.0)
    check("threshold and freeze", T.MIN_COVERED == 100 and T.FREEZE == "2025-08-15")
    check("sessions", T.SESSIONS == {"day": 1, "week": 5, "month": 21})


def test_quantile():
    v = [0, 10, 20, 30, 40]
    check("q10 interpolates", abs(T.quantile(v, 0.10) - 4.0) < 1e-12)
    check("q90 interpolates", abs(T.quantile(v, 0.90) - 36.0) < 1e-12)
    check("single value", T.quantile([7], 0.9) == 7)
    check("empty is None", T.quantile([], 0.5) is None)


def test_baseline_window_and_history():
    cl = series(400)
    q_lo, q_hi, n = T.baseline(cl, cl[300][0], "day")
    check("window capped at 250", n == 250, str(n))
    # base date 124 sessions in: only 124 day moves exist (< 125)
    q_lo, q_hi, n = T.baseline(cl, cl[124][0], "day")
    check("124 moves is short", q_lo is None and n == 124, str(n))
    q_lo, q_hi, n = T.baseline(cl, cl[125][0], "day")
    check("125 moves is enough", q_lo is not None and n == 125, str(n))
    # month horizon needs 21 more sessions
    q_lo, q_hi, n = T.baseline(cl, cl[144][0], "month")
    check("month 144-21+1=124 moves is short", q_lo is None and n == 124, str(n))
    q_lo, q_hi, n = T.baseline(cl, cl[145][0], "month")
    check("month 125 moves enough", q_lo is not None and n == 125, str(n))


def test_no_lookahead():
    cl = series(400)
    a = T.baseline(cl, cl[300][0], "week")
    cl2 = cl[:301] + [(d, c * 3.0) for d, c in cl[301:]]
    b = T.baseline(cl2, cl[300][0], "week")
    check("closes after base date never change the baseline", a == b)
    cl3 = cl[:300] + [(cl[300][0], 1000.0)] + cl[301:]
    check("the base-date close is used", T.baseline(cl3, cl[300][0], "week") != a)


def test_realised_date():
    cl = series(30)
    check("week realised 5 sessions later", T.realised_date(cl, cl[10][0], "week") == cl[15][0])
    check("last session has no realised close", T.realised_date(cl, cl[29][0], "day") is None)
    check("exact last fits", T.realised_date(cl, cl[28][0], "day") == cl[29][0])


def test_mix_edges():
    lo, hi = T.mix_edges(2.0, -3.0, 4.0, 1.0, 1.0)
    check("weights 1 give v2", (lo, hi) == (-2.0, 2.0))
    lo, hi = T.mix_edges(2.0, -3.0, 4.0, 0.0, 0.0)
    check("weights 0 give baseline", (lo, hi) == (-3.0, 4.0))
    lo, hi = T.mix_edges(2.0, -3.0, 4.0, 0.5, 0.25)
    check("mixed", abs(lo - (-2.5)) < 1e-12 and abs(hi - 3.5) < 1e-12, str((lo, hi)))


def mkrow(h="day", rdate="2025-01-01", real=0.5, q=(-1.0, 1.0), half=2.0, base="2024-12-01"):
    return {"ticker": "A.CA", "as_of": base, "horizon": h, "real": real, "naive_half": 3.0, "mult": 1.0,
            "half": half, "q_lo": q[0], "q_hi": q[1], "rdate": rdate, "base": base, "key": "A.CA %s %s" % (base, h)}


def test_prepare_exclusions():
    cl = series(400)
    base = cl[300][0]
    row = {"ticker": "A.CA", "as_of": base, "horizon": "day", "real": 0.1, "naive_half": 3.0, "mult": 1.0, "v2_sigma": 0.02}
    out, ex = T.prepare([row], {"A.CA": cl})
    check("good row kept", len(out) == 1 and not ex and out[0]["rdate"] == cl[301][0])
    out, ex = T.prepare([dict(row, v2_sigma=0)], {"A.CA": cl})
    check("zero sigma listed", not out and "v2_sigma" in ex[0])
    out, ex = T.prepare([dict(row, as_of=cl[399][0])], {"A.CA": cl})
    check("no realised close listed", not out and "no realised close" in ex[0], str(ex))
    out, ex = T.prepare([dict(row, as_of=cl[50][0])], {"A.CA": cl})
    check("short history listed", not out and "short history" in ex[0], str(ex))
    out, ex = T.prepare([row], {})
    check("no price file listed", not out and "no price history" in ex[0])


def test_fit_threshold_and_freeze():
    ok = [mkrow(rdate="2025-08-14") for _ in range(100)]
    n, ex, w = T.fit_pooled(ok)
    check("100 covered fits", n == 100 and w is not None and not ex)
    n, ex, w = T.fit_pooled(ok[:99])
    check("99 covered does not fit", n == 99 and w is None)
    mixed = ok[:99] + [mkrow(rdate="2025-08-15")]
    n, ex, w = T.fit_pooled(mixed)
    check("freeze date itself is excluded", n == 99 and w is None and len(ex) == 1 and "after freeze date" in ex[0], str((n, ex)))
    mixed = ok + [mkrow(rdate="2025-10-29")]
    n, ex, w = T.fit_pooled(mixed)
    check("later close excluded, listed, fit still runs", n == 100 and len(ex) == 1 and w is not None)
    n, ex, w = T.fit_pooled(ok[:50] + [mkrow(rdate="2025-08-14", h="week") for _ in range(30)] + [mkrow(rdate="2025-08-14", h="month") for _ in range(19)])
    check("99 pooled across horizons does not fit", n == 99 and w is None, str(n))
    n, ex, w = T.fit_pooled(ok[:50] + [mkrow(rdate="2025-08-14", h="week") for _ in range(30)] + [mkrow(rdate="2025-08-14", h="month") for _ in range(20)])
    check("100 pooled across horizons fits one shared pair", n == 100 and w is not None and len(w) == 2, str(n))


def test_fit_picks_best_and_ties():
    # real always 0, v2 half 2 and baseline edges tight: baseline (weights 0) scores best
    rows = [mkrow(real=0.0, q=(-0.5, 0.5), half=2.0, rdate="2025-01-01") for _ in range(100)]
    n, ex, w = T.fit_pooled(rows)
    check("tight baseline wins weights 0", w == (0.0, 0.0), str(w))
    # real far outside both: wider is better, v2 half 5 vs baseline 1 -> weights 1
    rows = [mkrow(real=4.0, q=(-1.0, 1.0), half=5.0, rdate="2025-01-01") for _ in range(100)]
    n, ex, w = T.fit_pooled(rows)
    check("upper weight just covers the real, lower weight 0 (narrowest)", w == (0.0, 0.75), str(w))
    # identical edges: every weight ties -> larger weights (nearer v2)
    rows = [mkrow(real=0.0, q=(-2.0, 2.0), half=2.0, rdate="2025-01-01") for _ in range(100)]
    n, ex, w = T.fit_pooled(rows)
    check("ties go to larger weights", w == (1.0, 1.0), str(w))


def test_crossed_edges():
    r = mkrow(real=0.0, q=(3.0, 4.0), half=2.0)
    is_ch, inside, crossed = T.row_scores(r, 0.0, 0.0)
    check("q_lo above q_hi side: not crossed", crossed is False)
    r = mkrow(real=0.0, q=(5.0, -5.0), half=2.0)
    is_ch, inside, crossed = T.row_scores(r, 0.0, 0.0)
    r0 = mkrow(real=0.0, q=(1.0, 1.0), half=2.0)
    check("equal edges count as crossed", T.row_scores(r0, 0.0, 0.0)[2] is True)
    check("crossed edges fall back to v2", crossed and is_ch == T.bs.winkler_is(0.0, -2.0, 2.0))


def test_leave_out_folds():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmarks"))
    import score_shrinkage_leave_out as L
    rows = []
    for base, tk, real in (("2025-10-01", "A", 0.5), ("2025-10-01", "B", 5.0),
                           ("2025-11-01", "A", 0.2), ("2025-11-01", "B", 0.1)):
        r = mkrow(base=base, real=real)
        r["ticker"] = tk
        rows.append(r)
    f = dict(L.build_folds(rows, 1.0, 1.0, "base"))
    check("cutoff folds: all plus one per cutoff", sorted(f) == ["2025-10-01", "2025-11-01", "all"])
    check("leaving a cutoff out drops exactly its rows", f["all"]["n"] == 4 and f["2025-10-01"]["n"] == 2 and f["2025-11-01"]["n"] == 2)
    check("weights 1: challenger equals v2, diff 0", abs(f["all"]["diff"]) < 1e-12)
    t = dict(L.build_folds(rows, 1.0, 1.0, "ticker"))
    check("ticker folds drop that ticker only", t["A"]["n"] == 2 and t["B"]["n"] == 2)
    # real=5 sits outside v2 half 2: leaving B out leaves 2 covered rows, coverage 1.0
    check("coverage excludes the left-out ticker", abs(t["B"]["cov"] - 1.0) < 1e-12 and abs(t["A"]["cov"] - 0.5) < 1e-12, str(t))
    w0 = dict(L.build_folds(rows, 0.0, 0.0, "base"))["all"]
    check("weights 0 use the baseline edges, so diff is not 0 for these rows", abs(w0["diff"]) > 1e-9)


def test_refusals():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r1 = T.main(["fit", "--captures", "x", "--ohlcv-dir", "x", "--reps", "4999"])
        r2 = T.main(["fit", "--captures", "x", "--ohlcv-dir", "x", "--reps", "5001"])
        r3 = T.main(["fit", "--captures", "x", "--ohlcv-dir", "x", "--max-cell", "48"])
        r4 = T.main(["describe", "--captures", "x", "--ohlcv-dir", "x", "--min-cell", "47"])
        r5 = T.main(["describe", "--captures", "x", "--ohlcv-dir", "x", "--max-cell", "91"])
    check("reps refused both sides", r1 == 2 and r2 == 2)
    check("fit refuses cell 48", r3 == 2)
    check("describe refuses 47 and 91", r4 == 2 and r5 == 2)
    check("refusals printed", buf.getvalue().count("refusing") == 5)


def _stub_pipeline(rows_for_prepare, gaps=None, ex=None, mod=None):
    """Replace discovery, build_rows and prepare; returns calls and a restore fn."""
    calls = {}
    T = mod or globals()["T"]
    saved = (T.cell_caps, T.R.build_rows, T.prepare, T.load_closes, os.listdir)
    T.cell_caps = lambda roots, lo, hi: (["ALL1", "ALL2", "IN1"], ["IN1"])
    def fake_build(caps, ref=None, *rest):
        calls["args"] = (list(caps), ref, rest)
        return [], list(gaps or [])
    T.R.build_rows = fake_build
    T.prepare = lambda rows, closes: (rows_for_prepare, list(ex or []))
    T.load_closes = lambda path: []
    os.listdir = lambda d: []
    def restore():
        T.cell_caps, T.R.build_rows, T.prepare, T.load_closes, os.listdir = saved
    return calls, restore


def test_reference_set_is_in_range_only():
    calls, restore = _stub_pipeline([])
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            T.main(["fit", "--captures", "x", "--ohlcv-dir", "x"])
    finally:
        restore()
    check("build_rows gets only the in-range captures", calls["args"][0] == ["IN1"], str(calls))
    check("no out-of-range reference set is passed", calls["args"][1] is None and calls["args"][2] == (), str(calls))


def test_seed_refused_before_loading():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r1 = T.main(["fit", "--captures", "/nonexistent", "--ohlcv-dir", "/nonexistent", "--seed", "1"])
        r2 = T.main(["describe", "--captures", "/nonexistent", "--ohlcv-dir", "/nonexistent", "--seed", "20261126"])
    check("other seeds refused before loading inputs", r1 == 2 and r2 == 2 and buf.getvalue().count("refusing: --seed must be the registered 20261125") == 2, buf.getvalue())


def test_crossed_rows_listed_before_statistics():
    # weights (a, b) = (0, 1): lower edge = q_lo, upper edge = half; q_lo above half crosses
    bad = mkrow(h="week", q=(5.0, 6.0), half=2.0, base="2025-12-31")
    bad["ticker"] = "X.CA"
    good = mkrow(h="week", base="2026-02-13")
    good["ticker"] = "Y.CA"
    res = T.evaluate_pairs([bad, good], (0.0, 1.0), 20, 1)
    check("crossed key carried through evaluate_pairs", res["week"]["crossed_keys"] == [bad["key"]] and res["week"]["crossed"] == 1, str(res["week"].get("crossed_keys")))
    calls, restore = _stub_pipeline([bad, good])
    import json, tempfile
    with tempfile.TemporaryDirectory() as d:
        wp = os.path.join(d, "w.json")
        with open(wp, "w") as fh:
            json.dump({"weights": [0.0, 1.0]}, fh)
        saved_eval = T.evaluate_pairs
        T.evaluate_pairs = lambda rows, w, reps, seed: saved_eval(rows, w, 20, seed)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                T.main(["describe", "--captures", "x", "--ohlcv-dir", "x", "--weights", wp])
        finally:
            T.evaluate_pairs = saved_eval
            restore()
    out = buf.getvalue()
    line = "crossed edges: %s (reason: crossed edges, v2 interval used)" % bad["key"]
    check("each crossed fallback is printed with key and reason", out.count(line) == 1, out[-600:])
    check("listing comes before the statistics", 0 <= out.index(line) < out.index("DESCRIPTIVE ONLY"))
    check("total count line kept", "crossed-edge rows=1" in out)


def test_leave_out_prints_exclusions_first():
    import score_shrinkage_leave_out as L
    import json, tempfile
    calls, restore = _stub_pipeline([], gaps=["gap-one"], ex=["excluded row Z: reason"], mod=L.T)
    with tempfile.TemporaryDirectory() as d:
        wp = os.path.join(d, "w.json")
        with open(wp, "w") as fh:
            json.dump({"weights": [0.1, 1.0]}, fh)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                L.main(["--captures", "x", "--ohlcv-dir", d, "--weights", wp])
        finally:
            restore()
    out = buf.getvalue()
    check("exclusions printed", "excluded: gap-one" in out and "excluded row Z: reason" in out, out)
    check("exclusions come before any fold", out.index("excluded: gap-one") < out.index("leave one cutoff out") if "leave one cutoff out" in out else True)
    check("leave-out also uses in-range captures only", calls["args"][0] == ["IN1"] and calls["args"][1] is None, str(calls))


def run_all():
    for fn in (test_constants, test_quantile, test_baseline_window_and_history, test_no_lookahead,
               test_realised_date, test_mix_edges, test_prepare_exclusions, test_fit_threshold_and_freeze,
               test_fit_picks_best_and_ties, test_crossed_edges, test_leave_out_folds, test_refusals,
               test_reference_set_is_in_range_only, test_seed_refused_before_loading,
               test_crossed_rows_listed_before_statistics, test_leave_out_prints_exclusions_first):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_shrinkage_challenger: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
