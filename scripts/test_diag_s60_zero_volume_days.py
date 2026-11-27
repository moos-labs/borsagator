#!/usr/bin/env python3
"""Tests for benchmarks/diag_s60_zero_volume_days.py (INS-IMPROVE-001
round 30, item 2). Standalone, stdlib only, SYNTHETIC data, assertions
through the script's functions and CLI output. __main__ guard
deliberate (#753 class)."""
import contextlib
import importlib.util
import io
import json
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
    "dz", os.path.join(ROOT, "benchmarks",
                       "diag_s60_zero_volume_days.py"))
Z = importlib.util.module_from_spec(spec)
sys.modules["dz"] = Z
spec.loader.exec_module(Z)
import test_screen_market_factor as TM  # noqa: E402

TM.NB = 480
HOL = 97


def test_zero_days_rule():
    d = {"a": [0.0] * 10, "b": [0.0] * 9 + [3.0], "c": [0.0] * 8 + [3.0] * 2,
         "d": [0.0] * 9}
    got = Z.zero_days(d)
    check("rule: >= 10 names and >= 90% zero", got == {"a", "b"}, got)


def test_s60_pair_exact():
    # 70 bars, closes built from known returns; zero days = 2 of them
    rs = [0.01 * ((k * 5) % 7 - 3) for k in range(70)]
    c, bars = 100.0, [("d00", 100.0)]
    for k, r in enumerate(rs, 1):
        c *= math.exp(r)
        bars.append(("d%02d" % k, c))
    rets = Z.MF.log_returns(bars)
    zero = {"d30", "d31"}
    i = 70                      # window = returns dated d10 .. d69
    w, wo = Z.s60_pair(bars, rets, zero, i)
    win = ["d%02d" % k for k in range(10, 70)]
    a = [rets[d] for d in win]
    b = [rets[d] for d in win if d not in zero]
    check("with = stdev of the 60 returns", abs(w - Z.R._sd(a)) < 1e-15)
    check("without drops exactly the zero-day returns",
          abs(wo - Z.R._sd(b)) < 1e-15 and wo != w, (wo, w))
    check("zero days outside the window change nothing",
          Z.s60_pair(bars, rets, {"d05"}, i) == (w, w))
    many = {"d%02d" % k for k in range(10, 45)}
    check("fewer than 30 kept returns gives without = None",
          Z.s60_pair(bars, rets, many, i)[1] is None)
    check("incomplete with-window gives (None, None)",
          Z.s60_pair(bars, rets, zero, 40) == (None, None))


def series_with_holidays():
    by_t = TM.series()
    dates = [d for d, _ in by_t["T00_CA"]]
    zero = {dates[k] for k in range(len(dates)) if k % HOL == HOL - 1}
    out = {}
    for t, bars in by_t.items():
        nb, prev = [], None
        for d, c in bars:
            if d in zero and prev is not None:
                c = prev            # carried close on the holiday
            nb.append((d, c))
            prev = c
        out[t] = nb
    return out, zero


def test_ratios_and_summary():
    by_t, zero = series_with_holidays()
    rows = Z.cutoff_ratios(by_t, zero)
    check("rows for all horizons (synthetic series is post-regime)", {
        (r["horizon"], r["regime"]) for r in rows} == {
        (h, "post") for h in Z.HORIZONS})
    aff = [r for r in rows if r["affected"] and r["ratio"] is not None]
    check("affected cutoffs exist and zero returns raise s60 when "
          "removed (ratio > 0)", len(aff) > 50
          and all(r["ratio"] > 0 for r in aff), len(aff))
    none = Z.cutoff_ratios(by_t, set())
    check("no zero days: every ratio is exactly 0",
          len(none) > 0 and all(r["ratio"] == 0.0 and not r["affected"]
                                for r in none))
    res = Z.summarize(rows)
    s = res[("day", "post")]
    sub = [r["ratio"] for r in rows if r["horizon"] == "day"
           and r["regime"] == "post" and r["ratio"] is not None]
    check("summary mean over all cutoffs recomputed independently",
          abs(s["mean_all"] - sum(sub) / len(sub)) < 1e-15
          and s["cutoffs"] >= len(sub), (s["mean_all"], len(sub)))
    check("affected mean >= all mean (unaffected add zeros)",
          s["mean_affected"] >= s["mean_all"] > 0)
    check("affected share between 0 and 1",
          0 < s["affected_share"] < 1, s["affected_share"])


def test_main():
    by_t, zero = series_with_holidays()
    with tempfile.TemporaryDirectory() as d:
        for t, bars in by_t.items():
            with open(os.path.join(d, t + ".csv"), "w") as f:
                f.write("date,high,low,close,volume,adjclose\n")
                for dd, c in bars:
                    v = 0.0 if dd in zero else 1000.0
                    f.write("%s,%.4f,%.4f,%.4f,%.1f,%.4f\n"
                            % (dd, c, c, c, v, c))
        out = io.StringIO()
        js = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(out):
            code = Z.main(["--history", d, "--json", js])
        res = json.load(open(js))
    txt = out.getvalue()
    check("exit 0, descriptive json, 6 readings", code == 0
          and res["descriptive"] is True and len(res["readings"]) == 6)
    check("zero days read from the volume column",
          res["zero_days"]["count"] == len(zero) and len(zero) > 3,
          (res["zero_days"], len(zero)))
    check("no verdict word or key", not any(
        w in txt.lower() for w in ("verdict", "keep", "reject", "adopt",
                                   "pass"))
          and not any("verdict" in k for k in res))
    check("report prints affected and all means",
          "affected (n=" in txt and "all: mean" in txt, txt[:300])


def main():
    for fn in (test_zero_days_rule, test_s60_pair_exact,
               test_ratios_and_summary, test_main):
        fn()
    print("test_diag_s60_zero_volume_days: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
