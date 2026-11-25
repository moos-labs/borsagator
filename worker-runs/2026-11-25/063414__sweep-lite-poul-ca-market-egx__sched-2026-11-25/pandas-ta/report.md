# Technical snapshot — POUL.CA

- Last session: **2026-11-23**
- Data used: 1928 rows (2019-01-01 → 2026-11-23), after dropping rows before 2019-01-01; 6528 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 7.03 |
| High | 7.23 |
| Low | 7.03 |
| Close | 7.1 |
| RSI(14) | 17.8788 |
| MACD | -2.0222 |
| MACD signal | -2.2793 |
| MACD histogram | 0.2571 |
| EMA(20) | 9.3857 |
| EMA(50) | 15.3535 |
| EMA(200) | 25.8874 |
| ADX(14) | 56.0652 |
| Bollinger upper | 11.3895 |
| Bollinger mid | 9.134 |
| Bollinger lower | 6.8785 |
| Bollinger %B | 0.0491 |
| ATR(14) | 0.6084 |
| Stochastic %K | 1.889 |
| Stochastic %D | 2.9251 |

## Trend read (facts only)

- Close 7.1 is below EMA_20 9.3857 (-24.35%).
- Close 7.1 is below EMA_50 15.3535 (-53.76%).
- Close 7.1 is below EMA_200 25.8874 (-72.57%).
- RSI(14) is 17.8788, in the oversold zone (<= 30).
- MACD -2.0222 is above its signal line -2.2793 (histogram 0.2571).
- Price sits at %B 0.0491 of the Bollinger range (lower 6.8785, mid 9.134, upper 11.3895).
- ADX(14) is 56.0652, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 1.889 is below %D 2.9251.
- ATR(14) is 0.6084 (8.57% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
