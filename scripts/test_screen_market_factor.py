#!/usr/bin/env python3
"""Tests for benchmarks/screen_market_factor.py (INS-IMPROVE-001 round
24 item 3). Standalone, stdlib only, fixed synthetic inputs, assertions
through the screen's own functions and CLI output. __main__ guard
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
    "smf", os.path.join(ROOT, "benchmarks", "screen_market_factor.py"))
M = importlib.util.module_from_spec(spec)
sys.modules["smf"] = M
spec.loader.exec_module(M)

NT, NB = 12, 260


def dates():
    d0, out, d = dt.date(2022, 1, 3), [], None
    d = d0
    while len(out) < NB:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def ret(t, k):
    """Deterministic return series: a common factor plus an own term."""
    common = 0.010 * math.sin(k * 0.7) + 0.004 * math.cos(k * 0.31)
    own = 0.006 * math.sin(k * (1.3 + 0.17 * t) + t)
    return common * (0.6 + 0.1 * t) + own


def series():
    ds, by_t = dates(), {}
    for t in range(NT):
        c, bars = 100.0, []
        for k, d in enumerate(ds):
            c *= math.exp(ret(t, k))
            bars.append((d, c))
        by_t["T%02d_CA" % t] = bars
    return by_t


def test_constants():
    check("v2 pinned", M.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("family 18", M.FAMILY_SIZE == 18 and len(M.MODELS) == 3)
    check("screen end", M.SCREEN_END == "2023-12-28")
    check("min names 10", M.MIN_NAMES == 10)


def test_sigma_identity_and_decomposition():
    r = [0.01, -0.02, 0.015, 0.0, -0.01, 0.02, -0.005, 0.012]
    m = [0.004, -0.01, 0.006, 0.001, -0.004, 0.008, -0.002, 0.005]
    s = M.sigma_from(r, m, M.R._sd(m))
    check("mv = stdev(m) reproduces stdev(r)",
          abs(s - M.R._sd(r)) < 1e-12, "%r %r" % (s, M.R._sd(r)))
    # doubling the market stdev must raise sigma by the beta term only
    s2 = M.sigma_from(r, m, 2 * M.R._sd(m))
    vm = M._cov(m, m)
    beta = M._cov(r, m) / vm
    want = math.sqrt(max(M._cov(r, r) - beta ** 2 * vm, 0)
                     + beta ** 2 * 4 * vm)
    check("market vol enters only through beta", abs(s2 - want) < 1e-12)
    check("flat factor is undefined", M.sigma_from(r, [0.0] * 8, 0.1)
          is None)


def test_leave_one_out_factor():
    rets = {"A": {"d1": 0.10, "d2": 0.20}, "B": {"d1": 0.0, "d2": 0.0}}
    for i in range(10):
        rets["X%d" % i] = {"d1": 0.01, "d2": 0.02}
    tot = M.market_sums(rets)
    fd, fv = M.factor_ex(tot, rets["A"])
    check("A's own return is excluded", abs(fv[0] - 0.10 / 11) < 1e-12
          and fd == ["d1", "d2"], str(fv))
    rets2 = {k: v for k, v in rets.items() if not k.startswith("X")}
    rets2.update({"X%d" % i: {"d1": 0.01} for i in range(8)})
    fd2, _ = M.factor_ex(M.market_sums(rets2), rets2["A"])
    check("a date needs >= 10 other names", fd2 == [], str(fd2))


def test_point_in_time():
    by_t = series()
    rets = {t: M.log_returns(b) for t, b in by_t.items()}
    tot = M.market_sums(rets)
    t = "T00_CA"
    fd, fv = M.factor_ex(tot, rets[t])
    k = 150
    cut = fd[k]
    r60 = [rets[t][d] for d in fd[k - 59:k + 1]]
    m60 = fv[k - 59:k + 1]
    base = M.model_sigmas(r60, m60, fd, fv, cut)
    # corrupt every factor value after the cutoff: nothing may move
    fv2 = fv[:k + 1] + [9.0] * (len(fv) - k - 1)
    after = M.model_sigmas(r60, m60, fd, fv2, cut)
    check("later factor values never enter", base == after, "%s %s"
          % (base, after))
    # a change on or before the cutoff does move the market-vol models
    fv3 = list(fv)
    fv3[k] = 0.5
    moved = M.model_sigmas(r60, m60, fd, fv3, cut)
    check("a value at the cutoff does enter",
          moved["mkt20"] != base["mkt20"]
          and moved["mktew"] != base["mktew"])
    check("s60 does not depend on the factor", moved["s60"] == base["s60"])


def test_screen_pairs_shape():
    by_t = series()
    pairs = M.screen_pairs(by_t, regime="post")
    check("every model produces pairs",
          all(len(pairs[m]) > 0 for m in M.MODELS))
    p = pairs["mkt20"][0]
    check("pair fields and post regime", p["regime"] == "post"
          and p["horizon"] in M.HORIZONS and p["ticker"].startswith("T"))
    check("no pre-regime pairs in a post-only series",
          len(M.screen_pairs(by_t, regime="pre")["mkt20"]) == 0)
    # the bar/lookback rule: a pair needs 60 sessions of returns
    short = {t: b[:100] for t, b in by_t.items()}
    check("short history makes no pairs", all(
        len(v) == 0 for v in M.screen_pairs(short).values()))


def test_load_and_main():
    by_t = series()
    with tempfile.TemporaryDirectory() as d:
        for t, bars in by_t.items():
            with open(os.path.join(d, t + ".csv"), "w") as f:
                f.write("date,high,low,close,volume,adjclose\n")
                for dd, c in bars:
                    f.write("%s,%.4f,%.4f,%.4f,1,%.4f\n"
                            % (dd, c, c, c, c * 0.5))
        with open(os.path.join(d, "NVDA.csv"), "w") as f:
            f.write("date,high,low,close,volume,adjclose\n"
                    "2022-01-03,1,1,1,1,1\n")
        loaded = M.load(d)
        check("NVDA excluded, 12 .CA names loaded",
              "NVDA" not in loaded and len(loaded) == NT, sorted(loaded))
        check("close column used, not adjclose",
              abs(loaded["T00_CA"][0][1] - by_t["T00_CA"][0][1]) < 1e-3)
        out = io.StringIO()
        js = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(out):
            code = M.main(["--history", d, "--regime", "post", "--reps",
                           "30", "--json", js])
        res = json.load(open(js))
    txt = out.getvalue()
    check("exit 0, descriptive json", code == 0
          and res["descriptive"] is True)
    check("no verdict word or key", not any(
        w in (txt + json.dumps(res)).lower()
        for w in ("verdict", "keep", "reject", "adopt", "pass")))
    check("family size fixed at 18 for a one-regime run",
          res["holm"]["family_size"] == 18
          and len(res["holm"]["readings"]) == 9)
    check("holm adjusted p is never below raw p", all(
        r["holm_adj_p"] is None or r["holm_adj_p"] >= r["p"]
        for r in res["holm"]["readings"]))


def main():
    for fn in (test_constants, test_sigma_identity_and_decomposition,
               test_leave_one_out_factor, test_point_in_time,
               test_screen_pairs_shape, test_load_and_main):
        fn()
    print("test_screen_market_factor: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
