# 🐊 Borsagator digest — sweep-lite CLHO.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 11:50 UTC · finished 11:54 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_CLHO.CA.csv=1208; CLHO.CA.csv_last_date=2026-11-23; CLHO.CA.csv_last_close=14.130000114440918 | — |
| openbb | data | ok | rows_CLHO_CA.csv=484; CLHO_CA.csv_last_date=2026-11-24; CLHO_CA.csv_last_close=14.130000114440918 | — |
| egx-data | data | ok | ticker=CLHO.CA; symbol=CLHO; rows_egxpy_clho.csv=2575; egxpy_clho.csv_last_date=2026-11-25; egxpy_clho.csv_last_close=14.34 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1686; ticker=CLHO.CA; date=2026-11-24; open=14.13; high=14.13 | — |
| talib | technicals | ok | ticker=CLHO.CA; drop_before=2019-01-01; rows_fetched=2461; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=1 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=13.6514 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=CLHO.CA; fetched_at=2026-11-25T11:54:25Z; tool=news-disclosure; news_count=30; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 14.34 (egx-data/egxpy_clho.csv, 2026-11-25). Daily volatility σ 1.94% (egx-data/egxpy_clho.csv (σ60=0.0194, σ10=0.0150)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **elevated**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.23% | -3.24% … +3.71% | 0.45 |
| week (≈3 sessions) | ➡ flat | -0.64% | -6.68% … +5.39% | 0.45 |
| month (≈14 sessions) | ⬇ down | -3.76% | -16.46% … +8.94% | 0.45 |

Family scores (−1…+1): technicals +0.45, sentiment -0.36, agent —, fundamentals -0.35, price-forecast -0.33.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/115426__sweep-lite-clho-ca-market-egx__runw5-sweeplite-clho-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-clho-001`._
