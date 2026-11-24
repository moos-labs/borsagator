# Forward quality benchmark — ensemble vs baselines (issue #79)

Computed from `ledger/ledger.json` (every matured forecast row: 45) and the point-in-time sweep archive. Generator: `benchmarks/score_forward_benchmark.py`; scoring is ledger.py's own machinery (direction with the ±0.75% flat band, move error in percentage points, realised moves dividend-adjusted where the ledger adjusted them).

Headline tables EXCLUDE the 12 gap-flagged matured rows (decision D-79-1: flagged rows stay listed and counted, never in aggregates). All-matured tables are in the appendix. Quality gate: no quality claim for any (entrant, horizon) cell with n < 10 matured forecasts; public accuracy claims need n ≥ 30 (D4). Cells below the gate print their numbers for the record, marked †.

Entrants: **ensemble** (the ledger row as published); **naive-flat** (predicted move 0.00%); **momentum** (the realised move over the s sessions ending at as_of, continued for the next s sessions); **family-\*** (each voting family standalone, definition (a): combine re-run with that family's weight 1, kmove zeroed for non-price families, Kronos kmove for price-forecast).

# Headline (gap-flagged rows excluded)

## day

| Entrant | n | Direction hit rate | Mean abs. error (pp) |
|---|---|---|---|
| ensemble | 20 | 0.000 | 11.20 |
| naive-flat | 20 | 0.000 | 4.08 |
| momentum | 20 | 0.600 | 8.15 |
| family-price-forecast | 19 | 0.000 | 12.38 |
| family-technicals | 20 | 0.000 | 5.02 |
| family-sentiment | 20 | 0.050 | 3.87 |
| family-agent | 1 † | 1.000 | 1.10 |
| family-fundamentals | 17 | 0.000 | 5.77 |

## week

| Entrant | n | Direction hit rate | Mean abs. error (pp) |
|---|---|---|---|
| ensemble | 13 | 0.000 | 17.26 |
| naive-flat | 13 | 0.000 | 6.58 |
| momentum | 13 | 1.000 | 15.35 |
| family-price-forecast | 12 | 0.250 | 20.44 |
| family-technicals | 13 | 0.000 | 8.55 |
| family-sentiment | 13 | 0.154 | 6.07 |
| family-agent | 0 | — | — |
| family-fundamentals | 13 | 0.000 | 8.98 |

## month

| Entrant | n | Direction hit rate | Mean abs. error (pp) |
|---|---|---|---|
| ensemble | 0 | — | — |
| naive-flat | 0 | — | — |
| momentum | 0 | — | — |
| family-price-forecast | 0 | — | — |
| family-technicals | 0 | — | — |
| family-sentiment | 0 | — | — |
| family-agent | 0 | — | — |
| family-fundamentals | 0 | — | — |

## Reading (gated cells only, n ≥ 10)

- **day**: the ensemble (hit 0.000, MAE 11.20 pp) ranks 6 of 7 gated entrants on MAE. Best MAE: family-sentiment (3.87 pp). Best hit rate: momentum (0.600). The ensemble does not beat the naive baselines on this horizon — on either metric.
- **week**: the ensemble (hit 0.000, MAE 17.26 pp) ranks 6 of 7 gated entrants on MAE. Best MAE: family-sentiment (6.07 pp). Best hit rate: momentum (1.000). The ensemble does not beat the naive baselines on this horizon — on either metric.
- The sample is one ticker (POUL.CA, 44 of 45 matured rows) plus one NVDA row, all from 2026-11-12 to 2026-11-19 — a window dominated by POUL's 1.90 EGP ex-dividend drop. These are the ledger's real numbers, published as scored; they are not yet evidence about any other ticker or regime.

# Appendix — all matured rows (gap-flagged included)

## day

| Entrant | n | Direction hit rate | Mean abs. error (pp) |
|---|---|---|---|
| ensemble | 24 | 0.000 | 13.03 |
| naive-flat | 24 | 0.000 | 6.90 |
| momentum | 24 | 0.667 | 10.05 |
| family-price-forecast | 23 | 0.000 | 14.10 |
| family-technicals | 24 | 0.000 | 7.74 |
| family-sentiment | 24 | 0.042 | 6.72 |
| family-agent | 1 † | 1.000 | 1.10 |
| family-fundamentals | 21 | 0.000 | 8.76 |

## week

| Entrant | n | Direction hit rate | Mean abs. error (pp) |
|---|---|---|---|
| ensemble | 21 | 0.333 | 19.77 |
| naive-flat | 21 | 0.000 | 13.55 |
| momentum | 21 | 0.810 | 18.49 |
| family-price-forecast | 20 | 0.550 | 21.63 |
| family-technicals | 21 | 0.000 | 15.01 |
| family-sentiment | 21 | 0.095 | 13.26 |
| family-agent | 1 † | 1.000 | 23.96 |
| family-fundamentals | 19 | 0.000 | 14.18 |

## month

| Entrant | n | Direction hit rate | Mean abs. error (pp) |
|---|---|---|---|
| ensemble | 0 | — | — |
| naive-flat | 0 | — | — |
| momentum | 0 | — | — |
| family-price-forecast | 0 | — | — |
| family-technicals | 0 | — | — |
| family-sentiment | 0 | — | — |
| family-agent | 0 | — | — |
| family-fundamentals | 0 | — | — |

## Gaps & notes

- Matured rows scored: 45; gap-flagged and excluded from the headline: 12; headline rows: 33.
- Month horizon: no matured forecasts yet (n=0 for every entrant) — nothing to score, nothing claimed.
- Momentum: computable on every matured row. The anchor is the last series close on or before as_of (three sweeps ran on Friday 2026-11-13, a non-trading day, on the 2026-11-12 close). The series close at each row's maturity reproduces the ledger's close_at_maturity within the 3% validation tolerance on all rows.
- On 8 row(s) the series close at the anchor differs from the sweep's recorded base_price by more than 3% — the 2026-11-16 ex-date rows, whose base was recorded cum-dividend while the exchange series is ex-dividend. Momentum is a return computed inside one series, so it is still scored; its prior window spans the mechanical ex-date drop, which is exactly what a naive momentum baseline would have predicted from raw closes.
- sigma_daily is not recorded in the archived ensemble.json of `sweeps/2026-11-12/163459__backfill-issue-14__sweep-lite-poul-ca-market-egx`, `sweeps/2026-11-12/170500__backfill-issue-15__sweep-lite-nvda-market-us`; for those sweeps sigma was recomputed with the combine's own ensemble.realized_sigma over the sweep's collected pool (the same function ensemble.py calls at freeze time). Family-alone rows from all other sweeps use the recorded sigma_daily.
- Family-alone n counts only rows where the family actually voted (score present in the sweep's ensemble.json); agent and fundamentals vote rarely, so their n is small and gated.

## Cross-checks

- ensemble day reproduces ledger.json by_horizon: PASS (n=20, hit=0.000, MAE=11.20)
- ensemble week reproduces ledger.json by_horizon: PASS (n=13, hit=0.000, MAE=17.26)
- family-alone reconstruction vs the frozen benchmark (ledger/benchmark.json): 40/40 overlapping rows agree on hit and |error| (<=0.01 pp)
