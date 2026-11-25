# 🐊 Borsagator digest — sweep-lite EGAL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 12:16 UTC · finished 12:18 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EGAL.CA.csv=1208; EGAL.CA.csv_last_date=2026-11-23; EGAL.CA.csv_last_close=302.0 | — |
| openbb | data | ok | rows_EGAL_CA.csv=484; EGAL_CA.csv_last_date=2026-11-24; EGAL_CA.csv_last_close=302.0 | — |
| egx-data | data | ok | ticker=EGAL.CA; symbol=EGAL; rows_egxpy_egal.csv=3000; egxpy_egal.csv_last_date=2026-11-25; egxpy_egal.csv_last_close=293.3 | — |
| pandas-ta | technicals | ok | macd_signal=-3.4884; ticker=EGAL.CA; date=2026-11-24; open=302.0; high=302.0 | — |
| talib | technicals | ok | ticker=EGAL.CA; drop_before=2019-01-01; rows_fetched=6533; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=16 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=40 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=40 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=40 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=302.1389 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EGAL.CA; fetched_at=2026-11-25T12:18:51Z; tool=news-disclosure; news_count=40; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 293.3 (egx-data/egxpy_egal.csv, 2026-11-25). Daily volatility σ 2.29% (egx-data/egxpy_egal.csv (σ60=0.0229, σ10=0.0191)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Market Outlook: Which Canadian Stocks Could Outperform Before Year-End? - The Globe and Ma; capital event: Bold Eagle Acquisition enters $1.08 million promissory note with sponsor By Investing.com ; earnings event: Franco-Nevada Corporation (FNV.TO) Stock Price, News, Quote & History - Yahoo! Finance Can.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.51% | -3.51% … +6.53% | 0.30 |
| week (≈3 sessions) | ⬆ up | +1.97% | -6.50% … +10.45% | 0.30 |
| month (≈14 sessions) | ⬆ up | +2.80% | -15.47% … +21.07% | 0.30 |

Family scores (−1…+1): technicals -0.20, sentiment +0.03, agent —, fundamentals +0.40, price-forecast +0.18.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/121852__sweep-lite-egal-ca-market-egx__runw5-sweeplite-egal-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-egal-001`._
