# 🐊 Borsagator digest — sweep-lite COMI.CA market=EGX

Started 2026-11-15 13:08 UTC · finished 13:25 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1255; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43717424636) |
| openbb | data | ok | rows_AAPL.csv=500; AAPL.csv_last_date=2026-11-13; AAPL.csv_last_close=356.2699890136719; rows_POUL_CA.csv=483; POUL_CA.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43717470322) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-15; egxpy_poul.csv_last_close=10.0 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43717538367) |
| pandas-ta | technicals | ok | macd_signal=-0.6247; ticker=COMI.CA; date=2026-11-12; open=130.34; high=130.32 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43717611632) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43717653664) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43717696300) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43717764796) |
| financetoolkit | fundamentals | ok | rows_statements.csv=13 | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43717867436) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=40 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43717932684) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=40 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43718028539) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=40 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43718156436) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-10; forecast.csv_last_close=121.3395 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43718313210) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43718412865) |
| news-disclosure | news | ok | ticker=COMI.CA; fetched_at=2026-11-15T13:24:51Z; tool=news-disclosure; news_count=40; disclosure_count=2 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43718452725) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.149999618530273 (consensus median). Daily volatility σ 17.65% (quantstats/ohlc.csv (σ60=0.1765, σ10=0.0183)). Kronos bars are calendar days — horizons are scaled to trading sessions (density 0.71/day). News risk: **shock** — management event: Nvidia stock faces new twist as Colette Kress breaks silence: what its new CEO reveal - In.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

⚠️ **Price sources disagree** (spread 1168.47%: pandas-ta/indicators.csv 128.75, talib/indicators.csv 10.15) — this forecast stands on consensus median = 10.15.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +702.27% | +661.88% … +742.66% | 0.30 |
| week (≈4 sessions) | ⬆ up | +711.50% | +630.41% … +792.60% | 0.30 |
| month (≈15 sessions) | ⬆ up | +674.99% | +523.02% … +826.95% | 0.30 |

Family scores (−1…+1): technicals +0.20, sentiment +0.16, agent —, fundamentals +0.40, price-forecast +1.00.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
