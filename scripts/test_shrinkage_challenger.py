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
    n, ex, w = T.fit_horizon(ok, "day")
    check("100 covered fits", n == 100 and w is not None and not ex)
    n, ex, w = T.fit_horizon(ok[:99], "day")
    check("99 covered does not fit", n == 99 and w is None)
    mixed = ok[:99] + [mkrow(rdate="2025-08-15")]
    n, ex, w = T.fit_horizon(mixed, "day")
    check("freeze date itself is excluded", n == 99 and w is None and len(ex) == 1 and "after freeze date" in ex[0], str((n, ex)))
    mixed = ok + [mkrow(rdate="2025-10-29")]
    n, ex, w = T.fit_horizon(mixed, "day")
    check("later close excluded, listed, fit still runs", n == 100 and len(ex) == 1 and w is not None)
    n, ex, w = T.fit_horizon(ok + [mkrow(h="week")], "day")
    check("other horizon not counted", n == 100)


def test_fit_picks_best_and_ties():
    # real always 0, v2 half 2 and baseline edges tight: baseline (weights 0) scores best
    rows = [mkrow(real=0.0, q=(-0.5, 0.5), half=2.0, rdate="2025-01-01") for _ in range(100)]
    n, ex, w = T.fit_horizon(rows, "day")
    check("tight baseline wins weights 0", w == (0.0, 0.0), str(w))
    # real far outside both: wider is better, v2 half 5 vs baseline 1 -> weights 1
    rows = [mkrow(real=4.0, q=(-1.0, 1.0), half=5.0, rdate="2025-01-01") for _ in range(100)]
    n, ex, w = T.fit_horizon(rows, "day")
    check("upper weight just covers the real, lower weight 0 (narrowest)", w == (0.0, 0.75), str(w))
    # identical edges: every weight ties -> larger weights (nearer v2)
    rows = [mkrow(real=0.0, q=(-2.0, 2.0), half=2.0, rdate="2025-01-01") for _ in range(100)]
    n, ex, w = T.fit_horizon(rows, "day")
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


def run_all():
    for fn in (test_constants, test_quantile, test_baseline_window_and_history, test_no_lookahead,
               test_realised_date, test_mix_edges, test_prepare_exclusions, test_fit_threshold_and_freeze,
               test_fit_picks_best_and_ties, test_crossed_edges, test_refusals):
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
