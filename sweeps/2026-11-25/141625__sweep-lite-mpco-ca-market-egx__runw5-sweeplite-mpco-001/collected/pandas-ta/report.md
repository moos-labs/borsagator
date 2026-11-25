# Technical snapshot — MPCO.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5840 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 1.92 |
| High | 1.92 |
| Low | 1.92 |
| Close | 1.92 |
| RSI(14) | 45.8618 |
| MACD | -0.0363 |
| MACD signal | -0.0424 |
| MACD histogram | 0.0061 |
| EMA(20) | 1.9789 |
| EMA(50) | 2.0604 |
| EMA(200) | 1.9641 |
| ADX(14) | 19.975 |
| Bollinger upper | 2.2155 |
| Bollinger mid | 1.931 |
| Bollinger lower | 1.6465 |
| Bollinger %B | 0.4807 |
| ATR(14) | 0.1439 |
| Stochastic %K | 21.3156 |
| Stochastic %D | 26.3075 |

## Trend read (facts only)

- Close 1.92 is below EMA_20 1.9789 (-2.98%).
- Close 1.92 is below EMA_50 2.0604 (-6.81%).
- Close 1.92 is below EMA_200 1.9641 (-2.25%).
- RSI(14) is 45.8618, in the neutral zone (30-70).
- MACD -0.0363 is above its signal line -0.0424 (histogram 0.0061).
- Price sits at %B 0.4807 of the Bollinger range (lower 1.6465, mid 1.931, upper 2.2155).
- ADX(14) is 19.975, indicating a weak / no clear trend (< 20).
- Stochastic %K 21.3156 is below %D 26.3075.
- ATR(14) is 0.1439 (7.49% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
