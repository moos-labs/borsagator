# 🐊 Borsagator digest — sweep-lite MTIE.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 09:15 UTC · finished 09:19 UTC · 14 tools

⚠️ **Degraded sweep:** finbert, finbert-tone, financial-roberta did not finish cleanly — families absent: sentiment. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_MTIE.CA.csv=1211; MTIE.CA.csv_last_date=2026-11-25; MTIE.CA.csv_last_close=6.75 | — |
| openbb | data | ok | rows_MTIE_CA.csv=484; MTIE_CA.csv_last_date=2026-11-26; MTIE_CA.csv_last_close=6.619999885559082 | — |
| egx-data | data | ok | ticker=MTIE.CA; symbol=MTIE; rows_egxpy_mtie.csv=2335; egxpy_mtie.csv_last_date=2026-11-26; egxpy_mtie.csv_last_close=6.62 | — |
| pandas-ta | technicals | ok | macd_signal=-0.244; ticker=MTIE.CA; date=2026-11-26; open=6.75; high=6.9 | — |
| talib | technicals | ok | ticker=MTIE.CA; drop_before=2019-01-01; rows_fetched=2372; rows_used=1933; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| finbert-tone | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| financial-roberta | sentiment | failed | ERROR: no English headlines found for this ticker | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=6.9951 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=MTIE.CA; fetched_at=2026-11-27T09:19:46Z; tool=news-disclosure; news_count=34; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 6.62 (egx-data/egxpy_mtie.csv, 2026-11-26). Daily volatility σ 3.37% (egx-data/egxpy_mtie.csv (σ60=0.0337, σ10=0.0293)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.40/day). News risk: **shock** — earnings event: متى يستعيد الذهب صعوده؟ خبراء يحددون مستويات التراجع - شبكة تواصل الإخبارية.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -5.81% … +5.81% | 0.30 |
| week | ➡ flat | +0.00% | -14.46% … +14.46% | 0.30 |
| month | ➡ flat | +0.00% | -27.79% … +27.79% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment -0.03, agent —, fundamentals +0.15, price-forecast +0.18.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/091948__sweep-lite-mtie-ca-market-egx__runw6-sweeplite-mtie-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-mtie-002`._
