# 🐊 Borsagator digest — sweep-lite JUFO.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:40 UTC · finished 13:42 UTC · 14 tools

⚠️ **Degraded sweep:** news-disclosure did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_JUFO.CA.csv=1208; JUFO.CA.csv_last_date=2026-11-23; JUFO.CA.csv_last_close=22.0 | — |
| openbb | data | ok | rows_JUFO_CA.csv=484; JUFO_CA.csv_last_date=2026-11-24; JUFO_CA.csv_last_close=22.0 | — |
| egx-data | data | ok | ticker=JUFO.CA; symbol=JUFO; rows_egxpy_jufo.csv=3000; egxpy_jufo.csv_last_date=2026-11-25; egxpy_jufo.csv_last_close=21.85 | — |
| pandas-ta | technicals | ok | macd_signal=-0.3396; ticker=JUFO.CA; date=2026-11-24; open=22.0; high=22.0 | — |
| talib | technicals | ok | ticker=JUFO.CA; drop_before=2019-01-01; rows_fetched=4066; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=1 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=23.5262 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | failed | ERROR: no items fetched from any source | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 21.85 (egx-data/egxpy_jufo.csv, 2026-11-25). Daily volatility σ 2.54% (egx-data/egxpy_jufo.csv (σ60=0.0254, σ10=0.0199)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **unknown** — news overlay unavailable — risk unassessed, confidence capped.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.12% | -3.60% … +5.85% | 0.35 |
| week (≈3 sessions) | ⬆ up | +2.71% | -5.65% … +11.06% | 0.35 |
| month (≈14 sessions) | ⬆ up | +4.70% | -12.91% … +22.31% | 0.35 |

Family scores (−1…+1): technicals -0.20, sentiment +0.00, agent —, fundamentals -0.10, price-forecast +0.40.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/134241__sweep-lite-jufo-ca-market-egx__runw5-sweeplite-jufo-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-jufo-001`._
