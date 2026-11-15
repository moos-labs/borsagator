# 🐊 Borsagator digest — sweep-lite POUL.CA

Started 2026-11-15 07:09 UTC · finished 07:47 UTC · 29 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1255; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL.CA.csv=1210; POUL.CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43688689257) |
| openbb | data | ok | rows_AAPL.csv=500; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43688725736) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-12; egxpy_poul.csv_last_close=10.15 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43688790561) |
| pandas-ta | technicals | ok | macd_signal=-2.9153; ticker=POUL.CA; date=2026-11-12; open=10.2; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43688850352) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43688885722) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43688948536) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43689008851) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43689096706) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=11 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43689156976) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=11 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43689266404) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=11 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43689347077) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-10; forecast.csv_last_close=9.7086 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43689455578) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43689546710) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=113398.53; total_return_pct=13.3985 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43689580157) |
| akshare | data | ok | — | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43689612652) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43689649336) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43689710032) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43689768051) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43689848491) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=117078.7471466067 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43689883089) |
| simfin | fundamentals | ok | rows_aapl_income.csv=5; rows_companies_us.csv=6592 | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43689939281) |
| qlib | forecast | ok | rows_port_analysis_1day.csv=10; rows_pred.csv=261300; rows_report_normal_1day.csv=871 | [run](https://github.com/moos-labs/qlib-runner/actions/runs/43689971582) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43690144695) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43690227476) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43690293147) |
| finrl | backtest | ok | rows_account_value.csv=114; account_value.csv_last_date=2024-06-27 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43690328929) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43690415354) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43690918773) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-15T07:47:30Z; tool=news-disclosure; news_count=23; disclosure_count=2 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43690977089) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.15 (pandas-ta). Daily volatility σ 2.25% (egx-data/egxpy_poul.csv (σ60=0.0225, σ10=0.0183)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: «القاهرة للدواجن» تحقق أرباحًا بقيمة 1.43 مليار جنيه خلال 9 أشهر بتراجع 39.1% - شبكة تواصل; earnings event: رغم ارتفاع الإيرادات.. أرباح القاهرة للدواجن تهبط 39% بأول 9 شهور من 2026 - https://www.yo; earnings event: القاهرة للدواجن تسجل 1.43 مليار جنيه أرباحًا خلال 9 أشهر - عالم المال.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.22% | -3.37% … +5.81% | 0.30 |
| week (≈3 sessions) | ⬇ down | -0.92% | -9.23% … +7.38% | 0.30 |
| month (≈14 sessions) | ⬇ down | -1.88% | -20.34% … +16.57% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment +0.03, agent —, fundamentals +0.40, price-forecast -0.26.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
