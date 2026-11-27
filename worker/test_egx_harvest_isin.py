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
import json
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

    def test_abuk_isin_is_the_ipf_value(self):
        """ABUK must be EGS38191C010 — IPF official fund-members
        list, row 50 (checked live 2026-11-27, issue #110). The old
        value EGS38161C013 is Unipak's ISIN (IPF row 57) and PASSES
        the check digit, so the validator alone cannot catch this
        class of error — only a pinned value can. The wrong ISIN
        made the harvest query Unipak's disclosures for ABUK."""
        _ar, isin = EGX_COMPANIES["ABUK"]
        self.assertEqual(isin, "EGS38191C010")

    def test_old_abuk_value_is_unipak_not_abuk(self):
        """The pre-fix value EGS38161C013 is a valid ISIN — for
        Unipak (UNIP.CA), not ABUK — so it must never appear as
        ABUK's entry again."""
        _ar, isin = EGX_COMPANIES["ABUK"]
        self.assertNotEqual(isin, "EGS38161C013")

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
                     "EGS38191C010",  # ABUK (IPF row 50; was EGS38161C013 = Unipak, #110)
                     "EGS69082C013"):  # EKHO
            self.assertTrue(is_valid_isin(isin), isin)

    def test_one_digit_off_fails(self):
        """Changing a single digit breaks the check digit."""
        self.assertFalse(is_valid_isin("EGS380P1C011"))  # AMOC +1
        self.assertFalse(is_valid_isin("EGS60121C019"))  # COMI +1

    # Issue #768 (BEAST MODE item 1): the harvester must accept the
    # living EGX33 freeze, not just the original 10 codes. The freeze
    # is sharia/benchmark/sources/egx33.json; the ISINs come from
    # evaluation/top30_manifest.json (stage-2). INS-PARALLEL-001 T1
    # (2026-11-26) closed the last gap: the 6 freeze codes with no
    # manifest ISIN (CLHO, FAITA, GOUR, ICFC, LCSW, RACC) now carry
    # verified ISINs in both the manifest and this table, so
    # _NO_ISIN_YET is empty — every freeze code must be present,
    # with the manifest's exact ISIN.
    _REPO = os.path.dirname(_HERE)
    _NO_ISIN_YET = frozenset()

    def _freeze_codes(self):
        with open(os.path.join(
                self._REPO, "sharia", "benchmark", "sources",
                "egx33.json"), encoding="utf-8") as f:
            rows = json.load(f)["rows"]
        return [r["ticker"].replace(".CA", "") for r in rows]

    def _manifest_isins(self):
        with open(os.path.join(
                self._REPO, "evaluation",
                "top30_manifest.json"), encoding="utf-8") as f:
            man = json.load(f)
        out = {}
        for iss in man["issuers"]:
            for listing in iss["listings"]:
                if listing.get("isin"):
                    out[listing["code"]] = listing["isin"]
        return out

    def test_freeze_coverage(self):
        """Every freeze code with a manifest ISIN is harvestable."""
        missing = [c for c in self._freeze_codes()
                   if c not in EGX_COMPANIES
                   and c not in self._NO_ISIN_YET]
        self.assertEqual(missing, [], f"freeze codes not in table: {missing}")
        self.assertEqual(len(EGX_COMPANIES), 41)

    def test_table_isins_match_manifest(self):
        """Table ISINs equal the manifest's — the manifest is the
        single source; a drifted copy fails here by name."""
        manifest = self._manifest_isins()
        mismatched = [(c, EGX_COMPANIES[c][1], manifest[c])
                      for c in self._freeze_codes()
                      if c in EGX_COMPANIES and c in manifest
                      and EGX_COMPANIES[c][1] != manifest[c]]
        self.assertEqual(mismatched, [], f"ISIN drift vs manifest: {mismatched}")

    def test_none_arabic_name_entries_validate(self):
        """Entries without a verified Arabic name (None) are
        allowed — the ISIN-keyed search needs no name — and still
        validate cleanly. After INS-PARALLEL-001 T2 (2026-11-26) the
        only unnamed entries are the 6 T1 codes, whose Arabic names
        were not delivered (never guessed)."""
        unnamed = [c for c, (ar, _isin) in EGX_COMPANIES.items()
                   if ar is None]
        self.assertEqual(sorted(unnamed),
                         ["CLHO", "FAITA", "GOUR", "ICFC", "LCSW",
                          "RACC"])
        self.assertEqual(validate_egx_companies_isins(), [])

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
