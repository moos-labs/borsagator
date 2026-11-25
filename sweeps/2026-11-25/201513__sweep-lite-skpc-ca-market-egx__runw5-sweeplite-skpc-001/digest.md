# 🐊 Borsagator digest — sweep-lite SKPC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 20:13 UTC · finished 20:15 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, finbert-tone, financial-roberta, news-disclosure did not finish cleanly — families absent: sentiment. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_SKPC.CA.csv=1208; SKPC.CA.csv_last_date=2026-11-23; SKPC.CA.csv_last_close=14.180000305175781 | — |
| openbb | data | ok | rows_SKPC_CA.csv=484; SKPC_CA.csv_last_date=2026-11-24; SKPC_CA.csv_last_close=14.180000305175781 | — |
| egx-data | data | ok | ticker=SKPC.CA; symbol=SKPC; rows_egxpy_skpc.csv=3000; egxpy_skpc.csv_last_date=2026-11-25; egxpy_skpc.csv_last_close=14.76 | — |
| pandas-ta | technicals | ok | macd_signal=-0.3103; ticker=SKPC.CA; date=2026-11-24; open=14.18; high=14.18 | — |
| talib | technicals | ok | ticker=SKPC.CA; drop_before=2019-01-01; rows_fetched=5343; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=16 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=14.9786 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 14.76 (egx-data/egxpy_skpc.csv, 2026-11-25). Daily volatility σ 2.24% (egx-data/egxpy_skpc.csv (σ60=0.0224, σ10=0.0217)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.35% … +3.35% | 0.35 |
| week | ➡ flat | +0.00% | -8.33% … +8.33% | 0.35 |
| month | ➡ flat | +0.00% | -16.01% … +16.01% | 0.35 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals -0.10, price-forecast +0.07.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-sentiment (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-25/201513__sweep-lite-skpc-ca-market-egx__runw5-sweeplite-skpc-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-skpc-001`._
