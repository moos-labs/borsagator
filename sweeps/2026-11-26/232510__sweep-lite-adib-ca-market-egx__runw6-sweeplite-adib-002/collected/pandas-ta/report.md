# Technical snapshot — ADIB.CA

- Last session: **2026-11-25**
- Data used: 1932 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6536 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 46.15 |
| High | 46.5 |
| Low | 45.5 |
| Close | 45.93 |
| RSI(14) | 42.7208 |
| MACD | -0.4521 |
| MACD signal | -0.2271 |
| MACD histogram | -0.225 |
| EMA(20) | 47.2471 |
| EMA(50) | 48.1016 |
| EMA(200) | 45.3151 |
| ADX(14) | 28.6098 |
| Bollinger upper | 50.6187 |
| Bollinger mid | 47.6205 |
| Bollinger lower | 44.6223 |
| Bollinger %B | 0.2181 |
| ATR(14) | 1.5346 |
| Stochastic %K | 27.8798 |
| Stochastic %D | 27.0994 |

## Trend read (facts only)

- Close 45.93 is below EMA_20 47.2471 (-2.79%).
- Close 45.93 is below EMA_50 48.1016 (-4.51%).
- Close 45.93 is above EMA_200 45.3151 (+1.36%).
- RSI(14) is 42.7208, in the neutral zone (30-70).
- MACD -0.4521 is below its signal line -0.2271 (histogram -0.225).
- Price sits at %B 0.2181 of the Bollinger range (lower 44.6223, mid 47.6205, upper 50.6187).
- ADX(14) is 28.6098, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 27.8798 is above %D 27.0994.
- ATR(14) is 1.5346 (3.34% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
