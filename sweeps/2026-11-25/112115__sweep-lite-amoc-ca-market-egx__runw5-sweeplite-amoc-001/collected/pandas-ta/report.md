# Technical snapshot — AMOC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5067 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 12.51 |
| High | 12.7 |
| Low | 12.17 |
| Close | 12.25 |
| RSI(14) | 35.8702 |
| MACD | -0.1928 |
| MACD signal | -0.0764 |
| MACD histogram | -0.1164 |
| EMA(20) | 13.084 |
| EMA(50) | 12.9375 |
| EMA(200) | 10.6 |
| ADX(14) | 11.6396 |
| Bollinger upper | 14.1536 |
| Bollinger mid | 13.2295 |
| Bollinger lower | 12.3054 |
| Bollinger %B | -0.03 |
| ATR(14) | 0.5468 |
| Stochastic %K | 7.759 |
| Stochastic %D | 8.8808 |

## Trend read (facts only)

- Close 12.25 is below EMA_20 13.084 (-6.37%).
- Close 12.25 is below EMA_50 12.9375 (-5.31%).
- Close 12.25 is above EMA_200 10.6 (+15.57%).
- RSI(14) is 35.8702, in the neutral zone (30-70).
- MACD -0.1928 is below its signal line -0.0764 (histogram -0.1164).
- Price sits at %B -0.03 of the Bollinger range (lower 12.3054, mid 13.2295, upper 14.1536).
- ADX(14) is 11.6396, indicating a weak / no clear trend (< 20).
- Stochastic %K 7.759 is below %D 8.8808.
- ATR(14) is 0.5468 (4.46% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
