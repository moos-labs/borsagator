# Technical snapshot — POUL.CA

- Last session: **2026-11-16**
- Data used: 1923 rows (2019-01-01 → 2026-11-16), after dropping rows before 2019-01-01; 6523 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 10.0 |
| High | 8.39 |
| Low | 8.01 |
| Close | 8.02 |
| RSI(14) | 18.4369 |
| MACD | -2.0693 |
| MACD signal | -2.7461 |
| MACD histogram | 0.6769 |
| EMA(20) | 10.699 |
| EMA(50) | 17.1184 |
| EMA(200) | 26.8356 |
| ADX(14) | 53.0624 |
| Bollinger upper | 10.7911 |
| Bollinger mid | 9.7485 |
| Bollinger lower | 8.7059 |
| Bollinger %B | -0.3289 |
| ATR(14) | 0.7113 |
| Stochastic %K | 57.3722 |
| Stochastic %D | 77.8566 |

## Trend read (facts only)

- Close 8.02 is below EMA_20 10.699 (-25.04%).
- Close 8.02 is below EMA_50 17.1184 (-53.15%).
- Close 8.02 is below EMA_200 26.8356 (-70.11%).
- RSI(14) is 18.4369, in the oversold zone (<= 30).
- MACD -2.0693 is above its signal line -2.7461 (histogram 0.6769).
- Price sits at %B -0.3289 of the Bollinger range (lower 8.7059, mid 9.7485, upper 10.7911).
- ADX(14) is 53.0624, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 57.3722 is below %D 77.8566.
- ATR(14) is 0.7113 (8.87% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
