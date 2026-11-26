#!/usr/bin/env python3
"""Tests for benchmarks/score_ledger_sentiment_tilt.py (INS-IMPROVE-001
r4). Standalone, stdlib only:
python3 scripts/test_ledger_sentiment_tilt.py
"""
import contextlib
import importlib.util
import io
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
    "slt", os.path.join(ROOT, "benchmarks",
                        "score_ledger_sentiment_tilt.py"))
S = importlib.util.module_from_spec(spec)
sys.modules["slt"] = S
spec.loader.exec_module(S)


def row(real=1.0, sent=0.5, lo=-4.0, hi=4.0, h="week", t="A",
        a="2026-11-12", status="matured", gap=None):
    return {"ticker": t, "as_of": a, "horizon": h, "status": status,
            "dividend_gap": gap, "range_low_pct": lo,
            "range_high_pct": hi, "realized_move_pct": real,
            "families": {"sentiment": sent}}


def test_constants():
    check("gamma 0.25", S.GAMMA == 0.25)
    check("minimums", (S.MIN_ROWS, S.MIN_TICKERS, S.MIN_DATES)
          == (30, 10, 2))
    check("coverage band", S.COV_BAND == (0.75, 0.85))


def test_eligible():
    check("matured ok", S.eligible(row()))
    check("pending out", not S.eligible(row(status="pending")))
    check("gap flagged out", not S.eligible(row(gap="x")))
    check("no sentiment out", not S.eligible(
        dict(row(), families={"technicals": 0.1})))
    check("missing band out", not S.eligible(dict(row(), range_low_pct=None)))
    check("fundamentals family selectable",
          S.eligible(dict(row(), families={"fundamentals": 0.2}),
                     "fundamentals"))


def test_band():
    lo, hi = S.shifted_band(row(sent=0.5, lo=-4.0, hi=4.0))
    check("shift is gamma x s x half", abs(lo + 4 - 0.5) < 1e-9
          and abs(hi - 4 - 0.5) < 1e-9, (lo, hi))
    lo, hi = S.shifted_band(row(sent=-1.0, lo=-2.0, hi=6.0))
    check("asymmetric band keeps width and shifts by half",
          abs((hi - lo) - 8.0) < 1e-9 and abs(lo - (-2.0 - 1.0)) < 1e-9)
    lo, hi = S.shifted_band(row(sent=3.0, lo=-4.0, hi=4.0))
    check("clip at 1", abs(hi - 4 - 1.0) < 1e-9)
    lo, hi = S.shifted_band(row(sent=0.0))
    check("zero score is no shift", (lo, hi) == (-4.0, 4.0))


def test_score_rows():
    p = S.score_rows([row(real=4.5, sent=1.0)])[0]
    check("tilt pulls move into band", p["in_ch"] and not p["in_v2"])
    check("tilt IS lower there", p["is_ch"] < p["is_naive"])
    q = S.score_rows([row(real=-4.5, sent=1.0)])[0]
    check("wrong-way move hurts", q["is_ch"] > q["is_naive"])
    check("ineligible skipped",
          S.score_rows([row(status="pending")]) == [])


def test_verdict():
    pairs = S.score_rows([row() for _ in range(5)])
    v = S.verdicts(pairs)
    check("small sample insufficient",
          all(v[h][0] == "INSUFFICIENT" for h in S.HORIZONS))
    rows = [row(real=0.5, t="T%d" % (i % 12), a="2026-11-%02d" % (i % 3 + 10))
            for i in range(36)]
    pairs = S.score_rows(rows)
    smp = S.sample(pairs)
    check("enough sample", S.enough(smp["week"]), str(smp["week"]))
    res = S.R.evaluate(pairs, reps=200)
    v = S.verdicts(pairs, res)
    check("week verdict is keep/reject once enough",
          v["week"][0] in ("KEEP", "REJECT"))
    check("day still insufficient", v["day"][0] == "INSUFFICIENT")


def _synthetic_ledger(tmpdir):
    """Fixed insufficient ledger: 5 matured rows, 1 ticker."""
    import json
    rows = [dict(row(real=1.0 + i, t="A", a="2026-11-1%d" % i))
            for i in range(5)]
    path = os.path.join(tmpdir, "ledger.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"forecasts_detail": rows}, f)
    return path


def test_default_hides_numbers():
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


def main():
    for fn in (test_constants, test_eligible, test_band,
               test_score_rows, test_verdict,
               test_default_hides_numbers):
        fn()
    print("test_ledger_sentiment_tilt: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
