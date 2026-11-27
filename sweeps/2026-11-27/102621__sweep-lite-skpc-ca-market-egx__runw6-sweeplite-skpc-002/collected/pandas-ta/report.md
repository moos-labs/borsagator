# Technical snapshot — SKPC.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 5345 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 14.76 |
| High | 15.03 |
| Low | 14.58 |
| Close | 14.7 |
| RSI(14) | 46.1972 |
| MACD | -0.2624 |
| MACD signal | -0.2976 |
| MACD histogram | 0.0352 |
| EMA(20) | 14.763 |
| EMA(50) | 15.3788 |
| EMA(200) | 16.6906 |
| ADX(14) | 18.1003 |
| Bollinger upper | 15.3666 |
| Bollinger mid | 14.7495 |
| Bollinger lower | 14.1324 |
| Bollinger %B | 0.4599 |
| ATR(14) | 0.4789 |
| Stochastic %K | 43.5417 |
| Stochastic %D | 31.875 |

## Trend read (facts only)

- Close 14.7 is below EMA_20 14.763 (-0.43%).
- Close 14.7 is below EMA_50 15.3788 (-4.41%).
- Close 14.7 is below EMA_200 16.6906 (-11.93%).
- RSI(14) is 46.1972, in the neutral zone (30-70).
- MACD -0.2624 is above its signal line -0.2976 (histogram 0.0352).
- Price sits at %B 0.4599 of the Bollinger range (lower 14.1324, mid 14.7495, upper 15.3666).
- ADX(14) is 18.1003, indicating a weak / no clear trend (< 20).
- Stochastic %K 43.5417 is above %D 31.875.
- ATR(14) is 0.4789 (3.26% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
