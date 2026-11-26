# 🐊 Borsagator digest — sweep-lite CIRA.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-26 23:37 UTC · finished 23:40 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_CIRA.CA.csv=1208; CIRA.CA.csv_last_date=2026-11-24; CIRA.CA.csv_last_close=38.45000076293945 | — |
| openbb | data | ok | rows_CIRA_CA.csv=484; CIRA_CA.csv_last_date=2026-11-25; CIRA_CA.csv_last_close=37.0 | — |
| egx-data | data | ok | ticker=CIRA.CA; symbol=CIRA; rows_egxpy_cira.csv=1979; egxpy_cira.csv_last_date=2026-11-26; egxpy_cira.csv_last_close=37.25 | — |
| pandas-ta | technicals | ok | macd_signal=0.3352; ticker=CIRA.CA; date=2026-11-25; open=38.45; high=38.5 | — |
| talib | technicals | ok | ticker=CIRA.CA; drop_before=2019-01-01; rows_fetched=5420; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=6 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=6 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=6 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=37.1121 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=CIRA.CA; fetched_at=2026-11-26T23:40:05Z; tool=news-disclosure; news_count=9; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 37.25 (egx-data/egxpy_cira.csv, 2026-11-26). Daily volatility σ 2.70% (egx-data/egxpy_cira.csv (σ60=0.0270, σ10=0.0212)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **elevated** — dividend event: CIRA Education stock: board backs EGP 312 million dividend - ad-hoc-news.de.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.72% … +3.72% | 0.45 |
| week | ➡ flat | +0.00% | -9.26% … +9.26% | 0.45 |
| month | ➡ flat | +0.00% | -17.79% … +17.79% | 0.45 |

Family scores (−1…+1): technicals -0.45, sentiment +0.11, agent —, fundamentals -0.10, price-forecast -0.01.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-26/234006__sweep-lite-cira-ca-market-egx__runw6-sweeplite-cira-002`; point-in-time inputs in `worker-runs/2026-11-26/w6-sweeplite-cira-002`._
