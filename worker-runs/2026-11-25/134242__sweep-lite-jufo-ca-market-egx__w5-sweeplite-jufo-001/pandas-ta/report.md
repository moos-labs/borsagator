# Technical snapshot — JUFO.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 4066 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 22.0 |
| High | 22.0 |
| Low | 22.0 |
| Close | 22.0 |
| RSI(14) | 37.1622 |
| MACD | -0.4935 |
| MACD signal | -0.3396 |
| MACD histogram | -0.1539 |
| EMA(20) | 23.3119 |
| EMA(50) | 24.2843 |
| EMA(200) | 26.3661 |
| ADX(14) | 28.7961 |
| Bollinger upper | 25.167 |
| Bollinger mid | 23.387 |
| Bollinger lower | 21.607 |
| Bollinger %B | 0.1104 |
| ATR(14) | 0.8671 |
| Stochastic %K | 7.1805 |
| Stochastic %D | 18.6056 |

## Trend read (facts only)

- Close 22.0 is below EMA_20 23.3119 (-5.63%).
- Close 22.0 is below EMA_50 24.2843 (-9.41%).
- Close 22.0 is below EMA_200 26.3661 (-16.56%).
- RSI(14) is 37.1622, in the neutral zone (30-70).
- MACD -0.4935 is below its signal line -0.3396 (histogram -0.1539).
- Price sits at %B 0.1104 of the Bollinger range (lower 21.607, mid 23.387, upper 25.167).
- ADX(14) is 28.7961, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 7.1805 is below %D 18.6056.
- ATR(14) is 0.8671 (3.94% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
