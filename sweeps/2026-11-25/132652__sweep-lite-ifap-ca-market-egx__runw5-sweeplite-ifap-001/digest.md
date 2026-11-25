# 🐊 Borsagator digest — sweep-lite IFAP.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:24 UTC · finished 13:26 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_IFAP.CA.csv=1208; IFAP.CA.csv_last_date=2026-11-23; IFAP.CA.csv_last_close=16.200000762939453 | — |
| openbb | data | ok | rows_IFAP_CA.csv=484; IFAP_CA.csv_last_date=2026-11-24; IFAP_CA.csv_last_close=15.789999961853027 | — |
| egx-data | data | ok | ticker=IFAP.CA; symbol=IFAP; rows_egxpy_ifap.csv=3000; egxpy_ifap.csv_last_date=2026-11-25; egxpy_ifap.csv_last_close=15.82 | — |
| pandas-ta | technicals | ok | macd_signal=-0.5291; ticker=IFAP.CA; date=2026-11-24; open=16.2; high=16.79 | — |
| talib | technicals | ok | ticker=IFAP.CA; drop_before=2019-01-01; rows_fetched=5633; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=3 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=3 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=16.6423 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 15.82 (egx-data/egxpy_ifap.csv, 2026-11-25). Daily volatility σ 2.81% (egx-data/egxpy_ifap.csv (σ60=0.0281, σ10=0.0203)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.16% | -3.28% … +7.60% | 0.35 |
| week (≈3 sessions) | ⬆ up | +2.33% | -6.74% … +11.40% | 0.35 |
| month (≈14 sessions) | ⬆ up | +3.89% | -14.93% … +22.70% | 0.35 |

Family scores (−1…+1): technicals -0.20, sentiment +0.31, agent —, fundamentals +0.15, price-forecast +0.25.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/132652__sweep-lite-ifap-ca-market-egx__runw5-sweeplite-ifap-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-ifap-001`._
