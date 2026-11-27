# Technical snapshot — EFIH.CA

- Last session: **2026-11-25**
- Data used: 1237 rows (2021-10-20 → 2026-11-25), after dropping rows before 2019-01-01; 1237 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 25.29 |
| High | 25.28 |
| Low | 24.81 |
| Close | 25.0 |
| RSI(14) | 56.9856 |
| MACD | 0.4865 |
| MACD signal | 0.416 |
| MACD histogram | 0.0705 |
| EMA(20) | 24.3626 |
| EMA(50) | 23.8188 |
| EMA(200) | 21.9566 |
| ADX(14) | 13.8215 |
| Bollinger upper | 26.1047 |
| Bollinger mid | 24.1865 |
| Bollinger lower | 22.2683 |
| Bollinger %B | 0.712 |
| ATR(14) | 0.9952 |
| Stochastic %K | 66.5926 |
| Stochastic %D | 67.1362 |

## Trend read (facts only)

- Close 25.0 is above EMA_20 24.3626 (+2.62%).
- Close 25.0 is above EMA_50 23.8188 (+4.96%).
- Close 25.0 is above EMA_200 21.9566 (+13.86%).
- RSI(14) is 56.9856, in the neutral zone (30-70).
- MACD 0.4865 is above its signal line 0.416 (histogram 0.0705).
- Price sits at %B 0.712 of the Bollinger range (lower 22.2683, mid 24.1865, upper 26.1047).
- ADX(14) is 13.8215, indicating a weak / no clear trend (< 20).
- Stochastic %K 66.5926 is below %D 67.1362.
- ATR(14) is 0.9952 (3.98% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
