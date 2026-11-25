# 🐊 Borsagator digest — sweep-lite ORWE.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 14:52 UTC · finished 14:55 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ORWE.CA.csv=1208; ORWE.CA.csv_last_date=2026-11-23; ORWE.CA.csv_last_close=24.700000762939453 | — |
| openbb | data | ok | rows_ORWE_CA.csv=484; ORWE_CA.csv_last_date=2026-11-24; ORWE_CA.csv_last_close=24.700000762939453 | — |
| egx-data | data | ok | ticker=ORWE.CA; symbol=ORWE; rows_egxpy_orwe.csv=3000; egxpy_orwe.csv_last_date=2026-11-25; egxpy_orwe.csv_last_close=24.0 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1897; ticker=ORWE.CA; date=2026-11-24; open=24.7; high=25.48 | — |
| talib | technicals | ok | ticker=ORWE.CA; drop_before=2019-01-01; rows_fetched=6533; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=1 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=24.7419 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ORWE.CA; fetched_at=2026-11-25T14:55:14Z; tool=news-disclosure; news_count=1; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 24.0 (egx-data/egxpy_orwe.csv, 2026-11-25). Daily volatility σ 2.43% (egx-data/egxpy_orwe.csv (σ60=0.0243, σ10=0.0145)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Orezone Gold Corporation (ORE.TO) Stock Price, News, Quote & History - Yahoo! Finance Cana.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.13% | -3.47% … +7.73% | 0.30 |
| week (≈3 sessions) | ⬆ up | +2.60% | -6.74% … +11.93% | 0.30 |
| month (≈14 sessions) | ⬆ up | +2.82% | -16.88% … +22.53% | 0.30 |

Family scores (−1…+1): technicals -0.30, sentiment -0.00, agent —, fundamentals +0.40, price-forecast +0.17.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/145515__sweep-lite-orwe-ca-market-egx__runw5-sweeplite-orwe-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-orwe-001`._
