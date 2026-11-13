# Technical snapshot — NVDA

- Last session: **2026-11-12**
- Data used: 1978 rows (2019-01-02 → 2026-11-12), after dropping rows before 2019-01-01; 6996 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 151.01 |
| High | 167.14 |
| Low | 148.8 |
| Close | 166.19 |
| RSI(14) | 25.9908 |
| MACD | -13.2421 |
| MACD signal | -9.0796 |
| MACD histogram | -4.1624 |
| EMA(20) | 196.4679 |
| EMA(50) | 208.6566 |
| EMA(200) | 203.7939 |
| ADX(14) | 39.4835 |
| Bollinger upper | 236.8281 |
| Bollinger mid | 201.2525 |
| Bollinger lower | 165.6769 |
| Bollinger %B | 0.0072 |
| ATR(14) | 9.8559 |
| Stochastic %K | 14.8215 |
| Stochastic %D | 12.8021 |

## Trend read (facts only)

- Close 166.19 is below EMA_20 196.4679 (-15.41%).
- Close 166.19 is below EMA_50 208.6566 (-20.35%).
- Close 166.19 is below EMA_200 203.7939 (-18.45%).
- RSI(14) is 25.9908, in the oversold zone (<= 30).
- MACD -13.2421 is below its signal line -9.0796 (histogram -4.1624).
- Price sits at %B 0.0072 of the Bollinger range (lower 165.6769, mid 201.2525, upper 236.8281).
- ADX(14) is 39.4835, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 14.8215 is above %D 12.8021.
- ATR(14) is 9.8559 (5.93% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
