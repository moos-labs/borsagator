# 🐊 Borsagator digest — sweep-lite EFID.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-26 23:45 UTC · finished 23:49 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EFID.CA.csv=1208; EFID.CA.csv_last_date=2026-11-24; EFID.CA.csv_last_close=20.399999618530273 | — |
| openbb | data | ok | rows_EFID_CA.csv=484; EFID_CA.csv_last_date=2026-11-25; EFID_CA.csv_last_close=20.700000762939453 | — |
| egx-data | data | ok | ticker=EFID.CA; symbol=EFID; rows_egxpy_efid.csv=2825; egxpy_efid.csv_last_date=2026-11-26; egxpy_efid.csv_last_close=21.3 | — |
| pandas-ta | technicals | ok | macd_signal=-0.0115; ticker=EFID.CA; date=2026-11-25; open=20.98; high=20.98 | — |
| talib | technicals | ok | ticker=EFID.CA; drop_before=2019-01-01; rows_fetched=2863; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=4 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=4 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=4 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=18.7332 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EFID.CA; fetched_at=2026-11-26T23:49:04Z; tool=news-disclosure; news_count=2; disclosure_count=1 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 20.399999618530273 (consensus median, 2026-11-24). Daily volatility σ 3.18% (egx-data/egxpy_efid.csv (σ60=0.0288, σ10=0.0318)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **none**.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

⚠️ **Price sources disagree** (spread 4.41%: egx-data/egxpy_efid.csv 20.98, openbb/efid_ca.csv 20.4, pandas-ta/indicators.csv 20.4, talib/indicators.csv 20.4, yahooquery/efid.ca.csv 20.4) — this forecast stands on consensus median = 20.4.

⚠️ **Stale base:** the base close is dated 2026-11-24 but the freshest collected series reaches 2026-11-26 — this forecast is anchored on an older close.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.32% … +3.32% | 0.60 |
| week | ➡ flat | +0.00% | -8.26% … +8.26% | 0.60 |
| month | ➡ flat | +0.00% | -15.86% … +15.86% | 0.60 |

Family scores (−1…+1): technicals +0.30, sentiment +0.64, agent —, fundamentals -0.10, price-forecast -0.28.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-26/234905__sweep-lite-efid-ca-market-egx__runw6-sweeplite-efid-002`; point-in-time inputs in `worker-runs/2026-11-26/w6-sweeplite-efid-002`._
