# Technical snapshot — MTIE.CA

- Last session: **2026-11-26**
- Data used: 1933 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 2372 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 6.75 |
| High | 6.9 |
| Low | 6.6 |
| Close | 6.62 |
| RSI(14) | 43.3744 |
| MACD | -0.2352 |
| MACD signal | -0.244 |
| MACD histogram | 0.0088 |
| EMA(20) | 6.8252 |
| EMA(50) | 7.3221 |
| EMA(200) | 7.9995 |
| ADX(14) | 23.099 |
| Bollinger upper | 7.4724 |
| Bollinger mid | 6.818 |
| Bollinger lower | 6.1636 |
| Bollinger %B | 0.3487 |
| ATR(14) | 0.3738 |
| Stochastic %K | 32.2718 |
| Stochastic %D | 23.9915 |

## Trend read (facts only)

- Close 6.62 is below EMA_20 6.8252 (-3.01%).
- Close 6.62 is below EMA_50 7.3221 (-9.59%).
- Close 6.62 is below EMA_200 7.9995 (-17.24%).
- RSI(14) is 43.3744, in the neutral zone (30-70).
- MACD -0.2352 is above its signal line -0.244 (histogram 0.0088).
- Price sits at %B 0.3487 of the Bollinger range (lower 6.1636, mid 6.818, upper 7.4724).
- ADX(14) is 23.099, indicating a developing trend (20-25).
- Stochastic %K 32.2718 is above %D 23.9915.
- ATR(14) is 0.3738 (5.65% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
