# Technical snapshot — POUL.CA

- Last session: **2026-11-17**
- Data used: 1924 rows (2019-01-01 → 2026-11-17), after dropping rows before 2019-01-01; 6524 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 8.02 |
| High | 8.09 |
| Low | 7.51 |
| Close | 7.57 |
| RSI(14) | 17.2302 |
| MACD | -2.0931 |
| MACD signal | -2.6155 |
| MACD histogram | 0.5224 |
| EMA(20) | 10.401 |
| EMA(50) | 16.7439 |
| EMA(200) | 26.6439 |
| ADX(14) | 53.6397 |
| Bollinger upper | 10.9907 |
| Bollinger mid | 9.612 |
| Bollinger lower | 8.2333 |
| Bollinger %B | -0.2405 |
| ATR(14) | 0.7019 |
| Stochastic %K | 28.9238 |
| Stochastic %D | 58.3842 |

## Trend read (facts only)

- Close 7.57 is below EMA_20 10.401 (-27.22%).
- Close 7.57 is below EMA_50 16.7439 (-54.79%).
- Close 7.57 is below EMA_200 26.6439 (-71.59%).
- RSI(14) is 17.2302, in the oversold zone (<= 30).
- MACD -2.0931 is above its signal line -2.6155 (histogram 0.5224).
- Price sits at %B -0.2405 of the Bollinger range (lower 8.2333, mid 9.612, upper 10.9907).
- ADX(14) is 53.6397, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 28.9238 is below %D 58.3842.
- ATR(14) is 0.7019 (9.27% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
