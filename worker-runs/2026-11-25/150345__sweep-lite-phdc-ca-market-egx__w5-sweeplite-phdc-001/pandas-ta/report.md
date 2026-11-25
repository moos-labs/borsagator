# Technical snapshot — PHDC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 4589 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 11.55 |
| High | 11.76 |
| Low | 11.15 |
| Close | 11.5 |
| RSI(14) | 44.4464 |
| MACD | -0.2654 |
| MACD signal | -0.2909 |
| MACD histogram | 0.0255 |
| EMA(20) | 11.7589 |
| EMA(50) | 12.4093 |
| EMA(200) | 12.2237 |
| ADX(14) | 26.4046 |
| Bollinger upper | 12.5364 |
| Bollinger mid | 11.5735 |
| Bollinger lower | 10.6106 |
| Bollinger %B | 0.4618 |
| ATR(14) | 0.5619 |
| Stochastic %K | 36.1428 |
| Stochastic %D | 40.2606 |

## Trend read (facts only)

- Close 11.5 is below EMA_20 11.7589 (-2.20%).
- Close 11.5 is below EMA_50 12.4093 (-7.33%).
- Close 11.5 is below EMA_200 12.2237 (-5.92%).
- RSI(14) is 44.4464, in the neutral zone (30-70).
- MACD -0.2654 is above its signal line -0.2909 (histogram 0.0255).
- Price sits at %B 0.4618 of the Bollinger range (lower 10.6106, mid 11.5735, upper 12.5364).
- ADX(14) is 26.4046, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 36.1428 is below %D 40.2606.
- ATR(14) is 0.5619 (4.89% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.
