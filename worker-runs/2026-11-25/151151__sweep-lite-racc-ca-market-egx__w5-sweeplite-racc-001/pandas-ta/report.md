# Technical snapshot — RACC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2253 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 7.75 |
| High | 7.75 |
| Low | 7.75 |
| Close | 7.75 |
| RSI(14) | 43.8364 |
| MACD | -0.1699 |
| MACD signal | -0.2002 |
| MACD histogram | 0.0304 |
| EMA(20) | 7.9279 |
| EMA(50) | 8.4054 |
| EMA(200) | 8.9641 |
| ADX(14) | 38.7284 |
| Bollinger upper | 8.5135 |
| Bollinger mid | 7.7555 |
| Bollinger lower | 6.9975 |
| Bollinger %B | 0.4964 |
| ATR(14) | 0.3822 |
| Stochastic %K | 44.6426 |
| Stochastic %D | 47.7428 |

## Trend read (facts only)

- Close 7.75 is below EMA_20 7.9279 (-2.24%).
- Close 7.75 is below EMA_50 8.4054 (-7.80%).
- Close 7.75 is below EMA_200 8.9641 (-13.54%).
- RSI(14) is 43.8364, in the neutral zone (30-70).
- MACD -0.1699 is above its signal line -0.2002 (histogram 0.0304).
- Price sits at %B 0.4964 of the Bollinger range (lower 6.9975, mid 7.7555, upper 8.5135).
- ADX(14) is 38.7284, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 44.6426 is below %D 47.7428.
- ATR(14) is 0.3822 (4.93% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
