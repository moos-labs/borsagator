#!/usr/bin/env python3
"""Unit tests for issue #169: the remaining Sharia standard packs.

Stdlib only, no network. Every fixture is hand-computed: expected
ratio values and verdicts are derived in the comments from the
published criteria in the rule-set files --

  MSCI / MSCI_M : MSCI Islamic Index Series Methodology, May 2025
                  (MSCI Inc.), sections 2.1-2.3, threshold tables
                  2.2.1 (total assets) and 2.2.2 (average market
                  capitalisation, 36 months).
  FTSE          : FTSE Russell's published Yasaar screening
                  criteria (index factsheet, data as at 2026-10-30;
                  Yasaar Shariah Supervisory Board Opinion,
                  2025-02-03).
  ISLAMICLY     : Islamicly's own screening criteria page (its
                  Leverage section's < 30% cash figure is the
                  operative one; the 33% figure in its Cash
                  section is the documented conflict).
  SP_SHARIAH    : S&P Shariah Indices Methodology, November
                  2026 (S&P Dow Jones Indices), as revised
                  effective 2026-09-18: leverage and cash each
                  < 30% of the 36-month average market value of
                  equity; non-permissible income (incl. ALL
                  interest income) < 5%. The pre-2023 receivables
                  screen (< 49%) is abolished and NOT encoded.
  DJIM          : Dow Jones Islamic Market Indices Methodology,
                  November 2026 (S&P Dow Jones Indices),
                  Appendix A screens as revised effective
                  2026-09-18: total interest-bearing debt and
                  cash + interest-bearing securities each < 30%
                  of the trailing 24-month average market
                  capitalisation; non-permissible revenue < 5%.

S&P Shariah and DJIM were pinned once S&P DJI's own current
methodology documents reached the build environment (supplied
2026-11-18; spglobal.com itself is blocked there). They shipped
as draft-disabled files under scripts/sharia_rules_draft/ until
then; the drafts are gone and the tests below prove the pinned
packs are live, with the buffer/hysteresis rule recorded as
methodology metadata, never applied to a point-in-time verdict.

Usage: python3 scripts/test_sharia_packs.py
Exit 0 only when every test passes.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import sharia_engine as se
import sharia_diff as sd

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


MSCI = se.load_ruleset("MSCI")
MSCI_M = se.load_ruleset("MSCI_M")
FTSE = se.load_ruleset("FTSE")
ISLAMICLY = se.load_ruleset("ISLAMICLY")
AAOIFI = se.load_ruleset("AAOIFI")
EGX33 = se.load_ruleset("EGX33")
SP = se.load_ruleset("SP_SHARIAH")
DJIM = se.load_ruleset("DJIM")

PERIOD = {"label": "FY2025", "start": "2025-01-01",
          "end": "2025-12-31"}


def snap(financials=None, market=None, activity="permissible",
         ticker="ACME.CA", dividends=None):
    return {
        "ticker": ticker,
        "statement_period": PERIOD,
        "screening_date": "2026-11-17",
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


# ------------------------------------------------------------ MSCI
# Denominator total assets 10,000 throughout, so the published
# 33.33% line sits at 3,333 and the 70% line at 7,000.

def _msci_fin(**over):
    fin = {"total_revenue": 10000, "non_compliant_revenue": 400,
           "interest_bearing_debt": 3000,
           "interest_bearing_assets": 1000,
           "cash_and_liquid_assets": 2000,
           "accounts_receivable": 4000, "total_assets": 10000}
    fin.update(over)
    return fin


def test_msci_compliant_with_purification_no_shares_needed():
    # income 400/10000 = 0.04 <= 0.05 pass
    # debt 3000/10000 = 0.30 <= 0.3333 pass
    # cash composite (2000 + 1000)/10000 = 0.30 <= 0.3333 pass
    # receivables+cash (4000 + 2000)/10000 = 0.60 <= 0.70 pass
    # non-compliant revenue > 0 and MSCI publishes dividend
    # purification (the DAF, section 2.3) -> the verdict is
    # compliant-with-purification, ratio = 1 - DAF = 0.04.
    # The snapshot deliberately carries NO shares_outstanding:
    # MSCI defines a purification RATIO only, so shares are not a
    # required input and per_share stays null.
    row = se.screen(snap(financials=_msci_fin()), MSCI)
    assert row["verdict"] == "compliant-with-purification", row
    assert row["missing_inputs"] == [], row["missing_inputs"]
    assert row["purification"]["defined"] is True
    assert row["purification"]["ratio"] == 0.04
    assert row["purification"]["per_share"] is None
    assert row["purification"]["per_share_definition"] is None


def test_msci_debt_boundary():
    # at the printed line: 3333/10000 = 0.3333 exactly -> pass (le)
    row = se.screen(snap(financials=_msci_fin(
        interest_bearing_debt=3333)), MSCI)
    assert ratio(row, "total_debt")["value"] == 0.3333
    assert ratio(row, "total_debt")["passed"] is True
    # just over: 3334/10000 = 0.3334 -> fail
    row = se.screen(snap(financials=_msci_fin(
        interest_bearing_debt=3334)), MSCI)
    assert ratio(row, "total_debt")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_msci_cash_composite_numerator():
    # each component alone is under the line (cash 0.20, interest
    # assets 0.1333) but the SUM is what MSCI tests:
    # (2000 + 1333)/10000 = 0.3333 -> pass at the boundary;
    # (2000 + 1334)/10000 = 0.3334 -> fail.
    row = se.screen(snap(financials=_msci_fin(
        interest_bearing_assets=1333)), MSCI)
    r = ratio(row, "cash_and_interest_bearing_securities")
    assert r["numerator"] == 3333 and r["value"] == 0.3333
    assert r["passed"] is True
    row = se.screen(snap(financials=_msci_fin(
        interest_bearing_assets=1334)), MSCI)
    r = ratio(row, "cash_and_interest_bearing_securities")
    assert r["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_msci_receivables_cash_boundary():
    # (5000 + 2000)/10000 = 0.70 at the boundary -> pass (le)
    row = se.screen(snap(financials=_msci_fin(
        accounts_receivable=5000)), MSCI)
    r = ratio(row, "receivables_and_cash")
    assert r["numerator"] == 7000 and r["value"] == 0.7
    assert r["passed"] is True
    # (5001 + 2000)/10000 = 0.7001 -> fail
    row = se.screen(snap(financials=_msci_fin(
        accounts_receivable=5001)), MSCI)
    assert ratio(row, "receivables_and_cash")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_msci_buffers_are_metadata_not_thresholds():
    # Section 2.2.1: entry 30% / threshold 33.33% / exit 35% for
    # debt and cash; entry 46% / threshold 70% / no exit for
    # receivables+cash. The encoded threshold is the middle figure.
    by_id = {r["id"]: r for r in MSCI["ratios"]}
    assert by_id["total_debt"]["buffers"] == \
        {"entry": 0.3, "exit": 0.35}
    assert by_id["cash_and_interest_bearing_securities"]["buffers"] \
        == {"entry": 0.3, "exit": 0.35}
    assert by_id["receivables_and_cash"]["buffers"] == \
        {"entry": 0.46, "exit": None}
    assert by_id["total_debt"]["threshold"] == 0.3333


def test_msci_missing_receivables_named():
    fin = _msci_fin()
    del fin["accounts_receivable"]
    row = se.screen(snap(financials=fin), MSCI)
    assert row["verdict"] == "insufficient-data"
    assert "accounts_receivable" in row["missing_inputs"]
    assert ratio(row, "receivables_and_cash")["value"] is None


# ------------------------------------------------------------ MSCI M
# Denominator: trailing 36-month average market value 10,000.

def _msci_m_snap(**over):
    fin = _msci_fin(**over)
    return snap(financials=fin,
                market={"avg_market_value_36m": 10000})


def test_msci_m_receivables_boundary_49():
    # (2900 + 2000)/10000 = 0.49 at the M-Series line -> pass (le)
    row = se.screen(_msci_m_snap(accounts_receivable=2900), MSCI_M)
    r = ratio(row, "receivables_and_cash")
    assert r["value"] == 0.49 and r["passed"] is True
    assert r["denominator"] == 10000
    assert r["denominator_base"] == "avg_market_value_36m"
    # (2901 + 2000)/10000 = 0.4901 -> fail
    row = se.screen(_msci_m_snap(accounts_receivable=2901), MSCI_M)
    assert ratio(row, "receivables_and_cash")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_msci_m_flip_vs_msci_same_financials():
    # receivables+cash = (4000 + 2000) = 6000 on a 10,000 base:
    # 0.60 passes the Index Series' 70% (total assets) line and
    # fails the M-Series' 49% (average market cap) line. Every
    # other ratio passes both. This is the canonical MSCI/MSCI_M
    # disagreement, on identical financials.
    s = _msci_m_snap()
    row_msci = se.screen(s, MSCI)
    row_m = se.screen(s, MSCI_M)
    assert row_msci["verdict"] == "compliant-with-purification"
    assert row_m["verdict"] == "non-compliant"
    assert ratio(row_m, "receivables_and_cash")["value"] == 0.6
    assert sd.flipping_ratios(row_m, row_msci) == \
        ["receivables_and_cash"]


def test_msci_m_missing_average_named():
    row = se.screen(snap(financials=_msci_fin()), MSCI_M)
    assert row["verdict"] == "insufficient-data"
    assert "avg_market_value_36m" in row["missing_inputs"]


# ------------------------------------------------------------ FTSE
# Denominator total assets 100,000, so the printed 33.333% line
# sits at 33,333 and the 50% line at 50,000. FTSE words the asset
# ratios "less than" (lt) and the income ratio "should not
# exceed" (le) -- the boundary tests pin exactly that asymmetry.

def _ftse_fin(**over):
    fin = {"total_revenue": 10000, "non_compliant_revenue": 400,
           "interest_bearing_debt": 30000,
           "interest_bearing_assets": 10000,
           "cash_and_liquid_assets": 20000,
           "accounts_receivable": 25000, "total_assets": 100000}
    fin.update(over)
    return fin


def test_ftse_compliant_with_purification():
    # income 0.04 (le 0.05); debt 0.30; cash composite
    # (20000 + 10000)/100000 = 0.30; receivables+cash
    # (25000 + 20000)/100000 = 0.45 -- all under their lines.
    # Yasaar publishes dividend purification -> with-purification.
    row = se.screen(snap(financials=_ftse_fin()), FTSE)
    assert row["verdict"] == "compliant-with-purification", row
    assert row["purification"]["ratio"] == 0.04
    assert row["purification"]["per_share"] is None


def test_ftse_debt_boundary_is_strict():
    # exactly at the line: 33333/100000 = 0.33333 -> FAIL (lt)
    row = se.screen(snap(financials=_ftse_fin(
        interest_bearing_debt=33333)), FTSE)
    r = ratio(row, "total_debt")
    assert r["value"] == 0.33333 and r["passed"] is False
    assert row["verdict"] == "non-compliant"
    # one unit under: 0.33332 -> pass
    row = se.screen(snap(financials=_ftse_fin(
        interest_bearing_debt=33332)), FTSE)
    assert ratio(row, "total_debt")["passed"] is True


def test_ftse_receivables_boundary_is_strict():
    # (30000 + 20000)/100000 = 0.50 exactly -> FAIL (lt)
    row = se.screen(snap(financials=_ftse_fin(
        accounts_receivable=30000)), FTSE)
    r = ratio(row, "receivables_and_cash")
    assert r["value"] == 0.5 and r["passed"] is False
    # (29999 + 20000)/100000 = 0.49999 -> pass
    row = se.screen(snap(financials=_ftse_fin(
        accounts_receivable=29999)), FTSE)
    assert ratio(row, "receivables_and_cash")["passed"] is True


def test_ftse_income_boundary_is_not_strict():
    # income is "should not exceed 5%": 500/10000 = 0.05 -> pass
    row = se.screen(snap(financials=_ftse_fin(
        non_compliant_revenue=500)), FTSE)
    assert ratio(row, "non_compliant_income")["passed"] is True


def test_ftse_missing_total_assets_named():
    fin = _ftse_fin()
    del fin["total_assets"]
    row = se.screen(snap(financials=fin), FTSE)
    assert row["verdict"] == "insufficient-data"
    assert "total_assets" in row["missing_inputs"]


# ------------------------------------------------------------ Islamicly
# Denominator: 36-month average market value of equity 10,000.
# All comparisons are strict ("<") on Islamicly's page.

def _islamicly_snap(**over):
    fin = {"total_revenue": 10000, "non_compliant_revenue": 400,
           "interest_bearing_debt": 2500,
           "interest_bearing_assets": 1000,
           "cash_and_liquid_assets": 1500,
           "accounts_receivable": 4000, "total_assets": 10000}
    fin.update(over)
    return snap(financials=fin,
                market={"avg_market_value_36m": 10000})


def test_islamicly_compliant_with_purification():
    # income 0.04 < 0.05; debt 0.25 < 0.30; cash composite
    # (1500 + 1000)/10000 = 0.25 < 0.30; receivables 0.40 < 0.49.
    # DP ratio = 0.04 -> compliant-with-purification.
    row = se.screen(_islamicly_snap(), ISLAMICLY)
    assert row["verdict"] == "compliant-with-purification", row
    assert row["purification"]["ratio"] == 0.04
    assert row["purification"]["per_share"] is None


def test_islamicly_boundaries_are_strict():
    # debt exactly 0.30 -> fail; 0.2999 -> pass
    row = se.screen(_islamicly_snap(interest_bearing_debt=3000),
                    ISLAMICLY)
    assert ratio(row, "interest_bearing_debt")["passed"] is False
    row = se.screen(_islamicly_snap(interest_bearing_debt=2999),
                    ISLAMICLY)
    assert ratio(row, "interest_bearing_debt")["passed"] is True
    # receivables exactly 0.49 -> fail
    row = se.screen(_islamicly_snap(accounts_receivable=4900),
                    ISLAMICLY)
    assert ratio(row, "accounts_receivable")["passed"] is False
    # income exactly 0.05 -> fail (the sector tolerance is "< 5%")
    row = se.screen(_islamicly_snap(non_compliant_revenue=500),
                    ISLAMICLY)
    assert ratio(row, "non_compliant_income")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_islamicly_cash_conflict_documented_and_operative():
    # The provider's own page contradicts itself: 33% in the Cash
    # Compliance section, < 30% in the Leverage Compliance
    # section. The conflict is documented, and the operative
    # figure is the stricter < 30% -- proven behaviourally: a
    # cash composite of exactly 0.30 FAILS (it would pass a
    # 33% line, and pass a "<= 30%" reading too).
    conflicts = ISLAMICLY["documented_conflicts"]
    assert len(conflicts) == 1
    assert conflicts[0]["operative_value"] == 0.3
    assert conflicts[0]["conflicting_value"] == 0.33
    row = se.screen(_islamicly_snap(cash_and_liquid_assets=2000,
                                    interest_bearing_assets=1000),
                    ISLAMICLY)
    r = ratio(row, "cash_and_interest_bearing_securities")
    assert r["value"] == 0.3 and r["threshold"] == 0.3
    assert r["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_islamicly_missing_average_named():
    fin = {"total_revenue": 10000, "non_compliant_revenue": 400,
           "interest_bearing_debt": 2500,
           "interest_bearing_assets": 1000,
           "cash_and_liquid_assets": 1500,
           "accounts_receivable": 4000, "total_assets": 10000}
    row = se.screen(snap(financials=fin), ISLAMICLY)
    assert row["verdict"] == "insufficient-data"
    assert "avg_market_value_36m" in row["missing_inputs"]


# ------------------------------------------------------------ S&P
# Denominator: 36-month average market value of equity 10,000, so
# the printed 30% lines sit at 3,000. Every comparison in the
# November 2026 methodology is strict ("<"): exactly at a line
# FAILS. There is NO receivables screen (abolished pre-2023).

def _sp_fin(**over):
    fin = {"total_revenue": 10000, "non_compliant_revenue": 400,
           "interest_bearing_debt": 2000,
           "interest_bearing_assets": 1000,
           "cash_and_liquid_assets": 1500,
           "accounts_receivable": 4000, "total_assets": 10000}
    fin.update(over)
    return fin


def _sp_snap(**over):
    return snap(financials=_sp_fin(**over),
                market={"avg_market_value_36m": 10000})


def test_sp_compliant_with_purification():
    # income 400/10000 = 0.04 < 0.05 pass
    # leverage 2000/10000 = 0.20 < 0.30 pass
    # cash composite (1500 + 1000)/10000 = 0.25 < 0.30 pass
    # S&P publishes dividend purification -> the verdict is
    # compliant-with-purification, ratio 0.04, per-share null
    # (the methodology's purification is a dividend share only).
    row = se.screen(_sp_snap(), SP)
    assert row["verdict"] == "compliant-with-purification", row
    assert row["missing_inputs"] == [], row["missing_inputs"]
    assert row["purification"]["defined"] is True
    assert row["purification"]["ratio"] == 0.04
    assert row["purification"]["per_share"] is None


def test_sp_boundaries_are_strict():
    # leverage exactly at the line: 3000/10000 = 0.30 -> FAIL (lt)
    row = se.screen(_sp_snap(interest_bearing_debt=3000), SP)
    r = ratio(row, "leverage")
    assert r["value"] == 0.3 and r["passed"] is False
    assert row["verdict"] == "non-compliant"
    # one unit under: 0.2999 -> pass
    row = se.screen(_sp_snap(interest_bearing_debt=2999), SP)
    assert ratio(row, "leverage")["passed"] is True
    # cash composite exactly 0.30: (1500 + 1500)/10000 -> FAIL
    row = se.screen(_sp_snap(interest_bearing_assets=1500), SP)
    r = ratio(row, "cash_and_interest_bearing_securities")
    assert r["value"] == 0.3 and r["passed"] is False
    # income exactly 0.05: 500/10000 -> FAIL (the tolerance is
    # "below 5%", strictly)
    row = se.screen(_sp_snap(non_compliant_revenue=500), SP)
    assert ratio(row, "non_compliant_income")["passed"] is False
    assert row["verdict"] == "non-compliant"


def test_sp_no_receivables_screen():
    # The pre-2023 receivables screen (< 49%) does NOT exist in
    # the November 2026 methodology: a snapshot with NO
    # accounts_receivable at all is fully determinate under
    # SP_SHARIAH, and even a huge receivables figure cannot fail
    # any ratio (there is no ratio that reads it).
    fin = _sp_fin()
    del fin["accounts_receivable"]
    row = se.screen(snap(financials=fin,
                         market={"avg_market_value_36m": 10000}), SP)
    assert row["verdict"] == "compliant-with-purification", row
    assert row["missing_inputs"] == []
    row = se.screen(_sp_snap(accounts_receivable=999999), SP)
    assert row["verdict"] == "compliant-with-purification", row
    assert {r["id"] for r in row["ratios"]} == {
        "non_compliant_income", "leverage",
        "cash_and_interest_bearing_securities"}


def test_sp_buffer_is_metadata_not_threshold():
    # The 2pp / 3-consecutive-period buffer is index-membership
    # hysteresis: recorded per ratio under 'buffers', while the
    # encoded threshold stays the raw 30% and a point-in-time
    # breach at 0.31 FAILS (index practice would hold a prior
    # constituent compliant inside the buffer).
    by_id = {r["id"]: r for r in SP["ratios"]}
    for rid in ("leverage", "cash_and_interest_bearing_securities"):
        assert by_id[rid]["buffers"] == {
            "consecutive_periods": 3, "hysteresis_pp": 0.02}
        assert by_id[rid]["threshold"] == 0.3
    row = se.screen(_sp_snap(interest_bearing_debt=3100), SP)
    assert ratio(row, "leverage")["value"] == 0.31
    assert ratio(row, "leverage")["passed"] is False


def test_sp_missing_average_named():
    row = se.screen(snap(financials=_sp_fin()), SP)
    assert row["verdict"] == "insufficient-data"
    assert "avg_market_value_36m" in row["missing_inputs"]


# ------------------------------------------------------------ DJIM
# Denominator: trailing 24-month average market capitalisation
# 10,000, so the printed 30% lines sit at 3,000. Every comparison
# is strict ("<"), as in the S&P pack -- but the WINDOW differs
# (24 months, not 36), which the flip test below pins.

def _djim_snap(fin_over=None, market=None):
    fin = _sp_fin()
    fin.update(fin_over or {})
    if market is None:
        market = {"avg_market_value_24m": 10000}
    return snap(financials=fin, market=market)


def test_djim_compliant_with_purification():
    # income 0.04 < 0.05; leverage 2000/10000 = 0.20 < 0.30;
    # cash composite (1500 + 1000)/10000 = 0.25 < 0.30.
    row = se.screen(_djim_snap(), DJIM)
    assert row["verdict"] == "compliant-with-purification", row
    assert row["missing_inputs"] == [], row["missing_inputs"]
    assert row["purification"]["ratio"] == 0.04
    assert row["purification"]["per_share"] is None
    r = ratio(row, "leverage")
    assert r["denominator"] == 10000
    assert r["denominator_base"] == "avg_market_value_24m"


def test_djim_boundaries_are_strict():
    # leverage exactly 0.30 -> FAIL (lt); 0.2999 -> pass
    row = se.screen(_djim_snap({"interest_bearing_debt": 3000}),
                    DJIM)
    assert ratio(row, "leverage")["passed"] is False
    assert row["verdict"] == "non-compliant"
    row = se.screen(_djim_snap({"interest_bearing_debt": 2999}),
                    DJIM)
    assert ratio(row, "leverage")["passed"] is True
    # income exactly 0.05 -> FAIL
    row = se.screen(_djim_snap({"non_compliant_revenue": 500}),
                    DJIM)
    assert ratio(row, "non_compliant_income")["passed"] is False


def test_djim_window_differs_from_sp():
    # Identical financials, two averages: avg24m 10,000 vs
    # avg36m 20,000. Debt 3,500: DJIM leverage 0.35 FAILS while
    # S&P leverage 0.175 passes; cash composite 2,500 passes both
    # (0.25 vs 0.125); income passes both. The 24-vs-36-month
    # window is the ONLY difference -- the canonical SP/DJIM
    # disagreement.
    s = _djim_snap({"interest_bearing_debt": 3500},
                   market={"avg_market_value_24m": 10000,
                           "avg_market_value_36m": 20000})
    row_djim = se.screen(s, DJIM)
    row_sp = se.screen(s, SP)
    assert row_djim["verdict"] == "non-compliant"
    assert row_sp["verdict"] == "compliant-with-purification"
    assert sd.flipping_ratios(row_djim, row_sp) == ["leverage"]


def test_djim_series_derived_24m_average():
    # No explicit aggregate: the engine derives avg24m from the
    # market-cap series. Points inside the 24-month window
    # (screening 2026-11-17, window from 2024-11-17): 10,000,
    # 12,000, 14,000 -> mean 12,000. The 2024-01-15 point (999,999)
    # is outside the window and must not count.
    series = [{"date": "2024-01-15", "market_cap": 999999},
              {"date": "2025-01-31", "market_cap": 10000},
              {"date": "2025-12-31", "market_cap": 12000},
              {"date": "2026-11-16", "market_cap": 14000}]
    s = _djim_snap(market={"market_cap_series": series})
    row = se.screen(s, DJIM)
    r = ratio(row, "leverage")
    assert r["denominator"] == 12000.0, r
    assert r["denominator_base"] == "avg_market_value_24m"
    assert row["verdict"] == "compliant-with-purification", row


def test_djim_missing_24m_average_named():
    # A snapshot carrying only the 36-month average cannot be
    # screened under DJIM: the 24-month aggregate is named.
    row = se.screen(_djim_snap(market={"avg_market_value_36m":
                                       10000}), DJIM)
    assert row["verdict"] == "insufficient-data"
    assert "avg_market_value_24m" in row["missing_inputs"]


# ------------------------------------------------------- pinned live

def test_sp_djim_pinned_and_live():
    assert se.available_standards() == [
        "AAOIFI", "DJIM", "EGX33", "FTSE", "ISLAMICLY", "MSCI",
        "MSCI_M", "SP_SHARIAH"]
    for ruleset in (SP, DJIM):
        assert len(ruleset["ratios"]) == 3
        assert ruleset["ruleset_version"] == "1.0.0"
        assert ruleset["sources"], ruleset["standard_id"]
        assert ruleset["activity_screen"]["required"] is True
        # the disabled drafts are gone: the pin replaced them
        draft = os.path.join(
            SCRIPTS, "sharia_rules_draft",
            ruleset["family"] + ".json")
        assert not os.path.exists(draft), draft


# ------------------------------------------------------------ POUL

def test_poul_insufficient_data_under_every_new_pack():
    path = os.path.join(SCRIPTS, "sharia_fixtures",
                        "covered_universe.json")
    with open(path, encoding="utf-8") as fh:
        poul = json.load(fh)[0]
    for ruleset in (MSCI, MSCI_M, FTSE, ISLAMICLY, SP, DJIM):
        row = se.screen(poul, ruleset)
        assert row["verdict"] == "insufficient-data", row
        assert "total_revenue" in row["missing_inputs"]


# ------------------------------------------------- report selection

def test_report_parameter_selects_msci():
    # The #170 contract: the Report Model's sharia_standards
    # parameter must select a new pack with NO compile_model
    # change. Fixture table produced by the real engine from the
    # hand-computed MSCI snapshot above (verdict
    # compliant-with-purification, purification ratio 0.04).
    import compile_model
    snapshot = snap(financials=_msci_fin(), ticker="POUL.CA")
    table = se.screen_table([snapshot], MSCI,
                            generated_at="2026-11-17T00:00:00Z")
    section, _flags = compile_model.build_sharia_section(
        "POUL.CA", ["MSCI"], ["MSCI"], {"MSCI": table}, se)
    entry = section["standards"][0]
    assert entry["standard"] == "MSCI"
    assert section["verdicts"] == {
        "MSCI": "compliant-with-purification"}
    assert entry["purification"]["ratio"] == 0.04
    assert section["average_purification"]["included"] == [
        {"standard": "MSCI", "ratio": 0.04}]
    # Case-insensitive resolution, and the default now spans all
    # eight implemented standards.
    resolved, _ = compile_model.resolve_sharia_standards(["msci"])
    assert resolved == ["MSCI"]
    resolved_all, _ = compile_model.resolve_sharia_standards(None)
    assert resolved_all == se.available_standards()


# ------------------------------------------------- purification use

def test_purification_calculator_uses_msci_ratio_only():
    # Issue #171 interplay: the calculator must compute the
    # dividend component for a ratio-only standard (MSCI) instead
    # of declaring insufficient-data for want of a per-share
    # figure it never uses. Fixture: the MSCI pass snapshot plus
    # a 2.00 dividend with ex-date 2026-11-16 inside a
    # 2026-11-02 -> 2026-11-17 holding of 1,000 shares:
    # dividend purification = 2.00 x 0.04 x 1000 = 80.00; the
    # capital component does not apply under MSCI (0.00, reason
    # shown); total 80.00, status ok. The window ends on the
    # snapshot's screening date (2026-11-17) so the event stream
    # covers it fully -- a longer window would honestly report
    # "partial" for the uncovered days (issue #171's gap rule).
    import sharia_purification as sp
    snapshot = snap(
        financials=_msci_fin(), ticker="POUL.CA",
        dividends=[{"per_share": 2.0, "ex_date": "2026-11-16",
                    "pay_date": "2026-11-18"}])
    result = sp.calculate(snapshot, 1000, "2026-11-02",
                          sell_date="2026-11-17",
                          standards=["MSCI"])
    entry = result["standards"][0]
    assert entry["status"] == "ok", entry
    assert entry["components"]["dividends"]["amount"] == 80.0
    assert entry["components"]["capital"]["applies"] is False
    assert entry["components"]["capital"]["amount"] == 0.0
    assert entry["total"] == 80.0


# ------------------------------------------------------------ diff

def _flip_snapshot():
    # One snapshot screened by four standards (see derivations):
    #   revenue 10,000, non-compliant 400 -> income 0.04 (all pass)
    #   debt 3,000; interest assets 1,000; cash 2,000;
    #   receivables 5,500; total assets 10,000;
    #   avg market value 36m 20,000; review-period average 10,000.
    # AAOIFI (avg36m): debt 0.15, assets 0.05 -> compliant-with-
    #   purification.
    # EGX33: base total assets 10,000 (the review-period market
    #   value is not used since issue #329); borrowing 0.30,
    #   investments 0.10, liquid 0.20 -> compliant.
    # MSCI: receivables+cash (5500 + 2000)/10000 = 0.75 > 0.70
    #   -> non-compliant; everything else passes.
    fin = {"total_revenue": 10000, "non_compliant_revenue": 400,
           "interest_bearing_debt": 3000,
           "interest_bearing_assets": 1000,
           "cash_and_liquid_assets": 2000,
           "accounts_receivable": 5500, "total_assets": 10000,
           "shares_outstanding": 1000}
    return snap(financials=fin,
                market={"avg_market_value_36m": 20000,
                        "avg_market_value_review_period": 10000})


def test_diff_names_the_flipping_ratio():
    s = _flip_snapshot()
    tables = {rs["standard_id"]: se.screen_table([s], rs)
              for rs in (AAOIFI, EGX33, MSCI)}
    report = sd.build_diff(tables,
                           generated_at="2026-11-17T00:00:00Z")
    assert len(report["disagreements"]) == 2, report
    for d in report["disagreements"]:
        assert d["standard"] == "MSCI"
        assert d["standard_verdict"] == "non-compliant"
        assert d["flipping_ratios"] == ["receivables_and_cash"], d
    bases = {d["baseline"] for d in report["disagreements"]}
    assert bases == {"AAOIFI", "EGX33"}
    assert report["indeterminate"] == []


def test_diff_purification_treatment_driver():
    # FTSE passes this fixture WITH a purification duty; EGX33
    # passes it plainly (no published purification rule). No
    # ratio flips -- the driver is the purification treatment.
    s = snap(financials=_ftse_fin(),
             market={"avg_market_value_review_period": 100000})
    tables = {rs["standard_id"]: se.screen_table([s], rs)
              for rs in (EGX33, FTSE)}
    report = sd.build_diff(tables,
                           generated_at="2026-11-17T00:00:00Z")
    assert len(report["disagreements"]) == 1, report
    d = report["disagreements"][0]
    assert d["standard"] == "FTSE" and d["baseline"] == "EGX33"
    assert d["flipping_ratios"] == []
    assert any("purification-treatment" in drv
               for drv in d["drivers"])


def test_diff_covered_universe_is_honestly_indeterminate():
    # Over today's covered universe (POUL.CA) every standard is
    # insufficient-data, so the diff must report ZERO
    # disagreements and list the pairs as indeterminate.
    path = os.path.join(SCRIPTS, "sharia_fixtures",
                        "covered_universe.json")
    with open(path, encoding="utf-8") as fh:
        snapshots = json.load(fh)
    tables = {}
    for std in se.available_standards():
        tables[std] = se.screen_table(snapshots,
                                      se.load_ruleset(std))
    report = sd.build_diff(tables,
                           generated_at="2026-11-17T00:00:00Z")
    assert report["disagreements"] == []
    # 6 non-baseline standards x 2 baselines = 12 indeterminate
    assert len(report["indeterminate"]) == 12
    assert set(report["verdicts"]["POUL.CA"].values()) == \
        {"insufficient-data"}
    md = sd.render_md(report)
    assert "fatwa" in md and "فتوى" in md


def main():
    tests = [
        ("MSCI compliant-with-purification, ratio-only "
         "purification needs no shares",
         test_msci_compliant_with_purification_no_shares_needed),
        ("MSCI debt boundary 33.33%", test_msci_debt_boundary),
        ("MSCI cash composite numerator sums",
         test_msci_cash_composite_numerator),
        ("MSCI receivables+cash boundary 70%",
         test_msci_receivables_cash_boundary),
        ("MSCI buffers are metadata, threshold is the middle "
         "figure", test_msci_buffers_are_metadata_not_thresholds),
        ("MSCI missing receivables named",
         test_msci_missing_receivables_named),
        ("MSCI_M receivables boundary 49%",
         test_msci_m_receivables_boundary_49),
        ("MSCI_M flips vs MSCI on identical financials",
         test_msci_m_flip_vs_msci_same_financials),
        ("MSCI_M missing 36m average named",
         test_msci_m_missing_average_named),
        ("FTSE compliant-with-purification",
         test_ftse_compliant_with_purification),
        ("FTSE debt boundary is strict (lt)",
         test_ftse_debt_boundary_is_strict),
        ("FTSE receivables boundary is strict (lt)",
         test_ftse_receivables_boundary_is_strict),
        ("FTSE income boundary is not strict (le)",
         test_ftse_income_boundary_is_not_strict),
        ("FTSE missing total assets named",
         test_ftse_missing_total_assets_named),
        ("Islamicly compliant-with-purification (DP ratio)",
         test_islamicly_compliant_with_purification),
        ("Islamicly boundaries are strict (lt)",
         test_islamicly_boundaries_are_strict),
        ("Islamicly cash conflict documented; operative < 30%",
         test_islamicly_cash_conflict_documented_and_operative),
        ("Islamicly missing 36m average named",
         test_islamicly_missing_average_named),
        ("S&P compliant-with-purification, ratio-only "
         "purification", test_sp_compliant_with_purification),
        ("S&P boundaries are strict (lt)",
         test_sp_boundaries_are_strict),
        ("S&P has NO receivables screen (abolished)",
         test_sp_no_receivables_screen),
        ("S&P buffer is metadata, threshold stays 30%",
         test_sp_buffer_is_metadata_not_threshold),
        ("S&P missing 36m average named",
         test_sp_missing_average_named),
        ("DJIM compliant-with-purification on the 24m window",
         test_djim_compliant_with_purification),
        ("DJIM boundaries are strict (lt)",
         test_djim_boundaries_are_strict),
        ("DJIM 24m window flips vs S&P 36m on identical "
         "financials", test_djim_window_differs_from_sp),
        ("DJIM 24m average derived from the series",
         test_djim_series_derived_24m_average),
        ("DJIM missing 24m average named",
         test_djim_missing_24m_average_named),
        ("S&P / DJIM pinned and live, drafts gone",
         test_sp_djim_pinned_and_live),
        ("POUL insufficient-data under every new pack",
         test_poul_insufficient_data_under_every_new_pack),
        ("Report Model parameter selects MSCI unchanged",
         test_report_parameter_selects_msci),
        ("Purification calculator computes for ratio-only MSCI",
         test_purification_calculator_uses_msci_ratio_only),
        ("Diff names the flipping ratio vs both baselines",
         test_diff_names_the_flipping_ratio),
        ("Diff labels purification-treatment differences",
         test_diff_purification_treatment_driver),
        ("Diff over the covered universe is honestly "
         "indeterminate", test_diff_covered_universe_is_honestly_indeterminate),
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
