#!/usr/bin/env python3
"""Tests for benchmarks/score_tsfm_control.py (INS-IMPROVE-006 E).
Standalone, stdlib only.
"""
import importlib.util
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
    "tsfm", os.path.join(ROOT, "benchmarks", "score_tsfm_control.py"))
T = importlib.util.module_from_spec(spec)
sys.modules["tsfm"] = T
spec.loader.exec_module(T)

GOOD = {"model": "chronos-2", "base_date": "2025-11-14",
        "context_sessions": 750,
        "horizons": {"day": {"q10": -2.0, "q50": 0.1, "q90": 2.2},
                     "week": {"q10": -4.0, "q50": 0.2, "q90": 4.4},
                     "month": {"q10": -8.0, "q50": 0.3, "q90": 8.8}}}


def write(d, obj, model="chronos-2"):
    p = os.path.join(d, "collected", model)
    os.makedirs(p)
    with open(os.path.join(p, "quantiles.json"), "w") as f:
        json.dump(obj, f)


def test_constants():
    check("v2 pinned", T.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("clean cells", T.CLEAN_MIN_CELL == 91)


def test_load():
    with tempfile.TemporaryDirectory() as d:
        write(d, GOOD)
        check("loads", T.load_quantiles(d, "chronos-2") is not None)
        check("wrong model is None", T.load_quantiles(d, "timesfm") is None)
    with tempfile.TemporaryDirectory() as d:
        bad = json.loads(json.dumps(GOOD))
        bad["horizons"]["week"]["q90"] = -5.0
        write(d, bad)
        check("inverted quantiles rejected",
              T.load_quantiles(d, "chronos-2") is None)
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "collected", "chronos-2"))
        with open(os.path.join(d, "collected", "chronos-2",
                               "quantiles.json"), "w") as f:
            f.write("{not json")
        check("malformed is None", T.load_quantiles(d, "chronos-2") is None)


def test_band():
    check("half is (q90-q10)/2", abs(T.band_half(
        GOOD["horizons"]["day"]) - 2.1) < 1e-9)
    check("risk mult applied", abs(T.band_half(
        GOOD["horizons"]["day"], 2.0) - 4.2) < 1e-9)


def test_score_rows():
    r = {"ticker": "A", "as_of": "d", "horizon": "week", "real": 1.0,
         "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02,
         "tsfm_half": 4.0}
    p = T.score_rows([r])[0]
    check("scored", p["in_ch"])
    check("no band excluded", T.score_rows([dict(r, tsfm_half=None)]) == [])


def test_refusal():
    check("refuses seen cells", T.main(
        ["score", "--captures", "/nonexistent", "--min-cell", "73"]) == 2)


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
              T.A.find_captures([d], 48) != [])
        with contextlib.redirect_stdout(buf):
            rc = T.main(["score", "--captures", d, "--min-cell", "48",
                         "--descriptive", "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("descriptive run exits 0", rc == 0)
        check("unnumbered capture dropped from scoring",
              all(data["results"][h]["n"] == 0 for h in ("day", "week", "month")))
        check("descriptive json carries no verdict",
              "verdict" not in data and data["descriptive"] is True)
        with contextlib.redirect_stdout(buf):
            T.main(["score", "--captures", d, "--reps", "50",
                    "--json", out])
        check("clean json carries a verdict",
              "verdict" in json.load(open(out)))


def main():
    for fn in (test_constants, test_load, test_band, test_score_rows,
               test_refusal, test_unnumbered_and_json):
        fn()
    print("test_tsfm_control: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
