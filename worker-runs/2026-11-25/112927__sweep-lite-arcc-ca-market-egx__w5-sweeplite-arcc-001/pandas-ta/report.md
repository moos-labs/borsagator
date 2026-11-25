# Technical snapshot — ARCC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 3088 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 66.09 |
| High | 68.0 |
| Low | 66.51 |
| Close | 67.03 |
| RSI(14) | 49.6957 |
| MACD | 0.0685 |
| MACD signal | 0.1325 |
| MACD histogram | -0.064 |
| EMA(20) | 67.1021 |
| EMA(50) | 67.1514 |
| EMA(200) | 60.1467 |
| ADX(14) | 15.0021 |
| Bollinger upper | 71.5918 |
| Bollinger mid | 66.681 |
| Bollinger lower | 61.7702 |
| Bollinger %B | 0.5355 |
| ATR(14) | 2.7402 |
| Stochastic %K | 30.3773 |
| Stochastic %D | 37.5242 |

## Trend read (facts only)

- Close 67.03 is below EMA_20 67.1021 (-0.11%).
- Close 67.03 is below EMA_50 67.1514 (-0.18%).
- Close 67.03 is above EMA_200 60.1467 (+11.44%).
- RSI(14) is 49.6957, in the neutral zone (30-70).
- MACD 0.0685 is below its signal line 0.1325 (histogram -0.064).
- Price sits at %B 0.5355 of the Bollinger range (lower 61.7702, mid 66.681, upper 71.5918).
- ADX(14) is 15.0021, indicating a weak / no clear trend (< 20).
- Stochastic %K 30.3773 is below %D 37.5242.
- ATR(14) is 2.7402 (4.09% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
