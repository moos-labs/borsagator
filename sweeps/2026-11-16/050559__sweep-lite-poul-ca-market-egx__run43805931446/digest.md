# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX

Started 2026-11-16 04:45 UTC · finished 05:05 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-11; POUL.CA.csv_last_close=10.199999809265137 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43805950449) |
| openbb | data | ok | rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-12; POUL_CA.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43806001208) |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-15; egxpy_poul.csv_last_close=10.0 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43806113802) |
| pandas-ta | technicals | ok | macd_signal=-2.9153; ticker=POUL.CA; date=2026-11-12; open=10.2; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43806190078) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43806234451) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43806281889) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43806361416) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43806510151) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=13 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43806587025) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=12 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43806697040) |
| financial-roberta | sentiment | no-summary (failure) | no 'results' artifact on the run | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43806811749) |
| kronos | forecast | no-summary (failure) | artifact carried no summary.json | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43807031623) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43807117554) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-16T05:05:44Z; tool=news-disclosure; news_count=23; disclosure_count=11 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43807193095) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.0 (egx-data/egxpy_poul.csv, 2026-11-15). Daily volatility σ 2.25% (egx-data/egxpy_poul.csv (σ60=0.0225, σ10=0.0186)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de; earnings event: القاهرة للدواجن تخفض أرباحها في تسعة أشهر - ArabFinance; earnings event: اليوم.. نهاية حق الحصول على التوزيع النقدي لـ القاهرة للدواجن - مجلة البوصلة الاقتصادية.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.993, technicals ×0.742, sentiment ×1.024, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -19.00% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.19% | -4.48% … +4.86% | 0.30 |
| week (≈3 sessions) | ➡ flat | +0.26% | -7.84% … +8.37% | 0.30 |
| month (≈14 sessions) | ⬆ up | +1.39% | -15.98% … +18.75% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment -0.03, agent —, fundamentals +0.40, price-forecast —.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
