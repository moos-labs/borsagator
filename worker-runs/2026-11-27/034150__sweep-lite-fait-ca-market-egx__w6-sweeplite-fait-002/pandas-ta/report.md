# Technical snapshot — FAIT.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6113 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 45.85 |
| High | 46.7 |
| Low | 45.32 |
| Close | 46.15 |
| RSI(14) | 58.6795 |
| MACD | 0.5855 |
| MACD signal | 0.4519 |
| MACD histogram | 0.1336 |
| EMA(20) | 44.9488 |
| EMA(50) | 44.1302 |
| EMA(200) | 39.6737 |
| ADX(14) | 19.7987 |
| Bollinger upper | 47.3075 |
| Bollinger mid | 44.6325 |
| Bollinger lower | 41.9575 |
| Bollinger %B | 0.7836 |
| ATR(14) | 1.4896 |
| Stochastic %K | 65.5392 |
| Stochastic %D | 61.8288 |

## Trend read (facts only)

- Close 46.15 is above EMA_20 44.9488 (+2.67%).
- Close 46.15 is above EMA_50 44.1302 (+4.58%).
- Close 46.15 is above EMA_200 39.6737 (+16.32%).
- RSI(14) is 58.6795, in the neutral zone (30-70).
- MACD 0.5855 is above its signal line 0.4519 (histogram 0.1336).
- Price sits at %B 0.7836 of the Bollinger range (lower 41.9575, mid 44.6325, upper 47.3075).
- ADX(14) is 19.7987, indicating a weak / no clear trend (< 20).
- Stochastic %K 65.5392 is above %D 61.8288.
- ATR(14) is 1.4896 (3.23% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
