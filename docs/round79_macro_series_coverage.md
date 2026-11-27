# Round 79: macro series coverage (what is collected, what is missing)

Scope: KEEP 5 YEARS (2021-11-27 to 2026-11-27). Every value below carries the page it was read from; nothing is from memory. Format: value, observed_date, published_date, source_url, source_name, readable as-is by benchmarks/regime_macro_tilt_shadow.py (load_rows: 30 rows, 0 rejected; load_decisions: 30 usable, 0 rejected).

## Collected
- evaluation/macro_series/cbe_overnight_deposit_rate.csv: CBE overnight deposit rate after each MPC decision, 30 decisions from 2023-03-30 to 2026-10-29. observed_date = published_date = the decision date (the release time is unsettled, so the regime uses it from the next session). Each source is the CBE MPC press release page (English; Arabic where the English page is not served to the fetcher: 2023-06-22, 2024-09-05, 2025-02-20; PDF for 2023-09-21 and 2023-11-02). Levels were read from each page's text.
- evaluation/macro_series/cbe_decisions.json: the change in basis points per decision, the scaffold's decision format. Four changes are as stated in the release (2023-03-30 +200, 2023-08-03 +100, 2024-02-01 +200, 2024-03-06 +600); the others are the difference of consecutive sourced levels (the pages state the level or "unchanged"; for 2025-04-17 the release states a 225 bp cut and the level difference agrees).
- evaluation/macro_series/regime_counts_descriptive.json: the scaffold's counts-only run on the real ledger with these decisions. Result: all 309 captures have a regime and ALL are "tightening" (the last decision before every capture is the 29 Oct 2026 hike), 13 cutoff dates per horizon. The current ledger therefore has no regime variation; the regime tilt cannot be compared across regimes on it.

## Missing (not collected, no value filled)
- CBE decisions from 2021-11-27 to 2023-03-29 that are inside the 5-year scope: 2021-12-16, 2022-02-03, 2022-03-21 (special), 2022-05-19, 2022-06-23, 2022-09-22, 2022-10-27 (special), 2022-12-22. The calendar lists them from annual reports and aggregators, not from a press-release page read this round. Without them the regime before 2023-03-30 is unknown (no last decision).
- CPI (CAPMAS release): not collected.
- USD/EGP: not collected. The index prices in the repo use the Mubasher basis; no FX series with a named basis is on file.
- 91-day T-bill auction yield: not collected.
Reason: collection by reading each source page took the whole time budget; the policy-rate series is the one that defines the pre-registered regime (design section 2), the other three are inputs only to the reserved second flag and are not needed for the first pass.
