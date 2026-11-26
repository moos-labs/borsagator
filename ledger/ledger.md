# 🐊 Borsagator — calibration ledger (v1)

Source: `moos-labs/borsagator` branch `archive` (tree 403677ae, commit 403677ae). Sweeps archived: 91 (70 with an ensemble).

**Forecasts found: 204 · matured: 48 · pending: 144 · invalid: 12 · dividend-adjusted: 8 · excluded from skill: 12 gap-flagged row(s) (issue #79)**

## By ticker

| Ticker | Found | Matured | Pending | Invalid | Series span |
|---|---|---|---|---|---|
| ACGC.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |
| ADIB.CA | 3 | 0 | 3 | 0 | 2014-07-15 → 2026-11-25 |
| AMOC.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |
| ARCC.CA | 3 | 0 | 3 | 0 | 2014-07-13 → 2026-11-25 |
| ATQA.CA | 3 | 0 | 3 | 0 | 2014-06-29 → 2026-11-25 |
| CIRA.CA | 3 | 0 | 3 | 0 | 2018-10-01 → 2026-11-25 |
| CLHO.CA | 3 | 0 | 3 | 0 | 2016-04-14 → 2026-11-25 |
| COMI.CA | 3 | 0 | 0 | 3 | 2018-01-01 → 2026-11-12 |
| EFID.CA | 3 | 0 | 3 | 0 | 2015-04-02 → 2026-11-25 |
| EFIH.CA | 3 | 0 | 3 | 0 | 2021-10-19 → 2026-11-25 |
| EGAL.CA | 3 | 0 | 3 | 0 | 2014-06-09 → 2026-11-25 |
| EGAS.CA | 3 | 0 | 3 | 0 | 2014-07-15 → 2026-11-25 |
| ETEL.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |
| ETRS.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |
| FAIT.CA | 3 | 0 | 3 | 0 | 2014-06-26 → 2026-11-25 |
| FAITA.CA | 3 | 0 | 3 | 0 | 2014-07-13 → 2026-11-25 |
| GOUR.CA | 3 | 0 | 3 | 0 | 2026-02-10 → 2026-11-25 |
| ICFC.CA | 3 | 0 | 3 | 0 | 2014-06-11 → 2026-11-25 |
| IFAP.CA | 3 | 0 | 3 | 0 | 2014-07-16 → 2026-11-25 |
| ISPH.CA | 3 | 0 | 3 | 0 | 2017-12-11 → 2026-11-25 |
| JUFO.CA | 3 | 0 | 3 | 0 | 2014-07-17 → 2026-11-25 |
| LCSW.CA | 3 | 0 | 3 | 0 | 2014-05-21 → 2026-11-25 |
| MASR.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |
| MCQE.CA | 3 | 0 | 3 | 0 | 2014-07-08 → 2026-11-25 |
| MPCO.CA | 3 | 0 | 3 | 0 | 2014-07-20 → 2026-11-25 |
| MTIE.CA | 3 | 0 | 3 | 0 | 2005-04-26 → 2026-11-25 |
| NVDA | 6 | 1 | 5 | 0 | 2021-11-15 → 2026-11-13 |
| OCDI.CA | 3 | 0 | 3 | 0 | 2014-07-20 → 2026-11-25 |
| OLFI.CA | 3 | 0 | 3 | 0 | 2016-10-03 → 2026-11-25 |
| ORHD.CA | 3 | 0 | 3 | 0 | 2014-06-29 → 2026-11-25 |
| ORWE.CA | 3 | 0 | 3 | 0 | 2014-07-20 → 2026-11-25 |
| PHDC.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |
| POUL.CA | 90 | 47 | 34 | 9 | 2014-06-04 → 2026-11-25 |
| RACC.CA | 3 | 0 | 3 | 0 | 2015-02-12 → 2026-11-25 |
| RMDA.CA | 3 | 0 | 3 | 0 | 2019-11-27 → 2026-11-25 |
| SAUD.CA | 3 | 0 | 3 | 0 | 2014-06-25 → 2026-11-25 |
| SKPC.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |
| TMGH.CA | 3 | 0 | 3 | 0 | 2014-07-21 → 2026-11-25 |

## By horizon (matured only, gap-flagged rows excluded from skill — issue #79)

| Horizon | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| day | 21 | 0.0 | 11.29 | 0.476 |
| week | 15 | 0.0 | 18.28 | 1.0 |
| month | 0 | — | — | — |

## Family skill (mean of family_score × sign(realized), matured only)

| Family | Mean skill | n |
|---|---|---|
| agent | +0.750 | 1 |
| ensemble (net_score) | -0.298 | 36 |
| price-forecast | -0.632 | 34 |
| sentiment | +0.063 | 36 |
| technicals | -0.330 | 36 |

## Forecasts

| Ticker | As of | Horizon | Dir | Expected % | Realized % | Hit | |Err| pp | In range | Adj | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| POUL.CA | 2026-11-12 | day | flat | +0.53 | -1.96 | ❌ | 2.49 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-12 | week | flat | -0.40 | -25.69 | ❌ | 25.29 | ❌ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-12 | month | down | -5.98 | — | — | — | — | | pending (9/21 sessions) |
| NVDA | 2026-11-12 | day | flat | -0.54 | -0.82 | ❌ | 0.28 | ✅ |  | matured 2026-11-13 |
| NVDA | 2026-11-12 | week | up | +8.07 | — | — | — | — | | pending (1/5 sessions) |
| NVDA | 2026-11-12 | month | up | +17.76 | — | — | — | — | | pending (1/21 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.23 | -1.96 | ❌ | 1.73 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.14 | -25.69 | ✅ | 24.55 | ❌ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-13 | month | down | -6.46 | — | — | — | — | | pending (9/21 sessions) |
| NVDA | 2026-11-13 | day | flat | -0.71 | — | — | — | — | | pending (0/1 sessions) |
| NVDA | 2026-11-13 | week | up | +6.93 | — | — | — | — | | pending (0/5 sessions) |
| NVDA | 2026-11-13 | month | up | +18.61 | — | — | — | — | | pending (0/21 sessions) |
| POUL.CA | 2026-11-13 | day | flat | -0.38 | -1.96 | ❌ | 1.58 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.67 | -25.69 | ✅ | 24.02 | ❌ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-13 | month | down | -6.93 | — | — | — | — | | pending (9/21 sessions) |
| POUL.CA | 2026-11-13 | day | up | +1.16 | -1.48 | ❌ | 2.64 | ✅ |  | matured 2026-11-15 |
| POUL.CA | 2026-11-13 | week | down | -1.01 | -25.32 | ✅ | 24.31 | ❌ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-13 | month | down | -1.76 | — | — | — | — | | pending (9/21 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.22 | -20.99 | ❌ | 22.21 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -0.92 | -24.14 | ✅ | 23.22 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.88 | — | — | — | — | | pending (8/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.22 | -20.99 | ❌ | 22.21 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -0.93 | -24.14 | ✅ | 23.21 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.89 | — | — | — | — | | pending (8/14 sessions) |
| COMI.CA | 2026-11-15 | day | up | +702.27 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| COMI.CA | 2026-11-15 | week | up | +711.50 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| COMI.CA | 2026-11-15 | month | up | +674.99 | — | — | — | — | | invalid — base_price 10.149999618530273 deviates 92.1% from the ticker-evidenced close 128.51 at 2026-11-15 — the sweep's data does not match COMI.CA (issue #87) |
| POUL.CA | 2026-11-15 | day | up | +1.21 | -20.99 | ❌ | 22.20 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -1.00 | -24.14 | ✅ | 23.14 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.91 | — | — | — | — | | pending (8/14 sessions) |
| POUL.CA | 2026-11-15 | day | up | +1.21 | -20.99 | ❌ | 22.20 | ❌ |  | matured 2026-11-16 |
| POUL.CA | 2026-11-15 | week | down | -1.00 | -24.14 | ✅ | 23.14 | ❌ |  | matured 2026-11-18 |
| POUL.CA | 2026-11-15 | month | down | -1.91 | — | — | — | — | | pending (8/14 sessions) |
| POUL.CA | 2026-11-16 | day | flat | +0.19 | -5.30 | ❌ | 5.49 | ❌ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | +0.26 | -5.20 | ❌ | 5.46 | ✅ | 💰 | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | up | +1.39 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +2.26 | -5.30 | ❌ | 7.56 | ❌ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | -0.61 | -5.20 | ❌ | 4.59 | ✅ | 💰 | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | down | -1.54 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +2.25 | -5.30 | ❌ | 7.55 | ❌ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | -0.63 | -5.20 | ❌ | 4.57 | ✅ | 💰 | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | down | -1.55 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.71 | -5.61 | ❌ | 24.32 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.73 | -5.49 | ❌ | 22.22 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | up | +16.36 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.62 | -5.61 | ❌ | 24.23 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.55 | -5.49 | ❌ | 22.04 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | up | +16.34 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.61 | -5.61 | ❌ | 24.22 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.54 | -5.49 | ❌ | 22.03 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | up | +16.33 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +1.90 | -6.70 | ❌ | 8.60 | ✅ | 💰 | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | flat | -0.61 | -12.02 | ❌ | 11.41 | ✅ | 💰 | matured 2026-11-22 |
| POUL.CA | 2026-11-16 | month | up | +4.77 | — | — | — | — | | pending (7/15 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.52 | -5.61 | ❌ | 24.13 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.35 | -5.49 | ❌ | 21.84 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | up | +16.21 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-16 | day | up | +18.63 | -5.61 | ❌ | 24.24 | ❌ |  | matured 2026-11-17 |
| POUL.CA | 2026-11-16 | week | up | +16.58 | -5.49 | ❌ | 22.07 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-16 | month | up | +16.36 | — | — | — | — | | pending (7/14 sessions) |
| POUL.CA | 2026-11-17 | day | up | +18.43 | — | — | — | — | | invalid — base_price 8.02 deviates 5.9% from the ticker-evidenced close 7.57 at 2026-11-17 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-17 | week | up | +16.17 | — | — | — | — | | invalid — base_price 8.02 deviates 5.9% from the ticker-evidenced close 7.57 at 2026-11-17 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-17 | month | up | +16.08 | — | — | — | — | | invalid — base_price 8.02 deviates 5.9% from the ticker-evidenced close 7.57 at 2026-11-17 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-18 | day | up | +7.68 | -0.79 | ❌ | 8.47 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-18 | week | up | +15.28 | -7.07 | ❌ | 22.35 | ✅ |  | matured 2026-11-23 |
| POUL.CA | 2026-11-18 | month | up | +17.56 | — | — | — | — | | pending (5/14 sessions) |
| POUL.CA | 2026-11-18 | day | up | +7.08 | -1.56 | ❌ | 8.64 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-18 | week | up | +14.61 | -7.79 | ❌ | 22.40 | ✅ |  | matured 2026-11-23 |
| POUL.CA | 2026-11-18 | month | up | +16.94 | — | — | — | — | | pending (5/14 sessions) |
| POUL.CA | 2026-11-18 | day | up | +6.79 | -1.56 | ❌ | 8.35 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-18 | week | up | +13.91 | -7.79 | ❌ | 21.70 | ✅ |  | matured 2026-11-23 |
| POUL.CA | 2026-11-18 | month | up | +16.77 | — | — | — | — | | pending (5/14 sessions) |
| POUL.CA | 2026-11-18 | day | up | +6.79 | -1.56 | ❌ | 8.35 | ✅ |  | matured 2026-11-19 |
| POUL.CA | 2026-11-18 | week | up | +13.92 | -7.79 | ❌ | 21.71 | ✅ |  | matured 2026-11-23 |
| POUL.CA | 2026-11-18 | month | up | +16.78 | — | — | — | — | | pending (5/14 sessions) |
| POUL.CA | 2026-11-19 | day | up | +6.80 | -8.70 | ❌ | 15.50 | ❌ |  | matured 2026-11-22 |
| POUL.CA | 2026-11-19 | week | up | +13.94 | -10.91 | ❌ | 24.85 | ✅ |  | matured 2026-11-24 |
| POUL.CA | 2026-11-19 | month | up | +16.79 | — | — | — | — | | pending (4/14 sessions) |
| POUL.CA | 2026-11-19 | day | up | +6.84 | -8.70 | ❌ | 15.54 | ❌ |  | matured 2026-11-22 |
| POUL.CA | 2026-11-19 | week | up | +14.02 | -10.91 | ❌ | 24.93 | ✅ |  | matured 2026-11-24 |
| POUL.CA | 2026-11-19 | month | up | +16.84 | — | — | — | — | | pending (4/14 sessions) |
| POUL.CA | 2026-11-22 | day | up | +4.98 | — | — | — | — | | invalid — base_price 7.58 deviates 7.8% from the ticker-evidenced close 7.03 at 2026-11-22 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-22 | week | up | +9.67 | — | — | — | — | | invalid — base_price 7.58 deviates 7.8% from the ticker-evidenced close 7.03 at 2026-11-22 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-22 | month | up | +15.16 | — | — | — | — | | invalid — base_price 7.58 deviates 7.8% from the ticker-evidenced close 7.03 at 2026-11-22 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-23 | day | up | +10.66 | -2.42 | ❌ | 13.08 | ❌ |  | matured 2026-11-24 |
| POUL.CA | 2026-11-23 | week | up | +15.90 | — | — | — | — | | pending (2/3 sessions) |
| POUL.CA | 2026-11-23 | month | up | +21.41 | — | — | — | — | | pending (2/14 sessions) |
| POUL.CA | 2026-11-24 | day | up | +1.04 | — | — | — | — | | invalid — base_price 7.1 deviates 3.5% from the ticker-evidenced close 6.86 at 2026-11-24 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-24 | week | up | +4.82 | — | — | — | — | | invalid — base_price 7.1 deviates 3.5% from the ticker-evidenced close 6.86 at 2026-11-24 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-24 | month | up | +25.29 | — | — | — | — | | invalid — base_price 7.1 deviates 3.5% from the ticker-evidenced close 6.86 at 2026-11-24 — the sweep's data does not match POUL.CA (issue #87) |
| POUL.CA | 2026-11-25 | day | up | +3.39 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-25 | week | up | +10.92 | — | — | — | — | | pending (0/3 sessions) |
| POUL.CA | 2026-11-25 | month | up | +27.27 | — | — | — | — | | pending (0/14 sessions) |
| ACGC.CA | 2026-11-25 | day | down | -1.01 | — | — | — | — | | pending (0/1 sessions) |
| ACGC.CA | 2026-11-25 | week | flat | -0.14 | — | — | — | — | | pending (0/3 sessions) |
| ACGC.CA | 2026-11-25 | month | down | -2.12 | — | — | — | — | | pending (0/14 sessions) |
| ADIB.CA | 2026-11-25 | day | flat | -0.45 | — | — | — | — | | pending (0/1 sessions) |
| ADIB.CA | 2026-11-25 | week | flat | +0.43 | — | — | — | — | | pending (0/3 sessions) |
| ADIB.CA | 2026-11-25 | month | up | +1.47 | — | — | — | — | | pending (0/14 sessions) |
| AMOC.CA | 2026-11-25 | day | up | +3.68 | — | — | — | — | | pending (0/1 sessions) |
| AMOC.CA | 2026-11-25 | week | up | +3.37 | — | — | — | — | | pending (0/3 sessions) |
| AMOC.CA | 2026-11-25 | month | up | +7.41 | — | — | — | — | | pending (0/14 sessions) |
| ARCC.CA | 2026-11-25 | day | flat | -0.67 | — | — | — | — | | pending (0/1 sessions) |
| ARCC.CA | 2026-11-25 | week | flat | -0.53 | — | — | — | — | | pending (0/3 sessions) |
| ARCC.CA | 2026-11-25 | month | down | -0.97 | — | — | — | — | | pending (0/14 sessions) |
| ATQA.CA | 2026-11-25 | day | up | +2.69 | — | — | — | — | | pending (0/1 sessions) |
| ATQA.CA | 2026-11-25 | week | up | +1.34 | — | — | — | — | | pending (0/3 sessions) |
| ATQA.CA | 2026-11-25 | month | down | -3.28 | — | — | — | — | | pending (0/14 sessions) |
| CIRA.CA | 2026-11-25 | day | flat | -0.21 | — | — | — | — | | pending (0/1 sessions) |
| CIRA.CA | 2026-11-25 | week | flat | +0.53 | — | — | — | — | | pending (0/3 sessions) |
| CIRA.CA | 2026-11-25 | month | flat | -0.52 | — | — | — | — | | pending (0/14 sessions) |
| CLHO.CA | 2026-11-25 | day | flat | +0.23 | — | — | — | — | | pending (0/1 sessions) |
| CLHO.CA | 2026-11-25 | week | flat | -0.64 | — | — | — | — | | pending (0/3 sessions) |
| CLHO.CA | 2026-11-25 | month | down | -3.76 | — | — | — | — | | pending (0/14 sessions) |
| EFID.CA | 2026-11-25 | day | flat | -0.04 | — | — | — | — | | pending (0/1 sessions) |
| EFID.CA | 2026-11-25 | week | flat | +0.13 | — | — | — | — | | pending (0/3 sessions) |
| EFID.CA | 2026-11-25 | month | down | -4.40 | — | — | — | — | | pending (0/14 sessions) |
| EFIH.CA | 2026-11-25 | day | flat | +0.10 | — | — | — | — | | pending (0/1 sessions) |
| EFIH.CA | 2026-11-25 | week | flat | -0.11 | — | — | — | — | | pending (0/3 sessions) |
| EFIH.CA | 2026-11-25 | month | down | -1.87 | — | — | — | — | | pending (0/14 sessions) |
| EGAL.CA | 2026-11-25 | day | up | +1.51 | — | — | — | — | | pending (0/1 sessions) |
| EGAL.CA | 2026-11-25 | week | up | +1.97 | — | — | — | — | | pending (0/3 sessions) |
| EGAL.CA | 2026-11-25 | month | up | +2.80 | — | — | — | — | | pending (0/14 sessions) |
| EGAS.CA | 2026-11-25 | day | flat | -0.05 | — | — | — | — | | pending (0/1 sessions) |
| EGAS.CA | 2026-11-25 | week | down | -1.52 | — | — | — | — | | pending (0/3 sessions) |
| EGAS.CA | 2026-11-25 | month | down | -1.73 | — | — | — | — | | pending (0/14 sessions) |
| ETEL.CA | 2026-11-25 | day | flat | +0.25 | — | — | — | — | | pending (0/1 sessions) |
| ETEL.CA | 2026-11-25 | week | up | +1.29 | — | — | — | — | | pending (0/3 sessions) |
| ETEL.CA | 2026-11-25 | month | up | +1.55 | — | — | — | — | | pending (0/14 sessions) |
| ETRS.CA | 2026-11-25 | day | flat | -0.03 | — | — | — | — | | pending (0/1 sessions) |
| ETRS.CA | 2026-11-25 | week | down | -1.20 | — | — | — | — | | pending (0/3 sessions) |
| ETRS.CA | 2026-11-25 | month | down | -3.32 | — | — | — | — | | pending (0/14 sessions) |
| FAIT.CA | 2026-11-25 | day | down | -0.99 | — | — | — | — | | pending (0/1 sessions) |
| FAIT.CA | 2026-11-25 | week | flat | +0.17 | — | — | — | — | | pending (0/3 sessions) |
| FAIT.CA | 2026-11-25 | month | down | -2.12 | — | — | — | — | | pending (0/14 sessions) |
| FAITA.CA | 2026-11-25 | day | flat | +0.16 | — | — | — | — | | pending (0/1 sessions) |
| FAITA.CA | 2026-11-25 | week | flat | +0.28 | — | — | — | — | | pending (0/3 sessions) |
| FAITA.CA | 2026-11-25 | month | down | -0.80 | — | — | — | — | | pending (0/14 sessions) |
| GOUR.CA | 2026-11-25 | day | flat | +0.42 | — | — | — | — | | pending (0/1 sessions) |
| GOUR.CA | 2026-11-25 | week | flat | +0.73 | — | — | — | — | | pending (0/3 sessions) |
| GOUR.CA | 2026-11-25 | month | up | +1.98 | — | — | — | — | | pending (0/14 sessions) |
| ICFC.CA | 2026-11-25 | day | down | -1.53 | — | — | — | — | | pending (0/1 sessions) |
| ICFC.CA | 2026-11-25 | week | down | -3.48 | — | — | — | — | | pending (0/3 sessions) |
| ICFC.CA | 2026-11-25 | month | down | -8.88 | — | — | — | — | | pending (0/14 sessions) |
| IFAP.CA | 2026-11-25 | day | up | +2.16 | — | — | — | — | | pending (0/1 sessions) |
| IFAP.CA | 2026-11-25 | week | up | +2.33 | — | — | — | — | | pending (0/3 sessions) |
| IFAP.CA | 2026-11-25 | month | up | +3.89 | — | — | — | — | | pending (0/14 sessions) |
| ISPH.CA | 2026-11-25 | day | up | +1.23 | — | — | — | — | | pending (0/1 sessions) |
| ISPH.CA | 2026-11-25 | week | up | +2.28 | — | — | — | — | | pending (0/3 sessions) |
| ISPH.CA | 2026-11-25 | month | flat | +0.09 | — | — | — | — | | pending (0/14 sessions) |
| JUFO.CA | 2026-11-25 | day | up | +1.12 | — | — | — | — | | pending (0/1 sessions) |
| JUFO.CA | 2026-11-25 | week | up | +2.71 | — | — | — | — | | pending (0/3 sessions) |
| JUFO.CA | 2026-11-25 | month | up | +4.70 | — | — | — | — | | pending (0/14 sessions) |
| LCSW.CA | 2026-11-25 | day | down | -1.48 | — | — | — | — | | pending (0/1 sessions) |
| LCSW.CA | 2026-11-25 | week | down | -1.98 | — | — | — | — | | pending (0/3 sessions) |
| LCSW.CA | 2026-11-25 | month | down | -7.95 | — | — | — | — | | pending (0/14 sessions) |
| MASR.CA | 2026-11-25 | day | up | +1.37 | — | — | — | — | | pending (0/1 sessions) |
| MASR.CA | 2026-11-25 | week | up | +2.48 | — | — | — | — | | pending (0/3 sessions) |
| MASR.CA | 2026-11-25 | month | up | +5.89 | — | — | — | — | | pending (0/14 sessions) |
| MCQE.CA | 2026-11-25 | day | up | +0.84 | — | — | — | — | | pending (0/1 sessions) |
| MCQE.CA | 2026-11-25 | week | up | +0.75 | — | — | — | — | | pending (0/3 sessions) |
| MCQE.CA | 2026-11-25 | month | down | -1.09 | — | — | — | — | | pending (0/14 sessions) |
| MPCO.CA | 2026-11-25 | day | up | +2.48 | — | — | — | — | | pending (0/1 sessions) |
| MPCO.CA | 2026-11-25 | week | up | +3.93 | — | — | — | — | | pending (0/3 sessions) |
| MPCO.CA | 2026-11-25 | month | up | +1.20 | — | — | — | — | | pending (0/14 sessions) |
| MTIE.CA | 2026-11-25 | day | down | -4.44 | — | — | — | — | | pending (0/1 sessions) |
| MTIE.CA | 2026-11-25 | week | down | -2.18 | — | — | — | — | | pending (0/2 sessions) |
| MTIE.CA | 2026-11-25 | month | up | +2.43 | — | — | — | — | | pending (0/8 sessions) |
| OCDI.CA | 2026-11-25 | day | flat | -0.21 | — | — | — | — | | pending (0/1 sessions) |
| OCDI.CA | 2026-11-25 | week | up | +1.03 | — | — | — | — | | pending (0/3 sessions) |
| OCDI.CA | 2026-11-25 | month | up | +4.59 | — | — | — | — | | pending (0/14 sessions) |
| OLFI.CA | 2026-11-25 | day | flat | -0.05 | — | — | — | — | | pending (0/1 sessions) |
| OLFI.CA | 2026-11-25 | week | flat | -0.18 | — | — | — | — | | pending (0/3 sessions) |
| OLFI.CA | 2026-11-25 | month | down | -2.47 | — | — | — | — | | pending (0/14 sessions) |
| ORHD.CA | 2026-11-25 | day | down | -1.82 | — | — | — | — | | pending (0/1 sessions) |
| ORHD.CA | 2026-11-25 | week | down | -1.62 | — | — | — | — | | pending (0/3 sessions) |
| ORHD.CA | 2026-11-25 | month | down | -1.34 | — | — | — | — | | pending (0/14 sessions) |
| ORWE.CA | 2026-11-25 | day | up | +2.13 | — | — | — | — | | pending (0/1 sessions) |
| ORWE.CA | 2026-11-25 | week | up | +2.60 | — | — | — | — | | pending (0/3 sessions) |
| ORWE.CA | 2026-11-25 | month | up | +2.82 | — | — | — | — | | pending (0/14 sessions) |
| PHDC.CA | 2026-11-25 | day | up | +1.68 | — | — | — | — | | pending (0/1 sessions) |
| PHDC.CA | 2026-11-25 | week | up | +2.09 | — | — | — | — | | pending (0/3 sessions) |
| PHDC.CA | 2026-11-25 | month | up | +3.77 | — | — | — | — | | pending (0/14 sessions) |
| RACC.CA | 2026-11-25 | day | up | +2.19 | — | — | — | — | | pending (0/1 sessions) |
| RACC.CA | 2026-11-25 | week | up | +2.05 | — | — | — | — | | pending (0/3 sessions) |
| RACC.CA | 2026-11-25 | month | up | +2.54 | — | — | — | — | | pending (0/11 sessions) |
| RMDA.CA | 2026-11-25 | day | flat | +0.00 | — | — | — | — | | pending (0/1 sessions) |
| RMDA.CA | 2026-11-25 | week | flat | +0.00 | — | — | — | — | | pending (0/5 sessions) |
| RMDA.CA | 2026-11-25 | month | flat | +0.00 | — | — | — | — | | pending (0/21 sessions) |
| SAUD.CA | 2026-11-25 | day | flat | +0.00 | — | — | — | — | | pending (0/1 sessions) |
| SAUD.CA | 2026-11-25 | week | flat | +0.00 | — | — | — | — | | pending (0/5 sessions) |
| SAUD.CA | 2026-11-25 | month | flat | +0.00 | — | — | — | — | | pending (0/21 sessions) |
| SKPC.CA | 2026-11-25 | day | flat | +0.00 | — | — | — | — | | pending (0/1 sessions) |
| SKPC.CA | 2026-11-25 | week | flat | +0.00 | — | — | — | — | | pending (0/5 sessions) |
| SKPC.CA | 2026-11-25 | month | flat | +0.00 | — | — | — | — | | pending (0/21 sessions) |
| TMGH.CA | 2026-11-25 | day | flat | +0.00 | — | — | — | — | | pending (0/1 sessions) |
| TMGH.CA | 2026-11-25 | week | flat | +0.00 | — | — | — | — | | pending (0/5 sessions) |
| TMGH.CA | 2026-11-25 | month | flat | +0.00 | — | — | — | — | | pending (0/21 sessions) |
| POUL.CA | 2026-11-25 | day | flat | +0.00 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-25 | week | flat | +0.00 | — | — | — | — | | pending (0/5 sessions) |
| POUL.CA | 2026-11-25 | month | flat | +0.00 | — | — | — | — | | pending (0/21 sessions) |
| POUL.CA | 2026-11-26 | day | flat | +0.00 | — | — | — | — | | pending (0/1 sessions) |
| POUL.CA | 2026-11-26 | week | flat | +0.00 | — | — | — | — | | pending (0/5 sessions) |
| POUL.CA | 2026-11-26 | month | flat | +0.00 | — | — | — | — | | pending (0/21 sessions) |

## Data gaps & notes

- 21 sweep(s) carry no ensemble.json (category/single-tool runs): sweeps/2026-11-12/053914__backfill-issue-7__sweep-poul-ca; sweeps/2026-11-12/153612__backfill-issue-13__sweep-lite-poul-ca-market-egx; sweeps/2026-11-13/070542__run-news-disclosure-poul-ca__run43382934691; sweeps/2026-11-13/105352__category-agent-poul-ca__run43411434864; sweeps/2026-11-13/112806__category-agent-poul-ca__run43414990698; sweeps/2026-11-13/123153__category-news-poul-ca__run43425457246; sweeps/2026-11-13/141636__category-news-poul-ca__run43440228991; sweeps/2026-11-13/171214__category-news-poul-ca__run43469687667; sweeps/2026-11-13/175202__category-news-poul-ca__run43475305450; sweeps/2026-11-13/181309__run-financetoolkit-comi-ca__run43480301234; sweeps/2026-11-13/181720__run-financetoolkit-poul-ca__run43481004601; sweeps/2026-11-13/184846__category-agent-poul-ca__run43482153785; sweeps/2026-11-14/085808__run-egx-data-poul-ca__run43578206341; sweeps/2026-11-15/130920__run-kronos-nvda__run43717394637; sweeps/2026-11-15/131641__category-news-poul-ca__run43717400241; sweeps/2026-11-15/134248__category-agent-poul-ca__run43717405249; sweeps/2026-11-15/140746__sweep-nvda__run43717388468; sweeps/2026-11-16/040734__run-egx-data-comi-ca__run43801992894; sweeps/2026-11-16/041112__category-news-poul-ca__run43801982888; sweeps/2026-11-16/041429__run-talib-comi-ca__run43802798857; sweeps/2026-11-16/042354__category-news-poul-ca__run43802770319
- ACGC.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/110009__sweep-lite-acgc-ca-market-egx__runw5-sweeplite-acgc-001/collected/egx-data/egxpy_acgc.csv)
- ADIB.CA: actuals series has 3000 sessions, 2014-07-15 → 2026-11-25 (last source: sweeps/2026-11-25/111021__sweep-lite-adib-ca-market-egx__runw5-sweeplite-adib-001/collected/egx-data/egxpy_adib.csv)
- AMOC.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/112115__sweep-lite-amoc-ca-market-egx__runw5-sweeplite-amoc-001/collected/egx-data/egxpy_amoc.csv)
- ARCC.CA: actuals series has 3000 sessions, 2014-07-13 → 2026-11-25 (last source: sweeps/2026-11-25/112926__sweep-lite-arcc-ca-market-egx__runw5-sweeplite-arcc-001/collected/egx-data/egxpy_arcc.csv)
- ATQA.CA: actuals series has 3000 sessions, 2014-06-29 → 2026-11-25 (last source: sweeps/2026-11-25/113637__sweep-lite-atqa-ca-market-egx__runw5-sweeplite-atqa-001/collected/egx-data/egxpy_atqa.csv)
- CIRA.CA: actuals series has 1978 sessions, 2018-10-01 → 2026-11-25 (last source: sweeps/2026-11-25/114458__sweep-lite-cira-ca-market-egx__runw5-sweeplite-cira-001/collected/egx-data/egxpy_cira.csv)
- CLHO.CA: actuals series has 2575 sessions, 2016-04-14 → 2026-11-25 (last source: sweeps/2026-11-25/115426__sweep-lite-clho-ca-market-egx__runw5-sweeplite-clho-001/collected/egx-data/egxpy_clho.csv)
- COMI.CA: actuals series has 2180 sessions, 2018-01-01 → 2026-11-12 (last source: sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248/collected/quantstats/ohlc.csv)
- EFID.CA: actuals series has 2824 sessions, 2015-04-02 → 2026-11-25 (last source: sweeps/2026-11-25/120234__sweep-lite-efid-ca-market-egx__runw5-sweeplite-efid-001/collected/egx-data/egxpy_efid.csv)
- EFIH.CA: actuals series has 1238 sessions, 2021-10-19 → 2026-11-25 (last source: sweeps/2026-11-25/121054__sweep-lite-efih-ca-market-egx__runw5-sweeplite-efih-001/collected/egx-data/egxpy_efih.csv)
- EGAL.CA: actuals series has 3000 sessions, 2014-06-09 → 2026-11-25 (last source: sweeps/2026-11-25/121852__sweep-lite-egal-ca-market-egx__runw5-sweeplite-egal-001/collected/egx-data/egxpy_egal.csv)
- EGAS.CA: actuals series has 3000 sessions, 2014-07-15 → 2026-11-25 (last source: sweeps/2026-11-25/122721__sweep-lite-egas-ca-market-egx__runw5-sweeplite-egas-001/collected/egx-data/egxpy_egas.csv)
- ETEL.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/124034__sweep-lite-etel-ca-market-egx__runw5-sweeplite-etel-001/collected/egx-data/egxpy_etel.csv)
- ETRS.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/124806__sweep-lite-etrs-ca-market-egx__runw5-sweeplite-etrs-001/collected/egx-data/egxpy_etrs.csv)
- FAIT.CA: actuals series has 3000 sessions, 2014-06-26 → 2026-11-25 (last source: sweeps/2026-11-25/125656__sweep-lite-fait-ca-market-egx__runw5-sweeplite-fait-001/collected/egx-data/egxpy_fait.csv)
- FAITA.CA: actuals series has 3000 sessions, 2014-07-13 → 2026-11-25 (last source: sweeps/2026-11-25/130440__sweep-lite-faita-ca-market-egx__runw5-sweeplite-faita-001/collected/egx-data/egxpy_faita.csv)
- GOUR.CA: actuals series has 192 sessions, 2026-02-10 → 2026-11-25 (last source: sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001/collected/egx-data/egxpy_gour.csv)
- ICFC.CA: actuals series has 3000 sessions, 2014-06-11 → 2026-11-25 (last source: sweeps/2026-11-25/131935__sweep-lite-icfc-ca-market-egx__runw5-sweeplite-icfc-001/collected/egx-data/egxpy_icfc.csv)
- IFAP.CA: actuals series has 3000 sessions, 2014-07-16 → 2026-11-25 (last source: sweeps/2026-11-25/132652__sweep-lite-ifap-ca-market-egx__runw5-sweeplite-ifap-001/collected/egx-data/egxpy_ifap.csv)
- ISPH.CA: actuals series has 2173 sessions, 2017-12-11 → 2026-11-25 (last source: sweeps/2026-11-25/133518__sweep-lite-isph-ca-market-egx__runw5-sweeplite-isph-001/collected/egx-data/egxpy_isph.csv)
- JUFO.CA: actuals series has 3000 sessions, 2014-07-17 → 2026-11-25 (last source: sweeps/2026-11-25/134241__sweep-lite-jufo-ca-market-egx__runw5-sweeplite-jufo-001/collected/egx-data/egxpy_jufo.csv)
- LCSW.CA: actuals series has 3000 sessions, 2014-05-21 → 2026-11-25 (last source: sweeps/2026-11-25/135002__sweep-lite-lcsw-ca-market-egx__runw5-sweeplite-lcsw-001/collected/egx-data/egxpy_lcsw.csv)
- MASR.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/135953__sweep-lite-masr-ca-market-egx__runw5-sweeplite-masr-001/collected/egx-data/egxpy_masr.csv)
- MCQE.CA: actuals series has 3000 sessions, 2014-07-08 → 2026-11-25 (last source: sweeps/2026-11-25/140917__sweep-lite-mcqe-ca-market-egx__runw5-sweeplite-mcqe-001/collected/egx-data/egxpy_mcqe.csv)
- MPCO.CA: actuals series has 3000 sessions, 2014-07-20 → 2026-11-25 (last source: sweeps/2026-11-25/141625__sweep-lite-mpco-ca-market-egx__runw5-sweeplite-mpco-001/collected/egx-data/egxpy_mpco.csv)
- MTIE.CA: actuals series has 2334 sessions, 2005-04-26 → 2026-11-25 (last source: sweeps/2026-11-25/142551__sweep-lite-mtie-ca-market-egx__runw5-sweeplite-mtie-001/collected/egx-data/egxpy_mtie.csv)
- NVDA: actuals series has 1255 sessions, 2021-11-15 → 2026-11-13 (last source: sweeps/2026-11-16/041633__run-openbb-nvda__run43802957047/collected/openbb/NVDA.csv)
- OCDI.CA: actuals series has 3000 sessions, 2014-07-20 → 2026-11-25 (last source: sweeps/2026-11-25/143311__sweep-lite-ocdi-ca-market-egx__runw5-sweeplite-ocdi-001/collected/egx-data/egxpy_ocdi.csv)
- OLFI.CA: actuals series has 2464 sessions, 2016-10-03 → 2026-11-25 (last source: sweeps/2026-11-25/144023__sweep-lite-olfi-ca-market-egx__runw5-sweeplite-olfi-001/collected/egx-data/egxpy_olfi.csv)
- ORHD.CA: actuals series has 3000 sessions, 2014-06-29 → 2026-11-25 (last source: sweeps/2026-11-25/144735__sweep-lite-orhd-ca-market-egx__runw5-sweeplite-orhd-001/collected/egx-data/egxpy_orhd.csv)
- ORWE.CA: actuals series has 3000 sessions, 2014-07-20 → 2026-11-25 (last source: sweeps/2026-11-25/145515__sweep-lite-orwe-ca-market-egx__runw5-sweeplite-orwe-001/collected/egx-data/egxpy_orwe.csv)
- PHDC.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/150344__sweep-lite-phdc-ca-market-egx__runw5-sweeplite-phdc-001/collected/egx-data/egxpy_phdc.csv)
- POUL.CA: actuals series has 3053 sessions, 2014-06-04 → 2026-11-25 (last source: sweeps/2026-11-26/074217__sweep-lite-poul-ca-market-egx__runsched-2026-11-26/collected/egx-data/egxpy_poul.csv)
- RACC.CA: actuals series has 2325 sessions, 2015-02-12 → 2026-11-25 (last source: sweeps/2026-11-25/151150__sweep-lite-racc-ca-market-egx__runw5-sweeplite-racc-001/collected/egx-data/egxpy_racc.csv)
- RMDA.CA: actuals series has 1699 sessions, 2019-11-27 → 2026-11-25 (last source: sweeps/2026-11-25/195201__sweep-lite-rmda-ca-market-egx__runw5-sweeplite-rmda-001/collected/egx-data/egxpy_rmda.csv)
- SAUD.CA: actuals series has 3000 sessions, 2014-06-25 → 2026-11-25 (last source: sweeps/2026-11-25/201240__sweep-lite-saud-ca-market-egx__runw5-sweeplite-saud-001/collected/egx-data/egxpy_saud.csv)
- SKPC.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/201513__sweep-lite-skpc-ca-market-egx__runw5-sweeplite-skpc-001/collected/egx-data/egxpy_skpc.csv)
- TMGH.CA: actuals series has 3000 sessions, 2014-07-21 → 2026-11-25 (last source: sweeps/2026-11-25/202510__sweep-lite-tmgh-ca-market-egx__runw5-sweeplite-tmgh-001/collected/egx-data/egxpy_tmgh.csv)
- price-CSV parsing skipped 8 malformed/non-positive row(s) across all candidate files
- 12 forecast(s) invalidated by the issue-#87 guard (base_price inconsistent with the ticker-evidenced price level; never scored): COMI.CA as of 2026-11-15 (day) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; COMI.CA as of 2026-11-15 (week) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; COMI.CA as of 2026-11-15 (month) from sweeps/2026-11-15/132518__sweep-lite-comi-ca-market-egx__run43717410248; POUL.CA as of 2026-11-17 (day) from sweeps/2026-11-16/225700__sweep-lite-poul-ca__run43967492548; POUL.CA as of 2026-11-17 (week) from sweeps/2026-11-16/225700__sweep-lite-poul-ca__run43967492548; POUL.CA as of 2026-11-17 (month) from sweeps/2026-11-16/225700__sweep-lite-poul-ca__run43967492548; POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24
- 12 matured forecast(s) span a known dividend ex-date (or carry an undated dividend action) but were NOT dividend-adjusted — their realized move includes the mechanical ex-div drop (issue #129): POUL.CA as of 2026-11-12 (week) from sweeps/2026-11-12/163459__backfill-issue-14__sweep-lite-poul-ca-market-egx: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-13 (week) from sweeps/2026-11-13/060515__backfill-issue-17__sweep-lite-poul-ca-market-egx: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-13 (week) from sweeps/2026-11-13/092727__sweep-poul-ca__run43386334186: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-13 (week) from sweeps/2026-11-13/095050__sweep-lite-poul-ca-market-egx__run43402572619: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/074752__sweep-lite-poul-ca__run43688673389: 1 undated dividend action(s) (DPS 1.9) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/074752__sweep-lite-poul-ca__run43688673389: 1 undated dividend action(s) (DPS 1.9) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/132459__sweep-lite-poul-ca-market-egx__run43717383224: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/132459__sweep-lite-poul-ca-market-egx__run43717383224: horizon spans known ex-date 2026-11-16 (DPS 1.8999999998, recorded by sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-egx__run43805931446) but this forecast carries no dividend action — realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/140509__sweep-lite-poul-ca-market-egx__run43720903619: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/140509__sweep-lite-poul-ca-market-egx__run43720903619: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (day) from sweeps/2026-11-15/141558__sweep-lite-poul-ca-market-egx__run43721738392: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129); POUL.CA as of 2026-11-15 (week) from sweeps/2026-11-15/141558__sweep-lite-poul-ca-market-egx__run43721738392: 1 undated dividend action(s) (DPS 1.89) with no ex-date and no entitlement_end — the horizon may span the ex-date but the drop cannot be placed, so the realized move is unadjusted (issue #129)
- 12 gap-flagged matured forecast(s) excluded from skill/weights/aggregates (issue #79): the rows stay listed with their dividend_gap flag — only the means exclude them; the published weights change on the next publish is the intended correction, announced at the #79 landing

_Skill is provisional until a meaningful number of forecasts have matured; a family is only as good as its measured record._
