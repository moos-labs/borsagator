#!/usr/bin/env python3
"""Tests for benchmarks/pooled_quantile_coverage.py (INS-IMPROVE-001
round 12). Standalone, stdlib only, fixed synthetic inputs, assertions
through the tool's own output. The __main__ guard below is deliberate
(the #753 bug class: sys.exit at import time)."""
import contextlib
import datetime as dt
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
    "pqc", os.path.join(ROOT, "benchmarks", "pooled_quantile_coverage.py"))
C = importlib.util.module_from_spec(spec)
sys.modules["pqc"] = C
spec.loader.exec_module(C)

NH = 1.2816  # naive_half -> scale exactly 1.0


def row(h, a, real, tk="A", cell=50):
    return {"cell": cell, "ticker": tk, "as_of": a, "horizon": h,
            "real": real, "naive_half": NH, "mult": 1.0,
            "v2_sigma": 0.01, "sig": {"park60": 0.01}}


def test_quantile():
    xs = [i / 10.0 for i in range(-20, 21)]  # 41 values
    check("q10 exact grid point", abs(C.quantile(xs, 0.10) + 1.6) < 1e-9)
    check("q90 exact grid point", abs(C.quantile(xs, 0.90) - 1.6) < 1e-9)
    check("interpolates", abs(C.quantile([0.0, 10.0], 0.25) - 2.5) < 1e-9)
    check("empty is None", C.quantile([], 0.5) is None)
    check("input order irrelevant",
          C.quantile([3, 1, 2], 0.5) == C.quantile([1, 2, 3], 0.5) == 2)


def test_fit_pools_and_bands():
    zh = {"day": [i / 10.0 for i in range(-20, 21)], "week": [1.0] * 5,
          "month": []}
    zc = {"day": [], "week": [], "month": []}
    f = C.fit(zh, zc)
    check("fit quantiles", abs(f["day"]["lo"] + 1.6) < 1e-9
          and abs(f["day"]["hi"] - 1.6) < 1e-9, f["day"])
    check("below MIN_FIT is undefined", f["week"]["lo"] is None
          and f["month"]["lo"] is None, f)
    zc2 = {"day": [9.0] * 10, "week": [], "month": []}
    f2 = C.fit(zh, zc2)
    check("cell residuals join the pool", f2["day"]["n_cells"] == 10
          and f2["day"]["hi"] > 1.6, f2["day"])
    # band = Q x row scale, asymmetric, undefined horizon skipped
    rows = [row("day", "d1", 1.5), row("day", "d1", -1.7),
            row("week", "d1", 0.0)]
    rows[0]["naive_half"] = NH * 2.0   # scale 2 -> band [-3.2, 3.2]
    ps = C.make_pairs(rows, f)
    check("undefined horizon dropped", len(ps) == 2
          and all(p["horizon"] == "day" for p in ps))
    check("band scales with the row", ps[0]["in_ch"] and not ps[1]["in_ch"],
          ps)
    check("Winkler of the scaled band", abs(ps[0]["is_ch"] - 6.4) < 1e-9,
          ps[0]["is_ch"])
    check("miss pays width + 10 x distance",
          abs(ps[1]["is_ch"] - (3.2 + 10 * 0.1)) < 1e-9, ps[1]["is_ch"])
    check("Parkinson-naive band is 1.2816 x park60 x sqrt(sessions)",
          abs(ps[1]["is_park"] - (2 * 1.2816 + 10 * (1.7 - 1.2816)))
          < 1e-6, ps[1]["is_park"])


def test_asymmetric_band():
    zh = {"day": [i / 10.0 for i in range(-10, 31)], "week": [],
          "month": []}   # skewed: Q10 -0.6, Q90 2.6
    f = C.fit(zh, {"day": [], "week": [], "month": []})
    check("skewed quantiles", abs(f["day"]["lo"] + 0.6) < 1e-9
          and abs(f["day"]["hi"] - 2.6) < 1e-9, f["day"])
    ps = C.make_pairs([row("day", "d", 2.0), row("day", "d", -0.8),
                       row("day", "d", 2.7)], f)
    check("band is not mirrored", [p["in_ch"] for p in ps]
          == [True, False, False], ps)
    check("Winkler uses the asymmetric edges",
          abs(ps[1]["is_ch"] - (3.2 + 10 * 0.2)) < 1e-9, ps[1]["is_ch"])


def write_csv(path, start, n, wild_after=None, adj=None):
    d0 = dt.date.fromisoformat(start)
    lines = ["date,high,low,close,volume,adjclose"]
    for i in range(n):
        d = d0 + dt.timedelta(days=i)
        c = 100 + (i % 7) - (i % 3) * 0.5
        if wild_after and d.isoformat() > wild_after:
            c *= 5 if i % 2 else 0.2   # wild bars after the cutoff
        lines.append("%s,%.2f,%.2f,%.2f,1,%s" % (
            d.isoformat(), c + 1, c - 1, c, adj or "1.0"))
    open(path, "w").write("\n".join(lines))


def test_history_filters():
    with tempfile.TemporaryDirectory() as d:
        write_csv(os.path.join(d, "AAA_CA.csv"), "2021-11-01", 800)
        write_csv(os.path.join(d, "NVDA.csv"), "2021-11-01", 800)
        h = C.load_history(d)
        check("only *_CA files", sorted(h) == ["AAA_CA"], sorted(h))
        z1 = C.history_z(h, "post")
        write_csv(os.path.join(d, "AAA_CA.csv"), "2021-11-01", 800,
                  wild_after=C.S.SCREEN_END, adj="9999")
        z2 = C.history_z(C.load_history(d), "post")
        last = max(b[0] for b in C.load_history(d)["AAA_CA"])
        check("bars after SCREEN_END are dropped on read",
              last <= C.S.SCREEN_END, last)
        check("later wild bars and adjclose never enter",
              z1 == z2 and any(z1[k] for k in z1), (len(z1["day"]),))
        check("all-post fixture has no pre windows",
              not any(C.history_z(C.load_history(d), "pre").values()))
    with tempfile.TemporaryDirectory() as d:
        write_csv(os.path.join(d, "BBB_CA.csv"), "2019-01-01", 400)
        h = C.load_history(d)
        check("pre-break history lands only in pre",
              not any(C.history_z(h, "post").values())
              and any(C.history_z(h, "pre").values()))


def run_main(argv, rows_by_cells, zh):
    seen = []
    orig = (C.A.find_captures, C.R.build_rows, C.load_history,
            C.history_z)
    caps = ["/x/r__w5-backtest-436-cell%d" % n
            for n in (5, 47, 48, 90, 91, 102)] + ["/x/r__nocell"]
    C.A.find_captures = lambda p, m: caps

    def fake_build(cs, ref):
        seen.append([os.path.basename(c) for c in cs])
        return [r for r in rows_by_cells
                if any(c.endswith("cell%d" % r["cell"]) for c in cs)], []
    C.R.build_rows = fake_build
    C.load_history = lambda p: {}
    C.history_z = lambda by_t, regime: (zh if regime == "post"
                                        else {h: [] for h in C.HORIZONS})
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = C.main(argv)
    finally:
        (C.A.find_captures, C.R.build_rows, C.load_history,
         C.history_z) = orig
    return code, out.getvalue(), err.getvalue(), seen


def test_main_split_and_numbers():
    zh = {"day": [i / 10.0 for i in range(-20, 21)], "week": [],
          "month": []}
    rows = [row("day", "d%d" % i, r, tk="T%d" % i, cell=50 + i)
            for i, r in enumerate([0.0, 1.5, -1.5, 1.7, -1.7])]
    rows[0]["cell"], rows[1]["cell"] = 48, 90
    rows[2]["cell"], rows[3]["cell"], rows[4]["cell"] = 48, 90, 48
    with tempfile.TemporaryDirectory() as d:
        js = os.path.join(d, "o.json")
        code, out, err, seen = run_main(
            ["--history", "h", "--captures", "c", "--reps", "20",
             "--json", js], rows, zh)
        res = json.load(open(js))
    check("exit 0", code == 0, err)
    check("fit gets cells <= 47 only", seen[0] == [
        "r__w5-backtest-436-cell5", "r__w5-backtest-436-cell47"], seen)
    check("score gets 48-90 only, unnumbered dropped", seen[1] == [
        "r__w5-backtest-436-cell48", "r__w5-backtest-436-cell90"], seen)
    flat = [x for s in seen for x in s]
    check("verdict cells 91+ never reach a build", not any(
        "cell91" in x or "cell102" in x or "nocell" in x for x in flat))
    day = res["results"]["day"]
    check("coverage is 3 of 5 in [-1.6, 1.6]",
          abs(day["ch"]["coverage"] - 0.6) < 1e-9 and day["n"] == 5, day)
    check("fit quantiles reach the output",
          abs(res["fit"]["day"]["lo"] + 1.6) < 1e-9)
    check("undefined horizons print n/a and score nothing",
          res["results"]["week"]["n"] == 0 and "n/a" in out, out[-200:])
    blob = (out + json.dumps(res)).lower()
    check("no verdict word or key", not any(
        w in blob for w in ("verdict", "keep", "adopt", "reject")), blob[:0])
    check("descriptive flag", res["descriptive"] is True)


def test_main_refuses_outside_window():
    for argv in (["--min-cell", "47"], ["--max-cell", "91"],
                 ["--min-cell", "0", "--max-cell", "102"]):
        code, out, err, seen = run_main(
            ["--history", "h", "--captures", "c"] + argv, [], {})
        check("refuses %s" % argv, code == 2 and "refusing" in err
              and not seen, (code, err))


def main():
    for fn in (test_quantile, test_fit_pools_and_bands,
               test_asymmetric_band,
               test_history_filters, test_main_split_and_numbers,
               test_main_refuses_outside_window):
        fn()
    print("test_pooled_quantile_coverage: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
