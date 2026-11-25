# Technical snapshot — LCSW.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 4686 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 40.44 |
| High | 40.44 |
| Low | 40.44 |
| Close | 40.44 |
| RSI(14) | 62.7967 |
| MACD | 1.6184 |
| MACD signal | 1.566 |
| MACD histogram | 0.0524 |
| EMA(20) | 38.2364 |
| EMA(50) | 36.0547 |
| EMA(200) | 31.6161 |
| ADX(14) | 18.6224 |
| Bollinger upper | 42.7599 |
| Bollinger mid | 38.0995 |
| Bollinger lower | 33.4391 |
| Bollinger %B | 0.7511 |
| ATR(14) | 1.8666 |
| Stochastic %K | 70.8548 |
| Stochastic %D | 68.0441 |

## Trend read (facts only)

- Close 40.44 is above EMA_20 38.2364 (+5.76%).
- Close 40.44 is above EMA_50 36.0547 (+12.16%).
- Close 40.44 is above EMA_200 31.6161 (+27.91%).
- RSI(14) is 62.7967, in the neutral zone (30-70).
- MACD 1.6184 is above its signal line 1.566 (histogram 0.0524).
- Price sits at %B 0.7511 of the Bollinger range (lower 33.4391, mid 38.0995, upper 42.7599).
- ADX(14) is 18.6224, indicating a weak / no clear trend (< 20).
- Stochastic %K 70.8548 is above %D 68.0441.
- ATR(14) is 1.8666 (4.62% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
