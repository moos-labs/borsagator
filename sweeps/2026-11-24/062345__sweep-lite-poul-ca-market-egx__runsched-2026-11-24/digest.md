# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-24 06:16 UTC · finished 06:23 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-22 10:00:00+02:00; POUL.CA.csv_last_close=7.03000020980835 | — |
| openbb | data | ok | rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-22; POUL_CA.csv_last_close=7.03000020980835 | — |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-23; egxpy_poul.csv_last_close=7.1 | — |
| pandas-ta | technicals | ok | macd_signal=-2.3435; ticker=POUL.CA; date=2026-11-22; open=7.58; high=7.48 | — |
| talib | technicals | ok | ticker=POUL.CA; drop_before=2019-01-01; rows_fetched=6527; rows_used=1927; last_date=2026-11-22 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2185; rows_ohlc.csv=2185 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2434; poul_ohlc.csv_last_close=7.03000020980835 | — |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=16 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=16 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=16 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-21; forecast.csv_last_close=9.4439 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-24T06:23:44Z; tool=news-disclosure; news_count=31; disclosure_count=10 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 7.1 (egx-data/egxpy_poul.csv, 2026-11-23). Daily volatility σ 6.92% (egx-data/egxpy_poul.csv (σ60=0.0378, σ10=0.0692)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Cairo Poultry stock: Nine-month net profit falls 38.3% - ad-hoc-news.de.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.689, sentiment ×1.072, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -26.76% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted. — via verified EGX disclosure event ev_bf7532c5c9185f9f113d (verbatim ex-date)

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.04% | -13.74% … +15.83% | 0.30 |
| week (≈3 sessions) | ⬆ up | +4.82% | -20.40% … +30.03% | 0.30 |
| month (≈14 sessions) | ⬆ up | +25.29% | -28.35% … +78.92% | 0.30 |

Family scores (−1…+1): technicals +0.50, sentiment +0.05, agent —, fundamentals +0.40, price-forecast +0.64.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24`; point-in-time inputs in `worker-runs/2026-11-24/sched-2026-11-24`._
