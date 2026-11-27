# Technical snapshot — JUFO.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 4068 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 21.85 |
| High | 22.08 |
| Low | 21.57 |
| Close | 21.72 |
| RSI(14) | 35.4497 |
| MACD | -0.5981 |
| MACD signal | -0.4249 |
| MACD histogram | -0.1732 |
| EMA(20) | 23.0343 |
| EMA(50) | 24.0921 |
| EMA(200) | 26.2754 |
| ADX(14) | 27.7957 |
| Bollinger upper | 25.273 |
| Bollinger mid | 23.2505 |
| Bollinger lower | 21.228 |
| Bollinger %B | 0.1216 |
| ATR(14) | 0.8524 |
| Stochastic %K | 5.206 |
| Stochastic %D | 6.3161 |

## Trend read (facts only)

- Close 21.72 is below EMA_20 23.0343 (-5.71%).
- Close 21.72 is below EMA_50 24.0921 (-9.85%).
- Close 21.72 is below EMA_200 26.2754 (-17.34%).
- RSI(14) is 35.4497, in the neutral zone (30-70).
- MACD -0.5981 is below its signal line -0.4249 (histogram -0.1732).
- Price sits at %B 0.1216 of the Bollinger range (lower 21.228, mid 23.2505, upper 25.273).
- ADX(14) is 27.7957, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 5.206 is below %D 6.3161.
- ATR(14) is 0.8524 (3.92% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
