# Technical snapshot — CLHO.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2461 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 14.13 |
| High | 14.13 |
| Low | 14.13 |
| Close | 14.13 |
| RSI(14) | 49.6905 |
| MACD | -0.0873 |
| MACD signal | -0.1686 |
| MACD histogram | 0.0813 |
| EMA(20) | 14.0572 |
| EMA(50) | 14.5713 |
| EMA(200) | 14.478 |
| ADX(14) | 25.6758 |
| Bollinger upper | 14.8007 |
| Bollinger mid | 13.892 |
| Bollinger lower | 12.9833 |
| Bollinger %B | 0.6309 |
| ATR(14) | 0.5465 |
| Stochastic %K | 51.3863 |
| Stochastic %D | 50.1195 |

## Trend read (facts only)

- Close 14.13 is above EMA_20 14.0572 (+0.52%).
- Close 14.13 is below EMA_50 14.5713 (-3.03%).
- Close 14.13 is below EMA_200 14.478 (-2.40%).
- RSI(14) is 49.6905, in the neutral zone (30-70).
- MACD -0.0873 is above its signal line -0.1686 (histogram 0.0813).
- Price sits at %B 0.6309 of the Bollinger range (lower 12.9833, mid 13.892, upper 14.8007).
- ADX(14) is 25.6758, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 51.3863 is above %D 50.1195.
- ATR(14) is 0.5465 (3.87% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
