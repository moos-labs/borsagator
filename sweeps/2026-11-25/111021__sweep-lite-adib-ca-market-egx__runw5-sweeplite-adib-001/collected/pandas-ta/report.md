# Technical snapshot — ADIB.CA

- Last session: **2026-11-24**
- Data used: 1931 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6535 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 46.43 |
| High | 47.0 |
| Low | 46.15 |
| Close | 46.15 |
| RSI(14) | 43.5712 |
| MACD | -0.3823 |
| MACD signal | -0.1708 |
| MACD histogram | -0.2115 |
| EMA(20) | 47.3857 |
| EMA(50) | 48.1902 |
| EMA(200) | 45.3089 |
| ADX(14) | 28.2478 |
| Bollinger upper | 50.5928 |
| Bollinger mid | 47.649 |
| Bollinger lower | 44.7052 |
| Bollinger %B | 0.2454 |
| ATR(14) | 1.5758 |
| Stochastic %K | 27.6572 |
| Stochastic %D | 26.0514 |

## Trend read (facts only)

- Close 46.15 is below EMA_20 47.3857 (-2.61%).
- Close 46.15 is below EMA_50 48.1902 (-4.23%).
- Close 46.15 is above EMA_200 45.3089 (+1.86%).
- RSI(14) is 43.5712, in the neutral zone (30-70).
- MACD -0.3823 is below its signal line -0.1708 (histogram -0.2115).
- Price sits at %B 0.2454 of the Bollinger range (lower 44.7052, mid 47.649, upper 50.5928).
- ADX(14) is 28.2478, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 27.6572 is above %D 26.0514.
- ATR(14) is 1.5758 (3.41% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
