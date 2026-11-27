# 🐊 Borsagator digest — sweep-lite ORHD.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 09:46 UTC · finished 09:48 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ORHD.CA.csv=1209; ORHD.CA.csv_last_date=2026-11-25; ORHD.CA.csv_last_close=10.380000114440918 | — |
| openbb | data | ok | rows_ORHD_CA.csv=484; ORHD_CA.csv_last_date=2026-11-26; ORHD_CA.csv_last_close=10.449999809265137 | — |
| egx-data | data | ok | ticker=ORHD.CA; symbol=ORHD; rows_egxpy_orhd.csv=3000; egxpy_orhd.csv_last_date=2026-11-26; egxpy_orhd.csv_last_close=10.45 | — |
| pandas-ta | technicals | ok | macd_signal=-1.7893; ticker=ORHD.CA; date=2026-11-26; open=10.38; high=10.5 | — |
| talib | technicals | ok | ticker=ORHD.CA; drop_before=2019-01-01; rows_fetched=4683; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=1 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=10.2014 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.45 (egx-data/egxpy_orhd.csv, 2026-11-26). Daily volatility σ 2.65% (egx-data/egxpy_orhd.csv (σ60=0.0265, σ10=0.0241)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.96% … +3.96% | 0.35 |
| week | ➡ flat | +0.00% | -9.85% … +9.85% | 0.35 |
| month | ➡ flat | +0.00% | -18.92% … +18.92% | 0.35 |

Family scores (−1…+1): technicals +0.23, sentiment -0.01, agent —, fundamentals +0.40, price-forecast -0.10.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/094837__sweep-lite-orhd-ca-market-egx__runw6-sweeplite-orhd-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-orhd-002`._
