#!/usr/bin/env python3
"""Tests for benchmarks/score_ledger_xsec_sentiment_tilt.py
(INS-IMPROVE-001 r8, X1). Standalone, stdlib only:
python3 scripts/test_ledger_xsec_sentiment_tilt.py
"""
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
    "xst", os.path.join(ROOT, "benchmarks",
                        "score_ledger_xsec_sentiment_tilt.py"))
X = importlib.util.module_from_spec(spec)
sys.modules["xst"] = X
spec.loader.exec_module(X)


def row(t, sent, real=1.0, lo=-4.0, hi=4.0, h="day", a="2026-11-25",
        status="matured", gap=None):
    return {"ticker": t, "as_of": a, "horizon": h, "status": status,
            "dividend_gap": gap, "range_low_pct": lo,
            "range_high_pct": hi, "realized_move_pct": real,
            "families": {"sentiment": sent}}


def group(sents, **kw):
    return [row("T%d" % i, s, **kw) for i, s in enumerate(sents)]


def test_constants():
    check("gamma 0.25", X.GAMMA == 0.25)
    check("minimums", (X.MIN_ROWS, X.MIN_TICKERS, X.MIN_CUTOFFS,
                       X.MIN_GROUP) == (30, 10, 2, 4))
    check("coverage band", X.COV_BAND == (0.75, 0.85))


def test_relative_scores():
    rows = group([0.1, 0.3, 0.5, 0.7, 0.9])
    rel = X.relative_scores(rows)
    got = [round(rel[("T%d" % i, "2026-11-25", "day")], 6)
           for i in range(5)]
    check("demeaned by the group median", got == [-0.4, -0.2, 0.0, 0.2,
                                                 0.4], str(got))
    rel = X.relative_scores(group([-0.9, 0.9, 0.9, 0.9, 0.9]))
    check("clipped to [-1, 1]",
          rel[("T0", "2026-11-25", "day")] == -1.0, str(rel))
    check("group under MIN_GROUP dropped",
          X.relative_scores(group([0.1, 0.5, 0.9])) == {})
    rows = group([0.1, 0.3, 0.5, 0.7]) + [
        row("P", 0.9, status="pending"), row("G", 0.9, gap="x")]
    check("ineligible rows neither counted nor demeaned",
          set(k[0] for k in X.relative_scores(rows))
          == {"T0", "T1", "T2", "T3"})
    rows = group([0.1, 0.3, 0.5, 0.7]) + group(
        [0.1, 0.3, 0.5, 0.7], h="week")
    check("groups are per horizon", len(X.relative_scores(rows)) == 8)
    rows = group([0.1, 0.3, 0.5, 0.7], a="2026-11-25") + group(
        [0.5, 0.7, 0.9, 0.3], a="2026-11-26")
    rel = X.relative_scores(rows)
    check("first cutoff demeaned on its own median",
          abs(rel[("T0", "2026-11-25", "day")] + 0.3) < 1e-9
          and abs(rel[("T3", "2026-11-25", "day")] - 0.3) < 1e-9, str(rel))
    check("second cutoff demeaned on its own median",
          abs(rel[("T0", "2026-11-26", "day")] + 0.1) < 1e-9
          and abs(rel[("T2", "2026-11-26", "day")] - 0.3) < 1e-9,
          str(rel))


def test_tilt_band():
    lo, hi = X.shifted_band(row("A", 0.0), 0.4)
    check("shift is gamma x rel x half", abs(lo - (-4 + 0.4)) < 1e-9
          and abs(hi - (4 + 0.4)) < 1e-9, "%s %s" % (lo, hi))
    rows = group([0.1, 0.3, 0.5, 0.9], real=4.3)
    pairs = X.score_rows(rows)
    by = {p["ticker"]: p for p in pairs}
    # rel T3 = 0.9 - 0.4 = 0.5: band [-3.5, 4.5] holds 4.3, the
    # published band [-4, 4] does not
    check("tilted band covers where the published band misses",
          by["T3"]["in_ch"] and not by["T3"]["in_v2"], str(by["T3"]))
    check("tilt band IS beats the published IS there",
          by["T3"]["is_ch"] < by["T3"]["is_v2"])
    check("dropped group scores nothing",
          X.score_rows(group([0.1, 0.5, 0.9])) == [])


def test_spearman():
    check("perfect", abs(X.spearman([1, 2, 3, 4], [10, 20, 30, 40])
                         - 1.0) < 1e-9)
    check("inverse", abs(X.spearman([1, 2, 3, 4], [40, 30, 20, 10])
                         + 1.0) < 1e-9)
    check("constant side undefined", X.spearman([1, 1, 1], [1, 2, 3])
          is None)
    check("ties use average ranks",
          abs(X.spearman([1, 2, 2, 3], [1, 2, 3, 4]) - 0.9486832981)
          < 1e-6, str(X.spearman([1, 2, 2, 3], [1, 2, 3, 4])))


def res_ok(lo=0.05):
    return {h: {"ch_ci_cutoff": [lo, 0.2], "ch": {"coverage": 0.8},
                "ch_cov_ci_cutoff": [0.72, 0.87]} for h in X.HORIZONS}


def ic_with(lo, cutoffs=5):
    return {h: {"cutoffs": cutoffs, "mean": 0.2, "ci": [lo, 0.4]}
            for h in X.HORIZONS}


def fake_pairs(n=36, tickers=12, cutoffs=3):
    return [{"ticker": "T%d" % (i % tickers), "as_of": "c%d" % (i % cutoffs),
             "horizon": h} for i in range(n) for h in X.HORIZONS]


def test_verdict():
    p = fake_pairs()
    v = X.verdicts(p, res_ok(), ic_with(0.05))
    check("all legs hold: keep", all(v[h][0] == "KEEP"
                                     for h in X.HORIZONS), str(v))
    v = X.verdicts(p, res_ok(0.0), ic_with(0.05))
    check("skill CI lower 0 rejects", v["day"][0] == "REJECT")
    v = X.verdicts(p, res_ok(), ic_with(0.0))
    check("rank-IC CI lower 0 rejects with the skill leg passing",
          v["day"][0] == "REJECT" and "rank-IC" in v["day"][1], str(v))
    v = X.verdicts(p, res_ok(), ic_with(None))
    check("undefined rank-IC CI rejects", v["day"][0] == "REJECT")
    r = res_ok()
    for h in X.HORIZONS:
        r[h]["ch_cov_ci_cutoff"] = [0.4, 0.6]
    v = X.verdicts(p, r, ic_with(0.05))
    check("coverage CI below the band rejects", v["day"][0] == "REJECT")
    r = res_ok()
    for h in X.HORIZONS:
        r[h]["ch_cov_ci_cutoff"] = [0.65, 0.88]
    v = X.verdicts(p, r, ic_with(0.05))
    check("overlapping CI wider than the cap rejects",
          v["day"][0] == "REJECT" and "cap" in v["day"][1], str(v))
    v = X.verdicts(fake_pairs(n=20), res_ok(), ic_with(0.05))
    check("under 30 rows insufficient", v["day"][0] == "INSUFFICIENT")
    v = X.verdicts(fake_pairs(tickers=9), res_ok(), ic_with(0.05))
    check("under 10 tickers insufficient", v["day"][0] == "INSUFFICIENT")
    v = X.verdicts(fake_pairs(cutoffs=1), res_ok(), ic_with(0.05))
    check("one cutoff insufficient", v["day"][0] == "INSUFFICIENT")


def ledger_rows():
    """Three cutoffs x 12 tickers on the day horizon; the realised move
    follows the relative score, so the rank leg is positive."""
    rows = []
    for ci, a in enumerate(("2026-11-23", "2026-11-24", "2026-11-25")):
        for i in range(12):
            s = -0.55 + 0.1 * i + 0.01 * ci
            rows.append(row("T%d" % i, s, real=6.0 * (s - 0.0), a=a))
    return rows


def run_main(rows, extra):
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "l.json")
        out = os.path.join(d, "o.json")
        with open(led, "w") as fh:
            json.dump({"forecasts_detail": rows}, fh)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = X.main(["--ledger", led, "--reps", "200", "--json", out]
                        + extra)
        return rc, buf.getvalue(), json.load(open(out))


def test_main_outputs():
    rows = ledger_rows()
    rc, text, data = run_main(rows, ["--descriptive"])
    check("descriptive exits 0", rc == 0)
    check("descriptive json carries no verdicts key",
          "verdicts" not in data and data["descriptive"] is True,
          str(list(data)))
    check("descriptive text has no verdict arrow",
          "->" not in text and "KEEP" not in text
          and "REJECT" not in text, text)
    check("descriptive text says no verdict is valid",
          "no keep/reject is valid" in text)
    check("sample counted through the scorer",
          data["sample"]["day"] == {"n": 36, "tickers": 12, "cutoffs": 3},
          str(data["sample"]))
    check("rank leg positive through the scorer",
          data["rank_ic"]["day"]["cutoffs"] == 3
          and data["rank_ic"]["day"]["mean"] > 0.99, str(data["rank_ic"]))
    rc, text, data = run_main(rows, [])
    check("clean json carries verdicts",
          data["descriptive"] is False
          and set(data["verdicts"]) == set(X.HORIZONS)
          and data["verdicts"]["week"] == "INSUFFICIENT")
    check("clean text carries the verdict", "day:" in text and "->" in text)
    rows2 = [dict(r, realized_move_pct=-r["realized_move_pct"])
             for r in ledger_rows()]
    _, _, data = run_main(rows2, ["--descriptive"])
    check("inverted realised moves give a negative rank leg",
          data["rank_ic"]["day"]["mean"] < -0.99)
    _, _, data = run_main(group([0.1, 0.5, 0.9]), ["--descriptive"])
    check("small groups score nothing end to end",
          data["sample"]["day"]["n"] == 0)


def main():
    for fn in (test_constants, test_relative_scores, test_tilt_band,
               test_spearman, test_verdict, test_main_outputs):
        fn()
    print("test_ledger_xsec_sentiment_tilt: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
