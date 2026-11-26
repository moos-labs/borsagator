# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-26 07:36 UTC · finished 07:42 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1208; POUL.CA.csv_last_date=2026-11-23; POUL.CA.csv_last_close=7.099999904632568 | — |
| openbb | data | ok | rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-24; POUL_CA.csv_last_close=7.099999904632568 | — |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-25; egxpy_poul.csv_last_close=6.73 | — |
| pandas-ta | technicals | ok | macd_signal=-2.2187; ticker=POUL.CA; date=2026-11-24; open=7.1; high=7.1 | — |
| talib | technicals | ok | ticker=POUL.CA; drop_before=2019-01-01; rows_fetched=6529; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=13 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=13 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=13 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=8.7545 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-26T07:42:16Z; tool=news-disclosure; news_count=25; disclosure_count=10 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 6.73 (egx-data/egxpy_poul.csv, 2026-11-25). Daily volatility σ 6.54% (egx-data/egxpy_poul.csv (σ60=0.0378, σ10=0.0654)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **elevated**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -28.23% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted. — via verified EGX disclosure event ev_bf7532c5c9185f9f113d (verbatim ex-date)

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -5.21% … +5.21% | 0.45 |
| week | ➡ flat | +0.00% | -12.98% … +12.98% | 0.45 |
| month | ➡ flat | +0.00% | -24.93% … +24.93% | 0.45 |

Family scores (−1…+1): technicals +0.50, sentiment +0.05, agent —, fundamentals +0.40, price-forecast +0.50.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-26/074217__sweep-lite-poul-ca-market-egx__runsched-2026-11-26`; point-in-time inputs in `worker-runs/2026-11-26/sched-2026-11-26`._
