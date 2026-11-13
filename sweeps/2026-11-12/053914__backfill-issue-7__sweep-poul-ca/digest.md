# 🐊 Borsagator digest — sweep POUL.CA

Started 2026-11-12 04:53 UTC · finished 05:39 UTC · 30 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1254; AAPL.csv_last_date=2026-11-11; AAPL.csv_last_close=355.6300048828125; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-09 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43157703755) |
| openbb | data | ok | rows_AAPL.csv=501; AAPL.csv_last_date=2026-11-11; AAPL.csv_last_close=355.6300048828125; rows_POUL_CA.csv=484; POUL_CA.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43157750458) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-11; egxpy_poul.csv_last_close=10.2 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43157836633) |
| pandas-ta | technicals | ok | macd_signal=-3.3575; ticker=POUL.CA; date=2026-11-10; open=9.99; high=10.37 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43157965304) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6520; rows_used=1920; last_date=2026-11-10; last_close=10.289999961853027 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43158048135) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2178; rows_ohlc.csv=2178 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43158095851) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2427; poul_ohlc.csv_last_close=10.289999961853027 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43158177383) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43158325476) |
| finbert | sentiment | ok | label=poul-pilot; model=ProsusAI/finbert; count=13 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43158409472) |
| finbert-tone | sentiment | ok | label=run; model=yiyanghkust/finbert-tone; count=13 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43158548839) |
| financial-roberta | sentiment | ok | label=run; model=soleimanian/financial-roberta-large-sentiment; count=13 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43158672228) |
| tradingagents | agent | ok | final_rating=Hold; company_of_interest=POUL.CA; asset_type=stock; trade_date=2026-11-12; past_context= | [run](https://github.com/moos-labs/tradingagents-runner/actions/runs/43158838072) |
| kronos | forecast | ok | rows_forecast.csv=10; forecast.csv_last_date=2026-11-23; forecast.csv_last_close=9.9802 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43159733109) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-09 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43159863437) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=113204.61; total_return_pct=13.2046 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43159914147) |
| akshare | data | ok | rows_a_share_600519.csv=243 | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43159968101) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43160021195) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43160109193) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43160210317) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43160336293) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=118248.56745147731 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43160428776) |
| simfin | fundamentals | ok | rows_aapl_income.csv=3; rows_companies_us.csv=6593 | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43160516161) |
| qlib | forecast | ok | rows_port_analysis_1day.csv=10; rows_pred.csv=261300; rows_report_normal_1day.csv=871 | [run](https://github.com/moos-labs/qlib-runner/actions/runs/43160604553) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43160999005) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43161128139) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43161220018) |
| finrl | backtest | ok | rows_account_value.csv=114; account_value.csv_last_date=2024-06-27 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43161308450) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43161463864) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43162142897) |
| finrobot | agent | ok | verdict=## VERDICT: bullish - the stock has shown positive momentum and is currently trading above key support levels.; tool=finrobot; ticker=POUL.CA; model=command-r-08-2024; messages=3 | [run](https://github.com/moos-labs/finrobot-runner/actions/runs/43162232108) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._
