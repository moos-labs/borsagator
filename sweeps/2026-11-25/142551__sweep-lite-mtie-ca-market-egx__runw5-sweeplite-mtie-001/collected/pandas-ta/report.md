# Technical snapshot — MTIE.CA

- Last session: **2026-11-24**
- Data used: 1931 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2370 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 6.28 |
| High | 6.9 |
| Low | 6.35 |
| Close | 6.6 |
| RSI(14) | 42.431 |
| MACD | -0.2706 |
| MACD signal | -0.2462 |
| MACD histogram | -0.0244 |
| EMA(20) | 6.8569 |
| EMA(50) | 7.3753 |
| EMA(200) | 8.026 |
| ADX(14) | 25.9904 |
| Bollinger upper | 7.5252 |
| Bollinger mid | 6.8585 |
| Bollinger lower | 6.1918 |
| Bollinger %B | 0.3061 |
| ATR(14) | 0.3671 |
| Stochastic %K | 14.6497 |
| Stochastic %D | 14.6165 |

## Trend read (facts only)

- Close 6.6 is below EMA_20 6.8569 (-3.75%).
- Close 6.6 is below EMA_50 7.3753 (-10.51%).
- Close 6.6 is below EMA_200 8.026 (-17.77%).
- RSI(14) is 42.431, in the neutral zone (30-70).
- MACD -0.2706 is below its signal line -0.2462 (histogram -0.0244).
- Price sits at %B 0.3061 of the Bollinger range (lower 6.1918, mid 6.8585, upper 7.5252).
- ADX(14) is 25.9904, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 14.6497 is above %D 14.6165.
- ATR(14) is 0.3671 (5.56% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
