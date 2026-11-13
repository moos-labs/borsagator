# Technical snapshot — POUL.CA

- Last session: **2026-11-10**
- Data used: 1920 rows (2019-01-01 → 2026-11-10), after dropping rows before 2019-01-01; 6520 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 9.99 |
| High | 10.37 |
| Low | 9.98 |
| Close | 10.29 |
| RSI(14) | 27.345 |
| MACD | -2.4102 |
| MACD signal | -3.3575 |
| MACD histogram | 0.9473 |
| EMA(20) | 11.1598 |
| EMA(50) | 18.0991 |
| EMA(200) | 27.3651 |
| ADX(14) | 54.8279 |
| Bollinger upper | 10.4447 |
| Bollinger mid | 9.801 |
| Bollinger lower | 9.1573 |
| Bollinger %B | 0.8799 |
| ATR(14) | 0.6568 |
| Stochastic %K | 83.4659 |
| Stochastic %D | 75.2466 |

## Trend read (facts only)

- Close 10.29 is below EMA_20 11.1598 (-7.79%).
- Close 10.29 is below EMA_50 18.0991 (-43.15%).
- Close 10.29 is below EMA_200 27.3651 (-62.40%).
- RSI(14) is 27.345, in the oversold zone (<= 30).
- MACD -2.4102 is above its signal line -3.3575 (histogram 0.9473).
- Price sits at %B 0.8799 of the Bollinger range (lower 9.1573, mid 9.801, upper 10.4447).
- ADX(14) is 54.8279, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 83.4659 is above %D 75.2466.
- ATR(14) is 0.6568 (6.38% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
