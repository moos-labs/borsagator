# 🐊 Borsagator digest — sweep-lite ARCC.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 11:26 UTC · finished 11:29 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ARCC.CA.csv=1208; ARCC.CA.csv_last_date=2026-11-23; ARCC.CA.csv_last_close=66.08999633789062 | — |
| openbb | data | ok | rows_ARCC_CA.csv=484; ARCC_CA.csv_last_date=2026-11-24; ARCC_CA.csv_last_close=67.02999877929688 | — |
| egx-data | data | ok | ticker=ARCC.CA; symbol=ARCC; rows_egxpy_arcc.csv=3000; egxpy_arcc.csv_last_date=2026-11-25; egxpy_arcc.csv_last_close=66.53 | — |
| pandas-ta | technicals | ok | macd_signal=0.1325; ticker=ARCC.CA; date=2026-11-24; open=66.09; high=68.0 | — |
| talib | technicals | ok | ticker=ARCC.CA; drop_before=2019-01-01; rows_fetched=3088; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=11 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=11 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=11 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=64.7639 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ARCC.CA; fetched_at=2026-11-25T11:29:24Z; tool=news-disclosure; news_count=12; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 66.53 (egx-data/egxpy_arcc.csv, 2026-11-25). Daily volatility σ 2.90% (egx-data/egxpy_arcc.csv (σ60=0.0290, σ10=0.0256)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: "آرك إنفستمنت" تفوّت مكاسب بـ10.7 مليون دولار بعد بيع أسهم "إنفيديا" - المشهد العربي.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.67% | -6.67% … +5.33% | 0.30 |
| week (≈3 sessions) | ➡ flat | -0.53% | -11.02% … +9.95% | 0.30 |
| month (≈14 sessions) | ⬇ down | -0.97% | -25.30% … +23.36% | 0.30 |

Family scores (−1…+1): technicals -0.45, sentiment -0.20, agent —, fundamentals +0.40, price-forecast -0.12.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/112926__sweep-lite-arcc-ca-market-egx__runw5-sweeplite-arcc-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-arcc-001`._
