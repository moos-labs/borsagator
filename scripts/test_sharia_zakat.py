#!/usr/bin/env python3
"""Unit tests for issue #173: the zakat calculator
(scripts/sharia_zakat.py) over the stored worked cases
(scripts/sharia_zakat_fixtures/worked_cases.json).

Stdlib only, no network. Every expected number is derived in
the fixture file's ``derivation`` field from the stored inputs
and the published method -- not copied from the calculator's
output. The derivations, in brief:

TRADING (trade goods; market value at the valuation date):
  tedawal        10,000 x 20.00 = 200,000; nisab 85 x 290
                 = 24,650; 200,000 x 2.5% = 5,000 (Tedawal's
                 published answer)
  askzakariya    40 x 230 = 9,200 + 180 declared unspent
                 dividends = 9,380; x 2.5% = 234.50
  spus alone     25 x 95 = 2,375 < nisab 6,800 -> 0
  poul           100 x 8.02 = 802 < 340,000 -> 0
  exact nisab    1,000 x 85 = 85,000 = 85 x 1,000 -> due,
                 85,000 x 2.5% = 2,125
  hawl           170 of 354 days -> 0; declared hawl -> 5,000
  silver/gold    base 100,000: silver nisab 595 x 50 = 29,750
                 -> 2,500; gold nisab 340,000 -> 0
  gregorian      rate 2.577%: 200,000 x 0.02577 = 5,154
  no nisab       amount computed, status nisab-not-provided

INVESTMENT (AAOIFI Std 35; zakatable assets per share):
  ACME per share = (500,000,000 + 300,000,000)
                   / 100,000,000 = 8.00
  50,000 shares  -> base 400,000 -> 10,000
  10,000 shares  -> base 80,000 < 340,000 -> 0
  +25,000 declared dividends -> base STAYS 400,000 (the
                 method's rule excludes them, with the note)
  POUL (real snapshot) -> insufficient-data, both missing
                 financial fields named, zakat null

Run: python3 scripts/test_sharia_zakat.py
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

import sharia_zakat as zk  # noqa: E402

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


FIXTURES_PATH = os.path.join(
    SCRIPTS, "sharia_zakat_fixtures", "worked_cases.json")
with open(FIXTURES_PATH, encoding="utf-8") as fh:
    FIXTURES = json.load(fh)


def resolve(case):
    case = copy.deepcopy(case)
    ref = case.pop("snapshot_ref", None)
    if ref is not None:
        case["snapshot"] = FIXTURES["snapshots"][ref]
    return case


def run_case(case_id):
    entry = next(c for c in FIXTURES["cases"]
                 if c["id"] == case_id)
    return zk.calculate(resolve(entry["case"])), entry["expected"]


# ------------------------------------------------------- worked cases

def worked_case(case_id):
    def fn():
        result, expected = run_case(case_id)
        assert result["status"] == expected["status"], result
        if expected["base_total"] is None:
            assert result["base"] is None, result
        else:
            assert result["base"]["total"] == \
                expected["base_total"], result["base"]
        assert result["zakat"] == expected["zakat"], result
        if expected.get("nisab_value") is not None:
            assert result["nisab_check"]["performed"] is True
            assert result["nisab_check"]["nisab_value"] == \
                expected["nisab_value"], result["nisab_check"]
        if expected.get("missing_inputs"):
            assert result["missing_inputs"] == \
                expected["missing_inputs"], result
    return fn


for _entry in FIXTURES["cases"]:
    check("worked case: %s" % _entry["id"],
          worked_case(_entry["id"]))


# ------------------------------------------------------- targeted checks

def t_framing_and_method_statement():
    for entry in FIXTURES["cases"]:
        r = zk.calculate(resolve(entry["case"]))
        assert r["framing_en"] == zk.FRAMING_EN
        assert r["framing_ar"] == zk.FRAMING_AR
        assert "not a fatwa" in r["framing_en"]
        assert r["method"]["statement_en"]
        assert r["method"]["statement_ar"]
        assert r["method"]["sources"], r["method"]
check("framing + method statement on every result",
      t_framing_and_method_statement)


def t_exact_nisab_relation():
    r, _ = run_case("exact-nisab")
    assert r["nisab_check"]["relation"] == "at"
    assert r["status"] == zk.STATUS_DUE
check("base exactly at the nisab is due (relation 'at')",
      t_exact_nisab_relation)


def t_investment_dividends_excluded_with_note():
    r, _ = run_case("acme-investment-dividends-excluded")
    assert r["base"]["total"] == 400000
    assert any("NOT added" in n["en"] for n in r["notes"]), \
        r["notes"]
check("INVESTMENT excludes declared dividends, with the "
      "rule stated", t_investment_dividends_excluded_with_note)


def t_trading_dividends_not_provided_note():
    r, _ = run_case("tedawal-trading-200k")
    assert any("never estimated" in n["en"] for n in r["notes"])
    comps = [c["id"] for c in r["base"]["components"]]
    assert comps == ["market_value"], comps
check("TRADING without declared dividends: base is market "
      "value alone, note says dividends are never estimated",
      t_trading_dividends_not_provided_note)


def t_missing_price_is_insufficient_data():
    case = {"ticker": "X", "method": "TRADING", "shares": 10,
            "buy_date": "2025-01-01",
            "valuation_date": "2026-01-10", "currency": "EGP"}
    r = zk.calculate(case)
    assert r["status"] == zk.STATUS_INSUFFICIENT
    assert r["missing_inputs"] == ["price_per_share"]
    assert r["zakat"] is None
check("TRADING with no price -> insufficient-data naming "
      "price_per_share", t_missing_price_is_insufficient_data)


def t_nisab_grams_override_is_explicit():
    # NZF's published variant (87.48 g gold) as an explicit
    # override: 87.48 x 1,000 = 87,480 > base 85,000 -> below.
    case, _ = None, None
    entry = next(c for c in FIXTURES["cases"]
                 if c["id"] == "exact-nisab")
    case = resolve(entry["case"])
    case["nisab"]["grams"] = 87.48
    r = zk.calculate(case)
    assert r["nisab_check"]["grams"] == 87.48
    assert r["nisab_check"]["nisab_value"] == 87480
    assert r["status"] == zk.STATUS_BELOW_NISAB
    assert r["zakat"] == 0
check("nisab grams are an explicit input (87.48 g override "
      "flips the exact-nisab case to below-nisab)",
      t_nisab_grams_override_is_explicit)


def t_methods_registry():
    assert set(zk.available_methods()) == {"TRADING",
                                           "INVESTMENT"}
    for mid in ("TRADING", "INVESTMENT"):
        m = zk.load_method(mid)
        assert m["rates"]["lunar"] == 0.025
        assert m["nisab_grams"] == {"gold": 85, "silver": 595}
check("method registry: TRADING + INVESTMENT, declared "
      "rates and nisab grams", t_methods_registry)


def t_validation_fails_loudly():
    base = {"ticker": "X", "method": "TRADING", "shares": 10,
            "buy_date": "2025-01-01",
            "valuation_date": "2026-01-10",
            "price_per_share": 5.0}
    for mutate in (
            lambda c: c.update(method="NOPE"),
            lambda c: c.update(calendar="sidereal"),
            lambda c: c.update(valuation_date="2024-01-01"),
            lambda c: c.update(shares=0),
            lambda c: c.update(dividends_received_held=-1),
            lambda c: c.update(nisab={"basis": "copper",
                                      "price_per_gram": 1}),
            lambda c: c.update(buy_date="not-a-date")):
        case = copy.deepcopy(base)
        mutate(case)
        try:
            zk.calculate(case)
        except ValueError:
            continue
        raise AssertionError("no ValueError for %r" % (case,))
check("invalid inputs raise ValueError (unknown method, "
      "calendar, dates, shares, dividends, nisab basis)",
      t_validation_fails_loudly)


def t_deterministic():
    a, _ = run_case("acme-investment-50k")
    b, _ = run_case("acme-investment-50k")
    assert json.dumps(a, sort_keys=True) == \
        json.dumps(b, sort_keys=True)
check("same stored case -> byte-identical result",
      t_deterministic)


def t_cli_case_file_and_flags():
    entry = next(c for c in FIXTURES["cases"]
                 if c["id"] == "tedawal-trading-200k")
    with tempfile.TemporaryDirectory() as td:
        case_path = os.path.join(td, "case.json")
        with open(case_path, "w", encoding="utf-8") as fh:
            json.dump(resolve(entry["case"]), fh)
        out = subprocess.run(
            [sys.executable,
             os.path.join(SCRIPTS, "sharia_zakat.py"),
             "calculate", "--case", case_path],
            capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        r = json.loads(out.stdout)
        assert r["zakat"] == 5000 and r["status"] == "due"
        # flags path: POUL trading below nisab
        out = subprocess.run(
            [sys.executable,
             os.path.join(SCRIPTS, "sharia_zakat.py"),
             "calculate", "--ticker", "POUL.CA",
             "--method", "TRADING", "--shares", "100",
             "--buy", "2025-11-20", "--valuation", "2026-11-18",
             "--price", "8.02", "--nisab-basis", "gold",
             "--nisab-price-per-gram", "4000",
             "--currency", "EGP"],
            capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        r = json.loads(out.stdout)
        assert r["status"] == "below-nisab" and r["zakat"] == 0
        # bad method -> exit 2, nothing on stdout
        out = subprocess.run(
            [sys.executable,
             os.path.join(SCRIPTS, "sharia_zakat.py"),
             "calculate", "--ticker", "X", "--method", "NOPE",
             "--shares", "1", "--buy", "2025-01-01",
             "--valuation", "2026-01-10", "--price", "1"],
            capture_output=True, text=True)
        assert out.returncode == 2 and "REFUSED" in out.stderr
check("CLI: --case file, flag-built case, and REFUSED/exit 2 "
      "on a bad method", t_cli_case_file_and_flags)


def main():
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\ntest_sharia_zakat: {passed}/{len(RESULTS)} passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
