# 🐊 Borsagator digest — sweep-lite ICFC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:17 UTC · finished 13:19 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ICFC.CA.csv=1208; ICFC.CA.csv_last_date=2026-11-23; ICFC.CA.csv_last_close=26.100000381469727 | — |
| openbb | data | ok | rows_ICFC_CA.csv=484; ICFC_CA.csv_last_date=2026-11-24; ICFC_CA.csv_last_close=26.540000915527344 | — |
| egx-data | data | ok | ticker=ICFC.CA; symbol=ICFC; rows_egxpy_icfc.csv=3000; egxpy_icfc.csv_last_date=2026-11-25; egxpy_icfc.csv_last_close=26.8 | — |
| pandas-ta | technicals | ok | macd_signal=1.0883; ticker=ICFC.CA; date=2026-11-24; open=26.1; high=27.27 | — |
| talib | technicals | ok | ticker=ICFC.CA; drop_before=2019-01-01; rows_fetched=2013; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=16 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=3 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=3 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=23.4672 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 26.8 (egx-data/egxpy_icfc.csv, 2026-11-25). Daily volatility σ 4.43% (egx-data/egxpy_icfc.csv (σ60=0.0443, σ10=0.0437)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -1.53% | -9.61% … +6.55% | 0.35 |
| week (≈3 sessions) | ⬇ down | -3.48% | -17.65% … +10.69% | 0.35 |
| month (≈14 sessions) | ⬇ down | -8.88% | -38.68% … +20.92% | 0.35 |

Family scores (−1…+1): technicals -0.30, sentiment +0.16, agent —, fundamentals -0.10, price-forecast -0.38.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/131935__sweep-lite-icfc-ca-market-egx__runw5-sweeplite-icfc-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-icfc-001`._
