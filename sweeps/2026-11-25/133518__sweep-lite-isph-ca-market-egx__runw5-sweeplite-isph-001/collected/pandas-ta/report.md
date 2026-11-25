# Technical snapshot — ISPH.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2202 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 10.17 |
| High | 10.17 |
| Low | 10.17 |
| Close | 10.17 |
| RSI(14) | 45.0608 |
| MACD | -0.15 |
| MACD signal | -0.2081 |
| MACD histogram | 0.0581 |
| EMA(20) | 10.3159 |
| EMA(50) | 10.8253 |
| EMA(200) | 11.2731 |
| ADX(14) | 32.1496 |
| Bollinger upper | 10.902 |
| Bollinger mid | 10.135 |
| Bollinger lower | 9.368 |
| Bollinger %B | 0.5228 |
| ATR(14) | 0.3885 |
| Stochastic %K | 56.9281 |
| Stochastic %D | 66.4923 |

## Trend read (facts only)

- Close 10.17 is below EMA_20 10.3159 (-1.41%).
- Close 10.17 is below EMA_50 10.8253 (-6.05%).
- Close 10.17 is below EMA_200 11.2731 (-9.79%).
- RSI(14) is 45.0608, in the neutral zone (30-70).
- MACD -0.15 is above its signal line -0.2081 (histogram 0.0581).
- Price sits at %B 0.5228 of the Bollinger range (lower 9.368, mid 10.135, upper 10.902).
- ADX(14) is 32.1496, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 56.9281 is below %D 66.4923.
- ATR(14) is 0.3885 (3.82% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
