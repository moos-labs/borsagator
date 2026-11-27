"""Tests for benchmarks/replay_aci_lever.py and loop_bar.py: fixed synthetic inputs."""
import contextlib
import importlib.util
import io
import json
import tempfile
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "benchmarks")
sys.path.insert(0, BENCH)
sys.path.insert(0, HERE)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(BENCH, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


L = _load("replay_aci_lever")
LB = _load("loop_bar")
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL: %s %s" % (name, detail))


def T(cov, sk):
    return {"coverage": cov, "range_skill": sk}


def test_grid_registered():
    check("grid", L.ALPHA_GRID == (0.15, 0.20, 0.25, 0.30))
    check("train max cell", L.TRAIN_MAX_CELL == 47)
    check("clean min cell", L.CLEAN_MIN_CELL == 91)
    check("min clusters", LB.MIN_CLUSTERS == 10)


def test_select():
    t = {0.15: T(0.90, 0.30), 0.20: T(0.84, 0.10), 0.25: T(0.80, 0.20), 0.30: T(0.70, 0.50)}
    check("best in-band skill", L.select_alpha(t) == 0.25)
    t = {0.15: T(0.85, 0.10), 0.20: T(0.80, 0.10)}
    check("tie goes to larger alpha", L.select_alpha(t) == 0.20)
    t = {0.15: T(0.75, 0.10), 0.30: T(0.85, 0.05)}
    check("band edges inclusive", L.select_alpha(t) == 0.15)
    t = {0.15: T(0.7499, 0.9), 0.20: T(0.8501, 0.9)}
    check("just outside band falls to closest", L.select_alpha(t) in (0.15, 0.20))
    t = {0.15: T(0.95, 0.9), 0.20: T(0.90, 0.9), 0.25: T(0.88, 0.9)}
    check("none in band: closest to 0.80", L.select_alpha(t) == 0.25)
    t = {0.15: T(0.70, 0.9), 0.30: T(0.90, 0.9)}
    check("equidistant closest: larger alpha", L.select_alpha(t) == 0.30)
    check("empty", L.select_alpha({0.15: T(None, None)}) is None)


def _cell(n, cut, lo, cci, cov=0.8, sk=0.1):
    return {"n": n, "cutoffs": cut, "ch": {"coverage": cov, "range_skill": sk},
            "ch_ci_cutoff": (lo, lo + 0.1), "ch_cov_ci_cutoff": cci}


def _res(cut=10, lo=0.01, cci=(0.74, 0.86)):
    return {h: _cell(60, cut, lo, cci) for h in LB.HORIZONS}


def test_loop_bar():
    v, _ = LB.loop_bar_verdict(_res())
    check("all pass is KEEP", v == "KEEP")
    v, _ = LB.loop_bar_verdict(_res(cut=9))
    check("9 clusters is counts only", v == "COUNTS ONLY")
    v, _ = LB.loop_bar_verdict(_res(lo=0.0))
    check("lower bound 0 is REJECT", v == "REJECT")
    v, _ = LB.loop_bar_verdict(_res(lo=1e-6))
    check("lower bound just above 0 passes", v == "KEEP")
    v, _ = LB.loop_bar_verdict(_res(cci=(0.80, 0.96)))
    check("cov CI wider than 0.15 is REJECT", v == "REJECT")
    v, _ = LB.loop_bar_verdict(_res(cci=(0.86, 0.90)))
    check("cov CI not overlapping is REJECT", v == "REJECT")
    v, _ = LB.loop_bar_verdict(_res(cci=(0.70, 0.75)))
    check("cov CI touching 0.75 passes", v == "KEEP")
    r = _res()
    r["week"] = _cell(60, 10, -0.1, (0.74, 0.86))
    v, why = LB.loop_bar_verdict(r)
    check("one horizon failing rejects", v == "REJECT" and len(why) == 1)
    r = _res()
    r["month"]["cutoffs"] = 3
    v, _ = LB.loop_bar_verdict(r)
    check("one short horizon is counts only", v == "COUNTS ONLY")


def test_alpha_restored_and_applied():
    seen = []
    orig = L.C.score_rows
    L.C.score_rows = lambda rows, pred: seen.append(L.C.ALPHA) or []
    before = L.C.ALPHA
    try:
        old_eval = L.R.evaluate
        L.R.evaluate = lambda p, reps, seed: {}
        L.run_alpha([], 0.27, None, 5)
    finally:
        L.C.score_rows = orig
        L.R.evaluate = old_eval
    check("alpha applied during run", seen == [0.27])
    check("alpha restored after run", L.C.ALPHA == before)


def test_score_refuses_training_cells():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = L.main(["score", "--selected", os.path.join(BENCH, "..", "evaluation", "aci_lever_selected.json"), "--captures", "/nonexistent",
                     "--min-cell", "90"])
    check("score refuses min-cell below 91", rc == 2 and "refusing" in buf.getvalue())


def test_counts_only_emits_no_metrics():
    res = _res(cut=3)
    for h in LB.HORIZONS:
        res[h]["v2"] = {"coverage": 0.123456, "range_skill": 0.654321}
        res[h]["ch_ci_cutoff"] = (-0.111111, 0.222222)
    v, why = LB.loop_bar_verdict(res)
    text, payload = L.clean_report(res, {"day": 0.3, "week": 0.3, "month": 0.3}, 91, v, why)
    blob = (text + json.dumps(payload)).lower()
    check("counts-only verdict", v == "COUNTS ONLY" and payload["verdict"] == "COUNTS ONLY")
    check("counts-only has no coverage/skill/CI words",
          not any(w in blob for w in ("coverage", "rangeskill", "range_skill", "ci_cutoff", "ci cutoff")), blob)
    check("counts-only has no metric numbers", not any(n in blob for n in ("0.123456", "0.654321", "0.111111", "0.222222", "0.8")))
    check("counts-only keeps counts and reasons",
          payload["counts"]["day"] == {"n": 60, "cutoffs": 3} and len(payload["reasons"]) == 3 and "cutoffs=3" in text)
    res = _res(cut=10)
    for h in LB.HORIZONS:
        res[h]["v2"] = {"coverage": 0.7, "range_skill": 0.0}
    v, why = LB.loop_bar_verdict(res)
    text, payload = L.clean_report(res, {}, 91, v, why)
    check("scorable run still reports metrics", "coverage" in text and "results" in payload)


def test_fit_refuses_empty_captures():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "sel.json")
        open(out, "w").write("SENTINEL")
        empty = os.path.join(d, "empty")
        os.makedirs(empty)
        for caps in (empty, os.path.join(d, "missing")):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = L.main(["fit", "--captures", caps, "--out", out])
            check("fit refuses %s" % os.path.basename(caps), rc == 2 and "refusing" in buf.getvalue())
            check("fit leaves out file untouched", open(out).read() == "SENTINEL")


def run_all():
    for fn in (test_grid_registered, test_select, test_loop_bar,
               test_alpha_restored_and_applied, test_score_refuses_training_cells, test_counts_only_emits_no_metrics,
               test_fit_refuses_empty_captures):
        fn()


class Suite(unittest.TestCase):
    def test_checks(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        run_all()
        self.assertEqual(CHECKS["fail"], 0)
        self.assertGreater(CHECKS["pass"], 0)


def main():
    CHECKS["pass"] = CHECKS["fail"] = 0
    run_all()
    print("test_aci_lever: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
