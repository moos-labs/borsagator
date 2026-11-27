# Technical snapshot — RMDA.CA

- Last session: **2026-11-26**
- Data used: 1687 rows (2019-12-11 → 2026-11-26), after dropping rows before 2019-01-01; 1687 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 5.05 |
| High | 5.08 |
| Low | 4.96 |
| Close | 5.01 |
| RSI(14) | 41.0427 |
| MACD | -0.0779 |
| MACD signal | -0.0419 |
| MACD histogram | -0.0359 |
| EMA(20) | 5.208 |
| EMA(50) | 5.3383 |
| EMA(200) | 5.0791 |
| ADX(14) | 23.9809 |
| Bollinger upper | 5.7751 |
| Bollinger mid | 5.275 |
| Bollinger lower | 4.7749 |
| Bollinger %B | 0.2351 |
| ATR(14) | 0.2134 |
| Stochastic %K | 14.5834 |
| Stochastic %D | 15.2472 |

## Trend read (facts only)

- Close 5.01 is below EMA_20 5.208 (-3.80%).
- Close 5.01 is below EMA_50 5.3383 (-6.15%).
- Close 5.01 is below EMA_200 5.0791 (-1.36%).
- RSI(14) is 41.0427, in the neutral zone (30-70).
- MACD -0.0779 is below its signal line -0.0419 (histogram -0.0359).
- Price sits at %B 0.2351 of the Bollinger range (lower 4.7749, mid 5.275, upper 5.7751).
- ADX(14) is 23.9809, indicating a developing trend (20-25).
- Stochastic %K 14.5834 is below %D 15.2472.
- ATR(14) is 0.2134 (4.26% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
