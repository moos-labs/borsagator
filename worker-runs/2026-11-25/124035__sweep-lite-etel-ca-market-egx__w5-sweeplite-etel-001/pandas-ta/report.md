# Technical snapshot — ETEL.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5218 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 139.98 |
| High | 142.5 |
| Low | 139.5 |
| Close | 141.0 |
| RSI(14) | 58.572 |
| MACD | 2.2083 |
| MACD signal | 1.1188 |
| MACD histogram | 1.0896 |
| EMA(20) | 135.5899 |
| EMA(50) | 131.84 |
| EMA(200) | 107.932 |
| ADX(14) | 19.6861 |
| Bollinger upper | 147.5444 |
| Bollinger mid | 131.8045 |
| Bollinger lower | 116.0646 |
| Bollinger %B | 0.7921 |
| ATR(14) | 5.8148 |
| Stochastic %K | 72.1779 |
| Stochastic %D | 71.3132 |

## Trend read (facts only)

- Close 141.0 is above EMA_20 135.5899 (+3.99%).
- Close 141.0 is above EMA_50 131.84 (+6.95%).
- Close 141.0 is above EMA_200 107.932 (+30.64%).
- RSI(14) is 58.572, in the neutral zone (30-70).
- MACD 2.2083 is above its signal line 1.1188 (histogram 1.0896).
- Price sits at %B 0.7921 of the Bollinger range (lower 116.0646, mid 131.8045, upper 147.5444).
- ADX(14) is 19.6861, indicating a weak / no clear trend (< 20).
- Stochastic %K 72.1779 is above %D 71.3132.
- ATR(14) is 5.8148 (4.12% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
