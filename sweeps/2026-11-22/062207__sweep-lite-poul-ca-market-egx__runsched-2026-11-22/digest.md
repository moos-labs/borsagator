# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-22 06:15 UTC · finished 06:22 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-18; POUL.CA.csv_last_close=7.699999809265137 | — |
| openbb | data | ok | rows_POUL_CA.csv=482; POUL_CA.csv_last_date=2026-11-19; POUL_CA.csv_last_close=7.579999923706055 | — |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-19; egxpy_poul.csv_last_close=7.58 | — |
| pandas-ta | technicals | ok | macd_signal=-2.4166; ticker=POUL.CA; date=2026-11-19; open=7.7; high=7.84 | — |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6526; rows_used=1926; last_date=2026-11-19; last_close=7.579999923706055 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2184; rows_ohlc.csv=2184 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2433; poul_ohlc.csv_last_close=7.579999923706055 | — |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=16 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=16 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=16 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-17; forecast.csv_last_close=8.9139 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-22T06:22:06Z; tool=news-disclosure; news_count=27; disclosure_count=10 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 7.58 (egx-data/egxpy_poul.csv, 2026-11-19). Daily volatility σ 6.75% (egx-data/egxpy_poul.csv (σ60=0.0367, σ10=0.0675)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **elevated**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.503, technicals ×0.717, sentiment ×1.069, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -25.07% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted. — via verified EGX disclosure event ev_bf7532c5c9185f9f113d (verbatim ex-date)

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +4.98% | -6.58% … +16.54% | 0.45 |
| week (≈3 sessions) | ⬆ up | +9.67% | -10.63% … +29.96% | 0.45 |
| month (≈14 sessions) | ⬆ up | +15.16% | -26.33% … +56.65% | 0.45 |

Family scores (−1…+1): technicals +0.50, sentiment -0.02, agent —, fundamentals +0.40, price-forecast +0.35.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22`; point-in-time inputs in `worker-runs/2026-11-22/sched-2026-11-22`._
