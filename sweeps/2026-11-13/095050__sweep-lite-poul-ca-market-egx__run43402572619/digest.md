# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX

Started 2026-11-13 09:35 UTC · finished 09:50 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1254; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=354.8800048828125; rows_POUL.CA.csv=1210; POUL.CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43402603095) |
| openbb | data | ok | rows_AAPL.csv=501; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=354.8800048828125; rows_POUL_CA.csv=485; POUL_CA.csv_last_date=2026-11-12 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43402672540) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-12; egxpy_poul.csv_last_close=10.15 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43402787166) |
| pandas-ta | technicals | ok | macd_signal=-2.9153; ticker=POUL.CA; date=2026-11-12; open=10.2; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43402898844) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6522; rows_used=1922; last_date=2026-11-12; last_close=10.149999618530273 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43402964464) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2180; rows_ohlc.csv=2180 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43403029748) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2429; poul_ohlc.csv_last_close=10.149999618530273 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43403139780) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43403303014) |
| finbert | sentiment | ok | label=live; model=ProsusAI/finbert; count=9 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43403418070) |
| finbert-tone | sentiment | ok | label=live; model=yiyanghkust/finbert-tone; count=9 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43403625420) |
| financial-roberta | sentiment | ok | label=live; model=soleimanian/financial-roberta-large-sentiment; count=9 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43403835172) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-10; forecast.csv_last_close=9.7086 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43404046243) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43404204728) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-13T09:50:33Z; tool=news-disclosure; news_count=25; disclosure_count=6 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43404294121) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v2)

Base price 10.15 (pandas-ta). Daily volatility σ 2.25% (egx-data/egxpy_poul.csv (σ60=0.0225, σ10=0.0183)). News risk: **shock** — shock headline(s): «القاهرة للدواجن» تحقق أرباحًا بقيمة 1.43 مليار جنيه خلال 9 أشهر بتراجع 39.1% - شبكة تواصل; shock headline(s): رغم ارتفاع الإيرادات.. أرباح القاهرة للدواجن تهبط 39% بأول 9 شهور من 2026 - https://www.yo; shock headline(s): القاهرة للدواجن تسجل 1.43 مليار جنيه أرباحًا خلال 9 أشهر - عالم المال.
Ranges are anchored in realized volatility. Confidence is provisional (uncalibrated) until the scoring ledger has history.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ⬆ up | +1.16% | -3.63% … +5.95% | 0.30 |
| week | ⬇ down | -1.01% | -11.79% … +9.77% | 0.30 |
| month | ⬇ down | -1.76% | -24.36% … +20.84% | 0.30 |

Family scores (−1…+1): technicals +0.30, sentiment -0.20, agent —, fundamentals +0.40, price-forecast -0.21.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
