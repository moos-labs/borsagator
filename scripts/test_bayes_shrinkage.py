#!/usr/bin/env python3
"""Tests for benchmarks/replay_bayes_shrinkage.py (round 58).
Standalone, stdlib only, fixed synthetic inputs.
"""
import contextlib
import importlib.util
import io
import math
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location(
    "bsh", os.path.join(ROOT, "benchmarks", "replay_bayes_shrinkage.py"))
B = importlib.util.module_from_spec(spec)
sys.modules["bsh"] = B
spec.loader.exec_module(B)


def row(t, s, real, a="d1", h="day"):
    return {"ticker": t, "as_of": a, "horizon": h, "real": real,
            "naive_half": B.R.half_pct(0.02, h, 1.2816, 1.0),
            "mult": 1.0, "v2_sigma": s, "sig": {}}


def cutoff(a, real_lo, real_hi, h="day"):
    # three tickers, sigmas 0.01 / 0.02 / 0.04, geometric mean 0.02
    return [row("L", 0.01, real_lo, a, h), row("M", 0.02, 0.0, a, h),
            row("H", 0.04, real_hi, a, h)]


def test_constants():
    check("v2 pinned", B.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("grid 0..1 step .05", (B.LAM_GRID[0], B.LAM_GRID[-1],
                                 len(B.LAM_GRID)) == (0.0, 1.0, 21))
    check("minimums", (B.MIN_FIT_ROWS, B.MIN_POOL) == (10, 3))
    check("training 47, clean 91",
          (B.FIT_MAX_CELL, B.CLEAN_MIN_CELL) == (47, 91))
    check("keep rule is the shared one",
          B.keep_verdict is B.PK.keep_verdict)


def test_pools():
    p = B.pools(cutoff("d1", 0, 0))
    check("geometric mean over distinct tickers",
          abs(p["d1"][0] - 0.02) < 1e-12 and p["d1"][1] == 3, p)
    dup = cutoff("d1", 0, 0) + cutoff("d1", 0, 0, "week")
    check("a ticker counts once per cutoff",
          B.pools(dup)["d1"][1] == 3)
    check("zero sigma skipped",
          B.pools([row("A", 0.0, 0)]) == {})


def test_shrunk_sigma():
    rows = cutoff("d1", 0, 0)
    pool = B.pools(rows)
    lo, hi = rows[0], rows[2]
    check("lam 0 is v2", abs(B.shrunk_sigma(lo, 0.0, pool) - 0.01) < 1e-12)
    check("lam 1 is the pool",
          abs(B.shrunk_sigma(lo, 1.0, pool) - 0.02) < 1e-12)
    mid = B.shrunk_sigma(lo, 0.5, pool)
    check("lam .5 is the geometric midpoint",
          abs(mid - math.sqrt(0.01 * 0.02)) < 1e-12, mid)
    check("high sigma shrinks down, low shrinks up",
          B.shrunk_sigma(hi, 0.5, pool) < 0.04 < 1
          and mid > 0.01)
    thin = [row("A", 0.01, 0), row("B", 0.03, 0)]
    check("under MIN_POOL tickers keeps v2",
          B.shrunk_sigma(thin[0], 0.8, B.pools(thin)) == 0.01)
    check("unpooled rows counted", B.unpooled_rows(thin) == 2
          and B.unpooled_rows(rows) == 0)


def training_rows():
    rows = []
    for i in range(6):
        # moves sized to the pooled sigma: low-sigma ticker moves more
        # than its own band, high-sigma ticker moves less
        rows += cutoff("t%d" % i, 2.0, 0.5)
    return rows


def test_fit():
    rows = training_rows()
    lam, n, _p = B.fit(rows)
    check("pooling helps when sigmas mis-state the moves",
          lam["day"] > 0.0, lam)
    check("training counts", n["day"] == 18 and n["week"] == 0)
    check("horizon without rows keeps lam 0 (v2)", lam["week"] == 0.0)
    few = cutoff("a", 2.0, 0.5)
    check("below MIN_FIT_ROWS keeps lam 0", B.fit(few)[0]["day"] == 0.0)
    exact = []
    for i in range(6):
        exact += [row("L", 0.01, 0.0, "e%d" % i), row("M", 0.01, 0.0,
                  "e%d" % i), row("H", 0.01, 0.0, "e%d" % i)]
    check("identical sigmas: shrinkage changes nothing, ties to 0",
          B.fit(exact)[0]["day"] == 0.0)


def test_score_rows():
    rows = cutoff("d1", 0.0, 0.0)
    lam = {"day": 1.0, "week": 0.0, "month": 0.0}
    v2lo = B.R.half_pct(0.01, "day", 1.15, 1.0)
    real = 1.5 * v2lo
    rows[0]["real"] = real
    out = B.score_rows(rows, lam)
    lo = [o for o in out if o["ticker"] == "L"][0]
    check("low-sigma ticker widened by the pool (through score_rows)",
          lo["in_ch"] and not lo["in_v2"], lo)
    hi = [o for o in out if o["ticker"] == "H"][0]
    check("high-sigma ticker narrowed",
          hi["is_ch"] < hi["is_v2"], hi)
    zero = B.score_rows(rows, {"day": 0.0, "week": 0.0, "month": 0.0})
    check("lam 0 equals v2 on every row",
          all(abs(z["is_ch"] - z["is_v2"]) < 1e-9
              and z["in_ch"] == z["in_v2"] for z in zero))
    check("no sigma skipped", B.score_rows([row("A", None, 1.0)], lam)
          == [])


def test_cell_selection():
    caps = ["/x/c-cell47/d/T", "/x/c-cell48/d/T", "/x/c-cell90/d/T",
            "/x/c-cell91/d/T", "/x/unnumbered/d/T"]
    pick = lambda lo, hi: [B.A.cell_number(c) for c in
                           B.select_caps(caps, lo, hi)]
    check("training is cells <= 47 only", pick(1, 47) == [47])
    check("descriptive window 48-90", pick(48, 90) == [48, 90])
    check("clean window 91+, unnumbered dropped", pick(91, None) == [91])


def test_cli_guards():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc1 = B.main(["score", "--captures", "/nonexistent",
                      "--min-cell", "73"])
        rc2 = B.main(["score", "--captures", "/nonexistent",
                      "--min-cell", "40", "--descriptive"])
        rc3 = B.main(["score", "--captures", "/nonexistent",
                      "--min-cell", "48", "--descriptive"])
    check("clean scoring refuses seen cells", rc1 == 2)
    check("scored cells may not overlap training", rc2 == 2)
    check("no training rows refuses", rc3 == 2
          and "no training rows" in buf.getvalue())


def test_render():
    lam, n, _p = B.fit(training_rows())
    cell = {"n": 1, "cutoffs": 1, "tickers": 1,
            "v2": {"coverage": 0.8, "range_skill": 0.0},
            "ch": {"coverage": 0.8, "range_skill": 0.0},
            "ch_ci_cutoff": [0.1, 0.2], "ch_cov_ci_cutoff": [0.7, 0.8],
            "ch_ci_ticker": [0.1, 0.2]}
    res = {h: dict(cell) for h in B.HORIZONS}
    d = B.render(res, lam, n, 0, True, "DESCRIPTIVE ONLY")
    c = B.render(res, lam, n, 0, False, "CLEAN SCORING")
    check("descriptive text has no verdict word or keep rule",
          "verdict" not in d.lower() and "KEEP" not in d, d)
    check("clean text carries the keep rule", "KEEP RULE" in c)
    check("fit printed", "lam day" in d)
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "o.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = B.main(["score", "--captures", t, "--min-cell", "48",
                         "--descriptive", "--json", out])
        check("no training rows writes no json",
              rc == 2 and not os.path.exists(out))


def test_fit_window_guards():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        c1 = B.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "90", "--min-cell", "91"])
        t1 = buf.getvalue()
        c2 = B.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "100", "--min-cell", "101",
                     "--descriptive"])
        buf.truncate(0)
        buf.seek(0)
        c3 = B.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "40", "--min-cell", "91"])
        t3 = buf.getvalue()
        c4 = B.main(["diag", "--captures", "/nonexistent",
                     "--fit-max-cell", "60"])
        buf.truncate(0)
        buf.seek(0)
        c5 = B.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "40", "--min-cell", "48",
                     "--descriptive"])
        t5 = buf.getvalue()
    check("clean fit window above 47 refused",
          c1 == 2 and "above the registered 47" in t1, t1)
    check("fit window above 47 refused, descriptive too", c2 == 2)
    check("clean scoring needs exactly the registered fit window",
          c3 == 2 and "needs --fit-max-cell 47" in t3, t3)
    check("diag above 47 refused", c4 == 2)
    check("descriptive may use a lower window (reaches the fit)",
          c5 == 2 and "no training rows" in t5, t5)


def fake_args(fit_max=47):
    ns = type("NS", (), {})()
    ns.captures = ["/x"]
    ns.fit_max_cell = fit_max
    ns.reps = 20
    ns.seed = 1
    return ns


def fake_res():
    return {h: {"n": 1, "cutoffs": 1, "tickers": 1,
                "v2": {"coverage": 0.8, "range_skill": 0.0},
                "ch": {"coverage": 0.8, "range_skill": 0.0},
                "ch_ci_cutoff": [0.1, 0.2],
                "ch_cov_ci_cutoff": [0.7, 0.8],
                "ch_ci_ticker": [0.1, 0.2]} for h in B.HORIZONS}


def test_fit_reference_and_provenance():
    caps = ["/x/c-cell%d/2025-01-0%d/T%d" % (n, 1 + n % 8, n % 7)
            for n in (3, 30, 47, 48, 90, 91)]
    calls = []

    def fake_build(cs, ref=None):
        calls.append((list(cs), list(ref)))
        if B.A.cell_number(cs[0]) == 3:
            return training_rows(), [
                "x: realised window rebuilt to 21 sessions from price.csv",
                "y: no usable pre-cutoff OHLC history"]
        return cutoff("s1", 0.5, 0.5), []
    old = (B.R.build_rows, B.A.find_captures, B.windowed_captures)
    B.R.build_rows, B.A.find_captures = fake_build, lambda *a: caps
    B.windowed_captures = lambda roots, lo, hi: [
        c for c in caps if B.A.cell_number(c) is not None
        and lo <= B.A.cell_number(c) <= (hi or 10 ** 9)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc, out = B._run(fake_args(), 48, 90, True, "DESCRIPTIVE ONLY")
    finally:
        (B.R.build_rows, B.A.find_captures,
         B.windowed_captures) = old
    train_caps, train_ref = calls[0]
    check("fit reference is the training captures only",
          train_ref == train_caps and not any(
              B.A.cell_number(c) > 47 for c in train_ref), calls[0])
    check("training captures are cells <= 47",
          sorted(B.A.cell_number(c) for c in train_caps) == [3, 30, 47])
    check("scored reference is the full capture set",
          calls[1][1] == caps)
    check("report records the effective fit window",
          out["fit_window"] == {"first_cell": 1, "last_cell": 47,
                                "registered_last_cell": 47}, out)
    fit_p = out["provenance"]["fit"]
    check("fit provenance counts rebuilds and dropped captures",
          fit_p["realised_rebuilt"] == 1
          and fit_p["dropped_no_ohlc_captures"] == 1
          and fit_p["captures"] == 3
          and "training captures only" in fit_p["price_reference"], fit_p)
    check("scored provenance names the wider reference",
          "all --captures" in out["provenance"]["scored"][
              "price_reference"])
    check("descriptive report has no verdict key", "verdict" not in out)
    lam, n, _p = B.fit(training_rows())
    clean = B.make_report(fake_res(), lam, n, 0, False, 47, {})
    check("clean report carries verdict and the fit window",
          "verdict" in clean and clean["fit_window"]["last_cell"] == 47)
    check("fit cutoff is labelled in the text",
          "cells <= 40 only" in B.render(fake_res(), lam, n, 0, True,
                                         "t", 40))


def make_capture(root, cell_dir, cutoff, ticker):
    d = os.path.join(root, cell_dir, cutoff, ticker)
    os.makedirs(os.path.join(d, "digest"))
    for fn in ("manifest.json", "realised.json"):
        open(os.path.join(d, fn), "w").write("{}")
    open(os.path.join(d, "digest", "ensemble.json"), "w").write("{}")
    return d


def test_dedup_within_window():
    with tempfile.TemporaryDirectory() as t:
        tr = make_capture(t, "run-cell47", "2025-01-01", "COMI.CA")
        ho = make_capture(t, "run-cell91", "2025-01-01", "COMI.CA")
        other = make_capture(t, "run-cell30", "2025-01-02", "ETEL.CA")
        un = make_capture(t, "run-unnumbered", "2025-01-03", "TMGH.CA")
        old = B.A.find_captures([t], None)
        check("global dedup lets the later cell replace the training "
              "capture (the defect this guards against)",
              ho in old and tr not in old, old)
        train = B.windowed_captures([t], 1, 47)
        check("training window keeps the training-cell capture",
              tr in train and ho not in train, train)
        check("training window keeps other training captures",
              other in train)
        held = B.windowed_captures([t], 91, None)
        check("clean window deduplicates to the later cell",
              held == [ho], held)
        check("descriptive window 48-90 excludes both",
              B.windowed_captures([t], 48, 90) == [])
        check("unnumbered never enters a window",
              un not in train and un not in held
              and un not in B.windowed_captures([t], 1, None))
        later = make_capture(t, "run-cell9", "2025-01-01", "COMI.CA")
        check("within one window the lexically latest path wins",
              B.windowed_captures([t], 1, 47) == [later, other] and tr not in B.windowed_captures(
                      [t], 1, 47), B.windowed_captures([t], 1, 47))



def test_run_uses_window_dedup():
    with tempfile.TemporaryDirectory() as t:
        tr = make_capture(t, "run-cell47", "2025-01-01", "COMI.CA")
        make_capture(t, "run-cell91", "2025-01-01", "COMI.CA")
        sc = make_capture(t, "run-cell60", "2025-01-05", "TMGH.CA")
        make_capture(t, "run-cell95", "2025-01-05", "TMGH.CA")
        calls = []

        def fake_build(cs, ref=None):
            calls.append((list(cs), list(ref)))
            return (training_rows() if cs and cs[0] == tr else
                    cutoff("s1", 0.5, 0.5)), []
        old = B.R.build_rows
        B.R.build_rows = fake_build
        try:
            ns = fake_args()
            ns.captures = [t]
            with contextlib.redirect_stdout(io.StringIO()):
                rc, out = B._run(ns, 48, 90, True, "DESCRIPTIVE ONLY")
        finally:
            B.R.build_rows = old
        check("_run fits on the training-cell capture despite the later "
              "cell", rc == 0 and calls[0][0] == [tr], calls)
        check("_run scores the in-window capture despite a later cell",
              calls[1][0] == [sc], calls[1])
        check("reference set stays the full dedup'd set for the score "
              "rebuild", calls[1][1] == B.A.find_captures([t], None))


def test_run_excludes_trained_keys():
    with tempfile.TemporaryDirectory() as t:
        tr = make_capture(t, "run-cell47", "2025-01-01", "COMI.CA")
        col = make_capture(t, "run-cell60", "2025-01-01", "COMI.CA")
        sc = make_capture(t, "run-cell60", "2025-01-05", "TMGH.CA")
        calls = []

        def fake_build(cs, ref=None):
            calls.append((list(cs), list(ref)))
            return (training_rows() if cs and cs[0] == tr else
                    cutoff("s1", 0.5, 0.5)), []
        old = B.R.build_rows
        B.R.build_rows = fake_build
        try:
            ns = fake_args()
            ns.captures = [t]
            with contextlib.redirect_stdout(io.StringIO()):
                rc, out = B._run(ns, 48, 90, True, "DESCRIPTIVE ONLY")
        finally:
            B.R.build_rows = old
        check("training capture is fitted on", calls[0][0] == [tr], calls)
        check("same (cutoff, ticker) under a scoring cell is excluded",
              calls[1][0] == [sc] and col not in calls[1][0], calls[1])
        check("reference set stays the full dedup'd set for the score "
              "rebuild", col in calls[1][1])


def test_diagnostic_training_window_kept():
    with tempfile.TemporaryDirectory() as t:
        tr = make_capture(t, "run-cell47", "2025-01-01", "COMI.CA")
        col = make_capture(t, "run-cell60", "2025-01-01", "COMI.CA")
        sc = make_capture(t, "run-cell60", "2025-01-05", "TMGH.CA")
        calls = []

        def fake_build(cs, ref=None):
            calls.append((list(cs), list(ref)))
            return (training_rows() if cs and cs[0] == tr else
                    cutoff("s1", 0.5, 0.5)), []
        old = B.R.build_rows
        B.R.build_rows = fake_build
        try:
            ns = fake_args()
            ns.captures = [t]
            with contextlib.redirect_stdout(io.StringIO()):
                rc, out = B._run(ns, 1, 47, True, "DESCRIPTIVE ONLY")
        finally:
            B.R.build_rows = old
        check("diagnostic scoring of the training window is not excluded",
              rc == 0 and calls[1][0] == [tr], calls)


def test_exclude_trained():
    tr = ["/r/c-cell47/2025-01-01/COMI.CA", "/r/c-cell3/2025-01-02/etel.ca"]
    sc = ["/r/c-cell60/2025-01-01/COMI.CA", "/r/c-cell61/2025-01-02/ETEL.CA",
          "/r/c-cell62/2025-01-03/COMI.CA"]
    out = B.exclude_trained(sc, tr)
    check("exclusion matches on (cutoff, TICKER), case-insensitive",
          out == ["/r/c-cell62/2025-01-03/COMI.CA"], out)
    check("empty training set excludes nothing",
          B.exclude_trained(sc, []) == sc)


class Suite(unittest.TestCase):
    """Runs the checks under `unittest discover -s scripts`."""

    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def run_all():
    for fn in (test_constants, test_pools, test_shrunk_sigma, test_fit,
               test_score_rows, test_cell_selection, test_cli_guards,
               test_render, test_dedup_within_window,
               test_run_uses_window_dedup, test_run_excludes_trained_keys, test_diagnostic_training_window_kept, test_exclude_trained, test_fit_window_guards,
               test_fit_reference_and_provenance):
        fn()


def main():
    run_all()
    print("test_bayes_shrinkage: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
