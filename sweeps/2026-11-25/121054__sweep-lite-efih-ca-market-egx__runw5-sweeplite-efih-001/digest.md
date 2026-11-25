# 🐊 Borsagator digest — sweep-lite EFIH.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 12:07 UTC · finished 12:10 UTC · 14 tools

⚠️ **Degraded sweep:** financial-roberta did not finish cleanly — families absent: —. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EFIH.CA.csv=1210; EFIH.CA.csv_last_date=2026-11-23; EFIH.CA.csv_last_close=24.799999237060547 | — |
| openbb | data | ok | rows_EFIH_CA.csv=484; EFIH_CA.csv_last_date=2026-11-24; EFIH_CA.csv_last_close=25.290000915527344 | — |
| egx-data | data | ok | ticker=EFIH.CA; symbol=EFIH; rows_egxpy_efih.csv=1238; egxpy_efih.csv_last_date=2026-11-25; egxpy_efih.csv_last_close=25.0 | — |
| pandas-ta | technicals | ok | macd_signal=0.3984; ticker=EFIH.CA; date=2026-11-24; open=24.8; high=25.4 | — |
| talib | technicals | ok | ticker=EFIH.CA; drop_before=2019-01-01; rows_fetched=1236; rows_used=1236; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=1 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=1 | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=24.4503 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EFIH.CA; fetched_at=2026-11-25T12:10:53Z; tool=news-disclosure; news_count=4; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 25.0 (egx-data/egxpy_efih.csv, 2026-11-25). Daily volatility σ 2.84% (egx-data/egxpy_efih.csv (σ60=0.0284, σ10=0.0231)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **none**.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.10% | -4.00% … +4.20% | 0.59 |
| week (≈3 sessions) | ➡ flat | -0.11% | -7.31% … +7.10% | 0.58 |
| month (≈14 sessions) | ⬇ down | -1.87% | -17.56% … +13.82% | 0.59 |

Family scores (−1…+1): technicals +0.30, sentiment +0.56, agent —, fundamentals -0.35, price-forecast -0.10.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/121054__sweep-lite-efih-ca-market-egx__runw5-sweeplite-efih-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-efih-001`._
