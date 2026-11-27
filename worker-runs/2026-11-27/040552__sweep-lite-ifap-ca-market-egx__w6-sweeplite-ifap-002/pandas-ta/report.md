# Technical snapshot — IFAP.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5634 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 15.79 |
| High | 16.39 |
| Low | 15.8 |
| Close | 15.82 |
| RSI(14) | 38.074 |
| MACD | -0.5779 |
| MACD signal | -0.5388 |
| MACD histogram | -0.039 |
| EMA(20) | 16.6887 |
| EMA(50) | 17.7515 |
| EMA(200) | 18.9667 |
| ADX(14) | 30.8753 |
| Bollinger upper | 18.346 |
| Bollinger mid | 16.6215 |
| Bollinger lower | 14.897 |
| Bollinger %B | 0.2676 |
| ATR(14) | 0.8291 |
| Stochastic %K | 14.2165 |
| Stochastic %D | 16.3846 |

## Trend read (facts only)

- Close 15.82 is below EMA_20 16.6887 (-5.21%).
- Close 15.82 is below EMA_50 17.7515 (-10.88%).
- Close 15.82 is below EMA_200 18.9667 (-16.59%).
- RSI(14) is 38.074, in the neutral zone (30-70).
- MACD -0.5779 is below its signal line -0.5388 (histogram -0.039).
- Price sits at %B 0.2676 of the Bollinger range (lower 14.897, mid 16.6215, upper 18.346).
- ADX(14) is 30.8753, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 14.2165 is below %D 16.3846.
- ATR(14) is 0.8291 (5.24% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
