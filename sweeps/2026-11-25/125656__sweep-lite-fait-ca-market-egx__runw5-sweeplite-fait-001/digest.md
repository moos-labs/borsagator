# 🐊 Borsagator digest — sweep-lite FAIT.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 12:53 UTC · finished 12:56 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_FAIT.CA.csv=1208; FAIT.CA.csv_last_date=2026-11-23; FAIT.CA.csv_last_close=45.369998931884766 | — |
| openbb | data | ok | rows_FAIT_CA.csv=484; FAIT_CA.csv_last_date=2026-11-24; FAIT_CA.csv_last_close=45.849998474121094 | — |
| egx-data | data | ok | ticker=FAIT.CA; symbol=FAIT; rows_egxpy_fait.csv=3000; egxpy_fait.csv_last_date=2026-11-25; egxpy_fait.csv_last_close=46.15 | — |
| pandas-ta | technicals | ok | macd_signal=0.4185; ticker=FAIT.CA; date=2026-11-24; open=45.37; high=45.97 | — |
| talib | technicals | ok | ticker=FAIT.CA; drop_before=2019-01-01; rows_fetched=6112; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=13 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=8 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=8 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=8 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=44.0159 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=FAIT.CA; fetched_at=2026-11-25T12:56:54Z; tool=news-disclosure; news_count=16; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 46.15 (egx-data/egxpy_fait.csv, 2026-11-25). Daily volatility σ 1.94% (egx-data/egxpy_fait.csv (σ60=0.0194, σ10=0.0149)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **elevated**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -0.99% | -4.43% … +2.45% | 0.45 |
| week (≈3 sessions) | ➡ flat | +0.17% | -5.32% … +5.65% | 0.45 |
| month (≈14 sessions) | ⬇ down | -2.12% | -14.92% … +10.68% | 0.45 |

Family scores (−1…+1): technicals +0.30, sentiment +0.09, agent —, fundamentals +0.40, price-forecast -0.32.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/125656__sweep-lite-fait-ca-market-egx__runw5-sweeplite-fait-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-fait-001`._
