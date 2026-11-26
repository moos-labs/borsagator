# Technical snapshot — ARCC.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 3089 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 67.03 |
| High | 67.45 |
| Low | 65.95 |
| Close | 65.95 |
| RSI(14) | 46.5758 |
| MACD | -0.0354 |
| MACD signal | 0.0989 |
| MACD histogram | -0.1343 |
| EMA(20) | 66.9924 |
| EMA(50) | 67.1043 |
| EMA(200) | 60.2045 |
| ADX(14) | 14.0583 |
| Bollinger upper | 71.5479 |
| Bollinger mid | 66.7785 |
| Bollinger lower | 62.0091 |
| Bollinger %B | 0.4131 |
| ATR(14) | 2.6516 |
| Stochastic %K | 26.3622 |
| Stochastic %D | 31.4658 |

## Trend read (facts only)

- Close 65.95 is below EMA_20 66.9924 (-1.56%).
- Close 65.95 is below EMA_50 67.1043 (-1.72%).
- Close 65.95 is above EMA_200 60.2045 (+9.54%).
- RSI(14) is 46.5758, in the neutral zone (30-70).
- MACD -0.0354 is below its signal line 0.0989 (histogram -0.1343).
- Price sits at %B 0.4131 of the Bollinger range (lower 62.0091, mid 66.7785, upper 71.5479).
- ADX(14) is 14.0583, indicating a weak / no clear trend (< 20).
- Stochastic %K 26.3622 is below %D 31.4658.
- ATR(14) is 2.6516 (4.02% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
