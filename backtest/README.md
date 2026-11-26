# Walk-forward backtest — v2 re-score for #592 (month = 21 sessions)

Published 2026-11-25, extended 2026-11-26 with batch-7 cells 48–50,
batch-8 cells 51–53 and batch-9 cells 54–59.
Scorer v2 (`scripts/backtest_score.py`, PR #665 plus the `agg()`
empty-subset fix in PR #677). Sessions day/week/month 1/5/21 per
`ledger.DEFAULT_SESSIONS`.

## Coverage

- **48 cells re-scored** (786 forecasts, all matured):
  cells 1–47 except the 11 below, plus batch-7 cells 48 (SWDY.CA
  2025-09-30), 49 (HRHO.CA 2025-09-30) and 50 (COMI.CA 2025-12-31),
  batch-8 cells 51 (ETEL.CA 2025-12-31), 52 (TMGH.CA 2025-12-31)
  and 53 (NVDA 2025-12-31), and batch-9 cells 54 (SWDY.CA
  2025-12-31), 55 (HRHO.CA 2025-12-31), 56 (COMI.CA 2026-03-31),
  57 (ETEL.CA 2026-03-31), 58 (TMGH.CA 2026-03-31) and 59 (NVDA
  2026-03-31).
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

## Headline (48 cells, month = 21)

| Entrant | Day MAE / RangeSkill | Week MAE / RangeSkill | Month MAE / RangeSkill |
|---|---|---|---|
| 2-family-ensemble | 3.20 / −0.906 | 8.46 / −1.440 | 18.10 / −1.287 |
| kronos-alone | 3.95 / −1.715 | 10.91 / −3.015 | 24.35 / −3.878 |
| family-technicals | 1.86 / −0.049 | 4.53 / −0.025 | 9.62 / −0.010 |
| naive-range (gate) | 1.75 / 0.000 | 4.57 / 0.000 | 9.59 / 0.000 |

Flat zero-move (buy-and-hold) MAE: 1.75 / 4.57 / 9.59. The ensemble
fails the RangeSkill gate at every horizon; Kronos month MAE 24.35 pp
vs zero-move 9.59 pp, direction hit 33.3%. The batch-7 cells alone:
ensemble month MAE 2.65 / 5.08 / 29.13 pp (cells 48/49/50), RangeSkill
+0.064 / +0.061 / −0.026 — the first two cells beat the naive range
on intervals; cell 50 (COMI +29.13% realised month) covers 0.000.
The batch-8 cells alone: ensemble month MAE 26.58 / 10.55 / 0.48 pp
(cells 51/52/53), RangeSkill −0.046 / +0.063 / +0.064; cell 51
(ETEL +26.58% realised month) covers 0.000, cell 53 (NVDA −0.48%)
is the first near-zero month. Kronos month on the batch-8 cells:
72.01 / 27.56 / 3.67 pp — still far worse than zero-move on the
two EGX cells. The batch-9 cells alone: ensemble month MAE 2.25 /
17.54 / 12.40 / 18.97 / 28.86 / 14.43 pp (cells 54/55/56/57/58/59),
RangeSkill +0.064 / −0.042 / +0.065 / +0.065 / −0.043 / −0.197;
Kronos month on the batch-9 cells: 5.82 / 8.24 / 22.86 / 43.46 /
19.43 / 3.83 pp — still far worse than zero-move on the five EGX
cells, and better than the ensemble only on cell 59 (NVDA, 3.83 vs
14.43 pp).

## Tilt-technicals (n = 12 — no quality claim)

The twelve batch-7/8/9 captures are the first v2 captures, so they
are the first cells with `tilt_centre_pct`: tilt-technicals month MAE
14.37 pp, RangeSkill −0.052 (n = 12). No claim at this n; the tilt
is adopted only if its RangeSkill CI lower bound > 0 on untouched
cells (#594 adoption test).

## v1 reference (T1/T2 triage, 41 cells, month = 14 sessions)

Ensemble MAE 3.56 / 9.15 / 19.2; RangeSkill −1.06 / −1.59 / −2.48;
zero-move MAE 1.80 / 4.50 / 6.85. The month=21 re-score changes
almost nothing: the ~3 pp of the old month error that was the
scoring mismatch is gone, and the decay is still there — this
confirms the decay is real, not a scoring artifact.

## Gaps recorded by the scorer (182)

Every v1 capture lacks `sigma60_daily` (naive-range falls back to
`sigma_daily` as proxy) and `tilt_centre_pct` (`tilt-technicals` has
zero rows on the 36 v1 cells — the tilt is a v2-only entrant). EGX
captures have no index leg (`^EGX30` 404s on Yahoo; the EW-proxy
index leg per #436 T6 is still open). The tilt gap wording changed
with the #689 scorer hardening ("no usable tilt_centre_pct —
horizon skipped") — the scores are unchanged (all 675 old rows
reproduce exactly). See `backtest.json` `gaps`.
