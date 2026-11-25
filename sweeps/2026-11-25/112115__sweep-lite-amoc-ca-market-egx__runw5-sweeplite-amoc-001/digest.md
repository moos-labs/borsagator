# 🐊 Borsagator digest — sweep-lite AMOC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 11:15 UTC · finished 11:21 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AMOC.CA.csv=1208; AMOC.CA.csv_last_date=2026-11-23; AMOC.CA.csv_last_close=12.510000228881836 | — |
| openbb | data | ok | rows_AMOC_CA.csv=484; AMOC_CA.csv_last_date=2026-11-24; AMOC_CA.csv_last_close=12.25 | — |
| egx-data | data | ok | ticker=AMOC.CA; symbol=AMOC; rows_egxpy_amoc.csv=3000; egxpy_amoc.csv_last_date=2026-11-25; egxpy_amoc.csv_last_close=12.0 | — |
| pandas-ta | technicals | ok | macd_signal=-0.0764; ticker=AMOC.CA; date=2026-11-24; open=12.51; high=12.7 | — |
| talib | technicals | ok | ticker=AMOC.CA; drop_before=2019-01-01; rows_fetched=5067; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=9 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=9 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=9 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=13.3067 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=AMOC.CA; fetched_at=2026-11-25T11:21:14Z; tool=news-disclosure; news_count=3; disclosure_count=6 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 12.0 (egx-data/egxpy_amoc.csv, 2026-11-25). Daily volatility σ 2.56% (egx-data/egxpy_amoc.csv (σ60=0.0256, σ10=0.0242)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **elevated** — 1 disclosure(s) in the last 3 days.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +3.68% | -1.32% … +8.68% | 0.45 |
| week (≈3 sessions) | ⬆ up | +3.37% | -4.63% … +11.37% | 0.45 |
| month (≈14 sessions) | ⬆ up | +7.41% | -9.19% … +24.00% | 0.45 |

Family scores (−1…+1): technicals -0.20, sentiment -0.09, agent —, fundamentals +0.15, price-forecast +0.57.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/112115__sweep-lite-amoc-ca-market-egx__runw5-sweeplite-amoc-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-amoc-001`._
