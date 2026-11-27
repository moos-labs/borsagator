# Round 83 — CBE bulletin series coverage (batch 3)

Takeover execution by the cycle (Ins silent past the 21:00 deadline, no result, no checkpoint, no branch).
Source: CBE Monthly Statistical Bulletin PDFs, Table 15 (weekly T-bill accepted yields, 91/182/273/364-day)
and Table 17 (weekly USD/EGP: interbank weighted average + market buy/sell, last working day of the week).
Basis: CBE market buy/sell and interbank averages — NOT the Mubasher price basis. Do not mix with repo price data.

Batch 3: 33 of 58 bulletins (No. 297 Dec 2021 – No. 354 Sep 2026) downloaded and extracted.
Bulletins done: 300, 301, 302, 303, 304, 305, 306, 312, 313, 314, 315, 316, 317, 318, 324, 325, 326, 327, 328, 329, 330, 338, 339, 340, 341, 342, 348, 349, 350, 351, 352, 353, 354.
Bulletins still to fetch (25): 297, 298, 299, 307, 308, 309, 310, 311, 319, 320, 321, 322, 323, 331, 332, 333, 334, 335, 336, 337, 343, 344, 345, 346, 347.

URL pattern (re-derived by the cycle from the CBE listing page + a probe of all 58 issues):
`https://www.cbe.org.eg/-/media/project/cbe/listing/monthly-statistical-bulletin/bulletin/<month>/monthly-statistical-bulletin-<N>.pdf`
where <month> is the lowercase English issue month and <N> the bulletin number.
Probe: 43/58 resolve on this pattern; the rest return 403 or a 112,038-byte "Request Rejected" page (CBE WAF, flaky —
the same URL can 403 once and serve the real PDF on retry; bulletin 340 landed on a batch-3 retry).
Legacy SharePoint `/_layouts/download.aspx?SourceUrl=%2FMonthlyStatisticaclBulletinDL%2FBulletin_<N>_%20<Mon>.%20<YYYY>.pdf`:
DEAD as tested in batch 3 — 4 filename variants (Dec. / Dec / full month / double-space) x the 25 missing bulletins, all 403/404.
Remaining route for the 25: further retries of the new pattern (WAF flakiness) or a browser-context fetch.

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

Validation on batch 3:
- Cross-bulletin consistency: every value that appears in more than one bulletin agrees EXACTLY (0 conflicts across all overlapping cells).
- June-2025 anchor: 91-day 28.619 (week ending 2025-06-19) and 29.108 (2025-06-26) confirmed in 9 independent bulletins (341, 342, 348–354).
- 273-day week ending 2021-07-01 is 13.297 (bulletins 300, 353) — the batch-1/2 coverage note calling it "genuinely empty"
  was wrong: it was the same band-boundary parser gap (bulletins 315/327/348/350/352 returned None pre-fix); the series
  value existed all along from 300/353 and now agrees across 6 bulletins. Corrected here.
- HEADER-MISLABEL-354: bulletin 354 (Sep 2026) has no 25-Jun or 9-Jul 2026 columns; the column it heads "25 June 2026" (marked ++ in the source) carries the week-ending-2026-07-02 values in all four tenors (91d 24.135, 182d 24.857, 273d 25.097, 364d 24.703 — exactly bulletins 352+353's 2026-07-02). 354's 2026-06-25 rows are dropped; the consensus 2026-06-25 value (91d 23.689) comes from 352/353. After this exclusion, cross-bulletin conflicts are 0.
- published_date is the first of the bulletin issue month (the bulletin lags ~2 months behind its issue month); observed_date is the week-ending date.

Series counts (batch 3):
- tbill_91d_weekly.csv: 172 weekly yields.
- tbill_182d_weekly.csv: 172 weekly yields.
- tbill_273d_weekly.csv: 172 weekly yields.
- tbill_364d_weekly.csv: 172 weekly yields.
- usd_egp_interbank_weekly.csv: 202 weekly rates.
- usd_egp_market_buy_weekly.csv: 202 weekly rates.
- usd_egp_market_sell_weekly.csv: 202 weekly rates.
