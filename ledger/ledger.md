# 🐊 Borsagator — calibration ledger (v1)

Source: `moos-labs/borsagator` branch `archive` (tree 23651cbc). Sweeps archived: 24 (9 with an ensemble).

**Forecasts found: 27 · matured: 4 · pending: 23 · dividend-adjusted: 0**

## By ticker

| Ticker | Found | Matured | Pending | Series span |
|---|---|---|---|---|
| COMI.CA | 3 | 0 | 3 | 2014-06-05 → 2026-11-15 |
| NVDA | 6 | 0 | 6 | 2025-11-14 → 2026-11-12 |
| POUL.CA | 18 | 4 | 14 | 2014-06-03 → 2026-11-15 |

## By horizon (matured only)

| Horizon | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| day | 4 | 0.0 | 2.11 | 1.0 |
| week | 0 | — | — | — |
| month | 0 | — | — | — |

## Family skill (mean of family_score × sign(realized), matured only)

| Family | Mean skill | n |
|---|---|---|
| agent | +0.750 | 1 |
| ensemble (net_score) | -0.121 | 4 |
| price-forecast | -0.021 | 4 |
| sentiment | -0.049 | 4 |
| technicals | -0.297 | 4 |

## Forecasts

| Ticker | As of | Horizon | Dir | Expected % | Realized % | Hit | |Err| pp | In range | Adj | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| POUL.CA | 2026-11-12 | day | flat | +0.53 | -1.96 | ❌ | 2.49 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-12 | week | flat | -0.40 | — | — | — | — | | pending (1/5 sessions) |
| POUL.CA | 2026-11-12 | month | down | -5.98 | — | — | — | — | | pending (1/14 sessions) |
| NVDA | 2026-11-12 | day | flat | -0.54 | — | — | — | — | | pending (0/1 sessions) |
| NVDA | 2026-11-12 | week | up | +8.07 | — | — | — | — | | pending (0/5 sessions) |
| NVDA | 2026-11-12 | month | up | +17.76 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.23 | -1.96 | ❌ | 1.73 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.14 | — | — | — | — | | pending (1/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -6.46 | — | — | — | — | | pending (1/14 sessions) |
| NVDA | 2026-11-13 | day | flat | -0.71 | — | — | — | — | | pending (0/1 sessions) |
| NVDA | 2026-11-13 | week | up | +6.93 | — | — | — | — | | pending (0/5 sessions) |
| NVDA | 2026-11-13 | month | up | +18.61 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.38 | -1.96 | ❌ | 1.58 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.67 | — | — | — | — | | pending (1/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -6.93 | — | — | — | — | | pending (1/14 sessions) |
| POUL.CA | 2026-11-13 | day | up | +1.16 | -1.48 | ❌ | 2.64 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.01 | — | — | — | — | | pending (1/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -1.76 | — | — | — | — | | pending (1/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.22 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-15 | week | down | -0.92 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-15 | month | down | -1.88 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.22 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-15 | week | down | -0.93 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-15 | month | down | -1.89 | — | — | — | — | | pending (0/14 sessions) |
| COMI.CA | 2026-11-15 | day | up | +702.27 | — | — | — | — | | pending (0/1 sessions) |
| COMI.CA | 2026-11-15 | week | up | +711.50 | — | — | — | — | | pending (0/4 sessions) |
| COMI.CA | 2026-11-15 | month | up | +674.99 | — | — | — | — | | pending (0/15 sessions) |

## Data gaps & notes

- 15 sweep(s) carry no ensemble.json (category/single-tool runs): sweeps/2026-11-12/053914__backfill-issue-7__sweep-poul-ca; sweeps/2026-11-12/153612__backfill-issue-13__sweep-lite-poul-ca-market-egx; sweeps/2026-11-13/070542__run-news-disclosure-poul-ca__run43382934691; sweeps/2026-11-13/105352__category-agent-poul-ca__run43411434864; sweeps/2026-11-13/112806__category-agent-poul-ca__run43414990698; sweeps/2026-11-13/123153__category-news-poul-ca__run43425457246; sweeps/2026-11-13/141636__category-news-poul-ca__run43440228991; sweeps/2026-11-13/171214__category-news-poul-ca__run43469687667; sweeps/2026-11-13/175202__category-news-poul-ca__run43475305450; sweeps/2026-11-13/181309__run-financetoolkit-comi-ca__run43480301234; sweeps/2026-11-13/181720__run-financetoolkit-poul-ca__run43481004601; sweeps/2026-11-13/184846__category-agent-poul-ca__run43482153785; sweeps/2026-11-14/085808__run-egx-data-poul-ca__run43578206341; sweeps/2026-11-15/130920__run-kronos-nvda__run43717394637; sweeps/2026-11-15/131641__category-news-poul-ca__run43717400241
- COMI.CA: actuals series has 3000 sessions, 2014-06-05 → 2026-11-15 (last source: sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248/collected/egx-data/egxpy_poul.csv)
- NVDA: actuals series has 250 sessions, 2025-11-14 → 2026-11-12 (last source: sweeps/2026-11-13/063412__backfill-issue-18__sweep-lite-nvda-market-us/collected/pandas-ta/indicators.csv)
- POUL.CA: actuals series has 3002 sessions, 2014-06-03 → 2026-11-15 (last source: sweeps/2026-11-15/132459__sweep-lite-poul-ca-market-egx__run43717383224/collected/egx-data/egxpy_poul.csv)
- no archived ensemble carries a corporate_actions block yet (the first post-#26 sweep has not run) — the dividend-adjustment path is implemented and covered by a synthetic check, with zero real adjusted rows so far

_Skill is provisional until a meaningful number of forecasts have matured; a family is only as good as its measured record._
