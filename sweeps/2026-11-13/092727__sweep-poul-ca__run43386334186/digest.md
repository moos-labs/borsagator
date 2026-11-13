# 🐊 Borsagator digest — sweep POUL.CA

Started 2026-11-13 07:31 UTC · finished 09:27 UTC · 31 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1254; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=354.8800048828125; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43386352919) |
| openbb | data | ok | rows_AAPL.csv=501; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=354.8800048828125; rows_POUL_CA.csv=484; POUL_CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43386411773) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-12; egxpy_poul.csv_last_close=10.15 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43386506734) |
| pandas-ta | technicals | ok | macd_signal=-3.1305; ticker=POUL.CA; date=2026-11-11; open=10.29; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43386646647) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6521; rows_used=1921; last_date=2026-11-11; last_close=10.199999809265137 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43386714677) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2179; rows_ohlc.csv=2179 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43386769586) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2428; poul_ohlc.csv_last_close=10.199999809265137 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43386869866) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43387049691) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=10 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43387153046) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=10 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43387286214) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=10 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43387378346) |
| tradingagents | agent | ok | final_rating=Sell; company_of_interest=POUL.CA; asset_type=stock; trade_date=2026-11-13; past_context= | [run](https://github.com/moos-labs/tradingagents-runner/actions/runs/43387556978) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-09; forecast.csv_last_close=9.2404 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43390391103) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43390544759) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=112977.36; total_return_pct=12.9774 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43390606398) |
| akshare | data | ok | rows_us_105.AAPL.csv=251 | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43390665308) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43390776195) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43390884387) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43390988941) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43391140924) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=117659.31024932888 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43391203775) |
| simfin | fundamentals | ok | rows_aapl_income.csv=5; rows_companies_us.csv=6592 | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43391308930) |
| qlib | forecast | ok | rows_port_analysis_1day.csv=10; rows_pred.csv=261300; rows_report_normal_1day.csv=871 | [run](https://github.com/moos-labs/qlib-runner/actions/runs/43391417528) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43391880292) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43391985472) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43392088370) |
| finrl | backtest | ok | rows_account_value.csv=114; account_value.csv_last_date=2024-06-27 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43392197367) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43392380953) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43393243114) |
| finrobot | agent | timeout | no completion within 60 min | [run](https://github.com/moos-labs/finrobot-runner/actions/runs/43393344641) |
| news-disclosure | news | error | could not read COMMANDS variable — left untouched | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.2 (pandas-ta). Daily volatility σ 2.25% (egx-data/egxpy_poul.csv (σ60=0.0225, σ10=0.0183)). News risk: **none**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.38% | -3.69% … +2.94% | 0.59 |
| week | ⬇ down | -1.67% | -9.21% … +5.88% | 0.58 |
| month | ⬇ down | -6.93% | -23.26% … +9.41% | 0.54 |

Family scores (−1…+1): technicals +0.30, sentiment -0.21, agent -0.75, fundamentals +0.40, price-forecast -0.46.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
