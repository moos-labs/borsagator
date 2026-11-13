# 🐊 Borsagator digest — sweep-lite NVDA market=US

Started 2026-11-12 16:42 UTC · finished 17:04 UTC · 20 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1255; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=357.32000732421875; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43261631482) |
| openbb | data | ok | rows_AAPL.csv=502; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=357.2900085449219; rows_POUL_CA.csv=485; POUL_CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43261775939) |
| pandas-ta | technicals | ok | macd_signal=-9.1114; ticker=NVDA; date=2026-11-12; open=150.99; high=167.14 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43261921016) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-13; forecast.csv_last_close=208.4591 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43262068964) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-09 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43262281946) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=113771.22; total_return_pct=13.7712 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43262367530) |
| akshare | data | ok | — | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43262454187) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43262602264) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43262701123) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43262845798) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43263054006) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=118069.79819488552 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43263198827) |
| simfin | fundamentals | ok | rows_aapl_income.csv=3; rows_companies_us.csv=6592 | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43263343560) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43263441876) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43263648131) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43263792691) |
| finrl | backtest | ok | rows_account_value.csv=124; account_value.csv_last_date=2024-06-28 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43263877911) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43264084192) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43265074594) |
| news-disclosure | news | ok | ticker=NVDA; fetched_at=2026-11-12T17:04:38Z; tool=news-disclosure; news_count=40; disclosure_count=25 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43265222116) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v1)

Base price 164.1995 (pandas-ta). News risk: **shock** — shock headline(s): Nvidia CEO Jensen Huang Resigns—and the Stock Is Falling - Barron's; shock headline(s): S&P 500, Nasdaq fall as Nvidia CEO's exit rattles AI stocks - Reuters; shock headline(s): What to Watch in Nvidia Earnings: Leadership, Data Center Concerns Take Center Stage - Mor.
Confidence is provisional (uncalibrated) until the scoring ledger has history.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.54% | -8.32% … +7.25% | 0.30 |
| week | ⬆ up | +8.07% | -1.39% … +17.53% | 0.30 |
| month | ⬆ up | +17.76% | +10.79% … +24.72% | 0.30 |

Family scores (−1…+1): price-forecast +1.00, technicals +0.10, sentiment -0.31, agent —, fundamentals —.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
