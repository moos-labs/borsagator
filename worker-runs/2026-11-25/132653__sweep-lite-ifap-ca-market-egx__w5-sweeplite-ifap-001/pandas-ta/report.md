# Technical snapshot — IFAP.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5633 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 16.2 |
| High | 16.79 |
| Low | 15.6 |
| Close | 15.79 |
| RSI(14) | 37.715 |
| MACD | -0.5696 |
| MACD signal | -0.5291 |
| MACD histogram | -0.0406 |
| EMA(20) | 16.7802 |
| EMA(50) | 17.8303 |
| EMA(200) | 18.9983 |
| ADX(14) | 31.8241 |
| Bollinger upper | 18.3515 |
| Bollinger mid | 16.6665 |
| Bollinger lower | 14.9815 |
| Bollinger %B | 0.2399 |
| ATR(14) | 0.8467 |
| Stochastic %K | 15.5486 |
| Stochastic %D | 18.0061 |

## Trend read (facts only)

- Close 15.79 is below EMA_20 16.7802 (-5.90%).
- Close 15.79 is below EMA_50 17.8303 (-11.44%).
- Close 15.79 is below EMA_200 18.9983 (-16.89%).
- RSI(14) is 37.715, in the neutral zone (30-70).
- MACD -0.5696 is below its signal line -0.5291 (histogram -0.0406).
- Price sits at %B 0.2399 of the Bollinger range (lower 14.9815, mid 16.6665, upper 18.3515).
- ADX(14) is 31.8241, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 15.5486 is below %D 18.0061.
- ATR(14) is 0.8467 (5.36% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
