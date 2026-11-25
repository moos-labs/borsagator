# 🐊 Borsagator digest — sweep-lite ISPH.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:32 UTC · finished 13:35 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ISPH.CA.csv=1208; ISPH.CA.csv_last_date=2026-11-23; ISPH.CA.csv_last_close=10.170000076293945 | — |
| openbb | data | ok | rows_ISPH_CA.csv=484; ISPH_CA.csv_last_date=2026-11-24; ISPH_CA.csv_last_close=10.170000076293945 | — |
| egx-data | data | ok | ticker=ISPH.CA; symbol=ISPH; rows_egxpy_isph.csv=2173; egxpy_isph.csv_last_date=2026-11-25; egxpy_isph.csv_last_close=10.03 | — |
| pandas-ta | technicals | ok | macd_signal=-0.2081; ticker=ISPH.CA; date=2026-11-24; open=10.17; high=10.17 | — |
| talib | technicals | ok | ticker=ISPH.CA; drop_before=2019-01-01; rows_fetched=2202; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=3 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=3 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=9.9584 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ISPH.CA; fetched_at=2026-11-25T13:35:17Z; tool=news-disclosure; news_count=6; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.03 (egx-data/egxpy_isph.csv, 2026-11-25). Daily volatility σ 2.58% (egx-data/egxpy_isph.csv (σ60=0.0258, σ10=0.0165)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.23% | -2.17% … +4.64% | 0.60 |
| week (≈3 sessions) | ⬆ up | +2.28% | -3.63% … +8.18% | 0.60 |
| month (≈14 sessions) | ➡ flat | +0.09% | -12.83% … +13.01% | 0.60 |

Family scores (−1…+1): technicals +0.15, sentiment +0.24, agent —, fundamentals +0.15, price-forecast -0.04.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/133518__sweep-lite-isph-ca-market-egx__runw5-sweeplite-isph-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-isph-001`._
