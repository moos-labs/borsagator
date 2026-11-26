# 🐊 Borsagator digest — sweep-lite ARCC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-26 23:31 UTC · finished 23:34 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ARCC.CA.csv=1208; ARCC.CA.csv_last_date=2026-11-24; ARCC.CA.csv_last_close=67.02999877929688 | — |
| openbb | data | ok | rows_ARCC_CA.csv=484; ARCC_CA.csv_last_date=2026-11-25; ARCC_CA.csv_last_close=65.94999694824219 | — |
| egx-data | data | ok | ticker=ARCC.CA; symbol=ARCC; rows_egxpy_arcc.csv=3000; egxpy_arcc.csv_last_date=2026-11-26; egxpy_arcc.csv_last_close=66.24 | — |
| pandas-ta | technicals | ok | macd_signal=0.0989; ticker=ARCC.CA; date=2026-11-25; open=67.03; high=67.45 | — |
| talib | technicals | ok | ticker=ARCC.CA; drop_before=2019-01-01; rows_fetched=3089; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=24 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=24 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=24 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=64.5525 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ARCC.CA; fetched_at=2026-11-26T23:34:43Z; tool=news-disclosure; news_count=21; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 66.24 (egx-data/egxpy_arcc.csv, 2026-11-26). Daily volatility σ 2.83% (egx-data/egxpy_arcc.csv (σ60=0.0283, σ10=0.0260)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — earnings event: "آرك إنفستمنت" تفوّت مكاسب بـ10.7 مليون دولار بعد بيع أسهم "إنفيديا" - المشهد العربي.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -4.89% … +4.89% | 0.30 |
| week | ➡ flat | +0.00% | -12.17% … +12.17% | 0.30 |
| month | ➡ flat | +0.00% | -23.37% … +23.37% | 0.30 |

Family scores (−1…+1): technicals -0.45, sentiment +0.07, agent —, fundamentals +0.40, price-forecast -0.10.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-26/233444__sweep-lite-arcc-ca-market-egx__runw6-sweeplite-arcc-002`; point-in-time inputs in `worker-runs/2026-11-26/w6-sweeplite-arcc-002`._
