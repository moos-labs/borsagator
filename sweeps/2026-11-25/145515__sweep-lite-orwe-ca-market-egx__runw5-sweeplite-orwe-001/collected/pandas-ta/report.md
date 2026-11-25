# Technical snapshot — ORWE.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6533 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 24.7 |
| High | 25.48 |
| Low | 24.65 |
| Close | 24.7 |
| RSI(14) | 43.4947 |
| MACD | -0.1999 |
| MACD signal | -0.1897 |
| MACD histogram | -0.0102 |
| EMA(20) | 25.235 |
| EMA(50) | 25.5438 |
| EMA(200) | 24.6192 |
| ADX(14) | 19.1267 |
| Bollinger upper | 26.7766 |
| Bollinger mid | 24.9225 |
| Bollinger lower | 23.0684 |
| Bollinger %B | 0.44 |
| ATR(14) | 0.9528 |
| Stochastic %K | 36.1464 |
| Stochastic %D | 48.8698 |

## Trend read (facts only)

- Close 24.7 is below EMA_20 25.235 (-2.12%).
- Close 24.7 is below EMA_50 25.5438 (-3.30%).
- Close 24.7 is above EMA_200 24.6192 (+0.33%).
- RSI(14) is 43.4947, in the neutral zone (30-70).
- MACD -0.1999 is below its signal line -0.1897 (histogram -0.0102).
- Price sits at %B 0.44 of the Bollinger range (lower 23.0684, mid 24.9225, upper 26.7766).
- ADX(14) is 19.1267, indicating a weak / no clear trend (< 20).
- Stochastic %K 36.1464 is below %D 48.8698.
- ATR(14) is 0.9528 (3.86% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
