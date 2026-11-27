# 🐊 Borsagator digest — sweep-lite EGAS.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 03:08 UTC · finished 03:11 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EGAS.CA.csv=1209; EGAS.CA.csv_last_date=2026-11-24; EGAS.CA.csv_last_close=49.099998474121094 | — |
| openbb | data | ok | rows_EGAS_CA.csv=483; EGAS_CA.csv_last_date=2026-11-25; EGAS_CA.csv_last_close=48.58000183105469 | — |
| egx-data | data | ok | ticker=EGAS.CA; symbol=EGAS; rows_egxpy_egas.csv=3000; egxpy_egas.csv_last_date=2026-11-26; egxpy_egas.csv_last_close=48.08 | — |
| pandas-ta | technicals | ok | macd_signal=-0.7045; ticker=EGAS.CA; date=2026-11-25; open=49.1; high=49.5 | — |
| talib | technicals | ok | ticker=EGAS.CA; drop_before=2019-01-01; rows_fetched=6423; rows_used=1931; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=16 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=10 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=10 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=10 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=46.8287 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EGAS.CA; fetched_at=2026-11-27T03:11:54Z; tool=news-disclosure; news_count=6; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 48.08 (egx-data/egxpy_egas.csv, 2026-11-26). Daily volatility σ 2.81% (egx-data/egxpy_egas.csv (σ60=0.0281, σ10=0.0227)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — legal event: غازتك تعقد اجتماع جمعية عامة غير عادية بشركة إيـجـاس لتعديل بعض مواد النظام الأساسي لمواكب.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -4.85% … +4.85% | 0.30 |
| week | ➡ flat | +0.00% | -12.07% … +12.07% | 0.30 |
| month | ➡ flat | +0.00% | -23.19% … +23.19% | 0.30 |

Family scores (−1…+1): technicals +0.15, sentiment +0.30, agent —, fundamentals -0.10, price-forecast -0.10.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/031155__sweep-lite-egas-ca-market-egx__runw6-sweeplite-egas-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-egas-002`._
