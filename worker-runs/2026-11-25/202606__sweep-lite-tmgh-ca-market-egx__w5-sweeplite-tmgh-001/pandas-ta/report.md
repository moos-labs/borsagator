# Technical snapshot — TMGH.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 4706 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 79.5 |
| High | 80.88 |
| Low | 77.77 |
| Close | 78.06 |
| RSI(14) | 35.3023 |
| MACD | -1.5124 |
| MACD signal | -1.3144 |
| MACD histogram | -0.198 |
| EMA(20) | 82.2286 |
| EMA(50) | 85.611 |
| EMA(200) | 86.7226 |
| ADX(14) | 24.7879 |
| Bollinger upper | 86.3443 |
| Bollinger mid | 81.7375 |
| Bollinger lower | 77.1307 |
| Bollinger %B | 0.1009 |
| ATR(14) | 2.4667 |
| Stochastic %K | 17.7214 |
| Stochastic %D | 34.3791 |

## Trend read (facts only)

- Close 78.06 is below EMA_20 82.2286 (-5.07%).
- Close 78.06 is below EMA_50 85.611 (-8.82%).
- Close 78.06 is below EMA_200 86.7226 (-9.99%).
- RSI(14) is 35.3023, in the neutral zone (30-70).
- MACD -1.5124 is below its signal line -1.3144 (histogram -0.198).
- Price sits at %B 0.1009 of the Bollinger range (lower 77.1307, mid 81.7375, upper 86.3443).
- ADX(14) is 24.7879, indicating a developing trend (20-25).
- Stochastic %K 17.7214 is below %D 34.3791.
- ATR(14) is 2.4667 (3.16% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
