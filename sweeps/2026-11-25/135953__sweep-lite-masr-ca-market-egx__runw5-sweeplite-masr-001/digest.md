# 🐊 Borsagator digest — sweep-lite MASR.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 13:55 UTC · finished 13:59 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_MASR.CA.csv=1208; MASR.CA.csv_last_date=2026-11-23; MASR.CA.csv_last_close=6.269999980926514 | — |
| openbb | data | ok | rows_MASR_CA.csv=484; MASR_CA.csv_last_date=2026-11-24; MASR_CA.csv_last_close=6.360000133514404 | — |
| egx-data | data | ok | ticker=MASR.CA; symbol=MASR; rows_egxpy_masr.csv=3000; egxpy_masr.csv_last_date=2026-11-25; egxpy_masr.csv_last_close=6.23 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1647; ticker=MASR.CA; date=2026-11-24; open=6.27; high=6.43 | — |
| talib | technicals | ok | ticker=MASR.CA; drop_before=2019-01-01; rows_fetched=6536; rows_used=1929; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=17 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=40 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=40 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=40 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=6.6919 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=MASR.CA; fetched_at=2026-11-25T13:59:51Z; tool=news-disclosure; news_count=40; disclosure_count=0 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 6.23 (egx-data/egxpy_masr.csv, 2026-11-25). Daily volatility σ 3.49% (egx-data/egxpy_masr.csv (σ60=0.0349, σ10=0.0228)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — legal event: "اتفرج ببلاش".. قناة مفتوحة تنقل مباراة مصر وبنما في كأس العالم للناشئين - Masrawy; legal event: الصحافة العالمية: قرارات تحكيمية مثيرة للجدل تخرج مصر من المونديال - الشرق الأوسط.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.37% | -6.19% … +8.94% | 0.30 |
| week (≈3 sessions) | ⬆ up | +2.48% | -10.60% … +15.57% | 0.30 |
| month (≈14 sessions) | ⬆ up | +5.89% | -22.53% … +34.31% | 0.30 |

Family scores (−1…+1): technicals -0.30, sentiment -0.09, agent —, fundamentals +0.40, price-forecast +0.28.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/135953__sweep-lite-masr-ca-market-egx__runw5-sweeplite-masr-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-masr-001`._
