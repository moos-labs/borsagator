"""Tests for benchmarks/index_regime_flag.py: fixed synthetic inputs."""
import importlib.util
import json
import math
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "index_regime_flag", os.path.join(HERE, "..", "benchmarks", "index_regime_flag.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def series(n=40, start="2024-01-%02d"):
    # 40 consecutive pseudo-sessions 2024-02-01.. via day counter, close = 100 * 1.01**i
    out = []
    for i in range(n):
        m, d = (2, i + 1) if i < 28 else (3, i - 27)
        out.append(("2024-%02d-%02d" % (m, d), 100 * 1.01 ** i))
    return out


def test_trailing_x():
    s = series()
    x = M.trailing_x(s, "2024-03-05")  # index 32
    check("x exact", abs(x - 21 * math.log(1.01)) < 1e-12, x)
    check("x on-or-before", M.trailing_x(s, "2024-03-05") == M.trailing_x(s, "2024-03-05"))
    # asof between sessions uses the earlier one
    s2 = [(d, c) for d, c in s if d != "2024-03-05"]
    check("x skips missing day", abs(M.trailing_x(s2, "2024-03-05") - M.trailing_x(s, "2024-03-04")) < 1e-12)
    check("x short history", M.trailing_x(s, "2024-02-10") is None)
    check("x not future", abs(M.trailing_x(s, "2024-03-03") - 21 * math.log(1.01)) < 1e-12)


def test_trailing_x_nongeometric():
    # closes 100,101,...: ln(c[i]/c[i-21]) differs for every i
    s = [(("2024-02-%02d" % (i + 1)) if i < 28 else ("2024-03-%02d" % (i - 27)), 100.0 + i) for i in range(40)]
    check("x exact day", abs(M.trailing_x(s, "2024-03-05") - math.log(132.0 / 111.0)) < 1e-12)
    check("x day before", abs(M.trailing_x(s, "2024-03-04") - math.log(131.0 / 110.0)) < 1e-12)
    check("x first usable", abs(M.trailing_x(s, "2024-02-22") - math.log(121.0 / 100.0)) < 1e-12)
    check("x one short", M.trailing_x(s, "2024-02-21") is None)


def test_spearman_and_ties():
    check("rho +1", abs(M.spearman([1, 2, 3, 4], [10, 20, 30, 45]) - 1) < 1e-12)
    check("rho -1", abs(M.spearman([1, 2, 3, 4], [9, 8, 7, 1]) + 1) < 1e-12)
    r = M.spearman([1, 2, 2, 3], [1, 2, 3, 4])
    check("rho ties", abs(r - 0.9486832980505138) < 1e-9, r)
    check("rho const none", M.spearman([1, 1, 1], [1, 2, 3]) is None)
    check("rho short none", M.spearman([1, 2], [1, 2]) is None)


def test_boot_clustered():
    rows = [("a", 1, 1), ("a", 2, 2), ("b", 3, 3), ("b", 4, 4), ("c", 5, 5), ("c", 6, 6)]
    lo, hi = M.boot_ci(rows, draws=200, seed=1)
    check("boot perfect", lo == 1.0 and hi == 1.0, (lo, hi))
    lo2, hi2 = M.boot_ci(rows, draws=200, seed=1)
    check("boot deterministic", (lo, hi) == (lo2, hi2))
    mixed = [("a", 1, 1), ("a", 2, 2), ("b", 3, 6), ("b", 4, 5), ("c", 5, 4), ("c", 6, 3)]
    ml, mh = M.boot_ci(mixed, draws=300, seed=2)
    check("boot resamples clusters", ml < mh, (ml, mh))
    inv = [("a", 1, 4), ("a", 2, 3), ("b", 3, 2), ("b", 4, 1)]
    l, h = M.boot_ci(inv, draws=200, seed=1)
    check("boot inverse", h < 0 or l < 0 and h <= 0.0 + 1e-9, (l, h))


def write_cell(d, n, ticker, asof, moves, gap=None, entrant="buy-and-hold"):
    F = []
    for h, v in moves.items():
        F.append({"ticker": ticker, "as_of": asof, "horizon": h, "entrant": entrant,
                  "status": "matured", "dividend_gap": gap, "realized_move_pct": v})
    F.append({"ticker": ticker, "as_of": asof, "horizon": "week", "entrant": "kronos-alone",
              "status": "matured", "dividend_gap": None, "realized_move_pct": 999.0})
    json.dump({"forecasts_detail": F}, open(os.path.join(d, "cell%d_score_v2.json" % n), "w"))


def test_build_filters_and_blocks():
    with tempfile.TemporaryDirectory() as d:
        write_cell(d, 1, "AAA.CA", "2024-03-05", {"day": 1.0, "week": 2.0, "month": 3.0})
        write_cell(d, 2, "BBB", "2024-03-06", {"day": -1.0, "week": 2.5, "month": 3.5})
        write_cell(d, 3, "CCC", "2024-03-07", {"day": 1.0, "week": 9.0, "month": 9.0}, gap=True)
        write_cell(d, 4, "DDD", "2024-02-05", {"day": 1.0, "week": 1.0, "month": 1.0})  # short history
        write_cell(d, 48, "EEE", "2024-03-05", {"day": 1.0, "week": 1.0, "month": 1.0})  # beyond block
        sr = {"EGX30": series(), "GSPC": [(a, 200 - c) for a, c in series()]}
        res, cells = M.build(d, sr)
        check("used cells", res["n_cells_used"] == 3, res["n_cells_used"])
        check("lacking listed", [r["cell"] for r in res["cells_without_index"]] == [4])
        check("flagged gap row not used", res["horizons"]["week"]["n"] == 2)
        check("kronos row ignored", all(c[4].get("week") != 999.0 for c in cells))
        check("cell 48 unread", all(c[0] != 48 for c in cells))
        check("index routing", cells[0][3] > 0 and cells[1][3] < 0, [c[3] for c in cells])
        check("sign agree", res["horizons"]["week"]["sign_agree"] == 1 and res["horizons"]["day"]["sign_agree"] == 2)
        write_cell(d, 5, "ZZZ", "2024-03-05", {"day": 1.0, "week": 1.0, "month": 1.0})
        sr0 = {"EGX30": series(), "GSPC": [(a, 100.0) for a, c in series()]}
        r0, _ = M.build(d, sr0)
        check("x==0 dropped from sign", r0["horizons"]["day"]["sign_n"] == r0["horizons"]["day"]["n"] - 1 or r0["horizons"]["day"]["sign_n"] < r0["horizons"]["day"]["n"])
        os.remove(os.path.join(d, "cell5_score_v2.json"))
        res2, cells2 = M.build(d, sr, max_cell=48)
        check("max_cell widens", any(c[0] == 48 for c in cells2))


def test_thresholds_and_cli():
    good = {"n": 30, "spearman": 0.2, "spearman_ci95": [0.01, 0.4], "sign_agree_share": 0.6}
    res = {"horizons": {"week": dict(good), "month": dict(good)}}
    check("all met at edge", M.prereg_thresholds(res)["all_met"])
    for key, val in (("n", 29), ("spearman", 0.199), ("sign_agree_share", 0.599), ("spearman_ci95", [0.0, 0.4])):
        r2 = {"horizons": {"week": dict(good), "month": dict(good, **{key: val})}}
        check("fails on " + key, not M.prereg_thresholds(r2)["all_met"], key)
    with tempfile.TemporaryDirectory() as d0:
        for nm in ("e.csv", "g.csv"):
            with open(os.path.join(d0, nm), "w") as f:
                f.write("date,close\n" + "".join("%s,%s\n" % r for r in series()))
        write_cell(d0, 1, "AAA.CA", "2024-03-05", {"day": 1.0, "week": 2.0, "month": 3.0})
        try:
            M.main(["--cells", d0, "--egx30", os.path.join(d0, "e.csv"), "--gspc",
                    os.path.join(d0, "g.csv"), "--max-cell", "48"])
            check("refuse extend without flag", False)
        except SystemExit as e:
            check("refuse extend without flag", "allow-extend" in str(e))
    with tempfile.TemporaryDirectory() as d:
        for nm, s in (("e.csv", series()), ("g.csv", series())):
            with open(os.path.join(d, nm), "w") as f:
                f.write("date,close\n" + "".join("%s,%s\n" % r for r in s))
        write_cell(d, 1, "AAA.CA", "2024-03-05", {"day": 1.0, "week": 2.0, "month": 3.0})
        out = os.path.join(d, "o.json")
        M.main(["--cells", d, "--egx30", os.path.join(d, "e.csv"), "--gspc", os.path.join(d, "g.csv"), "--json", out])
        txt = open(out).read().lower()
        check("cli json", json.loads(txt)["n_cells_used"] == 1)
        check("no verdict word", not any(w in txt for w in ("verdict", "keep", "reject", "adopt")))


def test_stale_bar_and_extension_gate():
    s = series()
    # last bar 2024-03-12 (index 39); asof 10 days later is still allowed, 11 is None
    check("stale 10 days ok", M.trailing_x(s, "2024-03-22") is not None)
    check("stale 11 days None", M.trailing_x(s, "2024-03-23") is None)
    check("stale far None", M.trailing_x(s, "2024-06-01") is None)
    with tempfile.TemporaryDirectory() as d:
        write_cell(d, 1, "AAA.CA", "2024-03-05", {"day": 1.0, "week": 2.0, "month": 3.0})
        write_cell(d, 2, "BBB.CA", "2024-06-01", {"day": 1.0, "week": 2.0, "month": 3.0})  # stale bar
        sr = {"EGX30": s, "GSPC": s}
        res, cells = M.build(d, sr)
        check("stale cell lacking", [r["cell"] for r in res["cells_without_index"]] == [2] and len(cells) == 1)
        # extension gate: training fails (n < 30), so extension is refused
        write_cell(d, 48, "CCC.CA", "2024-03-05", {"day": 1.0, "week": 1.0, "month": 1.0})
        try:
            M.run(d, sr, max_cell=48, allow_extend=True)
            check("extension refused when training fails", False)
        except SystemExit as e:
            check("extension refused when training fails", "training thresholds not all met" in str(e))
        # training passes: 40 cells with perfect monotone relation, extension allowed
    with tempfile.TemporaryDirectory() as d:
        ser = [("2024-%02d-%02d" % (1 + i // 28, 1 + i % 28), 100.0 * math.exp(0.0005 * i * i)) for i in range(200)]
        sr = {"EGX30": ser, "GSPC": ser}
        for k in range(1, 41):
            asof = ser[30 + k * 2][0]
            write_cell(d, k, "T%d.CA" % k, asof, {"day": k * 1.0, "week": k * 1.0, "month": k * 1.0})
        write_cell(d, 48, "ZZ.CA", ser[150][0], {"day": 1.0, "week": 1.0, "month": 1.0})
        res = M.run(d, sr, max_cell=48, allow_extend=True)
        check("training thresholds pass", res["prereg_thresholds"]["all_met"], res["prereg_thresholds"])
        check("training block excludes cell 48", res["n_cells_used"] == 40, res["n_cells_used"])
        check("extension read when passing", "extension" in res and res["extension"]["n_cells_used"] == 1)
        res_t = M.run(d, sr)
        check("default run has no extension", "extension" not in res_t)
        try:
            M.run(d, sr, max_cell=48, allow_extend=False)
            check("no flag refused", False)
        except SystemExit as e:
            check("no flag refused", "allow-extend" in str(e))


def run_all():
    for fn in (test_trailing_x, test_trailing_x_nongeometric, test_spearman_and_ties, test_boot_clustered,
               test_build_filters_and_blocks, test_thresholds_and_cli, test_stale_bar_and_extension_gate):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_index_regime_flag: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
