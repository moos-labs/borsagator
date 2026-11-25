# 🐊 Borsagator digest — sweep-lite EGAS.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 12:24 UTC · finished 12:27 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EGAS.CA.csv=1209; EGAS.CA.csv_last_date=2026-11-23; EGAS.CA.csv_last_close=49.099998474121094 | — |
| openbb | data | ok | rows_EGAS_CA.csv=484; EGAS_CA.csv_last_date=2026-11-24; EGAS_CA.csv_last_close=49.099998474121094 | — |
| egx-data | data | ok | ticker=EGAS.CA; symbol=EGAS; rows_egxpy_egas.csv=3000; egxpy_egas.csv_last_date=2026-11-25; egxpy_egas.csv_last_close=49.0 | — |
| pandas-ta | technicals | ok | macd_signal=-0.7644; ticker=EGAS.CA; date=2026-11-24; open=49.1; high=50.95 | — |
| talib | technicals | ok | ticker=EGAS.CA; drop_before=2019-01-01; rows_fetched=6422; rows_used=1930; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=16 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=11 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=11 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=47.7701 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EGAS.CA; fetched_at=2026-11-25T12:27:20Z; tool=news-disclosure; news_count=8; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 49.0 (egx-data/egxpy_egas.csv, 2026-11-25). Daily volatility σ 2.81% (egx-data/egxpy_egas.csv (σ60=0.0281, σ10=0.0227)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.05% | -3.84% … +3.74% | 0.60 |
| week (≈3 sessions) | ⬇ down | -1.52% | -8.41% … +5.37% | 0.60 |
| month (≈14 sessions) | ⬇ down | -1.73% | -15.97% … +12.50% | 0.60 |

Family scores (−1…+1): technicals +0.15, sentiment +0.20, agent —, fundamentals -0.10, price-forecast -0.12.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/122721__sweep-lite-egas-ca-market-egx__runw5-sweeplite-egas-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-egas-001`._
