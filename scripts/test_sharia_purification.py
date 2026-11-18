#!/usr/bin/env python3
"""Unit tests for issue #171: the timing-aware purification
calculator (scripts/sharia_purification.py).

Stdlib only, no network. Fixtures are engine snapshots screened
by the REAL Sharia engine (issue #168); every expected number
below is derived in comments from the fixture inputs and the
engine's published outputs (ratio, per-share), not copied from
the calculator's output.

Hand-computed fixture maths (POUL.CA, FY2025 = 365 days):

AAOIFI snapshot -- total_revenue 100,000,000;
non_compliant_revenue 2,000,000; shares_outstanding
1,789,351,397 (the #170 fixture figures):
  purification ratio     = 2,000,000 / 100,000,000 = 0.02
  purification per share = 2,000,000 / 1,789,351,397
                         = 0.001118 (engine, 6dp)
  verdict compliant-with-purification.

Dividend stream (the second event is the REAL POUL Nov 2026
coupon from the covered-universe fixture, issue #168):
  D1: 0.50/share, ex 2026-05-20, pay 2026-06-03
  D2: 1.90/share, ex 2026-11-16, pay 2026-11-18

With 10,000 shares held:
  D2 dividend purification = 1.90 x 0.02 x 10,000 = 380.00
  D1 + D2                  = 2.40 x 0.02 x 10,000 = 480.00
  capital, 18 days held    = 0.001118 x 18/365 x 10,000
                           = 0.551342
  capital, 3 days          = 0.091890 ; 14 days = 0.428822
  capital, 203 days        = 6.217918 ; 19 days = 0.581973
  capital, 211 days        = 6.462959
  capital, capped at 1.0   = 0.001118 x 10,000     = 11.18

Entitlement convention (stated in the calculator): entitled
iff buy_date < ex_date <= window end.

Run: python3 scripts/test_sharia_purification.py
Exit 0 only when every test passes.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import sharia_engine as se  # noqa: E402
import sharia_purification as sp  # noqa: E402

RESULTS = []


def check(name, fn):
    try:
        fn()
    except Exception as e:
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return
    RESULTS.append((name, True, ""))
    print(f"PASS {name}")


# ---------------------------------------------------------------- fixtures

PERIOD = {"label": "FY2025", "start": "2025-01-01",
          "end": "2025-12-31"}

DIVIDENDS = [
    {"per_share": 0.50, "ex_date": "2026-05-20",
     "pay_date": "2026-06-03"},
    {"per_share": 1.90, "ex_date": "2026-11-16",
     "pay_date": "2026-11-18"},
]

AAOIFI_SNAPSHOT = {
    "ticker": "POUL.CA",
    "statement_period": PERIOD,
    "screening_date": "2027-03-01",
    "activity": {"classification": "permissible",
                 "evidence_source": "test fixture"},
    "financials": {"total_revenue": 100_000_000,
                   "non_compliant_revenue": 2_000_000,
                   "interest_bearing_debt": 400_000_000,
                   "interest_bearing_assets": 100_000_000,
                   "shares_outstanding": 1_789_351_397},
    "market": {"avg_market_value_36m": 2_000_000_000},
    "dividends": DIVIDENDS,
}

EGX33_SNAPSHOT = {
    "ticker": "POUL.CA",
    "statement_period": PERIOD,
    "screening_date": "2027-03-01",
    "activity": {"classification": "permissible",
                 "evidence_source": "test fixture"},
    "financials": {"total_revenue": 100_000_000,
                   "non_compliant_revenue": 2_000_000,
                   "interest_bearing_debt": 300_000_000,
                   "interest_bearing_assets": 200_000_000,
                   "cash_and_liquid_assets": 600_000_000,
                   "total_assets": 1_200_000_000,
                   "shares_outstanding": 1_789_351_397},
    "market": {"avg_market_value_review_period": 900_000_000},
    "dividends": DIVIDENDS,
}

SHARES = 10_000

# One snapshot carries the union of the fields both standards
# read (the data model is one snapshot per ticker per period;
# the per-standard fixtures above are the minimal shapes the
# #170 tests used). AAOIFI on these figures: income 0.02,
# debt 300M/2,000M = 0.15, assets 100M/2,000M = 0.05 -- pass,
# purification ratio 0.02, per share 0.001118 (unchanged: those
# depend only on revenue / non-compliant revenue / shares).
# EGX33: denominator max(1,200M, 900M) = 1,200M; borrowing
# 0.25, investments 100M/1,200M = 0.0833, liquid 0.50 -- pass.
MERGED_SNAPSHOT = {
    "ticker": "POUL.CA",
    "statement_period": PERIOD,
    "screening_date": "2027-03-01",
    "activity": {"classification": "permissible",
                 "evidence_source": "test fixture"},
    "financials": {"total_revenue": 100_000_000,
                   "non_compliant_revenue": 2_000_000,
                   "interest_bearing_debt": 300_000_000,
                   "interest_bearing_assets": 100_000_000,
                   "cash_and_liquid_assets": 600_000_000,
                   "total_assets": 1_200_000_000,
                   "shares_outstanding": 1_789_351_397},
    "market": {"avg_market_value_36m": 2_000_000_000,
               "avg_market_value_review_period": 900_000_000},
    "dividends": DIVIDENDS,
}


def entry(result, standard):
    for e in result["standards"]:
        if e["standard"] == standard:
            return e
    raise AssertionError(f"no entry for {standard}")


def event(entry_, ex_date):
    for ev in entry_["dividend_events"]:
        if ev["ex_date"] == ex_date:
            return ev
    raise AssertionError(f"no event {ex_date}")


# ---------------------------------------------------------------- tests

def test_worked_example_poul_nov2026():
    # Acceptance criterion 1: bought before the ex-date, sold
    # after the pay date -- the Nov 2026 coupon's purification
    # is computed automatically from the event stream.
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-11-02",
                          sell_date="2026-11-20",
                          standards=["AAOIFI"])
    assert result["window"] == {"buy_date": "2026-11-02",
                                "end_date": "2026-11-20",
                                "end_kind": "sell",
                                "days_held": 18}
    e = entry(result, "AAOIFI")
    assert e["status"] == "ok", e
    assert e["screening_verdict"] == "compliant-with-purification"
    assert e["purification"]["ratio"] == 0.02
    assert e["purification"]["per_share"] == 0.001118
    d2 = event(e, "2026-11-16")
    assert d2["entitled"] is True
    assert d2["pay_date"] == "2026-11-18"
    assert d2["purification"] == 380.0
    d1 = event(e, "2026-05-20")
    assert d1["entitled"] is False  # window starts after it
    div = e["components"]["dividends"]
    assert div["amount"] == 380.0 and div["events_counted"] == 1
    cap = e["components"]["capital"]
    assert cap["applies"] is True
    assert cap["method"] == "time_apportioned_per_share"
    assert cap["days_in_period"] == 365
    assert cap["fraction"] == round(18 / 365, 6)
    assert cap["amount"] == 0.551342
    assert e["total"] == 380.551342
    assert e["total_partial"] is False


def test_bought_after_ex_date_contributes_zero():
    # Acceptance criterion 2: bought after the ex-date, that
    # dividend contributes 0 -- and the output shows why.
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-11-17",
                          sell_date="2026-11-20",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    d2 = event(e, "2026-11-16")
    assert d2["entitled"] is False
    assert "bought on or after the ex-date" in d2["reason_en"]
    assert d2["purification"] is None
    div = e["components"]["dividends"]
    assert div["amount"] == 0.0 and div["events_counted"] == 0
    # The capital component still accrues for the 3 days held:
    # a real, complete zero for dividends, not a gap.
    assert e["components"]["capital"]["amount"] == 0.09189
    assert e["total"] == 0.09189
    assert e["status"] == "ok" and e["gaps"] == []


def test_ex_date_boundaries():
    # Bought ON the ex-date: trades without the dividend.
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-11-16",
                          sell_date="2026-11-20",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    assert event(e, "2026-11-16")["entitled"] is False
    assert e["components"]["dividends"]["amount"] == 0.0
    # Sold ON the ex-date: entitlement fixed at the day's start,
    # so the dividend counts. 14 days held -> capital 0.428822.
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-11-02",
                          sell_date="2026-11-16",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    assert event(e, "2026-11-16")["entitled"] is True
    assert e["components"]["dividends"]["amount"] == 380.0
    assert e["components"]["capital"]["amount"] == 0.428822
    assert e["total"] == 380.428822
    # Sold the day BEFORE the ex-date: no entitlement, shown.
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-11-02",
                          sell_date="2026-11-15",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    d2 = event(e, "2026-11-16")
    assert d2["entitled"] is False
    assert "holding ended before the ex-date" in d2["reason_en"]
    assert e["components"]["dividends"]["amount"] == 0.0


def test_window_spanning_two_dividends():
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-05-01",
                          sell_date="2026-11-20",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    assert event(e, "2026-05-20")["purification"] == 100.0
    assert event(e, "2026-11-16")["purification"] == 380.0
    div = e["components"]["dividends"]
    assert div["amount"] == 480.0 and div["events_counted"] == 2
    # 203 days held: 0.001118 x 203/365 x 10,000 = 6.217918.
    assert e["components"]["capital"]["amount"] == 6.217918
    assert e["total"] == 486.217918
    assert e["status"] == "ok"


def test_window_with_no_dividends():
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-12-01",
                          sell_date="2026-12-20",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    assert all(ev["entitled"] is False
               for ev in e["dividend_events"])
    assert e["components"]["dividends"]["amount"] == 0.0
    assert e["components"]["dividends"]["events_counted"] == 0
    # 19 days of capital accrual only.
    assert e["total"] == 0.581973
    assert e["status"] == "ok"


def test_still_held_open_window():
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-11-02",
                          as_of="2026-11-20", standards=["AAOIFI"])
    assert result["window"]["end_kind"] == "as-of"
    e = entry(result, "AAOIFI")
    # Identical figures to the sold case over the same window.
    assert e["total"] == 380.551342
    # A still-held holding whose as-of precedes an ex-date is
    # not yet entitled, and says so.
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2026-11-02",
                          as_of="2026-11-10", standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    d2 = event(e, "2026-11-16")
    assert d2["entitled"] is False
    assert "after the as-of date" in d2["reason_en"]


def test_aaoifi_vs_egx33_rule_difference_named():
    # Acceptance criterion 3: the same window under both
    # standards, side by side, rule difference named.
    result = sp.calculate(MERGED_SNAPSHOT, SHARES, "2026-11-02",
                          sell_date="2026-11-20",
                          standards=["AAOIFI", "EGX33"])
    a = entry(result, "AAOIFI")
    assert a["total"] == 380.551342
    g = entry(result, "EGX33")
    assert g["status"] == "no-purification-rule"
    assert g["total"] is None  # NOT zero: no rule, no figure
    assert g["purification"]["defined"] is False
    assert g["screening_verdict"] == "compliant"
    assert "no purification rule" in \
        g["components"]["dividends"]["reason_en"]
    # Entitlement is a fact independent of the standard: the
    # event is still listed, with no amount under EGX33.
    assert event(g, "2026-11-16")["entitled"] is True
    assert event(g, "2026-11-16")["purification"] is None
    diffs = result["rule_differences"]
    assert diffs, "the rule difference must be named"
    joined = " ".join(d["en"] for d in diffs)
    assert "AAOIFI" in joined and "EGX33" in joined
    assert "no purification rule" in joined
    assert all(d["ar"] for d in diffs)


def test_missing_event_data_is_an_explicit_gap():
    # Acceptance criterion 4a: no dividends field at all -- an
    # explicit gap, no dividend figure, no total. Never a zero
    # built on missing events.
    snap = copy.deepcopy(AAOIFI_SNAPSHOT)
    del snap["dividends"]
    result = sp.calculate(snap, SHARES, "2026-11-02",
                          sell_date="2026-11-20",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    assert e["status"] == "partial"
    assert e["components"]["dividends"]["amount"] is None
    assert e["total"] is None
    assert any("event data is unavailable" in g["en"]
               for g in e["gaps"])
    # The capital component does not depend on events and is
    # still shown on its own.
    assert e["components"]["capital"]["amount"] == 0.551342


def test_window_beyond_event_coverage_is_partial():
    # Acceptance criterion 4b: the stream covers up to the
    # snapshot's screening date (2026-11-17); a window running
    # to 2027-06-01 is computed from known events and marked
    # partial, with the uncovered range named.
    snap = copy.deepcopy(AAOIFI_SNAPSHOT)
    snap["screening_date"] = "2026-11-17"
    result = sp.calculate(snap, SHARES, "2026-11-02",
                          sell_date="2027-06-01",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    assert e["status"] == "partial"
    assert e["total_partial"] is True
    assert any("2026-11-17" in g["en"] and "2027-06-01" in g["en"]
               for g in e["gaps"])
    # Known events still count: 380.00 + 211 days of capital.
    assert e["components"]["dividends"]["amount"] == 380.0
    assert e["total"] == 386.462959


def test_insufficient_data_real_fixture():
    # The repo's real covered-universe snapshot: POUL carries
    # shares + the Nov 2026 event but no financials, so AAOIFI
    # cannot produce a ratio -- insufficient-data with the
    # missing inputs named; the event's entitlement is still
    # determined and shown.
    path = os.path.join(SCRIPTS, "sharia_fixtures",
                        "covered_universe.json")
    with open(path, encoding="utf-8") as fh:
        snap = json.load(fh)[0]
    result = sp.calculate(snap, SHARES, "2026-11-02",
                          sell_date="2026-11-20",
                          standards=["AAOIFI", "EGX33"])
    e = entry(result, "AAOIFI")
    assert e["status"] == "insufficient-data"
    assert e["total"] is None
    assert "total_revenue" in e["missing_inputs"]
    assert "non_compliant_revenue" in e["missing_inputs"]
    d = event(e, "2026-11-16")
    assert d["entitled"] is True and d["per_share"] == 1.9
    assert d["purification"] is None
    assert entry(result, "EGX33")["status"] == \
        "no-purification-rule"


def test_capital_accrual_capped_at_one_period():
    # 902 days held against a 365-day period: the fraction is
    # capped at 1.0 and the cap is flagged, not silent.
    result = sp.calculate(AAOIFI_SNAPSHOT, SHARES, "2024-06-01",
                          sell_date="2026-11-20",
                          standards=["AAOIFI"])
    e = entry(result, "AAOIFI")
    cap = e["components"]["capital"]
    assert cap["days_held"] == 902
    assert cap["fraction"] == 1.0 and cap["capped"] is True
    assert "capped" in cap["reason_en"]
    assert cap["amount"] == 11.18


def test_validation_fails_loudly():
    def refused(**kw):
        try:
            sp.calculate(**kw)
        except ValueError:
            return True
        return False
    base = dict(snapshot=AAOIFI_SNAPSHOT, shares=SHARES,
                buy_date="2026-11-02", sell_date="2026-11-20")
    # DJIM is draft-disabled (issue #169 pin gate), hence an
    # unknown standard for the calculator, like any unimplemented
    # id. (MSCI itself became implemented in #169.)
    assert refused(**{**base, "standards": ["DJIM"]})
    assert refused(**{**base, "standards": []})
    assert refused(**{**base, "shares": 0})
    assert refused(**{**base, "shares": -5})
    assert refused(**{**base, "sell_date": "2026-11-01"})
    assert refused(snapshot=AAOIFI_SNAPSHOT, shares=SHARES,
                   buy_date="2026-11-02")  # no sell, no as-of
    # Case-insensitive ids normalise, as in the #170 contract.
    result = sp.calculate(**{**base, "standards": ["aaoifi"]})
    assert [e["standard"] for e in result["standards"]] == \
        ["AAOIFI"]
    # Default selection = all implemented standards.
    result = sp.calculate(**base)
    assert [e["standard"] for e in result["standards"]] == \
        se.available_standards()


def test_framing_bilingual_everywhere():
    result = sp.calculate(MERGED_SNAPSHOT, SHARES, "2026-11-02",
                          sell_date="2026-11-20",
                          standards=["AAOIFI", "EGX33"])
    assert result["framing_en"] == se.FRAMING_EN
    assert "not a fatwa" in result["framing_en"]
    assert result["framing_ar"] == se.FRAMING_AR
    assert "ليست فتوى" in result["framing_ar"]
    for e in result["standards"]:
        assert e["framing_en"] == se.FRAMING_EN
        assert e["framing_ar"] == se.FRAMING_AR
        for ev in e["dividend_events"]:
            assert ev["reason_en"] and ev["reason_ar"]


def test_cli_end_to_end():
    tmp = tempfile.mkdtemp(prefix="purify-")
    snap_path = os.path.join(tmp, "snapshot.json")
    with open(snap_path, "w", encoding="utf-8") as fh:
        json.dump([AAOIFI_SNAPSHOT], fh)
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS,
                                      "sharia_purification.py"),
         "calculate", "--snapshot", snap_path,
         "--ticker", "POUL.CA", "--shares", "10000",
         "--buy", "2026-11-02", "--sell", "2026-11-20",
         "--standard", "AAOIFI"],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["standards"][0]["total"] == 380.551342
    # Unknown standard refuses via the CLI too.
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS,
                                      "sharia_purification.py"),
         "calculate", "--snapshot", snap_path,
         "--ticker", "POUL.CA", "--shares", "10000",
         "--buy", "2026-11-02", "--sell", "2026-11-20",
         "--standard", "FOO"],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 2
    assert "unknown sharia standard" in proc.stderr
    # Still-held without an as-of date refuses (no wall clock).
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS,
                                      "sharia_purification.py"),
         "calculate", "--snapshot", snap_path,
         "--shares", "10000", "--buy", "2026-11-02"],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 2
    assert "as-of" in proc.stderr


def main():
    check("AC1 worked example: POUL across the Nov 2026 coupon "
          "-- dividend purification computed from the stream",
          test_worked_example_poul_nov2026)
    check("AC2 bought after the ex-date contributes 0, with "
          "the reason shown",
          test_bought_after_ex_date_contributes_zero)
    check("ex-date boundaries: buy on ex-date excluded, sell "
          "on ex-date entitled, sell before excluded",
          test_ex_date_boundaries)
    check("window spanning two dividends sums both",
          test_window_spanning_two_dividends)
    check("window with no dividends: dividend 0, capital only",
          test_window_with_no_dividends)
    check("still-held window resolves against the as-of date",
          test_still_held_open_window)
    check("AC3 AAOIFI vs EGX33 side by side, rule difference "
          "named, EGX33 total null (no rule -- not zero)",
          test_aaoifi_vs_egx33_rule_difference_named)
    check("AC4 missing event data: explicit gap, no figure, "
          "no total", test_missing_event_data_is_an_explicit_gap)
    check("AC4 window beyond event coverage: partial, range "
          "named, known events counted",
          test_window_beyond_event_coverage_is_partial)
    check("real POUL fixture: insufficient-data with missing "
          "inputs named, entitlement still shown",
          test_insufficient_data_real_fixture)
    check("capital accrual capped at one period, cap flagged",
          test_capital_accrual_capped_at_one_period)
    check("validation fails loudly (standard, shares, window, "
          "missing as-of); defaults cover all standards",
          test_validation_fails_loudly)
    check("not-a-fatwa framing in Arabic and English, top "
          "level and per standard",
          test_framing_bilingual_everywhere)
    check("CLI: calculate prints the result; unknown standard "
          "and missing as-of exit 2", test_cli_end_to_end)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\ntest_sharia_purification: {passed}/{len(RESULTS)} "
          f"passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
