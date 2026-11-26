#!/usr/bin/env python3
"""Tests for benchmarks/screen_news_width.py (INS-IMPROVE-001 round 24
item 3, Route 1 harness). Standalone, stdlib only, SYNTHETIC news and
prices only, assertions through the harness's own functions and CLI
output. __main__ guard deliberate (#753 class)."""
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
    "snw", os.path.join(ROOT, "benchmarks", "screen_news_width.py"))
N = importlib.util.module_from_spec(spec)
sys.modules["snw"] = N
spec.loader.exec_module(N)
import test_screen_market_factor as TM  # noqa: E402  (series fixture)

TM.NB = 480   # enough pseudo-cutoffs for 8 earlier ones, ends 2023-10


def test_constants():
    check("betas fixed, family 12", N.BETAS == (0.10, 0.20)
          and N.FAMILY_SIZE == 12)
    check("v2 pinned", N.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("window 7 days, min prior 8", (N.WINDOW_DAYS, N.MIN_PRIOR)
          == (7, 8))


def test_point_in_time_window():
    st = sorted(["20240509235959", "20240510000000", "20240514235959",
                 "20240515000000", "20240515120000", "20240516000000"])
    # cutoff day 2024-05-15: window is [05-08 00:00, 05-15 00:00)
    check("counts strictly before 00:00 UTC of the cutoff day",
          N.window_count(st, "2024-05-15") == 3, N.window_count(st, "2024-05-15"))
    check("a record at 00:00:00 of the cutoff day is excluded",
          N.window_count(["20240515000000"], "2024-05-15") == 0)
    check("one second earlier is included",
          N.window_count(["20240514235959"], "2024-05-15") == 1)
    check("window start is inclusive, 8 days back is out",
          N.window_count(["20240508000000"], "2024-05-15") == 1
          and N.window_count(["20240507235959"], "2024-05-15") == 0)


def test_zscore_and_multiplier():
    check("fewer than 8 priors gives 0", N.zscore(5.0, [1.0] * 7) == 0.0)
    pri = [1.0, 2.0, 3.0, 4.0, 1.0, 2.0, 3.0, 4.0]
    sd = math.sqrt(1.25)
    check("z against earlier values only", abs(
        N.zscore(4.5, pri) - (4.5 - 2.5) / sd) < 1e-12)
    check("constant history gives 0", N.zscore(9.0, [2.0] * 8) == 0.0)
    check("beta 0 is exactly 1", N.multiplier(0.0, 2.7) == 1.0)
    check("always positive at the clip (beta 0.5, z -3)",
          N.multiplier(0.5, -3.0) > 0
          and abs(N.multiplier(0.5, -30.0) - math.exp(-1.5)) < 1e-12)
    check("above the clip is capped", abs(
        N.multiplier(0.2, 99.0) - math.exp(0.6)) < 1e-12)


def news_for(by_t):
    """Synthetic matches: a burst of records before some days."""
    out = {}
    for t, bars in by_t.items():
        key = N.ticker_key(t)
        ts = []
        for k, (d, _) in enumerate(bars):
            reps = 1 + (k % 11 == 0) * 6
            for j in range(reps):
                ts.append(d.replace("-", "") + "%02d0000" % (j % 24))
        out[key] = sorted(ts)
    return out


def test_screen_pairs_semantics():
    by_t = TM.series()
    news = news_for(by_t)
    pairs = N.screen_pairs(by_t, news, regime="post")
    p0 = pairs[0.10]
    check("pairs produced for both betas",
          len(p0) > 0 and len(pairs[0.20]) == len(p0))
    zs = [p["z_news"] for p in p0]
    check("some z are non-zero once 8 priors exist",
          any(abs(z) > 0 for z in zs) and any(z == 0 for z in zs))
    # beta 0 equals frozen v2 on every pair
    saved = N.BETAS
    N.BETAS = (0.0,)
    try:
        z0 = N.screen_pairs(by_t, news, regime="post")[0.0]
    finally:
        N.BETAS = saved
    check("beta 0 reproduces frozen v2 exactly", len(z0) > 0 and all(
        p["is_ch"] == p["is_v2"] and p["in_ch"] == p["in_v2"]
        for p in z0))
    # a positive z widens, negative narrows, monotone in beta
    wide = [p for p in p0 if p["z_news"] > 0.5]
    check("z>0 never narrows the band (in_ch >= in_v2)",
          all(p["in_ch"] >= p["in_v2"] for p in wide) and len(wide) > 0)
    low = [p for p in p0 if p["z_news"] < -0.5]
    check("z<0 never widens the band (in_ch <= in_v2)",
          all(p["in_ch"] <= p["in_v2"] for p in low))
    check("bands differ from v2 where z != 0 (both directions)",
          any(p["is_ch"] != p["is_v2"] for p in wide)
          and any(p["is_ch"] != p["is_v2"] for p in low),
          (len([p for p in wide if p["is_ch"] != p["is_v2"]]),
           len([p for p in low if p["is_ch"] != p["is_v2"]])))
    # z of the 12th day-horizon cutoff is computed from the 11 EARLIER
    # cutoffs only, recomputed here independently from the news
    bars = by_t["T00_CA"]
    idx = list(range(N.SB.MIN_HIST, len(bars) - N.R.SESSIONS["day"] + 1,
                     N.SB.STEP))
    xs = [math.log1p(N.window_count(news["T00.CA"], bars[i - 1][0]))
          for i in idx]
    want = N.zscore(xs[11], xs[:11])
    got = [p["z_news"] for p in p0 if p["ticker"] == "T00_CA"
           and p["horizon"] == "day" and p["as_of"] == bars[idx[11] - 1][0]]
    check("z uses only earlier cutoffs", len(got) == 1
          and abs(got[0] - want) < 1e-12 and want != 0, (got, want))
    # point in time: records on or after the cutoff day cannot move z
    k = 200
    d = by_t["T00_CA"][k][0]
    base = N.window_count(news["T00.CA"], d)
    news2 = dict(news)
    news2["T00.CA"] = sorted(news["T00.CA"] + [d.replace("-", "") + "000000"]
                             * 50)
    check("50 extra records stamped on the cutoff day change nothing",
          N.window_count(news2["T00.CA"], d) == base)


def test_matches_loader_and_main():
    by_t = TM.series()
    news = news_for(by_t)
    with tempfile.TemporaryDirectory() as d:
        for t, bars in by_t.items():
            with open(os.path.join(d, t + ".csv"), "w") as f:
                f.write("date,high,low,close,volume,adjclose\n")
                for dd, c in bars:
                    f.write("%s,%.4f,%.4f,%.4f,1,%.4f\n"
                            % (dd, c, c, c, c))
        mp = os.path.join(d, "matches.jsonl")
        with open(mp, "wb") as f:
            for tk, stamps in news.items():
                for s in stamps[:200]:
                    f.write((json.dumps({"date": s, "tickers": [tk]})
                             + "\n").encode())
            f.write(b'{"date": "2024')            # truncated line
            f.write(b"\n")
            f.write('{"date":"20240101000000","tickers":["caf\u00e9"]}'
                    .encode("utf-8")[:-8] + b"\xc3\n")  # split UTF-8
        loaded, bad = N.load_matches(mp)
        check("bad lines counted, not fatal", bad == 2, bad)
        out = io.StringIO()
        js = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(out):
            code = N.main(["--history", d, "--matches", mp, "--regime",
                           "post", "--reps", "30", "--json", js])
        res = json.load(open(js))
    txt = out.getvalue()
    check("exit 0, descriptive json", code == 0
          and res["descriptive"] is True)
    check("no verdict word or key", not any(
        w in (txt + json.dumps(res)).lower()
        for w in ("verdict", "keep", "reject", "adopt", "pass")))
    check("family size 12, 6 readings for a one-regime run",
          res["holm"]["family_size"] == 12
          and len(res["holm"]["readings"]) == 6)
    check("unreadable lines reported", "unreadable match lines: 2" in txt)


def main():
    for fn in (test_constants, test_point_in_time_window,
               test_zscore_and_multiplier, test_screen_pairs_semantics,
               test_matches_loader_and_main):
        fn()
    print("test_screen_news_width: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
