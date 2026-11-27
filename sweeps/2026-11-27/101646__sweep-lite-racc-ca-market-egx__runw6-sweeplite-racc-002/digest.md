# 🐊 Borsagator digest — sweep-lite RACC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 10:14 UTC · finished 10:16 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_RACC.CA.csv=1209; RACC.CA.csv_last_date=2026-11-25; RACC.CA.csv_last_close=7.510000228881836 | — |
| openbb | data | ok | rows_RACC_CA.csv=484; RACC_CA.csv_last_date=2026-11-26; RACC_CA.csv_last_close=7.800000190734863 | — |
| egx-data | data | ok | ticker=RACC.CA; symbol=RACC; rows_egxpy_racc.csv=2326; egxpy_racc.csv_last_date=2026-11-26; egxpy_racc.csv_last_close=7.8 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1916; ticker=RACC.CA; date=2026-11-26; open=7.51; high=7.96 | — |
| talib | technicals | ok | ticker=RACC.CA; drop_before=2019-01-01; rows_fetched=2255; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=4 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=9 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=4 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=7.6143 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=RACC.CA; fetched_at=2026-11-27T10:16:45Z; tool=news-disclosure; news_count=5; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 7.8 (egx-data/egxpy_racc.csv, 2026-11-26). Daily volatility σ 3.00% (egx-data/egxpy_racc.csv (σ60=0.0300, σ10=0.0184)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.54/day). News risk: **shock** — legal event: شبكة “ألو راك ربحتي معانا”.. معلومات من الديستي طيحات متورط جديد كتقلب عليه الفرقة الجهوية.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -5.17% … +5.17% | 0.30 |
| week | ➡ flat | +0.00% | -12.86% … +12.86% | 0.30 |
| month | ➡ flat | +0.00% | -24.71% … +24.71% | 0.30 |

Family scores (−1…+1): technicals +0.15, sentiment +0.11, agent —, fundamentals +0.40, price-forecast -0.09.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/101646__sweep-lite-racc-ca-market-egx__runw6-sweeplite-racc-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-racc-002`._
