# Technical snapshot — ATQA.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2985 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 10.05 |
| High | 10.05 |
| Low | 10.05 |
| Close | 10.05 |
| RSI(14) | 47.2884 |
| MACD | -0.1338 |
| MACD signal | -0.2345 |
| MACD histogram | 0.1007 |
| EMA(20) | 10.0978 |
| EMA(50) | 10.4964 |
| EMA(200) | 10.2937 |
| ADX(14) | 26.6951 |
| Bollinger upper | 10.7325 |
| Bollinger mid | 9.782 |
| Bollinger lower | 8.8315 |
| Bollinger %B | 0.641 |
| ATR(14) | 0.5104 |
| Stochastic %K | 52.7823 |
| Stochastic %D | 58.2412 |

## Trend read (facts only)

- Close 10.05 is below EMA_20 10.0978 (-0.47%).
- Close 10.05 is below EMA_50 10.4964 (-4.25%).
- Close 10.05 is below EMA_200 10.2937 (-2.37%).
- RSI(14) is 47.2884, in the neutral zone (30-70).
- MACD -0.1338 is above its signal line -0.2345 (histogram 0.1007).
- Price sits at %B 0.641 of the Bollinger range (lower 8.8315, mid 9.782, upper 10.7325).
- ADX(14) is 26.6951, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 52.7823 is below %D 58.2412.
- ATR(14) is 0.5104 (5.08% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
