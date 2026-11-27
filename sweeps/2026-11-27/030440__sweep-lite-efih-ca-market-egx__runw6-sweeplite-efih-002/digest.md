# 🐊 Borsagator digest — sweep-lite EFIH.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 03:00 UTC · finished 03:04 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EFIH.CA.csv=1210; EFIH.CA.csv_last_date=2026-11-24; EFIH.CA.csv_last_close=25.290000915527344 | — |
| openbb | data | ok | rows_EFIH_CA.csv=483; EFIH_CA.csv_last_date=2026-11-25; EFIH_CA.csv_last_close=25.0 | — |
| egx-data | data | ok | ticker=EFIH.CA; symbol=EFIH; rows_egxpy_efih.csv=1239; egxpy_efih.csv_last_date=2026-11-26; egxpy_efih.csv_last_close=24.61 | — |
| pandas-ta | technicals | ok | macd_signal=0.416; ticker=EFIH.CA; date=2026-11-25; open=25.29; high=25.28 | — |
| talib | technicals | ok | ticker=EFIH.CA; drop_before=2019-01-01; rows_fetched=1237; rows_used=1237; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=1 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=24.2893 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EFIH.CA; fetched_at=2026-11-27T03:04:39Z; tool=news-disclosure; news_count=3; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 24.61 (egx-data/egxpy_efih.csv, 2026-11-26). Daily volatility σ 2.85% (egx-data/egxpy_efih.csv (σ60=0.0285, σ10=0.0235)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **none**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.27% … +3.27% | 0.60 |
| week | ➡ flat | +0.00% | -8.15% … +8.15% | 0.60 |
| month | ➡ flat | +0.00% | -15.65% … +15.65% | 0.54 |

Family scores (−1…+1): technicals +0.30, sentiment +0.69, agent —, fundamentals -0.35, price-forecast -0.05.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/030440__sweep-lite-efih-ca-market-egx__runw6-sweeplite-efih-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-efih-002`._
