# 🐊 Borsagator digest — sweep-lite LCSW.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:47 UTC · finished 13:50 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_LCSW.CA.csv=1208; LCSW.CA.csv_last_date=2026-11-23; LCSW.CA.csv_last_close=40.439998626708984 | — |
| openbb | data | ok | rows_LCSW_CA.csv=484; LCSW_CA.csv_last_date=2026-11-24; LCSW_CA.csv_last_close=40.439998626708984 | — |
| egx-data | data | ok | ticker=LCSW.CA; symbol=LCSW; rows_egxpy_lcsw.csv=3000; egxpy_lcsw.csv_last_date=2026-11-25; egxpy_lcsw.csv_last_close=41.39 | — |
| pandas-ta | technicals | ok | macd_signal=1.566; ticker=LCSW.CA; date=2026-11-24; open=40.44; high=40.44 | — |
| talib | technicals | ok | ticker=LCSW.CA; drop_before=2019-01-01; rows_fetched=4686; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=4 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=4 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=4 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=35.9874 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 41.39 (egx-data/egxpy_lcsw.csv, 2026-11-25). Daily volatility σ 3.07% (egx-data/egxpy_lcsw.csv (σ60=0.0307, σ10=0.0237)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -1.48% | -7.33% … +4.38% | 0.35 |
| week (≈3 sessions) | ⬇ down | -1.98% | -11.92% … +7.95% | 0.35 |
| month (≈14 sessions) | ⬇ down | -7.95% | -30.14% … +14.24% | 0.35 |

Family scores (−1…+1): technicals +0.30, sentiment +0.01, agent —, fundamentals +0.15, price-forecast -0.57.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/135002__sweep-lite-lcsw-ca-market-egx__runw5-sweeplite-lcsw-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-lcsw-001`._
