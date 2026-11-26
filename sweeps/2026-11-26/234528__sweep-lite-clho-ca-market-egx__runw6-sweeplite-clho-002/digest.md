# 🐊 Borsagator digest — sweep-lite CLHO.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-26 23:41 UTC · finished 23:45 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_CLHO.CA.csv=1208; CLHO.CA.csv_last_date=2026-11-24; CLHO.CA.csv_last_close=14.130000114440918 | — |
| openbb | data | ok | rows_CLHO_CA.csv=484; CLHO_CA.csv_last_date=2026-11-25; CLHO_CA.csv_last_close=14.199999809265137 | — |
| egx-data | data | ok | ticker=CLHO.CA; symbol=CLHO; rows_egxpy_clho.csv=2576; egxpy_clho.csv_last_date=2026-11-26; egxpy_clho.csv_last_close=14.4 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1486; ticker=CLHO.CA; date=2026-11-25; open=14.3; high=14.49 | — |
| talib | technicals | ok | ticker=CLHO.CA; drop_before=2019-01-01; rows_fetched=2462; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=1 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=13.5038 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=CLHO.CA; fetched_at=2026-11-26T23:45:27Z; tool=news-disclosure; news_count=31; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 14.4 (egx-data/egxpy_clho.csv, 2026-11-26). Daily volatility σ 1.95% (egx-data/egxpy_clho.csv (σ60=0.0195, σ10=0.0151)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — earnings event: "كله راح في لحظة".. "البوابة نيوز" تنشر 35 صورة توثق مشاهد حريق سيارة المواد البترولية أعل.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.37% … +3.37% | 0.30 |
| week | ➡ flat | +0.00% | -8.38% … +8.38% | 0.30 |
| month | ➡ flat | +0.00% | -16.10% … +16.10% | 0.30 |

Family scores (−1…+1): technicals +0.45, sentiment -0.38, agent —, fundamentals -0.35, price-forecast -0.35.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-26/234528__sweep-lite-clho-ca-market-egx__runw6-sweeplite-clho-002`; point-in-time inputs in `worker-runs/2026-11-26/w6-sweeplite-clho-002`._
