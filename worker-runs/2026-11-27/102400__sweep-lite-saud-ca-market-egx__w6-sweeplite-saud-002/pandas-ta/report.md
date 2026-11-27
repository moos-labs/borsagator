# Technical snapshot — SAUD.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 6530 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 21.95 |
| High | 22.41 |
| Low | 21.7 |
| Close | 21.77 |
| RSI(14) | 47.51 |
| MACD | 0.1907 |
| MACD signal | 0.1851 |
| MACD histogram | 0.0056 |
| EMA(20) | 22.0921 |
| EMA(50) | 22.1074 |
| EMA(200) | 20.8905 |
| ADX(14) | 16.0712 |
| Bollinger upper | 24.0559 |
| Bollinger mid | 21.821 |
| Bollinger lower | 19.5861 |
| Bollinger %B | 0.4886 |
| ATR(14) | 0.854 |
| Stochastic %K | 51.2153 |
| Stochastic %D | 60.1246 |

## Trend read (facts only)

- Close 21.77 is below EMA_20 22.0921 (-1.46%).
- Close 21.77 is below EMA_50 22.1074 (-1.53%).
- Close 21.77 is above EMA_200 20.8905 (+4.21%).
- RSI(14) is 47.51, in the neutral zone (30-70).
- MACD 0.1907 is above its signal line 0.1851 (histogram 0.0056).
- Price sits at %B 0.4886 of the Bollinger range (lower 19.5861, mid 21.821, upper 24.0559).
- ADX(14) is 16.0712, indicating a weak / no clear trend (< 20).
- Stochastic %K 51.2153 is below %D 60.1246.
- ATR(14) is 0.854 (3.92% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
