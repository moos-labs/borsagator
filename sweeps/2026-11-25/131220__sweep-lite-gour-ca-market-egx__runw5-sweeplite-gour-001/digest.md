# 🐊 Borsagator digest — sweep-lite GOUR.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:09 UTC · finished 13:12 UTC · 14 tools

⚠️ **Degraded sweep:** kronos did not finish cleanly — families absent: price-forecast. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | — | — |
| openbb | data | ok | — | — |
| egx-data | data | ok | ticker=GOUR.CA; symbol=GOUR; rows_egxpy_gour.csv=192; egxpy_gour.csv_last_date=2026-11-25; egxpy_gour.csv_last_close=13.37 | — |
| pandas-ta | technicals | ok | verdict=NO DATA: GOUR.CA returned no rows from the Yahoo chart API on this runner.; ticker=GOUR.CA | — |
| talib | technicals | ok | — | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=3 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=3 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=3 | — |
| kronos | forecast | failed | RuntimeError: All data sources failed: yahooquery: yahooquery returned no rows \\| yahoo-chart-api: 404 Client Error: Not Found for url: https://query1.finance.yahoo.com/v8/finance/chart/GOUR.CA?period1 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=GOUR.CA; fetched_at=2026-11-25T13:12:19Z; tool=news-disclosure; news_count=7; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 13.37 (egx-data/egxpy_gour.csv, 2026-11-25). Daily volatility σ 3.60% (egx-data/egxpy_gour.csv (σ60=0.0360, σ10=0.0270)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.42% | -4.19% … +5.03% | 0.60 |
| week (≈3 sessions) | ➡ flat | +0.73% | -7.25% … +8.72% | 0.60 |
| month (≈14 sessions) | ⬆ up | +1.98% | -15.50% … +19.47% | 0.60 |

Family scores (−1…+1): technicals —, sentiment +0.23, agent —, fundamentals +0.30, price-forecast —.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-sentiment, family-fundamentals, buy-and-hold.
Absent entrants: family-price-forecast (no-kronos-csv); family-technicals (family-did-not-vote); family-agent (family-did-not-vote); kronos-alone (no-kronos-csv); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-gour-001`._
