# Technical snapshot — POUL.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6529 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 7.1 |
| High | 7.1 |
| Low | 7.1 |
| Close | 7.1 |
| RSI(14) | 17.8788 |
| MACD | -1.9764 |
| MACD signal | -2.2187 |
| MACD histogram | 0.2423 |
| EMA(20) | 9.168 |
| EMA(50) | 15.0298 |
| EMA(200) | 25.7005 |
| ADX(14) | 56.6832 |
| Bollinger upper | 11.4614 |
| Bollinger mid | 9.0375 |
| Bollinger lower | 6.6136 |
| Bollinger %B | 0.1003 |
| ATR(14) | 0.5649 |
| Stochastic %K | 1.9666 |
| Stochastic %D | 2.3503 |

## Trend read (facts only)

- Close 7.1 is below EMA_20 9.168 (-22.56%).
- Close 7.1 is below EMA_50 15.0298 (-52.76%).
- Close 7.1 is below EMA_200 25.7005 (-72.37%).
- RSI(14) is 17.8788, in the oversold zone (<= 30).
- MACD -1.9764 is above its signal line -2.2187 (histogram 0.2423).
- Price sits at %B 0.1003 of the Bollinger range (lower 6.6136, mid 9.0375, upper 11.4614).
- ADX(14) is 56.6832, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 1.9666 is below %D 2.3503.
- ATR(14) is 0.5649 (7.96% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
