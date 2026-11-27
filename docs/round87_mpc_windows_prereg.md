# Round 87: scheduled-event windows (CBE MPC decision dates), width-neutral reallocation (pre-registration)

Written and committed before any number is computed. Additive only: nothing edits scripts/ensemble.py or any frozen value. Shadow and descriptive: no adoption, no merge.

## Event source and provenance check
- Series: evaluation/macro_series/cbe_decisions.json, 38 decisions, 2022-03-21 to 2026-10-29, each row with a CBE source_url (annual reports and press releases, per docs/round79_macro_series_coverage.md). All captured cells (cutoffs 2023-12-29 to 2026-09-30) fall inside the series span.
- Known gaps, stated and not filled: 2021-12-16 and 2022-02-03 are confirmed meetings absent from the series (before every cutoff); 2022-11-03 is not a confirmed meeting. None affects a cell.
- Open point (not settled by the repo): the series holds realised decision dates. Whether each date was public before the cutoff (the CBE publishes a yearly meeting calendar; special meetings are not scheduled) is not verified in the repo: evaluation/macro_event/calendar_primary.json carries null publication fields. This screen treats a decision date as known at the cutoff, which is exact only for pre-announced meetings. Correction after review: the earlier wording said special meetings precede all captures. That was wrong: the series holds one special meeting after the first cutoff, 2024-03-06 (cbe_special), and a scheduled meeting that was cancelled, 2024-03-28 (not in the series). Checked with this screen's flag function over the 17 numbered-cell cutoffs (2023-12-29 to 2026-09-30) x 3 horizons: neither date lies in any window (the 2023-12-29 month window ends 2024-01-28; the next numbered cutoff is 2024-03-31), so no cell flag depends on a special or cancelled meeting. Whether the scheduled dates were public before each cutoff is a separate question, examined in docs/round87_mpc_publication_check.md (PR #947).

## Flag (fixed here)
A capture row (ticker, cutoff date c, horizon h) is flagged when a decision date d satisfies c < d <= end(c, h), where end is the h-th Egyptian business day (Sunday to Thursday) after c, holidays ignored. h = 1, 5, 21 sessions as in the scorers.

## Model
half(row) = m_flag x frozen v2 half-width, with m_event and m_nonevent per horizon.
- Fit on cells 1-47 only. m_event is searched on 0.70 to 1.50 in steps of 0.05; m_nonevent follows from the mean-width constraint: the training mean of m x v2 half-width equals the training mean v2 half-width. Candidates with m_nonevent <= 0 are skipped.
- Objective: mean Winkler IS on the training rows. Ties go to the m_event closest to 1.
- A horizon with fewer than 5 flagged or fewer than 5 unflagged training rows gets m = 1 for both (frozen v2) and is reported as not fitted.
- Multipliers are written once to evaluation/mpc_windows_frozen.json and then frozen.

## Reading
- Descriptive, cells 48-102: per horizon, group counts, coverage, RangeSkill vs naive, cutoff-clustered CIs, next to frozen v2 on the same rows. Numbers only, no verdict word or key.
- Loop bar, cells 91+ only, scored once: RangeSkill cutoff-clustered CI lower bound > 0 AND coverage CI overlapping [0.75, 0.85] with width <= 0.15 AND at least 10 cutoff clusters on each horizon. Fewer than 10 clusters on any horizon: counts only (no coverage, skill or CI is printed or written), no KEEP and no REJECT.
- No KEEP is an adoption by itself. Adoption is measured relative to frozen v2 on the same rows.
