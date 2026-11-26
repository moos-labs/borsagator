# Technical snapshot — EFID.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 2863 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 20.98 |
| High | 20.98 |
| Low | 20.52 |
| Close | 20.7 |
| RSI(14) | 55.8205 |
| MACD | 0.2235 |
| MACD signal | -0.0115 |
| MACD histogram | 0.235 |
| EMA(20) | 19.9173 |
| EMA(50) | 21.0477 |
| EMA(200) | 24.72 |
| ADX(14) | 25.7532 |
| Bollinger upper | 21.7422 |
| Bollinger mid | 19.544 |
| Bollinger lower | 17.3458 |
| Bollinger %B | 0.7629 |
| ATR(14) | 0.8238 |
| Stochastic %K | 72.1166 |
| Stochastic %D | 72.3776 |

## Trend read (facts only)

- Close 20.7 is above EMA_20 19.9173 (+3.93%).
- Close 20.7 is below EMA_50 21.0477 (-1.65%).
- Close 20.7 is below EMA_200 24.72 (-16.26%).
- RSI(14) is 55.8205, in the neutral zone (30-70).
- MACD 0.2235 is above its signal line -0.0115 (histogram 0.235).
- Price sits at %B 0.7629 of the Bollinger range (lower 17.3458, mid 19.544, upper 21.7422).
- ADX(14) is 25.7532, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 72.1166 is below %D 72.3776.
- ATR(14) is 0.8238 (3.98% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
