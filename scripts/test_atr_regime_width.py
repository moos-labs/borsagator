#!/usr/bin/env python3
"""Tests for benchmarks/replay_atr_regime_width.py (round 57).
Standalone, stdlib only, fixed synthetic inputs.
"""
import contextlib
import importlib.util
import io
import json
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
    "atrw", os.path.join(ROOT, "benchmarks",
                         "replay_atr_regime_width.py"))
W = importlib.util.module_from_spec(spec)
sys.modules["atrw"] = W
spec.loader.exec_module(W)


def bars(ranges, close=10.0):
    return [(close, close + r / 2.0, close - r / 2.0, close)
            for r in ranges]


def row(x, real, h="day", t="A", a="d1", s=0.02):
    return {"ticker": t, "as_of": a, "horizon": h, "real": real,
            "naive_half": W.R.half_pct(s, h, 1.2816, 1.0), "mult": 1.0,
            "v2_sigma": s, "sig": {"atr_x": x}}


def test_constants():
    check("v2 pinned", W.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("training cutoff 47, clean 91",
          (W.FIT_MAX_CELL, W.CLEAN_MIN_CELL) == (47, 91))
    check("grid 0.50..2.00", (W.F_GRID[0], W.F_GRID[-1]) == (0.5, 2.0))
    check("keep rule is the shared one",
          W.keep_verdict is W.PK.keep_verdict)


def test_atr_ratio():
    b = bars([1.0] * 42 + [2.0] * 20)
    x = W.atr_ratio(b)
    check("ATR20/ATR60 exact", x is not None and abs(x - 1.5) < 1e-9, x)
    check("constant range is 1", abs(W.atr_ratio(bars([1.0] * 62)) - 1)
          < 1e-9)
    check("under 61 bars is None", W.atr_ratio(bars([1.0] * 60)) is None)
    gap = [(10, 10.1, 9.9, 10)] * 61 + [(20, 20.1, 19.9, 20)]
    tr = W._true_ranges(gap)
    check("true range uses the previous close", abs(tr[-1] - 10.1) < 1e-9,
          tr[-1])


def test_percentile_regime():
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    check("tertile nearest rank",
          (W.percentile(v, 1 / 3.0), W.percentile(v, 2 / 3.0)) == (3, 6))
    thr = (3, 6)
    check("regime edges", [W.regime(x, thr) for x in (3, 3.1, 6, 6.1)]
          == ["low", "medium", "medium", "high"])


def training():
    rows = []
    for i in range(12):
        rows.append(row(0.5, 0.1, a="l%d" % i))
        rows.append(row(1.0, 2.3, a="m%d" % i))
        rows.append(row(2.0, 6.0, a="h%d" % i))
    return rows


def test_fit():
    thr, f, n = W.fit(training())
    check("thresholds from training x", thr == (0.5, 1.0), thr)
    check("low regime narrows", f["day/low"] < 1.0, f["day/low"])
    check("high regime widens", f["day/high"] > 1.0, f["day/high"])
    check("medium stays near 1", abs(f["day/medium"] - 1.0) < 0.03,
          f["day/medium"])
    check("bucket counts", n["day/low"] == 12 and n["day/high"] == 12)
    check("thin bucket keeps 1.0 (no week rows)", f["week/low"] == 1.0)
    thin = [row(0.5, 0.1, a="l%d" % i) for i in range(9)]
    check("below MIN_FIT_ROWS keeps 1.0",
          W.fit(thin)[1]["day/low"] == 1.0)
    check("no usable x gives no fit", W.fit([row(None, 1.0)]) is None)


def test_score_rows():
    thr = (0.5, 1.0)
    fac = {"%s/%s" % (h, g): 1.0 for h in W.HORIZONS for g in W.REGIMES}
    fac["day/high"] = 2.0
    v2 = W.R.half_pct(0.02, "day", 1.15, 1.0)
    hi = W.score_rows([row(2.0, 1.5 * v2)], thr, fac)[0]
    lo = W.score_rows([row(0.5, 1.5 * v2)], thr, fac)[0]
    check("high regime widens the band (through score_rows)",
          hi["in_ch"] and not hi["in_v2"] and not lo["in_ch"], (hi, lo))
    check("factor 1 equals v2",
          abs(W.score_rows([row(1.0, 0.0)], thr, fac)[0]["is_ch"]
              - W.score_rows([row(1.0, 0.0)], thr, fac)[0]["is_v2"])
          < 1e-9)
    check("regime recorded", hi["regime"] == "high"
          and lo["regime"] == "low")
    check("no regime skipped", W.score_rows([row(None, 1.0)], thr, fac)
          == [])
    check("wider band costs width on an inside move",
          W.score_rows([row(2.0, 0.0)], thr, fac)[0]["is_ch"]
          > W.score_rows([row(2.0, 0.0)], thr, fac)[0]["is_v2"])


def test_cell_selection():
    caps = ["/x/c-cell47/d/T", "/x/c-cell48/d/T", "/x/c-cell90/d/T",
            "/x/c-cell91/d/T", "/x/unnumbered/d/T"]
    pick = lambda lo, hi: [W.A.cell_number(c) for c in
                           W.select_caps(caps, lo, hi)]
    check("training is cells <= 47 only", pick(1, 47) == [47], pick(1, 47))
    check("descriptive window 48-90", pick(48, 90) == [48, 90])
    check("clean window 91+, unnumbered dropped", pick(91, None) == [91])


def test_cli_guards():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc1 = W.main(["score", "--captures", "/nonexistent",
                      "--min-cell", "73"])
        rc2 = W.main(["score", "--captures", "/nonexistent",
                      "--min-cell", "40", "--descriptive"])
        rc3 = W.main(["score", "--captures", "/nonexistent",
                      "--min-cell", "48", "--descriptive"])
    check("clean scoring refuses seen cells", rc1 == 2)
    check("scored cells may not overlap training", rc2 == 2)
    check("no training rows refuses", rc3 == 2
          and "no training rows" in buf.getvalue())


def test_render_and_json():
    thr, f, n = W.fit(training())
    cell = {"n": 1, "cutoffs": 1, "tickers": 1,
            "v2": {"coverage": 0.8, "range_skill": 0.0},
            "ch": {"coverage": 0.8, "range_skill": 0.0},
            "ch_ci_cutoff": [0.1, 0.2], "ch_cov_ci_cutoff": [0.7, 0.8],
            "ch_ci_ticker": [0.1, 0.2]}
    res = {h: dict(cell) for h in W.HORIZONS}
    d = W.render(res, thr, f, n, 0, True, "DESCRIPTIVE ONLY")
    c = W.render(res, thr, f, n, 0, False, "CLEAN SCORING")
    check("descriptive text has no verdict word or keep rule",
          "verdict" not in d.lower() and "KEEP" not in d, d)
    check("clean text carries the keep rule", "KEEP RULE" in c)
    check("fit printed", "high>" in d and "day factors" in d)
    with tempfile.TemporaryDirectory() as t:
        cap = os.path.join(t, "2025-11-14", "TST")
        os.makedirs(os.path.join(cap, "digest"))
        for fn in ("manifest.json", "realised.json"):
            open(os.path.join(cap, fn), "w").write("{}")
        open(os.path.join(cap, "digest", "ensemble.json"), "w").write("{}")
        out = os.path.join(t, "o.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = W.main(["score", "--captures", t, "--min-cell", "48",
                         "--descriptive", "--json", out])
        check("no training rows writes no json",
              rc == 2 and not os.path.exists(out))


def main():
    for fn in (test_constants, test_atr_ratio, test_percentile_regime,
               test_fit, test_score_rows, test_cell_selection,
               test_cli_guards, test_render_and_json):
        fn()
    print("test_atr_regime_width: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
