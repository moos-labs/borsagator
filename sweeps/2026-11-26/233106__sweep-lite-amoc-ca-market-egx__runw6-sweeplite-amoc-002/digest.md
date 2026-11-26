# 🐊 Borsagator digest — sweep-lite AMOC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-26 23:25 UTC · finished 23:31 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AMOC.CA.csv=1208; AMOC.CA.csv_last_date=2026-11-24; AMOC.CA.csv_last_close=12.25 | — |
| openbb | data | ok | rows_AMOC_CA.csv=484; AMOC_CA.csv_last_date=2026-11-25; AMOC_CA.csv_last_close=11.899999618530273 | — |
| egx-data | data | ok | ticker=AMOC.CA; symbol=AMOC; rows_egxpy_amoc.csv=3000; egxpy_amoc.csv_last_date=2026-11-26; egxpy_amoc.csv_last_close=12.0 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1134; ticker=AMOC.CA; date=2026-11-25; open=12.25; high=12.29 | — |
| talib | technicals | ok | ticker=AMOC.CA; drop_before=2019-01-01; rows_fetched=5068; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=13 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=13 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=13 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=13.3194 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=AMOC.CA; fetched_at=2026-11-26T23:31:05Z; tool=news-disclosure; news_count=4; disclosure_count=6 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 12.0 (egx-data/egxpy_amoc.csv, 2026-11-26). Daily volatility σ 2.56% (egx-data/egxpy_amoc.csv (σ60=0.0256, σ10=0.0253)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **elevated**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.54% … +3.54% | 0.45 |
| week | ➡ flat | +0.00% | -8.80% … +8.80% | 0.45 |
| month | ➡ flat | +0.00% | -16.91% … +16.91% | 0.45 |

Family scores (−1…+1): technicals -0.20, sentiment -0.23, agent —, fundamentals +0.15, price-forecast +0.47.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-26/233106__sweep-lite-amoc-ca-market-egx__runw6-sweeplite-amoc-002`; point-in-time inputs in `worker-runs/2026-11-26/w6-sweeplite-amoc-002`._
