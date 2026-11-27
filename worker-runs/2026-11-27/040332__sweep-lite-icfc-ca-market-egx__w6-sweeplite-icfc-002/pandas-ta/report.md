# Technical snapshot — ICFC.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 2014 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 26.54 |
| High | 27.24 |
| Low | 25.8 |
| Close | 26.8 |
| RSI(14) | 58.8631 |
| MACD | 1.0039 |
| MACD signal | 1.0714 |
| MACD histogram | -0.0675 |
| EMA(20) | 25.2837 |
| EMA(50) | 23.5533 |
| EMA(200) | 19.7043 |
| ADX(14) | 20.8093 |
| Bollinger upper | 29.0341 |
| Bollinger mid | 25.3795 |
| Bollinger lower | 21.7249 |
| Bollinger %B | 0.6943 |
| ATR(14) | 1.5694 |
| Stochastic %K | 58.9559 |
| Stochastic %D | 46.7852 |

## Trend read (facts only)

- Close 26.8 is above EMA_20 25.2837 (+6.00%).
- Close 26.8 is above EMA_50 23.5533 (+13.78%).
- Close 26.8 is above EMA_200 19.7043 (+36.01%).
- RSI(14) is 58.8631, in the neutral zone (30-70).
- MACD 1.0039 is below its signal line 1.0714 (histogram -0.0675).
- Price sits at %B 0.6943 of the Bollinger range (lower 21.7249, mid 25.3795, upper 29.0341).
- ADX(14) is 20.8093, indicating a developing trend (20-25).
- Stochastic %K 58.9559 is above %D 46.7852.
- ATR(14) is 1.5694 (5.86% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
