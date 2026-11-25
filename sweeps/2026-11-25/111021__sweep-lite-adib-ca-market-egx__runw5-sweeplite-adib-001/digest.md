# 🐊 Borsagator digest — sweep-lite ADIB.CA market=EGX
<!-- borsagator-digest-status: complete -->

Started 2026-11-25 11:05 UTC · finished 11:10 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_ADIB.CA.csv=1210; ADIB.CA.csv_last_date=2026-11-23; ADIB.CA.csv_last_close=46.43000030517578 | — |
| openbb | data | ok | rows_ADIB_CA.csv=484; ADIB_CA.csv_last_date=2026-11-24; ADIB_CA.csv_last_close=46.150001525878906 | — |
| egx-data | data | ok | ticker=ADIB.CA; symbol=ADIB; rows_egxpy_adib.csv=3000; egxpy_adib.csv_last_date=2026-11-25; egxpy_adib.csv_last_close=46.31 | — |
| pandas-ta | technicals | ok | macd_signal=-0.1708; ticker=ADIB.CA; date=2026-11-24; open=46.43; high=47.0 | — |
| talib | technicals | ok | ticker=ADIB.CA; drop_before=2019-01-01; rows_fetched=6535; rows_used=1931; last_date=2026-11-24 | — |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2187; rows_ohlc.csv=2187 | — |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2436; poul_ohlc.csv_last_close=7.099999904632568 | — |
| financetoolkit | fundamentals | ok | rows_statements.csv=13 | — |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=27 | — |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=27 | — |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=27 | — |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-22; forecast.csv_last_close=46.8002 | — |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | — |
| news-disclosure | news | ok | ticker=ADIB.CA; fetched_at=2026-11-25T11:10:20Z; tool=news-disclosure; news_count=34; disclosure_count=1 | — |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 46.31 (egx-data/egxpy_adib.csv, 2026-11-25). Daily volatility σ 2.21% (egx-data/egxpy_adib.csv (σ60=0.0221, σ10=0.0109)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.66/day). News risk: **shock** — management event: عمرو أديب يهاجم الأهلي بعد هزيمته أمام بيراميدز 2-0 ويطالب ببقاء عموتة - شبكة تواصل الإخبا; management event: عمرو أديب بعد خسارة الأهلي أمام بيراميدز: الفريق السماوي يستحق لقب الدوري.. وتمسكوا بعموتة.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

Applied weights (ledger): price-forecast ×0.5, technicals ×0.679, sentiment ×1.068, agent ×1, fundamentals ×1.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | -0.45% | -5.03% … +4.12% | 0.30 |
| week (≈3 sessions) | ➡ flat | +0.43% | -7.58% … +8.44% | 0.30 |
| month (≈14 sessions) | ⬆ up | +1.47% | -16.41% … +19.35% | 0.30 |

Family scores (−1…+1): technicals -0.30, sentiment +0.07, agent —, fundamentals +0.40, price-forecast +0.06.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.

---

## 📊 Benchmark freeze (v1)

Frozen entrants: family-price-forecast, family-technicals, family-sentiment, family-fundamentals, kronos-alone, buy-and-hold.
Absent entrants: family-agent (family-did-not-vote); raw-llm-cohere (llm-key-absent).

Frozen files live under `benchmark/` in this sweep dir; the calibration ledger scores them in a separate benchmark table (issue #79).


_Merged on the worker (borsagator-worker-5) at `sweeps/2026-11-25/111021__sweep-lite-adib-ca-market-egx__runw5-sweeplite-adib-001`; point-in-time inputs in `worker-runs/2026-11-25/w5-sweeplite-adib-001`._
