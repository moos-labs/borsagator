# Technical snapshot — ETRS.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6150 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 11.05 |
| High | 11.49 |
| Low | 10.94 |
| Close | 11.15 |
| RSI(14) | 57.3674 |
| MACD | 0.144 |
| MACD signal | 0.1192 |
| MACD histogram | 0.0248 |
| EMA(20) | 10.8922 |
| EMA(50) | 10.7463 |
| EMA(200) | 9.6277 |
| ADX(14) | 18.9067 |
| Bollinger upper | 11.4059 |
| Bollinger mid | 10.8555 |
| Bollinger lower | 10.3051 |
| Bollinger %B | 0.7675 |
| ATR(14) | 0.4077 |
| Stochastic %K | 53.8628 |
| Stochastic %D | 58.4001 |

## Trend read (facts only)

- Close 11.15 is above EMA_20 10.8922 (+2.37%).
- Close 11.15 is above EMA_50 10.7463 (+3.76%).
- Close 11.15 is above EMA_200 9.6277 (+15.81%).
- RSI(14) is 57.3674, in the neutral zone (30-70).
- MACD 0.144 is above its signal line 0.1192 (histogram 0.0248).
- Price sits at %B 0.7675 of the Bollinger range (lower 10.3051, mid 10.8555, upper 11.4059).
- ADX(14) is 18.9067, indicating a weak / no clear trend (< 20).
- Stochastic %K 53.8628 is below %D 58.4001.
- ATR(14) is 0.4077 (3.66% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
