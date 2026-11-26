#!/usr/bin/env python3
"""Tests for benchmarks/replay_log_har.py (INS-IMPROVE-006 C).
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
    "lhar", os.path.join(ROOT, "benchmarks", "replay_log_har.py"))
H = importlib.util.module_from_spec(spec)
sys.modules["lhar"] = H
spec.loader.exec_module(H)


def bars(n, hl=0.02, wobble=0.0):
    out = []
    for i in range(n):
        w = 1.0 + wobble * math.sin(i)
        h = 10.0 * (1 + hl * w / 2)
        l = 10.0 * (1 - hl * w / 2)
        out.append((10.0, h, l, 10.0))
    return out


def test_constants():
    check("pinned v2", H.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("spec", (H.LAGS, H.FLOOR_FRAC, H.MIN_OBS)
          == ((1, 5, 22), 0.05, 120))
    check("clean cell start", H.CLEAN_MIN_CELL == 91)


def test_rv():
    b = [(10.0, 10.5, 9.5, 10.0)] * 5
    rv = H.rv_series(b, "park")
    want = math.log(10.5 / 9.5) ** 2 / (4 * math.log(2))
    check("parkinson rv", abs(rv[0] - want) < 1e-12)
    g = H.rv_series(b, "gk")
    want_g = 0.5 * math.log(10.5 / 9.5) ** 2
    check("gk rv with c == o", abs(g[0] - want_g) < 1e-12)
    z = H.rv_series([(10, 10, 10, 10)] + [(10, 10.5, 9.5, 10)] * 9)
    check("zero range floored, positive", z[0] > 0)


def test_solve():
    x = H._solve([[2.0, 0.0], [0.0, 4.0]], [2.0, 8.0])
    check("solve", abs(x[0] - 1.0) < 1e-12 and abs(x[1] - 2.0) < 1e-12)
    check("singular is None", H._solve([[1.0, 1.0], [1.0, 1.0]],
                                       [1.0, 1.0]) is None)


def test_forecast():
    H.RV["mode"] = "park"
    s = H.har_daily_sigma(bars(260, 0.02, 0.3), 5)
    want = math.sqrt(math.log(1.01 / 0.99) ** 2 / (4 * math.log(2)))
    check("near the constant-range sigma", s is not None
          and 0.6 * want < s < 1.6 * want, (s, want))
    check("under MIN_OBS is None", H.har_daily_sigma(bars(60), 5) is None)


def test_score_rows():
    r = {"ticker": "A", "as_of": "d", "horizon": "week", "real": 1.0,
         "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02,
         "sigma_har": 0.03}
    fz = {"k": {"day": 1.2, "week": 1.4, "month": 1.2}}
    p = H.score_rows([r], fz)[0]
    check("scored", p["in_ch"] and p["is_ch"] > 0)
    r2 = dict(r, sigma_har=None)
    check("no sigma excluded", H.score_rows([r2], fz) == [])


def test_frozen_file():
    path = os.path.join(ROOT, "benchmarks", "frozen_log_har_r6.json")
    if os.path.exists(path):
        fz = json.load(open(path))["frozen"]
        check("frozen k keys", set(fz["k"]) == set(H.HORIZONS))
        check("fit cells <= 47", fz["fit_cells"][1] <= 47, fz["fit_cells"])


def test_refusal():
    rc = H.main(["score", "--frozen", "x", "--captures", "/nonexistent",
                 "--min-cell", "73"])
    check("refuses seen cells", rc == 2)


def test_unnumbered_and_json():
    import contextlib
    import io
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cap = os.path.join(d, "2025-11-14", "TST")
        os.makedirs(os.path.join(cap, "digest"))
        for fn in ("manifest.json", "realised.json"):
            open(os.path.join(cap, fn), "w").write("{}")
        open(os.path.join(cap, "digest", "ensemble.json"), "w").write("{}")
        out = os.path.join(d, "o.json")
        buf = io.StringIO()
        check("unnumbered capture is findable by find_captures",
              H.A.find_captures([d], 48) != [])
        with contextlib.redirect_stdout(buf):
            rc = H.main(["score", "--captures", d, "--min-cell", "48",
                         "--descriptive", "--reps", "50", "--json", out], "--frozen", os.path.join(ROOT, "benchmarks", "frozen_log_har_r6.json"))
        data = json.load(open(out))
        check("descriptive run exits 0", rc == 0)
        check("unnumbered capture dropped from scoring",
              all(data["results"][h]["n"] == 0 for h in ("day", "week", "month")))
        check("descriptive json carries no verdict",
              "verdict" not in data and data["descriptive"] is True)
        with contextlib.redirect_stdout(buf):
            H.main(["score", "--captures", d, "--reps", "50",
                    "--json", out], "--frozen", os.path.join(ROOT, "benchmarks", "frozen_log_har_r6.json"))
        check("clean json carries a verdict",
              "verdict" in json.load(open(out)))


def main():
    for fn in (test_constants, test_rv, test_solve, test_forecast,
               test_score_rows, test_frozen_file, test_refusal):
        fn()
    print("test_log_har: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
