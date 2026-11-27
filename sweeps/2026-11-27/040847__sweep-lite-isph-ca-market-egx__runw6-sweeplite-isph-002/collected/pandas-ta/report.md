# Technical snapshot — ISPH.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 2203 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 9.98 |
| High | 10.29 |
| Low | 9.93 |
| Close | 10.03 |
| RSI(14) | 42.7325 |
| MACD | -0.157 |
| MACD signal | -0.1979 |
| MACD histogram | 0.0409 |
| EMA(20) | 10.2887 |
| EMA(50) | 10.7942 |
| EMA(200) | 11.2607 |
| ADX(14) | 32.556 |
| Bollinger upper | 10.9015 |
| Bollinger mid | 10.134 |
| Bollinger lower | 9.3665 |
| Bollinger %B | 0.4322 |
| ATR(14) | 0.3865 |
| Stochastic %K | 48.6928 |
| Stochastic %D | 58.0828 |

## Trend read (facts only)

- Close 10.03 is below EMA_20 10.2887 (-2.51%).
- Close 10.03 is below EMA_50 10.7942 (-7.08%).
- Close 10.03 is below EMA_200 11.2607 (-10.93%).
- RSI(14) is 42.7325, in the neutral zone (30-70).
- MACD -0.157 is above its signal line -0.1979 (histogram 0.0409).
- Price sits at %B 0.4322 of the Bollinger range (lower 9.3665, mid 10.134, upper 10.9015).
- ADX(14) is 32.556, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 48.6928 is below %D 58.0828.
- ATR(14) is 0.3865 (3.85% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
