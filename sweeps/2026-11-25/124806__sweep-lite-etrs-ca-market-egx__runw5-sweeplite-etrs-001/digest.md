# 🐊 Borsagator digest — sweep-lite ETRS.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 12:45 UTC · finished 12:48 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ETRS.CA.csv=1208; ETRS.CA.csv_last_date=2026-11-23; ETRS.CA.csv_last_close=11.100000381469727 | — |
| openbb | data | ok | rows_ETRS_CA.csv=484; ETRS_CA.csv_last_date=2026-11-24; ETRS_CA.csv_last_close=11.050000190734863 | — |
| egx-data | data | ok | ticker=ETRS.CA; symbol=ETRS; rows_egxpy_etrs.csv=3000; egxpy_etrs.csv_last_date=2026-11-25; egxpy_etrs.csv_last_close=11.15 | — |
| pandas-ta | technicals | ok | macd_signal=0.1131; ticker=ETRS.CA; date=2026-11-24; open=11.1; high=11.35 | — |
| talib | technicals | ok | ticker=ETRS.CA; drop_before=2019-01-01; rows_fetched=6149; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=3 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=3 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=10.6142 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ETRS.CA; fetched_at=2026-11-25T12:48:05Z; tool=news-disclosure; news_count=1; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 11.15 (egx-data/egxpy_etrs.csv, 2026-11-25). Daily volatility σ 2.49% (egx-data/egxpy_etrs.csv (σ60=0.0249, σ10=0.0166)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.03% | -3.49% … +3.43% | 0.60 |
| week (≈3 sessions) | ⬇ down | -1.20% | -7.30% … +4.91% | 0.60 |
| month (≈14 sessions) | ⬇ down | -3.32% | -16.24% … +9.61% | 0.60 |

Family scores (−1…+1): technicals +0.30, sentiment -0.07, agent —, fundamentals -0.10, price-forecast -0.26.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/124806__sweep-lite-etrs-ca-market-egx__runw5-sweeplite-etrs-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-etrs-001`._
