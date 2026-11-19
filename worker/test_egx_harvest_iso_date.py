#!/usr/bin/env python3
"""Regression tests: EGX harvester iso_date must take the publish date
from the standalone date line, never from the period start (issue #274).

Bug: worker/egx_harvest.py iso_date stamped the FIRST dd/mm/yyyy in
the first 400 chars of the body, falling back to the search-row text.
For earnings disclosures the title line itself carries the reporting
period ("... عن الفترة: من 01/01/2026 إلى 30/09/2026"), so the period
start won as the publish date — COMI 297291/297289 were stamped
2026-01-01 while the real publish date sits on its own line just
below ("10/11/2026"). The downstream news-disclosure-runner already
re-derives this at consumption (PR #1, merged 6943f1bf); this fixes
the harvester itself so the harvest file carries the right date.

The two COMI cases FAIL on pristine main and PASS on the fix; the
negative case (no standalone date line) must come back dateless (""),
never stamped with the period start.

Run:  python3 worker/test_egx_harvest_iso_date.py
  or:  python3 -m pytest worker/test_egx_harvest_iso_date.py -q
  or:  python3 -m unittest worker.test_egx_harvest_iso_date -v
No network, no fixture files: the real harvested bodies are embedded
below (COMI harvest, harvested_at 2026-11-18T13:40:16Z — same bodies
as news-disclosure-runner scripts/test_fetch_feed_iso_date.py).
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
iso_date = egx_harvest.iso_date

# --- Real harvested bodies (COMI, live harvest 2026-11-18) -----------
# 297291: consolidated Q3 results. Title carries the period range;
# standalone date line "10/11/2026" sits under it. Harvest "date"
# field (buggy): "2026-01-01".
BODY_297291 = 'تفاصيل الأخبار\n\n\n\nالبنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) تعلن نتائج أعمالها المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026\n10/11/2026\nاسم البنك: البنك التجاري الدولي -مصر (سى اى بى )\nكود الترقيم الدولي: EGS60121C018\nالعملة: جنيه مصرى\nالقوائم المالية المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026\nصافي الربح: 63,079,356 (القيمة بالألف)\nأرقام المقارنة المجمعة عن الفترة: من 01/01/2025 إلى 30/09/2025\nصافي الربح لفترة المقارنة: 62,100,264 (القيمة بالألف)\nتقرير فحص محدود: مرفق\nالمصدر: البنك التجاري الدولي -مصر (سى اى بى )\n\nمع الأخذ في الإعتبار حقوق الأقلية\n تقرير ممارسة النشاط المجمعة (64 KB)'
TITLE_297291 = 'البنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) تعلن نتائج أعمالها المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026'

# 297289: standalone Q3 results. Same layout, same bug.
BODY_297289 = 'تفاصيل الأخبار\n\n\n\nالبنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) تعلن نتائج أعمالها المستقلة عن الفترة: من 01/01/2026 إلى 30/09/2026\n10/11/2026\nاسم البنك: البنك التجاري الدولي -مصر (سى اى بى )\nكود الترقيم الدولي: EGS60121C018\nالعملة: جنيه مصرى\nالقوائم المالية المستقلة عن الفترة: من 01/01/2026 إلى 30/09/2026\nصافي الربح: 62,973,508 (القيمة بالألف)\nأرقام المقارنة المستقلة عن الفترة: من 01/01/2025 إلى 30/09/2025\nصافي الربح لفترة المقارنة: 62,207,506 (القيمة بالألف)\nتقرير فحص محدود: مرفق\nالمصدر: البنك التجاري الدولي -مصر (سى اى بى )\n تقرير ممارسة النشاط المستقل (63 KB)'
TITLE_297289 = 'البنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) تعلن نتائج أعمالها المستقلة عن الفترة: من 01/01/2026 إلى 30/09/2026'

# 297292: results statement (English). Correctly stamped 2026-11-10
# by the old code too — must stay 2026-11-10 (no regression).
BODY_297292 = 'تفاصيل الأخبار\n\n\n\nبيان من البنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) بخصوص نتائج أعمال البنك (باللغة الانجليزية)\n10/11/2026\nاسم البنك: البنك التجاري الدولي -مصر (سى اى بى )\nكود الترقيم الدولي: EGS60121C018\nكود رويترز: COMI.CA\nمضمون الإعلان :\nبيان من البنك بخصوص نتائج الأعمال عن الفترة المالية المنتهية في 30/09/2026 (باللغة الانجليزية).\n بيان من البنك باللغة الإنجليزية (440 KB)'
TITLE_297292 = 'بيان من البنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) بخصوص نتائج أعمال البنك (باللغة الانجليزية)'

# 296114: board report. Correctly stamped 2026-10-18 — must stay.
BODY_296114 = 'تفاصيل الأخبار\n\n\n\nالبنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) - نموذج تقرير إفصاح عن مجلس الإدارة وهيكل المساهمين\n18/10/2026\nاسم البنك: البنك التجاري الدولي -مصر (سى اى بى )\nكود الترقيم الدولي: EGS60121C018\nكود رويترز: COMI.CA\nمضمون الإعلان :\nورد نموذج تقرير إفصاح البنك عن مجلس الإدارة وهيكل المساهمين عن الفترة المنتهية في 30/09/2026, تنفيذاً للمادة 30 من قواعد القيد وذلك على مسئولية البنك.\n نموذج تقرير إفصاح باللغة العربية (205 KB)\n نموذج تقرير إفصاح باللغة الإنجليزية (2,662 KB)'
TITLE_296114 = 'البنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) - نموذج تقرير إفصاح عن مجلس الإدارة وهيكل المساهمين'

# Negative: 297291's body with the standalone date line deleted. The
# period range is still in the title, so a first-date reader would
# still find 01/01/2026 — the fixed code must return dateless instead.
BODY_NO_DATE_LINE = 'تفاصيل الأخبار\n\n\n\nالبنك التجاري الدولي -مصر (سى اى بى ) (COMI.CA) تعلن نتائج أعمالها المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026\nاسم البنك: البنك التجاري الدولي -مصر (سى اى بى )\nكود الترقيم الدولي: EGS60121C018\nالعملة: جنيه مصرى\nالقوائم المالية المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026\nصافي الربح: 63,079,356 (القيمة بالألف)\nأرقام المقارنة المجمعة عن الفترة: من 01/01/2025 إلى 30/09/2025\nصافي الربح لفترة المقارنة: 62,100,264 (القيمة بالألف)\nتقرير فحص محدود: مرفق\nالمصدر: البنك التجاري الدولي -مصر (سى اى بى )\n\nمع الأخذ في الإعتبار حقوق الأقلية\n تقرير ممارسة النشاط المجمعة (64 KB)'


class TestIsoDateFix(unittest.TestCase):
    def test_comi_297291_publish_date(self):
        """297291: stamped 2026-01-01 (period start) on pristine code;
        must be 2026-11-10 (standalone date line) after the fix."""
        self.assertEqual(iso_date(BODY_297291, TITLE_297291), "2026-11-10")

    def test_comi_297289_publish_date(self):
        """297289: same bug, same expected date."""
        self.assertEqual(iso_date(BODY_297289, TITLE_297289), "2026-11-10")

    def test_no_standalone_line_is_dateless_not_period_start(self):
        """No standalone date line: the item must come back dateless
        (""), never silently stamped with the period start 2026-01-01
        that the title line carries (and that the row-text fallback
        would have returned on pristine code)."""
        self.assertEqual(iso_date(BODY_NO_DATE_LINE, TITLE_297291), "")

    def test_unaffected_items_keep_their_dates(self):
        """Items the old code already dated right must not move."""
        self.assertEqual(iso_date(BODY_297292, TITLE_297292), "2026-11-10")
        self.assertEqual(iso_date(BODY_296114, TITLE_296114), "2026-10-18")

    def test_inline_dates_only_are_not_a_publish_date(self):
        """A body with only inline (period-range) dates has no publish
        date — dateless, not the period start."""
        body = ("Title عن الفترة: من 01/01/2026 إلى 30/09/2026\n"
                "صافي الربح: 63,079,356\n")
        self.assertEqual(iso_date(body, ""), "")

    def test_invalid_standalone_line_is_skipped(self):
        """An invalid standalone line is skipped; the next valid one
        wins."""
        self.assertEqual(
            iso_date("Title\n32/13/2026\n10/11/2026\nrest\n", ""), "2026-11-10")

    def test_single_digit_day_month(self):
        self.assertEqual(iso_date("Title\n5/1/2026\n", ""), "2026-01-05")

    def test_empty_body(self):
        self.assertEqual(iso_date("", ""), "")
        self.assertEqual(iso_date(None, None), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
