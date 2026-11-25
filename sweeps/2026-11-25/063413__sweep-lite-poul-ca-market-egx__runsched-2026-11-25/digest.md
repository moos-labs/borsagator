# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 06:26 UTC · finished 06:34 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1208; POUL.CA.csv_last_date=2026-11-22; POUL.CA.csv_last_close=7.03000020980835 | — |
| openbb | data | ok | rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-23; POUL_CA.csv_last_close=7.099999904632568 | — |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-24; egxpy_poul.csv_last_close=6.86 | — |
| pandas-ta | technicals | ok | macd_signal=-2.2793; ticker=POUL.CA; date=2026-11-23; open=7.03; high=7.23 | — |
| talib | technicals | ok | ticker=POUL.CA; drop_before=2019-01-01; rows_fetched=6528; rows_used=1928; last_date=2026-11-23 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2186; rows_ohlc.csv=2186 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2435; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=12 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=12 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=12 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-21; forecast.csv_last_close=9.3557 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-25T06:34:12Z; tool=news-disclosure; news_count=31; disclosure_count=10 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 6.86 (egx-data/egxpy_poul.csv, 2026-11-24). Daily volatility σ 6.59% (egx-data/egxpy_poul.csv (σ60=0.0380, σ10=0.0659)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Cairo Poultry stock: Nine-month net profit falls 38.3% - ad-hoc-news.de.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -27.70% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted. — via verified EGX disclosure event ev_bf7532c5c9185f9f113d (verbatim ex-date)

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +3.39% | -10.44% … +17.23% | 0.30 |
| week (≈3 sessions) | ⬆ up | +10.92% | -13.72% … +35.56% | 0.30 |
| month (≈14 sessions) | ⬆ up | +27.27% | -24.36% … +78.90% | 0.30 |

Family scores (−1…+1): technicals +0.50, sentiment +0.06, agent —, fundamentals +0.40, price-forecast +0.74.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/063413__sweep-lite-poul-ca-market-egx__runsched-2026-11-25`; point-in-time inputs in `worker-runs/2026-11-25/sched-2026-11-25`._
