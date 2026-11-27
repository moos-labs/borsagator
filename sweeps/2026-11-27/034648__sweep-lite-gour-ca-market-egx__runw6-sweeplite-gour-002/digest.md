# 🐊 Borsagator digest — sweep-lite GOUR.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 03:44 UTC · finished 03:46 UTC · 14 tools

⚠️ **Degraded sweep:** kronos did not finish cleanly — families absent: price-forecast. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | — | — |
| openbb | data | ok | — | — |
| egx-data | data | ok | ticker=GOUR.CA; symbol=GOUR; rows_egxpy_gour.csv=193; egxpy_gour.csv_last_date=2026-11-26; egxpy_gour.csv_last_close=13.42 | — |
| pandas-ta | technicals | ok | verdict=NO DATA: GOUR.CA returned no rows from the Yahoo chart API on this runner.; ticker=GOUR.CA | — |
| talib | technicals | ok | — | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=4 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=4 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=4 | — |
| kronos | forecast | failed | RuntimeError: All data sources failed: yahooquery: yahooquery returned no rows \\| yahoo-chart-api: 404 Client Error: Not Found for url: https://query1.finance.yahoo.com/v8/finance/chart/GOUR.CA?period1 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=GOUR.CA; fetched_at=2026-11-27T03:46:47Z; tool=news-disclosure; news_count=7; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 13.42 (egx-data/egxpy_gour.csv, 2026-11-26). Daily volatility σ 3.53% (egx-data/egxpy_gour.csv (σ60=0.0353, σ10=0.0263)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — legal event: تألق الإعلامية يارا أحمد ومي كساب وجوري بكر وأحمد الرافعي في احتفالية تكريم ضمن حملة «شباب.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -6.10% … +6.10% | 0.30 |
| week | ➡ flat | +0.00% | -15.17% … +15.17% | 0.30 |
| month | ➡ flat | +0.00% | -29.15% … +29.15% | 0.30 |

Family scores (−1…+1): technicals —, sentiment +0.29, agent —, fundamentals +0.30, price-forecast —.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-sentiment, family-fundamentals, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (no-kronos-csv); family-technicals (family-did-not-vote); family-agent (family-did-not-vote); kronos-alone (no-kronos-csv).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/034648__sweep-lite-gour-ca-market-egx__runw6-sweeplite-gour-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-gour-002`._
