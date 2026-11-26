#!/usr/bin/env python3
"""Tests for benchmarks/score_ledger_sentiment_width.py (INS-IMPROVE-001
r5 item 1). Standalone, stdlib only.
"""
import importlib.util
import io
import contextlib
import os
import sys

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
    "slw", os.path.join(ROOT, "benchmarks",
                        "score_ledger_sentiment_width.py"))
S = importlib.util.module_from_spec(spec)
sys.modules["slw"] = S
spec.loader.exec_module(S)


def row(real=1.0, sent=0.5, lo=-4.0, hi=4.0, h="week", t="A",
        a="2026-11-12", status="matured", gap=None):
    return {"ticker": t, "as_of": a, "horizon": h, "status": status,
            "dividend_gap": gap, "range_low_pct": lo,
            "range_high_pct": hi, "realized_move_pct": real,
            "families": {"sentiment": sent}}


def test_constants():
    check("beta", S.BETA == 0.25)
    check("same minimums as tilt", (S.T.MIN_ROWS, S.T.MIN_TICKERS,
                                    S.T.MIN_DATES) == (30, 10, 2))
    check("coverage band", S.T.COV_BAND == (0.75, 0.85))


def test_band():
    lo, hi = S.widened_band(row(sent=0.5))
    check("scale 1.125", abs(hi - 4.5) < 1e-9 and abs(lo + 4.5) < 1e-9,
          (lo, hi))
    lo, hi = S.widened_band(row(sent=-0.5))
    check("sign ignored (widen-only)", abs(hi - 4.5) < 1e-9)
    lo, hi = S.widened_band(row(sent=0.0))
    check("zero score no change", (lo, hi) == (-4.0, 4.0))
    lo, hi = S.widened_band(row(sent=5.0))
    check("capped at 1.25", abs(hi - 5.0) < 1e-9)
    lo, hi = S.widened_band(row(sent=1.0, lo=-2.0, hi=6.0))
    check("centre kept", abs((lo + hi) / 2 - 2.0) < 1e-9
          and abs((hi - lo) - 10.0) < 1e-9)
    for s in (-1.0, -0.2, 0.0, 0.3, 0.9):
        lo, hi = S.widened_band(row(sent=s))
        check("never narrower", hi - lo >= 8.0 - 1e-9)


def test_score():
    p = S.score_rows([row(real=4.4, sent=0.8)])[0]
    check("widening catches near miss", p["in_ch"] and not p["in_v2"])
    check("catching it lowers IS", p["is_ch"] < p["is_naive"])
    q = S.score_rows([row(real=0.0, sent=0.8)])[0]
    check("inside band widening costs IS", q["is_ch"] > q["is_naive"])
    check("ineligible skipped",
          S.score_rows([row(status="pending"), row(gap="x")]) == [])


def test_verdict():
    v = S.verdicts(S.score_rows([row() for _ in range(5)]))
    check("small is insufficient",
          all(v[h][0] == "INSUFFICIENT" for h in S.HORIZONS))
    rows = [row(real=0.5, t="T%d" % (i % 12),
                a="2026-11-%02d" % (i % 3 + 10)) for i in range(36)]
    pairs = S.score_rows(rows)
    res = S.R.evaluate(pairs, 200)
    v = S.verdicts(pairs, res)
    check("week decided once enough", v["week"][0] in ("KEEP", "REJECT"))
    check("coverage 1.0 fails the band", v["week"][0] == "REJECT")


def _synthetic_ledger(tmpdir):
    """Fixed insufficient ledger: 5 matured rows, 1 ticker."""
    import json
    rows = [dict(row(real=1.0 + i, t="A", a="2026-11-1%d" % i))
            for i in range(5)]
    path = os.path.join(tmpdir, "ledger.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"forecasts_detail": rows}, f)
    return path


def test_default_output():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = _synthetic_ledger(d)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = S.main(["--ledger", path])
        out = buf.getvalue()
    check("exit 0", rc == 0)
    check("insufficient reported", "INSUFFICIENT" in out, out)
    check("counts only while insufficient", "RangeSkill" not in out, out)
    buf = io.StringIO()
    with tempfile.TemporaryDirectory() as d:
        path = _synthetic_ledger(d)
        with contextlib.redirect_stdout(buf):
            S.main(["--ledger", path, "--descriptive", "--reps", "50"])
    check("descriptive shows numbers", "RangeSkill" in buf.getvalue())


def test_frozen():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import ensemble
    check("V2_BAND_K pinned", ensemble.V2_BAND_K == {
        "day": 1.15, "week": 1.28, "month": 1.20})


def main():
    for fn in (test_constants, test_band, test_score, test_verdict,
               test_default_output, test_frozen):
        fn()
    print("test_ledger_sentiment_width: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
