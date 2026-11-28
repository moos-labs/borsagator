#!/usr/bin/env python3
"""Tests for benchmarks/score_tsfm_control.py (INS-IMPROVE-006 E).
Standalone, stdlib only.
"""
import importlib.util
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
    "tsfm", os.path.join(ROOT, "benchmarks", "score_tsfm_control.py"))
T = importlib.util.module_from_spec(spec)
sys.modules["tsfm"] = T
spec.loader.exec_module(T)

GOOD = {"model": "chronos-2", "base_date": "2025-11-14",
        "context_sessions": 750,
        "horizons": {"day": {"q10": -2.0, "q50": 0.1, "q90": 2.2},
                     "week": {"q10": -4.0, "q50": 0.2, "q90": 4.4},
                     "month": {"q10": -8.0, "q50": 0.3, "q90": 8.8}}}


def write(d, obj, model="chronos-2"):
    p = os.path.join(d, "collected", model)
    os.makedirs(p)
    with open(os.path.join(p, "quantiles.json"), "w") as f:
        json.dump(obj, f)


def test_constants():
    check("v2 pinned", T.ens_mod.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})
    check("clean cells", T.CLEAN_MIN_CELL == 91)


def test_load():
    with tempfile.TemporaryDirectory() as d:
        write(d, GOOD)
        check("loads", T.load_quantiles(d, "chronos-2") is not None)
        check("wrong model is None", T.load_quantiles(d, "timesfm") is None)
    with tempfile.TemporaryDirectory() as d:
        bad = json.loads(json.dumps(GOOD))
        bad["horizons"]["week"]["q90"] = -5.0
        write(d, bad)
        check("inverted quantiles rejected",
              T.load_quantiles(d, "chronos-2") is None)
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "collected", "chronos-2"))
        with open(os.path.join(d, "collected", "chronos-2",
                               "quantiles.json"), "w") as f:
            f.write("{not json")
        check("malformed is None", T.load_quantiles(d, "chronos-2") is None)


def test_band():
    check("half is (q90-q10)/2", abs(T.band_half(
        GOOD["horizons"]["day"]) - 2.1) < 1e-9)
    check("risk mult applied", abs(T.band_half(
        GOOD["horizons"]["day"], 2.0) - 4.2) < 1e-9)


def test_score_rows():
    r = {"ticker": "A", "as_of": "d", "horizon": "week", "real": 1.0,
         "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02,
         "tsfm_half": 4.0}
    p = T.score_rows([r])[0]
    check("scored", p["in_ch"])
    check("no band excluded", T.score_rows([dict(r, tsfm_half=None)]) == [])


def _run(args):
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = T.main(args)
    return rc, buf.getvalue()


def _row(t, d, h, real=1.0, centre=0.0):
    return {"ticker": t, "as_of": d, "horizon": h, "real": real,
            "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02,
            "tsfm_half": 4.0, "tsfm_centre": centre}


def test_constants_new():
    check("desc max", T.DESC_MAX_CELL == 90 and T.TRAIN_MAX_CELL == 47)
    check("origin rule", T.MIN_ORIGIN == "2025-10-20")


def test_centre_arm():
    r = _row("A", "2026-01-01", "week", real=5.0, centre=3.0)
    check("q50 centre covers", T.score_rows([r])[0]["in_ch"])
    r0 = _row("A", "2026-01-01", "week", real=5.0, centre=0.0)
    check("zero centre misses the same move", not T.score_rows([r0])[0]["in_ch"])
    edge = _row("A", "2026-01-01", "week", real=7.0, centre=3.0)
    check("coverage edge inclusive", T.score_rows([edge])[0]["in_ch"])
    edge2 = _row("A", "2026-01-01", "week", real=7.01, centre=3.0)
    check("just outside misses", not T.score_rows([edge2])[0]["in_ch"])
    a = T.score_rows([r])[0]["is_ch"]
    b = T.score_rows([dict(r, tsfm_centre=0.0)])[0]["is_ch"]
    check("interval score uses the centre", a != b, "%s %s" % (a, b))


def test_build_rows_centre():
    import tempfile
    q50 = json.loads(json.dumps(GOOD))
    old = T.R.build_rows
    T.R.build_rows = lambda caps, refs: ([{
        "ticker": "A", "as_of": "2026-01-01", "horizon": h, "real": 1.0,
        "naive_half": 5.0, "mult": 1.0, "v2_sigma": 0.02}
        for h in ("day", "week", "month")], [])
    try:
        with tempfile.TemporaryDirectory() as d:
            write(d, q50)
            rz, _ = T.build_rows([d], [d], "chronos-2", "zero")
            rq, _ = T.build_rows([d], [d], "chronos-2", "q50")
            check("zero arm centre 0", all(r["tsfm_centre"] == 0.0 for r in rz))
            check("q50 arm centre is q50",
                  sorted(r["tsfm_centre"] for r in rq) == [0.1, 0.2, 0.3])
            check("same half", [r["tsfm_half"] for r in rz] == [r["tsfm_half"] for r in rq])
        bad = json.loads(json.dumps(GOOD))
        bad["horizons"]["day"]["q50"] = 9.0
        with tempfile.TemporaryDirectory() as d:
            write(d, bad)
            rq, g = T.build_rows([d], [d], "chronos-2", "q50")
            rz, _ = T.build_rows([d], [d], "chronos-2", "zero")
            check("q50 outside q10..q90 excluded for the q50 arm only",
                  rq == [] and len(rz) == 3 and "excluded" in g[-1], str(g))
    finally:
        T.R.build_rows = old


def test_origin_filter():
    rows = [_row("A", "2025-10-20", "day"), _row("A", "2025-10-21", "day"),
            _row("B", "2025-10-19T00:00:00", "week")]
    keep, lines = T.origin_filter(rows, "2025-10-20")
    check("boundary date excluded, next day kept",
          [r["as_of"] for r in keep] == ["2025-10-21"])
    check("one line per dropped row", lines == [
        "excluded: row A 2025-10-20 day: origin not after 2025-10-20 (possible pretraining overlap)",
        "excluded: row B 2025-10-19 week: origin not after 2025-10-20 (possible pretraining overlap)"],
          str(lines))


def test_exclusion_lines():
    L = T.exclusion_lines(["c1: no usable chronos-2 quantiles for the zero arm, excluded", "n1: a note"],
                          ["excluded: row A 2025-10-20 day: x"], ["/x/a", "/x/b"])
    check("header counts", "1 capture(s)" in L[0] and "1 row(s)" in L[0]
          and "2 unnumbered" in L[0] and "1 note(s)" in L[0], L[0])
    check("each listed", L[1:5] == [
        "excluded: c1: no usable chronos-2 quantiles for the zero arm, excluded",
        "excluded: row A 2025-10-20 day: x",
        "excluded: capture /x/a: no cell number, never scored",
        "excluded: capture /x/b: no cell number, never scored"], str(L))
    check("note last", L[5] == "note: n1: a note" and len(L) == 6)


def test_count_lines():
    rows = [_row("A", "2026-01-01", "day"), _row("B", "2026-01-01", "day"),
            _row("A", "2026-01-02", "day"), _row("A", "2026-01-03", "day"),
            _row("A", "2026-01-01", "week")]
    L = T.count_lines(rows)
    check("day: 4 rows, 3 clusters, 2 tickers", L[0] == "day: rows=4 cutoff clusters=3 tickers=2", L[0])
    check("week: 1 row, 1 cluster, 1 ticker", L[1] == "week: rows=1 cutoff clusters=1 tickers=1", L[1])
    check("month empty", L[2] == "month: rows=0 cutoff clusters=0 tickers=0")


def test_refusals():
    for lo, hi in ((47, 90), (48, 91), (60, 50), (0, 90), (48, 500), (91, 102)):
        rc, o = _run(["describe", "--captures", "/nonexistent",
                      "--min-cell", str(lo), "--max-cell", str(hi)])
        check("describe refuses %d-%d" % (lo, hi), rc == 2 and "describe needs 48 <=" in o, o[:100])
    for lo, hi in ((48, 90), (48, 48), (90, 90)):
        rc, o = _run(["describe", "--captures", "/nonexistent",
                      "--min-cell", str(lo), "--max-cell", str(hi)])
        check("describe validates %d-%d" % (lo, hi), "describe needs" not in o)
    rc, o = _run(["score", "--captures", "/nonexistent", "--min-cell", "90"])
    check("score refuses cell 90 (boundary)", rc == 2 and "score is for cells >= 91" in o)
    rc, o = _run(["score", "--captures", "/nonexistent", "--min-cell", "91"])
    check("score accepts cell 91", "score is for cells" not in o)
    rc, o = _run(["score", "--captures", "/nonexistent", "--min-cell", "73"])
    check("score refuses seen cells", rc == 2 and "score is for cells >= 91" in o)
    rc, o = _run(["score", "--captures", "/nonexistent", "--min-origin", "2025-10-19"])
    check("origin cannot move earlier", rc == 2 and "min-origin" in o)
    rc, o = _run(["describe", "--captures", "/nonexistent", "--min-origin", "2024-01-01"])
    check("describe origin cannot move earlier", rc == 2)


class _Mock:
    def __init__(self, cells, rows_fn):
        self.cells, self.rows_fn = cells, rows_fn
        self.seen = []

    def __enter__(self):
        self.old = (T.A.find_captures, T.A.cell_number, T.build_rows)
        T.A.find_captures = lambda dirs, mc: list(self.cells)
        T.A.cell_number = lambda c: self.cells[c]

        def fake(caps, allc, model, centre="zero"):
            self.seen.append((list(caps), centre))
            return self.rows_fn(caps), []
        T.build_rows = fake
        return self

    def __exit__(self, *a):
        T.A.find_captures, T.A.cell_number, T.build_rows = self.old


def _rows_for(caps):
    out = []
    for c in caps:
        for h in ("day", "week", "month"):
            out.append(_row("T", "2026-01-%02d" % (int(c[-2:]) % 28 + 1), h))
    return out


def test_describe_cell_window_and_counts_first():
    cells = {"/c/c47": 47, "/c/c48": 48, "/c/c90": 90, "/c/c91": 91, "/c/cNone": None}
    with _Mock(cells, _rows_for) as m:
        rc, o = _run(["describe", "--captures", "x", "--reps", "20"])
        check("describe ok", rc == 0, o[:200])
        check("describe sends only 48-90 captures",
              sorted(m.seen[0][0]) == ["/c/c48", "/c/c90"], str(m.seen))
        check("counts printed before the descriptive block",
              o.index("COUNTS") < o.index("DESCRIPTIVE ONLY"))
        check("unnumbered capture listed",
              "excluded: capture /c/cNone: no cell number, never scored" in o)
        check("centre passed through", m.seen[0][1] == "zero")
        rc, o = _run(["describe", "--captures", "x", "--reps", "20", "--centre", "q50"])
        check("q50 centre reaches build_rows", m.seen[-1][1] == "q50")


def test_score_counts_only_below_ten_clusters():
    import tempfile
    cells = {"/c/c91": 91, "/c/c95": 95, "/c/c20": 20}
    with _Mock(cells, _rows_for) as m:
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.json")
            rc, o = _run(["score", "--captures", "x", "--reps", "20", "--json", out])
            data = json.load(open(out))
        check("score ok", rc == 0)
        check("only cells >= 91 reach build_rows", sorted(m.seen[0][0]) == ["/c/c91", "/c/c95"])
        check("COUNTS ONLY printed", "COUNTS ONLY" in o)
        check("no coverage, skill or CI printed",
              not any(w in o for w in ("coverage", "RangeSkill", "CI cutoff", "KEEP RULE")), o)
        check("json has counts and no results",
              "results" not in data and data["verdict"] == "COUNTS ONLY" and "counts" in data)


def test_score_reads_with_ten_clusters():
    def rows(caps):
        out = []
        for k in range(10):
            for t in ("A", "B", "C", "D", "E", "F"):
                for h in ("day", "week", "month"):
                    out.append(dict(_row(t, "2026-02-%02d" % (k + 1), h, real=(k % 3) - 1.0), tsfm_half=4.0))
        return out
    cells = {"/c/c91": 91}
    with _Mock(cells, rows) as m:
        rc, o = _run(["score", "--captures", "x", "--reps", "50"])
    check("score with 10 clusters prints a verdict", rc == 0 and "KEEP RULE: " in o and "COUNTS ONLY" not in o, o[:300])
    check("verdict is KEEP or REJECT", "KEEP RULE: KEEP" in o or "KEEP RULE: REJECT" in o)


def run_all():
    for fn in (test_constants, test_load, test_band, test_score_rows,
               test_constants_new, test_centre_arm, test_build_rows_centre,
               test_origin_filter, test_exclusion_lines, test_count_lines, test_refusals,
               test_describe_cell_window_and_counts_first,
               test_score_counts_only_below_ten_clusters,
               test_score_reads_with_ten_clusters):
        fn()
    print("test_tsfm_control: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    return CHECKS["fail"]


import unittest  # noqa: E402


class Suite(unittest.TestCase):
    def test_all(self):
        CHECKS["pass"] = CHECKS["fail"] = 0
        self.assertEqual(run_all(), 0)


def main():
    sys.exit(1 if run_all() else 0)


if __name__ == "__main__":
    main()
