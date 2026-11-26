# Technical snapshot — AMOC.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5068 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 12.25 |
| High | 12.29 |
| Low | 11.73 |
| Close | 11.9 |
| RSI(14) | 32.2554 |
| MACD | -0.2612 |
| MACD signal | -0.1134 |
| MACD histogram | -0.1478 |
| EMA(20) | 12.9712 |
| EMA(50) | 12.8969 |
| EMA(200) | 10.613 |
| ADX(14) | 13.1315 |
| Bollinger upper | 14.2619 |
| Bollinger mid | 13.172 |
| Bollinger lower | 12.0821 |
| Bollinger %B | -0.0835 |
| ATR(14) | 0.5477 |
| Stochastic %K | 8.2003 |
| Stochastic %D | 8.3101 |

## Trend read (facts only)

- Close 11.9 is below EMA_20 12.9712 (-8.26%).
- Close 11.9 is below EMA_50 12.8969 (-7.73%).
- Close 11.9 is above EMA_200 10.613 (+12.13%).
- RSI(14) is 32.2554, in the neutral zone (30-70).
- MACD -0.2612 is below its signal line -0.1134 (histogram -0.1478).
- Price sits at %B -0.0835 of the Bollinger range (lower 12.0821, mid 13.172, upper 14.2619).
- ADX(14) is 13.1315, indicating a weak / no clear trend (< 20).
- Stochastic %K 8.2003 is below %D 8.3101.
- ATR(14) is 0.5477 (4.60% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
