# 🐊 Borsagator digest — sweep-lite MPCO.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 14:14 UTC · finished 14:16 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, finbert-tone, financial-roberta, news-disclosure did not finish cleanly — families absent: sentiment. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_MPCO.CA.csv=1208; MPCO.CA.csv_last_date=2026-11-23; MPCO.CA.csv_last_close=1.9199999570846558 | — |
| openbb | data | ok | rows_MPCO_CA.csv=484; MPCO_CA.csv_last_date=2026-11-24; MPCO_CA.csv_last_close=1.9199999570846558 | — |
| egx-data | data | ok | ticker=MPCO.CA; symbol=MPCO; rows_egxpy_mpco.csv=3000; egxpy_mpco.csv_last_date=2026-11-25; egxpy_mpco.csv_last_close=1.88 | — |
| pandas-ta | technicals | ok | macd_signal=-0.0424; ticker=MPCO.CA; date=2026-11-24; open=1.92; high=1.92 | — |
| talib | technicals | ok | ticker=MPCO.CA; drop_before=2019-01-01; rows_fetched=5840; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=1.9592 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 1.88 (egx-data/egxpy_mpco.csv, 2026-11-25). Daily volatility σ 4.77% (egx-data/egxpy_mpco.csv (σ60=0.0477, σ10=0.0378)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.48% | -5.82% … +10.78% | 0.35 |
| week (≈3 sessions) | ⬆ up | +3.93% | -10.32% … +18.19% | 0.35 |
| month (≈14 sessions) | ⬆ up | +1.20% | -32.01% … +34.42% | 0.35 |

Family scores (−1…+1): technicals +0.15, sentiment —, agent —, fundamentals -0.35, price-forecast +0.12.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-sentiment (family-did-not-vote); family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/141625__sweep-lite-mpco-ca-market-egx__runw5-sweeplite-mpco-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-mpco-001`._
