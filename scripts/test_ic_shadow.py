"""Tests for benchmarks/ic_shadow.py: fixed synthetic inputs."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import io
import contextlib

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ic_shadow", os.path.join(HERE, "..", "benchmarks", "ic_shadow.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL", name, detail)


def row(d, t, h, tech, sent, net, move, status="matured", gap=None):
    return {"ticker": "T%02d" % t, "as_of": d, "horizon": h, "status": status,
            "dividend_gap": gap, "net_score": net, "realized_move_pct": move,
            "families": {"technicals": tech, "sentiment": sent}}


def ledger(ndates, ntick=20, sign=1, horizons=("day", "week")):
    rows = []
    for di in range(ndates):
        for h in horizons:
            for t in range(ntick):
                v = (t * 7 + di) % ntick  # distinct values per date
                rows.append(row("D%02d" % di, t, h, v / 10.0, 0.0 if t % 2 else v / 10.0,
                                v / 20.0, sign * v * 0.1 + 5.0))
    return rows


def test_spearman_and_ranks():
    check("ranks ties", M._ranks([1, 1, 3]) == [1.5, 1.5, 3.0])
    check("perfect", abs(M.spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1) < 1e-12)
    check("inverse", abs(M.spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1) < 1e-12)
    check("constant none", M.spearman([1, 1, 1], [1, 2, 3]) is None)
    check("n<3 none", M.spearman([1, 2], [1, 2]) is None)


def test_wide_boundary_and_excess():
    r19 = [("A", "t%d" % i, float(i), float(i)) for i in range(19)]
    r20 = [("A", "t%d" % i, float(i), float(i)) for i in range(20)]
    check("19 not wide", M.date_ics(r19) == {})
    ic = M.date_ics(r20)
    check("20 wide, IC 1", list(ic) == ["A"] and abs(ic["A"] - 1) < 1e-12)
    # excess = move - date mean is a constant shift, so IC unchanged by level
    r20s = [(d, t, s, m + 100) for d, t, s, m in r20]
    check("level shift invariant", abs(M.date_ics(r20s)["A"] - 1) < 1e-12)


def test_clean_filters():
    base = row("D", 1, "day", 1, 1, 1, 1)
    rows = [base,
            row("D", 2, "day", 1, 1, 1, 1, status="pending"),
            row("D", 3, "day", 1, 1, 1, 1, gap=0.5),
            row("D", 4, "week", 1, 1, 1, 1),
            row("D", 5, "day", None, 1, 1, 1),
            row("D", 6, "day", 1, 1, 1, None)]
    c = M.clean_rows(rows, "technicals", "day")
    check("only clean kept", [x[1] for x in c] == ["T01"], c)
    check("null sentiment dropped", len(M.clean_rows([row("D", 7, "day", 1, None, 1, 1)], "sentiment", "day")) == 0)
    check("zero sentiment kept", len(M.clean_rows([row("D", 7, "day", 1, 0.0, 1, 1)], "sentiment", "day")) == 1)
    dup = [row("D", 1, "day", 1, 1, 1, 1.0), row("D", 1, "day", 2, 2, 2, 9.0)]
    c = M.clean_rows(dup, "technicals", "day")
    check("first duplicate kept", len(c) == 1 and c[0][2] == 1.0 and c[0][3] == 1.0, c)


def test_gate_counts_only():
    res = M.score(ledger(19))
    s = res["signals"]["technicals"]
    check("19 dates below gate", s["wide_dates_both"] == 19 and not s["gate_reached"])
    check("no statistic below gate", "day" not in s and "week" not in s and "ci_lower_gt_0_both" not in s)
    check("day only is below gate", not M.score(ledger(25, horizons=("day",)))["signals"]["technicals"]["gate_reached"])
    s = M.score(ledger(20))["signals"]["technicals"]
    check("20 dates reach gate", s["gate_reached"] and s["day"]["n_dates"] == 20)
    txt = json.dumps(M.score(ledger(19))).lower()
    check("no verdict word", not any(w in txt for w in ("keep", "verdict", "pass", "fail", "significant")))


def test_pass_leg_and_ci():
    s = M.score(ledger(20, sign=1))["signals"]["technicals"]
    check("positive IC CI>0", s["day"]["ci95"][0] > 0 and s["ci_lower_gt_0_both"], s)
    check("mean IC 1", abs(s["day"]["mean_ic"] - 1) < 1e-9)
    s = M.score(ledger(20, sign=-1))["signals"]["technicals"]
    check("negative IC not pass", s["day"]["ci95"][1] < 0 and not s["ci_lower_gt_0_both"])
    leg = {"day": {"ci95": (0.1, 0.2), "n_ic_defined": 20}, "week": {"ci95": (0.0, 0.2), "n_ic_defined": 20}}
    check("lower bound exactly 0 fails", not M.pass_leg(leg))
    leg["week"]["ci95"] = (0.01, 0.2)
    check("both >0 passes", M.pass_leg(leg))
    leg["week"]["n_ic_defined"] = 19
    check("n_ic_defined<20 fails", not M.pass_leg(leg))
    ics = {"d%d" % i: v for i, v in enumerate([0.1, 0.5, -0.2, 0.3, 0.05, 0.4, -0.1, 0.25])}
    a = M.boot_ci(ics)
    check("seed fixed", a == M.boot_ci(ics))
    check("seed matters", a != M.boot_ci(ics, seed=71))
    check("icir", abs(M.icir([1.0, 3.0]) - 2.0 / (2 ** 0.5)) < 1e-12 and M.icir([1.0, 1.0]) is None)
    check("constants", M.SEED == 70 and M.B_DRAWS == 2000 and M.WIDE == 20 and M.GATE_DATES == 20)


def test_signals_separate_and_cli():
    s = M.score(ledger(20))["signals"]
    check("three signals", set(s) == {"technicals", "sentiment", "net_score"})
    # sentiment has zeros for odd tickers: still scored, differs from technicals
    check("sentiment differs", s["sentiment"]["day"]["mean_ic"] != s["technicals"]["day"]["mean_ic"])
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "l.json")
        json.dump({"forecasts_detail": ledger(3)}, open(p, "w"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            M.main(["--ledger", p])
        out = json.loads(buf.getvalue())
        check("cli counts only", out["signals"]["technicals"]["wide_dates_both"] == 3
              and "day" not in out["signals"]["technicals"])


def test_nonfinite_and_constant_signal():
    nan, inf = float("nan"), float("inf")
    rows = [row("D", 1, "day", nan, 1, 1, 1), row("D", 2, "day", inf, 1, 1, 1),
            row("D", 3, "day", 1, 1, 1, nan), row("D", 4, "day", 1, 1, 1, -inf),
            row("D", 5, "day", 1, 1, 1, 1), row("D", 6, "day", True, 1, 1, 1)]
    c = M.clean_rows(rows, "technicals", "day")
    check("non-finite dropped", [x[1] for x in c] == ["T05"], c)
    check("bool signal dropped", all(x[1] != "T06" for x in c))
    check("nan net_score dropped", M.clean_rows([row("D", 1, "day", 1, 1, nan, 1)], "net_score", "day") == [])
    # 20 tickers, 20 dates: technicals constant (IC undefined) but dates still wide
    led = ledger(20)
    for f in led:
        f["families"]["technicals"] = 0.5
    s = M.score(led)["signals"]["technicals"]
    check("constant signal: wide counted", s["wide_dates_day"] == 20 and s["wide_dates_both"] == 20 and s["gate_reached"], s)
    check("constant signal: no IC defined", s["day"]["n_ic_defined"] == 0 and s["day"]["n_dates"] == 20)
    check("constant signal: no mean on empty", s["day"]["mean_ic"] is None and s["day"]["icir"] is None and s["day"]["ci95"] == [None, None])
    check("constant signal: not pass", s["ci_lower_gt_0_both"] is False)
    # 19 dates constant + 1 date non-constant is wide 20, defined 20 only for others
    led = ledger(20)
    for f in led:
        if f["as_of"] == "D00":
            f["families"]["technicals"] = 0.5
    s = M.score(led)["signals"]["technicals"]
    check("one undefined date: wide 20, defined 19", s["day"]["n_dates"] == 20 and s["day"]["n_ic_defined"] == 19, s["day"])
    check("one undefined date: pass needs 20 defined", s["ci_lower_gt_0_both"] is False)
    # NaN rows reduce a date below 20 clean tickers
    led = ledger(20)
    led[0]["realized_move_pct"] = nan
    s = M.score(led)["signals"]["technicals"]
    check("nan row removes wide date at day", s["wide_dates_day"] == 19 and s["wide_dates_week"] == 20 and not s["gate_reached"], s)


def run_all():
    for fn in (test_spearman_and_ranks, test_wide_boundary_and_excess, test_clean_filters,
               test_gate_counts_only, test_nonfinite_and_constant_signal, test_pass_leg_and_ci, test_signals_separate_and_cli):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    run_all()
    print("test_ic_shadow: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
