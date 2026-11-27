# Round 83 — CBE bulletin series coverage (batch 4)

Takeover execution by the cycle (Ins silent past the 21:00 deadline, no result, no checkpoint, no branch).
Source: CBE Monthly Statistical Bulletin PDFs, Table 15 (weekly T-bill accepted yields, 91/182/273/364-day)
and Table 17 (weekly USD/EGP: interbank weighted average + market buy/sell, last working day of the week).
Basis: CBE market buy/sell and interbank averages — NOT the Mubasher price basis. Do not mix with repo price data.

Batch 4: 58 of 58 bulletins (No. 297 Dec 2021 – No. 354 Sep 2026) downloaded and extracted. The pass is COMPLETE.
Bulletins done: 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354.
Bulletins still to fetch (0): none.

Batch 4 (this push): the remaining 25 bulletins (297–299, 307–311, 319–323, 331–337, 343–347) landed 23:03–23:07 Cairo
on their real listing URLs, first try except 332 and 343 (403 once, real PDF on retry — CBE WAF flakiness). All 25
extracted cleanly: 72 Table-15 cells each (18 weekly dates x 4 tenors), 16 Table-17 weeks each except 308 (11 — its
Table 17 window is genuinely shorter: 2022-07-07..2022-10-27 with gaps; the union across bulletins fills it).
The browser link-collection handoff for these 24 URLs never arrived — it was not needed: the URLs follow the
listing pattern with two variants the diagnostic exposed (see below), and all 25 fetched from the VM on retry.

URL forms (per-bulletin source_url is recorded in each series CSV row — do not reconstruct from a pattern):
- Usual form: `.../bulletin/<month>/monthly-statistical-bulletin-<N>.pdf` (month = lowercase English issue month).
- No. 297: `.../bulletin/dec/bulletin297dec2021.pdf` (old short filename form).
- No. 331–337: `.../bulletin/<month>/monthly-statistical-bulletin--<N>.pdf` (double dash before the number).
Legacy SharePoint `/_layouts/download.aspx?SourceUrl=%2FMonthlyStatisticaclBulletinDL%2FBulletin_<N>_%20<Mon>.%20<YYYY>.pdf`:
DEAD as tested in batch 3 — 4 filename variants (Dec. / Dec / full month / double-space) x the 25 missing bulletins, all 403/404.

Parser: `scripts/extract_cbe_bulletin.py` (pdftotext -bbox word coordinates). Table 15 column years come from the
Interbank "From d/m - d/m/yyyy" 2-week ranges printed on the same page — each range covers one pair of weekly columns;
the range end-year is the year for both columns. For a range that crosses New Year, the column dated before
New Year takes the year before the end-year, and the column dated after New Year takes the end-year.
No year is inferred from column order alone.
Batch-3 parser fix (band-boundary split): a tenor row's values can sit just across the round(y/3) band boundary
from its label (bulletin 353, 182-day: label y=283.4 -> band 94, values y=283.5 -> band 95), so the label's own
band held no values and the row parsed all-None. Value collection now merges bands k-1/k/k+1 (same merge as
Table 17); adjacent tenor rows are ~11pt apart, so the merge cannot reach another row's values. Re-extraction
of all 33 bulletins reproduces every previously extracted value byte-identically; the fix only fills cells that
were None (+8 net new series cells: 364-day 2023-07-06/13, 2025-05-08/15/22/29; 182-day 2025-07-03/10).

Batch-4 correction — HEADER-MISLABEL-354 now applied to the series CSVs: batch 3's build script never dropped
bulletin 354's 2026-06-25 rows, so the pushed tbill_*d_weekly.csv files carried 354's mislabelled values for that
week (91d 24.135, 182d 24.857, 273d 25.097, 364d 24.703) instead of the 352/353 consensus. This push corrects all
four 2026-06-25 rows to the consensus (91d 23.689, 182d 24.673, 273d 24.782, 364d 24.517, sourced from 352).
The 2026-07-02 rows were already right (24.135/24.857/25.097/24.703 from 352/353).

Validation on batch 4:
- Cross-bulletin consistency: every value that appears in more than one bulletin agrees EXACTLY (0 conflicts across all overlapping cells).
- June-2025 anchor: 91-day 28.619 (week ending 2025-06-19) and 29.108 (2025-06-26) confirmed in 9 independent bulletins (341, 342, 348–354).
- 273-day week ending 2021-07-01 is 13.297 (bulletins 300, 353) — the batch-1/2 coverage note calling it "genuinely empty"
  was wrong: it was the same band-boundary parser gap (bulletins 315/327/348/350/352 returned None pre-fix); the series
  value existed all along from 300/353 and now agrees across 6 bulletins. Corrected here.
- HEADER-MISLABEL-354: bulletin 354 (Sep 2026) has no 25-Jun or 9-Jul 2026 columns; the column it heads "25 June 2026" (marked ++ in the source) carries the week-ending-2026-07-02 values in all four tenors (91d 24.135, 182d 24.857, 273d 25.097, 364d 24.703 — exactly bulletins 352+353's 2026-07-02). 354's 2026-06-25 rows are dropped; the consensus 2026-06-25 value (91d 23.689) comes from 352/353. After this exclusion, cross-bulletin conflicts are 0.
- published_date is the first of the bulletin issue month (the bulletin lags ~2 months behind its issue month); observed_date is the week-ending date.

Series counts (batch 4, 58/58 bulletins):
- tbill_91d_weekly.csv: 263 weekly yields.
- tbill_182d_weekly.csv: 263 weekly yields.
- tbill_273d_weekly.csv: 263 weekly yields.
- tbill_364d_weekly.csv: 263 weekly yields.
- usd_egp_interbank_weekly.csv: 262 weekly rates.
- usd_egp_market_buy_weekly.csv: 262 weekly rates.
- usd_egp_market_sell_weekly.csv: 262 weekly rates.
