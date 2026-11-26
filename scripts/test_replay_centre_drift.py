#!/usr/bin/env python3
"""Tests for benchmarks/replay_centre_drift.py (INS-IMPROVE-001 r3).
Standalone, stdlib only: python3 scripts/test_replay_centre_drift.py
"""
import importlib.util
import json
import math
import os
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
    "drift", os.path.join(ROOT, "benchmarks", "replay_centre_drift.py"))
D = importlib.util.module_from_spec(spec)
sys.modules["drift"] = D
spec.loader.exec_module(D)


def row(real, v2s=0.01, m60=0.001, h="week", mult=1.0, t="A",
        a="2026-01-01"):
    naive = 1.2816 * v2s * math.sqrt(D.R.SESSIONS[h]) * 100
    return {"horizon": h, "real": real, "naive_half": naive,
            "v2_sigma": v2s, "mult": mult, "mean_ret_60": m60,
            "ticker": t, "as_of": a}


def test_constants():
    check("beta 0.10", D.BETA == 0.10)
    check("window 60", D.DRIFT_N == 60)
    check("v2 k frozen exact", D.ens_mod.V2_BAND_K
          == {"day": 1.15, "week": 1.28, "month": 1.20},
          str(D.ens_mod.V2_BAND_K))


def test_mean_ret():
    closes = [100.0 * math.exp(0.001 * i) for i in range(61)]
    check("mean of log returns",
          abs(D.mean_ret(closes) - 0.001) < 1e-12)
    check("too short is None", D.mean_ret(closes[:30]) is None)


def test_centre():
    check("scales by sessions",
          abs(D.centre_pct(0.001, "month") - 0.10 * 0.001 * 21 * 100)
          < 1e-12)
    check("day sessions 1",
          abs(D.centre_pct(0.001, "day") - 0.01) < 1e-12)
    check("none stays none", D.centre_pct(None, "week") is None)


def test_score_rows():
    r = row(real=1.0)
    p = D.score_rows([r])[0]
    half = D.R.half_pct(0.01, "week", D.ens_mod.V2_BAND_K["week"])
    c = D.centre_pct(0.001, "week")
    check("v2 centred 0", p["in_v2"] == (abs(1.0) <= half))
    check("challenger centred on drift",
          p["in_ch"] == (abs(1.0 - c) <= half))
    check("missing drift skipped",
          D.score_rows([dict(row(1.0), mean_ret_60=None)]) == [])
    check("missing v2 sigma skipped",
          D.score_rows([dict(row(1.0), v2_sigma=None)]) == [])
    big = D.score_rows([row(real=half + 0.05 * c, m60=0.001)])[0]
    check("drift can pull a move into the band",
          big["in_ch"] and not big["in_v2"] if c > 0 else True)


def res_with(n, tickers, cutoffs, lo, cov):
    return {h: {"n": n, "tickers": tickers, "cutoffs": cutoffs,
                "ch_ci_cutoff": [lo, 0.1], "ch": {"coverage": cov},
                "ch_cov_ci_cutoff": [cov - 0.03, cov + 0.03]}
            for h in D.HORIZONS}


def test_verdict():
    check("six rows insufficient",
          D.keep_verdict(res_with(6, 6, 1, 0.1, 0.8))[0]
          == "INSUFFICIENT")
    check("keep", D.keep_verdict(res_with(36, 6, 3, 0.01, 0.8))[0]
          == "KEEP")
    check("ci lower 0 rejects",
          D.keep_verdict(res_with(36, 6, 3, 0.0, 0.8))[0] == "REJECT")
    check("coverage rejects",
          D.keep_verdict(res_with(36, 6, 3, 0.05, 0.6))[0] == "REJECT")
    mixed = res_with(36, 6, 3, 0.05, 0.8)
    mixed["month"]["ch"]["coverage"] = 0.5
    mixed["month"]["ch_cov_ci_cutoff"] = [0.47, 0.53]
    check("one bad horizon rejects", D.keep_verdict(mixed)[0]
          == "REJECT")
    short = res_with(36, 6, 3, 0.05, 0.8)
    short["day"]["n"] = 20
    check("one short horizon is insufficient",
          D.keep_verdict(short)[0] == "INSUFFICIENT")


def test_coverage_ci_overlap():
    def with_ci(ci, cov):
        r = res_with(36, 6, 3, 0.05, cov)
        for h in D.HORIZONS:
            r[h]["ch_cov_ci_cutoff"] = ci
        return r
    check("point outside the band but CI overlaps: keep",
          D.keep_verdict(with_ci([0.66, 0.81], 0.73))[0] == "KEEP")
    check("CI entirely below the band rejects",
          D.keep_verdict(with_ci([0.55, 0.70], 0.62))[0] == "REJECT")
    check("CI entirely above the band rejects",
          D.keep_verdict(with_ci([0.86, 0.95], 0.90))[0] == "REJECT")
    check("CI touching 0.85 overlaps",
          D.keep_verdict(with_ci([0.85, 0.95], 0.90))[0] == "KEEP")
    check("CI touching 0.75 overlaps",
          D.keep_verdict(with_ci([0.60, 0.75], 0.68))[0] == "KEEP")
    check("undefined CI is not an overlap",
          D.keep_verdict(with_ci([None, None], 0.80))[0] == "REJECT")


def test_refuses_seen_cells():
    check("refuses cells below 73", D.main(
        ["--captures", "/nonexistent", "--min-cell", "48"]) == 2)


def test_descriptive_json_and_unnumbered():
    import contextlib
    import io
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cap = os.path.join(d, "2025-11-14", "TST")
        os.makedirs(os.path.join(cap, "digest"))
        for fn in ("manifest.json", "realised.json"):
            open(os.path.join(cap, fn), "w").write("{}")
        open(os.path.join(cap, "digest", "ensemble.json"), "w").write("{}")
        out = os.path.join(d, "o.json")
        seen = []

        def fake_rows(caps, allc):
            seen.append(list(caps))
            return [row(1.0, t="TST", a="2025-11-14", h=h)
                    for c in caps for h in D.HORIZONS], []
        real_build = D.build_rows
        D.build_rows = fake_rows
        buf = io.StringIO()
        try:
            check("unnumbered capture is findable",
                  D.A.find_captures([d], 48) != [])
            with contextlib.redirect_stdout(buf):
                rc = D.main(["--captures", d, "--min-cell", "48",
                             "--descriptive", "--reps", "50",
                             "--json", out])
            data = json.load(open(out))
            check("descriptive run exits 0", rc == 0)
            check("unnumbered capture dropped from scoring",
                  seen[-1] == [] and all(
                      data["results"][h]["n"] == 0 for h in D.HORIZONS))
            check("descriptive json carries no verdict",
                  "verdict" not in data and data["descriptive"] is True)
            with contextlib.redirect_stdout(buf):
                D.main(["--captures", d, "--reps", "50", "--json", out])
            data = json.load(open(out))
            check("clean json carries a verdict",
                  "verdict" in data and data["descriptive"] is False)
        finally:
            D.build_rows = real_build


def main():
    for fn in (test_constants, test_mean_ret, test_centre, test_score_rows,
               test_verdict, test_coverage_ci_overlap,
               test_refuses_seen_cells,
               test_descriptive_json_and_unnumbered):
        fn()
    print("test_replay_centre_drift: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
