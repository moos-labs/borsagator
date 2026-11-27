# Walk-forward backtest — v2 re-score for #592 (month = 21 sessions)

Published 2026-11-25, extended 2026-11-26 with batch-7 cells 48–50,
batch-8 cells 51–53, batch-9 cells 54–59, batch-10 cells 60–63,
batch-11 cells 64–67, batch-12 cells 68, 69, 71, 72, batch-13
cell 70 (TMGH.CA 2026-09-30, archive c0e7ebec) and batch-14
cells 73–78 (2026-08-14 × COMI/ETEL/TMGH/NVDA/SWDY/HRHO) and batch-15
cells 79–88 (2026-05-15 × COMI/ETEL/TMGH/NVDA/SWDY/HRHO and
2026-02-13 × COMI/ETEL/TMGH/NVDA) and batch-16 cells 89–90
(2026-02-13 × SWDY/HRHO, the batch-B remainder) and batch-17
cells 91–97 (2025-11-14 × COMI/ETEL/TMGH/NVDA/SWDY/HRHO and
2025-08-15 × COMI, the D/E batch) and batch-18 cells 98–102
(2025-08-15 × ETEL/TMGH/NVDA/SWDY/HRHO, the D/E batch remainder).
Cell 1 re-scored (r3, COMI.CA 2023-12-29, fixed Kronos pin 6964de99,
archive a62379f8). Cells 6, 7, 8, 20, 21 re-scored (REPAIR-001,
2024-03-31 × COMI/ETEL/TMGH/SWDY/HRHO: the 2024-05-01 close
repaired from verified TradingView closes in `scripts/backtest.py`
EGX_CLOSE_REPAIRS, sweep `repair001/`).
Scorer v2 (`scripts/backtest_score.py`, PR #665 plus the `agg()`
empty-subset fix in PR #677). Sessions day/week/month 1/5/21 per
`ledger.DEFAULT_SESSIONS`.

## Coverage

- **96 cells re-scored** (1659 forecasts, all matured):
  cells 1–47 except the 6 below, plus repair-001 cells 6 (COMI.CA
  2024-03-31), 7 (ETEL.CA 2024-03-31), 8 (TMGH.CA 2024-03-31),
  20 (SWDY.CA 2024-03-31) and 21 (HRHO.CA 2024-03-31), plus batch-7 cells 48 (SWDY.CA
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
  2026-08-14) and 78 (HRHO.CA 2026-08-14), and batch-15 cells 79
  (COMI.CA 2026-05-15), 80 (ETEL.CA 2026-05-15), 81 (TMGH.CA
  2026-05-15), 82 (NVDA 2026-05-15), 83 (SWDY.CA 2026-05-15),
  84 (HRHO.CA 2026-05-15), 85 (COMI.CA 2026-02-13), 86 (ETEL.CA
  2026-02-13), 87 (TMGH.CA 2026-02-13) and 88 (NVDA 2026-02-13), and batch-16 cells 89
  (SWDY.CA 2026-02-13) and 90 (HRHO.CA 2026-02-13), and batch-17 cells 91
  (COMI.CA 2025-11-14), 92 (ETEL.CA 2025-11-14), 93 (TMGH.CA 2025-11-14),
  94 (NVDA 2025-11-14), 95 (SWDY.CA 2025-11-14), 96 (HRHO.CA 2025-11-14)
  and 97 (COMI.CA 2025-08-15), and batch-18 cells 98
  (ETEL.CA 2025-08-15), 99 (TMGH.CA 2025-08-15), 100 (NVDA
  2025-08-15), 101 (SWDY.CA 2025-08-15) and 102 (HRHO.CA
  2025-08-15).
  Per-cell files: `cells/cellNN_score_v2.json`.
- **Cells 6, 7, 8, 20, 21 RESOLVED by REPAIR-001** — they were
  v1-scored only (month at 14 sessions) because the 21-session
  realised window fail-closed on 2024-05-01, which has no usable
  Yahoo close. 2024-05-01 was a trading session, so the harness
  now repairs the close from verified TradingView closes
  (`EGX_CLOSE_REPAIRS` in `scripts/backtest.py`: COMI 73.01,
  ETEL 33.00, TMGH 55.060001, SWDY 32.50, HRHO 15.14; raw closes,
  basis per ticker). The five cells are now in the grid at month
  = 21 sessions (maturity 2024-05-08); their day/week rows are
  identical to the v1 scoring except `sessions_available` 14 → 21.
  The repair cells alone: ensemble month MAE 0.23 / 8.40 / 59.13 /
  16.17 / 19.71 pp (cells 6/7/8/20/21) — cell 8 (TMGH.CA) is a
  genuine forecast miss, not a scoring artifact: the ensemble
  expected −57.75% (Kronos −79.25%) against a realised +1.38%.
- **6 cells have no captures at all** (gate-skipped worker runs, never
  scored): cells 3 (ORAS.CA 2023-12-29, stale-flat), 10, 11, 12, 22, 23
  (whole 2024-06-30 cutoff — the 2024-07-01 gap). REPAIR-002
  (PR pending, #436): the 2024-07-01 closes are verified (EGX30
  printed 27,969.59, +0.73%; Mubasher chartData: COMI 78.02 on the
  Yahoo basis, ETEL 30.99, TMGH 57.12, SWDY 47.63, HRHO 19.38)
  and the repair table now covers the date — the five cells await
  re-dispatch to the worker once the repair reaches worker-release
  (promotion, then `run backtest 2024-06-30 <ticker>`).

## Headline (96 cells, month = 21)

| Entrant | Day MAE / RangeSkill | Week MAE / RangeSkill | Month MAE / RangeSkill |
|---|---|---|---|
| 2-family-ensemble | 2.55 / −0.101 | 5.58 / −0.655 | 12.95 / −0.704 |
| kronos-alone | 2.93 / −0.336 | 8.06 / −2.169 | 21.12 / −3.815 |
| family-technicals | 2.23 / −0.029 | 4.02 / −0.004 | 8.45 / −0.011 |
| naive-range (gate) | 2.13 / 0.000 | 3.94 / 0.000 | 8.37 / 0.000 |

Flat zero-move (buy-and-hold) MAE: 2.13 / 3.94 / 8.37. The ensemble
fails the RangeSkill gate at every horizon; Kronos month MAE 21.12 pp
vs zero-move 8.37 pp, direction hit 36.5%. The batch-7 cells alone:
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
construction, not a scorer fault. The batch-15 cells alone
(2026-05-15 × six, 2026-02-13 × four): ensemble month MAE 1.63 /
3.72 / 1.94 / 7.95 / 2.82 / 3.29 / 13.83 / 13.05 / 13.69 / 0.48 pp
(cells 79/80/81/82/83/84/85/86/87/88), RangeSkill +0.063 / +0.063 /
+0.062 / +0.064 / +0.063 / +0.064 / −0.186 / +0.064 / −0.137 /
+0.064; Kronos month on the batch-15 cells: 21.33 / 32.39 / 34.57 /
8.61 / 9.69 / 4.22 / 22.96 / 45.79 / 11.81 / 0.53 pp — still far
worse than zero-move on all ten cells, and worse than the ensemble
on all ten; Kronos month coverage is 0.000 on nine of the ten
(cell 88, NVDA, 1.000). The 2026-02-13 EGX month was a −13% to
−14% down month (COMI −13.83%, ETEL −13.05%, TMGH −13.69%); cells
85 and 87 cover 0.000. Ensemble month direction hit is 0.00 on
nine of the ten cells (1.00 on cell 88, NVDA −0.48%). The batch-16 cells alone
(2026-02-13 × SWDY/HRHO, the batch-B remainder): ensemble month MAE 0.28 /
15.55 pp (cells 89/90), RangeSkill +0.063 / −0.088; Kronos month on the
batch-16 cells: 1.41 / 8.90 pp — worse than the ensemble on cell 89, better
on cell 90 (direction hit 1.00 on the −15.55% down month, though its range
still covers 0.000). Cell 89 (SWDY.CA −0.28% realised month) is the second
near-zero month after cell 88; the ensemble covers it 1.000 with hit 1.00.
Cell 90 (HRHO.CA −15.55% realised month) covers 0.000 at the month horizon
on every entrant; ensemble month direction hit is 0.00. The batch-17 cells alone
(2025-11-14 × six, 2025-08-15 × COMI, the D/E batch): ensemble month MAE 2.39 /
17.86 / 3.60 / 6.55 / 5.04 / 8.18 / 0.37 pp (cells 91/92/93/94/95/96/97),
RangeSkill +0.065 / −0.058 / +0.065 / +0.062 / +0.066 / +0.061 / +0.061;
Kronos month on the batch-17 cells: 14.74 / 60.39 / 18.24 / 11.76 / 11.76 /
7.97 / 11.21 pp — worse than zero-move on six of the seven cells, better
than the ensemble only on cell 96 (HRHO, 7.97 vs 8.18 pp); Kronos month
coverage is 0.000 on all seven. Cell 97 (COMI.CA −0.37% realised month) is the
third near-zero month after cells 88 and 89; the ensemble covers it 1.000
with hit 1.00. Cell 92 (ETEL.CA +17.86% realised month) covers 0.000 at the
month horizon on every entrant; ensemble month direction hit is 0.00 on six
of the seven cells (1.00 on cell 97). Cell 94 (NVDA) carries 21 forecasts —
the only cell with an index-baseline leg, so it has seven entrants instead
of six. The batch-18 cells alone
(2025-08-15 × ETEL/TMGH/NVDA/SWDY/HRHO, the D/E batch remainder):
ensemble month MAE 6.02 / 2.38 / 3.09 / 7.81 / 5.74 pp (cells
98/99/100/101/102), RangeSkill +0.065 / +0.065 / +0.062 / −0.104 /
+0.064; Kronos month on the batch-18 cells: 25.99 / 6.56 / 30.85 /
16.18 / 1.62 pp — worse than zero-move on four of the five cells,
better than the ensemble only on cell 102 (HRHO, 1.62 vs 5.74 pp);
Kronos month coverage is 0.000 on four of the five cells (1.000 on
cell 102). Cell 101 (SWDY.CA −7.81% realised month) covers 0.000 at
the month horizon on the ensemble; the other four cells cover
1.000. Ensemble month direction hit is 0.00 on all five cells.
Cell 100 (NVDA) carries 21 forecasts — an index-baseline leg, so
it has seven entrants instead of six. Cell 1 re-scored (r3, COMI.CA
2023-12-29, realised month +20.78%): ensemble MAE 0.40 / 2.48 /
20.78 pp, RangeSkill +0.099 / −0.002 / −0.067; Kronos month 42.65 pp
(was 75.41 pp on the pre-cap pin 54de65a2) — still far worse than
zero-move; Kronos month coverage 0.000. The r2 cell-1 rows are
replaced: 15 rows out, 18 rows in (tilt-technicals now present);
grid stays 91 cells, 1581 → 1584 forecasts. Tilt sample 55 → 56.

## Tilt-technicals (n = 56 — adoption test decisive at n = 31, DO NOT ADOPT)

The fifty-six batch-7/8/9/10/11/12/13/14/15/16/17/18 captures are the first v2
captures, so they are the first cells with `tilt_centre_pct`:
tilt-technicals month MAE 8.97 pp, RangeSkill −0.036 (n = 56);
day −0.015, week −0.003. Coverage 0.696 / 0.786 / 0.661. The #594 adoption test at n = 31
(2026-11-26) is decisive: DO NOT ADOPT on all three horizons —
frozen v2 RangeSkill −0.023 / −0.001 / −0.022 with 95% CIs
[−0.055, 0.024] / [−0.002, 0.001] / [−0.033, −0.009]; no CI
lower bound clears 0. The seven batch-17 cells extended the tilt
sample to 50, the five batch-18 cells extend it to 55 and the cell-1
r3 re-score extends it to 56; an
adoption re-run on the larger n is the improvement loop's, not this
publish's. See #594.

## v1 reference (T1/T2 triage, 41 cells, month = 14 sessions)

Ensemble MAE 3.56 / 9.15 / 19.2; RangeSkill −1.06 / −1.59 / −2.48;
zero-move MAE 1.80 / 4.50 / 6.85. The month=21 re-score changes
almost nothing: the ~3 pp of the old month error that was the
scoring mismatch is gone, and the decay is still there — this
confirms the decay is real, not a scoring artifact.

## Gaps recorded by the scorer (214)

Every v1 capture lacks `sigma60_daily` (naive-range falls back to
`sigma_daily` as proxy) and `tilt_centre_pct` (`tilt-technicals` has
zero rows on the 36 v1 cells — the tilt is a v2-only entrant). EGX
captures have no index leg (`^EGX30` 404s on Yahoo; the EW-proxy
index leg per #436 T6 is still open). The tilt gap wording changed
with the #689 scorer hardening ("no usable tilt_centre_pct —
horizon skipped") — the scores are unchanged (all 1359 old rows
reproduce exactly). Cell 1's r3 re-score removes its 5 old gaps
(sigma60 proxy, 3 tilt skips, index leg) and adds 1 (index leg only).
See `backtest.json` `gaps`.
