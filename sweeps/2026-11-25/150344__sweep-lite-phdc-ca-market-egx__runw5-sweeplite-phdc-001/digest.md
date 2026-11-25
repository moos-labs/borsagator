# 🐊 Borsagator digest — sweep-lite PHDC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 15:00 UTC · finished 15:03 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, financial-roberta did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_PHDC.CA.csv=1208; PHDC.CA.csv_last_date=2026-11-23; PHDC.CA.csv_last_close=11.550000190734863 | — |
| openbb | data | ok | rows_PHDC_CA.csv=484; PHDC_CA.csv_last_date=2026-11-24; PHDC_CA.csv_last_close=11.5 | — |
| egx-data | data | ok | ticker=PHDC.CA; symbol=PHDC; rows_egxpy_phdc.csv=3000; egxpy_phdc.csv_last_date=2026-11-25; egxpy_phdc.csv_last_close=11.35 | — |
| pandas-ta | technicals | ok | macd_signal=-0.2909; ticker=PHDC.CA; date=2026-11-24; open=11.55; high=11.76 | — |
| talib | technicals | ok | ticker=PHDC.CA; drop_before=2019-01-01; rows_fetched=4589; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=8 | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=11.7886 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=PHDC.CA; fetched_at=2026-11-25T15:03:43Z; tool=news-disclosure; news_count=6; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 11.35 (egx-data/egxpy_phdc.csv, 2026-11-25). Daily volatility σ 2.64% (egx-data/egxpy_phdc.csv (σ60=0.0255, σ10=0.0264)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **elevated** — abnormal move: 1.7σ in the last 3 sessions.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.68% | -2.77% … +6.12% | 0.45 |
| week (≈3 sessions) | ⬆ up | +2.09% | -5.51% … +9.70% | 0.45 |
| month (≈14 sessions) | ⬆ up | +3.77% | -12.48% … +20.01% | 0.45 |

Family scores (−1…+1): technicals +0.30, sentiment -0.05, agent —, fundamentals +0.40, price-forecast +0.20.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/150344__sweep-lite-phdc-ca-market-egx__runw5-sweeplite-phdc-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-phdc-001`._
