# Technical snapshot — POUL.CA

- Last session: **2026-11-19**
- Data used: 1926 rows (2019-01-01 → 2026-11-19), after dropping rows before 2019-01-01; 6526 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 7.7 |
| High | 7.84 |
| Low | 7.55 |
| Close | 7.58 |
| RSI(14) | 18.5147 |
| MACD | -2.0513 |
| MACD signal | -2.4166 |
| MACD histogram | 0.3653 |
| EMA(20) | 9.8996 |
| EMA(50) | 16.0438 |
| EMA(200) | 26.2676 |
| ADX(14) | 54.6829 |
| Bollinger upper | 11.1724 |
| Bollinger mid | 9.383 |
| Bollinger lower | 7.5936 |
| Bollinger %B | -0.0038 |
| ATR(14) | 0.6452 |
| Stochastic %K | 3.6909 |
| Stochastic %D | 11.8792 |

## Trend read (facts only)

- Close 7.58 is below EMA_20 9.8996 (-23.43%).
- Close 7.58 is below EMA_50 16.0438 (-52.75%).
- Close 7.58 is below EMA_200 26.2676 (-71.14%).
- RSI(14) is 18.5147, in the oversold zone (<= 30).
- MACD -2.0513 is above its signal line -2.4166 (histogram 0.3653).
- Price sits at %B -0.0038 of the Bollinger range (lower 7.5936, mid 9.383, upper 11.1724).
- ADX(14) is 54.6829, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 3.6909 is below %D 11.8792.
- ATR(14) is 0.6452 (8.51% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
