# Technical snapshot — SAUD.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6528 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 22.63 |
| High | 22.94 |
| Low | 22.11 |
| Close | 22.26 |
| RSI(14) | 51.5821 |
| MACD | 0.3119 |
| MACD signal | 0.1663 |
| MACD histogram | 0.1456 |
| EMA(20) | 22.1445 |
| EMA(50) | 22.1281 |
| EMA(200) | 20.8709 |
| ADX(14) | 18.2197 |
| Bollinger upper | 24.0283 |
| Bollinger mid | 21.7215 |
| Bollinger lower | 19.4147 |
| Bollinger %B | 0.6167 |
| ATR(14) | 0.8931 |
| Stochastic %K | 67.0115 |
| Stochastic %D | 73.9447 |

## Trend read (facts only)

- Close 22.26 is above EMA_20 22.1445 (+0.52%).
- Close 22.26 is above EMA_50 22.1281 (+0.60%).
- Close 22.26 is above EMA_200 20.8709 (+6.66%).
- RSI(14) is 51.5821, in the neutral zone (30-70).
- MACD 0.3119 is above its signal line 0.1663 (histogram 0.1456).
- Price sits at %B 0.6167 of the Bollinger range (lower 19.4147, mid 21.7215, upper 24.0283).
- ADX(14) is 18.2197, indicating a weak / no clear trend (< 20).
- Stochastic %K 67.0115 is below %D 73.9447.
- ATR(14) is 0.8931 (4.01% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
