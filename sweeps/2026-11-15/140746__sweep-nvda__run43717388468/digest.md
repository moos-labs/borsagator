# 🐊 Borsagator digest — sweep NVDA

Started 2026-11-15 13:08 UTC · finished 14:07 UTC · 31 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1255; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43717405759) |
| openbb | data | ok | rows_AAPL.csv=500; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43717450278) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-15; egxpy_poul.csv_last_close=10.0 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43717520307) |
| pandas-ta | technicals | ok | macd_signal=-2.9153; ticker=POUL.CA; date=2026-11-12; open=10.2; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43717593051) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43717636157) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43717678095) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43717746891) |
| financetoolkit | fundamentals | ok | — | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43717850508) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=40 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43717915853) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=40 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43717981140) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=40 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43718081844) |
| tradingagents | agent | ok | final_rating=Hold; company_of_interest=NVDA; asset_type=stock; trade_date=2026-11-15; past_context= | [run](https://github.com/moos-labs/tradingagents-runner/actions/runs/43718239932) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-13; forecast.csv_last_close=180.6044 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43719821263) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43719917260) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=113398.53; total_return_pct=13.3985 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43719955494) |
| akshare | data | ok | — | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43719994406) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43720032891) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43720098781) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43720165160) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43720268089) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=117078.7471466067 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43720335318) |
| simfin | fundamentals | ok | rows_aapl_income.csv=5; rows_companies_us.csv=6592 | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43720403764) |
| qlib | forecast | ok | rows_port_analysis_1day.csv=10; rows_pred.csv=261300; rows_report_normal_1day.csv=871 | [run](https://github.com/moos-labs/qlib-runner/actions/runs/43720442751) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43720689138) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43720760310) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43720830078) |
| finrl | backtest | ok | rows_account_value.csv=124; account_value.csv_last_date=2024-06-28 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43720869680) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43720999486) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43721548902) |
| finrobot | agent | ok | verdict=## VERDICT: bearish - the recent CEO scandal and departure have caused a significant drop in stock price.; tool=finrobot; ticker=NVDA; model=command-r-08-2024; messages=5 | [run](https://github.com/moos-labs/finrobot-runner/actions/runs/43721616956) |
| news-disclosure | news | ok | ticker=NVDA; fetched_at=2026-11-15T14:07:29Z; tool=news-disclosure; news_count=40; disclosure_count=25 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43722322288) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._
