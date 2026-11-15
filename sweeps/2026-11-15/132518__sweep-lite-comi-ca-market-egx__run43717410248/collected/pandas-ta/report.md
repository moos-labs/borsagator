# Technical snapshot — COMI.CA

- Last session: **2026-11-12**
- Data used: 1922 rows (2019-01-01 → 2026-11-12), after dropping rows before 2019-01-01; 6529 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 130.34 |
| High | 130.32 |
| Low | 128.6 |
| Close | 128.75 |
| RSI(14) | 55.3805 |
| MACD | 0.5524 |
| MACD signal | -0.6247 |
| MACD histogram | 1.177 |
| EMA(20) | 126.1832 |
| EMA(50) | 127.9768 |
| EMA(200) | 126.924 |
| ADX(14) | 30.7501 |
| Bollinger upper | 132.2499 |
| Bollinger mid | 124.9065 |
| Bollinger lower | 117.5631 |
| Bollinger %B | 0.7617 |
| ATR(14) | 2.6836 |
| Stochastic %K | 90.4659 |
| Stochastic %D | 91.9944 |

## Trend read (facts only)

- Close 128.75 is above EMA_20 126.1832 (+2.03%).
- Close 128.75 is above EMA_50 127.9768 (+0.60%).
- Close 128.75 is above EMA_200 126.924 (+1.44%).
- RSI(14) is 55.3805, in the neutral zone (30-70).
- MACD 0.5524 is above its signal line -0.6247 (histogram 1.177).
- Price sits at %B 0.7617 of the Bollinger range (lower 117.5631, mid 124.9065, upper 132.2499).
- ADX(14) is 30.7501, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 90.4659 is below %D 91.9944.
- ATR(14) is 2.6836 (2.08% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
