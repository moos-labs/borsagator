"""Tests for benchmarks/screen_mpc_windows.py: fixed synthetic inputs."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
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


S = _load("screen_mpc_windows")
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL: %s %s" % (name, detail))


def test_constants():
    check("grid", S.M_GRID[0] == 0.70 and S.M_GRID[-1] == 1.50 and len(S.M_GRID) == 17)
    check("min group", S.MIN_GROUP == 5)
    check("train and clean cells", S.TRAIN_MAX_CELL == 47 and S.CLEAN_MIN_CELL == 91)
    check("sessions", S.SESSIONS == {"day": 1, "week": 5, "month": 21})


def test_window_end():
    # 2025-01-02 is a Thursday; next sessions Sun 5, Mon 6 ...
    check("Thursday + 1 session is Sunday", S.window_end("2025-01-02", 1) == "2025-01-05")
    check("Thursday + 5 sessions is next Thursday", S.window_end("2025-01-02", 5) == "2025-01-09")
    check("Sunday + 1 is Monday", S.window_end("2025-01-05", 1) == "2025-01-06")
    check("Wednesday + 2 skips Fri/Sat", S.window_end("2025-01-01", 2) == "2025-01-05")


def test_flag_boundaries():
    dates = ["2025-01-09"]
    check("decision on window end is in", S.flagged("2025-01-02", "week", dates))
    check("decision on cutoff day is out", not S.flagged("2025-01-09", "week", dates))
    check("decision one day after window end is out", not S.flagged("2025-01-01", "week", dates)
          or S.window_end("2025-01-01", 5) >= "2025-01-09")
    check("decision before cutoff is out", not S.flagged("2025-01-10", "week", dates))
    check("day window misses a decision 4 sessions out", not S.flagged("2025-01-02", "day", dates))
    check("month window catches it", S.flagged("2024-12-20", "month", dates))
    check("cutoff time part ignored", S.flagged("2025-01-02T00:00:00", "week", dates))


def _row(h, as_of, real, v2s=0.02, cell=1):
    return {"horizon": h, "as_of": as_of, "real": real, "v2_sigma": v2s, "mult": 1.0,
            "naive_half": 5.0, "ticker": "T", "cell": cell}


def test_fit_constraint_and_groups():
    dates = ["2025-01-09"]
    ev = [_row("week", "2025-01-02", 9.0) for _ in range(6)]
    ne = [_row("week", "2025-03-02", 0.5) for _ in range(6)]
    f = S.fit_horizon(ev + ne, "week", dates)
    check("fitted with enough rows", f["fitted"] and f["n_event"] == 6 and f["n_nonevent"] == 6)
    se = sum(S.v2_half(r) for r in ev)
    sn = sum(S.v2_half(r) for r in ne)
    check("mean-width constraint holds",
          abs(f["m_event"] * se + f["m_nonevent"] * sn - (se + sn)) < 1e-9)
    check("event moves larger so event width rises", f["m_event"] > 1.0 and f["m_nonevent"] < 1.0, str(f))
    f = S.fit_horizon(ev[:4] + ne, "week", dates)
    check("4 event rows is not fitted", not f["fitted"] and f["m_event"] == 1.0 and f["m_nonevent"] == 1.0)
    f = S.fit_horizon(ev + ne[:4], "week", dates)
    check("4 nonevent rows is not fitted", not f["fitted"])
    f = S.fit_horizon(ev[:5] + ne[:5], "week", dates)
    check("exactly 5 and 5 fits", f["fitted"])
    ne_small = [_row("week", "2025-03-02", 9.0) for _ in range(5)]
    f = S.fit_horizon([_row("week", "2025-01-02", 0.1) for _ in range(5)] + ne_small, "week", dates)
    check("m_event within grid", 0.70 <= f["m_event"] <= 1.50)


def test_fit_tie_goes_to_one():
    # every move far outside every band: Winkler IS is linear in width, so with the
    # mean-width constraint the objective is flat and the tie rule decides
    dates = ["2025-01-09"]
    rows = [_row("week", "2025-01-02", 1000.0) for _ in range(6)] + \
           [_row("week", "2025-03-02", 1000.0) for _ in range(6)]
    f = S.fit_horizon(rows, "week", dates)
    check("flat objective ties to multiplier 1", f["fitted"] and f["m_event"] == 1.0, str(f))


def test_score_rows_uses_frozen():
    dates = ["2025-01-09"]
    frozen = {"horizons": {h: {"m_event": 2.0, "m_nonevent": 0.5} for h in S.HORIZONS}}
    a = _row("week", "2025-01-02", 1.0)
    b = _row("week", "2025-03-02", 1.0)
    a["real"] = b["real"] = S.v2_half(a)
    out = S.score_rows([a, b], frozen, dates)
    check("event flag carried", out[0]["event"] and not out[1]["event"])
    v2 = S.v2_half(a)
    check("event multiplier applied", out[0]["in_ch"] is True)
    check("nonevent multiplier applied", out[1]["in_ch"] is False)
    check("group counts", S.group_counts(out)["week"] == {"event": 1, "nonevent": 1})


def test_counts_only():
    res = {h: {"n": 60, "cutoffs": 3, "ch": {"coverage": 0.123456, "range_skill": 0.654321},
               "v2": {"coverage": 0.222222, "range_skill": 0.333333},
               "ch_ci_cutoff": (-0.111111, 0.444444), "ch_cov_ci_cutoff": (0.55, 0.66)}
           for h in S.HORIZONS}
    counts = {h: {"event": 7, "nonevent": 9} for h in S.HORIZONS}
    v, why = S.loop_bar.loop_bar_verdict(res)
    text, payload = S.clean_report(res, counts, 91, v, why)
    blob = (text + json.dumps(payload)).lower()
    check("counts only verdict", v == "COUNTS ONLY")
    check("no metric words", not any(w in blob for w in ("coverage", "rangeskill", "range_skill", "ci_cutoff", "ci cutoff")))
    check("no metric numbers", not any(n in blob for n in ("0.123456", "0.654321", "0.222222", "0.333333", "0.111111", "0.444444")))
    check("counts kept", "event=7 nonevent=9" in text and payload["counts"]["day"]["event"] == 7)


def test_refusals():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = S.main(["score", "--captures", "/nonexistent", "--frozen", "x", "--min-cell", "90"])
    check("score refuses min-cell 90", rc == 2 and "score is for cells" in buf.getvalue())
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "f.json")
        open(out, "w").write("SENTINEL")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = S.main(["fit", "--captures", d + "/missing", "--out", out])
        check("fit refuses empty discovery", rc == 2 and "no captures" in buf.getvalue())
        check("fit leaves out untouched", open(out).read() == "SENTINEL")


def test_decisions_file():
    ds = S.load_dates()
    check("38 decisions", len(ds) == 38, str(len(ds)))
    check("sorted unique", ds == sorted(set(ds)))
    check("span", ds[0] == "2022-03-21" and ds[-1] == "2026-10-29")


def run_all():
    for fn in (test_constants, test_window_end, test_flag_boundaries, test_fit_constraint_and_groups, test_fit_tie_goes_to_one,
               test_score_rows_uses_frozen, test_counts_only, test_refusals, test_decisions_file):
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
    print("test_screen_mpc_windows: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
