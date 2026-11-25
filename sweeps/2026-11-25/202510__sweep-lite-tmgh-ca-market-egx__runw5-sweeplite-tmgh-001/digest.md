# 🐊 Borsagator digest — sweep-lite TMGH.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 20:19 UTC · finished 20:25 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_TMGH.CA.csv=1208; TMGH.CA.csv_last_date=2026-11-23; TMGH.CA.csv_last_close=79.5 | — |
| openbb | data | ok | rows_TMGH_CA.csv=484; TMGH_CA.csv_last_date=2026-11-24; TMGH_CA.csv_last_close=78.05999755859375 | — |
| egx-data | data | ok | ticker=TMGH.CA; symbol=TMGH; rows_egxpy_tmgh.csv=3000; egxpy_tmgh.csv_last_date=2026-11-25; egxpy_tmgh.csv_last_close=78.95 | — |
| pandas-ta | technicals | ok | macd_signal=-1.3144; ticker=TMGH.CA; date=2026-11-24; open=79.5; high=80.88 | — |
| talib | technicals | ok | ticker=TMGH.CA; drop_before=2019-01-01; rows_fetched=4706; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=14 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=14 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=14 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=82.36 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=TMGH.CA; fetched_at=2026-11-25T20:25:09Z; tool=news-disclosure; news_count=40; disclosure_count=3 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 78.95 (egx-data/egxpy_tmgh.csv, 2026-11-25). Daily volatility σ 1.90% (egx-data/egxpy_tmgh.csv (σ60=0.0190, σ10=0.0161)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **elevated**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -2.63% … +2.63% | 0.45 |
| week | ➡ flat | +0.00% | -6.54% … +6.54% | 0.45 |
| month | ➡ flat | +0.00% | -12.56% … +12.56% | 0.45 |

Family scores (−1…+1): technicals -0.20, sentiment +0.44, agent —, fundamentals +0.15, price-forecast +0.25.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-25/202510__sweep-lite-tmgh-ca-market-egx__runw5-sweeplite-tmgh-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-tmgh-001`._
