# 🐊 Borsagator digest — sweep-lite OLFI.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 14:38 UTC · finished 14:40 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, finbert-tone, financial-roberta, news-disclosure did not finish cleanly — families absent: sentiment. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_OLFI.CA.csv=1208; OLFI.CA.csv_last_date=2026-11-23; OLFI.CA.csv_last_close=20.3799991607666 | — |
| openbb | data | ok | rows_OLFI_CA.csv=484; OLFI_CA.csv_last_date=2026-11-24; OLFI_CA.csv_last_close=20.3799991607666 | — |
| egx-data | data | ok | ticker=OLFI.CA; symbol=OLFI; rows_egxpy_olfi.csv=2464; egxpy_olfi.csv_last_date=2026-11-25; egxpy_olfi.csv_last_close=20.38 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1429; ticker=OLFI.CA; date=2026-11-24; open=20.38; high=20.38 | — |
| talib | technicals | ok | ticker=OLFI.CA; drop_before=2019-01-01; rows_fetched=2421; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=19.4758 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 20.38 (egx-data/egxpy_olfi.csv, 2026-11-25). Daily volatility σ 1.71% (egx-data/egxpy_olfi.csv (σ60=0.0171, σ10=0.0123)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.05% | -3.28% … +3.18% | 0.35 |
| week (≈3 sessions) | ➡ flat | -0.18% | -5.79% … +5.42% | 0.35 |
| month (≈14 sessions) | ⬇ down | -2.47% | -14.53% … +9.59% | 0.35 |

Family scores (−1…+1): technicals +0.45, sentiment —, agent —, fundamentals +0.15, price-forecast -0.35.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-sentiment (family-did-not-vote); family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/144023__sweep-lite-olfi-ca-market-egx__runw5-sweeplite-olfi-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-olfi-001`._
