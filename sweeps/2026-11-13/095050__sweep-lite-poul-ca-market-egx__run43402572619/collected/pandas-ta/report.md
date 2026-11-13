# Technical snapshot — POUL.CA

- Last session: **2026-11-12**
- Data used: 1922 rows (2019-01-01 → 2026-11-12), after dropping rows before 2019-01-01; 6522 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 10.2 |
| High | 10.4 |
| Low | 10.15 |
| Close | 10.15 |
| RSI(14) | 26.6369 |
| MACD | -2.0545 |
| MACD signal | -2.9153 |
| MACD histogram | 0.8608 |
| EMA(20) | 10.9809 |
| EMA(50) | 17.4897 |
| EMA(200) | 27.0247 |
| ADX(14) | 52.6746 |
| Bollinger upper | 10.5145 |
| Bollinger mid | 9.8375 |
| Bollinger lower | 9.1605 |
| Bollinger %B | 0.7308 |
| ATR(14) | 0.6014 |
| Stochastic %K | 88.8566 |
| Stochastic %D | 86.5545 |

## Trend read (facts only)

- Close 10.15 is below EMA_20 10.9809 (-7.57%).
- Close 10.15 is below EMA_50 17.4897 (-41.97%).
- Close 10.15 is below EMA_200 27.0247 (-62.44%).
- RSI(14) is 26.6369, in the oversold zone (<= 30).
- MACD -2.0545 is above its signal line -2.9153 (histogram 0.8608).
- Price sits at %B 0.7308 of the Bollinger range (lower 9.1605, mid 9.8375, upper 10.5145).
- ADX(14) is 52.6746, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 88.8566 is above %D 86.5545.
- ATR(14) is 0.6014 (5.93% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
