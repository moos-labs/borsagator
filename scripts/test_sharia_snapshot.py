#!/usr/bin/env python3
"""Unit tests for the Sharia snapshot extraction rule (issue #330).

Stdlib only, no network. Regression cases are the evidence figures
from #326 run 1 (hidden_files/issue-172/comparison-run-1.md and the
TMGH/PHDC H1-2026 snapshot provenance files) -- no figure is invented
here:

- TMGH: finance-income interest 958,318,757 (3.17% of revenue) plus
  EGP 2,092,779,078 of amortised-cost investment income in other
  income -> 3,051,097,835 (10.11%).
- PHDC: interest-income line 455,606,067 (2.33%) plus EGP 523,193,960
  of notes-receivable discount unwinding in other revenues ->
  978,800,027 (5.01%).

Coverage: both regression numerators and both ratios on the substance
basis; the finance-income-only (as-harvested) path still reproducing
the old figures (3.17% / 2.33%) from the same harvested lines; the
per-line breakdown summing to the numerator with every exclusion
reasoned; the rule failing loudly on unknown kinds, missing bases,
bad amounts and contradictory as_harvested flags; the committed
rebuilt snapshots matching the rule output; and the engine verdict
flip -- the rebuilt snapshots fail the MSCI/FTSE/EGX33 income screen
where the as-harvested ones pass it.

Usage: python3 scripts/test_sharia_snapshot.py
Exit 0 only when every test passes.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import sharia_engine as se  # noqa: E402
import sharia_snapshot as ss  # noqa: E402

SNAP_DIR = os.path.join(ROOT, "sharia", "snapshots")

# Evidence figures, #326 run 1 (see module docstring). Hand-computed:
# TMGH 3,051,097,835 / 30,192,000,051 = 10.1052% -> 10.11%;
#      958,318,757 / 30,192,000,051 = 3.1742% -> 3.17%.
# PHDC 978,800,027 / 19,528,117,727 = 5.0123% -> 5.01%;
#      455,606,067 / 19,528,117,727 = 2.3329% -> 2.33%.
TMGH_TOTAL = 3051097835
TMGH_AS_HARVESTED = 958318757
TMGH_REVENUE = 30192000051
PHDC_TOTAL = 978800027
PHDC_AS_HARVESTED = 455606067
PHDC_REVENUE = 19528117727

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


def _load_lines(ticker):
    with open(os.path.join(
            SNAP_DIR, "%s-h1-2026-interest-income-lines.json" % ticker),
            encoding="utf-8") as fh:
        return json.load(fh)


def _load_snapshot(ticker):
    with open(os.path.join(
            SNAP_DIR, "%s-h1-2026-snapshot.json" % ticker),
            encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, list) and len(data) == 1
    return data[0]


def _ratio(row, ratio_id):
    for entry in row["ratios"]:
        if entry["id"] == ratio_id:
            return entry
    raise AssertionError("ratio %s missing from row" % ratio_id)


@check("TMGH substance numerator and ratio (10.11%)")
def _():
    total, breakdown = ss.build_non_compliant_revenue(_load_lines("tmgh"))
    assert total == TMGH_TOTAL, total
    assert round(ss.income_ratio_pct(total, TMGH_REVENUE), 2) == 10.11
    included = [b for b in breakdown if b["included"]]
    assert sum(b["amount_egp"] for b in included) == total
    assert [b["label"] for b in included] == [
        "Credit interest - banks current accounts",
        "Time deposits interest",
        "Income from financial investment at amortized cost"]
    assert all(b.get("category") and b.get("reason") for b in breakdown)


@check("TMGH as-harvested path still yields 3.17%")
def _():
    lines = _load_lines("tmgh")
    assert ss.as_harvested_total(lines) == TMGH_AS_HARVESTED
    assert round(ss.income_ratio_pct(TMGH_AS_HARVESTED, TMGH_REVENUE),
                 2) == 3.17


@check("PHDC substance numerator and ratio (5.01%)")
def _():
    total, breakdown = ss.build_non_compliant_revenue(_load_lines("phdc"))
    assert total == PHDC_TOTAL, total
    assert round(ss.income_ratio_pct(total, PHDC_REVENUE), 2) == 5.01
    included = [b for b in breakdown if b["included"]]
    assert sum(b["amount_egp"] for b in included) == total
    assert [b["label"] for b in included] == [
        "Credit interest and Returns on investments Measured at "
        "Amortized cost",
        "Amortization of discount on notes receivables"]


@check("PHDC as-harvested path still yields 2.33%")
def _():
    lines = _load_lines("phdc")
    assert ss.as_harvested_total(lines) == PHDC_AS_HARVESTED
    assert round(ss.income_ratio_pct(PHDC_AS_HARVESTED, PHDC_REVENUE),
                 2) == 2.33


@check("Excluded lines stay excluded, with reasons (both tickers)")
def _():
    for ticker in ("tmgh", "phdc"):
        _, breakdown = ss.build_non_compliant_revenue(_load_lines(ticker))
        excluded = [b for b in breakdown if not b["included"]]
        assert excluded, ticker
        assert all(b["category"] == "excluded_not_interest"
                   and b["reason"] for b in excluded), ticker
    _, tmgh = ss.build_non_compliant_revenue(_load_lines("tmgh"))
    pv = [b for b in tmgh
          if b["kind"] == "present_value_discount"]
    assert len(pv) == 1 and pv[0]["amount_egp"] == 78975498
    assert not pv[0]["included"]
    fvpl = [b for b in tmgh if b["kind"] == "fvpl_gain"]
    assert len(fvpl) == 1 and not fvpl[0]["included"]
    _, phdc = ss.build_non_compliant_revenue(_load_lines("phdc"))
    fees = [b for b in phdc if b["kind"] == "other_non_interest"]
    assert len(fees) == 1 and fees[0]["amount_egp"] == 547790260
    assert not fees[0]["included"] and fees[0].get("basis")


@check("Rule fails loudly on bad input")
def _():
    base = {"label": "X", "amount_egp": 100,
            "presented_in": "other income", "kind": "credit_interest"}
    for bad, why in [
            (dict(base, kind="nope"), "unknown kind"),
            (dict(base, kind="interest_like_other"), "basis required"),
            (dict(base, kind="other_non_interest"), "basis required"),
            (dict(base, amount_egp=-5), "negative amount"),
            (dict(base, amount_egp=10.5), "non-integer amount"),
            (dict(base, amount_egp="100"), "string amount"),
            (dict(base, kind="fvpl_gain", as_harvested=True),
             "as_harvested on an excluded line"),
    ]:
        try:
            ss.classify_line(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("no ValueError: %s" % why)
    ok = ss.classify_line(dict(
        base, kind="interest_like_other", basis="note 12 wording"))
    assert ok["included"] is True


@check("Zero denominator yields None, never a silent pass")
def _():
    assert ss.income_ratio_pct(100, 0) is None
    assert ss.income_ratio_pct(100, None) is None


@check("Committed rebuilt snapshots match the rule output")
def _():
    for ticker, total, as_harvested, revenue, pct, pct_old in (
            ("tmgh", TMGH_TOTAL, TMGH_AS_HARVESTED, TMGH_REVENUE,
             10.11, 3.17),
            ("phdc", PHDC_TOTAL, PHDC_AS_HARVESTED, PHDC_REVENUE,
             5.01, 2.33)):
        snap = _load_snapshot(ticker)
        fin = snap["financials"]
        assert fin["non_compliant_revenue"] == total, ticker
        assert fin["non_compliant_revenue_as_harvested"] == as_harvested
        assert round(ss.income_ratio_pct(total, revenue), 2) == pct
        assert round(ss.income_ratio_pct(as_harvested, revenue),
                     2) == pct_old
        lines = _load_lines(ticker)
        rebuilt = ss.rebuild_snapshot(
            {k: v for k, v in snap.items()
             if k not in ("non_compliant_revenue_breakdown",
                          "non_compliant_revenue_rule")},
            lines)
        # Rebuilding the stored snapshot's own lines reproduces it.
        assert (rebuilt["financials"]["non_compliant_revenue"]
                == fin["non_compliant_revenue"])
        assert rebuilt["non_compliant_revenue_breakdown"] == \
            snap["non_compliant_revenue_breakdown"]
        stored = snap["non_compliant_revenue_breakdown"]
        assert sum(b["amount_egp"] for b in stored
                   if b["included"]) == total
        assert sum(b["amount_egp"] for b in stored
                   if b["included"] and b.get("as_harvested")) \
            == as_harvested
        assert snap["non_compliant_revenue_rule"]["rule_version"] == \
            ss.RULE_VERSION


@check("Engine verdict flip: rebuilt fails MSCI/FTSE/EGX33 income, "
       "as-harvested passes it")
def _():
    # As-harvested verdicts, hand-checked against the engine's ratios:
    # PHDC already fails FTSE on receivables+cash (60.98% vs the 50%
    # limit) as harvested -- the income flip is the #330 change, not
    # the whole verdict. EGX33 publishes no purification rule, so a
    # passing as-harvested screen there is plain "compliant".
    expected_old = {
        "tmgh": {"MSCI": "compliant-with-purification",
                 "FTSE": "compliant-with-purification",
                 "EGX33": "compliant"},
        "phdc": {"MSCI": "compliant-with-purification",
                 "FTSE": "non-compliant",
                 "EGX33": "compliant"},
    }
    for ticker in ("tmgh", "phdc"):
        snap = _load_snapshot(ticker)
        old = copy.deepcopy(snap)
        old["financials"]["non_compliant_revenue"] = \
            snap["financials"]["non_compliant_revenue_as_harvested"]
        for standard in ("MSCI", "FTSE", "EGX33"):
            ruleset = se.load_ruleset(standard)
            new_row = se.screen(snap, ruleset)
            old_row = se.screen(old, ruleset)
            assert _ratio(new_row, "non_compliant_income")["passed"] \
                is False, (ticker, standard, "rebuilt must fail income")
            assert _ratio(old_row, "non_compliant_income")["passed"] \
                is True, (ticker, standard, "as-harvested must pass income")
            assert new_row["verdict"] == "non-compliant", \
                (ticker, standard, new_row["verdict"])
            assert old_row["verdict"] == expected_old[ticker][standard], \
                (ticker, standard, old_row["verdict"])


@check("rebuild_snapshot does not mutate its input")
def _():
    snap = _load_snapshot("tmgh")
    before = copy.deepcopy(snap)
    ss.rebuild_snapshot(snap, _load_lines("tmgh"))
    assert snap == before


def main():
    failed = 0
    for name, fn in CHECKS:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 -- report and continue
            failed += 1
            print("FAIL %s: %s: %s" % (name, type(exc).__name__, exc))
        else:
            print("PASS %s" % name)
    print("\ntest_sharia_snapshot: %d/%d passed"
          % (len(CHECKS) - failed, len(CHECKS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
