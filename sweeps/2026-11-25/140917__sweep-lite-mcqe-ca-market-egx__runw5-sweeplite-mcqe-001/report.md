# Borsagator report — MCQE.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite MCQE.CA market=EGX · shape: sweep-lite MCQE.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/140917__sweep-lite-mcqe-ca-market-egx__runw5-sweeplite-mcqe-001 · archive commit: d42feb5f6982f10719b8bc75910681ab50048ae2

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 155.87
Model range high at 195.38
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.15 vs price-forecast -0.10 (spread +0.25)
- price-forecast: -0.10
- technicals: +0.15
- sentiment: +0.14
- fundamentals: +0.15
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.063, technicals ×0.670
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: up +0.84% (range -5.59% … +7.28%, confidence 0.45)
- week: up +0.75% (range -10.58% … +12.09%, confidence 0.45)
- month: down -1.09% (range -26.24% … +24.06%, confidence 0.45)
Base price: 174.31 (egx-data/egxpy_mcqe.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_mcqe.csv: 174.31 on 2026-11-25
- openbb/MCQE_CA.csv: 175.97 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 175.97 on 2026-11-24 (stale)
- talib/indicators.csv: 175.97 on 2026-11-24 (stale)
- yahooquery/MCQE.CA.csv: 175.97 on 2026-11-23 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: MCQE.CA.csv_last_close, MCQE.CA.csv_last_date, rows_MCQE.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: MCQE_CA.csv_last_close, MCQE_CA.csv_last_date, rows_MCQE_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_mcqe.csv_last_close, egxpy_mcqe.csv_last_date, rows_egxpy_mcqe.csv, symbol, ticker
# EGX data sources for MCQE — verdict

No POUL reference material applies to MCQE; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-08 → 2026-11-25
- Latest: 2026-11-25 close 174.31

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — MCQE.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6135 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 175.97 |
| High | 175.97 |
| Low | 175.97 |
| Close | 175.97 |
| RSI(14) | 49.026 |
| MACD | -0.9594 |
| MACD signal | -1.9054 |
| MACD histogram | 0.946 |
| EMA(20) | 175.9927 |
| EMA(50) | 183.0291 |
| EMA(200) | 177.7375 |
| ADX(14) | 13.0127 |
| Bollinger upper | 189.6831 |
| Bollinger mid | 173.5975 |
| Bollinger lower | 157.5119 |
| Bollinger %B | 0.5737 |
| ATR(14) | 9.829 |
| Stochastic %K | 29.7549 |
| Stochastic %D | 33.3858 |

## Trend read (facts only)

- Close 175.97 is below EMA_20 175.9927 (-0.01%).
- Close 175.97 is below EMA_50 183.0291 (-3.86%).
- Close 175.97 is below EMA_200 177.7375 (-0.99%).
- RSI(14) is 49.026, in the neutral zone (30-70).
- MACD -0.9594 is above its signal line -1.9054 (histogram 0.946).
- Price sits at %B 0.5737 of the Bollinger range (lower 157.5119, mid 173.5975, upper 189.6831).
- ADX(14) is 13.0127, indicating a weak / no clear trend (< 20).
- Stochastic %K 29.7549 is below %D 33.3858.
- ATR(14) is 9.829 (5.59% of the close).

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

Data: Yahoo chart API (direct), 2187 sessions, 2018-01-01 → 2026-11-24 (Africa/Cairo).

## (1) Daily returns from 2026-09-28 (window start 2026-09-28)

- Sessions: 40 (39 daily returns)
- Close: 9.7100 → 7.1000
- Cumulative return: -26.88%
- Sharpe: -2.6488
- Sortino: -2.8884
- Max drawdown: -31.75%
- Volatility (annualised): 66.97%
- Daily win rate: 41.0%
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
- Data: 2436 rows, 2017-01-02 → 2026-11-24 (first close 3.6559998989105225, last close 7.099999904632568)
- Attempts: POUL.CA via yf_download_ignore_tz (0 rows), POUL.CA via yf_ticker_history (0 rows), POUL.CA via yahoo_chart_api (2436 rows)

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
# Fundamentals (generic) — MCQE.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T14:05:55.722936+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 96000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 175.97000122070312.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 9545.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 2033.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 38.92, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 34.34, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 21.3, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 44.42, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 26.35, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.0

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 16
- Label counts: positive=1, negative=1, neutral=14
- Mean probabilities: positive=0.1617, negative=0.0827, neutral=0.7557

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0367 | 0.0288 | 0.9344 | McQueen Girls JV Basketball @ Lassen - MaxPreps |
| 2 | neutral | 0.0321 | 0.0889 | 0.8790 | Caputo named Fort Erie CAO days after McQueen firing - Fort Erie Radio |
| 3 | neutral | 0.0240 | 0.0585 | 0.9175 | Steve McQueen \| Biography, Films, & Facts - Britannica |
| 4 | neutral | 0.0344 | 0.0295 | 0.9361 | Nadena McQueen Obituary (1946 - 2026) - Porterville, CA - The Porterville Recorder - Legacy obituary |
| 5 | neutral | 0.3838 | 0.0261 | 0.5901 | McQueen calls for unity after fourth mayoral victory in Grey Highlands - CollingwoodToday.ca |
| 6 | neutral | 0.0338 | 0.0407 | 0.9255 | Ducks call up McQueen for NHL debut, Poehling out 6-8 weeks, Gauthier day-to-day - Sportsnet.ca |
| 7 | neutral | 0.0373 | 0.0255 | 0.9371 | ALEXANDER MCQUEEN \| SPRING SUMMER 2023 SHOW - Flaunt Magazine |
| 8 | neutral | 0.0318 | 0.0730 | 0.8952 | 'Vampire Diaries' Star Steven R. McQueen Looks Unrecognizable as He Says He's Heading Back to the Gym: Photo - Yahoo Lifestyle Canada |
| 9 | neutral | 0.1626 | 0.0138 | 0.8236 | Oakland gets a sports pub from soul-food chef Michele McQueen - East Bay Times |
| 10 | neutral | 0.2299 | 0.0363 | 0.7338 | Cambridge driver clocked at 146 km/hr on McQueen Shaver - CityNews Kitchener |
| 11 | negative | 0.0226 | 0.6596 | 0.3178 | Cambridge resident charged with stunt driving on McQueen Shaver Boulevard - CambridgeToday.ca |
| 12 | neutral | 0.0583 | 0.0231 | 0.9187 | Steve McQueen Ferrari NART Spyder heads Gooding Christie’s inaugural New York sale - Magneto magazine |
| 13 | neutral | 0.3597 | 0.0790 | 0.5612 | Heads or tails, Canada can still “win” this trade war - Substack |
| 14 | neutral | 0.0600 | 0.0990 | 0.8410 | Mark McQueen: There are only 2 ways to win this trade war, and both of them suck. Mark Carney needs to hurry up and pick one - Toronto Star |
| 15 | neutral | 0.3938 | 0.0163 | 0.5900 | New game cafe comes to Uptown, McQueen soft opens downtown pub, and more openings - The Oaklandside |
| 16 | positive | 0.6857 | 0.0249 | 0.2894 | McQueen, Reno, Damonte, Fallon roll to wins; Reed gets past Galena - Reno Gazette Journal |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 8
- Label counts: positive=0, negative=0, neutral=8
- Mean probabilities: positive=0.0000, negative=0.0001, neutral=0.9999

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Caputo named Fort Erie CAO days after McQueen firing - Fort Erie Radio |
| 2 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Fort Erie CAO Chris McQueen leaves Town position - Fort Erie Observer |
| 3 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Steve McQueen \| Biography, Films, & Facts - Britannica |
| 4 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Lassen vs McQueen - Girls Junior Varsity Basketball 11/30/2026 \| Watch Live & On Demand - NFHS Network |
| 5 | neutral | Neutral | 0.0000 | 0.0000 | 0.9999 | How Gen X is reshaping 55-plus living in California - Orange County Register |
| 6 | neutral | Neutral | 0.0000 | 0.0004 | 0.9996 | Ducks’ McQueen drops gloves with Canucks’ Quillan after big hit on Mintyukov - Sportsnet.ca |
| 7 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Nadena McQueen Obituary (1946 - 2026) - Porterville, CA - The Porterville Recorder - Legacy obituary |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 0.9999 | McQueen calls for unity after fourth mayoral victory in Grey Highlands - CollingwoodToday.ca |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 8
- Label counts: positive=1, negative=0, neutral=7
- Mean probabilities: positive=0.1285, negative=0.0156, neutral=0.8559

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0003 | 0.0002 | 0.9994 | Caputo named Fort Erie CAO days after McQueen firing - Fort Erie Radio |
| 2 | neutral | neutral | 0.0003 | 0.0092 | 0.9905 | Fort Erie CAO Chris McQueen leaves Town position - Fort Erie Observer |
| 3 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | Steve McQueen \| Biography, Films, & Facts - Britannica |
| 4 | neutral | neutral | 0.0010 | 0.0003 | 0.9987 | Lassen vs McQueen - Girls Junior Varsity Basketball 11/30/2026 \| Watch Live & On Demand - NFHS Network |
| 5 | neutral | neutral | 0.0022 | 0.0002 | 0.9976 | How Gen X is reshaping 55-plus living in California - Orange County Register |
| 6 | neutral | neutral | 0.0503 | 0.1144 | 0.8354 | Ducks’ McQueen drops gloves with Canucks’ Quillan after big hit on Mintyukov - Sportsnet.ca |
| 7 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | Nadena McQueen Obituary (1946 - 2026) - Porterville, CA - The Porterville Recorder - Legacy obituary |
| 8 | positive | positive | 0.9734 | 0.0003 | 0.0264 | McQueen calls for unity after fourth mayoral victory in Grey Highlands - CollingwoodToday.ca |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — MCQE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 175.97000122070312 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 175.9316
- 2026-11-25: 177.4073
- 2026-11-26: 176.6281
- 2026-11-29: 176.5109
- 2026-11-30: 175.3394
- 2026-12-01: 174.7911
- 2026-12-02: 174.1065
- 2026-12-03: 173.3029
- 2026-12-06: 175.3802
- 2026-12-07: 176.278
- 2026-12-08: 175.4835
- 2026-12-09: 174.4444
- 2026-12-10: 175.4248
- 2026-12-13: 175.2744
- 2026-12-14: 175.9485
- 2026-12-15: 172.4952
- 2026-12-16: 172.7054
- 2026-12-17: 172.4633
- 2026-12-20: 170.1692
- 2026-12-21: 168.9292
- 2026-12-22: 169.0974

**Change over the 21 sessions (last forecasted close vs last actual close): -3.91%**

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
News: 28 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- معالج أقوى وذاكرة أكبر.. "أبل" تقترب من إطلاق "ماك بوك نيو 2" - إرم نيوز
- استعاد بريقه ومكانته.. هل يتحرك ليفربول لحسم تمديد عقد ماك أليستر؟ - يلاكورة
- جوجل تتيح لتطبيق جيميناي تشغيل جهاز كمبيوتر ماك بدلا من المستخدم - شبكة تواصل الإخبارية
- ملفات خفية تستهلك مساحة جهاز ماك.. خطوات يسيرة لاستعادتها - الجزيرة نت
- الإطلاق 2027.. آبل تطور ذكاء اصطناعي يتحكم في أجهزة ماك بدلاً من المستخدم - اليوم السابع
- ليفربول يتحرك لتحصين ماك أليستر - يلاكورة
- بين التجديد والبيع.. 3 خيارات أمام ليفربول لحسم مستقبل ماك أليستر - يلاكورة
- خاص | والد ماك أليستر يعلن لأول مرة موعد بدء مفاوضات التجديد - winwin
- Perplexity تتيح ميزة وكلاء الذكاء الاصطناعى "Teammates" على أجهزة ماك - اليوم السابع
- Grok Bot على أجهزة ماك يضيف تكاملا مع تطبيقات أبل - اليوم السابع
- آبل تعيد إحياء شعار التفاحة المضىء فى ماك بوك.. ميزة قديمة تعود بخيارات جديدة - اليوم السابع
- بعد سنوات من الرفض.. «أبل» تطرح «ماك بوك برو» بشاشة لمس - الشبيبة | آخر أخبار سلطنة عمان المحلية وأخبار العالم - Shabiba
- «منصور» للسيارات تكشف موعد إنهاء أعمال إنشاء مصنع «ماك لتصنيع وسائل النقل» - المصدر
- ماك أليستر يكشف تطورات مستقبله مع ليفربول بعد أنباء رحيله إلى ريال مدريد - 365Scores
- هل تنهى آبل رفضها لشاشات اللمس فى حواسيب ماك بوك؟ - اليوم السابع
- بعد تأخر التجديد.. إيراولا يعلن موقفه من بقاء ماك أليستر في ليفربول - يلاكورة
- ماك أليستر عن انحسار المنافسة بين أرسنال والسيتي: نحن ليفربول - يلاكورة
- ماك أليستر يدخل خطط مورينيو - صحيفة الرياضية
- "أبل" تطلق أول "ماك بوك برو" بشاشة لمس بعد رفض استمر عقدين - الشرق بلومبرغ
- أبل تكشف عن أول "ماك بوك" بشاشة تعمل باللمس.. ماذا عن الأسعار؟ | التلفزيون العربي - التلفزيون العربي
- «أبل» تُطلق «ماك بوك برو» بشاشة تعمل باللمس للمرة الأولى - الشرق الأوسط
- أبل تكشف عن أول حاسوب ماك بوك برو بشاشة تعمل باللمس - الشرق للأخبار

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/MCQE-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- multilingual_positive: 0.63
- multilingual_negative: 0.04
- translated_positive: 0.22
- translated_negative: 0.07
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
Chart: egx-data/egxpy_mcqe.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_mcqe.csv: last 174.31 on 2026-11-25
- openbb/MCQE_CA.csv: last 175.97 on 2026-11-24
- pandas-ta/indicators.csv: last 175.97 on 2026-11-24
- talib/indicators.csv: last 175.97 on 2026-11-24
- yahooquery/MCQE.CA.csv: last 175.97 on 2026-11-23
- Kronos forecast: 21 points, last 169.10 at 2026-12-22

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 62 · forecasts: 117 · matured: 48 · pending: 57 · invalid: 12
No accuracy figure is published until n ≥ 30 matured forecasts (n = 48).

## Data-quality flags

## Data-quality flags
- summary-format-diff: news-disclosure (parsed-identical, bytes differ from the canonical indent=2 form)
- witnesses-stale: common_date 2026-11-23 vs base_date 2026-11-25
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/MCQE.CA.recommendation.json
- reaction-profile-missing: no profiles/MCQE.CA.json
- sharia-row-missing: AAOIFI MCQE.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 MCQE.CA
- sharia-row-missing: FTSE MCQE.CA
- sharia-row-missing: ISLAMICLY MCQE.CA
- sharia-row-missing: MSCI MCQE.CA
- sharia-row-missing: MSCI_M MCQE.CA
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