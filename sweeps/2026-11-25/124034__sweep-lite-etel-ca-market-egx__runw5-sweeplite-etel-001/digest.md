# 🐊 Borsagator digest — sweep-lite ETEL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 12:32 UTC · finished 12:40 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ETEL.CA.csv=1208; ETEL.CA.csv_last_date=2026-11-23; ETEL.CA.csv_last_close=139.97999572753906 | — |
| openbb | data | ok | rows_ETEL_CA.csv=484; ETEL_CA.csv_last_date=2026-11-24; ETEL_CA.csv_last_close=141.0 | — |
| egx-data | data | ok | ticker=ETEL.CA; symbol=ETEL; rows_egxpy_etel.csv=3000; egxpy_etel.csv_last_date=2026-11-25; egxpy_etel.csv_last_close=140.1 | — |
| pandas-ta | technicals | ok | macd_signal=1.1188; ticker=ETEL.CA; date=2026-11-24; open=139.98; high=142.5 | — |
| talib | technicals | ok | ticker=ETEL.CA; drop_before=2019-01-01; rows_fetched=5218; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=27 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=27 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=27 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=141.463 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ETEL.CA; fetched_at=2026-11-25T12:40:33Z; tool=news-disclosure; news_count=40; disclosure_count=11 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 140.1 (egx-data/egxpy_etel.csv, 2026-11-25). Daily volatility σ 2.80% (egx-data/egxpy_etel.csv (σ60=0.0280, σ10=0.0223)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — management event: Tamer El Mahdi - The CEO Magazine; earnings event: شكوي وبيان رسمي من الترسانة ضد حكم مباراة المصرية للاتصالات.. ماذا حدث؟ - Masrawy.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.25% | -5.55% … +6.04% | 0.30 |
| week (≈3 sessions) | ⬆ up | +1.29% | -8.51% … +11.09% | 0.30 |
| month (≈14 sessions) | ⬆ up | +1.55% | -19.57% … +22.68% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment +0.36, agent —, fundamentals +0.15, price-forecast +0.05.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/124034__sweep-lite-etel-ca-market-egx__runw5-sweeplite-etel-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-etel-001`._
