# Round 143: regime macro tilt, first pass (shadow, descriptive)

UPDATE (Moos Slack 1795858391.997729, relayed): the two calendar-excluded holds (2022-08-18, 2023-02-02) were added to calendar_primary.json (source: the CBE annual report 2022/23 text, which states both meeting dates and the unchanged rate) and removed from its `excluded` list; the verified file now has 38 decisions. No scored row is affected (first cutoff 2023-12-29). The 36-decision numbers below are unchanged by it.

Design and pre-registration: docs/round78_regime_macro_tilt_design.md (merged #933). Series: evaluation/macro_series (merged #939). Source: Moos Slack 1795857428.814079 (thread 1795818091.610649), relayed by the main agent. Shadow only: no ensemble.py or frozen-value edits, no verdict word or key, no KEEP claim.

## (a) Verification of evaluation/macro_series/cbe_decisions.json (38 decisions)
Checked against evaluation/macro_event/calendar_primary.json (events, `excluded` list) and the policy rate stated in the cited CBE source, read on 2026-11-28.
- 30 decisions cite an MPC press release (2023-03-30 to 2026-10-29). Each page was fetched and the stated overnight deposit rate and the stated change (raise/cut by N bps, or kept unchanged at X percent) were read: all 30 match the file's change_bps, the levels chain consecutively (e.g. 18.25 -> 19.25 -> 21.25 -> 27.25 -> 25.00 -> 24.00 -> 22.00 -> 21.00 -> 20.00 -> 19.00 -> 20.00), and each press-release date equals the meeting date. Three are Arabic pages (2023-06-22, 2024-09-05, 2025-02-20): hold at the stated levels. All 30 are on the calendar as cbe_scheduled or cbe_special.
- 6 decisions cite CBE annual reports (2022-03-21 +100, 2022-05-19 +200, 2022-06-23 hold, 2022-09-22 hold, 2022-10-27 +200, 2022-12-22 +300): meeting dates and changes are stated in the annual report text and the dates are on the calendar.
- FAIL, not used: 2022-08-18 (hold) and 2023-02-02 (hold). Both are in the calendar's `excluded` list ("day only in secondary schedule"), so neither date is a calendar event. The 2022/23 annual report text does state both meetings (August 18 and September 22, 2022 kept unchanged; February 2nd, 2023 kept unchanged); the calendar has not been updated to match. They are held out of the verified file until the calendar is updated. No scored row is affected: the earliest capture cutoff is 2023-12-29 and later decisions override both.
- The calendar has 7 CBE events with no decision row (2020-03-16, 2020-12-24, 2021-08-05, 2021-09-16, 2021-10-28, 2021-12-16, 2022-02-03): all before the first capture cutoff, unused.
- Release time is unsourced (calendar release_time null): a decision counts only from the NEXT session (published_date strictly before as_of), as in the shadow scaffold.
Verified file used by the scorer: evaluation/macro_series/cbe_decisions_verified_r143.json (36 decisions; the original file is unchanged).

## (b) Counts (benchmarks/regime_macro_tilt_shadow.py, then score_regime_macro_tilt.py counts)
The scaffold reads the live ledger (13 cutoffs, 2026-11-12 to 2026-11-27, 309 rows): 309 with a regime, 0 without, all tightening (last decision 2026-10-29 +100), 103 rows and 13 cutoff dates per horizon. For the backtest cells, counts come from capture paths only:
train 1-47: captures=46 with regime=46 without regime=0
  tightening day: captures=6 cutoff clusters=1
  tightening week: captures=6 cutoff clusters=1
  tightening month: captures=6 cutoff clusters=1
  easing day: captures=10 cutoff clusters=2
  easing week: captures=10 cutoff clusters=2
  easing month: captures=10 cutoff clusters=2
  hold day: captures=30 cutoff clusters=5
  hold week: captures=30 cutoff clusters=5
  hold month: captures=30 cutoff clusters=5
descriptive 48-90: captures=43 with regime=43 without regime=0
  tightening day: captures=0 cutoff clusters=0
  tightening week: captures=0 cutoff clusters=0
  tightening month: captures=0 cutoff clusters=0
  easing day: captures=20 cutoff clusters=4
  easing week: captures=20 cutoff clusters=4
  easing month: captures=20 cutoff clusters=4
  hold day: captures=23 cutoff clusters=4
  hold week: captures=23 cutoff clusters=4
  hold month: captures=23 cutoff clusters=4
untouched 91+: captures=12 with regime=12 without regime=0
  tightening day: captures=0 cutoff clusters=0
  tightening week: captures=0 cutoff clusters=0
  tightening month: captures=0 cutoff clusters=0
  easing day: captures=6 cutoff clusters=1
  easing week: captures=6 cutoff clusters=1
  easing month: captures=6 cutoff clusters=1
  hold day: captures=6 cutoff clusters=1
  hold week: captures=6 cutoff clusters=1
  hold month: captures=6 cutoff clusters=1
Untouched 91+ has 2 cutoff clusters in total (one easing, one hold), far below the 10-cluster bar.

## (c) Training fit (cells 1-47 only; grid 0.9 / 1.0 / 1.1; ties to 1.0; centre 0)
132 rows built, 132 usable, 0 exclusions. Rows per regime and horizon: tightening 6/6/6 (1 cluster), easing 10/10/4 (2/2/1 clusters), hold 30/30/30 (5 clusters).
Fitted width multipliers: tightening 0.9, easing 0.9, hold 0.9 (per regime, all horizons pooled, mean Winkler IS; my design choices are listed in the report).

## Descriptive numbers, cells 48-90 (numbers only, 5000 reps, seed 20261125)
DESCRIPTIVE ONLY cells 48-90, 5000 reps seed 20261125, multipliers {"tightening": 0.9, "easing": 0.9, "hold": 0.9}
day: n=43, 8 cutoffs
  tilt: coverage 0.674 RangeSkill -0.048 coverage CI cutoff [0.500, 0.850]
  frozen v2: coverage 0.674 RangeSkill -0.020
  tilt minus v2 RangeSkill CI cutoff [-0.055, 0.018]
week: n=43, 8 cutoffs
  tilt: coverage 0.814 RangeSkill -0.003 coverage CI cutoff [0.689, 0.932]
  frozen v2: coverage 0.814 RangeSkill -0.000
  tilt minus v2 RangeSkill CI cutoff [-0.046, 0.054]
month: n=43, 8 cutoffs
  tilt: coverage 0.535 RangeSkill -0.067 coverage CI cutoff [0.383, 0.729]
  frozen v2: coverage 0.628 RangeSkill -0.018
  tilt minus v2 RangeSkill CI cutoff [-0.080, -0.005]

## Keep rule (untouched 91+ only)
RangeSkill cutoff-clustered CI lower bound > 0 AND coverage CI overlaps [0.75, 0.85] with width <= 0.15 AND >= 10 fully mature clusters; fewer = counts only, no KEEP. `loop_bar` in the scorer states this rule; no mode loads outcomes of cells 91+, so no KEEP is computed.

## Decisions table
| published_date | change_bps | source file |
|---|---|---|
| 2022-03-21 | 100.0 | annual-report-2021-2022.pdf |
| 2022-05-19 | 200.0 | annual-report-2021-2022.pdf |
| 2022-06-23 | 0.0 | annual-report-2021-2022.pdf |
| 2022-08-18 | 0.0 | annual-report-2022-2023_-en.pdf |
| 2022-09-22 | 0.0 | annual-report-2022-2023_-en.pdf |
| 2022-10-27 | 200.0 | annual-report-2022-2023_-en.pdf |
| 2022-12-22 | 300.0 | annual-report-2022-2023_-en.pdf |
| 2023-02-02 | 0.0 | annual-report-2022-2023_-en.pdf |
| 2023-03-30 | 200 | mpc-press-release-30-march-2023 |
| 2023-05-18 | 0.0 | mpc-press-release-18-may-2023 |
| 2023-06-22 | 0.0 | mpc-press-release-22-june-2023 |
| 2023-08-03 | 100 | mpc-press-release-3-august-2023 |
| 2023-09-21 | 0.0 | mpc-press-release--21-september-2023.pdf |
| 2023-11-02 | 0.0 | mpc-press-release--2-november-2023.pdf |
| 2023-12-21 | 0.0 | mpc-press-release-21-december-2023 |
| 2024-02-01 | 200 | press-release-%E2%80%93-february-1st%2C-2024 |
| 2024-03-06 | 600 | special-mpc-press-release-6-march-2024 |
| 2024-05-23 | 0.0 | mpc-press-release-23-may-2024 |
| 2024-07-18 | 0.0 | mpc-press-release-18-july-2024 |
| 2024-09-05 | 0.0 | mpc-press-release-5-september-2024 |
| 2024-10-17 | 0.0 | mpc-press-release-17-october-2024 |
| 2024-11-21 | 0.0 | mpc-press-release-21-november-2024 |
| 2024-12-26 | 0.0 | mpc-press-release-26-december-2024 |
| 2025-02-20 | 0.0 | mpc-press-release-20-february-2025 |
| 2025-04-17 | -225.0 | mpc-press-release-17-april-2025 |
| 2025-05-22 | -100.0 | mpc-press-release-22-may-2025 |
| 2025-07-10 | 0.0 | mpc-press-release-10-july-2025 |
| 2025-08-28 | -200.0 | mpc-press-release-28-august-2025 |
| 2025-10-02 | -100.0 | mpc-press-release-2-october-2025 |
| 2025-11-20 | 0.0 | mpc-press-release-20-november-2025 |
| 2025-12-25 | -100.0 | mpc-press-release-25-december-2025 |
| 2026-02-12 | -100.0 | mpc-press-release-12-february-2026 |
| 2026-04-02 | 0.0 | mpc-press-release-2-april-2026 |
| 2026-05-21 | 0.0 | mpc-press-release-21-may-2026 |
| 2026-07-09 | 0.0 | mpc-press-release-9-july-2026 |
| 2026-08-20 | 0.0 | mpc-press-release-20-august-2026 |
| 2026-09-24 | 0.0 | mpc-press-release-24-september-2026 |
| 2026-10-29 | 100.0 | mpc-press-release-29-october-2026 |