# Technical snapshot — ORWE.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 6535 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 24.0 |
| High | 24.38 |
| Low | 23.74 |
| Close | 24.0 |
| RSI(14) | 38.1122 |
| MACD | -0.331 |
| MACD signal | -0.2316 |
| MACD histogram | -0.0994 |
| EMA(20) | 25.011 |
| EMA(50) | 25.4251 |
| EMA(200) | 24.6069 |
| ADX(14) | 20.9724 |
| Bollinger upper | 26.5467 |
| Bollinger mid | 25.0175 |
| Bollinger lower | 23.4883 |
| Bollinger %B | 0.1673 |
| ATR(14) | 0.9428 |
| Stochastic %K | 14.9515 |
| Stochastic %D | 23.7519 |

## Trend read (facts only)

- Close 24.0 is below EMA_20 25.011 (-4.04%).
- Close 24.0 is below EMA_50 25.4251 (-5.61%).
- Close 24.0 is below EMA_200 24.6069 (-2.47%).
- RSI(14) is 38.1122, in the neutral zone (30-70).
- MACD -0.331 is below its signal line -0.2316 (histogram -0.0994).
- Price sits at %B 0.1673 of the Bollinger range (lower 23.4883, mid 25.0175, upper 26.5467).
- ADX(14) is 20.9724, indicating a developing trend (20-25).
- Stochastic %K 14.9515 is below %D 23.7519.
- ATR(14) is 0.9428 (3.93% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
