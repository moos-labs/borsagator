#!/usr/bin/env python3
"""Tests for benchmarks/screen_delta_vs_v2.py (INS-IMPROVE-001 round 30,
paired delta vs frozen v2). Standalone, stdlib only, fixed synthetic
inputs, assertions through the screen's functions and CLI output.
__main__ guard deliberate (#753 class)."""
import contextlib
import importlib.util
import io
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
    "dv", os.path.join(ROOT, "benchmarks", "screen_delta_vs_v2.py"))
D = importlib.util.module_from_spec(spec)
sys.modules["dv"] = D
spec.loader.exec_module(D)
import test_screen_market_factor as TM  # noqa: E402
import test_screen_exog_factor as TX  # noqa: E402
import test_screen_fx_stress as TF  # noqa: E402

TM.NB = 480


def pr(as_of, naive, v2, ch, h="day"):
    return {"as_of": as_of, "ticker": "T", "horizon": h, "is_naive": naive,
            "is_v2": v2, "is_ch": ch, "in_v2": True, "in_ch": True}


def test_constants():
    check("family 48 = (3 + 3 + 2) x 3 x 2", D.FAMILY_SIZE == 48)


def test_delta_stat():
    ps = [pr("a", 10.0, 8.0, 6.0), pr("b", 10.0, 7.0, 7.0),
          pr("c", 20.0, 12.0, 15.0)]
    want = (8.0 + 7.0 + 12.0 - 6.0 - 7.0 - 15.0) / 40.0
    check("delta = (sum v2 - sum ch) / sum naive", abs(
        D.delta_stat(ps) - want) < 1e-15, (D.delta_stat(ps), want))
    check("delta equals range_skill(ch) - range_skill(v2)", abs(
        D.delta_stat(ps) - (D.A.range_skill(ps, "ch")
                            - D.A.range_skill(ps, "v2"))) < 1e-15)
    check("a worse candidate gives a negative delta",
          D.delta_stat([pr("a", 10.0, 5.0, 9.0)]) < 0)
    check("undefined when the naive sum is 0",
          D.delta_stat([pr("a", 0.0, 1.0, 1.0)]) is None
          and D.delta_stat([]) is None)


def test_bootstrap_and_p():
    two = [pr("a", 10.0, 8.0, 6.0), pr("a", 10.0, 8.0, 6.0),
           pr("b", 10.0, 5.0, 9.0)]
    da, db = D.delta_stat(two[:2]), D.delta_stat(two[2:])
    dab = D.delta_stat(two)
    allowed = (da, db, dab)
    draws = D.boot_delta(two, 200)
    check("200 draws, whole cutoffs only (3 possible values)",
          len(draws) == 200 and all(
              any(abs(x - v) < 1e-12 for v in allowed) for x in draws)
          and len({round(x, 9) for x in draws}) == 3, sorted(set(draws)))
    check("same seed, same draws", D.boot_delta(two, 50)
          == D.boot_delta(two, 50))
    same = [pr(str(k), 10.0, 6.0, 6.0) for k in range(5)]
    r = D.reading(same, 100)
    check("identical to v2: delta 0, every draw is 0, p = 1",
          r["delta"] == 0 and r["p"] == 1.0
          and r["ci"] == [0.0, 0.0], r)
    better = [pr(str(k), 10.0, 6.0, 4.0) for k in range(30)]
    rb = D.reading(better, 99)
    check("better on every cutoff: p = 1/100 (Phipson-Smyth +1)",
          abs(rb["p"] - 1.0 / 100.0) < 1e-12 and rb["delta"] > 0
          and rb["ci"][0] > 0, rb)
    worse = [pr(str(k), 10.0, 4.0, 6.0) for k in range(30)]
    check("worse on every cutoff: p = 1", D.reading(worse, 99)["p"] == 1.0)
    check("n and cutoffs reported", rb["n"] == 30 and rb["cutoffs"] == 30)


def test_holm_family_fixed():
    rd = {("s", "m%d" % k, "day", "post"): {
        "n": 1, "cutoffs": 1, "delta": 0.01, "ci": [0.0, 0.02],
        "p": 0.001 * (k + 1)} for k in range(3)}
    rows = D.holm_rows(rd)
    byname = {r["name"]: r for r in rows}
    check("Holm multiplies by the family of 48, not by the readings "
          "present", abs(byname["m0"]["holm_adj_p"] - 0.048) < 1e-12
          and abs(byname["m1"]["holm_adj_p"] - 47 * 0.002) < 1e-12
          and abs(byname["m2"]["holm_adj_p"] - 46 * 0.003) < 1e-12,
          [r["holm_adj_p"] for r in rows])


def test_render_small_delta():
    row = {"screen": "s", "name": "n", "horizon": "day", "regime": "post",
           "n": 10, "cutoffs": 5, "delta": 0.00063,
           "ci": [0.00021, 0.00094], "p": 0.0125, "holm_adj_p": 0.024}
    txt = D.render([row])
    check("small delta and interval keep 4 decimals", "delta 0.0006 "
          "(CI cutoff [0.0002, 0.0009])" in txt, txt)
    check("p keeps 3 decimals", "p 0.013 Holm-adjusted p 0.024" in txt, txt)
    check("none rounds to 0.000", "0.000 " not in txt, txt)


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
        for name, seed in zip(D.XF.FACTORS.values(), (0.0, 1.0, 2.0)):
            with open(os.path.join(fdir, name), "w") as f:
                f.write("date,close\n")
                for dd, c in TX.fbars(seed):
                    f.write("%s,%.6f\n" % (dd, c))
        fxp = os.path.join(d, "fx.csv")
        with open(fxp, "w") as f:
            f.write("date,close\n")
            for dd, c in TF.fx_bars():
                f.write("%s,%.6f\n" % (dd, c))
        out = io.StringIO()
        js = os.path.join(d, "o.json")
        with contextlib.redirect_stdout(out):
            code = D.main(["--history", hd, "--factors", fdir, "--fx", fxp,
                           "--regime", "post", "--reps", "30",
                           "--json", js])
        res = json.load(open(js))
        fxbars = D.FX.read_close_csv(fxp)
        loaded = D.MF.load(hd)
    txt = out.getvalue()
    check("exit 0, descriptive json", code == 0
          and res["descriptive"] is True)
    check("no verdict word or key", not any(
        w in (txt + json.dumps(res)).lower()
        for w in ("verdict", "keep", "reject", "adopt", "pass")))
    rows = res["holm"]["readings"]
    check("family 48 fixed, 24 readings for one regime (8 x 3 horizons)",
          res["holm"]["family_size"] == 48 and len(rows) == 24, len(rows))
    check("every reading has a delta, CI and p", all(
        r["delta"] is not None and r["p"] is not None
        and r["ci"][0] <= r["ci"][1] for r in rows))
    check("Holm adjusted p never below raw", all(
        r["holm_adj_p"] >= r["p"] for r in rows))
    check("three screens present", {r["screen"] for r in rows}
          == set(D.SCREENS))
    one = [r for r in rows if r["screen"] == "fx_stress"
           and r["name"] == "beta 0.10" and r["horizon"] == "day"][0]
    pairs = D.FX.screen_pairs(loaded, fxbars,
                              regime="post")[0.10]
    hp = [p for p in pairs if p["horizon"] == "day"]
    check("a printed delta equals the delta of that screen's own pairs",
          abs(one["delta"] - D.delta_stat(hp)) < 1e-15
          and one["n"] == len(hp), (one["delta"], D.delta_stat(hp), one["n"], len(hp)))


def main():
    for fn in (test_constants, test_delta_stat, test_bootstrap_and_p,
               test_holm_family_fixed, test_render_small_delta,
               test_main):
        fn()
    print("test_screen_delta_vs_v2: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
