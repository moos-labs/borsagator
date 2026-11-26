#!/usr/bin/env python3
"""Tests for benchmarks/audit_tilt_keep.py (INS-IMPROVE-001 round 23
item 1). Standalone, stdlib only, fixed synthetic pairs, assertions
through the tool's output. __main__ guard deliberate (#753 class)."""
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
    "atk", os.path.join(ROOT, "benchmarks", "audit_tilt_keep.py"))
K = importlib.util.module_from_spec(spec)
sys.modules["atk"] = K
spec.loader.exec_module(K)

TICK = ["T%d" % i for i in range(6)]


def pair(h, a, t, tilt, inr, naive=10.0):
    return {"ticker": t, "as_of": a, "horizon": h, "is_naive": naive,
            "is_tilt": tilt, "in_tilt": inr}


def fixture():
    ps = []
    # week: 5 cutoffs, tilt IS = 0.9 x naive everywhere, 5 of 6 in range
    for c in range(5):
        for i, t in enumerate(TICK):
            ps.append(pair("week", "w%d" % c, t, 9.0, i < 5))
    # month: 10 cutoffs, same shape
    for c in range(10):
        for i, t in enumerate(TICK):
            ps.append(pair("month", "m%02d" % c, t, 9.0, i < 5))
    # day: cutoff d0 carries all the skill (tilt IS 5), other four are
    # flat (tilt = naive); coverage alternates all-in / half-in
    for c in range(5):
        for i, t in enumerate(TICK):
            ps.append(pair("day", "d%d" % c, t, 5.0 if c == 0 else 10.0,
                           True if c % 2 == 0 else i < 3))
    return ps


def test_audit_values():
    res = K.audit(fixture(), reps=300, seed=7)
    w, m, d = res["week"], res["month"], res["day"]
    check("week skill 0.1", abs(w["range_skill"] - 0.1) < 1e-9, w)
    s = w["scorer"]
    check("week scorer legs", s["skill_leg"] and s["coverage_overlap_leg"],
          s)
    check("week fails the 10-cluster bar",
          w["cluster_bar"] == {"needed": 10, "met": False})
    check("month meets the 10-cluster bar", m["cluster_bar"]["met"])
    check("ticker view with equal tickers has lower 0.1",
          w["ticker_view"]["lower_gt_0"]
          and abs(w["ticker_view"]["skill_ci_ticker"][0] - 0.1) < 1e-9, w)
    check("cap passes on a zero-width coverage CI",
          w["cap"]["coverage_ci_ok"] and w["cap"]["coverage_ci_width"]
          < 1e-9, w["cap"])
    check("wide coverage CI fails the cap but overlaps",
          d["scorer"]["coverage_overlap_leg"]
          and not d["cap"]["coverage_ci_ok"]
          and d["cap"]["coverage_ci_width"] > 0.15, (d["scorer"], d["cap"]))
    check("jackknife of identical clusters", w["ci_audit"]["jackknife"][
        "pass"] and abs(w["ci_audit"]["jackknife"]["ci"][0] - 0.1) < 1e-9)
    check("sign-flip min p = 2^-k and unattainable at k = 5",
          abs(w["ci_audit"]["signflip"]["min_p"] - 1 / 32.0) < 1e-12
          and not w["ci_audit"]["signflip"]["pass"], w["ci_audit"]["signflip"])
    check("sign-flip passes at k = 10",
          m["ci_audit"]["signflip"]["pass"]
          and abs(m["ci_audit"]["signflip"]["p_one_sided"] - 1 / 1024.0)
          < 1e-9, m["ci_audit"]["signflip"])


def test_ticker_view_flags_one_ticker_carrying():
    ps = [pair("week", "w%d" % c, t, 5.0 if t == "T0" else 10.0, True)
          for c in range(5) for t in TICK]
    w = K.audit(ps, reps=400, seed=7)["week"]
    check("cutoff CI is positive but the ticker view reaches 0",
          w["scorer"]["skill_leg"] and not w["ticker_view"]["lower_gt_0"]
          and w["ticker_view"]["skill_ci_ticker"][0] <= 1e-9,
          (w["scorer"], w["ticker_view"]))


def test_leave_one_cutoff_out():
    d = K.audit(fixture(), reps=300, seed=7)["day"]
    check("day skill 0.1 carried by one cutoff",
          abs(d["range_skill"] - 0.1) < 1e-9)
    own = {o["as_of"]: o["range_skill"] for o in d["per_cutoff_skill"]}
    check("per-cutoff skill", abs(own["d0"] - 0.5) < 1e-9
          and abs(own["d1"]) < 1e-9, own)
    lo = {x["dropped"]: x for x in d["leave_one_cutoff_out"]}
    check("dropping the carrying cutoff removes the skill",
          abs(lo["d0"]["range_skill"]) < 1e-9 and lo["d0"]["clusters"] == 4,
          lo["d0"])
    check("dropping a flat cutoff raises it to 30/240",
          abs(lo["d1"]["range_skill"] - 0.125) < 1e-9, lo["d1"])
    check("one entry per cutoff", len(lo) == 5)


def test_main_output_no_verdict_and_filters():
    seen = {}
    orig = (K.A.find_captures, K.T.score_pairs)
    caps = ["/x/r__w5-backtest-436-cell80", "/x/r__nocell"]

    def fake_find(paths, mc):
        seen["min_cell"] = mc
        return caps
    K.A.find_captures = fake_find

    def fake_score(cs):
        seen["scored"] = list(cs)
        return fixture(), []
    K.T.score_pairs = fake_score
    out = io.StringIO()
    try:
        with tempfile.TemporaryDirectory() as d, \
                contextlib.redirect_stdout(out):
            js = os.path.join(d, "o.json")
            code = K.main(["--captures", "c", "--reps", "50",
                           "--json", js])
            res = json.load(open(js))
    finally:
        K.A.find_captures, K.T.score_pairs = orig
    check("exit 0 and min-cell 73 default", code == 0
          and seen["min_cell"] == 73, seen)
    check("unnumbered capture dropped before scoring",
          seen["scored"] == [caps[0]], seen)
    blob = (out.getvalue() + json.dumps(res)).lower()
    check("no verdict word or key", not any(
        w in blob for w in ("verdict", "keep", "reject", "adopt")))
    check("descriptive flag, note printed", res["descriptive"] is True
          and "unattainable" in out.getvalue())


def test_main_empty_horizon_does_not_crash():
    orig = (K.A.find_captures, K.T.score_pairs)
    K.A.find_captures = lambda paths, mc: ["/x/r__w5-backtest-436-cell80"]
    # day has no matured rows; week and month are populated
    K.T.score_pairs = lambda cs: (
        [p for p in fixture() if p["horizon"] != "day"], [])
    out = io.StringIO()
    try:
        with tempfile.TemporaryDirectory() as d, \
                contextlib.redirect_stdout(out):
            js = os.path.join(d, "o.json")
            code = K.main(["--captures", "c", "--reps", "50",
                           "--json", js])
            res = json.load(open(js))
    finally:
        K.A.find_captures, K.T.score_pairs = orig
    txt = out.getvalue()
    check("empty horizon: exit 0", code == 0)
    check("empty horizon: unavailable note printed",
          "no matured rows at this horizon" in txt
          and "sign-flip minimum p is unavailable" in txt)
    check("empty horizon: json min_p null, n 0",
          res["results"]["day"]["n"] == 0 and
          res["results"]["day"]["ci_audit"]["signflip"]["min_p"] is None)
    check("populated horizons keep the attainability note",
          txt.count("smallest attainable") == 2
          and "leg is unattainable" in txt and "leg is attainable" in txt,
          txt)


def main():
    for fn in (test_main_empty_horizon_does_not_crash,test_audit_values, test_ticker_view_flags_one_ticker_carrying,
               test_leave_one_cutoff_out,
               test_main_output_no_verdict_and_filters):
        fn()
    print("test_audit_tilt_keep: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
