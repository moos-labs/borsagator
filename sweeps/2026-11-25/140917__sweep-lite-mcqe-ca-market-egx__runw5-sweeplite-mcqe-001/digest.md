# 🐊 Borsagator digest — sweep-lite MCQE.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 14:05 UTC · finished 14:09 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_MCQE.CA.csv=1208; MCQE.CA.csv_last_date=2026-11-23; MCQE.CA.csv_last_close=175.97000122070312 | — |
| openbb | data | ok | rows_MCQE_CA.csv=484; MCQE_CA.csv_last_date=2026-11-24; MCQE_CA.csv_last_close=175.97000122070312 | — |
| egx-data | data | ok | ticker=MCQE.CA; symbol=MCQE; rows_egxpy_mcqe.csv=3000; egxpy_mcqe.csv_last_date=2026-11-25; egxpy_mcqe.csv_last_close=174.31 | — |
| pandas-ta | technicals | ok | macd_signal=-1.9054; ticker=MCQE.CA; date=2026-11-24; open=175.97; high=175.97 | — |
| talib | technicals | ok | ticker=MCQE.CA; drop_before=2019-01-01; rows_fetched=6135; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=16 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=8 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=8 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=169.0974 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=MCQE.CA; fetched_at=2026-11-25T14:09:15Z; tool=news-disclosure; news_count=28; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 174.31 (egx-data/egxpy_mcqe.csv, 2026-11-25). Daily volatility σ 4.16% (egx-data/egxpy_mcqe.csv (σ60=0.0416, σ10=0.0356)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **elevated**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +0.84% | -5.59% … +7.28% | 0.45 |
| week (≈3 sessions) | ⬆ up | +0.75% | -10.58% … +12.09% | 0.45 |
| month (≈14 sessions) | ⬇ down | -1.09% | -26.24% … +24.06% | 0.45 |

Family scores (−1…+1): technicals +0.15, sentiment +0.14, agent —, fundamentals +0.15, price-forecast -0.10.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/140917__sweep-lite-mcqe-ca-market-egx__runw5-sweeplite-mcqe-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-mcqe-001`._
