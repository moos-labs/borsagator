# 🐊 Borsagator digest — sweep-lite LCSW.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 08:39 UTC · finished 08:41 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_LCSW.CA.csv=1209; LCSW.CA.csv_last_date=2026-11-25; LCSW.CA.csv_last_close=41.38999938964844 | — |
| openbb | data | ok | rows_LCSW_CA.csv=484; LCSW_CA.csv_last_date=2026-11-26; LCSW_CA.csv_last_close=43.34000015258789 | — |
| egx-data | data | ok | ticker=LCSW.CA; symbol=LCSW; rows_egxpy_lcsw.csv=3000; egxpy_lcsw.csv_last_date=2026-11-26; egxpy_lcsw.csv_last_close=43.34 | — |
| pandas-ta | technicals | ok | macd_signal=1.6389; ticker=LCSW.CA; date=2026-11-26; open=41.39; high=43.35 | — |
| talib | technicals | ok | ticker=LCSW.CA; drop_before=2019-01-01; rows_fetched=4688; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=9 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=9 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=9 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=36.1717 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 43.34 (egx-data/egxpy_lcsw.csv, 2026-11-26). Daily volatility σ 3.09% (egx-data/egxpy_lcsw.csv (σ60=0.0309, σ10=0.0270)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -4.61% … +4.61% | 0.35 |
| week | ➡ flat | +0.00% | -11.48% … +11.48% | 0.35 |
| month | ➡ flat | +0.00% | -22.06% … +22.06% | 0.35 |

Family scores (−1…+1): technicals -0.10, sentiment +0.21, agent —, fundamentals +0.15, price-forecast -0.58.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/084131__sweep-lite-lcsw-ca-market-egx__runw6-sweeplite-lcsw-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-lcsw-002`._
