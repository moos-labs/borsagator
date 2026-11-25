# 🐊 Borsagator digest — sweep-lite ORHD.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 14:45 UTC · finished 14:47 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, finbert-tone, financial-roberta, news-disclosure did not finish cleanly — families absent: sentiment. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ORHD.CA.csv=1208; ORHD.CA.csv_last_date=2026-11-23; ORHD.CA.csv_last_close=9.979999542236328 | — |
| openbb | data | ok | rows_ORHD_CA.csv=484; ORHD_CA.csv_last_date=2026-11-24; ORHD_CA.csv_last_close=9.979999542236328 | — |
| egx-data | data | ok | ticker=ORHD.CA; symbol=ORHD; rows_egxpy_orhd.csv=3000; egxpy_orhd.csv_last_date=2026-11-25; egxpy_orhd.csv_last_close=10.38 | — |
| pandas-ta | technicals | ok | macd_signal=-2.0659; ticker=ORHD.CA; date=2026-11-24; open=9.98; high=9.98 | — |
| talib | technicals | ok | ticker=ORHD.CA; drop_before=2019-01-01; rows_fetched=4681; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=9.9439 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.38 (egx-data/egxpy_orhd.csv, 2026-11-25). Daily volatility σ 2.65% (egx-data/egxpy_orhd.csv (σ60=0.0265, σ10=0.0246)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -1.82% | -7.28% … +3.63% | 0.35 |
| week (≈3 sessions) | ⬇ down | -1.62% | -10.59% … +7.35% | 0.35 |
| month (≈14 sessions) | ⬇ down | -1.34% | -20.10% … +17.41% | 0.35 |

Family scores (−1…+1): technicals +0.40, sentiment —, agent —, fundamentals +0.40, price-forecast -0.21.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-sentiment (family-did-not-vote); family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/144735__sweep-lite-orhd-ca-market-egx__runw5-sweeplite-orhd-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-orhd-001`._
