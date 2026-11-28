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


def test_fit_lists_crossed_training_rows():
    bad = mkrow(h="week", q=(5.0, 6.0), half=2.0, base="2025-05-02", rdate="2025-05-09")
    bad["ticker"] = "X.CA"
    late = mkrow(h="week", q=(5.0, 6.0), half=2.0, base="2025-08-08", rdate="2025-08-20")
    late["ticker"] = "L.CA"
    good = mkrow(h="week", base="2025-05-02", rdate="2025-05-09")
    good["ticker"] = "Y.CA"
    for r in (bad, late, good):
        r["key"] = "%s %s week" % (r["ticker"], r["base"])
    calls, restore = _stub_pipeline([bad, late, good])
    saved = T.fit_pooled
    T.fit_pooled = lambda rows: (2, [], (0.0, 1.0))
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            T.main(["fit", "--captures", "x", "--ohlcv-dir", "x"])
    finally:
        T.fit_pooled = saved
        restore()
    out = buf.getvalue()
    head = "CROSSED-EDGE ROWS UNDER THE FROZEN PAIR, cells 1-47, covered rows: 1 of 2"
    line = "%s (reason: crossed edges under the frozen pair, v2 interval used)" % bad["key"]
    check("fit lists the covered crossed row with the count line", head in out and out.count(line) == 1, out[-700:])
    check("post-freeze crossed row and non-crossed row are not listed", late["key"] not in out.split("CROSSED-EDGE ROWS")[1] and good["key"] not in out.split("CROSSED-EDGE ROWS")[1], str((late["key"], good["key"], out.split("CROSSED-EDGE ROWS")[1])))


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


def _stub_pipeline(rows_for_prepare, gaps=None, ex=None, mod=None, gate=False):
    """Replace discovery, build_rows and prepare; returns calls and a restore fn.
    Unless gate=True the gate is bypassed so tests of other
    output (crossed rows, exclusions) still reach the statistics."""
    calls = {}
    T = mod or globals()["T"]
    saved_gate = T.gate_horizons
    if not gate:
        T.gate_horizons = lambda mature: []
    saved = (T.cell_caps, T.R.build_rows, T.prepare, T.load_closes, os.listdir)
    T.cell_caps = lambda roots, lo, hi: (["ALL1", "ALL2", "IN1"], ["IN1"])
    def fake_build(caps, ref=None, *rest, pending=None):
        calls["args"] = (list(caps), ref, rest)
        if pending is not None:
            pending.extend(calls.get("pending_in", []))
        return [], list(gaps or [])
    T.R.build_rows = fake_build
    T.prepare = lambda rows, closes: (rows_for_prepare, list(ex or []))
    T.load_closes = lambda path: []
    os.listdir = lambda d: []
    def restore():
        T.cell_caps, T.R.build_rows, T.prepare, T.load_closes, os.listdir = saved
        T.gate_horizons = saved_gate
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


def test_freeze_gate_uses_capture_endpoint():
    cl = series(400)
    base = cl[300][0]
    row = {"ticker": "A.CA", "as_of": base, "horizon": "day", "real": 0.1, "naive_half": 3.0, "mult": 1.0, "v2_sigma": 0.02}
    out, ex = T.prepare([dict(row, real_end=cl[302][0])], {"A.CA": cl})
    check("rdate is the capture endpoint, OHLCV date kept beside it",
          out[0]["rdate"] == cl[302][0] and out[0]["rdate_ohlcv"] == cl[301][0], str(out))
    check("a differing endpoint is noted, not excluded", len(T.endpoint_notes(out)) == 1 and not ex)
    out, ex = T.prepare([row], {"A.CA": cl})
    check("no recorded endpoint falls back to the OHLCV date and is not noted", out[0]["rdate"] == cl[301][0] and not T.endpoint_notes(out))
    # the leak path: OHLCV endpoint before FREEZE, capture endpoint on/after it
    ok = [mkrow(rdate="2025-08-14") for _ in range(100)]
    leak = dict(mkrow(rdate="2025-08-15"), rdate_ohlcv="2025-08-14")
    n, fx, w = T.fit_pooled(ok + [leak])
    check("a row whose capture endpoint is on the freeze date stays out of the fit and is listed",
          n == 100 and len(fx) == 1 and "after freeze date" in fx[0], str((n, fx)))
    n, fx, w = T.fit_pooled(ok + [dict(mkrow(rdate="2025-08-14"), rdate_ohlcv="2025-08-14")])
    check("agreeing endpoints before the freeze date are covered", n == 101 and not fx)
    # the realised endpoint rule: Nth session after the cutoff of the capture's own list
    sd = ["2025-01-02", "2025-01-03", "2025-01-05", "2025-01-06", "2025-01-07", "2025-01-08"]
    check("day endpoint is the 1st session after the cutoff", T.R.endpoint_date(sd, "2025-01-02", "day") == "2025-01-03")
    check("week endpoint is the 5th session after the cutoff", T.R.endpoint_date(sd, "2025-01-02", "week") == "2025-01-08")
    check("too short a list gives None", T.R.endpoint_date(sd, "2025-01-02", "month") is None)
    check("a cutoff after the session list gives None", T.R.endpoint_date(sd, "2025-01-08", "day") is None)


def test_rebuild_notices_are_not_exclusions():
    gaps = ["cap1: realised window rebuilt to 21 sessions from price.csv", "cap2: scoring failed: boom"]
    exg, rb = T.split_gaps(gaps)
    check("split_gaps separates the rebuild notice", exg == [gaps[1]] and rb == [gaps[0]])
    calls, restore = _stub_pipeline([], gaps=gaps)
    buf = io.StringIO()
    saved = T.fit_pooled
    T.fit_pooled = lambda rows: (0, [], None)
    try:
        with contextlib.redirect_stdout(buf):
            T.main(["fit", "--captures", "x", "--ohlcv-dir", "x"])
    finally:
        T.fit_pooled = saved
        restore()
    out = buf.getvalue()
    check("challenger fit: rebuild notice under its own heading, not in EXCLUSIONS",
          "REBUILT WINDOWS (scored, not exclusions)" in out and "excluded: cap1" not in out
          and "excluded: cap2: scoring failed: boom" in out
          and out.index("cap1: realised window rebuilt") < out.index("EXCLUSIONS (every one listed)"), out)
    import score_shrinkage_leave_out as L
    import json, tempfile
    calls, restore = _stub_pipeline([], gaps=gaps, mod=L.T)
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
    check("leave-out: rebuild notice under its own heading, not in EXCLUSIONS",
          "REBUILT WINDOWS (scored, not exclusions)" in out and "excluded: cap1" not in out
          and "excluded: cap2: scoring failed: boom" in out, out)


def test_leave_out_lists_crossed_rows():
    import score_shrinkage_leave_out as L
    import json, tempfile
    bad = mkrow(h="week", q=(5.0, 6.0), half=2.0, base="2025-05-02")
    bad["key"] = "X.CA 2025-05-02 week"
    good = mkrow(h="week", base="2025-05-09")
    good["key"] = "Y.CA 2025-05-09 week"
    calls, restore = _stub_pipeline([bad, good], mod=L.T)
    with tempfile.TemporaryDirectory() as d:
        wp = os.path.join(d, "w.json")
        with open(wp, "w") as fh:
            json.dump({"weights": [0.0, 1.0]}, fh)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                L.main(["--captures", "x", "--ohlcv-dir", d, "--weights", wp])
        finally:
            restore()
    out = buf.getvalue()
    line = "crossed edges: %s (reason: crossed edges, v2 interval used)" % bad["key"]
    check("leave-out lists the crossed row once with the reason", out.count(line) == 1 and good["key"] not in out.split("CROSSED-EDGE")[1].split("week, leave")[0], out[:900])
    check("count line present and listing precedes the folds",
          "CROSSED-EDGE FALLBACKS (every one listed, before any fold; rows stay in scoring): 1" in out
          and out.index(line) < out.index("leave one cutoff out"), out[:900])


def test_mature_cluster_counting():
    caps = ["/r/2025-01-02/A.CA", "/r/2025-01-02/B.CA", "/r/2025-01-09/A.CA", "/r/2025-01-09/B.CA",
            "/r/2025-01-09/B.CA", "/r/2025-01-16/A.CA"]
    def row(t, b, h="week"):
        r = mkrow(h=h, base=b)
        r["ticker"] = t
        return r
    rows = [row("A.CA", "2025-01-02"), row("B.CA", "2025-01-02"),
            row("A.CA", "2025-01-09"),                      # B.CA dropped at 01-09
            row("A.CA", "2025-01-16"), row("Z.CA", "2025-01-16"),   # extra row of another ticker
            row("A.CA", "2025-01-23"), row("B.CA", "2025-01-23")]   # cutoff with no capture
    mt, al = T.mature_clusters(caps, rows)
    check("only fully covered cutoffs are mature", mt == {"2025-01-02", "2025-01-16"}, str(mt))
    check("every captured cutoff is counted, an uncaptured one is not", al == {"2025-01-02", "2025-01-09", "2025-01-16"}, str(al))
    check("a dropped captured ticker keeps its cluster immature (no eligibility filter)", "2025-01-09" not in mt)
    check("duplicate captures collapse to one intended ticker",
          T.mature_clusters(caps, [row("A.CA", "2025-01-09"), row("B.CA", "2025-01-09")])[0] == {"2025-01-09"})
    mt2, _ = T.mature_clusters(caps, [r for r in rows if r["base"] != "2025-01-02"])
    check("removing one cutoff's rows removes only that cluster", mt2 == {"2025-01-16"})
    check("empty rows give no mature clusters", T.mature_clusters(caps, [])[0] == set())
    # through the describe CLI: per horizon, week has one dropped ticker
    import json, tempfile
    wk = [row("A.CA", "2025-01-02"), row("B.CA", "2025-01-02"), row("A.CA", "2025-01-09")]
    dy = [row("A.CA", "2025-01-02", "day"), row("B.CA", "2025-01-02", "day"),
          row("A.CA", "2025-01-09", "day"), row("B.CA", "2025-01-09", "day")]
    calls, restore = _stub_pipeline(wk + dy, gate=True)
    T.cell_caps = lambda roots, lo, hi: (caps, caps)
    with tempfile.TemporaryDirectory() as d:
        wp = os.path.join(d, "w.json")
        with open(wp, "w") as fh:
            json.dump({"weights": [0.1, 1.0]}, fh)
        jp = os.path.join(d, "o.json")
        saved_eval = T.evaluate_pairs
        T.evaluate_pairs = lambda rows_, w_, reps, seed: saved_eval(rows_, w_, 20, seed)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                T.main(["describe", "--captures", "x", "--ohlcv-dir", "x", "--weights", wp, "--json", jp])
        finally:
            T.evaluate_pairs = saved_eval
            restore()
        js = json.load(open(jp))
    out = buf.getvalue()
    check("describe prints mature clusters per horizon before the statistics",
          "day: fully mature cutoff clusters=2 of 3 (registered minimum 10" in out
          and "week: fully mature cutoff clusters=1 of 3 (registered minimum 10" in out
          and "month: fully mature cutoff clusters=0 of 3" in out
          and out.index("week: fully mature") < out.index("DESCRIPTIVE ONLY"), out[:1200])
    check("json carries the mature-cluster counts", js["mature_clusters"]["week"] == {"mature": 1, "cutoffs": 3}, str(js.get("mature_clusters")))
    check("the registered minimum is 10", T.MIN_CLUSTERS == 10)


def test_966c_captured_outcome_and_pending_records_and_gate():
    import json, tempfile
    cl = series(400)
    last = cl[399][0]
    row = {"ticker": "A.CA", "as_of": last, "horizon": "day", "real": 0.1, "naive_half": 3.0, "mult": 1.0, "v2_sigma": 0.02}
    # the OHLCV file ends at the cutoff: a captured outcome with its own endpoint stays
    out, ex = T.prepare([dict(row, real_end="2025-02-03")], {"A.CA": cl})
    check("captured real+real_end kept when OHLCV has no later rows",
          len(out) == 1 and not ex and out[0]["rdate"] == "2025-02-03" and out[0]["rdate_ohlcv"] is None, str((out, ex)))
    out, ex = T.prepare([row], {"A.CA": cl})
    check("no real_end and no OHLCV endpoint is still excluded", not out and "no realised close" in ex[0])
    out, ex = T.prepare([dict(row, real_end="2025-02-03", real=None)], {"A.CA": cl})
    check("no captured outcome is excluded even with an endpoint", not out and "no realised close" in ex[0])
    kept, _ = T.prepare([dict(row, real_end="2025-02-03")], {"A.CA": cl})
    check("endpoint notes skip rows without an OHLCV endpoint", T.endpoint_notes(kept) == [])
    ok = [dict(mkrow(), rdate="2025-01-03", rdate_ohlcv="2025-01-02")]
    check("endpoint notes still report a real difference", len(T.endpoint_notes(ok)) == 1 and "None" not in T.endpoint_notes(ok)[0])
    # pending capture rows are listed individually, in both commands
    pend = [("B.CA", "2025-01-02", "month", "pending")]
    check("pending record format", T.pending_exclusions(pend) == ["excluded row B.CA 2025-01-02 month: no realised close (capture status pending)"])
    calls, restore = _stub_pipeline([], gate=True)
    calls["pending_in"] = pend
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            T.main(["fit", "--captures", "x", "--ohlcv-dir", "x"])
    finally:
        restore()
    check("fit lists the pending row among exclusions", "excluded row B.CA 2025-01-02 month: no realised close (capture status pending)" in buf.getvalue())
    LO = importlib.util.module_from_spec(importlib.util.spec_from_file_location("lo", os.path.join(HERE, "..", "benchmarks", "score_shrinkage_leave_out.py")))
    LO.__spec__.loader.exec_module(LO)
    LO.T = T
    calls, restore = _stub_pipeline([], gate=True)
    calls["pending_in"] = pend
    with tempfile.TemporaryDirectory() as d:
        wp = os.path.join(d, "w.json")
        json.dump({"weights": [0.1, 1.0]}, open(wp, "w"))
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                LO.main(["--captures", "x", "--ohlcv-dir", "x", "--weights", wp])
        finally:
            restore()
    check("leave-out lists the pending row among exclusions", "excluded row B.CA 2025-01-02 month: no realised close (capture status pending)" in buf.getvalue())
    # the 91+ gate: 9 mature clusters is counts only, 10 gives statistics
    check("gate boundary", T.gate_horizons({"day": (9, 9), "week": (10, 10), "month": (0, 3)}) == ["day", "month"])
    def run(nclusters):
        bases = [(datetime.date(2025, 1, 2) + datetime.timedelta(days=7 * i)).isoformat() for i in range(nclusters)]
        caps = ["/r/%s/A.CA" % b for b in bases]
        rows = [dict(mkrow(h="day", base=b, real=0.3 + 0.1 * (i % 3)), ticker="A.CA") for i, b in enumerate(bases)]
        calls, restore = _stub_pipeline(rows, gate=True)
        T.cell_caps = lambda roots, lo, hi: (caps, caps)
        saved_eval = T.evaluate_pairs
        T.evaluate_pairs = lambda rows_, w_, reps, seed: saved_eval(rows_, w_, 20, seed)
        with tempfile.TemporaryDirectory() as d:
            wp, jp = os.path.join(d, "w.json"), os.path.join(d, "o.json")
            json.dump({"weights": [0.1, 1.0]}, open(wp, "w"))
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    T.main(["describe", "--captures", "x", "--ohlcv-dir", "x", "--weights", wp, "--json", jp])
            finally:
                T.evaluate_pairs = saved_eval
                restore()
            return buf.getvalue(), json.load(open(jp))
    o9, j9 = run(9)
    check("9 mature clusters: day is counts only, no statistics",
          "day: COUNTS ONLY, 9 of the registered 10" in o9 and "challenger:" not in o9 and "RangeSkill CI" not in o9, o9[-600:])
    check("9 clusters: json has no day results and names the gated horizons",
          "day" not in j9["results"] and j9["counts_only_horizons"] == ["day", "week", "month"])
    o10, j10 = run(10)
    check("10 mature clusters: day statistics are printed", "day: n=10" in o10 and "challenger: coverage" in o10 and "day: COUNTS ONLY" not in o10, o10[-600:])
    check("10 clusters: json has day results", "day" in j10["results"] and "day" not in j10["counts_only_horizons"])


def test_966d_nonfinite_window_and_fold_gate():
    import math
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmarks"))
    import score_shrinkage_leave_out as L
    cl = series(400)
    mk_row = lambda i, h="day": {"ticker": "A.CA", "as_of": cl[i][0], "horizon": h, "real": 0.2 + 0.01 * (i % 5),
                                 "naive_half": 3.0, "mult": 1.0, "v2_sigma": 0.02}
    for bad in (float("nan"), float("inf"), float("-inf")):
        c2 = list(cl)
        c2[100] = (c2[100][0], bad)
        old_idx, new_idx = list(range(300, 306)), list(range(360, 370))
        out, ex = T.prepare([mk_row(i) for i in old_idx + new_idx], {"A.CA": c2})
        check("rows whose window holds a %s close are excluded, each with a reason" % bad,
              len(ex) == 6 and all("non-finite close in the baseline window" in e for e in ex), str(ex))
        check("rows whose window starts after the bad close are kept", len(out) == 10 and all(math.isfinite(r["q_lo"]) and math.isfinite(r["q_hi"]) for r in out))
        res = T.evaluate_pairs(out, (0.1, 1.0), 20, 1)
        check("evaluate outputs stay finite", all(math.isfinite(res["day"][k]) for k in ("rs_ch", "rs_v2", "cov_ch")) and
              all(math.isfinite(x) for x in res["day"]["delta_ci_cutoff"] + res["day"]["cov_ci_cutoff"]), str(res["day"]))
        check("baseline itself returns no edges, never NaN edges", T.baseline(c2, cl[300][0], "day")[0] is None and T.window_nonfinite(c2, cl[300][0], "day"))
    c3 = list(cl); c3[380] = (c3[380][0], float("nan"))
    check("a bad close AFTER the base date changes nothing (no look-ahead)", T.baseline(c3, cl[300][0], "day") == T.baseline(cl, cl[300][0], "day")
          and not T.window_nonfinite(c3, cl[300][0], "day"))
    check("a bad close is not dropped from the history (offsets stay)", True and
          T.realised_date(c3, cl[300][0], "week") == cl[305][0])
    # the leave-one-cutoff fold gate
    def mkset(n_cut):
        cutoffs = ["2025-01-%02d" % (i + 1) for i in range(n_cut)]
        caps, rows = [], []
        for tk in ("A.CA", "B.CA"):
            for c in cutoffs:
                caps.append("/r/%s/%s" % (c, tk))
                r = mkrow(base=c, real=0.3)
                r["ticker"] = tk
                rows.append(r)
        return caps, rows
    caps, rows = mkset(10)
    f = dict(L.build_folds(rows, 0.1, 1.0, "base", caps))
    check("10-cluster horizon: the full sample keeps statistics", "counts_only" not in f["all"] and f["all"]["n"] == 20)
    check("10-cluster horizon: every leave-one-cutoff fold is counts only with 9 retained",
          all(f[c] == {"counts_only": 9} for c in f if c != "all") and len(f) == 11, str(f))
    caps, rows = mkset(11)
    f = dict(L.build_folds(rows, 0.1, 1.0, "base", caps))
    check("11-cluster horizon: folds with 10 retained mature clusters keep statistics",
          all("counts_only" not in f[c] and f[c]["n"] == 20 for c in f if c != "all") and len(f) == 12, str(f))
    caps, rows = mkset(10)
    t = dict(L.build_folds(rows, 0.1, 1.0, "ticker", caps))
    check("leave-one-ticker folds are unchanged: statistics, no gate", all("counts_only" not in t[k] for k in t) and t["A.CA"]["n"] == 10)
    # a fold whose left-out cutoff was already immature does not lose a mature cluster
    caps, rows = mkset(11)
    rows = [r for r in rows if not (r["base"] == "2025-01-11" and r["ticker"] == "B.CA")]   # cutoff 11 immature
    f = dict(L.build_folds(rows, 0.1, 1.0, "base", caps))
    check("leaving out the immature cutoff keeps 10 mature, statistics; leaving a mature one gives counts only",
          "counts_only" not in f["2025-01-11"] and f["2025-01-01"] == {"counts_only": 9}, str((f["2025-01-11"], f["2025-01-01"])))


def test_966e_unusable_close_kept_and_coverage_draws_kept():
    import math
    import tempfile
    import random as _rnd
    # F1: dated sessions with an unusable close stay as NaN; records without a usable date go
    with tempfile.TemporaryDirectory() as d:
        cl = series(400)
        path = os.path.join(d, "A_CA.csv")
        with open(path, "w") as fh:
            fh.write("date,close\n")
            for i, (dt, c) in enumerate(cl):
                if i == 100:
                    fh.write("%s,\n" % dt)          # empty close
                elif i == 101:
                    fh.write("%s,abc\n" % dt)       # unparseable close
                elif i == 102:
                    fh.write("%s,nan\n" % dt)       # literal nan
                else:
                    fh.write("%s,%s\n" % (dt, c))
            fh.write(",5.0\n")                        # no date
            fh.write("not-a-date,5.0\n")              # unusable date
        got = T.load_closes(path)
        check("dated sessions with an unusable close are kept (400 sessions), undated records rejected", len(got) == 400, str(len(got)))
        check("sessions 100-102 are NaN, their neighbours finite, dates unchanged",
              [math.isnan(got[i][1]) for i in (100, 101, 102)] == [True] * 3 and math.isfinite(got[99][1]) and math.isfinite(got[103][1])
              and [g[0] for g in got] == [c[0] for c in cl])
        check("session offsets are unchanged by the bad closes", T.realised_date(got, cl[90][0], "week") == T.realised_date(cl, cl[90][0], "week"))
        mk_row = lambda i, h="week": {"ticker": "A.CA", "as_of": cl[i][0], "horizon": h, "real": 0.2,
                                      "naive_half": 3.0, "mult": 1.0, "v2_sigma": 0.02}
        out, ex = T.prepare([mk_row(i) for i in (300, 360)], {"A.CA": got})
        check("a row whose window crosses the unusable closes is excluded with the window reason, a later one is kept",
              len(ex) == 1 and "non-finite close in the baseline window" in ex[0] and len(out) == 1 and out[0]["base"] == cl[360][0], str(ex))
        # a one-bad-close drop would have shifted offsets: the dropped-row variant gives a different window result
        dropped = [c for i, c in enumerate(cl) if i != 100]
        check("dropping the session instead would change the 5-session move set (offsets matter)",
              T.baseline(dropped, cl[110][0], "week") != T.baseline(cl, cl[110][0], "week"))
    # F2: coverage CI uses every draw, RangeSkill delta only the draws where it is defined
    cl = series(400)
    rows = []
    for k, i in enumerate((300, 310, 320, 330)):
        for t in range(1 + k):
            rows.append({"ticker": "T%d.CA" % t, "as_of": cl[i][0], "horizon": "day", "real": (0.2 if k % 2 == 0 else 5.0), "naive_half": 3.0,
                         "mult": 1.0, "v2_sigma": 0.02, "base": cl[i][0], "half": 1.0, "q_lo": -1.0, "q_hi": 1.0, "key": "k%d%d" % (k, t)})
    saved = T.A.range_skill
    T.A.range_skill = lambda draw, which: None if len(draw) % 2 == 0 else 0.5
    try:
        res = T.evaluate_pairs(rows, (0.1, 1.0), 200, 7)
    finally:
        T.A.range_skill = saved
    pairs_by = {}
    for r in rows:
        is_ch, inside, _c = T.row_scores(r, 0.1, 1.0)
        pairs_by.setdefault(r["base"], []).append(inside)
    keys = sorted(pairs_by)
    rng = _rnd.Random(7)
    cov_all, n_def = [], 0
    for _ in range(200):
        draw = []
        for _k in keys:
            draw.extend(pairs_by[rng.choice(keys)])
        cov_all.append(sum(draw) / len(draw))
        n_def += len(draw) % 2 == 1
    want = list(T.A.percentile_ci(cov_all))
    check("fixture really has draws with undefined RangeSkill and draws with a defined one", 0 < n_def < 200, str(n_def))
    check("coverage CI uses all 200 draws, not only the draws with a defined RangeSkill", res["day"]["cov_ci_cutoff"] == want, str((res["day"]["cov_ci_cutoff"], want)))
    check("the delta CI still skips the undefined draws (all defined draws equal 0 difference)", res["day"]["delta_ci_cutoff"] == [0.0, 0.0], str(res["day"]["delta_ci_cutoff"]))


def run_all():
    for fn in (test_constants, test_quantile, test_baseline_window_and_history, test_no_lookahead,
               test_realised_date, test_mix_edges, test_prepare_exclusions, test_fit_threshold_and_freeze,
               test_fit_picks_best_and_ties, test_crossed_edges, test_leave_out_folds, test_refusals,
               test_reference_set_is_in_range_only, test_seed_refused_before_loading,
               test_crossed_rows_listed_before_statistics, test_fit_lists_crossed_training_rows, test_leave_out_prints_exclusions_first,
               test_freeze_gate_uses_capture_endpoint, test_rebuild_notices_are_not_exclusions, test_leave_out_lists_crossed_rows, test_mature_cluster_counting,
               test_966c_captured_outcome_and_pending_records_and_gate, test_966d_nonfinite_window_and_fold_gate, test_966e_unusable_close_kept_and_coverage_draws_kept):
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
