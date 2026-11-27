# Technical snapshot — ETEL.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5219 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 141.0 |
| High | 141.28 |
| Low | 138.51 |
| Close | 139.2 |
| RSI(14) | 55.7887 |
| MACD | 2.2101 |
| MACD signal | 1.337 |
| MACD histogram | 0.8731 |
| EMA(20) | 135.9337 |
| EMA(50) | 132.1286 |
| EMA(200) | 108.2431 |
| ADX(14) | 18.8858 |
| Bollinger upper | 148.2939 |
| Bollinger mid | 132.4445 |
| Bollinger lower | 116.5951 |
| Bollinger %B | 0.7131 |
| ATR(14) | 5.5973 |
| Stochastic %K | 70.8455 |
| Stochastic %D | 70.8131 |

## Trend read (facts only)

- Close 139.2 is above EMA_20 135.9337 (+2.40%).
- Close 139.2 is above EMA_50 132.1286 (+5.35%).
- Close 139.2 is above EMA_200 108.2431 (+28.60%).
- RSI(14) is 55.7887, in the neutral zone (30-70).
- MACD 2.2101 is above its signal line 1.337 (histogram 0.8731).
- Price sits at %B 0.7131 of the Bollinger range (lower 116.5951, mid 132.4445, upper 148.2939).
- ADX(14) is 18.8858, indicating a weak / no clear trend (< 20).
- Stochastic %K 70.8455 is above %D 70.8131.
- ATR(14) is 5.5973 (4.02% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
