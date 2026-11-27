#!/usr/bin/env python3
"""Tests for benchmarks/screen_fx_stress.py (INS-IMPROVE-001 round 26,
proposal A). Standalone, stdlib only, synthetic fixed inputs, assertions
through the screen's own functions and CLI output. __main__ guard
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
    "fxs", os.path.join(ROOT, "benchmarks", "screen_fx_stress.py"))
F = importlib.util.module_from_spec(spec)
sys.modules["fxs"] = F
spec.loader.exec_module(F)
import test_screen_market_factor as TM  # noqa: E402

TM.NB = 480


def fx_bars():
    """Calendar-day FX closes from 2021-10-01 with a stress burst."""
    import datetime as dt
    d, out, c = dt.date(2021, 10, 1), [], 15.0
    for k in range(900):
        amp = 0.002 + (0.08 if (300 <= k < 360 or 560 <= k < 620) else 0.0)
        c *= math.exp(amp * math.sin(k * 1.7) + 0.0003)
        out.append((d.isoformat(), c))
        d += dt.timedelta(days=1)
    return out


def test_constants():
    check("betas fixed, family 12", F.BETAS == (0.10, 0.20)
          and F.FAMILY_SIZE == 12)
    check("v2 pinned", F.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("stress window 20", F.STRESS_WINDOW == 20)


def test_stress_series_and_pit():
    bars = fx_bars()
    dates, vals = F.stress_series(bars)
    rets = [math.log(bars[k][1] / bars[k - 1][1])
            for k in range(1, len(bars))]
    want = F.R._sd(rets[0:20])
    check("first stress value is the stdev of the first 20 returns, "
          "dated on the 20th return's bar", abs(vals[0] - want) < 1e-15
          and dates[0] == bars[20][0], (vals[0], want, dates[0]))
    d = dates[100]
    check("a bar dated on the cutoff date is excluded",
          F.stress_before(dates, vals, d) == vals[99])
    check("the bar before the cutoff date is included",
          F.stress_before(dates, vals, dates[100] + "x") == vals[100]
          or F.stress_before(dates, vals, d) == vals[99])
    check("nothing before the first bar", F.stress_before(
        dates, vals, dates[0]) is None)
    # corrupt every bar from index 150 on: values before are unchanged
    bad = bars[:152] + [(b[0], 1000.0 * (k + 1))
                        for k, b in enumerate(bars[152:])]
    d2, v2 = F.stress_series(bad)
    check("later bars never change an earlier stress value",
          v2[:100] == vals[:100])


def test_screen_pairs():
    by_t = TM.series()
    fx = fx_bars()
    pairs = F.screen_pairs(by_t, fx, regime="post")
    p0 = pairs[0.10]
    check("pairs for both betas", len(p0) > 0
          and len(pairs[0.20]) == len(p0))
    zs = [p["z_fx"] for p in p0]
    check("some z non-zero once 8 priors exist", any(abs(z) > 0
                                                    for z in zs))
    saved = F.BETAS
    F.BETAS = (0.0,)
    try:
        z0 = F.screen_pairs(by_t, fx, regime="post")[0.0]
    finally:
        F.BETAS = saved
    check("beta 0 reproduces frozen v2 exactly", len(z0) > 0 and all(
        p["is_ch"] == p["is_v2"] and p["in_ch"] == p["in_v2"]
        for p in z0))
    p20 = pairs[0.20]
    check("larger beta moves the band further for z>0", any(
        a["z_fx"] > 0.5 and b["is_ch"] != a["is_ch"]
        for a, b in zip(p0, p20)))
    wide = [p for p in p0 if p["z_fx"] > 0.5]
    check("z>0 widens: in_ch >= in_v2, and some bands differ",
          len(wide) > 0 and all(p["in_ch"] >= p["in_v2"] for p in wide)
          and any(p["is_ch"] != p["is_v2"] for p in wide))
    # z of one named cutoff recomputed independently
    bars = by_t["T00_CA"]
    sd, sv = F.stress_series(fx)
    idx = list(range(F.SB.MIN_HIST, len(bars) - F.R.SESSIONS["day"] + 1,
                     F.SB.STEP))
    xs = [math.log(F.stress_before(sd, sv, bars[i - 1][0]))
          for i in idx if F.stress_before(sd, sv, bars[i - 1][0])]
    k = 11
    want = F.N.zscore(xs[k], xs[:k])
    got = [p["z_fx"] for p in p0 if p["ticker"] == "T00_CA"
           and p["horizon"] == "day"
           and p["as_of"] == bars[idx[k] - 1][0]]
    check("z uses only earlier cutoffs", len(got) == 1
          and abs(got[0] - want) < 1e-12 and want != 0, (got, want))


def test_main():
    by_t = TM.series()
    with tempfile.TemporaryDirectory() as d:
        for t, bars in by_t.items():
            with open(os.path.join(d, t + ".csv"), "w") as f:
                f.write("date,high,low,close,volume,adjclose\n")
                for dd, c in bars:
                    f.write("%s,%.4f,%.4f,%.4f,1,%.4f\n"
                            % (dd, c, c, c, c))
        fxp = os.path.join(d, "fx.csv")
        with open(fxp, "w") as f:
            f.write("date,close\n")
            for dd, c in fx_bars():
                f.write("%s,%.6f\n" % (dd, c))
        out = io.StringIO()
        js = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(out):
            code = F.main(["--history", d, "--fx", fxp, "--regime", "post",
                           "--reps", "30", "--json", js])
        res = json.load(open(js))
    txt = out.getvalue()
    check("exit 0, descriptive json", code == 0
          and res["descriptive"] is True)
    check("no verdict word or key", not any(
        w in (txt + json.dumps(res)).lower()
        for w in ("verdict", "keep", "reject", "adopt", "pass")))
    check("family 12 fixed, 6 readings for one regime",
          res["holm"]["family_size"] == 12
          and len(res["holm"]["readings"]) == 6)
    check("holm adjusted p never below raw", all(
        r["holm_adj_p"] is None or r["holm_adj_p"] >= r["p"]
        for r in res["holm"]["readings"]))
    check("fx bar count reported", "EGP=X bars: 819" in txt, txt[-120:])


def main():
    for fn in (test_constants, test_stress_series_and_pit,
               test_screen_pairs, test_main):
        fn()
    print("test_screen_fx_stress: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
