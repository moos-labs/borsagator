# Borsagator report — SAUD.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite SAUD.CA market=EGX · shape: sweep-lite SAUD.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/102356__sweep-lite-saud-ca-market-egx__runw6-sweeplite-saud-002 · archive commit: 0684bb71628b797e3f3ba756a71119d82c1cf120

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 19.94
Model range high at 23.60
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs sentiment -0.40 (spread +0.80)
- price-forecast: -0.08
- technicals: +0.15
- sentiment: -0.40
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -3.38% … +3.38%, confidence 0.45)
- week: flat +0.00% (range -8.42% … +8.42%, confidence 0.45)
- month: flat +0.00% (range -16.18% … +16.18%, confidence 0.45)
Base price: 21.77 (egx-data/egxpy_saud.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-25, base date 2026-11-26)
Witnesses stale: common date 2026-11-25 trails base date 2026-11-26.
- egx-data/egxpy_saud.csv: 21.77 on 2026-11-26
- openbb/SAUD_CA.csv: 21.77 on 2026-11-26
- pandas-ta/indicators.csv: 21.77 on 2026-11-26
- talib/indicators.csv: 21.77 on 2026-11-26
- yahooquery/SAUD.CA.csv: 21.95 on 2026-11-25 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: SAUD.CA.csv_last_close, SAUD.CA.csv_last_date, rows_SAUD.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: SAUD_CA.csv_last_close, SAUD_CA.csv_last_date, rows_SAUD_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_saud.csv_last_close, egxpy_saud.csv_last_date, rows_egxpy_saud.csv, symbol, ticker
# EGX data sources for SAUD — verdict

No POUL reference material applies to SAUD; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-06-26 → 2026-11-26
- Latest: 2026-11-26 close 21.77

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — SAUD.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 6530 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 21.95 |
| High | 22.41 |
| Low | 21.7 |
| Close | 21.77 |
| RSI(14) | 47.51 |
| MACD | 0.1907 |
| MACD signal | 0.1851 |
| MACD histogram | 0.0056 |
| EMA(20) | 22.0921 |
| EMA(50) | 22.1074 |
| EMA(200) | 20.8905 |
| ADX(14) | 16.0712 |
| Bollinger upper | 24.0559 |
| Bollinger mid | 21.821 |
| Bollinger lower | 19.5861 |
| Bollinger %B | 0.4886 |
| ATR(14) | 0.854 |
| Stochastic %K | 51.2153 |
| Stochastic %D | 60.1246 |

## Trend read (facts only)

- Close 21.77 is below EMA_20 22.0921 (-1.46%).
- Close 21.77 is below EMA_50 22.1074 (-1.53%).
- Close 21.77 is above EMA_200 20.8905 (+4.21%).
- RSI(14) is 47.51, in the neutral zone (30-70).
- MACD 0.1907 is above its signal line 0.1851 (histogram 0.0056).
- Price sits at %B 0.4886 of the Bollinger range (lower 19.5861, mid 21.821, upper 24.0559).
- ADX(14) is 16.0712, indicating a weak / no clear trend (< 20).
- Stochastic %K 51.2153 is below %D 60.1246.
- ATR(14) is 0.854 (3.92% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.

### talib
Status: ok · exit code: 0
Summary keys: drop_before, indicators.csv_last_close, indicators.csv_last_date, last_close, last_date, rows_fetched, rows_indicators.csv, rows_used, ticker
No report for this tool.
### quantstats
Status: ok · exit code: 0
Summary keys: exchange_tz, ohlc.csv_last_close, rows, rows_ohlc.csv, source, ticker
# QuantStats report — POUL.CA

Data: Yahoo chart API (direct), 2189 sessions, 2018-01-01 → 2026-11-26 (Africa/Cairo).

## (1) Daily returns from 2026-09-28 (window start 2026-09-28)

- Sessions: 42 (41 daily returns)
- Close: 9.7100 → 6.8300
- Cumulative return: -29.66%
- Sharpe: -2.8831
- Sortino: -3.1275
- Max drawdown: -34.66%
- Volatility (annualised): 66.46%
- Daily win rate: 41.5%
- Tearsheet: ok (results/tearsheet.html)

> ⚠ Short-window caveat: this window is only a few dozen sessions (post-merger trading resumption), so Sharpe/Sortino/volatility are annualised from very little data — treat them as indicative, not stable.

## (2) Dividend-capture events (recomputed from the fetched data)

| End | Ex | Div | Entry close | Ex close | Capture @ ex close | Payday close | Capture @ payday |
|---|---|---|---|---|---|---|---|
| 2019-07-14 | 2019-07-15 | 0.25 | 4.9700 | 4.7800 | +1.21% | 4.6200 | -2.01% |
| 2021-05-17 | 2021-05-18 | 0.16 | 2.9300 | 2.8400 | +2.39% | 3.1400 | +12.63% |
| 2024-10-21 | 2024-10-22 | 0.847875 | 12.2500 | 12.0100 | +4.96% | 13.1800 | +14.51% |
| 2026-04-26 | 2026-04-27 | 0.33 | 34.9100 | 35.3500 | +2.21% | 35.7500 | +3.35% |

**Ex-day close** — n=4, mean +2.69%, win rate 100%, min +1.21%, max +4.96%

**Payday close (ex+2)** — n=4, mean +7.12%, win rate 75%, min -2.01%, max +14.51%

Capture = exit close + dividend − entry (last-cum) close, as % of entry close. Note: Yahoo's raw series is not merger-adjusted; % captures are scale-consistent per event. Events whose pre-2019 segment is corrupted in Yahoo's data are excluded from this runner's default event set.

### vectorbt
Status: ok · exit code: 0
Summary keys: poul_ohlc.csv_last_close, rows_poul_ohlc.csv
# Dividend-capture study — pilot run

- Ticker used: **POUL.CA**
- Fetch strategy used: **yahoo_chart_api**
- Data: 2438 rows, 2017-01-02 → 2026-11-26 (first close 3.6559998989105225, last close 6.829999923706055)
- Attempts: POUL.CA via yf_download_ignore_tz (0 rows), POUL.CA via yf_ticker_history (0 rows), POUL.CA via yahoo_chart_api (2438 rows)

Capture = dividend − (entry close − exit price); entry = close of the last session before the ex-date.

| Event | Rights-end | Ex-date | Div | Entry session | Entry close | Ex open → capture (% ) | Ex close → capture (%) | Payday close → capture (%) |
|---|---|---|---:|---|---:|---|---|---|
| 2018 ⚠ | 2018-04-05 | 2018-04-10 | 0.25 | 2018-04-09 | 3.7120 | 3.7120 → 0.2500 (6.73%) | 3.7120 → 0.2500 (6.73%) | 3.7120 → 0.2500 (6.73%) |
| 2019 | 2019-07-14 | 2019-07-15 | 0.25 | 2019-07-14 | 4.9700 | 4.9700 → 0.2500 (5.03%) | 4.7800 → 0.0600 (1.21%) | 4.6200 → -0.1000 (-2.01%) |
| 2021 | 2021-05-17 | 2021-05-18 | 0.16 | 2021-05-17 | 2.9300 | 2.9300 → 0.1600 (5.46%) | 2.8400 → 0.0700 (2.39%) | 3.1400 → 0.3700 (12.63%) |
| 2024 | 2024-10-21 | 2024-10-22 | 0.847875 | 2024-10-21 | 12.2500 | 12.2500 → 0.8479 (6.92%) | 12.0100 → 0.6079 (4.96%) | 13.1800 → 1.7779 (14.51%) |
| Apr 2026 | 2026-04-26 | 2026-04-27 | 0.33 | 2026-04-26 | 34.9100 | 34.9100 → 0.3300 (0.95%) | 35.3500 → 0.7700 (2.21%) | 35.7500 → 1.1700 (3.35%) |

## Averages (across events with data)

| Exit | Avg capture | Avg capture % | Events |
|---|---:|---:|---:|
| ex_open | 0.3676 | 5.02% | 5 |
| ex_close | 0.3516 | 3.50% | 5 |
| payday_close | 0.6936 | 7.04% | 5 |

## vectorbt showcase — Portfolio.from_signals (entries at cum closes, exits at ex-day closes)

- Events used: 5
- Init cash: 100000.0 → final value: 92548.36
- Total return: -7.4516%
- Trade count: 5

## Notes

- Downloaded entry closes match the verified exchange closes (median ratio 1.0000); the series is on the exchange scale and no rescaling was applied.
- Prices fetched with auto_adjust=False (no dividend adjustment), which is what a capture study needs.
- No fees, slippage or taxes are modelled.
- Event 2018: Downloaded prices around this event sit on a different scale than the verified exchange closes (ratio 0.4115); that segment of the provider series appears split-adjusted and/or stale, so this row's captures are not reliable.

### financetoolkit
Status: ok · exit code: 0
Summary keys: rows_statements.csv
# Fundamentals (generic) — SAUD.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T10:20:21.812248+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 727140000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 21.770000457763672.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 8090.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 3476.0, "basis": "vendor income statement"}, "net_margin_pct": {"value": 42.97, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 22.23, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 2.38, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.273, "basis": "vendor total debt / equity"}, "ocf_margin_pct": {"value": -88.49, "basis": "operating cash flow / revenue"}, "fcf_margin_pct": {"value": -96.8, "basis": "

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 11
- Label counts: positive=1, negative=4, neutral=6
- Mean probabilities: positive=0.1108, negative=0.4040, neutral=0.4852

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | positive | 0.8227 | 0.0532 | 0.1242 | Major Saudi Conferences to Proceed, Organisers Say, Despite Deadly Airport Attack - EnergyNow |
| 2 | neutral | 0.0940 | 0.0320 | 0.8740 | Rubio makes clear that Trump's foreign policy won't change after GOP election losses - San Francisco Chronicle |
| 3 | negative | 0.0092 | 0.9439 | 0.0469 | Saudi Interceptor Stocks Run Low After Riyadh Attacks - https://houseofsaud.com/ |
| 4 | neutral | 0.0539 | 0.2284 | 0.7176 | Wife of accused spy inside powerful California tech giant fled the US — as suspect’s link to royal family revealed - New York Post |
| 5 | negative | 0.0256 | 0.9283 | 0.0461 | Saudis say Riyadh airport struck for 2nd day in a row, separate airport also attacked - CBC |
| 6 | neutral | 0.0269 | 0.0770 | 0.8961 | Canada advises no travel to Riyadh airport after Houthi attacks, embassy remains open - CityNews Toronto |
| 7 | negative | 0.0204 | 0.9149 | 0.0647 | Saudi airport passenger terminal is struck again, a day after 12 were killed - CTV News |
| 8 | negative | 0.0328 | 0.6483 | 0.3189 | Multiple fatalities reported as drones, missiles hit Saudi international airports - Insurance Business |
| 9 | neutral | 0.0279 | 0.0331 | 0.9391 | Flames, smoke at Aramco facility south of Saudi capital: AFP - Region - World - Ahram Online |
| 10 | neutral | 0.0339 | 0.4428 | 0.5232 | Delegates walk out as Israel’s Netanyahu addresses UN - CTV News |
| 11 | neutral | 0.0717 | 0.1417 | 0.7866 | 25 Years After 9/11, Questions About the FBI’s Pursuit of Saudi Suspects in the Case Have Only Grown - ProPublica |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 11
- Label counts: positive=0, negative=3, neutral=8
- Mean probabilities: positive=0.0000, negative=0.2238, neutral=0.7762

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0012 | 0.9988 | Major Saudi Conferences to Proceed, Organisers Say, Despite Deadly Airport Attack - EnergyNow |
| 2 | neutral | Neutral | 0.0001 | 0.0455 | 0.9544 | Rubio makes clear that Trump's foreign policy won't change after GOP election losses - San Francisco Chronicle |
| 3 | neutral | Neutral | 0.0000 | 0.0131 | 0.9869 | Saudi Interceptor Stocks Run Low After Riyadh Attacks - https://houseofsaud.com/ |
| 4 | neutral | Neutral | 0.0000 | 0.0011 | 0.9989 | Wife of accused spy inside powerful California tech giant fled the US — as suspect’s link to royal family revealed - New York Post |
| 5 | negative | Negative | 0.0000 | 0.8367 | 0.1633 | Saudis say Riyadh airport struck for 2nd day in a row, separate airport also attacked - CBC |
| 6 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Canada advises no travel to Riyadh airport after Houthi attacks, embassy remains open - CityNews Toronto |
| 7 | neutral | Neutral | 0.0000 | 0.0187 | 0.9813 | Saudi airport passenger terminal is struck again, a day after 12 were killed - CTV News |
| 8 | negative | Negative | 0.0000 | 0.9327 | 0.0673 | Multiple fatalities reported as drones, missiles hit Saudi international airports - Insurance Business |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Flames, smoke at Aramco facility south of Saudi capital: AFP - Region - World - Ahram Online |
| 10 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Delegates walk out as Israel’s Netanyahu addresses UN - CTV News |
| 11 | negative | Negative | 0.0001 | 0.6125 | 0.3874 | 25 Years After 9/11, Questions About the FBI’s Pursuit of Saudi Suspects in the Case Have Only Grown - ProPublica |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 11
- Label counts: positive=1, negative=8, neutral=2
- Mean probabilities: positive=0.0778, negative=0.7252, neutral=0.1970

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.8439 | 0.0005 | 0.1555 | Major Saudi Conferences to Proceed, Organisers Say, Despite Deadly Airport Attack - EnergyNow |
| 2 | neutral | neutral | 0.0037 | 0.0010 | 0.9953 | Rubio makes clear that Trump's foreign policy won't change after GOP election losses - San Francisco Chronicle |
| 3 | negative | negative | 0.0003 | 0.9988 | 0.0010 | Saudi Interceptor Stocks Run Low After Riyadh Attacks - https://houseofsaud.com/ |
| 4 | negative | negative | 0.0012 | 0.9889 | 0.0099 | Wife of accused spy inside powerful California tech giant fled the US — as suspect’s link to royal family revealed - New York Post |
| 5 | negative | negative | 0.0003 | 0.9990 | 0.0007 | Saudis say Riyadh airport struck for 2nd day in a row, separate airport also attacked - CBC |
| 6 | neutral | neutral | 0.0036 | 0.0008 | 0.9956 | Canada advises no travel to Riyadh airport after Houthi attacks, embassy remains open - CityNews Toronto |
| 7 | negative | negative | 0.0002 | 0.9989 | 0.0009 | Saudi airport passenger terminal is struck again, a day after 12 were killed - CTV News |
| 8 | negative | negative | 0.0003 | 0.9990 | 0.0007 | Multiple fatalities reported as drones, missiles hit Saudi international airports - Insurance Business |
| 9 | negative | negative | 0.0002 | 0.9986 | 0.0012 | Flames, smoke at Aramco facility south of Saudi capital: AFP - Region - World - Ahram Online |
| 10 | negative | negative | 0.0020 | 0.9953 | 0.0028 | Delegates walk out as Israel’s Netanyahu addresses UN - CTV News |
| 11 | negative | negative | 0.0003 | 0.9967 | 0.0030 | 25 Years After 9/11, Questions About the FBI’s Pursuit of Saudi Suspects in the Case Have Only Grown - ProPublica |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — SAUD.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 21.950000762939453 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 21.964
- 2026-11-29: 21.9311
- 2026-11-30: 21.8426
- 2026-12-01: 21.9274
- 2026-12-02: 21.9547
- 2026-12-03: 21.8486
- 2026-12-06: 21.8328
- 2026-12-07: 21.6702
- 2026-12-08: 21.8998
- 2026-12-09: 21.7652
- 2026-12-10: 21.4717
- 2026-12-13: 21.6697
- 2026-12-14: 21.7156
- 2026-12-15: 21.439
- 2026-12-16: 21.5911
- 2026-12-17: 21.8333
- 2026-12-20: 21.3132
- 2026-12-21: 21.2078
- 2026-12-22: 21.2945
- 2026-12-23: 21.2588
- 2026-12-24: 21.3928

**Change over the 21 sessions (last forecasted close vs last actual close): -2.54%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.

### financedatabase
Status: ok · exit code: 0
Summary keys: count, method, rows_egypt_equities.csv, rows_us_sector_equities.csv
No report for this tool.
### news-disclosure
Status: ok · exit code: 0
Summary keys: arabic_headlines, bodies_fetched, disclosure_count, egx_bodies_attached, egx_disclosures_added, fetched_at, latest_disclosure_date, latest_news_date, llm_provider, multilingual_negative, multilingual_neutral, multilingual_positive, multilingual_scored, news_count, ticker, tool, top_headline, translated_negative, translated_neutral, translated_positive
No report for this tool.
### Tool run table
- yahooquery (data): ok, exit 0
- openbb (data): ok, exit 0
- egx-data (data): ok, exit 0
- pandas-ta (technicals): ok, exit 0
- talib (technicals): ok, exit 0
- quantstats (stats): ok, exit 0
- vectorbt (backtest): ok, exit 0
- financetoolkit (fundamentals): ok, exit 0
- finbert (sentiment): ok, exit 0
- finbert-tone (sentiment): ok, exit 0
- financial-roberta (sentiment): ok, exit 0
- kronos (forecast): ok, exit 0
- financedatabase (data): ok, exit 0
- news-disclosure (news): ok, exit 0

## News + disclosures

## News + disclosures
News: 18 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- روبيو ووزير الخارجية السعودي يدينان هجمات الحوثيين ويشددان على الملاحة في هرمز - houseofsaud.com
- إنتاج أرامكو خلال 9 أشهر يتراجع 13.7% وهجمات خط الأنابيب تُبقي ينبع دون 3 ملايين برميل يومياً - houseofsaud.com
- الحوثيون يهددون جدة وموانئ المملكة على البحر الأحمر في أعقاب ضربات الحديدة - houseofsaud.com
- خام برنت يسجّل خسارته الأسبوعية الثالثة ويهبط دون 89 دولاراً للمرة الأولى منذ أغسطس - houseofsaud.com
- ولي العهد السعودي يتصل بأمير الكويت للاطمئنان على صحته بعد فحوصات طبية في الولايات المتحدة - houseofsaud.com
- أوبك+ تجتمع في 29 نوفمبر لتحديد حصص 2027 دون خطة بعد ديسمبر - houseofsaud.com
- التحالف يعترض صاروخين باليستيين حوثيين فوق جازان وحطام يسقط في الشقيق - houseofsaud.com
- التحالف يضرب 60 هدفاً في اليمن مع تقدم الحوثيين إلى مسافة 100 كم من عدن - houseofsaud.com
- الحرس الثوري الإيراني يزعم غرق ناقلة نفط عملاقة كانت تحمل أكثر من 2 مليون برميل في الخليج - houseofsaud.com
- انسحاب القوات اليمنية الجنوبية من ضباب قرب باب المندب - houseofsaud.com
- المملكة العربية السعودية ترفع تعريفات الكهرباء والمياه للعام 2027 وتُقرّ بدلاً شهرياً بقيمة 500 ريال - houseofsaud.com
- ناقلة NCC Fajr في هجوم مشتبه به قرب مضيق هرمز فيما يدّعي الحرس الثوري الإيراني إصابة سفينتين بألغام - houseofsaud.com
- الاتحاد الآسيوي يؤجل كأس آسيا 2027 في السعودية 11 شهراً - houseofsaud.com
- الحوثيون يدّعون ضربات بطائرات مسيّرة وصواريخ على مطار أبها وخميس مشيط - houseofsaud.com
- مستشار الأمن القومي السعودي العيبان يحمل رسالة محمد بن سلمان إلى شي جين بينغ بينما يدعو وانغ يي إلى تأمين مضيق هرمز - houseofsaud.com
- الولايات المتحدة تأمر موظفيها بمغادرة السعودية وسفارة الرياض تعمل بطاقم طارئ - houseofsaud.com
- الحرس الثوري الإيراني يقول إن 3 ناقلات نفط اصطدمت بألغام في مضيق هرمز - houseofsaud.com
- الحوثيون يطلقون 3 صواريخ باليستية على السعودية والرياض تسمع 8 انفجارات - houseofsaud.com

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/SAUD-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- multilingual_positive: 0.12
- multilingual_negative: 0.55
- translated_positive: 0.08
- translated_negative: 0.49
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: elevated · confidence cap: 0.45
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_saud.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_saud.csv: last 21.77 on 2026-11-26
- openbb/SAUD_CA.csv: last 21.77 on 2026-11-26
- pandas-ta/indicators.csv: last 21.77 on 2026-11-26
- talib/indicators.csv: last 21.77 on 2026-11-26
- yahooquery/SAUD.CA.csv: last 21.95 on 2026-11-25
- Kronos forecast: 21 points, last 21.39 at 2026-12-24

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 91 · forecasts: 204 · matured: 48 · pending: 144 · invalid: 12
No accuracy figure is published until n ≥ 30 matured forecasts (n = 48).

## Data-quality flags

## Data-quality flags
- summary-format-diff: news-disclosure (parsed-identical, bytes differ from the canonical indent=2 form)
- witnesses-stale: common_date 2026-11-25 vs base_date 2026-11-26
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/SAUD.CA.recommendation.json
- reaction-profile-missing: no profiles/SAUD.CA.json
- sharia-row-missing: AAOIFI SAUD.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 SAUD.CA
- sharia-row-missing: FTSE SAUD.CA
- sharia-row-missing: ISLAMICLY SAUD.CA
- sharia-row-missing: MSCI SAUD.CA
- sharia-row-missing: MSCI_M SAUD.CA
- sharia-table-missing: SP_SHARIAH
- Coercion failed: {'field': 'latest_disclosure_date', 'raw_value': '', 'reason': 'unparseable date', 'tool': 'news-disclosure'}

## Sharia screening

## Sharia screening
NOT A FATWA — screening results per the selected standard; no Sharia Board certification.
ليست فتوى — نتائج فحص وفق المعيار المختار؛ لا توجد شهادة من هيئة رقابة شرعية.
> Screening result under the named standard only, computed from the company's published financials. This is not a fatwa, and not religious or investment advice.
> نتيجة فحص وفق المعيار المذكور فقط، محسوبة من القوائم المالية المنشورة للشركة. ليست فتوى، وليست نصيحة دينية أو استثمارية.
- AAOIFI: insufficient-data
- DJIM: insufficient-data
- EGX33: insufficient-data
- FTSE: insufficient-data
- ISLAMICLY: insufficient-data
- MSCI: insufficient-data
- MSCI_M: insufficient-data
- SP_SHARIAH: insufficient-data

## Provenance

## Provenance
Provenance: merged by worker · compiler: scripts/compile_model.py · model: borsagator-report-model/2
Viewer: <unassigned>

---

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Borsagator sells a computed report, not advice and not a managed service. The report shows what a fixed set of named analysis tools computed from public market data on a stated date. No person reviews your finances, no recommendation is tailored to you, and nothing in the report is a personal recommendation to buy, sell, or hold any security. Markets move; the tools can be wrong, data can be stale or corrected, and a reported figure can be superseded. Outputs are generated by automated tools with known limitations. Accuracy is not guaranteed. Past measured accuracy does not predict future results. You pay for the computation and delivery of the report, not for any outcome. Use of this product does not create an advisory or fiduciary relationship. Do not spend money you cannot afford to lose on the basis of any report. Data sources: listed per report; data may be delayed or incomplete.

### Arabic disclaimer

بورساجاتور ليست مستشارًا استثماريًا. هذا التقرير ناتج حسابي، وليس توصية بشراء أو بيع. النتائج الحسابية محسوبة بواسطة أدوات التحليل المذكورة من بيانات عامة؛ الأداء السابق لا يتنبأ بالنتائج المستقبلية. القرار قرارك — والمخاطرة عليك. الأوراق المالية تنطوي على مخاطر خسارة. قد تخسر مالك.

بورساجاتور تبيع تقريرًا محسوبًا، لا استشارة ولا خدمة إدارة. يعرض التقرير ما حسبته مجموعة ثابتة من أدوات التحليل المذكورة من بيانات سوق عامة في تاريخ محدد. لا يراجع أي شخص وضعك المالي، ولا توجد توصية مخصصة لك، ولا شيء في التقرير توصية شخصية بشراء أو بيع أو الاحتفاظ بأي ورقة مالية. الأسواق تتحرك؛ والأدوات قد تخطئ، والبيانات قد تكون قديمة أو مصححة، والأرقام قد تُستبدل. النواتج مولّدة بأدوات آلية لها قيود معروفة. الدقة غير مضمونة. الدقة المقاسة السابقة لا تتنبأ بالنتائج المستقبلية. أنت تدفع مقابل حساب التقرير وتسليمه، لا مقابل أي نتيجة. استخدام هذا المنتج لا ينشئ علاقة استشارية أو ائتمانية. لا تنفق مالًا لا تستطيع تحمل خسارته بناءً على أي تقرير. مصادر البيانات: تُذكر في كل تقرير؛ وقد تكون البيانات متأخرة أو غير مكتملة.

_Deterministic glue over the ensemble + reaction fit — research tooling, not financial advice._

Viewer: <unassigned>