# 🐊 Borsagator digest — sweep POUL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-18 13:58 UTC · finished 14:05 UTC · 15 tools

⚠️ **Degraded sweep:** tradingagents did not finish cleanly — families absent: agent. This digest is published with the banner so a 3-family ensemble is never read as a 5-family one (see #65 for tool keys).

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1208; POUL.CA.csv_last_date=2026-11-16; POUL.CA.csv_last_close=8.020000457763672 | — |
| openbb | data | ok | rows_POUL_CA.csv=484; POUL_CA.csv_last_date=2026-11-17; POUL_CA.csv_last_close=7.570000171661377 | — |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-18; egxpy_poul.csv_last_close=7.7 | — |
| pandas-ta | technicals | ok | macd_signal=-2.6155; ticker=POUL.CA; date=2026-11-17; open=8.02; high=8.09 | — |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6524; rows_used=1924; last_date=2026-11-17; last_close=7.570000171661377 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2182; rows_ohlc.csv=2182 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2431; poul_ohlc.csv_last_close=7.570000171661377 | — |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=5 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=11 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=11 | — |
| tradingagents | agent | failed | ERROR: COHERE_API_KEY is not set. Add it as a repository secret named COHERE_API_KEY before running in normal mode. | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-15; forecast.csv_last_close=9.2756 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-18T14:05:21Z; tool=news-disclosure; news_count=26; disclosure_count=10 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 7.7 (egx-data/egxpy_poul.csv, 2026-11-18). Daily volatility σ 6.80% (egx-data/egxpy_poul.csv (σ60=0.0367, σ10=0.0680)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — earnings event: القاهرة للدواجن تتصدر الأسهم الأكثر تراجعًا بالبورصة بخسائر 17% - شبكة تواصل الإخبارية.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.993, technicals ×0.742, sentiment ×1.024, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -24.68% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +7.08% | -7.84% … +22.00% | 0.30 |
| week (≈3 sessions) | ⬆ up | +14.61% | -12.15% … +41.38% | 0.30 |
| month (≈14 sessions) | ⬆ up | +16.94% | -35.08% … +68.96% | 0.30 |

Family scores (−1…+1): technicals +0.40, sentiment -0.03, agent —, fundamentals +0.40, price-forecast +0.40.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-18/140522__sweep-poul-ca-market-egx__runmanual-sweep-2026-11-18-001`; point-in-time inputs in `worker-runs/2026-11-18/manual-sweep-2026-11-18-001`._
