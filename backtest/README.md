# Walk-forward backtest — v2 re-score for #592 (month = 21 sessions)

Published 2026-11-25, extended 2026-11-26 with batch-7 cells 48–50.
Scorer v2 (`scripts/backtest_score.py`, PR #665 plus the `agg()`
empty-subset fix in PR #677). Sessions day/week/month 1/5/21 per
`ledger.DEFAULT_SESSIONS`.

## Coverage

- **39 of the 41 scored cells re-scored** (618 forecasts, all matured):
  cells 1–47 except the 11 below, plus batch-7 cells 48 (SWDY.CA
  2025-09-30), 49 (HRHO.CA 2025-09-30) and 50 (COMI.CA 2025-12-31).
  Per-cell files: `cells/cellNN_score_v2.json`.
- **5 cells still v1-scored, NOT in this grid** — the 21-session realised
  window is unbuildable from the feed: cells 6, 7, 8, 20, 21 fail closed
  because 2024-05-01 has no usable close inside the window (the v1
  14-session windows ended before it). They stay on their v1 scores
  (month at 14 sessions) until the feed yields that session or the
  harness rule changes — no workaround was applied.
- **6 cells have no captures at all** (gate-skipped worker runs, never
  scored): cells 3 (ORAS.CA 2023-12-29, stale-flat), 10, 11, 12, 22, 23
  (whole 2024-06-30 cutoff — the 2024-07-01 gap).

## Headline (39 cells, month = 21)

| Entrant | Day MAE / RangeSkill | Week MAE / RangeSkill | Month MAE / RangeSkill |
|---|---|---|---|
| 2-family-ensemble | 3.29 / −1.278 | 9.30 / −1.742 | 18.89 / −1.799 |
| kronos-alone | 4.28 / −2.375 | 12.33 / −3.499 | 24.66 / −4.663 |
| family-technicals | 1.60 / −0.022 | 4.34 / −0.010 | 8.26 / +0.008 |
| naive-range (gate) | 1.50 / 0.000 | 4.53 / 0.000 | 8.42 / 0.000 |

Flat zero-move (buy-and-hold) MAE: 1.50 / 4.53 / 8.42. The ensemble
fails the RangeSkill gate at every horizon; Kronos month MAE 24.66 pp
vs zero-move 8.42 pp, direction hit 30.8%. The batch-7 cells alone:
ensemble month MAE 2.65 / 5.08 / 29.13 pp (cells 48/49/50), RangeSkill
+0.064 / +0.061 / −0.026 — the first two cells beat the naive range
on intervals; cell 50 (COMI +29.13% realised month) covers 0.000.

## Tilt-technicals (n = 3 — no quality claim)

The three batch-7 captures are the first v2 captures, so they are
the first cells with `tilt_centre_pct`: tilt-technicals month MAE
12.32 pp, RangeSkill −0.041 (n = 3). No claim at this n; the tilt
is adopted only if its RangeSkill CI lower bound > 0 on untouched
cells (#594 adoption test).

## v1 reference (T1/T2 triage, 41 cells, month = 14 sessions)

Ensemble MAE 3.56 / 9.15 / 19.2; RangeSkill −1.06 / −1.59 / −2.48;
zero-move MAE 1.80 / 4.50 / 6.85. The month=21 re-score changes
almost nothing: the ~3 pp of the old month error that was the
scoring mismatch is gone, and the decay is still there — this
confirms the decay is real, not a scoring artifact.

## Gaps recorded by the scorer (175)

Every v1 capture lacks `sigma60_daily` (naive-range falls back to
`sigma_daily` as proxy) and `tilt_centre_pct` (`tilt-technicals` has
zero rows on the 36 v1 cells — the tilt is a v2-only entrant). EGX
captures have no index leg (`^EGX30` 404s on Yahoo; the EW-proxy
index leg per #436 T6 is still open). The tilt gap wording changed
with the #689 scorer hardening ("no usable tilt_centre_pct —
horizon skipped") — the scores are unchanged (all 564 old rows
reproduce exactly). See `backtest.json` `gaps`.
