# 🐊 Borsagator — calibration ledger (v1)

Source: `moos-labs/borsagator` branch `archive` (tree 43eb07c0, commit 43eb07c0). Sweeps archived: 46 (25 with an ensemble).

**Forecasts found: 69 · matured: 22 · pending: 41 · invalid: 6 · dividend-adjusted: 4 · excluded from skill: 8 gap-flagged row(s) (issue #79)**

## By ticker

| Ticker | Found | Matured | Pending | Invalid | Series span |
|---|---|---|---|---|---|
| COMI.CA | 3 | 0 | 0 | 3 | 2018-01-01 → 2026-11-12 |
| NVDA | 6 | 1 | 5 | 0 | 2021-11-15 → 2026-11-13 |
| POUL.CA | 60 | 21 | 36 | 3 | 2014-06-04 → 2026-11-18 |

## By horizon (matured only, gap-flagged rows excluded from skill — issue #79)

| Horizon | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| day | 14 | 0.0 | 11.36 | 0.429 |
| week | 0 | — | — | — |
| month | 0 | — | — | — |

## Family skill (mean of family_score × sign(realized), matured only)

| Family | Mean skill | n |
|---|---|---|
| agent | +0.750 | 1 |
| ensemble (net_score) | -0.254 | 14 |
| price-forecast | -0.497 | 13 |
| sentiment | +0.069 | 14 |
| technicals | -0.283 | 14 |

## Forecasts

| Ticker | As of | Horizon | Dir | Expected % | Realized % | Hit | |Err| pp | In range | Adj | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| POUL.CA | 2026-11-12 | day | flat | +0.53 | -1.96 | ❌ | 2.49 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-12 | week | flat | -0.40 | — | — | — | — | | pending (4/5 sessions) |
| POUL.CA | 2026-11-12 | month | down | -5.98 | — | — | — | — | | pending (4/14 sessions) |
| NVDA | 2026-11-12 | day | flat | -0.54 | -0.82 | ❌ | 0.28 | ✅ |  | matured 2026-11-13 |
| NVDA | 2026-11-12 | week | up | +8.07 | — | — | — | — | | pending (1/5 sessions) |
| NVDA | 2026-11-12 | month | up | +17.76 | — | — | — | — | | pending (1/14 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.23 | -1.96 | ❌ | 1.73 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.14 | — | — | — | — | | pending (4/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -6.46 | — | — | — | — | | pending (4/14 sessions) |
| NVDA | 2026-11-13 | day | flat | -0.71 | — | — | — | — | | pending (0/1 sessions) |
| NVDA | 2026-11-13 | week | up | +6.93 | — | — | — | — | | pending (0/5 sessions) |
| NVDA | 2026-11-13 | month | up | +18.61 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.38 | -1.96 | ❌ | 1.58 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.67 | — | — | — | — | | pending (4/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -6.93 | — | — | — | — | | pending (4/14 sessions) |
| POUL.CA | 2026-11-13 | day | up | +1.16 | -1.48 | ❌ | 2.64 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.01 | — | — | — | — | | pending (4/5 sessions) |
| POUL.CA | 2026-11-13 | month | down | -1.76 | — | — | — | — | | pending (4/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.22 | -20.99 | ❌ | 22.21 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -0.92 | -24.14 | ✅ | 23.22 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.88 | — | — | — | — | | pending (3/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.22 | -20.99 | ❌ | 22.21 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -0.93 | -24.14 | ✅ | 23.21 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.89 | — | — | — | — | | pending (3/14 sessions) |
| COMI.CA | 2026-11-15 | day | up | +702.27 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| COMI.CA | 2026-11-15 | week | up | +711.50 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| COMI.CA | 2026-11-15 | month | up | +674.99 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| POUL.CA | 2026-11-15 | day | up | +1.21 | -20.99 | ❌ | 22.20 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -1.00 | -24.14 | ✅ | 23.14 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.91 | — | — | — | — | | pending (3/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.21 | -20.99 | ❌ | 22.20 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -1.00 | -24.14 | ✅ | 23.14 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.91 | — | — | — | — | | pending (3/14 sessions) |
| POUL.CA | 2026-11-16 | day | flat | +0.19 | -5.30 | ❌ | 5.49 | ❌ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | +0.26 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | up | +1.39 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +2.26 | -5.30 | ❌ | 7.56 | ❌ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | -0.61 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | down | -1.54 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +2.25 | -5.30 | ❌ | 7.55 | ❌ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | -0.63 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | down | -1.55 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.71 | -5.61 | ❌ | 24.32 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.73 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | up | +16.36 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.62 | -5.61 | ❌ | 24.23 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.55 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | up | +16.34 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.61 | -5.61 | ❌ | 24.22 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.54 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | up | +16.33 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +1.90 | -6.70 | ❌ | 8.60 | ✅ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | -0.61 | — | — | — | — | | pending (2/4 sessions) |
| POUL.CA | 2026-11-16 | month | up | +4.77 | — | — | — | — | | pending (2/15 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.52 | -5.61 | ❌ | 24.13 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.35 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | up | +16.21 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.63 | -5.61 | ❌ | 24.24 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.58 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-16 | month | up | +16.36 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-17 | day | up | +18.43 | — | — | — | — | | invalid — base_price 8.02 deviates 5.9% from the ticker-evidenced close 7.57 at 2026-11-17 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-17 | week | up | +16.17 | — | — | — | — | | invalid — base_price 8.02 deviates 5.9% from the ticker-evidenced close 7.57 at 2026-11-17 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-17 | month | up | +16.08 | — | — | — | — | | invalid — base_price 8.02 deviates 5.9% from the ticker-evidenced close 7.57 at 2026-11-17 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-18 | day | up | +7.68 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-18 | week | up | +15.28 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-18 | month | up | +17.56 | — | — | — | — | | pending (0/14 sessions) |
| POUL.CA | 2026-11-18 | day | up | +7.08 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-18 | week | up | +14.61 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-18 | month | up | +16.94 | — | — | — | — | | pending (0/14 sessions) |

## Data gaps & notes

- 21 sweep(s) carry no ensemble.json (category/single-tool runs): sweeps/2026-11-12/053914__backfill-issue-7__sweep-poul-ca; sweeps/2026-11-12/153612__backfill-issue-13__sweep-lite-poul-ca-market-egx; sweeps/2026-11-13/070542__run-news-disclosure-poul-ca__run43382934691; sweeps/2026-11-13/105352__category-agent-poul-ca__run43411434864; sweeps/2026-11-13/112806__category-agent-poul-ca__run43414990698; sweeps/2026-11-13/123153__category-news-poul-ca__run43425457246; sweeps/2026-11-13/141636__category-news-poul-ca__run43440228991; sweeps/2026-11-13/171214__category-news-poul-ca__run43469687667; sweeps/2026-11-13/175202__category-news-poul-ca__run43475305450; sweeps/2026-11-13/181309__run-financetoolkit-comi-ca__run43480301234; sweeps/2026-11-13/181720__run-financetoolkit-poul-ca__run43481004601; sweeps/2026-11-13/184846__category-agent-poul-ca__run43482153785; sweeps/2026-11-14/085808__run-egx-data-poul-ca__run43578206341; sweeps/2026-11-15/130920__run-kronos-nvda__run43717394637; sweeps/2026-11-15/131641__category-news-poul-ca__run43717400241; sweeps/2026-11-15/134248__category-agent-poul-ca__run43717405249; sweeps/2026-11-15/140746__sweep-nvda__run43717388468; sweeps/2026-11-16/040734__run-egx-data-comi-ca__run43801992894; sweeps/2026-11-16/041112__category-news-poul-ca__run43801982888; sweeps/2026-11-16/041429__run-talib-comi-ca__run43802798857; sweeps/2026-11-16/042354__category-news-poul-ca__run43802770319
- COMI.CA: actuals series has 2180 sessions, 2018-01-01 → 2026-11-12 (last source: sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248/collected/quantstats/ohlc.csv)
- NVDA: actuals series has 1255 sessions, 2021-11-15 → 2026-11-13 (last source: sweeps/2026-11-16/041633__run-openbb-nvda__run43802957047/collected/openbb/NVDA.csv)
- POUL.CA: actuals series has 3048 sessions, 2014-06-04 → 2026-11-18 (last source: sweeps/2026-11-18/140522__sweep-poul-ca-market-egx__runmanual-sweep-2026-11-18-001/collected/egx-data/egxpy_poul.csv)
- price-CSV parsing skipped 8 malformed/non-positive row(s) across all candidate files
- 6 forecast(s) invalidated by the issue-#87 guard (base_price inconsistent with the ticker-evidenced price level; never scored): COMI.CA as of 2026-11-15 (day) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; COMI.CA as of 2026-11-15 (week) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; COMI.CA as of 2026-11-15 (month) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; POUL.CA as of 2026-11-17 (day) from sweeps/2026-11-16/225700__sweep-lite-poul-ca__run43967492548; POUL.CA as of 2026-11-17 (week) from sweeps/2026-11-16/225700__sweep-lite-poul-ca__run43967492548; POUL.CA as of 2026-11-17 (month) from sweeps/2026-11-16/225700__sweep-lite-poul-ca__run43967492548
- 8 matured forecast(s) span a known dividend ex-date (or carry an undated dividend action) but were NOT dividend-adjusted — their realized move includes the mechanical ex-div drop (issue #129): POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/074752__sweep-lite-poul-ca__run43688673389: 1 undated dividend action(s) (DPS 1.9) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/074752__sweep-lite-poul-ca__run43688673389: 1 undated dividend action(s) (DPS 1.9) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/132459__sweep-lite-poul-ca-market-egx__run43717383224: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/132459__sweep-lite-poul-ca-market-egx__run43717383224: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/140509__sweep-lite-poul-ca-market-egx__run43720903619: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/140509__sweep-lite-poul-ca-market-egx__run43720903619: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/141558__sweep-lite-poul-ca-market-egx__run43721738392: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/141558__sweep-lite-poul-ca-market-egx__run43721738392: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129)
- 8 gap-flagged matured forecast(s) excluded from skill/weights/aggregates (issue #79): the rows stay listed with their dividend_gap flag — only the means exclude them; the published weights change on the next publish is the intended correction, announced at the #79 landing

_Skill is provisional until a meaningful number of forecasts have matured; a family is only as good as its measured record._
