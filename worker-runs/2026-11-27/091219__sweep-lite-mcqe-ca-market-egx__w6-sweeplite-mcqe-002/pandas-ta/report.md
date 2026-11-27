# Technical snapshot — MCQE.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 6137 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 174.31 |
| High | 174.69 |
| Low | 170.3 |
| Close | 173.49 |
| RSI(14) | 47.1541 |
| MACD | -1.1315 |
| MACD signal | -1.6099 |
| MACD histogram | 0.4784 |
| EMA(20) | 175.6094 |
| EMA(50) | 182.3265 |
| EMA(200) | 177.6615 |
| ADX(14) | 11.4754 |
| Bollinger upper | 189.3912 |
| Bollinger mid | 174.5635 |
| Bollinger lower | 159.7358 |
| Bollinger %B | 0.4638 |
| ATR(14) | 9.1587 |
| Stochastic %K | 21.7939 |
| Stochastic %D | 26.6562 |

## Trend read (facts only)

- Close 173.49 is below EMA_20 175.6094 (-1.21%).
- Close 173.49 is below EMA_50 182.3265 (-4.85%).
- Close 173.49 is below EMA_200 177.6615 (-2.35%).
- RSI(14) is 47.1541, in the neutral zone (30-70).
- MACD -1.1315 is above its signal line -1.6099 (histogram 0.4784).
- Price sits at %B 0.4638 of the Bollinger range (lower 159.7358, mid 174.5635, upper 189.3912).
- ADX(14) is 11.4754, indicating a weak / no clear trend (< 20).
- Stochastic %K 21.7939 is below %D 26.6562.
- ATR(14) is 9.1587 (5.28% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
