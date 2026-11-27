# 🐊 Borsagator digest — sweep-lite PHDC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 10:11 UTC · finished 10:13 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_PHDC.CA.csv=1209; PHDC.CA.csv_last_date=2026-11-25; PHDC.CA.csv_last_close=11.350000381469727 | — |
| openbb | data | ok | rows_PHDC_CA.csv=484; PHDC_CA.csv_last_date=2026-11-26; PHDC_CA.csv_last_close=11.34000015258789 | — |
| egx-data | data | ok | ticker=PHDC.CA; symbol=PHDC; rows_egxpy_phdc.csv=3000; egxpy_phdc.csv_last_date=2026-11-26; egxpy_phdc.csv_last_close=11.34 | — |
| pandas-ta | technicals | ok | macd_signal=-0.2823; ticker=PHDC.CA; date=2026-11-26; open=11.35; high=11.5 | — |
| talib | technicals | ok | ticker=PHDC.CA; drop_before=2019-01-01; rows_fetched=4591; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=8 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=8 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=8 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=11.5296 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=PHDC.CA; fetched_at=2026-11-27T10:13:52Z; tool=news-disclosure; news_count=6; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 11.34 (egx-data/egxpy_phdc.csv, 2026-11-26). Daily volatility σ 2.63% (egx-data/egxpy_phdc.csv (σ60=0.0254, σ10=0.0263)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **none**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -2.92% … +2.92% | 0.60 |
| week | ➡ flat | +0.00% | -7.28% … +7.28% | 0.60 |
| month | ➡ flat | +0.00% | -13.98% … +13.98% | 0.60 |

Family scores (−1…+1): technicals +0.30, sentiment +0.36, agent —, fundamentals +0.40, price-forecast +0.07.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/101353__sweep-lite-phdc-ca-market-egx__runw6-sweeplite-phdc-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-phdc-002`._
