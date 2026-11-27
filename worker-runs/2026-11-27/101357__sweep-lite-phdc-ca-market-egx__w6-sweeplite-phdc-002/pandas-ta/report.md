# Technical snapshot — PHDC.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 4591 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 11.35 |
| High | 11.5 |
| Low | 11.23 |
| Close | 11.34 |
| RSI(14) | 42.5895 |
| MACD | -0.2667 |
| MACD signal | -0.2823 |
| MACD histogram | 0.0156 |
| EMA(20) | 11.6838 |
| EMA(50) | 12.3274 |
| EMA(200) | 12.2063 |
| ADX(14) | 25.4036 |
| Bollinger upper | 12.5217 |
| Bollinger mid | 11.5555 |
| Bollinger lower | 10.5893 |
| Bollinger %B | 0.3885 |
| ATR(14) | 0.5389 |
| Stochastic %K | 29.4807 |
| Stochastic %D | 33.7883 |

## Trend read (facts only)

- Close 11.34 is below EMA_20 11.6838 (-2.94%).
- Close 11.34 is below EMA_50 12.3274 (-8.01%).
- Close 11.34 is below EMA_200 12.2063 (-7.10%).
- RSI(14) is 42.5895, in the neutral zone (30-70).
- MACD -0.2667 is above its signal line -0.2823 (histogram 0.0156).
- Price sits at %B 0.3885 of the Bollinger range (lower 10.5893, mid 11.5555, upper 12.5217).
- ADX(14) is 25.4036, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 29.4807 is below %D 33.7883.
- ATR(14) is 0.5389 (4.75% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
