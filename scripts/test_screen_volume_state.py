#!/usr/bin/env python3
"""Tests for benchmarks/screen_volume_state.py (INS-IMPROVE-001 round 30,
proposal B). Standalone, stdlib only, SYNTHETIC prices and volumes only,
assertions through the screen's functions and CLI output. __main__ guard
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
    "vs", os.path.join(ROOT, "benchmarks", "screen_volume_state.py"))
V = importlib.util.module_from_spec(spec)
sys.modules["vs"] = V
spec.loader.exec_module(V)
import test_screen_market_factor as TM  # noqa: E402

TM.NB = 480
HOL = 37          # every 37th bar is a market-wide zero-volume day


def vol(t, k):
    if k % HOL == HOL - 1:
        return 0.0
    return 1000.0 + 40.0 * ((k * 7 + t * 3) % 13) + 5.0 * (k // 50)


def data():
    by_t = TM.series()
    vols = {t: [vol(n, k) for k in range(len(b))]
            for n, (t, b) in enumerate(sorted(by_t.items()))}
    dates = [d for d, _ in by_t["T00_CA"]]
    zero = {dates[k] for k in range(len(dates)) if k % HOL == HOL - 1}
    return by_t, vols, zero, dates


def test_constants():
    check("betas fixed, family 12", V.BETAS == (0.10, 0.20)
          and V.FAMILY_SIZE == 12)
    check("v2 pinned", V.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("eligibility 120 bars at 90%, window 20",
          (V.ELIG_BARS, V.ELIG_SHARE, V.VOL_WINDOW) == (120, 0.9, 20))
    check("zero-day rule 10 names, 90%",
          (V.ZERO_DAY_MIN_NAMES, V.ZERO_DAY_SHARE) == (10, 0.9))


def test_zero_days():
    ten = {"a": [0.0] * 10, "b": [0.0] * 9 + [5.0],
           "c": [0.0] * 8 + [5.0, 5.0], "d": [0.0] * 9,
           "e": [0.0] * 40 + [1.0] * 2}
    got = V.zero_days(ten)
    check("90% zero with >= 10 names is market-wide",
          "a" in got and "b" in got and "e" in got, got)
    check("80% zero is not", "c" not in got, got)
    check("fewer than 10 names is never market-wide", "d" not in got, got)


def test_volume_state_rules():
    vols = [1000.0] * 300
    dates = ["d%03d" % k for k in range(300)]
    ok, x = V.volume_state(vols, dates, set(), 200)
    check("flat volume is eligible, x = log1p(mean)",
          ok and abs(x - math.log1p(1000.0)) < 1e-12, (ok, x))
    check("fewer than 120 prior bars is not eligible",
          V.volume_state(vols, dates, set(), 100)[0] is False)
    # as_of bar is i-1; window is bars 0..i-2. Volume spike ON bar i-1
    # and after must not move anything.
    v2 = list(vols)
    v2[199] = 9e9
    v2[200] = 9e9
    check("bars on or after as_of change nothing",
          V.volume_state(v2, dates, set(), 200) == (ok, x))
    v3 = list(vols)
    v3[198] = 21000.0       # last usable bar, inside the 20-bar window
    x3 = V.volume_state(v3, dates, set(), 200)[1]
    check("the last bar before as_of is in the mean",
          abs(x3 - math.log1p((19 * 1000.0 + 21000.0) / 20)) < 1e-12, x3)
    # holiday rule: excluded from mean, kept in eligibility count
    v4 = list(vols)
    for k in (190, 191):
        v4[k] = 0.0
    zero = {dates[190], dates[191]}
    ok4, x4 = V.volume_state(v4, dates, zero, 200)
    check("market-wide zero days leave the mean at 1000 (divisor 18)",
          ok4 and abs(x4 - math.log1p(1000.0)) < 1e-12, (ok4, x4))
    ok5, x5 = V.volume_state(v4, dates, set(), 200)
    check("the same zeros, not market-wide, pull the mean down",
          ok5 and abs(x5 - math.log1p(18 * 1000.0 / 20)) < 1e-12, x5)
    # eligibility keeps the market-wide zero bars in the count: 13 zero
    # bars of 120 is 89.2% non-zero -> not eligible even though flagged
    v6 = list(vols)
    zs = set()
    for k in range(80, 93):
        v6[k] = 0.0
        zs.add(dates[k])
    check("market-wide zero bars still count against eligibility",
          V.volume_state(v6, dates, zs, 200)[0] is False)
    v7 = list(vols)
    zs = set()
    for k in range(80, 92):
        v7[k] = 0.0
        zs.add(dates[k])
    check("12 zero bars of 120 is exactly 90%, eligible",
          V.volume_state(v7, dates, zs, 200)[0] is True)
    allz = {dates[k] for k in range(179, 199)}
    v8 = list(vols)
    for k in range(179, 199):
        v8[k] = 0.0
    check("a window made only of market-wide zero days skips the cutoff",
          V.volume_state(v8, dates, allz, 200) == (False, None))


def test_screen_pairs_semantics():
    by_t, vols, zero, dates = data()
    pairs = V.screen_pairs(by_t, vols, zero, regime="post")
    p0 = pairs[0.10]
    check("pairs for both betas", len(p0) > 0
          and len(pairs[0.20]) == len(p0))
    zs = [p["z_vol"] for p in p0]
    check("z non-zero once 8 priors exist, zero before",
          any(abs(z) > 0 for z in zs) and any(z == 0 for z in zs))
    saved = V.BETAS
    V.BETAS = (0.0,)
    try:
        z0 = V.screen_pairs(by_t, vols, zero, regime="post")[0.0]
    finally:
        V.BETAS = saved
    check("beta 0 reproduces frozen v2 exactly", len(z0) > 0 and all(
        p["is_ch"] == p["is_v2"] and p["in_ch"] == p["in_v2"]
        for p in z0))
    wide = [p for p in p0 if p["z_vol"] > 0.5]
    low = [p for p in p0 if p["z_vol"] < -0.5]
    check("z>0 never narrows, z<0 never widens",
          len(wide) > 0 and len(low) > 0
          and all(p["in_ch"] >= p["in_v2"] for p in wide)
          and all(p["in_ch"] <= p["in_v2"] for p in low))
    check("bands differ from v2 where z != 0",
          any(p["is_ch"] != p["is_v2"] for p in wide)
          and any(p["is_ch"] != p["is_v2"] for p in low))
    # z of the 12th day cutoff recomputed independently from the series
    bars = by_t["T00_CA"]
    idx = [i for i in range(V.SB.MIN_HIST, len(bars) - V.R.SESSIONS["day"]
                            + 1, V.SB.STEP)]
    xs = []
    for i in idx:
        if i - 1 - V.ELIG_BARS < 0:     # first cutoff: under 120 bars
            continue
        kept = [vols["T00_CA"][k] for k in range(i - 1 - 20, i - 1)
                if dates[k] not in zero]
        xs.append(math.log1p(sum(kept) / len(kept)))
    want = V.N.zscore(xs[11], xs[:11])   # idx[0] is not eligible
    got = [p["z_vol"] for p in p0 if p["ticker"] == "T00_CA"
           and p["horizon"] == "day" and p["as_of"] == bars[idx[12] - 1][0]]
    check("z uses only earlier eligible cutoffs, holiday days excluded",
          len(got) == 1 and abs(got[0] - want) < 1e-12 and want != 0,
          (got, want))
    # an ineligible ticker contributes nothing: zero out one ticker
    v_dead = {t: list(v) for t, v in vols.items()}
    v_dead["T01_CA"] = [0.0] * len(v_dead["T01_CA"])
    pd = V.screen_pairs(by_t, v_dead, zero, regime="post")[0.10]
    check("a ticker below 90% non-zero volume is dropped",
          not any(p["ticker"] == "T01_CA" for p in pd)
          and any(p["ticker"] == "T00_CA" for p in pd))


def test_main():
    by_t, vols, zero, dates = data()
    with tempfile.TemporaryDirectory() as d:
        for t, bars in by_t.items():
            with open(os.path.join(d, t + ".csv"), "w") as f:
                f.write("date,high,low,close,volume,adjclose\n")
                for k, (dd, c) in enumerate(bars):
                    f.write("%s,%.4f,%.4f,%.4f,%.1f,%.4f\n"
                            % (dd, c, c, c, vols[t][k], c))
        loaded = V.load(d)
        out = io.StringIO()
        js = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(out):
            code = V.main(["--history", d, "--regime", "post",
                           "--reps", "30", "--json", js])
        res = json.load(open(js))
    check("loader finds the market-wide zero days", loaded[2] == zero
          and len(zero) > 5, (len(loaded[2]), len(zero)))
    txt = out.getvalue()
    check("exit 0, descriptive json", code == 0
          and res["descriptive"] is True)
    check("no verdict word or key", not any(
        w in txt.lower() for w in ("verdict", "keep", "reject", "adopt",
                                   "pass"))
          and not any("verdict" in k for k in res))
    check("family 12 fixed, 6 rows for one regime, delta beside p",
          res["holm"]["family_size"] == 12
          and len(res["holm"]["readings"]) == 6
          and all("delta" in r and "p" in r and "delta_p" in r
                  for r in res["holm"]["readings"]))
    check("zero-day rule recorded in the json",
          res["zero_days"]["count"] == len(zero)
          and res["zero_days"]["min_names"] == 10)
    check("report prints delta vs v2 and the zero-day count",
          "delta vs v2" in txt and "market-wide zero-volume days: %d"
          % len(zero) in txt, txt[-300:])


def main():
    for fn in (test_constants, test_zero_days, test_volume_state_rules,
               test_screen_pairs_semantics, test_main):
        fn()
    print("test_screen_volume_state: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
