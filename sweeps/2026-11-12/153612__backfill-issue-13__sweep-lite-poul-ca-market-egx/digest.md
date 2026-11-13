# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX

Started 2026-11-12 15:19 UTC · finished 15:36 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1255; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=356.69000244140625; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43246531015) |
| openbb | data | ok | rows_AAPL.csv=502; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=356.69000244140625; rows_POUL_CA.csv=485; POUL_CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43246616210) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-12; egxpy_poul.csv_last_close=10.15 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43246892931) |
| pandas-ta | technicals | ok | macd_signal=-3.1305; ticker=POUL.CA; date=2026-11-11; open=10.29; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43247100884) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6521; rows_used=1921; last_date=2026-11-11; last_close=10.199999809265137 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43247188731) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2179; rows_ohlc.csv=2179 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43247279437) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2428; poul_ohlc.csv_last_close=10.199999809265137 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43247487687) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43247763998) |
| finbert | sentiment | ok | label=poul-pilot; model=ProsusAI/finbert; count=13 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43247912540) |
| finbert-tone | sentiment | ok | label=run; model=yiyanghkust/finbert-tone; count=13 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43248240129) |
| financial-roberta | sentiment | ok | label=run; model=soleimanian/financial-roberta-large-sentiment; count=13 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43248511438) |
| kronos | forecast | ok | rows_forecast.csv=10; forecast.csv_last_date=2026-11-24; forecast.csv_last_close=9.5423 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43248868539) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43249082547) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-12T15:35:54Z; tool=news-disclosure; news_count=40; disclosure_count=7 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43249234784) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._
