#!/usr/bin/env python3
"""Tests for issue #172 (Sharia accuracy benchmark).

Stdlib only, no network. The comparison/agreement math runs on
hand-computed fixtures; the parsers run on excerpts that mirror the
real frozen artifacts token-for-token (the Ostool lines reproduce the
token order and values of the 2026-08-04 PDF rows for JUFO / EFIH /
POUL / ADIB as extracted by pdftotext -layout into
sharia/benchmark/raw/ostool-compliance-list.layout.txt); one
integration test scores the committed frozen snapshots end to end.

Usage: python3 scripts/test_sharia_benchmark.py
Exit 0 only when every test passes.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import sharia_benchmark as sb  # noqa: E402

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


def approx(a, b, tol=1e-9):
    assert a is not None and abs(a - b) <= tol, f"{a} != {b} (±{tol})"


def our_row(verdict, missing=None, ratios=None, purif_ratio=None):
    return {"verdict": verdict, "missing_inputs": missing or [],
            "ratios": ratios or [],
            "purification": {"ratio": purif_ratio}}


def source(rows, **kw):
    doc = {"source_id": "test", "status": "ok", "rows": rows}
    doc.update(kw)
    return doc


def their(ticker, verdict, ratios=None):
    return {"ticker": ticker, "verdict": verdict,
            "verdict_raw": verdict, "published_ratios": ratios}


# ------------------------------------------------------------- math

def t_agreement_mix():
    ours = {
        "AAA.CA": our_row("compliant"),
        "BBB.CA": our_row("compliant-with-purification"),
        "CCC.CA": our_row("non-compliant"),
        "DDD.CA": our_row("insufficient-data", missing=["total_revenue"]),
        "EEE.CA": our_row("compliant"),
        "FFF.CA": our_row("compliant"),
    }
    snap = source([
        their("AAA.CA", "compliant"),
        their("BBB.CA", "non-compliant"),
        their("CCC.CA", "compliant"),
        their("DDD.CA", "non-compliant"),
        their("EEE.CA", "doubtful"),
    ])
    out = sb.compare(ours, snap)
    c = out["counts"]
    assert c["agree"] == 1, c
    assert c["we_compliant_they_non_compliant"] == 1, c
    assert c["we_noncompliant_they_compliant"] == 1, c
    assert c["our_insufficient_data"] == 1, c
    assert c["their_indeterminate"] == 1, c
    assert c["not_covered_by_source"] == 1, c
    assert out["determinate_pairs"] == 3, out
    approx(out["agreement_pct"], 33.33, tol=0.01)
    outcomes = {r["ticker"]: r["outcome"] for r in out["rows"]}
    assert outcomes["BBB.CA"] == "disagree-we-compliant-they-non-compliant"
    assert outcomes["CCC.CA"] == "disagree-we-noncompliant-they-compliant"
    assert outcomes["DDD.CA"] == "our-insufficient-data"


def t_agreement_none_determinate():
    ours = {"AAA.CA": our_row("insufficient-data", missing=["x"])}
    snap = source([their("AAA.CA", "non-compliant")])
    out = sb.compare(ours, snap)
    assert out["determinate_pairs"] == 0
    assert out["agreement_pct"] is None  # never 0, never 100


def t_complete_list_derivation():
    # EGX33-style: a complete constituent list makes absence a
    # published non-membership.
    ours = {"ZZZ.CA": our_row("compliant")}
    snap = source([their("AAA.CA", "compliant")], list_complete=True)
    out = sb.compare(ours, snap)
    assert out["counts"]["we_compliant_they_non_compliant"] == 1, out
    row = out["rows"][0]
    assert "derived" in row["theirs_raw"]


def t_explanations():
    # Insufficient-data names the missing inputs.
    ours = {"A.CA": our_row("insufficient-data",
                            missing=["total_revenue", "interest_bearing_debt"])}
    out = sb.compare(ours, source([their("A.CA", "non-compliant")]))
    ex = out["rows"][0]["explanation"]
    assert "total_revenue" in ex and "never as agreement" in ex, ex
    # Disagreement with no ratio data on either side -> unexplained.
    ours = {"A.CA": our_row("non-compliant")}
    out = sb.compare(ours, source([their("A.CA", "compliant")]))
    assert out["rows"][0]["explanation"] == "unexplained"
    # Disagreement with published ratios -> labelled hypothesis.
    ours = {"A.CA": our_row("compliant")}
    out = sb.compare(ours, source([their(
        "A.CA", "non-compliant",
        ratios={"prohibited_income_pct": 5.5})]))
    assert out["rows"][0]["explanation"].startswith("Hypothesis"), \
        out["rows"][0]["explanation"]


def t_purification_stats():
    pairs = [{"ticker": "A", "ours": 0.02, "theirs": 0.025},
             {"ticker": "B", "ours": 0.05, "theirs": 0.04}]
    st = sb.purification_stats(pairs)
    assert st["n_pairs"] == 2
    approx(st["mean_abs_diff"], 0.0075)
    approx(st["max_abs_diff"], 0.01)
    approx(st["mean_rel_diff"], 0.225)
    st = sb.purification_stats([])
    assert st["n_pairs"] == 0 and st["mean_abs_diff"] is None
    assert st["max_abs_diff"] is None and st["mean_rel_diff"] is None


def t_normalization():
    assert sb.normalize_ours("compliant") == "compliant"
    assert sb.normalize_ours("compliant-with-purification") == "compliant"
    assert sb.normalize_ours("non-compliant") == "non-compliant"
    assert sb.normalize_ours("insufficient-data") == "insufficient-data"
    assert sb.normalize_theirs(None) == "not-covered"
    assert sb.normalize_theirs({"verdict": "doubtful"}) == "doubtful"


# ------------------------------------------------------------- parsers

# Token order mirrors the real frozen layout lines: verdict,
# %income, %liquid, %loans, %deposits, total assets, avg market
# value, sector, name, code.
OSTOOL_EXCERPT = "\n".join([
    "متوافق     %0.5               %6.5                %24.0          %6.0"
    "          21,097.9         32,625.6                     أغذية و مشروبات"
    " و تبغ                               جهينة                         JUFO.CA",
    "غير متوافق    %6.8               %2.6                %0.0           %3.0"
    "          13,079.6         62,174.7              اتصاالت و اعالم و"
    " تكنولوجيا المعلومات             اي فاينانس                       EFIH.CA",
    "غير متوافق    %5.5               %40.5               %1.0          %40.0"
    "          11,485.1         14,030.0                     أغذية و مشروبات"
    " و تبغ                              القاهرة للدواجن                      POUL.CA",
    "متوافق                                                                 "
    " بنوك                                      أبو ظبي األسالمي             ADIB.CA",
])


def t_ostool_parser():
    rows = {r["ticker"]: r for r in sb.parse_ostool_layout(OSTOOL_EXCERPT)}
    assert set(rows) == {"JUFO.CA", "EFIH.CA", "POUL.CA", "ADIB.CA"}, rows
    poul = rows["POUL.CA"]
    assert poul["verdict"] == "non-compliant"
    # Column mapping pinned by the PDF header's word x-positions.
    assert poul["published_ratios"] == {
        "prohibited_income_pct": 5.5, "liquid_assets_pct": 40.5,
        "interest_loans_pct": 1.0, "interest_deposits_pct": 40.0}, poul
    approx(poul["total_assets_m_egp"], 11485.1)
    approx(poul["avg_market_value_m_egp"], 14030.0)
    assert rows["JUFO.CA"]["verdict"] == "compliant"
    assert rows["JUFO.CA"]["published_ratios"]["interest_loans_pct"] == 24.0
    assert rows["EFIH.CA"]["published_ratios"]["prohibited_income_pct"] == 6.8
    adib = rows["ADIB.CA"]
    assert adib["verdict"] == "compliant"
    assert adib["published_ratios"] is None  # Sharia-board row, no ratios


def t_musaffa_parser():
    p = sb.parse_musaffa_page(
        "As of November 2026, Cairo Poultry is classified as NOT HALAL "
        "by Musaffa under AAOIFI-based Shariah screening standards.")
    assert p["verdict"] == "non-compliant" and p["as_of"] == "November 2026"
    p = sb.parse_musaffa_page("the stock is classified as HALAL today")
    assert p["verdict"] == "compliant"
    p = sb.parse_musaffa_page("the stock is classified as Doubtful today")
    assert p["verdict"] == "doubtful"
    assert sb.parse_musaffa_page("no verdict here") is None


def t_egx33_parser():
    html = ("<td>Ibnsina Pharma<br>ISPH.CA</td><td>AMOC.CA</td>"
            "<td>ISPH.CA</td>")
    assert sb.parse_egx33_constituents(html) == ["ISPH.CA", "AMOC.CA"]


def t_faisal_parser_synthetic():
    # Synthetic excerpt only — the real PDF was not retrievable in
    # the 2026-11-18 freeze (see the faisal snapshot).
    text = "الأسهم المتوافقة: JUFO.CA و POUL.CA و JUFO.CA مرة أخرى"
    rows = sb.parse_faisal_text(text)
    assert [r["ticker"] for r in rows] == ["JUFO.CA", "POUL.CA"]
    assert all(r["verdict"] == "compliant" for r in rows)


def t_driver_hypothesis():
    hyp = sb.driver_hypothesis_ostool(
        {"published_ratios": {"prohibited_income_pct": 5.5,
                              "liquid_assets_pct": 40.5,
                              "interest_loans_pct": 1.0,
                              "interest_deposits_pct": 40.0}})
    assert hyp.startswith("Hypothesis"), hyp
    assert "prohibited income 5.5%" in hyp
    assert "interest-bearing deposits 40.0%" in hyp
    assert "liquid assets" not in hyp  # 40.5 <= 70 passes
    assert sb.driver_hypothesis_ostool(
        {"published_ratios": {"prohibited_income_pct": 1.0}}) is None


# ------------------------------------------------------------- integration

def t_frozen_snapshots_end_to_end():
    snaps = sb.load_snapshots()
    for sid in ("musaffa", "ostool", "egx33", "faisal", "nour_borsa"):
        assert sid in snaps, f"missing frozen snapshot {sid}"
        for row in snaps[sid]["rows"]:
            assert row.get("source_url") and row.get("retrieved_at"), row
    assert snaps["faisal"]["status"] == "unavailable"
    assert snaps["nour_borsa"]["status"] == "unavailable"
    report = sb.score()
    by_id = {c["source_id"]: c for c in report["comparisons"]}
    # The measured result of the first run: our only covered ticker
    # has no balance-sheet inputs yet, so every live comparison
    # lands in the insufficient-data bucket and agreement stays null.
    for sid in ("musaffa", "ostool", "egx33"):
        c = by_id[sid]
        assert c["counts"]["our_insufficient_data"] == 1, c
        assert c["agreement_pct"] is None, c
    assert by_id["faisal"]["source_status"] == "unavailable"
    purif = report["purification"]
    assert purif["stats"]["n_pairs"] == 0
    awaiting = {a["ticker"]: a for a in purif["awaiting_our_inputs"]}
    assert awaiting["POUL.CA"]["published_pct"] == 5.5
    ost_row = by_id["ostool"]["rows"][0]
    assert ost_row["driver_hypothesis"].startswith("Hypothesis")
    md = sb.render_md(report)
    assert "not a fatwa" in md and "ليست فتوى" in md


def main():
    check("agreement math: hand-computed mix", t_agreement_mix)
    check("agreement: zero determinate pairs -> null", t_agreement_none_determinate)
    check("complete-list absence derives non-membership", t_complete_list_derivation)
    check("explanations: missing inputs / unexplained / hypothesis", t_explanations)
    check("purification stats: known pairs + empty", t_purification_stats)
    check("verdict normalization", t_normalization)
    check("ostool parser: column mapping on real rows", t_ostool_parser)
    check("musaffa parser: halal / not halal / doubtful", t_musaffa_parser)
    check("egx33 constituent parser", t_egx33_parser)
    check("faisal parser (synthetic excerpt)", t_faisal_parser_synthetic)
    check("driver hypothesis from published ratios", t_driver_hypothesis)
    check("frozen snapshots end-to-end score", t_frozen_snapshots_end_to_end)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\ntest_sharia_benchmark: {len(RESULTS) - len(failed)}/"
          f"{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
