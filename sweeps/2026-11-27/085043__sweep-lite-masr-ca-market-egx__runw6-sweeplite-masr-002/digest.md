# 🐊 Borsagator digest — sweep-lite MASR.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-27 08:41 UTC · finished 08:50 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_MASR.CA.csv=1209; MASR.CA.csv_last_date=2026-11-25; MASR.CA.csv_last_close=6.230000019073486 | — |
| openbb | data | ok | rows_MASR_CA.csv=484; MASR_CA.csv_last_date=2026-11-26; MASR_CA.csv_last_close=6.349999904632568 | — |
| egx-data | data | ok | ticker=MASR.CA; symbol=MASR; rows_egxpy_masr.csv=3000; egxpy_masr.csv_last_date=2026-11-26; egxpy_masr.csv_last_close=6.35 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1774; ticker=MASR.CA; date=2026-11-26; open=6.23; high=6.35 | — |
| talib | technicals | ok | ticker=MASR.CA; drop_before=2019-01-01; rows_fetched=6538; rows_used=1931; last_date=2026-11-26 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2189; rows_ohlc.csv=2189 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2438; poul_ohlc.csv_last_close=6.829999923706055 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=31 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=31 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=31 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-24; forecast.csv_last_close=6.6301 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=MASR.CA; fetched_at=2026-11-27T08:50:42Z; tool=news-disclosure; news_count=40; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 6.35 (egx-data/egxpy_masr.csv, 2026-11-26). Daily volatility σ 3.50% (egx-data/egxpy_masr.csv (σ60=0.0350, σ10=0.0245)). Kronos forecast rows are trading sessions — horizons read the row at the ledger's session count directly (price-series density 0.66/day). News risk: **shock** — earnings event: أسعار الذهب في مصر اليوم الجمعة 27 نوفمبر 2026.. تحديث عيار 21 - CNN الاقتصادية; legal event: جريمة قتل بدافع «الشرف» تُثير جدلاً في مصر - الشرق الأوسط; earnings event: مصر.. النيابة تعلن ضبط المتهم بالتسبب في حادث "حريق دائري الوراق" - الشرق للأخبار.
Ranges are the calibrated range (issue #594): centre 0, half-width k × σ60 × √(ledger sessions), k = 1.15 / 1.28 / 1.20. The risk overlay widens the range only (multiplier untested). Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (frozen-v2): price-forecast ×1, technicals ×1, sentiment ×1, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.00% | -6.04% … +6.04% | 0.30 |
| week | ➡ flat | +0.00% | -15.03% … +15.03% | 0.30 |
| month | ➡ flat | +0.00% | -28.88% … +28.88% | 0.30 |

Family scores (−1…+1): technicals -0.30, sentiment -0.16, agent —, fundamentals +0.40, price-forecast +0.14.
Headline is the centre-0 range; family tilts are shadow challengers (tilt_centre_pct in ensemble.json), adopted only if they pass the RangeSkill gate (#594).

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-technicals, family-sentiment, family-fundamentals, kronos-alone, raw-llm-cohere, buy-and-hold.
Absent entrants: family-price-forecast (family-did-not-vote); family-agent (family-did-not-vote).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-6) at `sweeps/2026-11-27/085043__sweep-lite-masr-ca-market-egx__runw6-sweeplite-masr-002`; point-in-time inputs in `worker-runs/2026-11-27/w6-sweeplite-masr-002`._
