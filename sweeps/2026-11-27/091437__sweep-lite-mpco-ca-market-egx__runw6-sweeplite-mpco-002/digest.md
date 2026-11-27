# 🐊 Borsagator digest — sweep-lite MPCO.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 09:12 UTC · finished 09:14 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, finbert-tone, financial-roberta, news-disclosure did not finish cleanly — families absent: sentiment. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_MPCO.CA.csv=1209; MPCO.CA.csv_last_date=2026-11-25; MPCO.CA.csv_last_close=1.8799999952316284 | — |
| openbb | data | ok | rows_MPCO_CA.csv=484; MPCO_CA.csv_last_date=2026-11-26; MPCO_CA.csv_last_close=1.8700000047683716 | — |
| egx-data | data | ok | ticker=MPCO.CA; symbol=MPCO; rows_egxpy_mpco.csv=3000; egxpy_mpco.csv_last_date=2026-11-26; egxpy_mpco.csv_last_close=1.87 | — |
| pandas-ta | technicals | ok | macd_signal=-0.0423; ticker=MPCO.CA; date=2026-11-26; open=1.88; high=1.9 | — |
| talib | technicals | ok | ticker=MPCO.CA; drop_before=2019-01-01; rows_fetched=5842; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=1.9209 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 1.87 (egx-data/egxpy_mpco.csv, 2026-11-26). Daily volatility σ 4.77% (egx-data/egxpy_mpco.csv (σ60=0.0477, σ10=0.0341)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -7.13% … +7.13% | 0.35 |
| week | ➡ flat | +0.00% | -17.74% … +17.74% | 0.35 |
| month | ➡ flat | +0.00% | -34.09% … +34.09% | 0.35 |

Family scores (−1…+1): technicals -0.20, sentiment —, agent —, fundamentals -0.35, price-forecast +0.06.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-sentiment (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/091437__sweep-lite-mpco-ca-market-egx__runw6-sweeplite-mpco-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-mpco-002`._
