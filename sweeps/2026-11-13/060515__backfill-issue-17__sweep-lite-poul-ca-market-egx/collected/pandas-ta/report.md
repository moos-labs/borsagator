# Technical snapshot — POUL.CA

- Last session: **2026-11-11**
- Data used: 1921 rows (2019-01-01 → 2026-11-11), after dropping rows before 2019-01-01; 6521 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 10.29 |
| High | 10.4 |
| Low | 10.14 |
| Close | 10.2 |
| RSI(14) | 26.8976 |
| MACD | -2.2227 |
| MACD signal | -3.1305 |
| MACD histogram | 0.9078 |
| EMA(20) | 11.0684 |
| EMA(50) | 17.7893 |
| EMA(200) | 27.1943 |
| ADX(14) | 53.7113 |
| Bollinger upper | 10.4907 |
| Bollinger mid | 9.827 |
| Bollinger lower | 9.1633 |
| Bollinger %B | 0.781 |
| ATR(14) | 0.6284 |
| Stochastic %K | 87.341 |
| Stochastic %D | 81.494 |

## Trend read (facts only)

- Close 10.2 is below EMA_20 11.0684 (-7.85%).
- Close 10.2 is below EMA_50 17.7893 (-42.66%).
- Close 10.2 is below EMA_200 27.1943 (-62.49%).
- RSI(14) is 26.8976, in the oversold zone (<= 30).
- MACD -2.2227 is above its signal line -3.1305 (histogram 0.9078).
- Price sits at %B 0.781 of the Bollinger range (lower 9.1633, mid 9.827, upper 10.4907).
- ADX(14) is 53.7113, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 87.341 is above %D 81.494.
- ATR(14) is 0.6284 (6.16% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
