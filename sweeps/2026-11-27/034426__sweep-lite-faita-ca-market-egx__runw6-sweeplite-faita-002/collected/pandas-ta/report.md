# Technical snapshot — FAITA.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5633 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 1.0 |
| High | 1.0 |
| Low | 1.0 |
| Close | 1.0 |
| RSI(14) | 52.8822 |
| MACD | 0.0028 |
| MACD signal | 0.0029 |
| MACD histogram | -0.0002 |
| EMA(20) | 0.9982 |
| EMA(50) | 0.9939 |
| EMA(200) | 0.9912 |
| ADX(14) | 29.8267 |
| Bollinger upper | 1.008 |
| Bollinger mid | 0.9989 |
| Bollinger lower | 0.9897 |
| Bollinger %B | 0.563 |
| ATR(14) | 0.0098 |
| Stochastic %K | 36.1703 |
| Stochastic %D | 38.2979 |

## Trend read (facts only)

- Close 1.0 is above EMA_20 0.9982 (+0.18%).
- Close 1.0 is above EMA_50 0.9939 (+0.61%).
- Close 1.0 is above EMA_200 0.9912 (+0.89%).
- RSI(14) is 52.8822, in the neutral zone (30-70).
- MACD 0.0028 is below its signal line 0.0029 (histogram -0.0002).
- Price sits at %B 0.563 of the Bollinger range (lower 0.9897, mid 0.9989, upper 1.008).
- ADX(14) is 29.8267, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 36.1703 is below %D 38.2979.
- ATR(14) is 0.0098 (0.98% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
