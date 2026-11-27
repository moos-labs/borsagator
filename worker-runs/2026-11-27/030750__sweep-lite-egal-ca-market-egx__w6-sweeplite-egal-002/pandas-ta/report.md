# Technical snapshot — EGAL.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6534 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 298.0 |
| High | 299.0 |
| Low | 292.02 |
| Close | 293.35 |
| RSI(14) | 36.7946 |
| MACD | -4.991 |
| MACD signal | -3.7889 |
| MACD histogram | -1.2021 |
| EMA(20) | 308.9033 |
| EMA(50) | 317.417 |
| EMA(200) | 298.3431 |
| ADX(14) | 27.4966 |
| Bollinger upper | 329.5612 |
| Bollinger mid | 309.7875 |
| Bollinger lower | 290.0138 |
| Bollinger %B | 0.0844 |
| ATR(14) | 9.1961 |
| Stochastic %K | 13.7956 |
| Stochastic %D | 18.568 |

## Trend read (facts only)

- Close 293.35 is below EMA_20 308.9033 (-5.04%).
- Close 293.35 is below EMA_50 317.417 (-7.58%).
- Close 293.35 is below EMA_200 298.3431 (-1.67%).
- RSI(14) is 36.7946, in the neutral zone (30-70).
- MACD -4.991 is below its signal line -3.7889 (histogram -1.2021).
- Price sits at %B 0.0844 of the Bollinger range (lower 290.0138, mid 309.7875, upper 329.5612).
- ADX(14) is 27.4966, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 13.7956 is below %D 18.568.
- ATR(14) is 9.1961 (3.13% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
