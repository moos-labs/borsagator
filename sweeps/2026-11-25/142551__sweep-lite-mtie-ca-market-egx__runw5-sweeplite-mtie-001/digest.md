# 🐊 Borsagator digest — sweep-lite MTIE.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 14:21 UTC · finished 14:25 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, finbert-tone, financial-roberta did not finish cleanly — families absent: sentiment. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_MTIE.CA.csv=1210; MTIE.CA.csv_last_date=2026-11-23; MTIE.CA.csv_last_close=6.28000020980835 | — |
| openbb | data | ok | rows_MTIE_CA.csv=484; MTIE_CA.csv_last_date=2026-11-24; MTIE_CA.csv_last_close=6.599999904632568 | — |
| egx-data | data | ok | ticker=MTIE.CA; symbol=MTIE; rows_egxpy_mtie.csv=2334; egxpy_mtie.csv_last_date=2026-11-25; egxpy_mtie.csv_last_close=6.75 | — |
| pandas-ta | technicals | ok | macd_signal=-0.2462; ticker=MTIE.CA; date=2026-11-24; open=6.28; high=6.9 | — |
| talib | technicals | ok | ticker=MTIE.CA; drop_before=2019-01-01; rows_fetched=2370; rows_used=1931; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=6.9792 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=MTIE.CA; fetched_at=2026-11-25T14:25:49Z; tool=news-disclosure; news_count=34; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 6.75 (egx-data/egxpy_mtie.csv, 2026-11-25). Daily volatility σ 3.36% (egx-data/egxpy_mtie.csv (σ60=0.0336, σ10=0.0292)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.40/day). News risk: **shock** — earnings event: متى يستعيد الذهب صعوده؟ خبراء يحددون مستويات التراجع - شبكة تواصل الإخبارية.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.67, sentiment ×1.063, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬇ down | -4.44% | -12.08% … +3.19% | 0.30 |
| week (≈2 sessions) | ⬇ down | -2.18% | -11.84% … +7.48% | 0.30 |
| month (≈8 sessions) | ⬆ up | +2.43% | -17.06% … +21.92% | 0.30 |

Family scores (−1…+1): technicals -0.20, sentiment -0.03, agent —, fundamentals +0.15, price-forecast +0.18.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/142551__sweep-lite-mtie-ca-market-egx__runw5-sweeplite-mtie-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-mtie-001`._
