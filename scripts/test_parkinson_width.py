#!/usr/bin/env python3
"""Tests for benchmarks/replay_parkinson_width.py (INS-IMPROVE-006 A).
Standalone, stdlib only.
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
    "pkw", os.path.join(ROOT, "benchmarks", "replay_parkinson_width.py"))
P = importlib.util.module_from_spec(spec)
sys.modules["pkw"] = P
spec.loader.exec_module(P)


def row(real=1.0, sp=0.02, s60=0.02, h="week", t="A", a="d1"):
    return {"ticker": t, "as_of": a, "horizon": h, "real": real,
            "naive_half": P.R.half_pct(s60, h, 1.2816, 1.0),
            "mult": 1.0, "v2_sigma": s60,
            "sig": {"s60": s60, "park60": sp}}


def test_constants():
    check("v2 pinned", P.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("rule minimums", (P.MIN_ROWS, P.MIN_TICKERS, P.MIN_CUTOFFS)
          == (30, 5, 2))
    check("clean cells start at 91", P.CLEAN_MIN_CELL == 91)


def test_estimator():
    bars = [(10, 10.5, 9.5, 10)] * 60
    sp = P.R.sigmas(bars)["park60"]
    want = math.sqrt(math.log(10.5 / 9.5) ** 2 / (4 * math.log(2)))
    check("parkinson formula", sp is not None and abs(sp - want) < 1e-9,
          (sp, want))


def test_score_rows():
    wide = P.score_rows([row(real=8.0, sp=0.04, s60=0.02)])[0]
    base = P.score_rows([row(real=8.0, sp=0.02, s60=0.02)])[0]
    half = P.R.half_pct(0.04, "week", 1.28, 1.0)
    half_v2 = P.R.half_pct(0.02, "week", 1.28, 1.0)
    check("wider sigma widens band (through score_rows)",
          wide["in_ch"] and not base["in_ch"] and 8.0 < half
          and 8.0 > half_v2, (half, half_v2))
    check("wider band reflected in IS for an inside move",
          P.score_rows([row(real=0.0, sp=0.04, s60=0.02)])[0]["is_ch"]
          > P.score_rows([row(real=0.0, sp=0.02, s60=0.02)])[0]["is_ch"])
    check("k not refitted: equal sigma equals v2",
          abs(P.score_rows([row(sp=0.02, s60=0.02)])[0]["is_ch"]
              - P.score_rows([row(sp=0.02, s60=0.02)])[0]["is_v2"]) < 1e-9)
    check("missing park skipped", P.score_rows([row(sp=None)]) == [])
    check("coverage flag", P.score_rows([row(real=0.0)])[0]["in_ch"])


def test_verdict():
    res = {h: {"n": 5, "tickers": 2, "cutoffs": 1,
               "ch_ci_cutoff": [0.1, 0.2], "ch": {"coverage": 0.8},
               "ch_cov_ci_cutoff": [0.76, 0.84]}
           for h in P.HORIZONS}
    check("small insufficient", P.keep_verdict(res)[0] == "INSUFFICIENT")
    for h in P.HORIZONS:
        res[h].update(n=40, tickers=6, cutoffs=3)
    check("keep", P.keep_verdict(res)[0] == "KEEP")
    res["day"]["ch_ci_cutoff"] = [-0.01, 0.2]
    check("ci spans zero rejects", P.keep_verdict(res)[0] == "REJECT")
    res["day"]["ch_ci_cutoff"] = [0.1, 0.2]
    res["week"]["ch"]["coverage"] = 0.7
    res["week"]["ch_cov_ci_cutoff"] = [0.60, 0.72]
    check("coverage CI below the band rejects",
          P.keep_verdict(res)[0] == "REJECT")
    res["week"]["ch_cov_ci_cutoff"] = [0.66, 0.79]
    check("point outside band but CI overlaps keeps",
          P.keep_verdict(res)[0] == "KEEP")
    res["week"]["ch_cov_ci_cutoff"] = [0.60, 0.79]
    check("overlapping CI wider than the 0.15 cap rejects",
          P.keep_verdict(res)[0] == "REJECT")
    res["week"]["ch_cov_ci_cutoff"] = [0.66, 0.79]
    res["week"]["ch_cov_ci_cutoff"] = [0.62, 0.75]
    check("CI touching the lower edge overlaps",
          P.keep_verdict(res)[0] == "KEEP")
    res["week"]["ch_cov_ci_cutoff"] = [0.86, 0.95]
    check("CI above the band rejects", P.keep_verdict(res)[0] == "REJECT")
    res["week"]["ch_cov_ci_cutoff"] = [None, None]
    check("undefined CI rejects", P.keep_verdict(res)[0] == "REJECT")


def test_refusal():
    rc = P.main(["score", "--captures", "/nonexistent", "--min-cell", "73"])
    check("refuses seen cells", rc == 2)


def test_unnumbered_and_json():
    import tempfile
    import contextlib
    import io
    with tempfile.TemporaryDirectory() as d:
        cap = os.path.join(d, "2025-11-14", "TST")
        os.makedirs(os.path.join(cap, "digest"))
        for fn in ("manifest.json", "realised.json"):
            open(os.path.join(cap, fn), "w").write("{}")
        open(os.path.join(cap, "digest", "ensemble.json"), "w").write("{}")
        check("unnumbered capture is findable",
              P.A.find_captures([d], 91) != [])
        out = os.path.join(d, "o.json")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = P.main(["score", "--captures", d, "--min-cell", "91",
                         "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("exit 0", rc == 0)
        check("unnumbered capture dropped from scoring",
              all(data["results"][h]["n"] == 0 for h in P.HORIZONS),
              data["results"])
        with contextlib.redirect_stdout(buf):
            P.main(["score", "--captures", d, "--min-cell", "48",
                    "--descriptive", "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("descriptive json carries no verdict",
              "verdict" not in data and data["descriptive"] is True)
        with contextlib.redirect_stdout(buf):
            P.main(["score", "--captures", d, "--reps", "50",
                    "--json", out])
        check("clean json carries a verdict",
              "verdict" in json.load(open(out)))


def main():
    for fn in (test_constants, test_estimator, test_score_rows,
               test_verdict, test_refusal, test_unnumbered_and_json):
        fn()
    print("test_parkinson_width: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
