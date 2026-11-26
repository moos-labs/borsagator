# Walk-forward backtest — v2 re-score for #592 (month = 21 sessions)

Published 2026-11-25, extended 2026-11-26 with batch-7 cells 48–50
and batch-8 cells 51–53.
Scorer v2 (`scripts/backtest_score.py`, PR #665 plus the `agg()`
empty-subset fix in PR #677). Sessions day/week/month 1/5/21 per
`ledger.DEFAULT_SESSIONS`.

## Coverage

- **42 cells re-scored** (675 forecasts, all matured):
  cells 1–47 except the 11 below, plus batch-7 cells 48 (SWDY.CA
  2025-09-30), 49 (HRHO.CA 2025-09-30) and 50 (COMI.CA 2025-12-31),
  and batch-8 cells 51 (ETEL.CA 2025-12-31), 52 (TMGH.CA 2025-12-31)
  and 53 (NVDA 2025-12-31).
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

## Headline (42 cells, month = 21)

| Entrant | Day MAE / RangeSkill | Week MAE / RangeSkill | Month MAE / RangeSkill |
|---|---|---|---|
| 2-family-ensemble | 3.19 / −1.162 | 8.91 / −1.645 | 18.43 / −1.592 |
| kronos-alone | 4.05 / −2.115 | 11.82 / −3.375 | 25.36 / −4.562 |
| family-technicals | 1.60 / −0.030 | 4.36 / −0.018 | 8.64 / −0.002 |
| naive-range (gate) | 1.53 / 0.000 | 4.47 / 0.000 | 8.71 / 0.000 |

Flat zero-move (buy-and-hold) MAE: 1.53 / 4.47 / 8.71. The ensemble
fails the RangeSkill gate at every horizon; Kronos month MAE 25.36 pp
vs zero-move 8.71 pp, direction hit 28.6%. The batch-7 cells alone:
ensemble month MAE 2.65 / 5.08 / 29.13 pp (cells 48/49/50), RangeSkill
+0.064 / +0.061 / −0.026 — the first two cells beat the naive range
on intervals; cell 50 (COMI +29.13% realised month) covers 0.000.
The batch-8 cells alone: ensemble month MAE 26.58 / 10.55 / 0.48 pp
(cells 51/52/53), RangeSkill −0.046 / +0.063 / +0.064; cell 51
(ETEL +26.58% realised month) covers 0.000, cell 53 (NVDA −0.48%)
is the first near-zero month. Kronos month on the batch-8 cells:
72.01 / 27.56 / 3.67 pp — still far worse than zero-move on the
two EGX cells.

## Tilt-technicals (n = 6 — no quality claim)

The six batch-7/8 captures are the first v2 captures, so they are
the first cells with `tilt_centre_pct`: tilt-technicals month MAE
12.67 pp, RangeSkill −0.05 (n = 6). No claim at this n; the tilt
is adopted only if its RangeSkill CI lower bound > 0 on untouched
cells (#594 adoption test).

## v1 reference (T1/T2 triage, 41 cells, month = 14 sessions)

Ensemble MAE 3.56 / 9.15 / 19.2; RangeSkill −1.06 / −1.59 / −2.48;
zero-move MAE 1.80 / 4.50 / 6.85. The month=21 re-score changes
almost nothing: the ~3 pp of the old month error that was the
scoring mismatch is gone, and the decay is still there — this
confirms the decay is real, not a scoring artifact.

## Gaps recorded by the scorer (177)

Every v1 capture lacks `sigma60_daily` (naive-range falls back to
`sigma_daily` as proxy) and `tilt_centre_pct` (`tilt-technicals` has
zero rows on the 36 v1 cells — the tilt is a v2-only entrant). EGX
captures have no index leg (`^EGX30` 404s on Yahoo; the EW-proxy
index leg per #436 T6 is still open). The tilt gap wording changed
with the #689 scorer hardening ("no usable tilt_centre_pct —
horizon skipped") — the scores are unchanged (all 618 old rows
reproduce exactly). See `backtest.json` `gaps`.
