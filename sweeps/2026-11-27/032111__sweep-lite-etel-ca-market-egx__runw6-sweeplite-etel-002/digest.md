# 🐊 Borsagator digest — sweep-lite ETEL.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 03:12 UTC · finished 03:21 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ETEL.CA.csv=1208; ETEL.CA.csv_last_date=2026-11-24; ETEL.CA.csv_last_close=141.0 | — |
| openbb | data | ok | rows_ETEL_CA.csv=483; ETEL_CA.csv_last_date=2026-11-25; ETEL_CA.csv_last_close=139.1999969482422 | — |
| egx-data | data | ok | ticker=ETEL.CA; symbol=ETEL; rows_egxpy_etel.csv=3000; egxpy_etel.csv_last_date=2026-11-26; egxpy_etel.csv_last_close=135.9 | — |
| pandas-ta | technicals | ok | macd_signal=1.337; ticker=ETEL.CA; date=2026-11-25; open=141.0; high=141.28 | — |
| talib | technicals | ok | ticker=ETEL.CA; drop_before=2019-01-01; rows_fetched=5219; rows_used=1930; last_date=2026-11-25 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2188; rows_ohlc.csv=2188 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2437; poul_ohlc.csv_last_close=6.730000019073486 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=28 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=28 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=28 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-23; forecast.csv_last_close=138.7034 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ETEL.CA; fetched_at=2026-11-27T03:21:10Z; tool=news-disclosure; news_count=40; disclosure_count=10 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 135.9 (egx-data/egxpy_etel.csv, 2026-11-26). Daily volatility σ 2.83% (egx-data/egxpy_etel.csv (σ60=0.0283, σ10=0.0235)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — management event: Telecom Egypt CEO highlights social impact of digital infrastructure through healthcare in; earnings event: قفزة قياسية.. أرباح المصرية للاتصالات WE تصعد لـ 24.4 مليار جنيه - شبكة تواصل الإخبارية; earnings event: هل أصبح سهم المصرية للاتصالات أكثر جاذبية بعد نمو الأرباح وتراجع المديونية؟ - www.youlyou..
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -4.88% … +4.88% | 0.30 |
| week | ➡ flat | +0.00% | -12.15% … +12.15% | 0.30 |
| month | ➡ flat | +0.00% | -23.34% … +23.34% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment +0.35, agent —, fundamentals +0.15, price-forecast +0.08.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/032111__sweep-lite-etel-ca-market-egx__runw6-sweeplite-etel-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-etel-002`._
