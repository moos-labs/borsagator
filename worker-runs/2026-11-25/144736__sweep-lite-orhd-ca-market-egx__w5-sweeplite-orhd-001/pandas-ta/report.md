# Technical snapshot — ORHD.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 4681 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 9.98 |
| High | 9.98 |
| Low | 9.98 |
| Close | 9.98 |
| RSI(14) | 27.6204 |
| MACD | -1.4896 |
| MACD signal | -2.0659 |
| MACD histogram | 0.5763 |
| EMA(20) | 10.7688 |
| EMA(50) | 16.524 |
| EMA(200) | 26.2799 |
| ADX(14) | 56.8906 |
| Bollinger upper | 10.7645 |
| Bollinger mid | 10.114 |
| Bollinger lower | 9.4635 |
| Bollinger %B | 0.397 |
| ATR(14) | 0.5668 |
| Stochastic %K | 40.0868 |
| Stochastic %D | 52.1069 |

## Trend read (facts only)

- Close 9.98 is below EMA_20 10.7688 (-7.32%).
- Close 9.98 is below EMA_50 16.524 (-39.60%).
- Close 9.98 is below EMA_200 26.2799 (-62.02%).
- RSI(14) is 27.6204, in the oversold zone (<= 30).
- MACD -1.4896 is above its signal line -2.0659 (histogram 0.5763).
- Price sits at %B 0.397 of the Bollinger range (lower 9.4635, mid 10.114, upper 10.7645).
- ADX(14) is 56.8906, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 40.0868 is below %D 52.1069.
- ATR(14) is 0.5668 (5.68% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
