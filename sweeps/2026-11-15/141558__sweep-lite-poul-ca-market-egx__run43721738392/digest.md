# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX

Started 2026-11-15 13:58 UTC · finished 14:15 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1255; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43721761063) |
| openbb | data | ok | rows_AAPL.csv=500; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43721798361) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-15; egxpy_poul.csv_last_close=10.0 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43721890649) |
| pandas-ta | technicals | ok | macd_signal=-2.9153; ticker=POUL.CA; date=2026-11-12; open=10.2; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43721966066) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43722045053) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43722086160) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43722157888) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43722268160) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=10 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43722340314) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=10 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43722444815) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=9 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43722552677) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-10; forecast.csv_last_close=9.7086 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43722718758) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43722789743) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-15T14:15:35Z; tool=news-disclosure; news_count=22; disclosure_count=2 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43722864089) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.15 (pandas-ta). Daily volatility σ 2.25% (egx-data/egxpy_poul.csv (σ60=0.0225, σ10=0.0186)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: اليوم.. نهاية حق الحصول على التوزيع النقدي لـ القاهرة للدواجن - مجلة البوصلة الاقتصادية.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.21% | -3.43% … +5.84% | 0.30 |
| week (≈3 sessions) | ⬇ down | -1.00% | -9.29% … +7.29% | 0.30 |
| month (≈14 sessions) | ⬇ down | -1.91% | -20.44% … +16.61% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment -0.00, agent —, fundamentals +0.40, price-forecast -0.26.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
