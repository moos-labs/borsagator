# Walk-forward backtest — v2 re-score for #592 (month = 21 sessions)

Published 2026-11-25. Scorer v2 (`scripts/backtest_score.py`, PR #665
plus the `agg()` empty-subset fix in PR #677). Sessions day/week/month
1/5/21 per `ledger.DEFAULT_SESSIONS`.

## Coverage

- **36 of the 41 scored cells re-scored** (564 forecasts, all matured):
  cells 1–47 except the 11 below. Per-cell files: `cells/cellNN_score_v2.json`.
- **5 cells still v1-scored, NOT in this grid** — the 21-session realised
  window is unbuildable from the feed: cells 6, 7, 8, 20, 21 fail closed
  because 2024-05-01 has no usable close inside the window (the v1
  14-session windows ended before it). They stay on their v1 scores
  (month at 14 sessions) until the feed yields that session or the
  harness rule changes — no workaround was applied.
- **6 cells have no captures at all** (gate-skipped worker runs, never
  scored): cells 3 (ORAS.CA 2023-12-29, stale-flat), 10, 11, 12, 22, 23
  (whole 2024-06-30 cutoff — the 2024-07-01 gap).

## Headline (36 cells, month = 21)

| Entrant | Day MAE / RangeSkill | Week MAE / RangeSkill | Month MAE / RangeSkill |
|---|---|---|---|
| 2-family-ensemble | 3.48 / −1.333 | 9.86 / −1.796 | 19.44 / −2.119 |
| kronos-alone | 4.54 / −2.439 | 13.13 / −3.564 | 25.08 / −5.298 |
| family-technicals | 1.64 / −0.028 | 4.46 / −0.003 | 7.92 / +0.020 |
| naive-range (gate) | 1.54 / 0.000 | 4.68 / 0.000 | 8.09 / 0.000 |

Flat zero-move (buy-and-hold) MAE: 1.54 / 4.68 / 8.09. The ensemble
fails the RangeSkill gate at every horizon; Kronos month MAE 25.08 pp
vs zero-move 8.09 pp, direction hit 30.6%.

## v1 reference (T1/T2 triage, 41 cells, month = 14 sessions)

Ensemble MAE 3.56 / 9.15 / 19.2; RangeSkill −1.06 / −1.59 / −2.48;
zero-move MAE 1.80 / 4.50 / 6.85. The month=21 re-score changes
almost nothing: the ~3 pp of the old month error that was the
scoring mismatch is gone, and the decay is still there — this
confirms the decay is real, not a scoring artifact.

## Gaps recorded by the scorer (172)

Every v1 capture lacks `sigma60_daily` (naive-range falls back to
`sigma_daily` as proxy) and `tilt_centre_pct` (`tilt-technicals` has
zero rows on all 36 cells — the tilt is a v2-only entrant). EGX
captures have no index leg (`^EGX30` 404s on Yahoo; the EW-proxy
index leg per #436 T6 is still open). See `backtest.json` `gaps`.
