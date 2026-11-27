# Technical snapshot — ORHD.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 4683 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 10.38 |
| High | 10.5 |
| Low | 10.31 |
| Close | 10.45 |
| RSI(14) | 34.9866 |
| MACD | -1.2444 |
| MACD signal | -1.7893 |
| MACD histogram | 0.5449 |
| EMA(20) | 10.7049 |
| EMA(50) | 16.0543 |
| EMA(200) | 25.9657 |
| ADX(14) | 54.0914 |
| Bollinger upper | 10.7736 |
| Bollinger mid | 10.193 |
| Bollinger lower | 9.6124 |
| Bollinger %B | 0.7213 |
| ATR(14) | 0.5434 |
| Stochastic %K | 63.0252 |
| Stochastic %D | 51.1033 |

## Trend read (facts only)

- Close 10.45 is below EMA_20 10.7049 (-2.38%).
- Close 10.45 is below EMA_50 16.0543 (-34.91%).
- Close 10.45 is below EMA_200 25.9657 (-59.75%).
- RSI(14) is 34.9866, in the neutral zone (30-70).
- MACD -1.2444 is above its signal line -1.7893 (histogram 0.5449).
- Price sits at %B 0.7213 of the Bollinger range (lower 9.6124, mid 10.193, upper 10.7736).
- ADX(14) is 54.0914, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 63.0252 is above %D 51.1033.
- ATR(14) is 0.5434 (5.20% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
