# Technical snapshot — LCSW.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 4688 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 41.39 |
| High | 43.35 |
| Low | 40.86 |
| Close | 43.34 |
| RSI(14) | 70.6666 |
| MACD | 1.8471 |
| MACD signal | 1.6389 |
| MACD histogram | 0.2082 |
| EMA(20) | 38.9942 |
| EMA(50) | 36.5414 |
| EMA(200) | 31.8291 |
| ADX(14) | 20.2701 |
| Bollinger upper | 43.5152 |
| Bollinger mid | 38.877 |
| Bollinger lower | 34.2388 |
| Bollinger %B | 0.9811 |
| ATR(14) | 1.8576 |
| Stochastic %K | 89.1656 |
| Stochastic %D | 80.6007 |

## Trend read (facts only)

- Close 43.34 is above EMA_20 38.9942 (+11.14%).
- Close 43.34 is above EMA_50 36.5414 (+18.61%).
- Close 43.34 is above EMA_200 31.8291 (+36.16%).
- RSI(14) is 70.6666, in the overbought zone (>= 70).
- MACD 1.8471 is above its signal line 1.6389 (histogram 0.2082).
- Price sits at %B 0.9811 of the Bollinger range (lower 34.2388, mid 38.877, upper 43.5152).
- ADX(14) is 20.2701, indicating a developing trend (20-25).
- Stochastic %K 89.1656 is above %D 80.6007.
- ATR(14) is 1.8576 (4.29% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
