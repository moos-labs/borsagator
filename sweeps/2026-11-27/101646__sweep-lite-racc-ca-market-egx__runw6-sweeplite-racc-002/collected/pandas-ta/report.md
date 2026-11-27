# Technical snapshot — RACC.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 2255 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 7.51 |
| High | 7.96 |
| Low | 7.5 |
| Close | 7.8 |
| RSI(14) | 46.2969 |
| MACD | -0.1702 |
| MACD signal | -0.1916 |
| MACD histogram | 0.0215 |
| EMA(20) | 7.8797 |
| EMA(50) | 8.3479 |
| EMA(200) | 8.9382 |
| ADX(14) | 40.9897 |
| Bollinger upper | 8.4603 |
| Bollinger mid | 7.8065 |
| Bollinger lower | 7.1527 |
| Bollinger %B | 0.495 |
| ATR(14) | 0.3916 |
| Stochastic %K | 45.7023 |
| Stochastic %D | 45.203 |

## Trend read (facts only)

- Close 7.8 is below EMA_20 7.8797 (-1.01%).
- Close 7.8 is below EMA_50 8.3479 (-6.56%).
- Close 7.8 is below EMA_200 8.9382 (-12.73%).
- RSI(14) is 46.2969, in the neutral zone (30-70).
- MACD -0.1702 is above its signal line -0.1916 (histogram 0.0215).
- Price sits at %B 0.495 of the Bollinger range (lower 7.1527, mid 7.8065, upper 8.4603).
- ADX(14) is 40.9897, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 45.7023 is above %D 45.203.
- ATR(14) is 0.3916 (5.02% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
