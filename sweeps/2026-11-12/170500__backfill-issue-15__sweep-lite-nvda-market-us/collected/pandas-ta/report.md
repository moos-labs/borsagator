# Technical snapshot — NVDA

- Last session: **2026-11-12**
- Data used: 1978 rows (2019-01-02 → 2026-11-12), after dropping rows before 2019-01-01; 6996 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 150.99 |
| High | 167.14 |
| Low | 148.8 |
| Close | 164.1995 |
| RSI(14) | 25.3513 |
| MACD | -13.4008 |
| MACD signal | -9.1114 |
| MACD histogram | -4.2895 |
| EMA(20) | 196.2783 |
| EMA(50) | 208.5785 |
| EMA(200) | 203.7741 |
| ADX(14) | 39.4835 |
| Bollinger upper | 237.1292 |
| Bollinger mid | 201.153 |
| Bollinger lower | 165.1767 |
| Bollinger %B | -0.0136 |
| ATR(14) | 9.8559 |
| Stochastic %K | 13.8895 |
| Stochastic %D | 12.4914 |

## Trend read (facts only)

- Close 164.1995 is below EMA_20 196.2783 (-16.34%).
- Close 164.1995 is below EMA_50 208.5785 (-21.28%).
- Close 164.1995 is below EMA_200 203.7741 (-19.42%).
- RSI(14) is 25.3513, in the oversold zone (<= 30).
- MACD -13.4008 is below its signal line -9.1114 (histogram -4.2895).
- Price sits at %B -0.0136 of the Bollinger range (lower 165.1767, mid 201.153, upper 237.1292).
- ADX(14) is 39.4835, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 13.8895 is above %D 12.4914.
- ATR(14) is 9.8559 (6.00% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
