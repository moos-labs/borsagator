# 🐊 Borsagator digest — sweep POUL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 21:26 UTC · finished 21:43 UTC · 15 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_POUL.CA.csv=1208; POUL.CA.csv_last_date=2026-11-23; POUL.CA.csv_last_close=7.099999904632568 | — |
| openbb | data | ok | rows_POUL_CA.csv=484; POUL_CA.csv_last_date=2026-11-24; POUL_CA.csv_last_close=7.099999904632568 | — |
| egx-data | data | ok | ticker=POUL.CA; symbol=POUL; rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-25; egxpy_poul.csv_last_close=6.73 | — |
| pandas-ta | technicals | ok | macd_signal=-2.2187; ticker=POUL.CA; date=2026-11-24; open=7.1; high=7.1 | — |
| talib | technicals | ok | ticker=POUL.CA; drop_before=2019-01-01; rows_fetched=6529; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=15 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=15 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=15 | — |
| tradingagents | agent | ok | final_rating=Buy; company_of_interest=POUL.CA; asset_type=stock; trade_date=2026-11-25; past_context= | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=8.7545 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-25T21:43:13Z; tool=news-disclosure; news_count=29; disclosure_count=10 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 6.73 (egx-data/egxpy_poul.csv, 2026-11-25). Daily volatility σ 6.54% (egx-data/egxpy_poul.csv (σ60=0.0378, σ10=0.0654)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — earnings event: Cairo Poultry stock: Nine-month net profit falls 38.3% - ad-hoc-news.de.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

💰 **Corporate action:** dividend 1.9/share, ex-date 2026-11-16 — a mechanical ≈ -28.23% move is expected on the ex-date (not a market signal). Horizons spanning it are marked; the calibration ledger will score them dividend-adjusted. — via verified EGX disclosure event ev_bf7532c5c9185f9f113d (verbatim ex-date)

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -6.52% … +6.52% | 0.30 |
| week | ➡ flat | +0.00% | -16.22% … +16.22% | 0.30 |
| month | ➡ flat | +0.00% | -31.16% … +31.16% | 0.30 |

Family scores (−1…+1): technicals +0.50, sentiment +0.03, agent +0.75, fundamentals +0.40, price-forecast +0.50.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-agent, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-25/214314__sweep-poul-ca-market-egx__runmanual-sweep-2026-11-25-cohere65`; point-in-time inputs in `worker-runs/2026-11-25/manual-sweep-2026-11-25-cohere65`._
