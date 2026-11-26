# Technical snapshot — CLHO.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 2462 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 14.3 |
| High | 14.49 |
| Low | 14.06 |
| Close | 14.2 |
| RSI(14) | 50.9317 |
| MACD | -0.0684 |
| MACD signal | -0.1486 |
| MACD histogram | 0.0802 |
| EMA(20) | 14.0708 |
| EMA(50) | 14.5567 |
| EMA(200) | 14.4752 |
| ADX(14) | 24.2929 |
| Bollinger upper | 14.8293 |
| Bollinger mid | 13.912 |
| Bollinger lower | 12.9947 |
| Bollinger %B | 0.657 |
| ATR(14) | 0.5382 |
| Stochastic %K | 52.6739 |
| Stochastic %D | 51.9653 |

## Trend read (facts only)

- Close 14.2 is above EMA_20 14.0708 (+0.92%).
- Close 14.2 is below EMA_50 14.5567 (-2.45%).
- Close 14.2 is below EMA_200 14.4752 (-1.90%).
- RSI(14) is 50.9317, in the neutral zone (30-70).
- MACD -0.0684 is above its signal line -0.1486 (histogram 0.0802).
- Price sits at %B 0.657 of the Bollinger range (lower 12.9947, mid 13.912, upper 14.8293).
- ADX(14) is 24.2929, indicating a developing trend (20-25).
- Stochastic %K 52.6739 is above %D 51.9653.
- ATR(14) is 0.5382 (3.79% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
