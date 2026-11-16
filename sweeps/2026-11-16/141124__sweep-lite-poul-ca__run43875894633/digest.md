# 🐊 Borsagator digest — sweep-lite POUL.CA

Started 2026-11-16 13:27 UTC · finished 14:11 UTC · 29 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1210; POUL.CA.csv_last_date=2026-11-16 10:00:00+02:00; POUL.CA.csv_last_close= | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43875933196) |
| openbb | data | ok | rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-12; POUL_CA.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43876006437) |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-16; egxpy_poul.csv_last_close=8.02 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43876137437) |
| pandas-ta | technicals | ok | macd_signal=-2.9153; ticker=POUL.CA; date=2026-11-12; open=10.2; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43876265682) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43876346285) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43876484773) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43876618374) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43876862937) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=12 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43876991404) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=12 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43877186145) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=12 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43877384546) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-13; forecast.csv_last_close=9.6256 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43877625171) |
| pandas-datareader | data | ok | rows_fred_DGS10.csv=259; fred_DGS10.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/pandas-datareader-runner/actions/runs/43877809606) |
| backtrader | backtest | ok | ticker=AAPL; strategy=SMA20 cross (buy on cross above, close on cross below, 95% cash stake); start_value=100000.0; final_value=113398.53; total_return_pct=13.3985 | [run](https://github.com/moos-labs/backtrader-runner/actions/runs/43877887673) |
| akshare | data | ok | — | [run](https://github.com/moos-labs/akshare-runner/actions/runs/43877964095) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43878097551) |
| pybroker | backtest | ok | tool=pybroker; ticker=AAPL; strategy=long when close crosses above 20-day SMA, exit all when close crosses below it; initial_cash=100000; sma_period=20 | [run](https://github.com/moos-labs/pybroker-runner/actions/runs/43878230670) |
| finvizfinance | data | ok | Company=Apple Inc; Sector=Technology; Industry=Consumer Electronics; Country=USA; Exchange=NASD | [run](https://github.com/moos-labs/finvizfinance-runner/actions/runs/43878361550) |
| edgartools | fundamentals | ok | ticker=AAPL; company_name=Apple Inc.; cik=320193; identity=Moos Labs research moos@sherbeeny.com | [run](https://github.com/moos-labs/edgartools-runner/actions/runs/43878547631) |
| bt | backtest | ok | tool=bt; tool_description=bt - Flexible Backtesting for Python (by pmorissette); initial_capital_requested=100000.0; start_value=100000.0; final_value=117081.28694152797 | [run](https://github.com/moos-labs/bt-runner/actions/runs/43878677441) |
| simfin | fundamentals | ok | rows_aapl_income.csv=5; rows_companies_us.csv=6592 | [run](https://github.com/moos-labs/simfin-runner/actions/runs/43878814949) |
| qlib | forecast | ok | rows_port_analysis_1day.csv=10; rows_pred.csv=261300; rows_report_normal_1day.csv=871 | [run](https://github.com/moos-labs/qlib-runner/actions/runs/43878952580) |
| zipline | backtest | ok | — | [run](https://github.com/moos-labs/zipline-runner/actions/runs/43879479183) |
| vnpy | backtest | ok | start_date=2023-11-01; end_date=2026-10-30; total_days=752; profit_days=330; loss_days=320 | [run](https://github.com/moos-labs/vnpy-runner/actions/runs/43879722732) |
| nautilus | backtest | ok | — | [run](https://github.com/moos-labs/nautilus-runner/actions/runs/43879854822) |
| finrl | backtest | ok | rows_account_value.csv=114; account_value.csv_last_date=2024-06-27 | [run](https://github.com/moos-labs/finrl-runner/actions/runs/43879989039) |
| lean | backtest | ok | succeeded-data-requests-count=2; failed-data-requests-count=0; succeeded-universe-data-requests-count=0; failed-universe-data-requests-count=0; total-data-requests-count=2 | [run](https://github.com/moos-labs/lean-runner/actions/runs/43880173316) |
| stocksharp | backtest | ok | — | [run](https://github.com/moos-labs/stocksharp-runner/actions/runs/43881371472) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-16T14:11:04Z; tool=news-disclosure; news_count=22; disclosure_count=11 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43881510876) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 8.02 (egx-data/egxpy_poul.csv, 2026-11-16). Daily volatility σ 6.77% (egx-data/egxpy_poul.csv (σ60=0.0360, σ10=0.0677)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de; earnings event: اليوم.. نهاية حق الحصول على التوزيع النقدي لـ القاهرة للدواجن - مجلة البوصلة الاقتصادية; price confirms: last session 3.3σ.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.993, technicals ×0.742, sentiment ×1.024, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -23.69% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +18.71% | +2.82% … +34.61% | 0.30 |
| week (≈3 sessions) | ⬆ up | +16.73% | -11.04% … +44.49% | 0.30 |
| month (≈14 sessions) | ⬆ up | +16.36% | -35.85% … +68.56% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment -0.10, agent —, fundamentals +0.40, price-forecast +0.40.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
