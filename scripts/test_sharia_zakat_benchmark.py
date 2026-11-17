#!/usr/bin/env python3
"""Unit tests for issue #173's benchmark
(scripts/sharia_zakat_benchmark.py).

Stdlib only, no network: the parsers are exercised against
the committed raw cache in sharia/zakat-benchmark/raw/, and
the scoring runs against the committed frozen snapshots --
exactly what a re-run offline consumes.

Hand-computed expectations:
  Tedawal worked example: 200,000 x 2.5% = 5,000; nisab
    85 g x 290 = 24,650.
  AskZakariya: components 9,200 + 2,375 + 180 = 11,755;
    our aggregation 11,755 x 2.5% = 293.875; published
    293.88 (their 2dp rounding) -> delta -0.005 -> matched.
  Proxies on the ACME case at a declared 20.00/share
    (market value 50,000 x 20 = 1,000,000):
    NZF 25%  -> base 250,000 -> 6,250;  ours 10,000;
                delta +3,750.
    ZakatCalc 30% -> base 300,000 -> 7,500; ours 10,000;
                delta +2,500.
  Internal gate: all 15 stored worked cases reproduce.

Run: python3 scripts/test_sharia_zakat_benchmark.py
Exit 0 only when every test passes.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import sharia_zakat_benchmark as zb  # noqa: E402

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


def raw_text(name):
    with open(os.path.join(zb.RAW_DIR, name),
              encoding="utf-8") as fh:
        return zb.strip_text(fh.read())


def t_parse_tedawal():
    row = zb.parse_tedawal(raw_text("tedawal.html"))
    assert row is not None
    assert row["market_value"] == 200000
    assert row["published_zakat"] == 5000
    assert row["nisab_value"] == 24650
    assert row["nisab_gold_price_per_gram"] == 290
check("parser: Tedawal worked example + nisab figures",
      t_parse_tedawal)


def t_parse_askzakariya():
    row = zb.parse_askzakariya(raw_text("askzakariya.html"))
    assert row is not None
    assert row["components"] == {
        "aapl_market_value": 9200, "spus_market_value": 2375,
        "dividends_received_unspent": 180}
    assert row["published_total_base"] == 11755
    assert row["published_zakat"] == 293.88
check("parser: AskZakariya worked example components",
      t_parse_askzakariya)


def t_parse_almurakib():
    row = zb.parse_almurakib(raw_text("almurakib.html"))
    assert row is not None
    assert "القيمة السوقية" in row["trading_formula_ar"]
    assert "الأرباح" in row["trading_formula_ar"]
    assert row["nisab_grams_gold"] == 85
    assert row["hawl_required"] is True
check("parser: Almurakib formulas + nisab/hawl statements",
      t_parse_almurakib)


def t_parse_proxies():
    zc = zb.parse_zakatcalc(raw_text("zakatcalc.html"))
    assert zc is not None and zc["proxy_pct"] == 0.30
    am = zb.parse_amal_nzf(raw_text("amal-nzf.html"))
    assert am is not None and am["proxy_pct"] == 0.25
    assert am["components_phrase_present"] is True
    assert am["gregorian_rate_present"] is True
check("parsers: ZakatCalc 30% and NZF 25% proxies, SS35 "
      "components phrase", t_parse_proxies)


def t_unavailable_snapshots_carry_attempts():
    for sid in ("kashif", "borsa_halal"):
        snap = zb._load_snapshot(sid)
        assert snap is not None, sid
        assert snap["status"] == "unavailable", sid
        assert snap["rows"] == [], sid
        assert len(snap["attempts"]) >= 1, sid
        assert all(a.strip() for a in snap["attempts"]), sid
check("unavailable sources are first-class snapshots with "
      "attempts on record", t_unavailable_snapshots_carry_attempts)


def t_score_end_to_end():
    report = zb.score()
    gate = report["internal_gate"]
    assert gate == {"worked_cases_reproduced": 15,
                    "worked_cases_total": 15}, gate
    by = {}
    for c in report["comparisons"]:
        by.setdefault(c["source"], []).append(c)
    assert by["tedawal"][0]["verdict"] == "matched"
    assert by["tedawal"][0]["delta"] == 0
    assert by["askzakariya"][0]["verdict"] == "matched"
    assert by["askzakariya"][0]["ours"] == 293.875
    assert by["askzakariya"][0]["delta"] == -0.005
    assert [c["verdict"] for c in by["almurakib"]] == \
        ["explained-divergence", "explained-divergence"]
    assert by["amal_nzf"][0]["published"] == 6250
    assert by["amal_nzf"][0]["delta"] == 3750
    assert by["zakatcalc"][0]["published"] == 7500
    assert by["zakatcalc"][0]["delta"] == 2500
    assert by["kashif"][0]["verdict"] == "unavailable"
    assert by["borsa_halal"][0]["verdict"] == "unavailable"
    # no comparison is left unexplained, none is a defect
    for c in report["comparisons"]:
        assert c["verdict"] != "defect", c
        assert c["explanation_en"].strip(), c
check("score: matched worked examples, explained proxy "
      "divergences, unavailable named calculators, gate "
      "15/15", t_score_end_to_end)


def main():
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\ntest_sharia_zakat_benchmark: {passed}/"
          f"{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
