# Technical snapshot — OCDI.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6538 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 23.32 |
| High | 24.07 |
| Low | 23.36 |
| Close | 23.78 |
| RSI(14) | 43.6484 |
| MACD | -0.4659 |
| MACD signal | -0.41 |
| MACD histogram | -0.0559 |
| EMA(20) | 24.7107 |
| EMA(50) | 25.851 |
| EMA(200) | 26.4658 |
| ADX(14) | 29.434 |
| Bollinger upper | 26.8789 |
| Bollinger mid | 24.475 |
| Bollinger lower | 22.0711 |
| Bollinger %B | 0.3554 |
| ATR(14) | 1.1981 |
| Stochastic %K | 27.0337 |
| Stochastic %D | 40.0187 |

## Trend read (facts only)

- Close 23.78 is below EMA_20 24.7107 (-3.77%).
- Close 23.78 is below EMA_50 25.851 (-8.01%).
- Close 23.78 is below EMA_200 26.4658 (-10.15%).
- RSI(14) is 43.6484, in the neutral zone (30-70).
- MACD -0.4659 is below its signal line -0.41 (histogram -0.0559).
- Price sits at %B 0.3554 of the Bollinger range (lower 22.0711, mid 24.475, upper 26.8789).
- ADX(14) is 29.434, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 27.0337 is below %D 40.0187.
- ATR(14) is 1.1981 (5.04% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
