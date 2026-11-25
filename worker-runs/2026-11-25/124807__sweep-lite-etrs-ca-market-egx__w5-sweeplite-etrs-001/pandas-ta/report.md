# Technical snapshot — ETRS.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6149 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 11.1 |
| High | 11.35 |
| Low | 10.92 |
| Close | 11.05 |
| RSI(14) | 55.4097 |
| MACD | 0.1391 |
| MACD signal | 0.1131 |
| MACD histogram | 0.026 |
| EMA(20) | 10.8651 |
| EMA(50) | 10.7298 |
| EMA(200) | 9.6124 |
| ADX(14) | 18.4141 |
| Bollinger upper | 11.3881 |
| Bollinger mid | 10.8165 |
| Bollinger lower | 10.2449 |
| Bollinger %B | 0.7043 |
| ATR(14) | 0.3967 |
| Stochastic %K | 56.041 |
| Stochastic %D | 60.6239 |

## Trend read (facts only)

- Close 11.05 is above EMA_20 10.8651 (+1.70%).
- Close 11.05 is above EMA_50 10.7298 (+2.98%).
- Close 11.05 is above EMA_200 9.6124 (+14.96%).
- RSI(14) is 55.4097, in the neutral zone (30-70).
- MACD 0.1391 is above its signal line 0.1131 (histogram 0.026).
- Price sits at %B 0.7043 of the Bollinger range (lower 10.2449, mid 10.8165, upper 11.3881).
- ADX(14) is 18.4141, indicating a weak / no clear trend (< 20).
- Stochastic %K 56.041 is below %D 60.6239.
- ATR(14) is 0.3967 (3.59% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
