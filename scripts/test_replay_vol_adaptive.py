#!/usr/bin/env python3
"""Tests for benchmarks/replay_vol_adaptive.py (INS-IMPROVE-001 r3).
Standalone, stdlib only: python3 scripts/test_replay_vol_adaptive.py
"""
import importlib.util
import json
import math
import os
import random
import sys

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
    "vadapt", os.path.join(ROOT, "benchmarks", "replay_vol_adaptive.py"))
V = importlib.util.module_from_spec(spec)
sys.modules["vadapt"] = V
spec.loader.exec_module(V)


def test_constants():
    check("eps 0.20", V.EPS == 0.20)
    check("long window 250", V.LONG_N == 250)
    check("v2 k frozen exact", V.ens_mod.V2_BAND_K
          == {"day": 1.15, "week": 1.28, "month": 1.20},
          str(V.ens_mod.V2_BAND_K))


def test_sigma_eff():
    check("eps 0 is s60", V.sigma_eff(0.02, 0.03, eps=0.0) == 0.02)
    check("eps 1 is sigma_long",
          abs(V.sigma_eff(0.02, 0.03, eps=1.0) - 0.03) < 1e-12)
    check("default pulls 20% toward long",
          abs(V.sigma_eff(0.02, 0.03) - 0.022) < 1e-12)
    check("equal vols unchanged", abs(V.sigma_eff(0.02, 0.02) - 0.02)
          < 1e-12)
    check("missing long is None", V.sigma_eff(0.02, None) is None)
    check("zero s60 is None", V.sigma_eff(0.0, 0.02) is None)


def test_sigma_long():
    rng = random.Random(1)
    c = [100.0]
    for _ in range(260):
        c.append(c[-1] * math.exp(rng.gauss(0, 0.01)))
    check("long sigma near 0.01", abs(V.sigma_long(c) - 0.01) < 0.002)
    check("under 200 returns is None", V.sigma_long(c[:150]) is None)
    check("uses last 250 returns only",
          len(V.R._logrets(c)[-V.LONG_N:]) == 250)


def mkrow(real, h="week", t="A", a="2026-01-01", s60=0.01, sl=0.012):
    se = V.sigma_eff(s60, sl)
    naive = 1.2816 * s60 * math.sqrt(V.R.SESSIONS[h]) * 100
    return {"horizon": h, "real": real, "naive_half": naive,
            "v2_sigma": s60, "mult": 1.0, "ticker": t, "as_of": a,
            "sig": {"s60": s60}, "sigma_long": sl, "sigma_eff": se,
            "cell": 1}


def test_fit_and_score():
    rows = []
    rng = random.Random(3)
    for i in range(40):
        for h in V.HORIZONS:
            sd = 0.012 * math.sqrt(V.R.SESSIONS[h]) * 100
            rows.append(mkrow(rng.gauss(0, sd), h=h, t="T%d" % (i % 4),
                              a="2025-0%d-01" % (i % 5 + 1)))
    fz = V.fit(rows)
    check("k fitted on grid", all(0.5 <= fz["k"][h] <= 2.5
                                  for h in V.HORIZONS), str(fz["k"]))
    check("eps recorded", fz["eps"] == 0.20)
    pairs = V.score_rows(rows[:6], fz)
    check("score rows built", len(pairs) == 6
          and {"is_naive", "is_v2", "is_ch", "in_ch"} <= set(pairs[0]))
    check("rows without sigma_eff skipped",
          V.score_rows([dict(rows[0], sigma_eff=None)], fz) == [])
    check("rows without v2 sigma skipped",
          V.score_rows([dict(rows[0], v2_sigma=None)], fz) == [])


def res_with(n, tickers, cutoffs, lo, cov):
    return {h: {"n": n, "tickers": tickers, "cutoffs": cutoffs,
                "ch_ci_cutoff": [lo, 0.1], "ch": {"coverage": cov},
                "ch_cov_ci_cutoff": [cov - 0.03, cov + 0.03]}
            for h in V.HORIZONS}


def test_verdict():
    check("six rows insufficient",
          V.keep_verdict(res_with(6, 6, 1, 0.1, 0.8))[0]
          == "INSUFFICIENT")
    check("keep", V.keep_verdict(res_with(36, 6, 3, 0.01, 0.8))[0]
          == "KEEP")
    check("ci lower 0 rejects",
          V.keep_verdict(res_with(36, 6, 3, 0.0, 0.8))[0] == "REJECT")
    check("coverage above band rejects",
          V.keep_verdict(res_with(36, 6, 3, 0.05, 0.9))[0] == "REJECT")
    m = res_with(36, 6, 3, 0.05, 0.8)
    m["month"]["ch"]["coverage"] = 0.42
    m["month"]["ch_cov_ci_cutoff"] = [0.39, 0.45]
    check("one bad horizon rejects", V.keep_verdict(m)[0] == "REJECT")


def test_coverage_ci_overlap():
    def with_ci(ci, cov):
        r = res_with(36, 6, 3, 0.05, cov)
        for h in V.HORIZONS:
            r[h]["ch_cov_ci_cutoff"] = ci
        return r
    check("point outside the band but CI overlaps: keep",
          V.keep_verdict(with_ci([0.66, 0.81], 0.73))[0] == "KEEP")
    check("CI entirely below the band rejects",
          V.keep_verdict(with_ci([0.55, 0.70], 0.62))[0] == "REJECT")
    check("CI entirely above the band rejects",
          V.keep_verdict(with_ci([0.86, 0.95], 0.90))[0] == "REJECT")
    check("CI touching 0.85 overlaps",
          V.keep_verdict(with_ci([0.85, 0.95], 0.90))[0] == "KEEP")
    check("CI touching 0.75 overlaps",
          V.keep_verdict(with_ci([0.60, 0.75], 0.68))[0] == "KEEP")
    check("undefined CI is not an overlap",
          V.keep_verdict(with_ci([None, None], 0.80))[0] == "REJECT")


def test_refuses_seen_cells():
    check("refuses cells below 73", V.main(
        ["score", "--frozen", "/x", "--captures", "/nonexistent",
         "--min-cell", "48"]) == 2)


def test_descriptive_json_has_no_verdict():
    import contextlib
    import io
    import tempfile
    frozen = os.path.join(ROOT, "benchmarks", "frozen_vol_adaptive_r3.json")
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.json")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = V.main(["score", "--frozen", frozen, "--captures", d,
                         "--min-cell", "48", "--descriptive",
                         "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("descriptive run exits 0", rc == 0)
        check("descriptive json carries no verdict",
              "verdict" not in data and data["descriptive"] is True)
        with contextlib.redirect_stdout(buf):
            rc = V.main(["score", "--frozen", frozen, "--captures", d,
                         "--min-cell", "73", "--reps", "50",
                         "--json", out])
        data = json.load(open(out))
        check("clean run exits 0", rc == 0)
        check("clean json carries a verdict",
              "verdict" in data and data["descriptive"] is False)


def test_unnumbered_dropped_both_paths():
    import contextlib
    import io
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cap = os.path.join(d, "2025-11-14", "TST")
        os.makedirs(os.path.join(cap, "digest"))
        for fn in ("manifest.json", "realised.json"):
            open(os.path.join(cap, fn), "w").write("{}")
        open(os.path.join(cap, "digest", "ensemble.json"), "w").write("{}")
        frozen = os.path.join(ROOT, "benchmarks",
                              "frozen_vol_adaptive_r3.json")
        out = os.path.join(d, "o.json")
        seen = []

        def fake_rows(caps, allc):
            seen.append(list(caps))
            return [{"ticker": "TST", "as_of": "2025-11-14", "horizon": h,
                     "real": 1.0, "naive_half": 5.0, "mult": 1.0,
                     "v2_sigma": 0.02, "sigma_long": 0.02,
                     "sigma_eff": 0.02, "cell": 0}
                    for c in caps for h in V.HORIZONS], []
        real_build, real_fit = V.build_rows, V.fit
        real_render = V.render_fit
        V.render_fit = lambda fz: "fit"
        V.build_rows = fake_rows
        V.fit = lambda rows: {"k": {h: 1.0 for h in V.HORIZONS},
                              "eps": 0.2, "n": len(rows)}
        buf = io.StringIO()
        try:
            check("unnumbered capture is findable",
                  V.A.find_captures([d], None) != [])
            with contextlib.redirect_stdout(buf):
                V.main(["fit", "--captures", d, "--out", out])
            check("fit path drops unnumbered capture", seen[-1] == [])
            with contextlib.redirect_stdout(buf):
                V.main(["score", "--frozen", frozen, "--captures", d,
                        "--min-cell", "48", "--descriptive",
                        "--reps", "50", "--json", out])
            check("score path drops unnumbered capture", seen[-1] == [])
            data = json.load(open(out))
            check("nothing scored",
                  all(data["results"][h]["n"] == 0 for h in V.HORIZONS))
        finally:
            V.build_rows, V.fit = real_build, real_fit
            V.render_fit = real_render


def main():
    for fn in (test_constants, test_sigma_eff, test_sigma_long,
               test_fit_and_score, test_verdict, test_coverage_ci_overlap,
               test_refuses_seen_cells,
               test_descriptive_json_has_no_verdict,
               test_unnumbered_dropped_both_paths):
        fn()
    print("test_replay_vol_adaptive: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
