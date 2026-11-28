#!/usr/bin/env python3
"""Tests for benchmarks/score_adoption_594.py (#594 adoption scorer).

Standalone: `python3 scripts/test_adoption_594.py` (stdlib only, no
network, no model). Builds small synthetic captures in a temp dir.
"""
import importlib.util
import json
import math
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    if ok:
        CHECKS["pass"] += 1
    else:
        CHECKS["fail"] += 1
        print("FAIL %s %s" % (name, detail))


spec = importlib.util.spec_from_file_location(
    "adopt594", os.path.join(ROOT, "benchmarks", "score_adoption_594.py"))
A = importlib.util.module_from_spec(spec)
sys.modules["adopt594"] = A
spec.loader.exec_module(A)


def make_capture(root, run, cutoff, ticker, closes, sigma=0.02,
                 kronos_close=None):
    """closes: 21 realised session closes after base 100."""
    d = os.path.join(root, run, "backtest", cutoff, ticker)
    os.makedirs(os.path.join(d, "digest"))
    os.makedirs(os.path.join(d, "collected", "kronos"))
    json.dump({"ticker": ticker, "cutoff": cutoff, "status": "ok"},
              open(os.path.join(d, "manifest.json"), "w"))
    sessions = []
    for i, c in enumerate(closes):
        sessions.append({"date": "2030-01-%02d" % (i + 1), "close": c})
    json.dump({"ticker": ticker, "cutoff": cutoff, "base_close": 100.0,
               "base_date": cutoff, "sessions": sessions,
               "index_gap": "synthetic"},
              open(os.path.join(d, "realised.json"), "w"))
    json.dump({"ticker": ticker, "date": cutoff, "base_price": 100.0,
               "sigma_daily": sigma, "sigma60_daily": sigma,
               "risk": {"level": "none", "price_mult": 1.0,
                        "conf_cap": 0.6},
               "family_scores": {"technicals": 0.5, "sentiment": None,
                                 "agent": None, "fundamentals": None},
               "corporate_actions": [], "horizons": {}},
              open(os.path.join(d, "digest", "ensemble.json"), "w"))
    kc = kronos_close or 90.0
    with open(os.path.join(d, "collected", "kronos", "forecast.csv"),
              "w") as f:
        f.write("date,open,high,low,close\n")
        for i in range(21):
            f.write("2030-01-%02d,%s,%s,%s,%s\n"
                    % (i + 1, kc, kc + 1, kc - 1, kc))
    return d


def test_winkler_and_skill():
    check("winkler inside", A.bs.winkler_is(1, -2, 2) == 4)
    check("winkler below", abs(A.bs.winkler_is(-3, -2, 2) - 14) < 1e-9)
    pairs = [{"is_v1": 12.0, "is_v2": 6.0, "is_naive": 8.0},
             {"is_v1": 4.0, "is_v2": 2.0, "is_naive": 8.0}]
    check("skill v2", abs(A.range_skill(pairs, "v2") - 0.5) < 1e-9)
    check("skill v1 (equal to naive is 0)",
          abs(A.range_skill(pairs, "v1")) < 1e-9)
    check("skill empty", A.range_skill([], "v2") is None)
    check("skill zero naive",
          A.range_skill([{"is_v2": 1.0, "is_naive": 0.0}], "v2") is None)


def test_frozen_v2_band():
    ens = {"sigma60_daily": 0.02, "risk": {"level": "none"}}
    hz = A.v2_horizons(ens)
    check("v2 centre 0", all(hz[h]["expected_move_pct"] == 0.0
                             for h in A.HORIZONS))
    exp = {"day": 1.15 * 0.02, "week": 1.28 * 0.02 * math.sqrt(5),
           "month": 1.20 * 0.02 * math.sqrt(21)}
    for h in A.HORIZONS:
        check("v2 half %s" % h,
              abs(hz[h]["range_high_pct"] - exp[h] * 100) < 1e-9,
              repr(hz[h]))
        check("v2 symmetric %s" % h,
              hz[h]["range_low_pct"] == -hz[h]["range_high_pct"])
    # Risk overlay widens, calibration block is ignored.
    ens["risk"] = {"level": "elevated"}
    ens["horizons"] = {"day": {"band_calibration": {"applied": True}}}
    check("v2 risk overlay",
          abs(A.v2_horizons(ens)["day"]["range_high_pct"]
              - 1.2 * 1.15 * 2.0) < 1e-9)
    check("v2 no sigma -> no horizons", A.v2_horizons({}) == {})
    check("V2 constants match ensemble",
          A.ens_mod.V2_BAND_K == {"day": 1.15, "week": 1.28,
                                  "month": 1.20})


def test_v1_formula():
    ens = {"sigma_daily": 0.02, "risk": {"level": "none",
                                         "price_mult": 1.0},
           "family_scores": {"technicals": 0.5}}
    kpath = [(90.0, 91.0, 89.0)] * 21
    hz = A.v1_horizons(ens, kpath, 100.0)
    # day: kmove -10%, vol_h 2%, price score = -1 (clamped).
    # weights tech .30, price .45 -> net = (.5*.3 + -1*.45)/.75 = -.4
    net = (0.5 * 0.30 - 1.0 * 0.45) / 0.75
    exp_centre = (0.6 * -0.10 + 0.4 * net * 1.28 * 0.02) * 100
    check("v1 day centre", abs(hz["day"]["expected_move_pct"]
                               - exp_centre) < 1e-9, repr(hz["day"]))
    var = (0.30 * (0.5 - net) ** 2 + 0.45 * (-1.0 - net) ** 2) / 0.75
    half = max(1.28 * 0.02, 0.01) * (1 + 0.5 * math.sqrt(var)) * 100
    check("v1 day half",
          abs((hz["day"]["range_high_pct"] - hz["day"]["range_low_pct"])
              / 2 - half) < 1e-9, repr(hz["day"]))
    check("v1 no base -> none", A.v1_horizons(ens, kpath, None) == {})
    # Without Kronos the band still comes from sigma.
    hz2 = A.v1_horizons(ens, None, 100.0)
    check("v1 no kronos", "day" in hz2
          and abs(hz2["day"]["expected_move_pct"]
                  - 0.4 * 0.5 * 1.28 * 0.02 * 100) < 1e-6, repr(hz2))


def test_block_bootstrap_by_ticker():
    # Ticker A: v2 clearly better, 10 rows. Ticker B: v2 clearly worse.
    # A by-row bootstrap would give a CI near the pooled mean;
    # resampling whole tickers must produce all-A, all-B and mixed
    # draws, so the CI must span both signs.
    pairs = []
    for i in range(10):
        pairs.append({"ticker": "A", "horizon": "day", "is_v1": 10.0,
                      "is_v2": 5.0, "is_naive": 8.0})
        pairs.append({"ticker": "B", "horizon": "day", "is_v1": 6.0,
                      "is_v2": 12.0, "is_naive": 8.0})
    draws = A.block_bootstrap(pairs, reps=400, seed=1)
    lo, hi = A.percentile_ci(draws["v2"])
    check("block CI spans both tickers", lo < 0.0 < 0.4 < hi or
          (lo <= -0.4 and hi >= 0.3), "%s %s" % (lo, hi))
    only_a = {round(d, 6) for d in draws["v2"]}
    check("draws are ticker blocks (few distinct values)",
          len(only_a) <= 3, repr(sorted(only_a)))
    check("deterministic",
          A.block_bootstrap(pairs, 50, 7) == A.block_bootstrap(pairs, 50, 7))
    check("empty input", A.block_bootstrap([], 10, 1) ==
          {"v1": [], "v2": [], "diff": []})
    check("percentile empty", A.percentile_ci([]) == (None, None))


def test_verdict_rules():
    check("insufficient rows", A.verdict(10, 6, 0.5) == "INSUFFICIENT")
    check("insufficient tickers", A.verdict(60, 2, 0.5) == "INSUFFICIENT")
    check("no ci", A.verdict(60, 6, None) == "INSUFFICIENT")
    check("adopt", A.verdict(60, 6, 0.01) == "ADOPT")
    check("lower bound zero is not adopt",
          A.verdict(60, 6, 0.0) == "DO NOT ADOPT")
    check("negative", A.verdict(60, 6, -0.2) == "DO NOT ADOPT")


def test_max_cell_applied_before_dedup():
    with tempfile.TemporaryDirectory() as tmp:
        closes = [100 + 0.3 * i for i in range(21)]
        make_capture(tmp, "r1__w5-backtest-436-cell48", "2025-09-30", "AAA.CA", closes)
        make_capture(tmp, "r2__w5-backtest-436-cell91", "2025-09-30", "AAA.CA", closes)
        both = A.find_captures([tmp], None)
        check("unbounded dedup keeps only the latest path (cell91)",
              len(both) == 1 and "cell91" in both[0], repr(both))
        low = A.find_captures([tmp], 48, 90)
        check("max_cell applied before dedup: eligible cell48 survives",
              len(low) == 1 and "cell48" in low[0], repr(low))
        high = A.find_captures([tmp], 91, None)
        check("min-only call unchanged", len(high) == 1 and "cell91" in high[0], repr(high))
        check("max_cell is inclusive", len(A.find_captures([tmp], 48, 48)) == 1
              and "cell48" in A.find_captures([tmp], 48, 48)[0])
        check("below max_cell excludes cell91 and cell48 when max is 47",
              A.find_captures([tmp], None, 47) == [])


def test_discovery_and_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        closes = [100 + 0.3 * i for i in range(21)]
        make_capture(tmp, "r1__w5-backtest-436-cell47", "2025-06-30",
                     "AAA.CA", closes)
        make_capture(tmp, "r2__w5-backtest-436-cell48", "2025-09-30",
                     "AAA.CA", closes)
        make_capture(tmp, "r3__w5-backtest-436-cell49", "2025-09-30",
                     "BBB.CA", [100 - 0.5 * i for i in range(21)])
        make_capture(tmp, "r4__w5-backtest-436-cell49-r2", "2025-09-30",
                     "BBB.CA", [100 - 0.5 * i for i in range(21)])
        caps = A.find_captures([tmp], 48)
        names = sorted(os.path.basename(c) + "@" +
                       os.path.basename(os.path.dirname(c))
                       for c in caps)
        check("min-cell drops cell47, dedupes rerun",
              names == ["AAA.CA@2025-09-30", "BBB.CA@2025-09-30"],
              repr(names))
        check("rerun path wins",
              any("cell49-r2" in c for c in caps), repr(caps))
        check("no min-cell keeps all",
              len(A.find_captures([tmp], None)) == 3)
        pairs, gaps = A.score_rows(caps)
        check("6 pairs (2 cells x 3 horizons)", len(pairs) == 6,
              repr(pairs))
        check("pairs carry all three scores",
              all(k in p for p in pairs
                  for k in ("is_v1", "is_v2", "is_naive")))
        check("no tilt/index noise in gaps",
              not any("tilt-technicals" in g or "index-baseline" in g
                      for g in gaps), repr(gaps))
        # v2 day band is 1.15 sigma, naive 1.2816 sigma: a tight band
        # with a realised inside both scores its width, so v2 < naive.
        day = [p for p in pairs if p["horizon"] == "day"][0]
        check("v2 day IS is its width", abs(
            day["is_v2"] - 2 * 1.15 * 2.0) < 1e-6
            or day["is_v2"] > 2 * 1.15 * 2.0, repr(day))
        check("naive day IS >= width",
              day["is_naive"] >= 2 * 1.2816 * 2.0 - 0.01, repr(day))
        res = A.evaluate(pairs, reps=100, seed=3)
        check("2 rows -> INSUFFICIENT everywhere",
              all(res[h][v]["verdict"] == "INSUFFICIENT"
                  for h in A.HORIZONS for v in ("v1", "v2")))
        txt = A.render(res, len(caps), gaps)
        check("criterion printed plainly",
              "ADOPTION CRITERION: Adopt a tilt only if its RangeSkill "
              "CI lower bound > 0" in txt)
        out = os.path.join(tmp, "out.json")
        rc = A.main(["--captures", tmp, "--reps", "50", "--json", out])
        data = json.load(open(out))
        check("main ok + json", rc == 0 and data["captures"] == 2
              and "month" in data["results"])


def test_cutoff_cluster_bootstrap():
    """INS-IMPROVE-001: cutoff blocks resample whole cutoffs, the
    default (ticker) path is unchanged, and the coverage draws sit
    inside [0, 1]."""
    pairs = []
    for i, cut in enumerate(("2026-03-31", "2026-06-30", "2026-09-30")):
        for t in ("AAA", "BBB"):
            pairs.append({"ticker": t, "as_of": cut, "horizon": "day",
                          "is_v1": 2.0, "is_v2": 1.0 + i, "is_naive": 2.0,
                          "in_v1": True, "in_v2": i != 2})
    d = A.block_bootstrap(pairs, reps=200, seed=1, by="as_of")
    check("cluster draws made", len(d["v2"]) == 200, str(len(d["v2"])))
    d0 = A.block_bootstrap(pairs, reps=200, seed=1)
    check("default is by ticker",
          d0 == A.block_bootstrap(pairs, reps=200, seed=1, by="ticker"))
    cov = A.coverage_bootstrap(pairs, "v2", reps=200, seed=1)
    check("coverage draws in [0,1]",
          len(cov) == 200 and all(0.0 <= c <= 1.0 for c in cov))
    check("empty pairs give no draws",
          A.coverage_bootstrap([], "v2", reps=10) == [])
    res = A.evaluate(pairs, reps=100, seed=1)
    check("evaluate reports cutoffs",
          res["day"]["cutoffs"] == 3
          and "cutoff_cluster" in res["day"])


def test_dedup_prefers_numbered_and_cell_anchor():
    check("cell number read from a real archive name",
          A.cell_number("/a/150649__run-x__w5-backtest-436-cell2-r2/b")
          == 2)
    check("rerun suffix kept", A.cell_number("/a/w5-cell49-r2/b") == 49)
    check("last match wins", A.cell_number("/cell12/x/w5-cell7") == 7)
    check("component start is anchored", A.cell_number("/a/cell91/b")
          == 91)
    check("embedded in a word is not a cell number",
          A.cell_number("/a/notcell91/b") is None
          and A.cell_number("/a/cell91x/b") is None
          and A.cell_number("/a/subcell3-r1/b") is None)
    with tempfile.TemporaryDirectory() as tmp:
        closes = [100 + 0.3 * i for i in range(21)]
        make_capture(tmp, "r1__w5-backtest-436-cell60", "2025-09-30",
                     "AAA.CA", closes)
        make_capture(tmp, "zz-rerun-unnumbered", "2025-09-30",
                     "AAA.CA", closes)
        make_capture(tmp, "r2__notcell91", "2025-09-30", "BBB.CA", closes)
        caps = A.find_captures([tmp], 48)
        a = [c for c in caps if c.endswith("AAA.CA")]
        check("numbered cell60 wins the dedup over the unnumbered rerun",
              len(a) == 1 and "cell60" in a[0], repr(a))
        b = [c for c in A.find_captures([tmp], 100)
             if c.endswith("BBB.CA")]
        check("notcell91 is unnumbered, so min-cell does not drop it",
              len(b) == 1 and A.cell_number(b[0]) is None, repr(b))


def test_no_pycache_written():
    bad = []
    for dp, dn, fn in os.walk(ROOT):
        if ".git" in dp.split(os.sep):
            continue
        for x in dn + fn:
            if "pycache" in x or x.endswith(".pyc"):
                bad.append(os.path.join(dp, x))
    check("no pycache artefacts", not bad, repr(bad[:3]))


if __name__ == "__main__":
    test_winkler_and_skill()
    test_frozen_v2_band()
    test_v1_formula()
    test_block_bootstrap_by_ticker()
    test_verdict_rules()
    test_cutoff_cluster_bootstrap()
    test_max_cell_applied_before_dedup()
    test_discovery_and_end_to_end()
    test_dedup_prefers_numbered_and_cell_anchor()
    test_no_pycache_written()
    print("test_adoption_594: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)
