# 🐊 Borsagator digest — sweep-lite FAITA.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 03:42 UTC · finished 03:44 UTC · 14 tools

⚠️ **Degraded sweep:** finbert-tone did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_FAITA.CA.csv=1208; FAITA.CA.csv_last_date=2026-11-24; FAITA.CA.csv_last_close=1.0 | — |
| openbb | data | ok | rows_FAITA_CA.csv=483; FAITA_CA.csv_last_date=2026-11-25; FAITA_CA.csv_last_close=1.0 | — |
| egx-data | data | ok | ticker=FAITA.CA; symbol=FAITA; rows_egxpy_faita.csv=3000; egxpy_faita.csv_last_date=2026-11-26; egxpy_faita.csv_last_close=1.0 | — |
| pandas-ta | technicals | ok | macd_signal=0.0029; ticker=FAITA.CA; date=2026-11-25; open=1.0; high=1.0 | — |
| talib | technicals | ok | ticker=FAITA.CA; drop_before=2019-01-01; rows_fetched=5633; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | — | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=5 | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=5 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=0.9874 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=FAITA.CA; fetched_at=2026-11-27T03:44:25Z; tool=news-disclosure; news_count=1; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 1.0 (egx-data/egxpy_faita.csv, 2026-11-26). Daily volatility σ 0.81% (egx-data/egxpy_faita.csv (σ60=0.0081, σ10=0.0034)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **none**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -0.93% … +0.93% | 0.60 |
| week | ➡ flat | +0.00% | -2.32% … +2.32% | 0.60 |
| month | ➡ flat | +0.00% | -4.46% … +4.46% | 0.60 |

Family scores (−1…+1): technicals -0.15, sentiment +0.17, agent —, fundamentals —, price-forecast -0.17.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote); family-fundamentals (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/034426__sweep-lite-faita-ca-market-egx__runw6-sweeplite-faita-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-faita-002`._
