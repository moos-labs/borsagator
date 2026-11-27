"""Tests for benchmarks/score_regime_tilt.py: fixed synthetic inputs."""
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


S = _load("score_regime_tilt")
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL: %s %s" % (name, detail))


def _dec(date, bps):
    return {"published_date": date, "change_bps": bps, "source_url": "u", "source_name": "n"}


# tightening from 2024-01-10, easing from 2024-06-10, hold from 2024-09-10
DECS = [_dec("2024-01-10", 100.0), _dec("2024-06-10", -100.0), _dec("2024-09-10", 0.0)]
D_TIGHT, D_EASE, D_HOLD = "2024-02-01", "2024-07-01", "2024-10-01"


def _row(h, as_of, frac=None, v2s=0.02):
    r = {"horizon": h, "as_of": as_of, "real": 0.0, "v2_sigma": v2s, "mult": 1.0,
         "naive_half": 5.0, "ticker": "T"}
    if frac is not None:
        r["real"] = frac * S.v2_half(r)
    return r


def test_constants():
    check("grid", S.W_GRID == (0.9, 1.0, 1.1))
    check("clip bounds", S.W_MIN == 0.9 and S.W_MAX == 1.1)
    check("clip applied", S.clip(0.5) == 0.9 and S.clip(2.0) == 1.1 and S.clip(1.0) == 1.0)
    check("min group", S.MIN_GROUP == 5)
    check("cells", S.TRAIN_MAX_CELL == 47 and S.CLEAN_MIN_CELL == 91 and S.DESC_MAX_CELL == 90)
    check("regimes", set(S.REGIMES) == {"tightening", "easing", "hold"})


def test_regime_boundaries():
    g = lambda d: S.regime_of({"as_of": d}, DECS)
    check("before first decision has none", g("2024-01-09") is None)
    check("decision day itself does not count (next session)", g("2024-01-10") is None)
    check("day after counts", g("2024-01-11") == "tightening")
    check("easing", g(D_EASE) == "easing")
    check("hold", g(D_HOLD) == "hold")
    check("time part ignored", g("2024-01-11T00:00:00") == "tightening")
    check("decision day with time part still not counted", g("2024-01-10T00:00:00") is None)


def _grp(h, as_of, frac, n):
    return [_row(h, as_of, frac) for _ in range(n)]


def test_fit_picks_per_regime():
    rows = (_grp("week", D_TIGHT, 0.5, 6) + _grp("week", D_EASE, 1.05, 6) + _grp("week", D_HOLD, 0.97, 6))
    f = S.fit_horizon(rows, "week", DECS)
    check("all fitted", all(f[g]["fitted"] and f[g]["n"] == 6 for g in S.REGIMES), str(f))
    check("deep inside band narrows to 0.9", f["tightening"]["w"] == 0.9, str(f))
    check("just outside band widens to 1.1", f["easing"]["w"] == 1.1, str(f))
    check("inside close to edge keeps 1.0", f["hold"]["w"] == 1.0, str(f))
    check("other horizon untouched", S.fit_horizon(rows, "day", DECS)["easing"]["n"] == 0)


def test_fit_min_group_and_tie():
    rows = _grp("week", D_TIGHT, 0.5, 4) + _grp("week", D_EASE, 0.5, 5)
    f = S.fit_horizon(rows, "week", DECS)
    check("4 rows not fitted, w stays 1.0", not f["tightening"]["fitted"] and f["tightening"]["w"] == 1.0)
    check("exactly 5 fits", f["easing"]["fitted"] and f["easing"]["w"] == 0.9)
    old = S.R.row_is
    S.R.row_is = lambda row, half: 1.0
    try:
        f = S.fit_horizon(_grp("week", D_TIGHT, 0.5, 6), "week", DECS)
    finally:
        S.R.row_is = old
    check("flat objective ties to 1.0", f["tightening"]["fitted"] and f["tightening"]["w"] == 1.0, str(f))


def test_fit_uses_only_given_rows_and_skips_no_sigma():
    rows = _grp("week", D_TIGHT, 0.5, 5) + [{**_row("week", D_TIGHT, 0.5), "v2_sigma": None}]
    f = S.fit_horizon(rows, "week", DECS)
    check("row without sigma not counted", f["tightening"]["n"] == 5)


def test_score_rows_uses_frozen():
    frozen = {"horizons": {h: {"tightening": {"w": 0.9}, "easing": {"w": 1.1}, "hold": {"w": 1.0}}
                           for h in S.HORIZONS}}
    a = _row("week", D_TIGHT, 0.95)
    b = _row("week", D_EASE, 1.05)
    c = _row("week", "2023-01-01", 0.5)
    out = S.score_rows([a, b, c], frozen, DECS)
    check("tightening 0.9 excludes 0.95 of v2", out[0]["regime"] == "tightening" and out[0]["in_ch"] is False and out[0]["in_v2"] is True)
    check("easing 1.1 includes 1.05 of v2", out[1]["regime"] == "easing" and out[1]["in_ch"] is True and out[1]["in_v2"] is False)
    check("no regime keeps v2 exactly", out[2]["regime"] == "none" and out[2]["is_ch"] == out[2]["is_v2"])
    check("group counts", S.group_counts(out)["week"] == {"tightening": 1, "easing": 1, "none": 1})
    e = _row("week", D_HOLD, 1.0)
    check("real exactly on the band edge is inside", S.score_rows([e], frozen, DECS)[0]["in_ch"] is True)
    check("no-sigma row skipped", S.score_rows([{**a, "v2_sigma": None}], frozen, DECS) == [])


def test_regime_counts_and_degenerate():
    rows = [_row(h, d) for h in S.HORIZONS for d in (D_TIGHT, D_TIGHT, "2024-02-02")]
    c = S.regime_counts(rows, DECS)
    check("rows and cutoffs", c["week"]["tightening"] == {"rows": 3, "cutoffs": 2}, str(c))
    check("single regime is degenerate", S.degenerate(c))
    L = S.count_lines("TITLE", c)
    check("title first, degenerate said", L[0] == "TITLE" and any("TILT DEGENERATE" in x for x in L))
    c2 = S.regime_counts(rows + [_row(h, D_EASE) for h in S.HORIZONS], DECS)
    check("two regimes not degenerate", not S.degenerate(c2))
    check("no degenerate line then", not any("DEGENERATE" in x for x in S.count_lines("T", c2)))
    c3 = S.regime_counts([_row("week", "2023-01-01")], DECS)
    check("no regime counted as none, and not degenerate-by-none",
          c3["week"]["none"]["rows"] == 1 and S.degenerate(c3))


def test_counts_only():
    res = {h: {"n": 60, "cutoffs": 3, "ch": {"coverage": 0.123456, "range_skill": 0.654321},
               "v2": {"coverage": 0.222222, "range_skill": 0.333333},
               "ch_ci_cutoff": (-0.111111, 0.444444), "ch_cov_ci_cutoff": (0.55, 0.66)}
           for h in S.HORIZONS}
    counts = {h: {"easing": 7, "hold": 9} for h in S.HORIZONS}
    v, why = S.loop_bar.loop_bar_verdict(res)
    text, payload = S.clean_report(res, counts, 91, v, why)
    blob = (text + json.dumps(payload)).lower()
    check("counts only verdict", v == "COUNTS ONLY")
    check("no metric words", not any(w in blob for w in ("coverage", "rangeskill", "range_skill", "ci_cutoff", "ci cutoff")))
    check("no metric numbers", not any(n in blob for n in ("0.123456", "0.654321", "0.222222", "0.333333", "0.111111", "0.444444")))
    check("counts kept", "'easing': 7" in text and payload["counts"]["day"]["by_regime"]["hold"] == 9)


def test_exclusions_listed():
    L = S.exclusion_lines(["cap1: no usable pre-cutoff OHLC history",
                           "cap3: realised window rebuilt to 21 sessions from price.csv"], 3, 2)
    check("header counts", "1 capture(s) dropped" in L[0] and "3 row(s) without a v2 sigma" in L[0]
          and "2 unnumbered" in L[0] and "1 note(s)" in L[0], L[0])
    check("drop and note lines", L[1] == "excluded: cap1: no usable pre-cutoff OHLC history"
          and L[2].startswith("note: cap3"))


def _run(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = S.main(args)
    return rc, buf.getvalue()


def test_refusals():
    rc, o = _run(["score", "--captures", "/nonexistent", "--frozen", "x", "--min-cell", "90"])
    check("score refuses min-cell 90", rc == 2 and "score is for cells" in o)
    rc, o = _run(["describe", "--captures", "/nonexistent", "--frozen", "x", "--min-cell", "47"])
    check("describe refuses training cell", rc == 2 and "after training cell" in o)
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "f.json")
        open(out, "w").write("SENTINEL")
        rc, o = _run(["fit", "--captures", d + "/missing", "--out", out])
        check("fit refuses empty discovery", rc == 2 and "no captures" in o)
        check("fit leaves out untouched", open(out).read() == "SENTINEL")


def test_modes_with_mocked_discovery():
    old = (S.A.find_captures, S.R.build_rows, S.A.cell_number)
    S.A.find_captures = lambda dirs, mc: ["/x/c5", "/x/c60", "/x/c95", "/x/u"]
    S.A.cell_number = lambda p: {"/x/c5": 5, "/x/c60": 60, "/x/c95": 95}.get(p)
    train = _grp("week", D_TIGHT, 0.5, 6)
    bad = {**_row("week", D_TIGHT, 0.5), "v2_sigma": None}

    def build(caps, refs):
        if caps == ["/x/c5"]:
            return train + [bad], ["/x/c5: no usable pre-cutoff OHLC history"]
        return _grp("week", D_EASE, 0.5, 2) + [bad], []
    S.R.build_rows = build
    try:
        with tempfile.TemporaryDirectory() as d:
            dec = os.path.join(d, "d.json")
            json.dump(DECS, open(dec, "w"))
            out = os.path.join(d, "f.json")
            rc, o = _run(["fit", "--captures", "x", "--out", out, "--decisions", dec])
            check("fit ok", rc == 0, o[:200])
            first = o.splitlines()[0]
            check("training regime counts printed first", first.startswith("TRAINING CELLS 1-47 regime counts"), first)
            check("fit says degenerate", "TILT DEGENERATE" in o)
            check("fit lists gap and dropped row", "excluded: /x/c5: no usable" in o and "1 row(s) without a v2 sigma" in o
                  and "1 unnumbered" in o, o[-300:])
            fz = json.load(open(out))
            check("fitted w stored", fz["frozen"]["degenerate"] is True and fz["frozen"]["horizons"]["week"]["tightening"]["w"] == 0.9)
            for mode in ("describe", "score"):
                rc, o = _run([mode, "--captures", "x", "--frozen", out, "--reps", "5", "--decisions", dec,
                              "--min-cell", "48" if mode == "describe" else "91"])
                check("%s ok" % mode, rc == 0, o[:300])
                check("%s lists dropped row" % mode, "1 row(s) without a v2 sigma" in o, o[-200:])
                check("%s prints regime in counts" % mode, "easing" in o)
            check("score prints degenerate note", "TILT DEGENERATE: cells >= 91" in o, o[-300:])
            check("score output has no metric words", "RangeSkill" not in o and "coverage" not in o, o[:400])
            open(out, "w").write("SENTINEL")
            rc, o = _run(["fit", "--captures", "x", "--out", out, "--decisions", dec + ".missing"])
            check("missing decisions refused, out untouched", rc == 2 and "no usable decisions" in o
                  and open(out).read() == "SENTINEL", o[:200])
    finally:
        S.A.find_captures, S.R.build_rows, S.A.cell_number = old


def test_decisions_file():
    ds, n = S.load_decisions()
    check("38 usable, none rejected", len(ds) == 38 and n == 0, "%d %d" % (len(ds), n))


def run_all():
    for fn in (test_constants, test_regime_boundaries, test_fit_picks_per_regime, test_fit_min_group_and_tie,
               test_fit_uses_only_given_rows_and_skips_no_sigma, test_score_rows_uses_frozen,
               test_regime_counts_and_degenerate, test_counts_only, test_exclusions_listed, test_refusals,
               test_modes_with_mocked_discovery, test_decisions_file):
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
    print("test_regime_tilt: %d passed, %d failed" % (CHECKS["pass"], CHECKS["fail"]))
    return 1 if CHECKS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
