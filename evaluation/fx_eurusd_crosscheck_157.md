# EURUSD / USDJPY level cross-check (INS-IMPROVE-157 note 2)

Second source: Frankfurter (api.frankfurter.dev/v1/<date>?base=EUR&symbols=USD,JPY; ECB reference rates, published once a day), fetched 2026-11-28. Harvest = Yahoo daily close (UTC session date). Numbers only.

| Date | Frankfurter EUR/USD | Harvest EURUSD close | Diff % | Frankfurter EUR/JPY / EUR/USD (implied USDJPY) | Harvest USDJPY close |
|---|---|---|---|---|---|
| 2026-11-27 | 1.0957 | 1.09721 | +0.14 | 159.54 | 159.28 |
| 2026-01-02 | 1.1721 | 1.17505 | +0.25 | 156.94 | 156.73 |
| 2025-06-30 | 1.1720 | 1.17872 | +0.57 | 144.35 | 143.80 |

The level (about 1.10 to 1.18) agrees. The gaps are the timing difference between the ECB reference fix and a UTC end-of-day close, plus rounding; three dates checked, not a full-series audit.
