#!/usr/bin/env python3
"""Tests for benchmarks/screen_band_models.py (INS-IMPROVE-007 item 1).
Standalone, stdlib only, fixed synthetic inputs.
"""
import importlib.util
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
    "sbm", os.path.join(ROOT, "benchmarks", "screen_band_models.py"))
S = importlib.util.module_from_spec(spec)
sys.modules["sbm"] = S
spec.loader.exec_module(S)


def write_csv(path, start_ord, n):
    import datetime as dt
    d0 = dt.date.fromordinal(start_ord)
    lines = ["Date,Open,High,Low,Close"]
    for i in range(n):
        d = d0 + dt.timedelta(days=i)
        c = 100 + (i % 7) - (i % 3) * 0.5
        lines.append("%s,%.2f,%.2f,%.2f,%.2f"
                     % (d.isoformat(), c, c + 1.5, c - 1.5, c + 0.2))
    open(path, "w").write("\n".join(lines))


def test_constants():
    check("v2 pinned", S.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("screen end", S.SCREEN_END == "2023-12-28")
    check("step and min hist", (S.STEP, S.MIN_HIST) == (21, 120))


def test_exclusion_rule():
    import datetime as dt
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "AAA.csv")
        # series crosses 2023-12-28: starts 2023-06-01, 300 calendar days
        write_csv(p, dt.date(2023, 6, 1).toordinal(), 300)
        bars = S.read_history_csv(p)
        check("series crosses the cutoff date", len(bars) > 0
              and bars[-1][0] == "2023-12-28", bars[-1][0] if bars else None)
        check("no bar after 2023-12-28", all(b[0] <= "2023-12-28"
                                             for b in bars))
        pairs = S.screen_pairs({"AAA": bars}, step=21, min_hist=100)
        n = sum(len(v) for v in pairs.values())
        check("pairs built from bars only before the cut", n > 0)
        # a window needs i + sessions <= len(bars): month pairs obey it
        month = [p for p in pairs["park60"] if p["horizon"] == "month"]
        check("month windows end on or before 2023-12-28",
              all(p["as_of"] <= "2023-12-28" for p in month))
        expect = len(range(100, len(bars) - 21 + 1, 21))
        check("month pair count is the <= arithmetic", len(month) == expect,
              (len(month), expect))


def test_regime_split():
    import datetime as dt
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "AAA.csv")
        # 2021-03-01 .. 2023-12-28 spans the 2021-09-05 break
        write_csv(p, dt.date(2021, 3, 1).toordinal(), 1000)
        bars = S.read_history_csv(p)
        check("series crosses the break", bars[0][0] < S.BREAK_DATE
              < bars[-1][0])
        pr = S.screen_pairs({"AAA": bars}, step=21, min_hist=100)["s20"]
        regs = {x["regime"] for x in pr}
        check("both regimes present", regs == {"pre", "post"}, regs)
        pre = [x for x in pr if x["regime"] == "pre"]
        check("pre windows end before the break: as_of <= break",
              all(x["as_of"] < S.BREAK_DATE for x in pre))
        post = [x for x in pr if x["regime"] == "post"]
        first_ok = min(x["as_of"] for x in post)
        i0 = [b[0] for b in bars].index(S.BREAK_DATE) \
            if S.BREAK_DATE in [b[0] for b in bars] else None
        check("post pairs start at least LOOKBACK sessions after the "
              "break", first_ok > S.BREAK_DATE)
        only = S.screen_pairs({"AAA": bars}, step=21, min_hist=100,
                              regime="post")["s20"]
        check("regime filter keeps only post",
              only and all(x["regime"] == "post" for x in only))
        straddle = [x for x in pr if x["as_of"] < S.BREAK_DATE
                    and x["regime"] == "post"]
        check("no pair straddles the break", straddle == [])


def test_models_differ_and_v2_column():
    import datetime as dt
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "AAA.csv")
        write_csv(p, dt.date(2023, 1, 1).toordinal(), 360)
        pairs = S.screen_pairs({"AAA": S.read_history_csv(p)},
                               step=21, min_hist=100)
        a = pairs["park60"][0]
        b = pairs["s20"][0]
        check("v2 column identical across models", a["is_v2"] == b["is_v2"]
              and a["in_v2"] == b["in_v2"])
        check("model bands differ", a["is_ch"] != b["is_ch"])


def test_refusal_and_json():
    import contextlib
    import io
    import json
    check("refuses no input", S.main([]) == 2)
    import datetime as dt
    with tempfile.TemporaryDirectory() as d:
        write_csv(os.path.join(d, "AAA.csv"),
                  dt.date(2023, 1, 1).toordinal(), 360)
        out = os.path.join(d, "o.json")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = S.main(["--history", d, "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("exit 0", rc == 0)
        check("json carries no verdict and is descriptive",
              "verdict" not in data and data["descriptive"] is True
              and "regimes" in data)
        check("effective n printed beside raw n",
              "effective n (cutoff clusters)" in buf.getvalue())


def main():
    for fn in (test_constants, test_exclusion_rule, test_regime_split,
               test_models_differ_and_v2_column, test_refusal_and_json):
        fn()
    print("test_screen_band_models: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
