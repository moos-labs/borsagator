# Technical snapshot — FAITA.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5632 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 1.0 |
| High | 1.0 |
| Low | 1.0 |
| Close | 1.0 |
| RSI(14) | 52.8822 |
| MACD | 0.003 |
| MACD signal | 0.003 |
| MACD histogram | 0.0 |
| EMA(20) | 0.998 |
| EMA(50) | 0.9936 |
| EMA(200) | 0.9912 |
| ADX(14) | 28.2855 |
| Bollinger upper | 1.0085 |
| Bollinger mid | 0.9983 |
| Bollinger lower | 0.988 |
| Bollinger %B | 0.5853 |
| ATR(14) | 0.0105 |
| Stochastic %K | 36.1703 |
| Stochastic %D | 44.099 |

## Trend read (facts only)

- Close 1.0 is above EMA_20 0.998 (+0.20%).
- Close 1.0 is above EMA_50 0.9936 (+0.64%).
- Close 1.0 is above EMA_200 0.9912 (+0.89%).
- RSI(14) is 52.8822, in the neutral zone (30-70).
- MACD 0.003 is above its signal line 0.003 (histogram 0.0).
- Price sits at %B 0.5853 of the Bollinger range (lower 0.988, mid 0.9983, upper 1.0085).
- ADX(14) is 28.2855, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 36.1703 is below %D 44.099.
- ATR(14) is 0.0105 (1.05% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
