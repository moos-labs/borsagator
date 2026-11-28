"""Tests for scripts/score_fx_shrinkage_159.py: fixed synthetic inputs only."""
import datetime
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_shrinkage_159 as Z  # noqa: E402

D = Z.D
CHECKS = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def close(a, b, t=1e-9):
    return abs(a - b) < t


def test_quantile_and_baseline():
    v = [float(i) for i in range(11)]
    check("quantile p10/p90 of 0..10 are 1 and 9", close(Z.quantile(v, 0.10), 1.0) and close(Z.quantile(v, 0.90), 9.0))
    check("quantile interpolates linearly between order statistics", close(Z.quantile([0.0, 10.0], 0.10), 1.0))
    g = math.log(1.001)
    closes = [100.0 * math.exp(g * k) for k in range(400)]
    flags = [False] * 400
    bl = Z.baseline(closes, flags, 399, 1, False)
    check("window caps at 250 moves; constant growth gives equal quantiles", bl[2] == 250 and close(bl[0], g * 100) and close(bl[1], g * 100), str(bl))
    check("125 matured moves are enough", Z.baseline(closes, flags, 1 + 124, 1, False) is not None)
    check("124 matured moves are short history", Z.baseline(closes, flags, 1 + 123, 1, False) is None)
    check("week step: moves need t + 5 <= cutoff", Z.baseline(closes, flags, 5 + 124, 5, False)[2] == 125 and Z.baseline(closes, flags, 5 + 123, 5, False) is None)
    c2 = list(closes)
    for k in range(300, 400):
        c2[k] = 1.0
    check("closes after the cutoff never enter the baseline", Z.baseline(c2, flags, 299, 1, False)[:2] == Z.baseline(closes, flags, 299, 1, False)[:2])
    # exact count, small case: cutoff 140, step 5 -> moves t=0..135 (136), flag at 100 hits t=95..99 (5 moves)
    a = Z.baseline(closes, fl2 if False else [i == 100 for i in range(400)], 140, 5, False)[2]
    b = Z.baseline(closes, [i == 100 for i in range(400)], 140, 5, True)[2]
    check("flag at 100, week step: exactly 5 moves removed", a == 136 and b == 131, str((a, b)))


def test_baseline_quantiles_and_flag_edges():
    # day moves 100 x log(c[t+1]/c[t]) = (t % 50) x 0.1 exactly by construction
    closes = [100.0]
    for t in range(399):
        closes.append(closes[-1] * math.exp((t % 50) * 0.001))
    bl = Z.baseline(closes, [False] * 400, 399, 1, False)
    mv = sorted((t % 50) * 0.1 for t in range(149, 399))
    e10 = mv[24] + (mv[25] - mv[24]) * 0.9      # (250-1) x 0.10 = 24.9
    e90 = mv[224] + (mv[225] - mv[224]) * 0.1   # (250-1) x 0.90 = 224.1
    check("10th and 90th percentiles of a known move set", close(bl[0], e10, 1e-6) and close(bl[1], e90, 1e-6), str((bl, e10, e90)))
    fl_end = [i == 140 for i in range(400)]
    check("a flag on the cutoff index removes the one move that ends there",
          Z.baseline(closes, fl_end, 140, 5, False)[2] - Z.baseline(closes, fl_end, 140, 5, True)[2] == 1)
    fl_start = [i == 0 for i in range(400)]
    check("a flag on the first index starts no move window (the return INTO index 0 is not in any window)",
          Z.baseline(closes, fl_start, 140, 5, False)[2] == Z.baseline(closes, fl_start, 140, 5, True)[2])


def test_challenger_and_fit():
    r, half, qlo, qhi = 0.5, 2.0, -1.0, 1.0
    check("a = b = 1 is the frozen v2 interval", close(Z.challenger_is(r, half, qlo, qhi, 1.0, 1.0)[0], D.winkler(r, -half, half)))
    check("a = b = 0 is the baseline quantile interval", close(Z.challenger_is(r, half, qlo, qhi, 0.0, 0.0)[0], D.winkler(r, qlo, qhi)))
    s, cov, cr = Z.challenger_is(r, half, qlo, qhi, 0.5, 0.5)
    check("a = b = 0.5: edges are the midpoints (-1.5, 1.5)", close(s, D.winkler(r, -1.5, 1.5)) and cov and not cr)
    s, cov, cr = Z.challenger_is(0.1, 2.0, 5.0, -5.0, 0.0, 0.0)
    check("crossed edges fall back to the v2 interval and are flagged", cr and close(s, D.winkler(0.1, -2.0, 2.0)) and cov)
    s, cov, cr = Z.challenger_is(0.1, 2.0, 0.0, 0.0, 0.0, 0.0)
    check("equal edges count as crossed and fall back to v2", cr and close(s, D.winkler(0.1, -2.0, 2.0)))
    check("coverage is the inclusive edge test", Z.challenger_is(1.0, 2.0, -1.0, 1.0, 0.0, 0.0)[1] and not Z.challenger_is(1.01, 2.0, -1.0, 1.0, 0.0, 0.0)[1])
    base = [{"real": (0.5 if i % 2 else -0.5), "half": 10.0, "qlo": -1.0, "qhi": 1.0} for i in range(100)]
    p = Z.fit_pair(base)
    check("tight baseline beats a wide v2: pair (0, 0)", p[:2] == (0.0, 0.0), str(p))
    wide = [{"real": (0.9 if i % 2 else -0.9), "half": 1.0, "qlo": -10.0, "qhi": 10.0} for i in range(100)]
    p = Z.fit_pair(wide)
    check("tight v2 beats a wide baseline: pair (1, 1)", p[:2] == (1.0, 1.0), str(p))
    same = [{"real": 0.3, "half": 1.0, "qlo": -1.0, "qhi": 1.0} for i in range(100)]
    p = Z.fit_pair(same)
    check("every pair ties: the larger weights win", p[:2] == (1.0, 1.0), str(p))
    check("99 rows: no fit", Z.fit_pair(base[:99]) is None and Z.fit_pair(base) is not None)


def synth_closes(n, seed):
    x, out = 100.0, []
    for _ in range(n):
        seed = (seed * 1103515245 + 12345) % (2 ** 31)
        x *= math.exp(((seed / 2 ** 31) - 0.5) * 0.02)
        out.append(x)
    return out


def write_series(data_dir, name, seed, tweak_holdout=False):
    d, rows = datetime.date(2021, 1, 4), []
    cl = synth_closes(1500, seed)
    k = 0
    while d <= datetime.date(2026, 6, 30):
        if d.weekday() < 5:
            c = cl[k]
            if tweak_holdout and d >= datetime.date(2026, 1, 1):
                c *= 1.5 + 0.001 * k
            rows.append("%s,%f,%f,%f,0,%f" % (d.isoformat(), c * 1.001, c * 0.999, c, c))
            k += 1
        d += datetime.timedelta(days=1)
    with open(os.path.join(data_dir, name + ".csv"), "w") as f:
        f.write("date,high,low,close,volume,adjclose\n" + "\n".join(rows) + "\n")


def test_fit_is_training_only_and_end_to_end():
    names = [c[0] for c in Z.H.CELLS]
    outs = []
    for tweak in (False, True):
        with tempfile.TemporaryDirectory() as d:
            for i, n in enumerate(names):
                write_series(d, n, 7 + i, tweak)
            for extra in ("USDSAR", "USDAED"):
                write_series(d, extra, 99, tweak)
            outs.append(Z.run(d, "2026-07-01", reps=50))
    a, b = outs
    check("fit pair is on the registered grid and pooled rows >= 100", a["fit"]["a"] in Z.GRID and a["fit"]["b"] in Z.GRID and a["fit"]["covered_rows_pooled"] >= 100, str(a["fit"]))
    check("changing every hold-out close leaves the fit identical (no hold-out row is read for the fit)",
          (a["fit"]["a"], a["fit"]["b"], a["fit"]["covered_rows_pooled"], a["fit"]["mean_is_train"]) ==
          (b["fit"]["a"], b["fit"]["b"], b["fit"]["covered_rows_pooled"], b["fit"]["mean_is_train"]), str((a["fit"], b["fit"])))
    check("fit uses only the three registered cells", a["fit_cells"] == ["EURUSD", "USDJPY", "USDEGP"]
          and sorted({k.split("/")[0] for k in a["fit"]["per_cell_horizon"]}) == ["EURUSD", "USDEGP", "USDJPY"])
    hs = a["cells"]["EURUSD"]["horizons"]
    check("EURUSD day cell scored on hold-out rows with every registered key",
          "day/all_rows" in hs and hs["day/all_rows"]["n"] > 0 and ("range_skill_ch_vs_naive" in hs["day/all_rows"]
                                                                  or hs["day/all_rows"].get("counts_only") is True))
    check("hold-out cells differ when the hold-out data differs", a["cells"]["EURUSD"]["horizons"] != b["cells"]["EURUSD"]["horizons"])
    rc = Z.main(["--data", "/nonexistent", "--asof", "2026-11-28", "--out-json", "/tmp/x.json", "--reps", "10"])
    check("non-registered reps refused", rc == 2)


def main():
    test_quantile_and_baseline()
    test_baseline_quantiles_and_flag_edges()
    test_challenger_and_fit()
    test_fit_is_training_only_and_end_to_end()
    print("test_score_fx_shrinkage_159: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
