# Technical snapshot — OLFI.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 2423 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 20.38 |
| High | 20.6 |
| Low | 20.07 |
| Close | 20.23 |
| RSI(14) | 49.4261 |
| MACD | -0.0176 |
| MACD signal | -0.0979 |
| MACD histogram | 0.0803 |
| EMA(20) | 20.2043 |
| EMA(50) | 20.687 |
| EMA(200) | 21.6909 |
| ADX(14) | 30.1871 |
| Bollinger upper | 21.3244 |
| Bollinger mid | 19.99 |
| Bollinger lower | 18.6556 |
| Bollinger %B | 0.5899 |
| ATR(14) | 0.6594 |
| Stochastic %K | 55.2314 |
| Stochastic %D | 60.0657 |

## Trend read (facts only)

- Close 20.23 is above EMA_20 20.2043 (+0.13%).
- Close 20.23 is below EMA_50 20.687 (-2.21%).
- Close 20.23 is below EMA_200 21.6909 (-6.74%).
- RSI(14) is 49.4261, in the neutral zone (30-70).
- MACD -0.0176 is above its signal line -0.0979 (histogram 0.0803).
- Price sits at %B 0.5899 of the Bollinger range (lower 18.6556, mid 19.99, upper 21.3244).
- ADX(14) is 30.1871, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 55.2314 is below %D 60.0657.
- ATR(14) is 0.6594 (3.26% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
