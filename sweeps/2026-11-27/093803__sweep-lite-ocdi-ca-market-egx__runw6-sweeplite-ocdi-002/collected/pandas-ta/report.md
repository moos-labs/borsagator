# Technical snapshot — OCDI.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 6540 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 23.6 |
| High | 23.77 |
| Low | 22.98 |
| Close | 23.6 |
| RSI(14) | 42.8318 |
| MACD | -0.5227 |
| MACD signal | -0.4471 |
| MACD histogram | -0.0756 |
| EMA(20) | 24.5092 |
| EMA(50) | 25.6779 |
| EMA(200) | 26.4091 |
| ADX(14) | 30.2757 |
| Bollinger upper | 26.8798 |
| Bollinger mid | 24.4575 |
| Bollinger lower | 22.0352 |
| Bollinger %B | 0.323 |
| ATR(14) | 1.1332 |
| Stochastic %K | 33.4822 |
| Stochastic %D | 30.6382 |

## Trend read (facts only)

- Close 23.6 is below EMA_20 24.5092 (-3.71%).
- Close 23.6 is below EMA_50 25.6779 (-8.09%).
- Close 23.6 is below EMA_200 26.4091 (-10.64%).
- RSI(14) is 42.8318, in the neutral zone (30-70).
- MACD -0.5227 is below its signal line -0.4471 (histogram -0.0756).
- Price sits at %B 0.323 of the Bollinger range (lower 22.0352, mid 24.4575, upper 26.8798).
- ADX(14) is 30.2757, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 33.4822 is above %D 30.6382.
- ATR(14) is 1.1332 (4.80% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
