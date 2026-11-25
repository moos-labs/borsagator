# Technical snapshot — EFIH.CA

- Last session: **2026-11-24**
- Data used: 1236 rows (2021-10-20 → 2026-11-24), after dropping rows before 2019-01-01; 1236 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 24.8 |
| High | 25.4 |
| Low | 24.82 |
| Close | 25.29 |
| RSI(14) | 59.6986 |
| MACD | 0.493 |
| MACD signal | 0.3984 |
| MACD histogram | 0.0946 |
| EMA(20) | 24.2955 |
| EMA(50) | 23.7706 |
| EMA(200) | 21.926 |
| ADX(14) | 14.4091 |
| Bollinger upper | 26.1505 |
| Bollinger mid | 24.032 |
| Bollinger lower | 21.9135 |
| Bollinger %B | 0.7969 |
| ATR(14) | 1.0349 |
| Stochastic %K | 64.8583 |
| Stochastic %D | 71.3413 |

## Trend read (facts only)

- Close 25.29 is above EMA_20 24.2955 (+4.09%).
- Close 25.29 is above EMA_50 23.7706 (+6.39%).
- Close 25.29 is above EMA_200 21.926 (+15.34%).
- RSI(14) is 59.6986, in the neutral zone (30-70).
- MACD 0.493 is above its signal line 0.3984 (histogram 0.0946).
- Price sits at %B 0.7969 of the Bollinger range (lower 21.9135, mid 24.032, upper 26.1505).
- ADX(14) is 14.4091, indicating a weak / no clear trend (< 20).
- Stochastic %K 64.8583 is below %D 71.3413.
- ATR(14) is 1.0349 (4.09% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
