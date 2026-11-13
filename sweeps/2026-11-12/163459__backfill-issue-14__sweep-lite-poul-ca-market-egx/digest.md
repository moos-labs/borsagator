# 🐊 Borsagator digest — sweep-lite POUL.CA market=EGX

Started 2026-11-12 16:19 UTC · finished 16:34 UTC · 14 tools

| Tool | Category | Status | Key results | Run |
|---|---|---|---|---|
| yahooquery | data | ok | rows_AAPL.csv=1255; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=358.3800048828125; rows_POUL.CA.csv=1209; POUL.CA.csv_last_date=2026-11-10 | [run](https://github.com/moos-labs/yahooquery-runner/actions/runs/43257418533) |
| openbb | data | ok | rows_AAPL.csv=502; AAPL.csv_last_date=2026-11-12; AAPL.csv_last_close=358.3999938964844; rows_POUL_CA.csv=485; POUL_CA.csv_last_date=2026-11-11 | [run](https://github.com/moos-labs/openbb-runner/actions/runs/43257505745) |
| egx-data | data | ok | rows_egxpy_poul.csv=3000; egxpy_poul.csv_last_date=2026-11-12; egxpy_poul.csv_last_close=10.15 | [run](https://github.com/moos-labs/egx-data-runner/actions/runs/43257656502) |
| pandas-ta | technicals | ok | macd_signal=-3.1305; ticker=POUL.CA; date=2026-11-11; open=10.29; high=10.4 | [run](https://github.com/moos-labs/pandas-ta-runner/actions/runs/43257823716) |
| talib | technicals | ok | ticker=POUL.CA; rows_fetched=6521; rows_used=1921; last_date=2026-11-11; last_close=10.199999809265137 | [run](https://github.com/moos-labs/talib-runner/actions/runs/43257911929) |
| quantstats | stats | ok | ticker=POUL.CA; source=Yahoo chart API (direct, via requests); exchange_tz=Africa/Cairo; rows=2179; rows_ohlc.csv=2179 | [run](https://github.com/moos-labs/quantstats-runner/actions/runs/43258063938) |
| vectorbt | backtest | ok | rows_poul_ohlc.csv=2428; poul_ohlc.csv_last_close=10.199999809265137 | [run](https://github.com/moos-labs/vectorbt-runner/actions/runs/43258280456) |
| financetoolkit | fundamentals | ok | company=Cairo Poultry Company (EGX: POUL); input_csv=data/poul_statements.csv | [run](https://github.com/moos-labs/financetoolkit-runner/actions/runs/43258496782) |
| finbert | sentiment | ok | label=poul-pilot; model=ProsusAI/finbert; count=13 | [run](https://github.com/moos-labs/finbert-runner/actions/runs/43258650292) |
| finbert-tone | sentiment | ok | label=run; model=yiyanghkust/finbert-tone; count=13 | [run](https://github.com/moos-labs/finbert-tone-runner/actions/runs/43258862429) |
| financial-roberta | sentiment | ok | label=run; model=soleimanian/financial-roberta-large-sentiment; count=13 | [run](https://github.com/moos-labs/roberta-sentiment-runner/actions/runs/43259127099) |
| kronos | forecast | ok | rows_forecast.csv=21; forecast.csv_last_date=2026-12-09; forecast.csv_last_close=9.2404 | [run](https://github.com/moos-labs/kronos-runner/actions/runs/43259528365) |
| financedatabase | data | ok | count=11; method=show_options(selection=...); rows_egypt_equities.csv=50; rows_us_sector_equities.csv=50 | [run](https://github.com/moos-labs/financedatabase-runner/actions/runs/43259743169) |
| news-disclosure | news | ok | ticker=POUL.CA; fetched_at=2026-11-12T16:34:43Z; tool=news-disclosure; news_count=40; disclosure_count=7 | [run](https://github.com/moos-labs/news-disclosure-runner/actions/runs/43259897722) |

_Verdicts are each tool's own, preserved as reported — Borsagator never averages them into one score._

---

## 🎯 Ensemble forecast (synthesizer v1)

Base price 10.2 (pandas-ta). News risk: **shock** — shock headline(s): «القاهرة للدواجن» تحقق أرباحًا بقيمة 1.43 مليار جنيه خلال 9 أشهر بتراجع 39.1% - شبكة تواصل; shock headline(s): رغم ارتفاع الإيرادات.. أرباح القاهرة للدواجن تهبط 39% بأول 9 شهور من 2026 - https://www.yo; shock headline(s): القاهرة للدواجن تسجل 1.43 مليار جنيه أرباحًا خلال 9 أشهر - عالم المال.
Confidence is provisional (uncalibrated) until the scoring ledger has history.

| Horizon | Direction | Expected | Range | Confidence |
|---|---|---|---|---|
| day | ➡ flat | +0.53% | -5.00% … +6.07% | 0.30 |
| week | ➡ flat | -0.40% | -5.97% … +5.17% | 0.30 |
| month | ⬇ down | -5.98% | -10.85% … -1.11% | 0.30 |

Family scores (−1…+1): price-forecast -0.75, technicals +0.30, sentiment +0.76, agent —, fundamentals —.
Verdicts are combined by family, weighted by horizon; disagreement widens the range instead of being averaged away.
