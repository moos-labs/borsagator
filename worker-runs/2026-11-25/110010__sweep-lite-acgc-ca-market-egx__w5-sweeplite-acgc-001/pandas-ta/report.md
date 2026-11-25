# Technical snapshot — ACGC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5950 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 13.5 |
| High | 13.5 |
| Low | 13.5 |
| Close | 13.5 |
| RSI(14) | 50.8964 |
| MACD | 0.0593 |
| MACD signal | 0.0338 |
| MACD histogram | 0.0255 |
| EMA(20) | 13.4641 |
| EMA(50) | 13.3301 |
| EMA(200) | 11.3646 |
| ADX(14) | 23.0211 |
| Bollinger upper | 14.1514 |
| Bollinger mid | 13.3625 |
| Bollinger lower | 12.5736 |
| Bollinger %B | 0.5871 |
| ATR(14) | 0.5162 |
| Stochastic %K | 61.0183 |
| Stochastic %D | 65.395 |

## Trend read (facts only)

- Close 13.5 is above EMA_20 13.4641 (+0.27%).
- Close 13.5 is above EMA_50 13.3301 (+1.27%).
- Close 13.5 is above EMA_200 11.3646 (+18.79%).
- RSI(14) is 50.8964, in the neutral zone (30-70).
- MACD 0.0593 is above its signal line 0.0338 (histogram 0.0255).
- Price sits at %B 0.5871 of the Bollinger range (lower 12.5736, mid 13.3625, upper 14.1514).
- ADX(14) is 23.0211, indicating a developing trend (20-25).
- Stochastic %K 61.0183 is below %D 65.395.
- ATR(14) is 0.5162 (3.82% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
