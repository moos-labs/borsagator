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


def main():
    for fn in (test_constants, test_pools, test_shrunk_sigma, test_fit,
               test_score_rows, test_cell_selection, test_cli_guards,
               test_render):
        fn()
    print("test_bayes_shrinkage: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
