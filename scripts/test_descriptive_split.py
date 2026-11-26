#!/usr/bin/env python3
"""Fixed synthetic checks for benchmarks/descriptive_split_r6.py."""
import importlib.util
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


def load():
    sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    spec = importlib.util.spec_from_file_location(
        "descriptive_split_r6",
        os.path.join(ROOT, "benchmarks", "descriptive_split_r6.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S = load()


def bar(d, c, h=None, l=None, v=100.0):
    return (d, c, h if h is not None else c, l if l is not None else c,
            c, v)


def test_counts():
    bars = [bar("d0", 100.0), bar("d1", 109.6),
            bar("d2", 109.6, h=110.0, l=109.6),
            bar("d3", 131.5, h=132.0, l=109.6)]
    c = S.limit_counts(bars)
    check("bars", c["bars"] == 4)
    check("zero-range bars (H == L)", c["zero_range"] == 2, c)
    check("10% close hits: +9.6% and +20%", c["near_10_close"] == 2, c)
    check("20% close hit: +20% only, 9.6% is not", c["near_20_close"] == 1, c)
    check("intraday 20% from prev close 109.6 to high 132",
          c["near_20_intraday"] == 1, c)
    check("close counts from price.csv",
          S.close_counts([100.0, 109.6, 131.5])["near_10_close"] == 2)


def test_features():
    bars = [bar("d%02d" % i, 100.0, v=10.0) for i in range(30)]
    f = S.capture_features(bars)
    check("flat bars are all zero-range", f["zero_range_share"] == 1.0)
    check("turnover is median of volume x close", f["turnover"] == 1000.0)
    check("no near-limit day", f["near_limit"] is False)
    check("too short history gives None",
          S.capture_features(bars[:10]) is None)


def prow(h, inside, t="A", a="2026-01-02"):
    return {"pair": {"horizon": h, "ticker": t, "as_of": a,
                     "is_naive": 2.0, "is_v2": 1.0, "in_v2": inside},
            "feat": {"zero_range_share": 0.0, "turnover": 5.0,
                     "near_limit": False}}


def test_split_counts_only():
    recs = [prow("day", True, t="T%d" % (i % 6)) for i in range(29)]
    res = S.split(recs)
    b = res["all rows"]["day"]
    check("29 rows: counts only, no metrics",
          b["n"] == 29 and "coverage" not in b, b)
    recs.append(prow("day", False))
    b = S.split(recs)["all rows"]["day"]
    check("30 rows: metrics appear", b["n"] == 30
          and abs(b["coverage"] - 29 / 30) < 1e-9
          and abs(b["range_skill"] - 0.5) < 1e-9, b)
    check("zero-range buckets partition the rows",
          S.split(recs)["zero-range share = 0"]["day"]["n"] == 30
          and S.split(recs)["zero-range share > 0"]["day"]["n"] == 0)


def test_no_verdict_and_json():
    import contextlib
    import io
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = S.main(["--captures", d, "--json", out])
        data = json.load(open(out))
        check("runs on an empty dir", rc == 0)
        check("descriptive flag and no verdict key",
              data["descriptive"] is True and "verdict" not in data)


def main():
    for fn in (test_counts, test_features, test_split_counts_only,
               test_no_verdict_and_json):
        fn()
    print("test_descriptive_split: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
