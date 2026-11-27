# 🐊 Borsagator digest — sweep-lite TMGH.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 10:26 UTC · finished 10:34 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_TMGH.CA.csv=1209; TMGH.CA.csv_last_date=2026-11-25; TMGH.CA.csv_last_close=78.94999694824219 | — |
| openbb | data | ok | rows_TMGH_CA.csv=484; TMGH_CA.csv_last_date=2026-11-26; TMGH_CA.csv_last_close=79.23999786376953 | — |
| egx-data | data | ok | ticker=TMGH.CA; symbol=TMGH; rows_egxpy_tmgh.csv=3000; egxpy_tmgh.csv_last_date=2026-11-26; egxpy_tmgh.csv_last_close=79.24 | — |
| pandas-ta | technicals | ok | macd_signal=-1.4199; ticker=TMGH.CA; date=2026-11-26; open=78.95; high=79.5 | — |
| talib | technicals | ok | ticker=TMGH.CA; drop_before=2019-01-01; rows_fetched=4708; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=17 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=17 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=17 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=82.2037 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=TMGH.CA; fetched_at=2026-11-27T10:34:21Z; tool=news-disclosure; news_count=40; disclosure_count=3 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 79.24 (egx-data/egxpy_tmgh.csv, 2026-11-26). Daily volatility σ 1.91% (egx-data/egxpy_tmgh.csv (σ60=0.0191, σ10=0.0159)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — management event: Egyptian billionaire Mohamed Mansour joins tycoons giving $1 million to fire victims - Bil; management event: Hisham Talaat Moustafa, Ahmed Ezz, Yassin Mansour donate EGP 30m to families of Ring Road ; management event: TMG, Tamer Hosny postpone Madinaty concert to 4 December following Ring Road tragedy - Dai.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.29% … +3.29% | 0.30 |
| week | ➡ flat | +0.00% | -8.18% … +8.18% | 0.30 |
| month | ➡ flat | +0.00% | -15.72% … +15.72% | 0.30 |

Family scores (−1…+1): technicals -0.20, sentiment +0.41, agent —, fundamentals +0.15, price-forecast +0.21.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/103422__sweep-lite-tmgh-ca-market-egx__runw6-sweeplite-tmgh-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-tmgh-002`._
