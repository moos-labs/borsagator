# Technical snapshot — POUL.CA

- Last session: **2026-11-22**
- Data used: 1927 rows (2019-01-01 → 2026-11-22), after dropping rows before 2019-01-01; 6527 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 7.58 |
| High | 7.48 |
| Low | 7.01 |
| Close | 7.03 |
| RSI(14) | 16.8927 |
| MACD | -2.0512 |
| MACD signal | -2.3435 |
| MACD histogram | 0.2923 |
| EMA(20) | 9.6263 |
| EMA(50) | 15.6903 |
| EMA(200) | 26.0762 |
| ADX(14) | 55.3997 |
| Bollinger upper | 11.3069 |
| Bollinger mid | 9.2515 |
| Bollinger lower | 7.1961 |
| Bollinger %B | -0.0404 |
| ATR(14) | 0.6398 |
| Stochastic %K | 3.1955 |
| Stochastic %D | 3.3031 |

## Trend read (facts only)

- Close 7.03 is below EMA_20 9.6263 (-26.97%).
- Close 7.03 is below EMA_50 15.6903 (-55.20%).
- Close 7.03 is below EMA_200 26.0762 (-73.04%).
- RSI(14) is 16.8927, in the oversold zone (<= 30).
- MACD -2.0512 is above its signal line -2.3435 (histogram 0.2923).
- Price sits at %B -0.0404 of the Bollinger range (lower 7.1961, mid 9.2515, upper 11.3069).
- ADX(14) is 55.3997, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 3.1955 is below %D 3.3031.
- ATR(14) is 0.6398 (9.10% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
