# 🐊 Borsagator — calibration ledger (v1)

Source: `moos-labs/borsagator` branch `archive` (tree 4475c544). Sweeps archived: 14 (6 with an ensemble).

**Forecasts found: 18 · matured: 0 · pending: 18 · dividend-adjusted: 0**

## By ticker

| Ticker | Found | Matured | Pending | Series span |
|---|---|---|---|---|
| NVDA | 6 | 0 | 6 | 2025-11-14 → 2026-11-12 |
| POUL.CA | 12 | 0 | 12 | 2014-06-03 → 2026-11-12 |

## By horizon (matured only)

| Horizon | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| day | 0 | — | — | — |
| week | 0 | — | — | — |
| month | 0 | — | — | — |

## Family skill (mean of family_score × sign(realized), matured only)

| Family | Mean skill | n |
|---|---|---|
| — | no matured forecasts yet | 0 |

## Forecasts

| Ticker | As of | Horizon | Dir | Expected % | Realized % | Hit | |Err| pp | In range | Adj | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| POUL.CA | 2026-11-12 | day | flat | +0.53 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-12 | week | flat | -0.40 | — | — | — | — | | pending (0/5 sessions) |
| POUL.CA | 2026-11-12 | month | down | -5.98 | — | — | — | — | | pending (0/14 sessions) |
| NVDA | 2026-11-12 | day | flat | -0.54 | — | — | — | — | | pending (0/1 sessions) |
| NVDA | 2026-11-12 | week | up | +8.07 | — | — | — | — | | pending (0/5 sessions) |
| NVDA | 2026-11-12 | month | up | +17.76 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.23 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-13 | week | down | -1.14 | — | — | — | — | | pending (0/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -6.46 | — | — | — | — | | pending (0/14 sessions) |
| NVDA | 2026-11-13 | day | flat | -0.71 | — | — | — | — | | pending (0/1 sessions) |
| NVDA | 2026-11-13 | week | up | +6.93 | — | — | — | — | | pending (0/5 sessions) |
| NVDA | 2026-11-13 | month | up | +18.61 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.38 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-13 | week | down | -1.67 | — | — | — | — | | pending (0/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -6.93 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-13 | day | up | +1.16 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-13 | week | down | -1.01 | — | — | — | — | | pending (0/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -1.76 | — | — | — | — | | pending (0/14 sessions) |

## Data gaps & notes

- 8 sweep(s) carry no ensemble.json (category/single-tool runs): sweeps/2026-11-12/053914__backfill-issue-7__sweep-poul-ca; sweeps/2026-11-12/153612__backfill-issue-13__sweep-lite-poul-ca-market-egx; sweeps/2026-11-13/070542__run-news-disclosure-poul-ca__run43382934691; sweeps/2026-11-13/105352__category-agent-poul-ca__run43411434864; sweeps/2026-11-13/112806__category-agent-poul-ca__run43414990698; sweeps/2026-11-13/123153__category-news-poul-ca__run43425457246; sweeps/2026-11-13/141636__category-news-poul-ca__run43440228991; sweeps/2026-11-13/171214__category-news-poul-ca__run43469687667
- NVDA: actuals series has 250 sessions, 2025-11-14 → 2026-11-12 (last source: sweeps/2026-11-13/063412__backfill-issue-18__sweep-lite-nvda-market-us/collected/pandas-ta/indicators.csv)
- POUL.CA: actuals series has 3001 sessions, 2014-06-03 → 2026-11-12 (last source: sweeps/2026-11-13/095050__sweep-lite-poul-ca-market-egx__run43402572619/collected/egx-data/egxpy_poul.csv)
- no archived ensemble carries a corporate_actions block yet (the first post-#26 sweep has not run) — the dividend-adjustment path is implemented and covered by a synthetic check, with zero real adjusted rows so far
- no forecast has matured yet: every archived price series ends 2026-11-12, so even the earliest forecasts (as of 2026-11-12) have zero sessions after their date in the archive; later sweeps will extend the series and mature them

_Skill is provisional until a meaningful number of forecasts have matured; a family is only as good as its measured record._
