# Technical snapshot — EGAL.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6533 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 302.0 |
| High | 302.0 |
| Low | 302.0 |
| Close | 302.0 |
| RSI(14) | 41.7083 |
| MACD | -4.1006 |
| MACD signal | -3.4884 |
| MACD histogram | -0.6123 |
| EMA(20) | 310.5405 |
| EMA(50) | 318.3994 |
| EMA(200) | 298.3932 |
| ADX(14) | 26.5319 |
| Bollinger upper | 328.8378 |
| Bollinger mid | 310.295 |
| Bollinger lower | 291.7522 |
| Bollinger %B | 0.2763 |
| ATR(14) | 9.1358 |
| Stochastic %K | 18.4069 |
| Stochastic %D | 24.1167 |

## Trend read (facts only)

- Close 302.0 is below EMA_20 310.5405 (-2.75%).
- Close 302.0 is below EMA_50 318.3994 (-5.15%).
- Close 302.0 is above EMA_200 298.3932 (+1.21%).
- RSI(14) is 41.7083, in the neutral zone (30-70).
- MACD -4.1006 is below its signal line -3.4884 (histogram -0.6123).
- Price sits at %B 0.2763 of the Bollinger range (lower 291.7522, mid 310.295, upper 328.8378).
- ADX(14) is 26.5319, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 18.4069 is below %D 24.1167.
- ATR(14) is 9.1358 (3.03% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
