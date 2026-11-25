# Technical snapshot — OLFI.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2421 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 20.38 |
| High | 20.38 |
| Low | 20.38 |
| Close | 20.38 |
| RSI(14) | 51.6352 |
| MACD | -0.0343 |
| MACD signal | -0.1429 |
| MACD histogram | 0.1087 |
| EMA(20) | 20.1829 |
| EMA(50) | 20.719 |
| EMA(200) | 21.7189 |
| ADX(14) | 33.9301 |
| Bollinger upper | 21.2864 |
| Bollinger mid | 19.872 |
| Bollinger lower | 18.4576 |
| Bollinger %B | 0.6796 |
| ATR(14) | 0.6847 |
| Stochastic %K | 62.2934 |
| Stochastic %D | 63.0386 |

## Trend read (facts only)

- Close 20.38 is above EMA_20 20.1829 (+0.98%).
- Close 20.38 is below EMA_50 20.719 (-1.64%).
- Close 20.38 is below EMA_200 21.7189 (-6.16%).
- RSI(14) is 51.6352, in the neutral zone (30-70).
- MACD -0.0343 is above its signal line -0.1429 (histogram 0.1087).
- Price sits at %B 0.6796 of the Bollinger range (lower 18.4576, mid 19.872, upper 21.2864).
- ADX(14) is 33.9301, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 62.2934 is below %D 63.0386.
- ATR(14) is 0.6847 (3.36% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
