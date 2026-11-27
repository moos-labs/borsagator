# Technical snapshot — EGAS.CA

- Last session: **2026-11-25**
- Data used: 1931 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6423 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 49.1 |
| High | 49.5 |
| Low | 48.5 |
| Close | 48.58 |
| RSI(14) | 46.2593 |
| MACD | -0.465 |
| MACD signal | -0.7045 |
| MACD histogram | 0.2395 |
| EMA(20) | 49.2525 |
| EMA(50) | 50.9158 |
| EMA(200) | 50.0925 |
| ADX(14) | 29.6212 |
| Bollinger upper | 52.031 |
| Bollinger mid | 48.4565 |
| Bollinger lower | 44.882 |
| Bollinger %B | 0.5173 |
| ATR(14) | 2.4732 |
| Stochastic %K | 20.4608 |
| Stochastic %D | 25.7034 |

## Trend read (facts only)

- Close 48.58 is below EMA_20 49.2525 (-1.37%).
- Close 48.58 is below EMA_50 50.9158 (-4.59%).
- Close 48.58 is below EMA_200 50.0925 (-3.02%).
- RSI(14) is 46.2593, in the neutral zone (30-70).
- MACD -0.465 is above its signal line -0.7045 (histogram 0.2395).
- Price sits at %B 0.5173 of the Bollinger range (lower 44.882, mid 48.4565, upper 52.031).
- ADX(14) is 29.6212, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 20.4608 is below %D 25.7034.
- ATR(14) is 2.4732 (5.09% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
