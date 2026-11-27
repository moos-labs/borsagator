# Technical snapshot — TMGH.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 4708 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 78.95 |
| High | 79.5 |
| Low | 78.3 |
| Close | 79.24 |
| RSI(14) | 39.6095 |
| MACD | -1.6179 |
| MACD signal | -1.4199 |
| MACD histogram | -0.198 |
| EMA(20) | 81.6615 |
| EMA(50) | 85.1102 |
| EMA(200) | 86.5716 |
| ADX(14) | 26.7684 |
| Bollinger upper | 86.3223 |
| Bollinger mid | 81.5095 |
| Bollinger lower | 76.6967 |
| Bollinger %B | 0.2642 |
| ATR(14) | 2.4082 |
| Stochastic %K | 17.9452 |
| Stochastic %D | 17.6555 |

## Trend read (facts only)

- Close 79.24 is below EMA_20 81.6615 (-2.97%).
- Close 79.24 is below EMA_50 85.1102 (-6.90%).
- Close 79.24 is below EMA_200 86.5716 (-8.47%).
- RSI(14) is 39.6095, in the neutral zone (30-70).
- MACD -1.6179 is below its signal line -1.4199 (histogram -0.198).
- Price sits at %B 0.2642 of the Bollinger range (lower 76.6967, mid 81.5095, upper 86.3223).
- ADX(14) is 26.7684, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 17.9452 is above %D 17.6555.
- ATR(14) is 2.4082 (3.04% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
