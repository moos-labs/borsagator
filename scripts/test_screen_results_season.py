"""Tests for benchmarks/screen_results_season.py: fixed synthetic inputs."""
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


S = _load("screen_results_season")
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


SEASON = [("2025-01-09", "2025-01-16")]


def test_flag_boundaries():
    # season Jan 9 to Jan 16. 2025-01-02 is a Thursday: week window ends Thu Jan 9.
    check("window end on season start flags", S.flagged("2025-01-02", "week", SEASON))
    check("window ending a day before season start does not", not S.flagged("2025-01-01", "week", SEASON)
          or S.window_end("2025-01-01", 5) >= "2025-01-09")
    check("window ending one session before season start is out", not S.flagged("2024-12-31", "week", SEASON))
    check("cutoff on the season end date is out (window starts after it)", not S.flagged("2025-01-16", "day", SEASON))
    check("cutoff the day before season end flags", S.flagged("2025-01-15", "day", SEASON))
    check("cutoff after the season is out", not S.flagged("2025-01-17", "week", SEASON))
    check("day window misses a season 4 sessions out", not S.flagged("2025-01-02", "day", SEASON))
    check("month window reaches it", S.flagged("2024-12-20", "month", SEASON))
    check("cutoff time part ignored", S.flagged("2025-01-02T00:00:00", "week", SEASON))


def test_load_season():
    se = S.load_season()
    check("constants", S.QUARTER_DAYS == 45 and S.ANNUAL_DAYS == 90)
    check("four periods per year, 2022 to 2027", len(se) == 24 and se == sorted(se))
    d = dict(se)
    check("Q1: Apr 1 to May 15 (45 days)", d["2025-04-01"] == "2025-05-15")
    check("Q2: Jul 1 to Aug 14", d["2025-07-01"] == "2025-08-14")
    check("Q3: Oct 1 to Nov 14", d["2025-10-01"] == "2025-11-14")
    check("year end: Jan 1 to Mar 31 (90 days)", d["2026-01-01"] == "2026-03-31")
    check("2024 leap year year end: Jan 1 to Mar 30", d["2025-01-01"] == "2025-03-31" and d["2024-01-01"] == "2024-03-30")
    check("parameters override", dict(S.load_season(60, 91))["2025-04-01"] == "2025-05-30")


def test_cutoff_structure():
    se = S.load_season()
    cut = ["2023-12-29", "2024-03-31", "2024-06-30", "2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30",
           "2025-08-15", "2025-09-30", "2025-11-14", "2025-12-31", "2026-02-13", "2026-03-31", "2026-05-15",
           "2026-06-30", "2026-08-14", "2026-09-30"]
    n = {h: sum(S.flagged(c, h, se) for c in cut) for h in S.HORIZONS}
    check("pre-registered structural counts 12/13/13 of 17", n == {"day": 12, "week": 13, "month": 13}, str(n))
    check("2025-08-15 unflagged at every horizon", not any(S.flagged("2025-08-15", h, se) for h in S.HORIZONS))
    check("2024-03-31 flagged at every horizon", all(S.flagged("2024-03-31", h, se) for h in S.HORIZONS))


def _row(h, as_of, real, v2s=0.02, cell=1):
    return {"horizon": h, "as_of": as_of, "real": real, "v2_sigma": v2s, "mult": 1.0,
            "naive_half": 5.0, "ticker": "T", "cell": cell}


def test_fit_constraint_and_groups():
    dates = SEASON
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
    dates = SEASON
    rows = [_row("week", "2025-01-02", 1000.0) for _ in range(6)] + \
           [_row("week", "2025-03-02", 1000.0) for _ in range(6)]
    f = S.fit_horizon(rows, "week", dates)
    check("flat objective ties to multiplier 1", f["fitted"] and f["m_event"] == 1.0, str(f))


def test_score_rows_uses_frozen():
    dates = SEASON
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


def test_exclusions_listed():
    L = S.exclusion_lines(["cap1: no usable pre-cutoff OHLC history", "cap2: scoring failed: x",
                           "cap3: realised window rebuilt to 21 sessions from price.csv"],
                          ["T 2025-01-02 week", "U 2025-01-02 day", "V 2025-01-02 month"], ["/x/a", "/x/b"])
    check("header counts", "2 capture(s) dropped" in L[0] and "3 row(s) without a v2 sigma" in L[0]
          and "2 unnumbered" in L[0] and "1 note(s)" in L[0], L[0])
    check("each drop listed with reason", L[1:3] == ["excluded: cap1: no usable pre-cutoff OHLC history",
                                                    "excluded: cap2: scoring failed: x"])
    check("each row without sigma listed", L[3:6] == ["excluded: row %s: no v2 sigma" % x for x in (
        "T 2025-01-02 week", "U 2025-01-02 day", "V 2025-01-02 month")], str(L))
    check("each unnumbered capture listed", L[6:8] == [
        "excluded: capture /x/a: no cell number, never scored", "excluded: capture /x/b: no cell number, never scored"])
    check("rebuild note is a note, last", L[8] == "note: cap3: realised window rebuilt to 21 sessions from price.csv" and len(L) == 9)
    check("no gaps still prints header", len(S.exclusion_lines([], [], [])) == 1)
    check("row id", S.row_id({"ticker": "T", "as_of": "2025-01-02T00:00:00", "horizon": "week"}) == "T 2025-01-02 week")


def _run(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = S.main(args)
    return rc, buf.getvalue()


def test_describe_range_guard():
    check("default max-cell is 90", S.DESC_MAX_CELL == 90)
    for lo, hi in ((47, 90), (48, 91), (60, 50), (0, 90), (48, 500), (91, 102), (48, 102)):
        rc, o = _run(["describe", "--captures", "/nonexistent", "--frozen", "x",
                      "--min-cell", str(lo), "--max-cell", str(hi)])
        check("describe refuses %d-%d" % (lo, hi), rc == 2 and "describe needs 48 <= min-cell" in o, o[:120])
    for lo, hi in ((48, 90), (48, 48), (90, 90)):
        rc, o = _run(["describe", "--captures", "/nonexistent", "--frozen", "x",
                      "--min-cell", str(lo), "--max-cell", str(hi)])
        check("describe passes validation %d-%d" % (lo, hi), "describe needs" not in o and "no captures" in o, o[:120])
    rc, o = _run(["describe", "--captures", "/nonexistent", "--frozen", "x"])
    check("default range passes validation", "describe needs" not in o and "no captures" in o, o[:120])


def test_describe_never_scores_clean_cells():
    old = (S.A.find_captures, S.R.build_rows, S.A.cell_number, S.R.evaluate)
    seen = []
    S.A.find_captures = lambda dirs, mc: ["/x/c60", "/x/c95"]
    S.A.cell_number = lambda p: {"/x/c60": 60, "/x/c95": 95}[p]
    S.R.build_rows = lambda caps, refs: (seen.append(list(caps)) or [], [])
    S.R.evaluate = lambda pairs, reps: {h: {"n": 0, "cutoffs": 0, "ch": {"coverage": None, "range_skill": None},
                                          "v2": {"coverage": None, "range_skill": None},
                                          "ch_ci_cutoff": (None, None), "ch_cov_ci_cutoff": (None, None)} for h in S.HORIZONS}
    try:
        with tempfile.TemporaryDirectory() as d:
            fz = os.path.join(d, "f.json")
            json.dump({"frozen": {"horizons": {h: {"m_event": 1.0, "m_nonevent": 1.0} for h in S.HORIZONS}}}, open(fz, "w"))
            rc, o = _run(["describe", "--captures", "x", "--frozen", fz, "--reps", "5"])
            check("describe default run ok", rc == 0, o[:200])
            check("describe passes only cell 60 to build_rows, never 95", seen == [["/x/c60"]], str(seen))
    finally:
        S.A.find_captures, S.R.build_rows, S.A.cell_number, S.R.evaluate = old


def test_modes_print_gap_list():
    # run the three modes with mocked discovery and build_rows that returns a gap
    old = (S.A.find_captures, S.R.build_rows, S.A.cell_number)
    S.A.find_captures = lambda dirs, mc: ["/x/2024-06-30/T-cell5", "/x/2024-06-30/U"]
    S.A.cell_number = lambda p: 5 if "cell5" in p else None
    rows = [_row("week", "2025-01-02", 1.0, cell=5)] * 6 + [_row("week", "2025-03-02", 1.0, cell=5)] * 6
    rows.append({**_row("week", "2025-03-02", 1.0), "v2_sigma": None})
    S.R.build_rows = lambda caps, refs: (rows, ["/x/2024-06-30/T: no usable pre-cutoff OHLC history"])
    try:
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "f.json")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = S.main(["fit", "--captures", "x", "--out", out])
            fit_out = buf.getvalue()
            check("fit ok", rc == 0)
            check("fit prints gap and dropped row", "excluded: /x/2024-06-30/T: no usable pre-cutoff OHLC history" in fit_out
                  and "1 row(s) without a v2 sigma" in fit_out and "1 unnumbered" in fit_out
                  and "excluded: row T 2025-03-02 week: no v2 sigma" in fit_out
                  and "excluded: capture /x/2024-06-30/U: no cell number, never scored" in fit_out, fit_out[-400:])
            for mode, extra in (("describe", []), ("score", [])):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = S.main([mode, "--captures", "x", "--frozen", out, "--reps", "5"] + extra)
                o = buf.getvalue()
                check("%s ok" % mode, rc == 0, o[:200])
                check("%s prints gap list" % mode, "excluded: /x/2024-06-30/T: no usable pre-cutoff OHLC history" in o, o[-300:])
                check("%s counts dropped rows" % mode, "1 row(s) without a v2 sigma" in o, o[-300:])
                check("%s lists the row and the unnumbered capture" % mode,
                      "excluded: row T 2025-03-02 week: no v2 sigma" in o
                      and "excluded: capture /x/2024-06-30/U: no cell number, never scored" in o, o[-400:])
    finally:
        S.A.find_captures, S.R.build_rows, S.A.cell_number = old


def run_all():
    for fn in (test_constants, test_window_end, test_flag_boundaries, test_fit_constraint_and_groups, test_fit_tie_goes_to_one,
               test_score_rows_uses_frozen, test_counts_only, test_refusals, test_exclusions_listed, test_describe_range_guard, test_describe_never_scores_clean_cells, test_modes_print_gap_list, test_load_season, test_cutoff_structure):
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
    print("test_screen_results_season: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
