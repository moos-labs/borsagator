# Technical snapshot — SKPC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5343 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 14.18 |
| High | 14.18 |
| Low | 14.18 |
| Close | 14.18 |
| RSI(14) | 35.2842 |
| MACD | -0.3289 |
| MACD signal | -0.3103 |
| MACD histogram | -0.0185 |
| EMA(20) | 14.7706 |
| EMA(50) | 15.4329 |
| EMA(200) | 16.7302 |
| ADX(14) | 20.5781 |
| Bollinger upper | 15.3626 |
| Bollinger mid | 14.743 |
| Bollinger lower | 14.1234 |
| Bollinger %B | 0.0456 |
| ATR(14) | 0.4436 |
| Stochastic %K | 19.375 |
| Stochastic %D | 22.0517 |

## Trend read (facts only)

- Close 14.18 is below EMA_20 14.7706 (-4.00%).
- Close 14.18 is below EMA_50 15.4329 (-8.12%).
- Close 14.18 is below EMA_200 16.7302 (-15.24%).
- RSI(14) is 35.2842, in the neutral zone (30-70).
- MACD -0.3289 is below its signal line -0.3103 (histogram -0.0185).
- Price sits at %B 0.0456 of the Bollinger range (lower 14.1234, mid 14.743, upper 15.3626).
- ADX(14) is 20.5781, indicating a developing trend (20-25).
- Stochastic %K 19.375 is below %D 22.0517.
- ATR(14) is 0.4436 (3.13% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
