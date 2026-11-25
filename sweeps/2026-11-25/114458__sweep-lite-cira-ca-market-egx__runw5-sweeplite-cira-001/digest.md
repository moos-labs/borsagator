# 🐊 Borsagator digest — sweep-lite CIRA.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 11:41 UTC · finished 11:44 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_CIRA.CA.csv=1208; CIRA.CA.csv_last_date=2026-11-23; CIRA.CA.csv_last_close=37.709999084472656 | — |
| openbb | data | ok | rows_CIRA_CA.csv=484; CIRA_CA.csv_last_date=2026-11-24; CIRA_CA.csv_last_close=38.45000076293945 | — |
| egx-data | data | ok | ticker=CIRA.CA; symbol=CIRA; rows_egxpy_cira.csv=1978; egxpy_cira.csv_last_date=2026-11-25; egxpy_cira.csv_last_close=38.0 | — |
| pandas-ta | technicals | ok | macd_signal=0.3455; ticker=CIRA.CA; date=2026-11-24; open=37.71; high=39.0 | — |
| talib | technicals | ok | ticker=CIRA.CA; drop_before=2019-01-01; rows_fetched=5419; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=7 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=7 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=7 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=37.6218 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=CIRA.CA; fetched_at=2026-11-25T11:44:57Z; tool=news-disclosure; news_count=9; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 38.0 (egx-data/egxpy_cira.csv, 2026-11-25). Daily volatility σ 2.68% (egx-data/egxpy_cira.csv (σ60=0.0268, σ10=0.0181)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **elevated** — dividend event: CIRA Education stock: board backs EGP 312 million dividend - ad-hoc-news.de.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.21% | -4.83% … +4.40% | 0.45 |
| week (≈3 sessions) | ➡ flat | +0.53% | -7.22% … +8.28% | 0.45 |
| month (≈14 sessions) | ➡ flat | -0.52% | -17.35% … +16.32% | 0.45 |

Family scores (−1…+1): technicals +0.45, sentiment +0.15, agent —, fundamentals -0.10, price-forecast -0.05.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/114458__sweep-lite-cira-ca-market-egx__runw5-sweeplite-cira-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-cira-001`._
