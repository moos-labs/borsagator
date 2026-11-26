# Technical snapshot — ATQA.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 2986 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 9.91 |
| High | 9.98 |
| Low | 9.63 |
| Close | 9.74 |
| RSI(14) | 42.6268 |
| MACD | -0.1489 |
| MACD signal | -0.2174 |
| MACD histogram | 0.0685 |
| EMA(20) | 10.0637 |
| EMA(50) | 10.4667 |
| EMA(200) | 10.2882 |
| ADX(14) | 27.0341 |
| Bollinger upper | 10.7359 |
| Bollinger mid | 9.794 |
| Bollinger lower | 8.8521 |
| Bollinger %B | 0.4713 |
| ATR(14) | 0.5039 |
| Stochastic %K | 41.6864 |
| Stochastic %D | 50.8166 |

## Trend read (facts only)

- Close 9.74 is below EMA_20 10.0637 (-3.22%).
- Close 9.74 is below EMA_50 10.4667 (-6.94%).
- Close 9.74 is below EMA_200 10.2882 (-5.33%).
- RSI(14) is 42.6268, in the neutral zone (30-70).
- MACD -0.1489 is above its signal line -0.2174 (histogram 0.0685).
- Price sits at %B 0.4713 of the Bollinger range (lower 8.8521, mid 9.794, upper 10.7359).
- ADX(14) is 27.0341, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 41.6864 is below %D 50.8166.
- ATR(14) is 0.5039 (5.17% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
