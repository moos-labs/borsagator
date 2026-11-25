# 🐊 Borsagator digest — sweep-lite SAUD.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 20:05 UTC · finished 20:12 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_SAUD.CA.csv=1208; SAUD.CA.csv_last_date=2026-11-23; SAUD.CA.csv_last_close=22.6299991607666 | — |
| openbb | data | ok | rows_SAUD_CA.csv=484; SAUD_CA.csv_last_date=2026-11-24; SAUD_CA.csv_last_close=22.260000228881836 | — |
| egx-data | data | ok | ticker=SAUD.CA; symbol=SAUD; rows_egxpy_saud.csv=3000; egxpy_saud.csv_last_date=2026-11-25; egxpy_saud.csv_last_close=21.95 | — |
| pandas-ta | technicals | ok | macd_signal=0.1663; ticker=SAUD.CA; date=2026-11-24; open=22.63; high=22.94 | — |
| talib | technicals | ok | ticker=SAUD.CA; drop_before=2019-01-01; rows_fetched=6528; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=13 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=4 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=4 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=4 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=21.6369 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=SAUD.CA; fetched_at=2026-11-25T20:12:38Z; tool=news-disclosure; news_count=22; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 21.95 (egx-data/egxpy_saud.csv, 2026-11-25). Daily volatility σ 2.46% (egx-data/egxpy_saud.csv (σ60=0.0246, σ10=0.0244)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — management event: US Tech Stock Rebound Opens Opportunities for Saudi Companies, with HUMAIN in Spotlight - ; earnings event: أوبك+ تجتمع في 29 نوفمبر لتحديد حصص 2027 دون خطة بعد ديسمبر - houseofsaud.com.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -4.24% … +4.24% | 0.30 |
| week | ➡ flat | +0.00% | -10.54% … +10.54% | 0.30 |
| month | ➡ flat | +0.00% | -20.25% … +20.25% | 0.30 |

Family scores (−1…+1): technicals +0.45, sentiment +0.52, agent —, fundamentals +0.40, price-forecast -0.06.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-25/201240__sweep-lite-saud-ca-market-egx__runw5-sweeplite-saud-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-saud-001`._
