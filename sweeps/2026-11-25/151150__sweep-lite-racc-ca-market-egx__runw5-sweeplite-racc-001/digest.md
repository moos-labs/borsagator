# 🐊 Borsagator digest — sweep-lite RACC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 15:09 UTC · finished 15:11 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_RACC.CA.csv=1208; RACC.CA.csv_last_date=2026-11-23; RACC.CA.csv_last_close=7.75 | — |
| openbb | data | ok | rows_RACC_CA.csv=484; RACC_CA.csv_last_date=2026-11-24; RACC_CA.csv_last_close=7.75 | — |
| egx-data | data | ok | ticker=RACC.CA; symbol=RACC; rows_egxpy_racc.csv=2325; egxpy_racc.csv_last_date=2026-11-25; egxpy_racc.csv_last_close=7.51 | — |
| pandas-ta | technicals | ok | macd_signal=-0.2002; ticker=RACC.CA; date=2026-11-24; open=7.75; high=7.75 | — |
| talib | technicals | ok | ticker=RACC.CA; drop_before=2019-01-01; rows_fetched=2253; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=6 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=6 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=6 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=7.6429 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=RACC.CA; fetched_at=2026-11-25T15:11:49Z; tool=news-disclosure; news_count=4; disclosure_count=1 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 7.51 (egx-data/egxpy_racc.csv, 2026-11-25). Daily volatility σ 2.96% (egx-data/egxpy_racc.csv (σ60=0.0296, σ10=0.0127)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.54/day). News risk: **shock** — legal event: شبكة “ألو راك ربحتي معانا”.. معلومات من الديستي طيحات متورط جديد كتقلب عليه الفرقة الجهوية.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +2.19% | -3.94% … +8.32% | 0.30 |
| week (≈3 sessions) | ⬆ up | +2.05% | -8.28% … +12.37% | 0.30 |
| month (≈11 sessions) | ⬆ up | +2.54% | -17.59% … +22.67% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment +0.08, agent —, fundamentals +0.40, price-forecast +0.09.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/151150__sweep-lite-racc-ca-market-egx__runw5-sweeplite-racc-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-racc-001`._
