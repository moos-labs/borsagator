# Technical snapshot — MASR.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6536 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 6.27 |
| High | 6.43 |
| Low | 6.24 |
| Close | 6.36 |
| RSI(14) | 41.4335 |
| MACD | -0.1912 |
| MACD signal | -0.1647 |
| MACD histogram | -0.0264 |
| EMA(20) | 6.6535 |
| EMA(50) | 6.9805 |
| EMA(200) | 6.7087 |
| ADX(14) | 19.1648 |
| Bollinger upper | 7.141 |
| Bollinger mid | 6.65 |
| Bollinger lower | 6.159 |
| Bollinger %B | 0.2047 |
| ATR(14) | 0.2973 |
| Stochastic %K | 22.2222 |
| Stochastic %D | 21.2765 |

## Trend read (facts only)

- Close 6.36 is below EMA_20 6.6535 (-4.41%).
- Close 6.36 is below EMA_50 6.9805 (-8.89%).
- Close 6.36 is below EMA_200 6.7087 (-5.20%).
- RSI(14) is 41.4335, in the neutral zone (30-70).
- MACD -0.1912 is below its signal line -0.1647 (histogram -0.0264).
- Price sits at %B 0.2047 of the Bollinger range (lower 6.159, mid 6.65, upper 7.141).
- ADX(14) is 19.1648, indicating a weak / no clear trend (< 20).
- Stochastic %K 22.2222 is above %D 21.2765.
- ATR(14) is 0.2973 (4.67% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
