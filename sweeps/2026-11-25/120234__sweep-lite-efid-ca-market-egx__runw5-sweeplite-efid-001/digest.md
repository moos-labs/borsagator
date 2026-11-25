# 🐊 Borsagator digest — sweep-lite EFID.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 11:59 UTC · finished 12:02 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EFID.CA.csv=1208; EFID.CA.csv_last_date=2026-11-23; EFID.CA.csv_last_close=20.399999618530273 | — |
| openbb | data | ok | rows_EFID_CA.csv=484; EFID_CA.csv_last_date=2026-11-24; EFID_CA.csv_last_close=20.399999618530273 | — |
| egx-data | data | ok | ticker=EFID.CA; symbol=EFID; rows_egxpy_efid.csv=2824; egxpy_efid.csv_last_date=2026-11-25; egxpy_efid.csv_last_close=20.66 | — |
| pandas-ta | technicals | ok | macd_signal=-0.0702; ticker=EFID.CA; date=2026-11-24; open=20.4; high=20.4 | — |
| talib | technicals | ok | ticker=EFID.CA; drop_before=2019-01-01; rows_fetched=2862; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=7 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=7 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=7 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=19.0769 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EFID.CA; fetched_at=2026-11-25T12:02:33Z; tool=news-disclosure; news_count=4; disclosure_count=2 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 20.66 (egx-data/egxpy_efid.csv, 2026-11-25). Daily volatility σ 3.17% (egx-data/egxpy_efid.csv (σ60=0.0288, σ10=0.0317)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: Edita Food Industries S.A.E (CAI:EFID) Q3 2026 Earnings Call Highlights: Record Revenue of.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.04% | -7.06% … +6.97% | 0.30 |
| week (≈3 sessions) | ➡ flat | +0.13% | -12.03% … +12.30% | 0.30 |
| month (≈14 sessions) | ⬇ down | -4.40% | -30.78% … +21.99% | 0.30 |

Family scores (−1…+1): technicals +0.45, sentiment +0.62, agent —, fundamentals -0.10, price-forecast -0.32.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/120234__sweep-lite-efid-ca-market-egx__runw5-sweeplite-efid-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-efid-001`._
