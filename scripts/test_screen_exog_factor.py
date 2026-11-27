#!/usr/bin/env python3
"""Tests for benchmarks/screen_exog_factor.py (INS-IMPROVE-001 round 26,
proposal B). Standalone, stdlib only, synthetic fixed inputs, assertions
through the screen's functions and CLI output. __main__ guard
deliberate (#753 class)."""
import contextlib
import datetime as dt
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
    "exg", os.path.join(ROOT, "benchmarks", "screen_exog_factor.py"))
X = importlib.util.module_from_spec(spec)
sys.modules["exg"] = X
spec.loader.exec_module(X)
import test_screen_market_factor as TM  # noqa: E402

TM.NB = 480


def fbars(seed):
    d, out, c = dt.date(2021, 9, 1), [], 50.0
    for k in range(900):
        amp = 0.004 + 0.01 * (1 + math.sin(k / 40.0 + seed))
        c *= math.exp(amp * math.sin(k * 1.3 + seed) + 0.0002)
        out.append((d.isoformat(), c))
        d += dt.timedelta(days=1)
    return out


def test_constants():
    check("family 18, three factors", X.FAMILY_SIZE == 18
          and list(X.FACTORS) == ["EEM", "BZ=F", "GC=F"])
    check("v2 pinned", X.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("ewma window 250", X.EW_WINDOW == 250)


def test_lag_and_pit():
    bars = fbars(0.0)
    fd, fv = X.factor_returns(bars)
    d = fd[100]
    check("a factor return dated on d is NOT used for d",
          X.lagged(fd, fv, d) == fv[99])
    check("strictly earlier date uses the return before it",
          X.lagged(fd, fv, fd[101]) == fv[100])
    check("nothing before the first return", X.lagged(fd, fv, fd[0])
          is None)
    want = X.R._ewma(fv[0:100])
    check("mv uses returns dated before d only (100 available)",
          abs(X.mv_before(fd, fv, d) - want) < 1e-15)
    bad = [(b[0], b[1]) for b in bars[:102]] + [
        (b[0], 1e6 * (k + 1)) for k, b in enumerate(bars[102:])]
    fd2, fv2 = X.factor_returns(bad)
    check("later bars never change the volatility at d",
          X.mv_before(fd2, fv2, d) == X.mv_before(fd, fv, d)
          and X.lagged(fd2, fv2, d) == X.lagged(fd, fv, d))
    long_d = fd[500]
    e = 500
    check("window capped at the last 250 returns", abs(
        X.mv_before(fd, fv, long_d) - X.R._ewma(fv[e - 250:e])) < 1e-15)


def test_identity_and_pairs():
    by_t = TM.series()
    fb = {"EEM": fbars(0.0), "BZ=F": fbars(1.0), "GC=F": fbars(2.0)}
    pairs = X.screen_pairs(by_t, fb, regime="post")
    check("pairs for each factor", all(len(pairs[k]) > 0 for k in fb))
    check("factors give different bands", any(
        a["is_ch"] != b["is_ch"] for a, b in zip(pairs["EEM"],
                                                 pairs["BZ=F"])))
    # identity: mv = stdev of the aligned factor reproduces s60
    r = [0.01 * math.sin(k) for k in range(60)]
    m = [0.02 * math.cos(k * 0.7) for k in range(60)]
    mv = X.R._sd(m)
    s = X.MF.sigma_from(r, m, mv)
    check("mv = stdev(m) reproduces stdev(r)",
          abs(s - X.R._sd(r)) < 1e-12)
    # independent recomputation of one pair's band for EEM
    t = "T00_CA"
    bars = by_t[t]
    fd, fv = X.factor_returns(fb["EEM"])
    rets = X.MF.log_returns(bars)
    got = {}
    for p in pairs["EEM"]:
        if p["ticker"] == t and p["horizon"] == "day":
            got[p["as_of"]] = p
    check("T00 day pairs exist", len(got) > 3)
    as_of = sorted(got)[3]
    i = [k for k in range(len(bars)) if bars[k][0] == as_of][0] + 1
    dts = [bars[k][0] for k in range(i - 60, i)]
    r60 = [rets[d] for d in dts]
    m60 = [X.lagged(fd, fv, d) for d in dts]
    sig = X.MF.sigma_from(r60, m60, X.mv_before(fd, fv, as_of))
    real = (bars[i + 0][1] / bars[i - 1][1] - 1) * 100
    half = X.R.half_pct(sig, "day", X.ens_mod.V2_BAND_K["day"])
    check("band recomputed independently matches in_ch",
          got[as_of]["in_ch"] == (abs(real) <= half))
    check("is_ch recomputed matches", abs(
        got[as_of]["is_ch"] - X.bs.winkler_is(real, -half, half)) < 1e-9)


def test_main():
    by_t = TM.series()
    with tempfile.TemporaryDirectory() as d:
        hd, fdir = os.path.join(d, "h"), os.path.join(d, "f")
        os.makedirs(hd)
        os.makedirs(fdir)
        for t, bars in by_t.items():
            with open(os.path.join(hd, t + ".csv"), "w") as f:
                f.write("date,high,low,close,volume,adjclose\n")
                for dd, c in bars:
                    f.write("%s,%.4f,%.4f,%.4f,1,%.4f\n"
                            % (dd, c, c, c, c))
        for k, (name, seed) in enumerate(zip(
                X.FACTORS.values(), (0.0, 1.0, 2.0))):
            with open(os.path.join(fdir, name), "w") as f:
                f.write("date,close\n")
                for dd, c in fbars(seed):
                    f.write("%s,%.6f\n" % (dd, c))
        out = io.StringIO()
        js = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(out):
            code = X.main(["--history", hd, "--factors", fdir,
                           "--regime", "post", "--reps", "30",
                           "--json", js])
        res = json.load(open(js))
    txt = out.getvalue()
    check("exit 0, descriptive json", code == 0
          and res["descriptive"] is True)
    check("no verdict word or key", not any(
        w in (txt + json.dumps(res)).lower()
        for w in ("verdict", "keep", "reject", "adopt", "pass")))
    check("family 18 fixed, 9 readings for one regime",
          res["holm"]["family_size"] == 18
          and len(res["holm"]["readings"]) == 9)
    check("holm adjusted p never below raw", all(
        r["holm_adj_p"] is None or r["holm_adj_p"] >= r["p"]
        for r in res["holm"]["readings"]))
    check("factor bar counts reported", "EEM 849" in txt, txt[-200:])


def main():
    for fn in (test_constants, test_lag_and_pit, test_identity_and_pairs,
               test_main):
        fn()
    print("test_screen_exog_factor: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
