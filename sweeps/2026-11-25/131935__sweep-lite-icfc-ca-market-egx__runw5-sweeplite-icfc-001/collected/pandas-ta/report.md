# Technical snapshot — ICFC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2013 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 26.1 |
| High | 27.27 |
| Low | 26.15 |
| Close | 26.54 |
| RSI(14) | 57.9586 |
| MACD | 0.9904 |
| MACD signal | 1.0883 |
| MACD histogram | -0.0979 |
| EMA(20) | 25.1241 |
| EMA(50) | 23.4207 |
| EMA(200) | 19.6329 |
| ADX(14) | 21.5039 |
| Bollinger upper | 29.1911 |
| Bollinger mid | 25.075 |
| Bollinger lower | 20.9589 |
| Bollinger %B | 0.678 |
| ATR(14) | 1.5794 |
| Stochastic %K | 44.351 |
| Stochastic %D | 40.8349 |

## Trend read (facts only)

- Close 26.54 is above EMA_20 25.1241 (+5.64%).
- Close 26.54 is above EMA_50 23.4207 (+13.32%).
- Close 26.54 is above EMA_200 19.6329 (+35.18%).
- RSI(14) is 57.9586, in the neutral zone (30-70).
- MACD 0.9904 is below its signal line 1.0883 (histogram -0.0979).
- Price sits at %B 0.678 of the Bollinger range (lower 20.9589, mid 25.075, upper 29.1911).
- ADX(14) is 21.5039, indicating a developing trend (20-25).
- Stochastic %K 44.351 is above %D 40.8349.
- ATR(14) is 1.5794 (5.95% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
