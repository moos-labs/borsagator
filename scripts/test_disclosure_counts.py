#!/usr/bin/env python3
"""Tests for scripts/disclosure_counts.py and its ledger.py hook.
Standalone, stdlib only, fixture-backed (shape of the Mubasher harvest
JSONL: ann2/<TICKER>.jsonl, no ticker field).
"""
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disclosure_counts as DC  # noqa: E402

CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


def rec(i, date, head="x (POUL.CA) Reports"):
    return {"id": str(i), "headline": head, "date": date, "text": "...",
            "attachments": []}


def test_parse_and_session_rule():
    t = DC.parse_stamp("12-Nov-2026 08:44")
    check("parse", t is not None and (t.year, t.month, t.day, t.hour,
                                      t.minute) == (2026, 11, 12, 8, 44))
    check("bad stamp is None", DC.parse_stamp("nonsense") is None
          and DC.parse_stamp(None) is None)
    # 2026-11-12 is a Thursday (trading day), 11-13 Friday, 11-15 Sunday
    check("before close, trading day: same day",
          DC.session_date("12-Nov-2026 08:44") == "2026-11-12")
    check("exactly 14:30: same day",
          DC.session_date("12-Nov-2026 14:30") == "2026-11-12")
    check("14:31 Thursday: next trading day is Sunday",
          DC.session_date("12-Nov-2026 14:31") == "2026-11-15")
    check("Friday morning: Sunday",
          DC.session_date("13-Nov-2026 09:00") == "2026-11-15")
    check("Sunday after close: Monday",
          DC.session_date("15-Nov-2026 15:10") == "2026-11-16")
    check("unparseable: None", DC.session_date("") is None)


def test_load_and_dedup():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "POUL.jsonl"), "w") as f:
            for r in (rec(1, "12-Nov-2026 08:44"),
                      rec(2, "12-Nov-2026 10:00"),
                      rec(2, "12-Nov-2026 10:00"),       # duplicate id
                      rec(3, "12-Nov-2026 15:00"),       # next session
                      rec(4, "bad date")):
                f.write(json.dumps(r) + "\n")
            f.write("not json\n")
        open(os.path.join(d, "EMPT.jsonl"), "w").write("")
        open(os.path.join(d, "readme.txt"), "w").write("x")
        c = DC.load_counts(d)
        check("file name maps to .CA ticker", "POUL.CA" in c)
        check("duplicate id counted once, bad lines skipped",
              c["POUL.CA"] == {"2026-11-12": 2, "2026-11-15": 1}, c)
        check("empty file is measured with no items", c["EMPT.CA"] == {})
        check("non-jsonl ignored", len(c) == 2)
        check("unset dir adds nothing", DC.load_counts(None) == {}
              and DC.load_counts("/nonexistent") == {})


def test_annotate_rows_additive():
    counts = {"POUL.CA": {"2026-11-12": 2}, "EMPT.CA": {}}
    rows = [{"ticker": "POUL.CA", "as_of": "2026-11-12", "horizon": "day"},
            {"ticker": "POUL.CA", "as_of": "2026-11-15", "horizon": "day"},
            {"ticker": "EMPT.CA", "as_of": "2026-11-12", "horizon": "day"},
            {"ticker": "NVDA", "as_of": "2026-11-12", "horizon": "day"}]
    before = [dict(r) for r in rows]
    n = DC.annotate_rows(rows, counts)
    check("three rows have a harvest file", n == 3, n)
    check("session with items", rows[0]["news_count"] == 2
          and rows[0]["has_disclosure"] is True)
    check("session without items is zero, not missing",
          rows[1]["news_count"] == 0 and rows[1]["has_disclosure"] is False)
    check("ticker with an empty file is measured zero",
          rows[2]["news_count"] == 0)
    check("ticker without a file carries no key",
          "news_count" not in rows[3] and "has_disclosure" not in rows[3])
    check("existing keys unchanged", all(
        {k: v for k, v in r.items() if k not in ("news_count",
                                                  "has_disclosure")} == b
        for r, b in zip(rows, before)))
    rows2 = [dict(r) for r in before]
    check("empty counts adds nothing",
          DC.annotate_rows(rows2, {}) == 0 and rows2 == before)


def test_ledger_hook_is_env_gated():
    src = open(os.path.join(HERE, "ledger.py"), encoding="utf-8").read()
    check("hook reads LEDGER_DISCLOSURE_DIR", 'LEDGER_DISCLOSURE_DIR' in src)
    i = src.index('disc_dir = os.environ.get("LEDGER_DISCLOSURE_DIR")')
    j = src.index("if disc_dir:", i)
    k = src.index("annotate_rows", j)
    check("annotation only inside the env check", i < j < k)
    check("hook sits before the ledger dict is built",
          k < src.index('"tool": "calibration-ledger"'))


def main():
    for fn in (test_parse_and_session_rule, test_load_and_dedup,
               test_annotate_rows_additive, test_ledger_hook_is_env_gated):
        fn()
    print("test_disclosure_counts: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
