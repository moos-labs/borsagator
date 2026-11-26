# Technical snapshot — CIRA.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5420 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 38.45 |
| High | 38.5 |
| Low | 36.99 |
| Close | 37.0 |
| RSI(14) | 47.2932 |
| MACD | 0.2939 |
| MACD signal | 0.3352 |
| MACD histogram | -0.0412 |
| EMA(20) | 37.6366 |
| EMA(50) | 37.0987 |
| EMA(200) | 30.5427 |
| ADX(14) | 14.2627 |
| Bollinger upper | 40.3043 |
| Bollinger mid | 37.4565 |
| Bollinger lower | 34.6087 |
| Bollinger %B | 0.4198 |
| ATR(14) | 1.6104 |
| Stochastic %K | 50.0158 |
| Stochastic %D | 56.1357 |

## Trend read (facts only)

- Close 37.0 is below EMA_20 37.6366 (-1.69%).
- Close 37.0 is below EMA_50 37.0987 (-0.27%).
- Close 37.0 is above EMA_200 30.5427 (+21.14%).
- RSI(14) is 47.2932, in the neutral zone (30-70).
- MACD 0.2939 is below its signal line 0.3352 (histogram -0.0412).
- Price sits at %B 0.4198 of the Bollinger range (lower 34.6087, mid 37.4565, upper 40.3043).
- ADX(14) is 14.2627, indicating a weak / no clear trend (< 20).
- Stochastic %K 50.0158 is below %D 56.1357.
- ATR(14) is 1.6104 (4.35% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
