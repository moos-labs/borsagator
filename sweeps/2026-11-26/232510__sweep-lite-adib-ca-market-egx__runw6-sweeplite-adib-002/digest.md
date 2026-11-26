# 🐊 Borsagator digest — sweep-lite ADIB.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-26 23:20 UTC · finished 23:25 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ADIB.CA.csv=1210; ADIB.CA.csv_last_date=2026-11-24; ADIB.CA.csv_last_close=46.150001525878906 | — |
| openbb | data | ok | rows_ADIB_CA.csv=484; ADIB_CA.csv_last_date=2026-11-25; ADIB_CA.csv_last_close=45.93000030517578 | — |
| egx-data | data | ok | ticker=ADIB.CA; symbol=ADIB; rows_egxpy_adib.csv=3000; egxpy_adib.csv_last_date=2026-11-26; egxpy_adib.csv_last_close=45.98 | — |
| pandas-ta | technicals | ok | macd_signal=-0.2271; ticker=ADIB.CA; date=2026-11-25; open=46.15; high=46.5 | — |
| talib | technicals | ok | ticker=ADIB.CA; drop_before=2019-01-01; rows_fetched=6536; rows_used=1932; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=13 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=30 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=30 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=31 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=46.7053 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ADIB.CA; fetched_at=2026-11-26T23:25:09Z; tool=news-disclosure; news_count=40; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 45.98 (egx-data/egxpy_adib.csv, 2026-11-26). Daily volatility σ 2.19% (egx-data/egxpy_adib.csv (σ60=0.0219, σ10=0.0106)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — earnings event: ADIB raises $500m in perpetual sukuk to support growth strategy - The National; earnings event: عمرو أديب بعد حادث دائري الوراق: خسائر الطرق في مصر مرعبة وأعدادها غريبة - فيتو; earnings event: عمرو أديب يعلق على حادث الوراق: الظلام على الطريق الدائري مرعب - Masrawy.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.77% … +3.77% | 0.30 |
| week | ➡ flat | +0.00% | -9.39% … +9.39% | 0.30 |
| month | ➡ flat | +0.00% | -18.05% … +18.05% | 0.30 |

Family scores (−1…+1): technicals -0.30, sentiment +0.25, agent —, fundamentals +0.40, price-forecast +0.08.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-26/232510__sweep-lite-adib-ca-market-egx__runw6-sweeplite-adib-002`; point-in-time inputs in `worker-runs/2026-11-26/w6-sweeplite-adib-002`._
