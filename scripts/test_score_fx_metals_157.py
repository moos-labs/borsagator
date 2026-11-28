"""Fixed synthetic checks for scripts/score_fx_metals_157.py. Mutation-checked."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_fx_metals_157 as M  # noqa: E402
import score_fx_holdout as H  # noqa: E402
import score_fx_descriptive as D  # noqa: E402
import test_score_fx_holdout as T  # noqa: E402

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", name, detail)


def sessions(n, flagged=()):
    out, c = [], 100.0
    for i, d in enumerate(T.weekdays("2025-09-01", "2026-12-31")):
        if i >= n:
            break
        c *= 1.0 + (0.01 if i % 2 == 0 else -0.007) * (1 + (i % 5) / 5.0)
        out.append((d, c, d in flagged))
    return out


def test_all():
    # fit_k: every |z| = 1.5 -> the grid minimiser is 1.5; fewer than 20 rows -> None
    rows = [{"real": (1 if i % 2 else -1) * 1.5 * 0.01 * 100, "sigma": 0.01} for i in range(30)]
    check("fit_k picks the grid value that just covers |z| = 1.5", M.fit_k(rows, 1) == 1.5, str(M.fit_k(rows, 1)))
    check("fit_k: 19 rows -> no fit, 20 rows -> fit", M.fit_k(rows[:19], 1) is None and M.fit_k(rows[:20], 1) == 1.5)
    rows2 = [{"real": (1 if i % 2 else -1) * 0.5 * 0.01 * 100, "sigma": 0.01} for i in range(30)]
    check("fit_k lower grid edge: |z| = 0.5 gives 0.5", M.fit_k(rows2, 1) == 0.5)
    rows3 = [{"real": 9.0, "sigma": 0.01} for i in range(30)]
    check("fit_k upper grid edge 3.0 when |z| is 9", M.fit_k(rows3, 1) == 3.0)
    check("week/month scale uses sqrt(h): |z| = 1.5 x sqrt(5) fits k = 1.5 at h = 5",
          M.fit_k([{"real": 1.5 * 0.01 * math.sqrt(5) * 100 * (1 if i % 2 else -1), "sigma": 0.01} for i in range(30)], 5) == 1.5)
    # train_rows exclude hold-out sessions
    sess = [(d, 1.0 + 0.001 * i) for i, d in enumerate(T.weekdays("2025-01-01", "2026-06-30"))]
    tr = M.train_rows(sess, 1, False)
    check("training rows never use a session dated on/after 2026-01-01", all(r["cutoff"] < "2025-12-31" for r in tr) and len(tr) > 100, str(tr[-1]["cutoff"] if tr else None))
    # FX run on a short synthetic series: gate passes, too few training rows -> no fit, counts only
    res, dd = T.run_dir()
    out = M.run_fx(dd, "2026-04-01", reps=200)
    check("fx run: gate passes and the day horizon (>= 20 training rows) gets a fitted k on the grid",
          not out["gate"]["stop_positive_skill"] and out["cells"]["EURUSD"]["horizons"]["day"]["k_fit"] in M.K_GRID)
    h = out["cells"]["EURUSD"]["horizons"]["month"]
    check("month: no fit under 20 training rows is reported as NO FIT, counts only", h["k_fit"] is None and h["counts_only"] is True and "NO FIT" in h["keep_rule"], str(h))
    res3, dd3 = T.run_dir(flat_from="2026-01-01")
    out3 = M.run_fx(dd3, "2026-04-01", reps=200)
    check("fx run: gate stops a flat hold-out before any challenger number", out3["gate"]["stop_positive_skill"] and out3["rows"] == [])
    # metals rows
    sess = sessions(330)
    dates = [s[0] for s in sess]
    flagged = {dates[k] for k in range(len(dates)) if k % 10 in (0, 1, 2, 3)}      # 40% flagged
    sess = [(d_, c, d_ in flagged) for d_, c, _ in sess]
    rows, drop = M.metal_rows(sess, 1)
    check("metals day: a row whose realised return ends on a flagged date is dropped and counted",
          drop["roll_flag_in_realised_window"] > 0 and all(r["cutoff"] >= "2026-01-01" for r in rows), str(drop))
    idx = {s[0]: k for k, s in enumerate(sess)}
    check("no scored row has a flagged return ending in its realised window",
          all(not sess[idx[r["cutoff"]] + 1][2] for r in rows if r["matured"]))
    # sigma excludes flagged returns: recompute independently for the first row
    r0 = rows[0]
    i = idx[r0["cutoff"]]
    rets, j = [], i
    while j >= 1 and len(rets) < 60:
        if not sess[j][2]:
            rets.append(math.log(sess[j][1] / sess[j - 1][1]))
        j -= 1
    mu = sum(rets) / 60
    want = math.sqrt(sum((x - mu) ** 2 for x in rets) / 59)
    check("sigma = std of the 60 most recent UNFLAGGED returns", abs(r0["sigma"] - want) < 1e-12, str((r0["sigma"], want)))
    all_ret = [math.log(sess[k][1] / sess[k - 1][1]) for k in range(i - 59, i + 1)]
    mu2 = sum(all_ret) / 60
    check("flagged returns would change sigma (test is sensitive)", abs(math.sqrt(sum((x - mu2) ** 2 for x in all_ret) / 59) - want) > 1e-6)
    rows_s, drop_s = M.metal_rows(sess, 1, "window60_strict")
    check("strict window: 40% flagged leaves < 40 unflagged returns, every row dropped and counted",
          rows_s == [] and drop_s["sigma_window_too_few_unflagged_returns"] > 0, str(drop_s))
    flagged_all = {s[0] for s in sess}
    rows_f, drop_f = M.metal_rows([(a, b, True) for a, b, _ in sess], 1)
    check("everything flagged: no rows", rows_f == [])
    # boundary: unflagged sessions -> nothing dropped for roll
    rows_n, drop_n = M.metal_rows([(a, b, False) for a, b, _ in sess], 1)
    check("no flags: nothing dropped for roll, the last cutoff has no realised close", drop_n["roll_flag_in_realised_window"] == 0 and rows_n[-1]["matured"] is False)
    # 5-session window boundary: a flag on session i+5 drops a week row, on i+6 does not
    base = [(a, b, False) for a, b, _ in sess]
    i0 = next(k for k, s in enumerate(base) if s[0] >= "2026-01-01")
    for off, row0_kept in ((5, False), (6, True)):
        b2 = list(base)
        b2[i0 + off] = (b2[i0 + off][0], b2[i0 + off][1], True)
        r2, dr = M.metal_rows(b2, 5)
        kept = any(r["cutoff"] == base[i0][0] for r in r2)
        check("weekly row at cutoff i: a flag at i+%d %s its realised window (i, i+5]" % (off, "is inside" if off == 5 else "is outside"),
              kept == row0_kept and dr["roll_flag_in_realised_window"] == 1, str((kept, dr)))
    # metals run end-to-end on files
    import tempfile
    dm = tempfile.mkdtemp()
    for sym, fn in M.METALS:
        with open(os.path.join(dm, fn + ".csv"), "w") as f:
            f.write("date,high,low,close,volume,adjclose,roll_window,proxy\n")
            for a, b, fl in sess:
                f.write("%s,,,%s,,,%d,x\n" % (a, b, 1 if fl else 0))
    om = M.run_metals(dm, "2026-12-31", reps=200)
    check("metals run: gate passes, label says futures proxy not spot", not om["gate"]["stop_positive_skill"] and "NOT tradeable spot" in om["label"])
    flat = [(a, (b if a < "2026-01-01" else 100.0), fl) for a, b, fl in sess]
    for sym, fn in M.METALS:
        with open(os.path.join(dm, fn + ".csv"), "w") as f:
            f.write("date,high,low,close,volume,adjclose,roll_window,proxy\n")
            for a, b, fl in flat:
                f.write("%s,,,%s,,,0,x\n" % (a, b))
    of = M.run_metals(dm, "2026-12-31", reps=200)
    check("metals run: the gate stops a flat hold-out before any v2 number", of["gate"]["stop_positive_skill"] is True and of["rows"] == [])
    check("metals run: counts for flagged sessions in the hold-out are reported", om["cells"]["GC=F"]["flagged_sessions_in_holdout"] > 0)


if __name__ == "__main__":
    test_all()
    print("test_score_fx_metals_157: %d passed, %d failed" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)
