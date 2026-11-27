# Technical snapshot — MASR.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 6538 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 6.23 |
| High | 6.35 |
| Low | 6.19 |
| Close | 6.35 |
| RSI(14) | 42.3043 |
| MACD | -0.1983 |
| MACD signal | -0.1774 |
| MACD histogram | -0.0209 |
| EMA(20) | 6.5881 |
| EMA(50) | 6.9275 |
| EMA(200) | 6.7004 |
| ADX(14) | 20.9512 |
| Bollinger upper | 7.1577 |
| Bollinger mid | 6.6345 |
| Bollinger lower | 6.1113 |
| Bollinger %B | 0.2281 |
| ATR(14) | 0.2804 |
| Stochastic %K | 28.2282 |
| Stochastic %D | 25.4254 |

## Trend read (facts only)

- Close 6.35 is below EMA_20 6.5881 (-3.61%).
- Close 6.35 is below EMA_50 6.9275 (-8.34%).
- Close 6.35 is below EMA_200 6.7004 (-5.23%).
- RSI(14) is 42.3043, in the neutral zone (30-70).
- MACD -0.1983 is below its signal line -0.1774 (histogram -0.0209).
- Price sits at %B 0.2281 of the Bollinger range (lower 6.1113, mid 6.6345, upper 7.1577).
- ADX(14) is 20.9512, indicating a developing trend (20-25).
- Stochastic %K 28.2282 is above %D 25.4254.
- ATR(14) is 0.2804 (4.42% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
