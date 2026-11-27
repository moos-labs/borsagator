# Walk-forward backtest — v2 re-score for #592 (month = 21 sessions)

Published 2026-11-25, extended 2026-11-26 with batch-7 cells 48–50,
batch-8 cells 51–53, batch-9 cells 54–59, batch-10 cells 60–63,
batch-11 cells 64–67, batch-12 cells 68, 69, 71, 72, batch-13
cell 70 (TMGH.CA 2026-09-30, archive c0e7ebec) and batch-14
cells 73–78 (2026-08-14 × COMI/ETEL/TMGH/NVDA/SWDY/HRHO).
Scorer v2 (`scripts/backtest_score.py`, PR #665 plus the `agg()`
empty-subset fix in PR #677). Sessions day/week/month 1/5/21 per
`ledger.DEFAULT_SESSIONS`.

## Coverage

- **67 cells re-scored** (1137 forecasts, all matured):
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
  2026-09-30), and batch-13 cell 70 (TMGH.CA 2026-09-30), and
  batch-14 cells 73 (COMI.CA 2026-08-14), 74 (ETEL.CA 2026-08-14),
  75 (TMGH.CA 2026-08-14), 76 (NVDA 2026-08-14), 77 (SWDY.CA
  2026-08-14) and 78 (HRHO.CA 2026-08-14).
  Per-cell files: `cells/cellNN_score_v2.json`.
- **5 cells still v1-scored, NOT in this grid** — the 21-session realised
  window is unbuildable from the feed: cells 6, 7, 8, 20, 21 fail closed
  because 2024-05-01 has no usable close inside the window (the v1
  14-session windows ended before it). They stay on their v1 scores
  (month at 14 sessions) until the feed yields that session or the
  harness rule changes — no workaround was applied.
- **6 cells have no captures at all** (gate-skipped worker runs, never
  scored): cells 3 (ORAS.CA 2023-12-29, stale-flat), 10, 11, 12, 22, 23
  (whole 2024-06-30 cutoff — the 2024-07-01 gap). REPAIR-002
  (PR pending, #436): the 2024-07-01 closes are verified (EGX30
  printed 27,969.59, +0.73%; Mubasher chartData: COMI 78.02 on the
  Yahoo basis, ETEL 30.99, TMGH 57.12, SWDY 47.63, HRHO 19.38)
  and the repair table now covers the date — the five cells await
  re-dispatch to the worker once the repair reaches worker-release
  (promotion, then `run backtest 2024-06-30 <ticker>`).

## Headline (67 cells, month = 21)

| Entrant | Day MAE / RangeSkill | Week MAE / RangeSkill | Month MAE / RangeSkill |
|---|---|---|---|
| 2-family-ensemble | 2.72 / −0.603 | 6.96 / −1.135 | 15.35 / −0.995 |
| kronos-alone | 3.41 / −1.161 | 9.34 / −2.693 | 22.55 / −3.841 |
| family-technicals | 1.82 / −0.057 | 4.23 / −0.026 | 9.30 / −0.031 |
| naive-range (gate) | 1.68 / 0.000 | 4.18 / 0.000 | 9.25 / 0.000 |

Flat zero-move (buy-and-hold) MAE: 1.68 / 4.18 / 9.25. The ensemble
fails the RangeSkill gate at every horizon; Kronos month MAE 22.55 pp
vs zero-move 9.25 pp, direction hit 34.3%. The batch-7 cells alone:
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
−8.60% realised month) covers 0.000. The batch-14 cells alone
(2026-08-14): ensemble month MAE 4.27 / 11.40 / 1.07 / 5.77 /
17.18 / 5.29 pp (cells 73/74/75/76/77/78), RangeSkill +0.067 /
+0.065 / +0.062 / +0.062 / −0.096 / +0.063; Kronos month on the
batch-14 cells: 4.94 / 44.66 / 11.29 / 4.49 / 43.73 / 9.07 pp —
still far worse than zero-move on five of the six cells, better
than the ensemble only on cell 76 (NVDA, 4.49 vs 5.77 pp);
Kronos month coverage is 0.000 on all six. Note: day MAE is 0.00
on the five EGX batch-14 cells because the Yahoo series repeats
the 2026-08-14 close on the 2026-08-16 session — the worker's own
v1 realised.json agrees, so the flat day-1 move is feed
construction, not a scorer fault.

## Tilt-technicals (n = 31 — adoption test decisive, DO NOT ADOPT)

The thirty-one batch-7/8/9/10/11/12/13/14 captures are the first v2 captures, so they
are the first cells with `tilt_centre_pct`: tilt-technicals month MAE
10.75 pp, RangeSkill −0.057 (n = 31); day −0.024, week −0.011.
Coverage 0.710 / 0.774 / 0.581. The #594 adoption test at n = 31
(2026-11-26) is decisive: DO NOT ADOPT on all three horizons —
frozen v2 RangeSkill −0.023 / −0.001 / −0.022 with 95% CIs
[−0.055, 0.024] / [−0.002, 0.001] / [−0.033, −0.009]; no CI
lower bound clears 0. See #594.

## v1 reference (T1/T2 triage, 41 cells, month = 14 sessions)

Ensemble MAE 3.56 / 9.15 / 19.2; RangeSkill −1.06 / −1.59 / −2.48;
zero-move MAE 1.80 / 4.50 / 6.85. The month=21 re-score changes
almost nothing: the ~3 pp of the old month error that was the
scoring mismatch is gone, and the decay is still there — this
confirms the decay is real, not a scoring artifact.

## Gaps recorded by the scorer (198)

Every v1 capture lacks `sigma60_daily` (naive-range falls back to
`sigma_daily` as proxy) and `tilt_centre_pct` (`tilt-technicals` has
zero rows on the 36 v1 cells — the tilt is a v2-only entrant). EGX
captures have no index leg (`^EGX30` 404s on Yahoo; the EW-proxy
index leg per #436 T6 is still open). The tilt gap wording changed
with the #689 scorer hardening ("no usable tilt_centre_pct —
horizon skipped") — the scores are unchanged (all 1008 old rows
reproduce exactly). See `backtest.json` `gaps`.
