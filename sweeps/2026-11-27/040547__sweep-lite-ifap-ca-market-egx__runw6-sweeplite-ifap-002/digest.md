# 🐊 Borsagator digest — sweep-lite IFAP.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 04:03 UTC · finished 04:05 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_IFAP.CA.csv=1208; IFAP.CA.csv_last_date=2026-11-24; IFAP.CA.csv_last_close=15.789999961853027 | — |
| openbb | data | ok | rows_IFAP_CA.csv=483; IFAP_CA.csv_last_date=2026-11-25; IFAP_CA.csv_last_close=15.819999694824219 | — |
| egx-data | data | ok | ticker=IFAP.CA; symbol=IFAP; rows_egxpy_ifap.csv=3000; egxpy_ifap.csv_last_date=2026-11-26; egxpy_ifap.csv_last_close=15.89 | — |
| pandas-ta | technicals | ok | macd_signal=-0.5388; ticker=IFAP.CA; date=2026-11-25; open=15.79; high=16.39 | — |
| talib | technicals | ok | ticker=IFAP.CA; drop_before=2019-01-01; rows_fetched=5634; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=3 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=3 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=16.4295 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 15.89 (egx-data/egxpy_ifap.csv, 2026-11-26). Daily volatility σ 2.81% (egx-data/egxpy_ifap.csv (σ60=0.0281, σ10=0.0208)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -4.20% … +4.20% | 0.35 |
| week | ➡ flat | +0.00% | -10.45% … +10.45% | 0.35 |
| month | ➡ flat | +0.00% | -20.08% … +20.08% | 0.35 |

Family scores (−1…+1): technicals -0.20, sentiment +0.28, agent —, fundamentals +0.15, price-forecast +0.13.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/040547__sweep-lite-ifap-ca-market-egx__runw6-sweeplite-ifap-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-ifap-002`._
