# Technical snapshot — EFID.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2862 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 20.4 |
| High | 20.4 |
| Low | 20.4 |
| Close | 20.4 |
| RSI(14) | 53.7627 |
| MACD | 0.1878 |
| MACD signal | -0.0702 |
| MACD histogram | 0.258 |
| EMA(20) | 19.8349 |
| EMA(50) | 21.0619 |
| EMA(200) | 24.7604 |
| ADX(14) | 25.8634 |
| Bollinger upper | 21.6436 |
| Bollinger mid | 19.4055 |
| Bollinger lower | 17.1674 |
| Bollinger %B | 0.7222 |
| ATR(14) | 0.8426 |
| Stochastic %K | 68.8765 |
| Stochastic %D | 74.804 |

## Trend read (facts only)

- Close 20.4 is above EMA_20 19.8349 (+2.85%).
- Close 20.4 is below EMA_50 21.0619 (-3.14%).
- Close 20.4 is below EMA_200 24.7604 (-17.61%).
- RSI(14) is 53.7627, in the neutral zone (30-70).
- MACD 0.1878 is above its signal line -0.0702 (histogram 0.258).
- Price sits at %B 0.7222 of the Bollinger range (lower 17.1674, mid 19.4055, upper 21.6436).
- ADX(14) is 25.8634, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 68.8765 is below %D 74.804.
- ATR(14) is 0.8426 (4.13% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
