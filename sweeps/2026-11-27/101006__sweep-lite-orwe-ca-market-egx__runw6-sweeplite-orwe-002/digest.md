# 🐊 Borsagator digest — sweep-lite ORWE.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 10:06 UTC · finished 10:10 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ORWE.CA.csv=1209; ORWE.CA.csv_last_date=2026-11-25; ORWE.CA.csv_last_close=24.0 | — |
| openbb | data | ok | rows_ORWE_CA.csv=484; ORWE_CA.csv_last_date=2026-11-26; ORWE_CA.csv_last_close=24.0 | — |
| egx-data | data | ok | ticker=ORWE.CA; symbol=ORWE; rows_egxpy_orwe.csv=3000; egxpy_orwe.csv_last_date=2026-11-26; egxpy_orwe.csv_last_close=24.0 | — |
| pandas-ta | technicals | ok | macd_signal=-0.2316; ticker=ORWE.CA; date=2026-11-26; open=24.0; high=24.38 | — |
| talib | technicals | ok | ticker=ORWE.CA; drop_before=2019-01-01; rows_fetched=6535; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=1 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=24.7548 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ORWE.CA; fetched_at=2026-11-27T10:10:05Z; tool=news-disclosure; news_count=1; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 24.0 (egx-data/egxpy_orwe.csv, 2026-11-26). Daily volatility σ 2.43% (egx-data/egxpy_orwe.csv (σ60=0.0243, σ10=0.0115)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — earnings event: Orezone Gold Corporation (ORE.TO) Stock Price, News, Quote & History - Yahoo! Finance Cana.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -4.20% … +4.20% | 0.30 |
| week | ➡ flat | +0.00% | -10.44% … +10.44% | 0.30 |
| month | ➡ flat | +0.00% | -20.06% … +20.06% | 0.30 |

Family scores (−1…+1): technicals -0.20, sentiment -0.00, agent —, fundamentals +0.40, price-forecast +0.14.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/101006__sweep-lite-orwe-ca-market-egx__runw6-sweeplite-orwe-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-orwe-002`._
