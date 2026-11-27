# 🐊 Borsagator digest — sweep-lite ICFC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 04:01 UTC · finished 04:03 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ICFC.CA.csv=1208; ICFC.CA.csv_last_date=2026-11-24; ICFC.CA.csv_last_close=26.540000915527344 | — |
| openbb | data | ok | rows_ICFC_CA.csv=483; ICFC_CA.csv_last_date=2026-11-25; ICFC_CA.csv_last_close=26.799999237060547 | — |
| egx-data | data | ok | ticker=ICFC.CA; symbol=ICFC; rows_egxpy_icfc.csv=3000; egxpy_icfc.csv_last_date=2026-11-26; egxpy_icfc.csv_last_close=27.65 | — |
| pandas-ta | technicals | ok | macd_signal=1.0714; ticker=ICFC.CA; date=2026-11-25; open=26.54; high=27.24 | — |
| talib | technicals | ok | ticker=ICFC.CA; drop_before=2019-01-01; rows_fetched=2014; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=16 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=3 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=3 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=22.824 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 27.65 (egx-data/egxpy_icfc.csv, 2026-11-26). Daily volatility σ 4.44% (egx-data/egxpy_icfc.csv (σ60=0.0444, σ10=0.0432)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -6.64% … +6.64% | 0.35 |
| week | ➡ flat | +0.00% | -16.53% … +16.53% | 0.35 |
| month | ➡ flat | +0.00% | -31.75% … +31.75% | 0.35 |

Family scores (−1…+1): technicals -0.30, sentiment +0.16, agent —, fundamentals -0.10, price-forecast -0.43.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/040324__sweep-lite-icfc-ca-market-egx__runw6-sweeplite-icfc-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-icfc-002`._
