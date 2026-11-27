# 🐊 Borsagator digest — sweep-lite EGAL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 03:05 UTC · finished 03:07 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_EGAL.CA.csv=1208; EGAL.CA.csv_last_date=2026-11-24; EGAL.CA.csv_last_close=302.0 | — |
| openbb | data | ok | rows_EGAL_CA.csv=483; EGAL_CA.csv_last_date=2026-11-25; EGAL_CA.csv_last_close=293.3500061035156 | — |
| egx-data | data | ok | ticker=EGAL.CA; symbol=EGAL; rows_egxpy_egal.csv=3000; egxpy_egal.csv_last_date=2026-11-26; egxpy_egal.csv_last_close=292.5 | — |
| pandas-ta | technicals | ok | macd_signal=-3.7889; ticker=EGAL.CA; date=2026-11-25; open=298.0; high=299.0 | — |
| talib | technicals | ok | ticker=EGAL.CA; drop_before=2019-01-01; rows_fetched=6534; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=16 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=40 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=31 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=31 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=299.5266 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=EGAL.CA; fetched_at=2026-11-27T03:07:44Z; tool=news-disclosure; news_count=31; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 292.5 (egx-data/egxpy_egal.csv, 2026-11-26). Daily volatility σ 2.21% (egx-data/egxpy_egal.csv (σ60=0.0221, σ10=0.0179)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — earnings event: Agnico Eagle Mines Limited (AEM.TO) Stock Price, News, Quote & History - Yahoo! Finance Ca; earnings event: Agnico Eagle Mines Limited (AEM.TO) stock price, news, quote and history - Yahoo Finance U; earnings event: American Eagle options signal 13% move around Dec. 2 earnings By Investing.com - Investing.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -3.80% … +3.80% | 0.30 |
| week | ➡ flat | +0.00% | -9.47% … +9.47% | 0.30 |
| month | ➡ flat | +0.00% | -18.19% … +18.19% | 0.30 |

Family scores (−1…+1): technicals -0.20, sentiment +0.14, agent —, fundamentals +0.40, price-forecast +0.12.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/030746__sweep-lite-egal-ca-market-egx__runw6-sweeplite-egal-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-egal-002`._
