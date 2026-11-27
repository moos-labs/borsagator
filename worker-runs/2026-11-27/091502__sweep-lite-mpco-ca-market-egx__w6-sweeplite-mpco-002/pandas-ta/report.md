# Technical snapshot — MPCO.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 5842 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 1.88 |
| High | 1.9 |
| Low | 1.85 |
| Close | 1.87 |
| RSI(14) | 43.6308 |
| MACD | -0.0436 |
| MACD signal | -0.0423 |
| MACD histogram | -0.0013 |
| EMA(20) | 1.96 |
| EMA(50) | 2.0462 |
| EMA(200) | 1.9624 |
| ADX(14) | 17.782 |
| Bollinger upper | 2.2126 |
| Bollinger mid | 1.938 |
| Bollinger lower | 1.6634 |
| Bollinger %B | 0.3762 |
| ATR(14) | 0.1336 |
| Stochastic %K | 9.8333 |
| Stochastic %D | 16.0311 |

## Trend read (facts only)

- Close 1.87 is below EMA_20 1.96 (-4.59%).
- Close 1.87 is below EMA_50 2.0462 (-8.61%).
- Close 1.87 is below EMA_200 1.9624 (-4.71%).
- RSI(14) is 43.6308, in the neutral zone (30-70).
- MACD -0.0436 is below its signal line -0.0423 (histogram -0.0013).
- Price sits at %B 0.3762 of the Bollinger range (lower 1.6634, mid 1.938, upper 2.2126).
- ADX(14) is 17.782, indicating a weak / no clear trend (< 20).
- Stochastic %K 9.8333 is below %D 16.0311.
- ATR(14) is 0.1336 (7.14% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
