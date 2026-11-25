# 🐊 Borsagator digest — sweep-lite FAITA.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:02 UTC · finished 13:04 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_FAITA.CA.csv=1208; FAITA.CA.csv_last_date=2026-11-23; FAITA.CA.csv_last_close=1.0 | — |
| openbb | data | ok | rows_FAITA_CA.csv=484; FAITA_CA.csv_last_date=2026-11-24; FAITA_CA.csv_last_close=1.0 | — |
| egx-data | data | ok | ticker=FAITA.CA; symbol=FAITA; rows_egxpy_faita.csv=3000; egxpy_faita.csv_last_date=2026-11-25; egxpy_faita.csv_last_close=1.0 | — |
| pandas-ta | technicals | ok | macd_signal=0.003; ticker=FAITA.CA; date=2026-11-24; open=1.0; high=1.0 | — |
| talib | technicals | ok | ticker=FAITA.CA; drop_before=2019-01-01; rows_fetched=5632; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | — | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=5 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=5 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=5 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=0.9895 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=FAITA.CA; fetched_at=2026-11-25T13:04:39Z; tool=news-disclosure; news_count=1; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 1.0 (egx-data/egxpy_faita.csv, 2026-11-25). Daily volatility σ 0.81% (egx-data/egxpy_faita.csv (σ60=0.0081, σ10=0.0034)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.16% | -0.95% … +1.27% | 0.60 |
| week (≈3 sessions) | ➡ flat | +0.28% | -1.64% … +2.19% | 0.60 |
| month (≈14 sessions) | ⬇ down | -0.80% | -4.91% … +3.32% | 0.60 |

Family scores (−1…+1): technicals -0.15, sentiment +0.13, agent —, fundamentals —, price-forecast -0.17.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); family-fundamentals (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/130440__sweep-lite-faita-ca-market-egx__runw5-sweeplite-faita-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-faita-001`._
