#!/usr/bin/env python3
"""Unit tests for the Sharia screening engine core (issue #168).

Stdlib only, no network. Every fixture is hand-computed: the expected
ratio values and verdicts are derived in the comments next to each
fixture, from the published criteria in the rule-set files
(AAOIFI Std 21 as operationalised by Musaffa / Faisal Securities;
EGX33 methodology per the EGX Sharia Supervisory Committee).

Coverage: both rule sets' thresholds just under / at / just over the
boundary; both AAOIFI denominator variants (spot market cap vs
trailing 36-month average market value), including a snapshot whose
verdict flips between them; the EGX33 whichever-is-greater base in
both directions; missing-data behaviour (a missing input yields the
first-class insufficient-data verdict with the input named, never a
silent pass); the decisive prohibited-activity screen; purification
ratio and per-share maths; market aggregates derived from a
market-cap series; and the real covered ticker POUL.CA, whose fleet
data currently carries only shares outstanding + the Nov 2026
dividend event, so both standards must answer insufficient-data
naming what is missing.

Usage: python3 scripts/test_sharia_engine.py
Exit 0 only when every test passes.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import sharia_engine as se

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


AAOIFI = se.load_ruleset("AAOIFI")
EGX33 = se.load_ruleset("EGX33")


def snap(financials=None, market=None, activity="permissible",
         ticker="ACME.CA", period=None, screening_date="2026-11-17",
         dividends=None):
    return {
        "ticker": ticker,
        "statement_period": period or {"label": "FY2025",
                                       "start": "2025-01-01",
                                       "end": "2025-12-31"},
        "screening_date": screening_date,
        "activity": ({"classification": activity,
                      "evidence_source": "test fixture"}
                     if activity is not None else {}),
        "financials": financials or {},
        "market": market or {},
        "dividends": dividends or [],
    }


def ratio(row, rid):
    for r in row["ratios"]:
        if r["id"] == rid:
            return r
    raise AssertionError("no ratio %s in row" % rid)


# ------------------------------------------------------------ AAOIFI

def test_aaoifi_compliant_with_purification():
    # revenue 200, non-compliant 8 -> 8/200 = 0.04 <= 0.05 pass
    # debt 270 / avg36m 1000 = 0.27 <= 0.30 pass
    # interest assets 250 / 1000 = 0.25 <= 0.30 pass
    # non-compliant revenue > 0 -> compliant-with-purification
    # purification ratio 0.04; per share 8 / 400 shares = 0.02
    s = snap(financials={"total_revenue": 200, "non_compliant_revenue": 8,
                         "interest_bearing_debt": 270,
                         "interest_bearing_assets": 250,
                         "shares_outstanding": 400},
             market={"avg_market_value_36m": 1000})
    row = se.screen(s, AAOIFI)
    assert row["verdict"] == "compliant-with-purification", row["verdict"]
    assert ratio(row, "non_compliant_income")["value"] == 0.04
    assert ratio(row, "interest_bearing_debt")["value"] == 0.27
    assert ratio(row, "interest_bearing_assets")["value"] == 0.25
    assert row["purification"]["ratio"] == 0.04
    assert row["purification"]["per_share"] == 0.02
    assert row["parameters"]["denominator_variant"] == "avg36m"
    assert row["missing_inputs"] == []


def test_aaoifi_fully_compliant_no_purification():
    # non-compliant revenue exactly 0 -> plain compliant, purification 0
    s = snap(financials={"total_revenue": 200, "non_compliant_revenue": 0,
                         "interest_bearing_debt": 100,
                         "interest_bearing_assets": 100,
                         "shares_outstanding": 400},
             market={"avg_market_value_36m": 1000})
    row = se.screen(s, AAOIFI)
    assert row["verdict"] == "compliant", row["verdict"]
    assert row["purification"]["ratio"] == 0.0
    assert row["purification"]["per_share"] == 0.0


def test_aaoifi_income_boundary():
    base = {"total_revenue": 200, "interest_bearing_debt": 0,
            "interest_bearing_assets": 0, "shares_outstanding": 100}
    # at the boundary: 10/200 = 0.05 exactly -> pass (<=)
    s = snap(financials=dict(base, non_compliant_revenue=10),
             market={"avg_market_value_36m": 1000})
    row = se.screen(s, AAOIFI)
    assert ratio(row, "non_compliant_income")["passed"] is True
    assert row["verdict"] == "compliant-with-purification"
    # just over: 10.02/200 = 0.0501 -> fail -> non-compliant
    s = snap(financials=dict(base, non_compliant_revenue=10.02),
             market={"avg_market_value_36m": 1000})
    row = se.screen(s, AAOIFI)
    assert ratio(row, "non_compliant_income")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_aaoifi_debt_boundary():
    base = {"total_revenue": 200, "non_compliant_revenue": 0,
            "interest_bearing_assets": 0, "shares_outstanding": 100}
    # at the boundary: 300/1000 = 0.30 exactly -> pass
    s = snap(financials=dict(base, interest_bearing_debt=300),
             market={"avg_market_value_36m": 1000})
    assert se.screen(s, AAOIFI)["verdict"] == "compliant"
    # just over: 301/1000 = 0.301 -> fail
    s = snap(financials=dict(base, interest_bearing_debt=301),
             market={"avg_market_value_36m": 1000})
    row = se.screen(s, AAOIFI)
    assert ratio(row, "interest_bearing_debt")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_aaoifi_denominator_variants_flip_verdict():
    # debt 320: vs spot market cap 1000 -> 0.32 FAIL;
    #           vs 36m average 1200 -> 0.266667 PASS. Same financials.
    fin = {"total_revenue": 200, "non_compliant_revenue": 0,
           "interest_bearing_debt": 320, "interest_bearing_assets": 0,
           "shares_outstanding": 100}
    mkt = {"spot_market_cap": 1000, "avg_market_value_36m": 1200}
    row_spot = se.screen(snap(financials=fin, market=mkt), AAOIFI,
                         {"denominator_variant": "spot"})
    assert row_spot["verdict"] == "non-compliant", row_spot["verdict"]
    assert ratio(row_spot, "interest_bearing_debt")["value"] == 0.32
    assert ratio(row_spot, "interest_bearing_debt")["denominator"] == 1000
    assert "spot" in ratio(row_spot, "interest_bearing_debt")[
        "denominator_base"]
    row_avg = se.screen(snap(financials=fin, market=mkt), AAOIFI,
                        {"denominator_variant": "avg36m"})
    assert row_avg["verdict"] == "compliant", row_avg["verdict"]
    assert ratio(row_avg, "interest_bearing_debt")["value"] == 0.266667
    assert row_avg["parameters"]["denominator_variant"] == "avg36m"


def test_aaoifi_invalid_parameters_rejected():
    s = snap(financials={"total_revenue": 200})
    for bad in ({"denominator_variant": "weekly"}, {"bogus": 1}):
        try:
            se.screen(s, AAOIFI, bad)
        except ValueError:
            continue
        raise AssertionError("params %r not rejected" % (bad,))


# ------------------------------------------------------------ EGX33

def _egx33_fin(**over):
    fin = {"total_revenue": 200, "non_compliant_revenue": 8,
           "interest_bearing_debt": 320, "interest_bearing_assets": 330,
           "cash_and_liquid_assets": 560, "total_assets": 800,
           "shares_outstanding": 100}
    fin.update(over)
    return fin


def test_egx33_whichever_greater_uses_market_value():
    # base = max(total_assets 800, review-period avg market value 1000)
    #      = 1000. On total assets alone borrowing would be 320/800 =
    # 0.40 (fail); on the correct greater base it is 0.32 (pass).
    # investments 330/1000 = 0.33 at boundary -> pass.
    # liquid 560/800 = 0.70 at boundary -> pass. income 8/200 = 0.04.
    s = snap(financials=_egx33_fin(),
             market={"avg_market_value_review_period": 1000})
    row = se.screen(s, EGX33)
    assert row["verdict"] == "compliant", row["verdict"]
    assert ratio(row, "interest_bearing_borrowing")["denominator"] == 1000
    assert ratio(row, "interest_bearing_borrowing")["value"] == 0.32
    assert ratio(row, "interest_bearing_investments")["value"] == 0.33
    assert ratio(row, "interest_bearing_investments")["passed"] is True
    assert ratio(row, "liquid_assets")["value"] == 0.7
    assert ratio(row, "liquid_assets")["passed"] is True


def test_egx33_whichever_greater_uses_total_assets():
    # base = max(total_assets 1200, avg market value 900) = 1200.
    # borrowing 396/1200 = 0.33 at boundary -> pass.
    fin = _egx33_fin(total_assets=1200, interest_bearing_debt=396,
                     interest_bearing_assets=0, cash_and_liquid_assets=0)
    s = snap(financials=fin, market={"avg_market_value_review_period": 900})
    row = se.screen(s, EGX33)
    assert ratio(row, "interest_bearing_borrowing")["denominator"] == 1200
    assert ratio(row, "interest_bearing_borrowing")["value"] == 0.33
    assert row["verdict"] == "compliant", row["verdict"]


def test_egx33_borrowing_just_over():
    # 340/1000 = 0.34 > 0.33 -> fail -> non-compliant
    fin = _egx33_fin(interest_bearing_debt=340)
    s = snap(financials=fin, market={"avg_market_value_review_period": 1000})
    row = se.screen(s, EGX33)
    assert ratio(row, "interest_bearing_borrowing")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_egx33_liquid_just_over():
    # 561/800 = 0.70125 > 0.70 -> fail -> non-compliant
    fin = _egx33_fin(cash_and_liquid_assets=561)
    s = snap(financials=fin, market={"avg_market_value_review_period": 1000})
    row = se.screen(s, EGX33)
    assert ratio(row, "liquid_assets")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_egx33_income_operative_five_percent():
    # 14/200 = 0.07: fails the operative 5% limit (it would pass the
    # 10% figure from June 2024 launch coverage -- that figure is a
    # documented conflict in the rule set, NOT the encoded threshold).
    fin = _egx33_fin(non_compliant_revenue=14)
    s = snap(financials=fin, market={"avg_market_value_review_period": 1000})
    row = se.screen(s, EGX33)
    assert ratio(row, "non_compliant_income")["threshold"] == 0.05
    assert ratio(row, "non_compliant_income")["passed"] is False
    assert row["verdict"] == "non-compliant"
    conflicts = EGX33["documented_conflicts"]
    assert len(conflicts) == 1
    assert conflicts[0]["operative_value"] == 0.05
    assert conflicts[0]["conflicting_value"] == 0.10


def test_egx33_no_purification_rule():
    # EGX publishes no purification rule: the outputs are null, and a
    # passing company with non-compliant revenue > 0 is plain
    # "compliant" (the with-purification verdict does not exist here).
    s = snap(financials=_egx33_fin(),
             market={"avg_market_value_review_period": 1000})
    row = se.screen(s, EGX33)
    assert row["purification"]["defined"] is False
    assert row["purification"]["ratio"] is None
    assert row["purification"]["per_share"] is None
    assert row["verdict"] == "compliant"


# ------------------------------------------------------------ missing data

def test_missing_input_named_insufficient_data():
    # interest_bearing_debt absent -> insufficient-data, named; the
    # ratio itself is uncomputable, never a silent pass.
    fin = {"total_revenue": 200, "non_compliant_revenue": 0,
           "interest_bearing_assets": 0, "shares_outstanding": 100}
    s = snap(financials=fin, market={"avg_market_value_36m": 1000})
    row = se.screen(s, AAOIFI)
    assert row["verdict"] == "insufficient-data", row["verdict"]
    assert "interest_bearing_debt" in row["missing_inputs"]
    r = ratio(row, "interest_bearing_debt")
    assert r["value"] is None and r["passed"] is None
    assert r["missing"] == ["interest_bearing_debt"]


def test_missing_activity_insufficient_data():
    fin = {"total_revenue": 200, "non_compliant_revenue": 0,
           "interest_bearing_debt": 0, "interest_bearing_assets": 0,
           "shares_outstanding": 100}
    s = snap(financials=fin, market={"avg_market_value_36m": 1000},
             activity=None)
    row = se.screen(s, AAOIFI)
    assert row["verdict"] == "insufficient-data"
    assert "activity.classification" in row["missing_inputs"]


def test_missing_market_aggregate_named():
    # default AAOIFI variant needs avg_market_value_36m; absent ->
    # insufficient-data naming that aggregate (not the unused spot).
    fin = {"total_revenue": 200, "non_compliant_revenue": 0,
           "interest_bearing_debt": 0, "interest_bearing_assets": 0,
           "shares_outstanding": 100}
    row = se.screen(snap(financials=fin, market={}), AAOIFI)
    assert row["verdict"] == "insufficient-data"
    assert "avg_market_value_36m" in row["missing_inputs"]
    assert "spot_market_cap" not in row["missing_inputs"]


def test_prohibited_activity_decisive():
    # perfect ratios, prohibited activity -> non-compliant
    fin = {"total_revenue": 200, "non_compliant_revenue": 0,
           "interest_bearing_debt": 0, "interest_bearing_assets": 0,
           "cash_and_liquid_assets": 0, "total_assets": 800,
           "shares_outstanding": 100}
    s = snap(financials=fin, activity="prohibited",
             market={"avg_market_value_36m": 1000,
                     "avg_market_value_review_period": 1000})
    assert se.screen(s, AAOIFI)["verdict"] == "non-compliant"
    assert se.screen(s, EGX33)["verdict"] == "non-compliant"
    # ... and decisive even when financials are also missing (the
    # missing inputs are still named in the row for audit)
    row = se.screen(snap(financials={}, activity="prohibited"), AAOIFI)
    assert row["verdict"] == "non-compliant"
    assert "total_revenue" in row["missing_inputs"]


def test_zero_denominator_not_silent():
    # total_revenue present but 0: the income ratio is not computable;
    # the row says so instead of dividing or passing silently.
    fin = {"total_revenue": 0, "non_compliant_revenue": 0,
           "interest_bearing_debt": 0, "interest_bearing_assets": 0,
           "shares_outstanding": 100}
    row = se.screen(snap(financials=fin,
                         market={"avg_market_value_36m": 1000}), AAOIFI)
    assert row["verdict"] == "insufficient-data"
    assert ratio(row, "non_compliant_income")["error"] is not None


# ------------------------------------------------------------ series

def test_series_derived_aggregates():
    # points: 2024-01-15 -> 900, 2025-06-15 -> 1100, 2026-11-16 -> 1234
    # screening 2026-11-17; 36-month window starts 2023-11-17, so all
    # three points count: avg36m = (900+1100+1234)/3 = 1078.
    # spot = latest point on/before screening = 1234.
    # statement period 2025 contains only the 1100 point -> 1100.
    series = [{"date": "2024-01-15", "market_cap": 900},
              {"date": "2025-06-15", "market_cap": 1100},
              {"date": "2026-11-16", "market_cap": 1234}]
    s = snap(financials={}, market={"market_cap_series": series})
    aggs = se._market_aggregates(s)
    assert aggs["spot_market_cap"] == (1234, "series"), aggs
    assert aggs["avg_market_value_36m"] == (1078.0, "series"), aggs
    # 24-month window starts 2024-11-17, so the 2024-01-15 point
    # falls outside it: avg24m = (1100+1234)/2 = 1167 (DJIM's
    # trailing window, issue #169).
    assert aggs["avg_market_value_24m"] == (1167.0, "series"), aggs
    assert aggs["avg_market_value_review_period"] == (1100, "series"), aggs
    # an explicit aggregate wins over the series-derived one
    s2 = snap(financials={}, market={"market_cap_series": series,
                                     "avg_market_value_36m": 2000})
    assert se._market_aggregates(s2)["avg_market_value_36m"] == \
        (2000, "market")


# ------------------------------------------------------------ POUL

def test_poul_real_ticker_insufficient_data():
    # The currently covered universe: POUL.CA. Fleet data today
    # carries shares outstanding (1,789,351,397 post-merger) and the
    # Nov 2026 dividend event (coupon 1.90, ex 2026-11-16, pay
    # 2026-11-18) -- but no activity classification and no balance
    # sheet. Both standards must answer insufficient-data and name
    # what is missing; shares must NOT be reported missing.
    path = os.path.join(SCRIPTS, "sharia_fixtures", "covered_universe.json")
    with open(path, encoding="utf-8") as fh:
        snapshots = json.load(fh)
    assert [s["ticker"] for s in snapshots] == ["POUL.CA"]
    for ruleset in (AAOIFI, EGX33):
        row = se.screen(snapshots[0], ruleset)
        assert row["verdict"] == "insufficient-data", row
        assert "activity.classification" in row["missing_inputs"]
        assert "total_revenue" in row["missing_inputs"]
        assert "shares_outstanding" not in row["missing_inputs"]
        divs = row["inputs"]["dividends"]
        assert len(divs) == 1 and divs[0]["per_share"] == 1.90
        assert divs[0]["ex_date"] == "2026-11-16"
    egx_row = se.screen(snapshots[0], EGX33)
    assert "total_assets" in egx_row["missing_inputs"]
    assert "cash_and_liquid_assets" in egx_row["missing_inputs"]


# ------------------------------------------------------------ tables / CLI

def test_screen_table_shape_and_framing():
    snaps = [snap(ticker="ZZZ.CA"), snap(ticker="AAA.CA")]
    table = se.screen_table(snaps, AAOIFI, generated_at="2026-11-17T00:00:00Z")
    assert table["schema"] == se.SCHEMA
    assert table["engine_version"] == se.ENGINE_VERSION
    assert table["generated_at"] == "2026-11-17T00:00:00Z"
    assert table["standard"]["id"] == "AAOIFI"
    assert table["standard"]["ruleset_version"] == "1.0.0"
    assert [r["ticker"] for r in table["rows"]] == ["AAA.CA", "ZZZ.CA"]
    for row in table["rows"]:
        assert row["ruleset_version"] == "1.0.0"
        assert "fatwa" in row["framing_en"]
        assert "فتوى" in row["framing_ar"]


def test_rulesets_are_declarative_files():
    # Issue #169 added MSCI, MSCI_M, FTSE and ISLAMICLY as further
    # declarative files, and pinned S&P Shariah / DJIM from S&P
    # DJI's own November 2026 methodology documents (the drafts
    # that shipped disabled under scripts/sharia_rules_draft/ are
    # gone -- the pinned packs live here now).
    assert se.available_standards() == [
        "AAOIFI", "DJIM", "EGX33", "FTSE", "ISLAMICLY", "MSCI",
        "MSCI_M", "SP_SHARIAH"]
    assert len(AAOIFI["ratios"]) == 3 and len(EGX33["ratios"]) == 4
    for rs in (AAOIFI, EGX33):
        assert rs["ruleset_version"] == "1.0.0"
        assert rs["sources"], rs["standard_id"]
        assert rs["activity_screen"]["required"] is True


def test_cli_writes_tables():
    inputs = os.path.join(SCRIPTS, "sharia_fixtures", "covered_universe.json")
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "sharia_engine.py"),
             "screen", "--inputs", inputs, "--out-dir", td],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        for std in ("aaoifi", "egx33"):
            path = os.path.join(td, "verdicts-%s.json" % std)
            assert os.path.exists(path), path
            with open(path, encoding="utf-8") as fh:
                table = json.load(fh)
            assert table["rows"][0]["ticker"] == "POUL.CA"
            assert table["rows"][0]["verdict"] == "insufficient-data"
            assert table["generated_at"]


def main():
    tests = [
        ("A1 purification verdict", test_aaoifi_compliant_with_purification),
        ("A2 fully compliant", test_aaoifi_fully_compliant_no_purification),
        ("A3 income boundary", test_aaoifi_income_boundary),
        ("A4 debt boundary", test_aaoifi_debt_boundary),
        ("A5 denominator variants flip",
         test_aaoifi_denominator_variants_flip_verdict),
        ("A6 invalid params rejected", test_aaoifi_invalid_parameters_rejected),
        ("E1 greater base = market value",
         test_egx33_whichever_greater_uses_market_value),
        ("E2 greater base = total assets",
         test_egx33_whichever_greater_uses_total_assets),
        ("E3 borrowing just over", test_egx33_borrowing_just_over),
        ("E4 liquid just over", test_egx33_liquid_just_over),
        ("E5 operative 5% + conflict doc",
         test_egx33_income_operative_five_percent),
        ("E6 no purification rule", test_egx33_no_purification_rule),
        ("M1 missing input named", test_missing_input_named_insufficient_data),
        ("M2 missing activity", test_missing_activity_insufficient_data),
        ("M3 missing aggregate named", test_missing_market_aggregate_named),
        ("M4 prohibited decisive", test_prohibited_activity_decisive),
        ("M5 zero denominator", test_zero_denominator_not_silent),
        ("S1 series aggregates", test_series_derived_aggregates),
        ("P1 POUL insufficient-data", test_poul_real_ticker_insufficient_data),
        ("T1 table shape + framing", test_screen_table_shape_and_framing),
        ("T2 declarative rule sets", test_rulesets_are_declarative_files),
        ("T3 CLI writes tables", test_cli_writes_tables),
    ]
    for name, fn in tests:
        check(name, fn)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        for name, _ok, detail in failed:
            print(f"  FAILED: {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
