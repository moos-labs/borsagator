# 🐊 Borsagator — calibration ledger (v1)

Source: `moos-labs/borsagator` branch `archive` (tree 59fca428). Sweeps archived: 37 (16 with an ensemble).

**Forecasts found: 42 · matured: 5 · pending: 34 · invalid: 3 · dividend-adjusted: 0**

## By ticker

| Ticker | Found | Matured | Pending | Invalid | Series span |
|---|---|---|---|---|---|
| COMI.CA | 3 | 0 | 0 | 3 | 2018-01-01 → 2026-11-12 |
| NVDA | 6 | 1 | 5 | 0 | 2021-11-15 → 2026-11-13 |
| POUL.CA | 33 | 4 | 29 | 0 | 2014-06-04 → 2026-11-15 |

## By horizon (matured only)

| Horizon | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| day | 5 | 0.0 | 1.74 | 1.0 |
| week | 0 | — | — | — |
| month | 0 | — | — | — |

## Family skill (mean of family_score × sign(realized), matured only)

| Family | Mean skill | n |
|---|---|---|
| agent | +0.750 | 1 |
| ensemble (net_score) | -0.089 | 5 |
| price-forecast | -0.007 | 5 |
| sentiment | +0.024 | 5 |
| technicals | -0.258 | 5 |

## Forecasts

| Ticker | As of | Horizon | Dir | Expected % | Realized % | Hit | |Err| pp | In range | Adj | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| POUL.CA | 2026-11-12 | day | flat | +0.53 | -1.96 | ❌ | 2.49 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-12 | week | flat | -0.40 | — | — | — | — | | pending (1/5 sessions) |
| POUL.CA | 2026-11-12 | month | down | -5.98 | — | — | — | — | | pending (1/14 sessions) |
| NVDA | 2026-11-12 | day | flat | -0.54 | -0.82 | ❌ | 0.28 | ✅ |  | matured 2026-11-13 |
| NVDA | 2026-11-12 | week | up | +8.07 | — | — | — | — | | pending (1/5 sessions) |
| NVDA | 2026-11-12 | month | up | +17.76 | — | — | — | — | | pending (1/14 sessions) |
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
| COMI.CA | 2026-11-15 | day | up | +702.27 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| COMI.CA | 2026-11-15 | week | up | +711.50 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| COMI.CA | 2026-11-15 | month | up | +674.99 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| POUL.CA | 2026-11-15 | day | up | +1.21 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-15 | week | down | -1.00 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-15 | month | down | -1.91 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.21 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-15 | week | down | -1.00 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-15 | month | down | -1.91 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-16 | day | flat | +0.19 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-16 | week | flat | +0.26 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-16 | month | up | +1.39 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +2.26 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-16 | week | flat | -0.61 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-16 | month | down | -1.54 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +2.25 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-16 | week | flat | -0.63 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-16 | month | down | -1.55 | — | — | — | — | | pending (0/14 sessions) |

## Data gaps & notes

- 21 sweep(s) carry no ensemble.json (category/single-tool runs): sweeps/2026-11-12/053914__backfill-issue-7__sweep-poul-ca; sweeps/2026-11-12/153612__backfill-issue-13__sweep-lite-poul-ca-market-egx; sweeps/2026-11-13/070542__run-news-disclosure-poul-ca__run43382934691; sweeps/2026-11-13/105352__category-agent-poul-ca__run43411434864; sweeps/2026-11-13/112806__category-agent-poul-ca__run43414990698; sweeps/2026-11-13/123153__category-news-poul-ca__run43425457246; sweeps/2026-11-13/141636__category-news-poul-ca__run43440228991; sweeps/2026-11-13/171214__category-news-poul-ca__run43469687667; sweeps/2026-11-13/175202__category-news-poul-ca__run43475305450; sweeps/2026-11-13/181309__run-financetoolkit-comi-ca__run43480301234; sweeps/2026-11-13/181720__run-financetoolkit-poul-ca__run43481004601; sweeps/2026-11-13/184846__category-agent-poul-ca__run43482153785; sweeps/2026-11-14/085808__run-egx-data-poul-ca__run43578206341; sweeps/2026-11-15/130920__run-kronos-nvda__run43717394637; sweeps/2026-11-15/131641__category-news-poul-ca__run43717400241; sweeps/2026-11-15/134248__category-agent-poul-ca__run43717405249; sweeps/2026-11-15/140746__sweep-nvda__run43717388468; sweeps/2026-11-16/040734__run-egx-data-comi-ca__run43801992894; sweeps/2026-11-16/041112__category-news-poul-ca__run43801982888; sweeps/2026-11-16/041429__run-talib-comi-ca__run43802798857; sweeps/2026-11-16/042354__category-news-poul-ca__run43802770319
- COMI.CA: actuals series has 2180 sessions, 2018-01-01 → 2026-11-12 (last source: sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248/collected/quantstats/ohlc.csv)
- NVDA: actuals series has 1255 sessions, 2021-11-15 → 2026-11-13 (last source: sweeps/2026-11-16/041633__run-openbb-nvda__run43802957047/collected/openbb/NVDA.csv)
- POUL.CA: actuals series has 3001 sessions, 2014-06-04 → 2026-11-15 (last source: sweeps/2026-11-16/085806__sweep-lite-poul-ca__run43829283730/collected/egx-data/egxpy_poul.csv)
- price-CSV parsing skipped 1 malformed/non-positive row(s) across all candidate files
- 3 forecast(s) invalidated by the issue-#87 guard (base_price inconsistent with the ticker-evidenced price level; never scored): COMI.CA as of 2026-11-15 (day) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; COMI.CA as of 2026-11-15 (week) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; COMI.CA as of 2026-11-15 (month) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248

_Skill is provisional until a meaningful number of forecasts have matured; a family is only as good as its measured record._
