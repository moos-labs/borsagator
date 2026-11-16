# 🐊 Borsagator digest — sweep-lite POUL.CA
<!-- borsagator-digest-status: complete -->

Started 2026-11-16 18:06 UTC · finished 19:50 UTC · 29 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1210; POUL.CA.csv_last_date=2026-11-16 10:00:00+02:00; POUL.CA.csv_last_close= | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43925390277) |
| openbb | data | ok | rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-12; POUL_CA.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43925535626) |
| egx-data | data | no-summary | artifact download failed: HTTP Error 503: Egress is over the account limit. | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43925731982) |
| pandas-ta | technicals | ok | macd_signal=-2.9153; ticker=POUL.CA; date=2026-11-12; open=10.2; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43925870325) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43925944982) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43926027186) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43926220351) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43926420723) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=12 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43926571198) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=12 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43926784954) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=12 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43927245811) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-13; forecast.csv_last_close=9.6256 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43927445647) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43927694916) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=112565.28; total_return_pct=12.5653 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43927780117) |
| akshare | data | ok | — | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43927916022) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43928053170) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43928199422) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43928332783) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43928534254) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=116172.89894866908 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43928675895) |
| simfin | fundamentals | timeout | no completion within 60 min | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43928818579) |
| qlib | forecast | ok | rows_port_analysis_1day.csv=10; rows_pred.csv=261300; rows_report_normal_1day.csv=871 | [run](https://github.com/moos-labs/qlib-runner/actions/runs/43939417844) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43940078604) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43940279591) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43940417962) |
| finrl | backtest | ok | rows_account_value.csv=114; account_value.csv_last_date=2024-06-27 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43940561036) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43940819293) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43941982029) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-16T19:50:30Z; tool=news-disclosure; news_count=22; disclosure_count=11 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43942132387) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.149999618530273 (openbb/poul_ca.csv, 2026-11-12). Daily volatility σ 17.65% (quantstats/ohlc.csv (σ60=0.1765, σ10=0.0183)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.71/day). News risk: **shock** — earnings event: القاهرة للدواجن تتصدر الأسهم الأكثر تراجعًا بالبورصة بخسائر 17% - شبكة تواصل الإخبارية; earnings event: Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de; earnings event: اليوم.. نهاية حق الحصول على التوزيع النقدي لـ القاهرة للدواجن - مجلة البوصلة الاقتصادية.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.843, technicals ×0.725, sentiment ×1.009, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -18.72% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.90% | -34.73% … +38.54% | 0.30 |
| week (≈4 sessions) | ➡ flat | -0.61% | -74.10% … +72.88% | 0.30 |
| month (≈15 sessions) | ⬆ up | +4.77% | -140.22% … +149.76% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment -0.09, agent —, fundamentals +0.40, price-forecast -0.04.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
