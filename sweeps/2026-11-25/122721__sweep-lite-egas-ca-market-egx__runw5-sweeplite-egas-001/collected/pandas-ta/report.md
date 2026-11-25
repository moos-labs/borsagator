# Technical snapshot — EGAS.CA

- Last session: **2026-11-24**
- Data used: 1930 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6422 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 49.1 |
| High | 50.95 |
| Low | 48.87 |
| Close | 49.1 |
| RSI(14) | 47.9247 |
| MACD | -0.4498 |
| MACD signal | -0.7644 |
| MACD histogram | 0.3146 |
| EMA(20) | 49.3233 |
| EMA(50) | 51.0111 |
| EMA(200) | 50.1077 |
| ADX(14) | 29.7612 |
| Bollinger upper | 52.007 |
| Bollinger mid | 48.3775 |
| Bollinger lower | 44.748 |
| Bollinger %B | 0.5995 |
| ATR(14) | 2.5865 |
| Stochastic %K | 25.4151 |
| Stochastic %D | 29.0616 |

## Trend read (facts only)

- Close 49.1 is below EMA_20 49.3233 (-0.45%).
- Close 49.1 is below EMA_50 51.0111 (-3.75%).
- Close 49.1 is below EMA_200 50.1077 (-2.01%).
- RSI(14) is 47.9247, in the neutral zone (30-70).
- MACD -0.4498 is above its signal line -0.7644 (histogram 0.3146).
- Price sits at %B 0.5995 of the Bollinger range (lower 44.748, mid 48.3775, upper 52.007).
- ADX(14) is 29.7612, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 25.4151 is below %D 29.0616.
- ATR(14) is 2.5865 (5.27% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
