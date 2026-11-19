#!/usr/bin/env python3
"""Regression tests: every ISIN in EGX_COMPANIES must pass the
ISO 6166 check digit (issue #304).

Bug: worker/egx_harvest.py carried AMOC as EGS3E2B1C018, which fails
check-digit validation — it cannot be a valid ISIN (and it appears
nowhere in the Investor Protection Fund official fund-members list).
The correct value is EGS380P1C010 (IPF list, row 103, "Alexandria
Mineral Oils Company – AMOC", checked live 2026-11-19); the stage-2
manifest already carries it. The old value flowed straight into
harvest queries because nothing ever validated the table.

The table-wide test FAILS on pristine main (AMOC) and PASSES on the
fix; the old-value test proves the new validator would have caught
the typo. The validator also runs in main() before any query, so a
future typo fails loudly instead of harvesting against a bad ISIN.

Run:  python3 worker/test_egx_harvest_isin.py
  or:  python3 -m pytest worker/test_egx_harvest_isin.py -q
  or:  python3 -m unittest worker.test_egx_harvest_isin -v
No network, no fixture files.
"""
import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "egx_harvest_under_test",
    os.path.join(_HERE, "egx_harvest.py"))
egx_harvest = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(egx_harvest)

is_valid_isin = egx_harvest.is_valid_isin
validate_egx_companies_isins = egx_harvest.validate_egx_companies_isins
EGX_COMPANIES = egx_harvest.EGX_COMPANIES


class TestIsinCheckDigit(unittest.TestCase):
    def test_every_isin_in_table_passes_check_digit(self):
        """The whole EGX_COMPANIES table must be valid ISINs — a
        single mistyped entry fails this test by name."""
        bad = [(code, isin) for code, (_ar, isin)
               in EGX_COMPANIES.items() if not is_valid_isin(isin)]
        self.assertEqual(bad, [], f"invalid ISIN(s): {bad}")

    def test_validate_table_returns_empty_on_clean_table(self):
        self.assertEqual(validate_egx_companies_isins(), [])

    def test_amoc_isin_is_the_ipf_value(self):
        """AMOC must be EGS380P1C010 — IPF official fund-members
        list, row 103 (checked live 2026-11-19)."""
        _ar, isin = EGX_COMPANIES["AMOC"]
        self.assertEqual(isin, "EGS380P1C010")

    def test_old_amoc_value_fails_check_digit(self):
        """The pre-fix value EGS3E2B1C018 is not a valid ISIN: the
        validator must reject it, so this test would have caught
        the #304 typo before it ever reached a harvest query."""
        self.assertFalse(is_valid_isin("EGS3E2B1C018"))

    def test_validator_names_the_bad_entry(self):
        """validate_egx_companies_isins raises ValueError naming
        every bad entry, so the typo is found at the source."""
        table = dict(EGX_COMPANIES)
        table["AMOC"] = ("الإسكندرية للزيوت المعدنية", "EGS3E2B1C018")
        with self.assertRaises(ValueError) as ctx:
            validate_egx_companies_isins(table)
        self.assertIn("AMOC=EGS3E2B1C018", str(ctx.exception))

    def test_known_good_isins(self):
        """Spot-check the validator against the other table entries
        (all independently valid)."""
        for isin in ("EGS02051C018",  # POUL
                     "EGS60121C018",  # COMI
                     "EGS48031C016",  # ETEL
                     "EGS69101C011",  # HRHO
                     "EGS691S1C011",  # TMGH
                     "EGS3G0Z1C014",  # SWDY
                     "EGS3C251C013",  # ESRS
                     "EGS38161C013",  # ABUK
                     "EGS69082C013"):  # EKHO
            self.assertTrue(is_valid_isin(isin), isin)

    def test_one_digit_off_fails(self):
        """Changing a single digit breaks the check digit."""
        self.assertFalse(is_valid_isin("EGS380P1C011"))  # AMOC +1
        self.assertFalse(is_valid_isin("EGS60121C019"))  # COMI +1

    def test_malformed_isins_fail(self):
        """Wrong shape is invalid even before the check digit."""
        self.assertFalse(is_valid_isin("EGS380P1C01"))    # too short
        self.assertFalse(is_valid_isin("EGS380P1C0100"))  # too long
        self.assertFalse(is_valid_isin("egs380p1c010"))   # lowercase
        self.assertFalse(is_valid_isin("12S380P1C010"))   # bad country
        self.assertFalse(is_valid_isin("EGS380P1C01X"))   # bad check char
        self.assertFalse(is_valid_isin(""))
        self.assertFalse(is_valid_isin(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
