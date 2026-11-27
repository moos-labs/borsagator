# 🐊 Borsagator digest — sweep-lite SAUD.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 10:19 UTC · finished 10:23 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_SAUD.CA.csv=1209; SAUD.CA.csv_last_date=2026-11-25; SAUD.CA.csv_last_close=21.950000762939453 | — |
| openbb | data | ok | rows_SAUD_CA.csv=484; SAUD_CA.csv_last_date=2026-11-26; SAUD_CA.csv_last_close=21.770000457763672 | — |
| egx-data | data | ok | ticker=SAUD.CA; symbol=SAUD; rows_egxpy_saud.csv=3000; egxpy_saud.csv_last_date=2026-11-26; egxpy_saud.csv_last_close=21.77 | — |
| pandas-ta | technicals | ok | macd_signal=0.1851; ticker=SAUD.CA; date=2026-11-26; open=21.95; high=22.41 | — |
| talib | technicals | ok | ticker=SAUD.CA; drop_before=2019-01-01; rows_fetched=6530; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=13 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=11 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=11 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=11 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=21.3928 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=SAUD.CA; fetched_at=2026-11-27T10:23:54Z; tool=news-disclosure; news_count=18; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 21.77 (egx-data/egxpy_saud.csv, 2026-11-26). Daily volatility σ 2.45% (egx-data/egxpy_saud.csv (σ60=0.0245, σ10=0.0240)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **elevated**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.38% … +3.38% | 0.45 |
| week | ➡ flat | +0.00% | -8.42% … +8.42% | 0.45 |
| month | ➡ flat | +0.00% | -16.18% … +16.18% | 0.45 |

Family scores (−1…+1): technicals +0.15, sentiment -0.40, agent —, fundamentals +0.40, price-forecast -0.08.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/102356__sweep-lite-saud-ca-market-egx__runw6-sweeplite-saud-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-saud-002`._
