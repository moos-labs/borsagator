# Walk-forward backtest — v2 re-score for #592 (month = 21 sessions)

Published 2026-11-25, extended 2026-11-26 with batch-7 cells 48–50,
batch-8 cells 51–53, batch-9 cells 54–59, batch-10 cells 60–63,
batch-11 cells 64–67, batch-12 cells 68, 69, 71, 72 and batch-13
cell 70 (TMGH.CA 2026-09-30, archive c0e7ebec).
Scorer v2 (`scripts/backtest_score.py`, PR #665 plus the `agg()`
empty-subset fix in PR #677). Sessions day/week/month 1/5/21 per
`ledger.DEFAULT_SESSIONS`.

## Coverage

- **61 cells re-scored** (1026 forecasts, all matured):
  cells 1–47 except the 11 below, plus batch-7 cells 48 (SWDY.CA
  2025-09-30), 49 (HRHO.CA 2025-09-30) and 50 (COMI.CA 2025-12-31),
  batch-8 cells 51 (ETEL.CA 2025-12-31), 52 (TMGH.CA 2025-12-31)
  and 53 (NVDA 2025-12-31), batch-9 cells 54 (SWDY.CA
  2025-12-31), 55 (HRHO.CA 2025-12-31), 56 (COMI.CA 2026-03-31),
  57 (ETEL.CA 2026-03-31), 58 (TMGH.CA 2026-03-31) and 59 (NVDA
  2026-03-31), and batch-10 cells 60 (SWDY.CA 2026-03-31),
  61 (HRHO.CA 2026-03-31), 62 (COMI.CA 2026-06-30) and 63 (ETEL.CA
  2026-06-30), and batch-11 cells 64 (TMGH.CA 2026-06-30),
  65 (NVDA 2026-06-30), 66 (SWDY.CA 2026-06-30) and 67 (HRHO.CA
  2026-06-30), and batch-12 cells 68 (COMI.CA 2026-09-30),
  69 (ETEL.CA 2026-09-30), 71 (NVDA 2026-09-30) and 72 (SWDY.CA
  2026-09-30), and batch-13 cell 70 (TMGH.CA 2026-09-30).
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

## Headline (61 cells, month = 21)

| Entrant | Day MAE / RangeSkill | Week MAE / RangeSkill | Month MAE / RangeSkill |
|---|---|---|---|
| 2-family-ensemble | 2.99 / −0.639 | 7.38 / −1.209 | 16.12 / −1.060 |
| kronos-alone | 3.62 / −1.224 | 9.67 / −2.723 | 22.83 / −3.750 |
| family-technicals | 1.95 / −0.043 | 4.38 / −0.024 | 9.58 / −0.033 |
| naive-range (gate) | 1.85 / 0.000 | 4.32 / 0.000 | 9.43 / 0.000 |

Flat zero-move (buy-and-hold) MAE: 1.85 / 4.32 / 9.43. The ensemble
fails the RangeSkill gate at every horizon; Kronos month MAE 22.83 pp
vs zero-move 9.43 pp, direction hit 32.8%. The batch-7 cells alone:
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
14.43 pp). The batch-10 cells alone: ensemble month MAE 11.68 /
12.16 / 10.98 / 22.55 pp (cells 60/61/62/63), RangeSkill −0.120 /
+0.065 / −0.237 / −0.042; Kronos month on the batch-10 cells:
14.11 / 2.61 / 18.20 / 43.31 pp — still far worse than zero-move
on three of the four cells, but better than the ensemble on cell 61
(HRHO, 2.61 vs 12.16 pp, coverage 1.000). The batch-11 cells alone:
ensemble month MAE 4.35 / 2.52 / 11.01 / 0.71 pp (cells 64/65/66/67),
RangeSkill +0.066 / +0.063 / −0.084 / +0.064; Kronos month on the
batch-11 cells: 31.59 / 1.52 / 18.17 / 9.75 pp — still far worse than
zero-move on three of the four cells, but better than the ensemble on
cell 65 (NVDA, 1.52 vs 2.52 pp, coverage 1.000, hit 1.000). The
batch-12 cells alone: ensemble month MAE 6.57 / 12.07 / 6.45 /
5.15 pp (cells 68/69/71/72), RangeSkill −0.166 / +0.012 / +0.063 /
+0.063; Kronos month on the batch-12 cells: 13.35 / 21.23 / 4.09 /
28.11 pp — still far worse than zero-move on three of the four
cells, but better than the ensemble on cell 71 (NVDA, 4.09 vs
6.45 pp, coverage 1.000). Cell 72 (SWDY.CA) shows a large day-1
miss on every entrant — a realised move, not a scorer fault. The
batch-13 cell alone: ensemble MAE 0.83 / 1.05 / 8.60 pp (cell 70),
RangeSkill +0.100 / 0.000 / −0.111; Kronos month on cell 70:
17.87 pp — still far worse than zero-move; cell 70 (TMGH.CA
−8.60% realised month) covers 0.000.

## Tilt-technicals (n = 25 — no quality claim)

The twenty-five batch-7/8/9/10/11/12/13 captures are the first v2 captures, so they
are the first cells with `tilt_centre_pct`: tilt-technicals month MAE
11.60 pp, RangeSkill −0.071 (n = 25). No claim at this n; the tilt
is adopted only if its RangeSkill CI lower bound > 0 on untouched
cells (#594 adoption test).

## v1 reference (T1/T2 triage, 41 cells, month = 14 sessions)

Ensemble MAE 3.56 / 9.15 / 19.2; RangeSkill −1.06 / −1.59 / −2.48;
zero-move MAE 1.80 / 4.50 / 6.85. The month=21 re-score changes
almost nothing: the ~3 pp of the old month error that was the
scoring mismatch is gone, and the decay is still there — this
confirms the decay is real, not a scoring artifact.

## Gaps recorded by the scorer (193)

Every v1 capture lacks `sigma60_daily` (naive-range falls back to
`sigma_daily` as proxy) and `tilt_centre_pct` (`tilt-technicals` has
zero rows on the 36 v1 cells — the tilt is a v2-only entrant). EGX
captures have no index leg (`^EGX30` 404s on Yahoo; the EW-proxy
index leg per #436 T6 is still open). The tilt gap wording changed
with the #689 scorer hardening ("no usable tilt_centre_pct —
horizon skipped") — the scores are unchanged (all 1008 old rows
reproduce exactly). See `backtest.json` `gaps`.
