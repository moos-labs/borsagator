#!/usr/bin/env python3
"""Tests for benchmarks/ledger_freshness.py and its use in the ledger
scorers (issue #791, round 10). Standalone, stdlib only, fixed synthetic
ledgers, assertions through each scorer's own output."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
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


def load(name, fn):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "benchmarks", fn))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


LF = load("lf_t", "ledger_freshness.py")
SCORERS = {
    "tilt": load("lf_tilt", "score_ledger_sentiment_tilt.py"),
    "width": load("lf_width", "score_ledger_sentiment_width.py"),
    "xsec": load("lf_xsec", "score_ledger_xsec_sentiment_tilt.py"),
}


def row(a, mat, status="matured", t="A", h="week"):
    return {"ticker": t, "as_of": a, "horizon": h, "status": status,
            "maturity_date": mat, "dividend_gap": None,
            "range_low_pct": -4.0, "range_high_pct": 4.0,
            "realized_move_pct": 1.0,
            "families": {"sentiment": 0.5, "fundamentals": 0.5}}


ROWS = [row("2026-11-01", "2026-11-08"),
        row("2026-11-10", "2026-11-17"),
        row("2026-11-20", "2026-11-27", status="pending"),
        row("2026-11-25", "2026-12-25", status="pending", h="month")]
LINE = ("ledger freshness: rows 4, newest as_of 2026-11-25, newest "
        "maturity_date 2026-12-25, newest matured maturity_date "
        "2026-11-17")


def run(mod, rows, extra=(), js=None):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "ledger.json")
        json.dump({"forecasts_detail": rows}, open(p, "w"))
        argv = ["--ledger", p] + list(extra)
        if js:
            argv += ["--json", os.path.join(d, "o.json")]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mod.main(argv)
        data = json.load(open(os.path.join(d, "o.json"))) if js else None
    return code, out.getvalue(), err.getvalue(), data


def test_summary():
    fr = LF.summary(ROWS)
    check("newest as_of is over every row",
          fr["newest_as_of"] == "2026-11-25", fr)
    check("newest maturity over every row",
          fr["newest_maturity_date"] == "2026-12-25", fr)
    check("matured maturity ignores pending rows",
          fr["newest_matured_maturity_date"] == "2026-11-17", fr)
    check("line", LF.line(fr) == LINE, LF.line(fr))
    e = LF.summary([])
    check("empty ledger gives none", e["newest_as_of"] is None
          and "none" in LF.line(e))
    b = LF.summary([row("bad", "2026-11-02"), row("2026-11-03", None)])
    check("unparseable dates ignored", b["newest_as_of"] == "2026-11-03"
          and b["newest_maturity_date"] == "2026-11-02", b)


def test_check():
    _, why = LF.check(ROWS, None, "2030-01-01")
    check("default off never refuses", why is None)
    fr, why = LF.check(ROWS, 10, "2026-11-27")
    check("age 10 days at limit 10 passes", why is None
          and fr["age_days"] == 10, (fr, why))
    fr, why = LF.check(ROWS, 9, "2026-11-27")
    check("age 10 days at limit 9 refuses", why and "10 days" in why, why)
    _, why = LF.check([row("2026-11-20", "2026-11-27", "pending")], 5,
                      "2026-11-27")
    check("no matured row cannot be fresh", why and "no matured" in why,
          why)
    for bad in ("not-a-date", "", "2026-11-27garbage", "2026-11-27 ",
                "2026-1-27", "20261127", "2026-02-30", " 2026-11-27",
                "2026-W48-5"):
        for lim in (None, 5):
            _, why = LF.check(ROWS, lim, bad)
            check("bad --today %r (limit %s) refuses" % (bad, lim),
                  why and "valid YYYY-MM-DD" in why, why)
    _, why = LF.check(ROWS, None, "2026-11-27")
    check("exact date accepted without a limit", why is None, why)
    future = [row("2026-11-20", "2026-12-05"),
              row("2026-11-01", "2026-11-08")]
    fr, why = LF.check(future, 30, "2026-11-27")
    check("future-dated matured row is ignored for age",
          why is None and fr["age_days"] == 19, (fr, why))
    _, why = LF.check(future, 10, "2026-11-27")
    check("future-dated matured row cannot rescue a stale ledger",
          why and "19 days" in why, why)
    _, why = LF.check([row("2026-11-20", "2026-12-05")], 30, "2026-11-27")
    check("only future-dated matured rows refuse",
          why and "on or before 2026-11-27" in why, why)
    fr, why = LF.check([row("2026-11-20", "2026-11-27")], 0, "2026-11-27")
    check("maturity today counts, age 0", why is None
          and fr["age_days"] == 0, (fr, why))


def test_every_scorer_prints_and_exports():
    for name, mod in SCORERS.items():
        code, out, err, js = run(mod, ROWS, js=True)
        check(name + " exit 0", code == 0, (code, err))
        check(name + " prints the freshness line", LINE in out, out[:300])
        check(name + " json carries freshness, no verdict key from it",
              js["freshness"] == LF.summary(ROWS), js.get("freshness"))


def test_every_scorer_refuses_when_stale():
    for name, mod in SCORERS.items():
        code, out, err, _ = run(mod, ROWS, ["--max-age-days", "9",
                                            "--today", "2026-11-27"])
        check(name + " refuses with 2", code == 2, code)
        check(name + " reason on stderr", "over --max-age-days 9" in err,
              err)
        check(name + " no scoring output",
              out.strip() == LINE, out[:300])
        code, out, err, _ = run(mod, ROWS, ["--max-age-days", "10",
                                            "--today", "2026-11-27"])
        check(name + " within limit scores", code == 0 and not err,
              (code, err))
        code, out, err, _ = run(mod, ROWS, ["--today", "2030-01-01"])
        check(name + " default off scores any age", code == 0, code)
        for bad in ("", "2026-11-27garbage"):
            code, out, err, _ = run(mod, ROWS, ["--today", bad])
            check(name + " refuses bad --today %r" % bad, code == 2
                  and "valid YYYY-MM-DD" in err and out.strip() == LINE,
                  (code, err))
        fut = ROWS + [row("2026-11-20", "2026-12-30")]
        code, out, err, _ = run(mod, fut, ["--max-age-days", "9",
                                           "--today", "2026-11-27"])
        check(name + " future matured row does not pass the gate",
              code == 2, code)


def test_forward_benchmark_refuses():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "ledger.json")
        json.dump({"forecasts_detail": ROWS}, open(p, "w"))
        r = subprocess.run(
            [sys.executable, "-B", os.path.join(
                ROOT, "benchmarks", "score_forward_benchmark.py"),
             "--ledger", p, "--archive", d, "--scripts", HERE,
             "--out-md", os.path.join(d, "o.md"),
             "--max-age-days", "9", "--today", "2026-11-27"],
            capture_output=True, text=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        check("forward benchmark refuses with 2", r.returncode == 2,
              (r.returncode, r.stderr[-300:]))
        check("forward benchmark prints line and reason",
              LINE in r.stdout and "over --max-age-days 9" in r.stderr,
              (r.stdout[:200], r.stderr[-200:]))
        check("forward benchmark wrote nothing",
              not os.path.exists(os.path.join(d, "o.md")))


def main():
    for fn in (test_summary, test_check,
               test_every_scorer_prints_and_exports,
               test_every_scorer_refuses_when_stale,
               test_forward_benchmark_refuses):
        fn()
    print("test_ledger_freshness: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
