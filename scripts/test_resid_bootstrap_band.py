#!/usr/bin/env python3
"""Tests for benchmarks/replay_resid_bootstrap_band.py (round 61).
Standalone, stdlib only, fixed synthetic inputs. Also runs under
`python3 -m unittest discover -s scripts`.
"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest

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
    "rbb", os.path.join(ROOT, "benchmarks",
                        "replay_resid_bootstrap_band.py"))
Q = importlib.util.module_from_spec(spec)
sys.modules["rbb"] = Q
spec.loader.exec_module(Q)

SIG = 0.02


def row(t, z, a="d1", h="day", s=SIG):
    """A row whose realised move is z scale units of the v2 scale."""
    sc = Q.R.half_pct(s or SIG, h, 1.0, 1.0)
    return {"ticker": t, "as_of": a, "horizon": h, "real": z * sc,
            "naive_half": Q.R.half_pct(s or SIG, h, 1.2816, 1.0), "mult": 1.0,
            "v2_sigma": s, "sig": {}}


def training(n=12, zs=(0.2, 0.5, 0.8, 1.0, 2.0)):
    out = []
    for i in range(n):
        out += [row("T%d" % j, z, "t%d" % i) for j, z in enumerate(zs)]
    return out


def test_constants():
    check("level .80", Q.LEVEL == 0.80)
    check("training 47, clean 91, keep clusters 10",
          (Q.FIT_MAX_CELL, Q.CLEAN_MIN_CELL, Q.MIN_KEEP_CLUSTERS)
          == (47, 91, 10))
    check("v2 pinned", Q.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})


def test_clusters_quantile():
    rows = training(3)
    cl = Q.clusters(rows, "day")
    check("one cluster per cutoff, all tickers",
          sorted(cl) == ["t0", "t1", "t2"]
          and all(len(v) == 5 for v in cl.values()))
    check("residual is |move| over the v2 scale",
          abs(cl["t0"][4] - 2.0) < 1e-9, cl["t0"])
    check("other horizons empty", Q.clusters(rows, "week") == {})
    check("nearest-rank quantile",
          Q.quantile([1, 2, 3, 4, 5], 0.8) == 4
          and Q.quantile([1, 2, 3, 4, 5], 1.0) == 5)
    check("negative move counts as |z|",
          abs(Q.clusters([row("A", -1.5)], "day")["d1"][0] - 1.5) < 1e-9)


def test_fit_q():
    rows = training()
    q, n = Q.fit_q(rows, draws=200)
    check("whole clusters: pool is 5 per cluster so q in the set",
          abs(q["day"] - 1.0) < 1e-9, q)
    check("training cluster counts", n["day"] == 12 and n["week"] == 0)
    check("horizon without clusters has no q", q["week"] is None)
    one = training(1)
    check("one cluster is below the minimum", Q.fit_q(one, 50)[0][
        "day"] is None)
    wide = training(12, zs=(3.0, 3.0, 3.0, 3.0, 3.0))
    check("wider residuals widen q",
          Q.fit_q(wide, 100)[0]["day"] > q["day"])
    check("deterministic", Q.fit_q(rows, 100) == Q.fit_q(rows, 100))
    held = rows + [row("X", 50.0, "held%d" % i) for i in range(12)]
    check("extra clusters in the rows do change the fit "
          "(so the CLI must never pass held-out rows)",
          Q.fit_q(held, 100)[0]["day"] > q["day"])


def test_score_rows():
    q = {"day": 2.0, "week": None, "month": None}
    inn = Q.score_rows([row("A", 1.9)], q)[0]
    check("band is q x v2 scale (through score_rows)",
          inn["in_ch"] and not inn["in_v2"], inn)
    out = Q.score_rows([row("A", 2.1)], q)[0]
    check("outside the band", not out["in_ch"])
    nof = Q.score_rows([row("A", 1.0, h="week")], q)[0]
    check("no q keeps the v2 half-width",
          nof["in_ch"] == nof["in_v2"]
          and abs(nof["is_ch"] - nof["is_v2"]) < 1e-9)
    check("unfit rows counted",
          Q.unfit_rows([row("A", 1.0, h="week"), row("A", 1.0)], q) == 1)
    check("no sigma skipped", Q.score_rows([row("A", 1.0, s=None)], q)
          == [])
    narrow = Q.score_rows([row("A", 0.0)], {"day": 0.5, "week": None,
                                            "month": None})[0]
    check("narrower band scores a lower interval score on an inside move",
          narrow["is_ch"] < narrow["is_v2"])


def res_with(cutoffs, n=40, tickers=6):
    return {h: {"n": n, "cutoffs": cutoffs, "tickers": tickers,
                "v2": {"coverage": 0.8, "range_skill": 0.0},
                "ch": {"coverage": 0.8, "range_skill": 0.1},
                "ch_ci_cutoff": [0.05, 0.2],
                "ch_cov_ci_cutoff": [0.76, 0.84],
                "ch_ci_ticker": [0.05, 0.2]} for h in Q.HORIZONS}


def test_verdict():
    check("under 10 clusters is insufficient",
          Q.keep_verdict(res_with(9))[0] == "INSUFFICIENT")
    check("10 clusters can keep", Q.keep_verdict(res_with(10))[0]
          == "KEEP")
    r = res_with(10)
    r["day"]["ch_ci_cutoff"] = [-0.01, 0.2]
    check("CI spanning zero rejects", Q.keep_verdict(r)[0] == "REJECT")
    r = res_with(10)
    r["week"]["ch_cov_ci_cutoff"] = [0.55, 0.9]
    check("coverage CI wider than 0.15 rejects",
          Q.keep_verdict(r)[0] == "REJECT")
    check("too few rows insufficient",
          Q.keep_verdict(res_with(12, n=10))[0] == "INSUFFICIENT")


def test_cell_selection():
    caps = ["/x/c-cell47/d/T", "/x/c-cell48/d/T", "/x/c-cell90/d/T",
            "/x/c-cell91/d/T", "/x/unnumbered/d/T"]
    pick = lambda lo, hi: [Q.A.cell_number(c) for c in
                           Q.select_caps(caps, lo, hi)]
    check("training is cells <= 47 only", pick(1, 47) == [47])
    check("descriptive window 48-90", pick(48, 90) == [48, 90])
    check("clean window 91+, unnumbered dropped", pick(91, None) == [91])


def test_cli_guards():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        c0 = Q.main(["score", "--captures", "/nonexistent",
                     "--min-cell", "73"])
        c1 = Q.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "90", "--min-cell", "91"])
        t1 = buf.getvalue()
        buf.truncate(0)
        buf.seek(0)
        c3 = Q.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "40", "--min-cell", "91"])
        t3 = buf.getvalue()
        c2 = Q.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "100", "--min-cell", "101",
                     "--descriptive"])
        c4 = Q.main(["diag", "--captures", "/nonexistent",
                     "--fit-max-cell", "60"])
        c6 = Q.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "40", "--min-cell", "40",
                     "--descriptive"])
        buf.truncate(0)
        buf.seek(0)
        c5 = Q.main(["score", "--captures", "/nonexistent",
                     "--fit-max-cell", "40", "--min-cell", "48",
                     "--descriptive"])
        t5 = buf.getvalue()
    check("clean scoring refuses seen cells", c0 == 2)
    check("clean fit window above 47 refused",
          c1 == 2 and "above the registered 47" in t1, t1)
    check("clean scoring needs exactly 47",
          c3 == 2 and "needs --fit-max-cell 47" in t3, t3)
    check("fit window above 47 refused, descriptive too", c2 == 2)
    check("diag above 47 refused", c4 == 2)
    check("scored cells may not overlap training", c6 == 2)
    check("descriptive may lower the window (reaches the fit)",
          c5 == 2 and "no training rows" in t5, t5)


def fake_args(fit_max=47):
    ns = type("NS", (), {})()
    ns.captures = ["/x"]
    ns.fit_max_cell = fit_max
    ns.reps = 20
    ns.seed = 1
    ns.draws = 50
    return ns


def test_fit_reference_and_report():
    caps = ["/x/c-cell%d/2025-01-0%d/T%d" % (n, 1 + n % 8, n % 7)
            for n in (3, 30, 47, 48, 90, 91)]
    calls = []

    def fake_build(cs, ref=None):
        calls.append((list(cs), list(ref)))
        if Q.A.cell_number(cs[0]) == 3:
            return training(), [
                "x: realised window rebuilt to 21 sessions from price.csv",
                "y: no usable pre-cutoff OHLC history"]
        return [row("S%d" % j, 0.5, "s%d" % (j % 3)) for j in range(6)], []
    old = (Q.R.build_rows, Q.A.find_captures)
    Q.R.build_rows, Q.A.find_captures = fake_build, lambda *a: caps
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc, out = Q._run(fake_args(), 48, 90, True, "DESCRIPTIVE ONLY")
    finally:
        Q.R.build_rows, Q.A.find_captures = old
    train_caps, train_ref = calls[0]
    check("fit reference is the training captures only",
          train_ref == train_caps and not any(
              Q.A.cell_number(c) > 47 for c in train_ref), calls[0])
    check("training captures are cells <= 47",
          sorted(Q.A.cell_number(c) for c in train_caps) == [3, 30, 47])
    check("scored reference is the full capture set",
          calls[1][1] == caps)
    check("report records the effective fit window",
          out["fit_window"] == {"first_cell": 1, "last_cell": 47,
                                "registered_last_cell": 47}, out)
    fp = out["provenance"]["fit"]
    check("fit provenance counts rebuilds and dropped captures",
          fp["realised_rebuilt"] == 1 and fp["dropped_no_ohlc_captures"]
          == 1 and fp["captures"] == 3
          and "training captures only" in fp["price_reference"], fp)
    check("training clusters recorded",
          out["training_clusters"]["day"] == 12, out)
    check("descriptive report has no verdict key", "verdict" not in out)
    q, n = Q.fit_q(training(), 50)
    clean = Q.make_report(res_with(10), q, n, 0, False, 47, {})
    check("clean report carries verdict", clean["verdict"] == "KEEP")
    txt = Q.render(res_with(10), q, n, 0, True, "t", 40)
    check("descriptive text has no verdict word or keep rule",
          "verdict" not in txt.lower() and "KEEP" not in txt, txt)
    check("fit cutoff is labelled in the text", "cells <= 40 only" in txt)
    check("clean text carries the keep rule",
          "KEEP RULE" in Q.render(res_with(10), q, n, 0, False, "t"))
    with tempfile.TemporaryDirectory() as t:
        o = os.path.join(t, "o.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rc2 = Q.main(["score", "--captures", t, "--min-cell", "48",
                          "--descriptive", "--json", o])
        check("no training rows writes no json",
              rc2 == 2 and not os.path.exists(o))


class Suite(unittest.TestCase):
    """Runs the checks under `unittest discover -s scripts`."""

    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def run_all():
    for fn in (test_constants, test_clusters_quantile, test_fit_q,
               test_score_rows, test_verdict, test_cell_selection,
               test_cli_guards, test_fit_reference_and_report):
        fn()


def main():
    run_all()
    print("test_resid_bootstrap_band: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
