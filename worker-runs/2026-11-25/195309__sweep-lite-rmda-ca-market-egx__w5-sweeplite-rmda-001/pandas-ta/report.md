# Technical snapshot — RMDA.CA

- Last session: **2026-11-24**
- Data used: 1685 rows (2019-12-11 → 2026-11-24), after dropping rows before 2019-01-01; 1685 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 5.05 |
| High | 5.05 |
| Low | 5.05 |
| Close | 5.05 |
| RSI(14) | 42.2545 |
| MACD | -0.0605 |
| MACD signal | -0.024 |
| MACD histogram | -0.0365 |
| EMA(20) | 5.2476 |
| EMA(50) | 5.364 |
| EMA(200) | 5.0801 |
| ADX(14) | 27.3589 |
| Bollinger upper | 5.7735 |
| Bollinger mid | 5.277 |
| Bollinger lower | 4.7805 |
| Bollinger %B | 0.2714 |
| ATR(14) | 0.2029 |
| Stochastic %K | 14.2274 |
| Stochastic %D | 20.8577 |

## Trend read (facts only)

- Close 5.05 is below EMA_20 5.2476 (-3.77%).
- Close 5.05 is below EMA_50 5.364 (-5.85%).
- Close 5.05 is below EMA_200 5.0801 (-0.59%).
- RSI(14) is 42.2545, in the neutral zone (30-70).
- MACD -0.0605 is below its signal line -0.024 (histogram -0.0365).
- Price sits at %B 0.2714 of the Bollinger range (lower 4.7805, mid 5.277, upper 5.7735).
- ADX(14) is 27.3589, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 14.2274 is below %D 20.8577.
- ATR(14) is 0.2029 (4.02% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
