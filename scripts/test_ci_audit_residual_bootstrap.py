#!/usr/bin/env python3
"""Tests for benchmarks/ci_audit_residual_bootstrap.py (INS-IMPROVE-001
round 9 item 2). Standalone, stdlib only, fixed synthetic inputs,
assertions through the tool's own output."""
import importlib.util
import io
import json
import os
import random
import sys
import tempfile
from contextlib import redirect_stdout

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
    "cirb", os.path.join(ROOT, "benchmarks",
                         "ci_audit_residual_bootstrap.py"))
C = importlib.util.module_from_spec(spec)
sys.modules["cirb"] = C
spec.loader.exec_module(C)

NH = 1.2816  # naive_half -> scale exactly 1.0
TRAIN = {"c1": [10.0, 10.5, 11.0], "c2": [20.0, 20.5, 21.0],
         "c3": [30.0, 30.5, 31.0]}


def row(h, a, tk, real):
    return {"horizon": h, "as_of": a, "ticker": tk, "real": real,
            "naive_half": NH, "mult": 1.0}


def train_rows(h="week"):
    return [row(h, a, "T%d" % i, v)
            for a, vs in TRAIN.items() for i, v in enumerate(vs)]


def test_whole_cluster_resampling():
    cl, ks = C.fit(train_rows())
    test = [row("week", "t1", "T%d" % i, 0.0) for i in range(3)]
    rng = random.Random(7)
    sets, signs, whole = set(), set(), True
    for _ in range(60):
        ps = C.synthetic_pairs(test, cl, ks, rng)
        reals = [p["real"] for p in ps]
        mags = tuple(sorted(abs(x) for x in reals))
        sets.add(mags)
        signs.add(tuple(sorted(set(x > 0 for x in reals))))
        if mags not in {tuple(v) for v in TRAIN.values()}:
            whole = False
    check("whole training cluster per test cluster", whole, sets)
    check("every training cluster is drawn", len(sets) == 3, sets)
    check("one sign per cluster, both signs occur",
          signs == {(True,), (False,)}, signs)


def test_individual_resampling_would_fail():
    # the same assertion on a per-residual draw is violated
    pool = [v for vs in TRAIN.values() for v in vs]
    rng = random.Random(7)
    bad = 0
    for _ in range(60):
        mags = tuple(sorted(rng.choice(pool) for _ in range(3)))
        if mags not in {tuple(v) for v in TRAIN.values()}:
            bad += 1
    check("per-residual draws break cluster preservation", bad > 30, bad)


def test_fit_uses_training_only_and_k_scale():
    cl, ks = C.fit(train_rows())
    check("fit k on large residuals is the grid maximum",
          ks["week"] == max(C.R.K_GRID), ks)
    check("horizon without training rows has no k", ks["day"] is None)
    check("clusters keyed by horizon and cutoff",
          sorted(cl["week"]) == ["c1", "c2", "c3"] and not cl["day"])


def test_audit_output_no_verdict_and_cluster_counts():
    tr = train_rows()
    te = [row("week", "t%d" % j, "T%d" % i, 5.0 * (1 if j % 2 else -1))
          for j in range(4) for i in range(3)]
    res = C.audit(tr, te, reps=20, inner=20, seed=3)
    w = res["week"]
    check("counts raw and clusters", w["train_rows"] == 9
          and w["train_clusters"] == 3 and w["test_rows"] == 12
          and w["test_clusters"] == 4 and w["defined"], w)
    check("day undefined, not a number", res["day"]["defined"] is False)
    blob = json.dumps(res).lower() + C.render(res, 20, 20).lower()
    check("no verdict key or word", "verdict" not in blob
          and "keep" not in blob and "adopt" not in blob)
    check("rates in [0,1]", all(0 <= w[k] <= 1 for k in
                                ("skill_leg_rate", "coverage_leg_rate",
                                 "both_legs_rate")))
    res2 = C.audit(tr, te, reps=20, inner=20, seed=3)
    check("fixed seed reproduces", res == res2)


def test_main_drops_unnumbered_and_splits_cells():
    seen = {}
    caps = ["/x/run__w5-backtest-436-cell5", "/x/run__w5-backtest-436-cell60",
            "/x/run__nocell"]
    orig = (C.A.find_captures, C.R.build_rows)

    def fake_find(paths, _):
        return caps

    def fake_build(cs, ref):
        seen.setdefault("calls", []).append(list(cs))
        return [], []
    C.A.find_captures, C.R.build_rows = fake_find, fake_build
    try:
        with redirect_stdout(io.StringIO()):
            with tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, "o.json")
                C.main(["--captures", "x", "--reps", "2",
                        "--inner-reps", "5", "--json", out])
                js = json.load(open(out))
    finally:
        C.A.find_captures, C.R.build_rows = orig
    calls = seen["calls"]
    check("train gets cell5 only", calls[0] == [caps[0]], calls)
    check("test gets cell60 only", calls[1] == [caps[1]], calls)
    check("unnumbered dropped", all(caps[2] not in c for c in calls))
    check("json descriptive flag, no verdict", js["descriptive"] is True
          and "verdict" not in json.dumps(js).lower())


def main():
    for fn in (test_whole_cluster_resampling,
               test_individual_resampling_would_fail,
               test_fit_uses_training_only_and_k_scale,
               test_audit_output_no_verdict_and_cluster_counts,
               test_main_drops_unnumbered_and_splits_cells):
        fn()
    print("test_ci_audit_residual_bootstrap: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
