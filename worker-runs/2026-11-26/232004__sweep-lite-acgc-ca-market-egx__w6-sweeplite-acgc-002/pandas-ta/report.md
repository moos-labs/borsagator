# Technical snapshot — ACGC.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5951 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 13.77 |
| High | 13.99 |
| Low | 13.5 |
| Close | 13.99 |
| RSI(14) | 58.375 |
| MACD | 0.093 |
| MACD signal | 0.0456 |
| MACD histogram | 0.0474 |
| EMA(20) | 13.5142 |
| EMA(50) | 13.3559 |
| EMA(200) | 11.3907 |
| ADX(14) | 21.7982 |
| Bollinger upper | 14.2252 |
| Bollinger mid | 13.414 |
| Bollinger lower | 12.6028 |
| Bollinger %B | 0.855 |
| ATR(14) | 0.5143 |
| Stochastic %K | 67.5571 |
| Stochastic %D | 65.2473 |

## Trend read (facts only)

- Close 13.99 is above EMA_20 13.5142 (+3.52%).
- Close 13.99 is above EMA_50 13.3559 (+4.75%).
- Close 13.99 is above EMA_200 11.3907 (+22.82%).
- RSI(14) is 58.375, in the neutral zone (30-70).
- MACD 0.093 is above its signal line 0.0456 (histogram 0.0474).
- Price sits at %B 0.855 of the Bollinger range (lower 12.6028, mid 13.414, upper 14.2252).
- ADX(14) is 21.7982, indicating a developing trend (20-25).
- Stochastic %K 67.5571 is above %D 65.2473.
- ATR(14) is 0.5143 (3.68% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
