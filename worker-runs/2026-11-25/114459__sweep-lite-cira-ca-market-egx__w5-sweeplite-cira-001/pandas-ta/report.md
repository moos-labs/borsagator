# Technical snapshot — CIRA.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5419 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 37.71 |
| High | 39.0 |
| Low | 37.8 |
| Close | 38.45 |
| RSI(14) | 54.9713 |
| MACD | 0.4019 |
| MACD signal | 0.3455 |
| MACD histogram | 0.0565 |
| EMA(20) | 37.7036 |
| EMA(50) | 37.1027 |
| EMA(200) | 30.4778 |
| ADX(14) | 14.5995 |
| Bollinger upper | 40.479 |
| Bollinger mid | 37.3225 |
| Bollinger lower | 34.166 |
| Bollinger %B | 0.6786 |
| ATR(14) | 1.6181 |
| Stochastic %K | 57.4283 |
| Stochastic %D | 61.3316 |

## Trend read (facts only)

- Close 38.45 is above EMA_20 37.7036 (+1.98%).
- Close 38.45 is above EMA_50 37.1027 (+3.63%).
- Close 38.45 is above EMA_200 30.4778 (+26.16%).
- RSI(14) is 54.9713, in the neutral zone (30-70).
- MACD 0.4019 is above its signal line 0.3455 (histogram 0.0565).
- Price sits at %B 0.6786 of the Bollinger range (lower 34.166, mid 37.3225, upper 40.479).
- ADX(14) is 14.5995, indicating a weak / no clear trend (< 20).
- Stochastic %K 57.4283 is below %D 61.3316.
- ATR(14) is 1.6181 (4.21% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
