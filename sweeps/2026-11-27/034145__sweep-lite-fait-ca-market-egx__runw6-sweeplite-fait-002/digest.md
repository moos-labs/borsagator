# 🐊 Borsagator digest — sweep-lite FAIT.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 03:37 UTC · finished 03:41 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_FAIT.CA.csv=1208; FAIT.CA.csv_last_date=2026-11-24; FAIT.CA.csv_last_close=45.849998474121094 | — |
| openbb | data | ok | rows_FAIT_CA.csv=483; FAIT_CA.csv_last_date=2026-11-25; FAIT_CA.csv_last_close=46.150001525878906 | — |
| egx-data | data | ok | ticker=FAIT.CA; symbol=FAIT; rows_egxpy_fait.csv=3000; egxpy_fait.csv_last_date=2026-11-26; egxpy_fait.csv_last_close=47.48 | — |
| pandas-ta | technicals | ok | macd_signal=0.4519; ticker=FAIT.CA; date=2026-11-25; open=45.85; high=46.7 | — |
| talib | technicals | ok | ticker=FAIT.CA; drop_before=2019-01-01; rows_fetched=6113; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=13 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=10 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=10 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=10 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=44.3169 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=FAIT.CA; fetched_at=2026-11-27T03:41:44Z; tool=news-disclosure; news_count=14; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 47.48 (egx-data/egxpy_fait.csv, 2026-11-26). Daily volatility σ 1.96% (egx-data/egxpy_fait.csv (σ60=0.0196, σ10=0.0133)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **elevated**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -2.71% … +2.71% | 0.45 |
| week | ➡ flat | +0.00% | -6.75% … +6.75% | 0.45 |
| month | ➡ flat | +0.00% | -12.96% … +12.96% | 0.45 |

Family scores (−1…+1): technicals +0.30, sentiment +0.06, agent —, fundamentals +0.40, price-forecast -0.37.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/034145__sweep-lite-fait-ca-market-egx__runw6-sweeplite-fait-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-fait-002`._
