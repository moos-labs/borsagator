# 🐊 Borsagator digest — sweep-lite NVDA market=US

Started 2026-11-13 06:07 UTC · finished 06:34 UTC · 20 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1254; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=354.8800048828125; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43376505398) |
| openbb | data | ok | rows_AAPL.csv=501; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=354.8800048828125; rows_POUL_CA.csv=484; POUL_CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43376602594) |
| pandas-ta | technicals | ok | macd_signal=-9.0796; ticker=NVDA; date=2026-11-12; open=151.01; high=167.14 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43376696073) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-13; forecast.csv_last_close=208.8533 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43376751949) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43376893297) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=112977.36; total_return_pct=12.9774 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43376947599) |
| akshare | data | ok | rows_a_share_600519.csv=243 | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43377004595) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43377099102) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43377189007) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43377285072) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43377423938) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=117659.31024932888 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43377526089) |
| simfin | fundamentals | ok | rows_aapl_income.csv=3; rows_companies_us.csv=6592 | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43377657177) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43377754897) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43377881270) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43377978045) |
| finrl | backtest | ok | rows_account_value.csv=124; account_value.csv_last_date=2024-06-28 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43378076932) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43378254070) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43379297166) |
| news-disclosure | news | ok | ticker=NVDA; fetched_at=2026-11-13T06:33:55Z; tool=news-disclosure; news_count=40; disclosure_count=25 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43379394638) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 166.19 (pandas-ta). Daily volatility σ 3.91% (pandas-ta/indicators.csv (σ60=0.0273, σ10=0.0391)). News risk: **shock** — shock headline(s): Nvidia stock plunges as CEO Jensen Huang resigns: How low it might go - Mashable; shock headline(s): Nvidia market cap plunges $490 billion following former CEO Huang's affair scandals - Yaho; shock headline(s): Nvidia CEO Jensen Huang Resigns—and the Stock Is Falling - Barron's.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.71% | -8.77% … +7.34% | 0.30 |
| week | ⬆ up | +6.93% | -12.67% … +26.53% | 0.30 |
| month | ⬆ up | +18.61% | -22.41% … +59.64% | 0.30 |

Family scores (−1…+1): technicals +0.10, sentiment -0.25, agent —, fundamentals —, price-forecast +0.72.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
