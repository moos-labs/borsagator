# 🐊 Borsagator digest — sweep-lite RMDA.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 10:17 UTC · finished 10:19 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_RMDA.CA.csv=1209; RMDA.CA.csv_last_date=2026-11-25; RMDA.CA.csv_last_close=5.050000190734863 | — |
| openbb | data | ok | rows_RMDA_CA.csv=484; RMDA_CA.csv_last_date=2026-11-26; RMDA_CA.csv_last_close=5.010000228881836 | — |
| egx-data | data | ok | ticker=RMDA.CA; symbol=RMDA; rows_egxpy_rmda.csv=1700; egxpy_rmda.csv_last_date=2026-11-26; egxpy_rmda.csv_last_close=5.01 | — |
| pandas-ta | technicals | ok | macd_signal=-0.0419; ticker=RMDA.CA; date=2026-11-26; open=5.05; high=5.08 | — |
| talib | technicals | ok | ticker=RMDA.CA; drop_before=2019-01-01; rows_fetched=1687; rows_used=1687; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=2 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=2 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=2 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=5.1659 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 5.01 (egx-data/egxpy_rmda.csv, 2026-11-26). Daily volatility σ 2.65% (egx-data/egxpy_rmda.csv (σ60=0.0265, σ10=0.0220)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.97% … +3.97% | 0.35 |
| week | ➡ flat | +0.00% | -9.87% … +9.87% | 0.35 |
| month | ➡ flat | +0.00% | -18.97% … +18.97% | 0.35 |

Family scores (−1…+1): technicals -0.20, sentiment +0.04, agent —, fundamentals -0.35, price-forecast +0.13.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/101919__sweep-lite-rmda-ca-market-egx__runw6-sweeplite-rmda-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-rmda-002`._
