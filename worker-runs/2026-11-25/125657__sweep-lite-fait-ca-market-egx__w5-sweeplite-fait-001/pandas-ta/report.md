# Technical snapshot — FAIT.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6112 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 45.37 |
| High | 45.97 |
| Low | 44.8 |
| Close | 45.85 |
| RSI(14) | 57.2218 |
| MACD | 0.5502 |
| MACD signal | 0.4185 |
| MACD histogram | 0.1317 |
| EMA(20) | 44.8223 |
| EMA(50) | 44.0478 |
| EMA(200) | 39.6087 |
| ADX(14) | 21.3106 |
| Bollinger upper | 47.1797 |
| Bollinger mid | 44.452 |
| Bollinger lower | 41.7243 |
| Bollinger %B | 0.7563 |
| ATR(14) | 1.498 |
| Stochastic %K | 60.4461 |
| Stochastic %D | 60.322 |

## Trend read (facts only)

- Close 45.85 is above EMA_20 44.8223 (+2.29%).
- Close 45.85 is above EMA_50 44.0478 (+4.09%).
- Close 45.85 is above EMA_200 39.6087 (+15.76%).
- RSI(14) is 57.2218, in the neutral zone (30-70).
- MACD 0.5502 is above its signal line 0.4185 (histogram 0.1317).
- Price sits at %B 0.7563 of the Bollinger range (lower 41.7243, mid 44.452, upper 47.1797).
- ADX(14) is 21.3106, indicating a developing trend (20-25).
- Stochastic %K 60.4461 is above %D 60.322.
- ATR(14) is 1.498 (3.27% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
