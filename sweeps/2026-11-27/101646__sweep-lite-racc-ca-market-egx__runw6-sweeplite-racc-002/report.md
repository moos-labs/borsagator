# Borsagator report — RACC.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite RACC.CA market=EGX · shape: sweep-lite RACC.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/101646__sweep-lite-racc-ca-market-egx__runw6-sweeplite-racc-002 · archive commit: c2f27f2b69d1b6124c5fc74fc29d71ccd06eab27

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 6.80
Model range high at 8.80
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs price-forecast -0.09 (spread +0.49)
- price-forecast: -0.09
- technicals: +0.15
- sentiment: +0.10
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -5.17% … +5.17%, confidence 0.30)
- week: flat +0.00% (range -12.86% … +12.86%, confidence 0.30)
- month: flat +0.00% (range -24.71% … +24.71%, confidence 0.30)
Base price: 7.80 (egx-data/egxpy_racc.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-25, base date 2026-11-26)
Witnesses stale: common date 2026-11-25 trails base date 2026-11-26.
- egx-data/egxpy_racc.csv: 7.80 on 2026-11-26
- openbb/RACC_CA.csv: 7.80 on 2026-11-26
- pandas-ta/indicators.csv: 7.80 on 2026-11-26
- talib/indicators.csv: 7.80 on 2026-11-26
- yahooquery/RACC.CA.csv: 7.51 on 2026-11-25 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: RACC.CA.csv_last_close, RACC.CA.csv_last_date, rows_RACC.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: RACC_CA.csv_last_close, RACC_CA.csv_last_date, rows_RACC_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_racc.csv_last_close, egxpy_racc.csv_last_date, rows_egxpy_racc.csv, symbol, ticker
# EGX data sources for RACC — verdict

No POUL reference material applies to RACC; the series below is reported as fetched.

## egxpy — ok
- Rows: 2326 · Range: 2015-02-12 → 2026-11-26
- Latest: 2026-11-26 close 7.8

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — RACC.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 2255 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 7.51 |
| High | 7.96 |
| Low | 7.5 |
| Close | 7.8 |
| RSI(14) | 46.2969 |
| MACD | -0.1702 |
| MACD signal | -0.1916 |
| MACD histogram | 0.0215 |
| EMA(20) | 7.8797 |
| EMA(50) | 8.3479 |
| EMA(200) | 8.9382 |
| ADX(14) | 40.9897 |
| Bollinger upper | 8.4603 |
| Bollinger mid | 7.8065 |
| Bollinger lower | 7.1527 |
| Bollinger %B | 0.495 |
| ATR(14) | 0.3916 |
| Stochastic %K | 45.7023 |
| Stochastic %D | 45.203 |

## Trend read (facts only)

- Close 7.8 is below EMA_20 7.8797 (-1.01%).
- Close 7.8 is below EMA_50 8.3479 (-6.56%).
- Close 7.8 is below EMA_200 8.9382 (-12.73%).
- RSI(14) is 46.2969, in the neutral zone (30-70).
- MACD -0.1702 is above its signal line -0.1916 (histogram 0.0215).
- Price sits at %B 0.495 of the Bollinger range (lower 7.1527, mid 7.8065, upper 8.4603).
- ADX(14) is 40.9897, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 45.7023 is above %D 45.203.
- ATR(14) is 0.3916 (5.02% of the close).

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
# Fundamentals (generic) — RACC.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T10:14:53.981381+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 205120000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 7.800000190734863.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 2877.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 269.34, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 44.28, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 16.38, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 9.36, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 23.36, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 10.99, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.6

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 4
- Label counts: positive=0, negative=0, neutral=4
- Mean probabilities: positive=0.0525, negative=0.0350, neutral=0.9125

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0239 | 0.0252 | 0.9509 | RACC: Research Alliance Corporation III filed SEC Form 8-K: Submission of Matters to a Vote of Security Holders - Quantisnow |
| 2 | neutral | 0.0370 | 0.0718 | 0.8912 | Over 3.2 million shares were put up for redemption as Research Alliance Corp III (RACC) held a deal vote. - Stock Titan |
| 3 | neutral | 0.0872 | 0.0184 | 0.8944 | RACC seeks families to foster pets for Thanksgiving - WWBT |
| 4 | neutral | 0.0619 | 0.0246 | 0.9134 | From shelter to snuggles: RACC seeks Thanksgiving foster homes for pets - WWBT |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 9
- Label counts: positive=0, negative=0, neutral=9
- Mean probabilities: positive=0.0001, negative=0.0003, neutral=0.9996

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0026 | 0.9973 | RACC: Research Alliance Corporation III filed SEC Form 8-K: Submission of Matters to a Vote of Security Holders - Quantisnow |
| 2 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | Over 3.2 million shares were put up for redemption as Research Alliance Corp III (RACC) held a deal vote. - Stock Titan |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | RACC seeks families to foster pets for Thanksgiving - WWBT |
| 4 | neutral | Neutral | 0.0003 | 0.0000 | 0.9996 | From shelter to snuggles: RACC seeks Thanksgiving foster homes for pets - WWBT |
| 5 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | RACC asks community to foster or adopt as shelter reaches capacity - WWBT |
| 6 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Portland arts leader talks about why her organization is still relevant after 30 years - The Business Journals |
| 7 | neutral | Neutral | 0.0000 | 0.0002 | 0.9998 | RACC applies for grant for pocket park improvements in Clearfield - The Progress |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | RACC Tommie Fund gets nearly $160k from license plate purchases - WWBT |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | RACC Tommie Fund running dry, shelter seeks donations: ‘Word is getting out’ - WWBT |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 4
- Label counts: positive=1, negative=0, neutral=3
- Mean probabilities: positive=0.3661, negative=0.0003, neutral=0.6337

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | RACC: Research Alliance Corporation III filed SEC Form 8-K: Submission of Matters to a Vote of Security Holders - Quantisnow |
| 2 | neutral | neutral | 0.0011 | 0.0002 | 0.9987 | Over 3.2 million shares were put up for redemption as Research Alliance Corp III (RACC) held a deal vote. - Stock Titan |
| 3 | positive | positive | 0.9949 | 0.0003 | 0.0048 | RACC seeks families to foster pets for Thanksgiving - WWBT |
| 4 | neutral | neutral | 0.4678 | 0.0003 | 0.5318 | From shelter to snuggles: RACC seeks Thanksgiving foster homes for pets - WWBT |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — RACC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 7.510000228881836 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 7.5589
- 2026-11-29: 7.5769
- 2026-11-30: 7.4901
- 2026-12-01: 7.679
- 2026-12-02: 7.6022
- 2026-12-03: 7.6661
- 2026-12-06: 7.6993
- 2026-12-07: 7.6428
- 2026-12-08: 7.5669
- 2026-12-09: 7.5865
- 2026-12-10: 7.5956
- 2026-12-13: 7.512
- 2026-12-14: 7.4805
- 2026-12-15: 7.4922
- 2026-12-16: 7.4501
- 2026-12-17: 7.474
- 2026-12-20: 7.4065
- 2026-12-21: 7.4691
- 2026-12-22: 7.5869
- 2026-12-23: 7.5857
- 2026-12-24: 7.6143

**Change over the 21 sessions (last forecasted close vs last actual close): +1.39%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.

### financedatabase
Status: ok · exit code: 0
Summary keys: count, method, rows_egypt_equities.csv, rows_us_sector_equities.csv
No report for this tool.
### news-disclosure
Status: ok · exit code: 0
Summary keys: arabic_headlines, bodies_fetched, disclosure_count, egx_bodies_attached, egx_disclosures_added, fetched_at, finbert_negative, finbert_neutral, finbert_positive, finbert_scored, latest_disclosure_date, latest_news_date, llm_provider, multilingual_negative, multilingual_neutral, multilingual_positive, multilingual_scored, news_count, ticker, tool
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
News: 5 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- RACC: Research Alliance Corporation III filed SEC Form 8-K: Submission of Matters to a Vote of Security Holders - Quantisnow
- Over 3.2 million shares were put up for redemption as Research Alliance Corp III (RACC) held a deal vote. - Stock Titan
- شبكة “ألو راك ربحتي معانا”.. معلومات من الديستي طيحات متورط جديد كتقلب عليه الفرقة الجهوية ففاس - كود
- «حفيت وراك عشان تعملي تيتو».. أحمد السقا يرفض اعتذار هشام سليمان ويوجه له رسالة مؤثرة - شبكة تواصل الإخبارية
- استكمال الأعمال الإنشائية لمشروع راك سنترال سكوير في رأس الخيمة - البيان

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/RACC-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.05
- finbert_positive: 0.03
- multilingual_positive: 0.39
- multilingual_negative: 0.03
- translated_positive: 0.16
- translated_negative: 0.40
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- legal event: شبكة “ألو راك ربحتي معانا”.. معلومات من الديستي طيحات متورط جديد كتقلب عليه الفرقة الجهوية
- شبكة “ألو راك ربحتي معانا”.. معلومات من الديستي طيحات متورط جديد كتقلب عليه الفرقة الجهوية (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_racc.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_racc.csv: last 7.80 on 2026-11-26
- openbb/RACC_CA.csv: last 7.80 on 2026-11-26
- pandas-ta/indicators.csv: last 7.80 on 2026-11-26
- talib/indicators.csv: last 7.80 on 2026-11-26
- yahooquery/RACC.CA.csv: last 7.51 on 2026-11-25
- Kronos forecast: 21 points, last 7.61 at 2026-12-24

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 91 · forecasts: 204 · matured: 48 · pending: 144 · invalid: 12
No accuracy figure is published until n ≥ 30 matured forecasts (n = 48).

## Data-quality flags

## Data-quality flags
- witnesses-stale: common_date 2026-11-25 vs base_date 2026-11-26
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/RACC.CA.recommendation.json
- reaction-profile-missing: no profiles/RACC.CA.json
- sharia-row-missing: AAOIFI RACC.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 RACC.CA
- sharia-row-missing: FTSE RACC.CA
- sharia-row-missing: ISLAMICLY RACC.CA
- sharia-row-missing: MSCI RACC.CA
- sharia-row-missing: MSCI_M RACC.CA
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