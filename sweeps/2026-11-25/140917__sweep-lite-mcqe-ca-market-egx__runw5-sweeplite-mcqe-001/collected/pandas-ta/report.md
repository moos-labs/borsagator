# Technical snapshot — MCQE.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6135 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 175.97 |
| High | 175.97 |
| Low | 175.97 |
| Close | 175.97 |
| RSI(14) | 49.026 |
| MACD | -0.9594 |
| MACD signal | -1.9054 |
| MACD histogram | 0.946 |
| EMA(20) | 175.9927 |
| EMA(50) | 183.0291 |
| EMA(200) | 177.7375 |
| ADX(14) | 13.0127 |
| Bollinger upper | 189.6831 |
| Bollinger mid | 173.5975 |
| Bollinger lower | 157.5119 |
| Bollinger %B | 0.5737 |
| ATR(14) | 9.829 |
| Stochastic %K | 29.7549 |
| Stochastic %D | 33.3858 |

## Trend read (facts only)

- Close 175.97 is below EMA_20 175.9927 (-0.01%).
- Close 175.97 is below EMA_50 183.0291 (-3.86%).
- Close 175.97 is below EMA_200 177.7375 (-0.99%).
- RSI(14) is 49.026, in the neutral zone (30-70).
- MACD -0.9594 is above its signal line -1.9054 (histogram 0.946).
- Price sits at %B 0.5737 of the Bollinger range (lower 157.5119, mid 173.5975, upper 189.6831).
- ADX(14) is 13.0127, indicating a weak / no clear trend (< 20).
- Stochastic %K 29.7549 is below %D 33.3858.
- ATR(14) is 9.829 (5.59% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
