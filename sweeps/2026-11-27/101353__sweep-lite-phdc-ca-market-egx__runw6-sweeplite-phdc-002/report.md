# Borsagator report — PHDC.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite PHDC.CA market=EGX · shape: sweep-lite PHDC.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/101353__sweep-lite-phdc-ca-market-egx__runw6-sweeplite-phdc-002 · archive commit: b68de6ec7798a8eff5b10e8431ddc1ab02b77be5

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 10.51
Model range high at 12.17
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs price-forecast +0.07 (spread +0.33)
- price-forecast: +0.07
- technicals: +0.30
- sentiment: +0.36
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -2.92% … +2.92%, confidence 0.60)
- week: flat +0.00% (range -7.28% … +7.28%, confidence 0.60)
- month: flat +0.00% (range -13.98% … +13.98%, confidence 0.60)
Base price: 11.34 (egx-data/egxpy_phdc.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-25, base date 2026-11-26)
Witnesses stale: common date 2026-11-25 trails base date 2026-11-26.
- egx-data/egxpy_phdc.csv: 11.34 on 2026-11-26
- openbb/PHDC_CA.csv: 11.34 on 2026-11-26
- pandas-ta/indicators.csv: 11.34 on 2026-11-26
- talib/indicators.csv: 11.34 on 2026-11-26
- yahooquery/PHDC.CA.csv: 11.35 on 2026-11-25 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: PHDC.CA.csv_last_close, PHDC.CA.csv_last_date, rows_PHDC.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: PHDC_CA.csv_last_close, PHDC_CA.csv_last_date, rows_PHDC_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_phdc.csv_last_close, egxpy_phdc.csv_last_date, rows_egxpy_phdc.csv, symbol, ticker
# EGX data sources for PHDC — verdict

No POUL reference material applies to PHDC; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-22 → 2026-11-26
- Latest: 2026-11-26 close 11.34

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — PHDC.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 4591 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 11.35 |
| High | 11.5 |
| Low | 11.23 |
| Close | 11.34 |
| RSI(14) | 42.5895 |
| MACD | -0.2667 |
| MACD signal | -0.2823 |
| MACD histogram | 0.0156 |
| EMA(20) | 11.6838 |
| EMA(50) | 12.3274 |
| EMA(200) | 12.2063 |
| ADX(14) | 25.4036 |
| Bollinger upper | 12.5217 |
| Bollinger mid | 11.5555 |
| Bollinger lower | 10.5893 |
| Bollinger %B | 0.3885 |
| ATR(14) | 0.5389 |
| Stochastic %K | 29.4807 |
| Stochastic %D | 33.7883 |

## Trend read (facts only)

- Close 11.34 is below EMA_20 11.6838 (-2.94%).
- Close 11.34 is below EMA_50 12.3274 (-8.01%).
- Close 11.34 is below EMA_200 12.2063 (-7.10%).
- RSI(14) is 42.5895, in the neutral zone (30-70).
- MACD -0.2667 is above its signal line -0.2823 (histogram 0.0156).
- Price sits at %B 0.3885 of the Bollinger range (lower 10.5893, mid 11.5555, upper 12.5217).
- ADX(14) is 25.4036, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 29.4807 is below %D 33.7883.
- ATR(14) is 0.5389 (4.75% of the close).

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
# Fundamentals (generic) — PHDC.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T10:11:46.515084+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 2848000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 11.34000015258789.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 36169.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 4217.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 41.16, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 22.45, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 11.66, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 22.47, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 2.45, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 1.

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 8
- Label counts: positive=6, negative=0, neutral=2
- Mean probabilities: positive=0.6066, negative=0.0098, neutral=0.3835

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | positive | 0.5526 | 0.0096 | 0.4378 | President Mahama hails PHDC’s $28billion partnership for Phase 2 of Petroleum Hub Project - Graphic Online |
| 2 | positive | 0.8432 | 0.0088 | 0.1480 | PHDC signs $28 billion deal for second phase of Ghana's Petroleum Hub - GhanaWeb |
| 3 | positive | 0.6697 | 0.0093 | 0.3210 | Ghana’s PHDC advancing Phase 2 of multibillion-dollar downstream petroleum hub - Oil & Gas Journal |
| 4 | positive | 0.7785 | 0.0082 | 0.2134 | PHDC signs BOO deal to develop $28-B petroleum hub in Ghana - Hydrocarbon Processing |
| 5 | neutral | 0.2507 | 0.0122 | 0.7371 | PHDC signs US$28bn deal for Jomoro petroleum hub - Business & Financial Times |
| 6 | positive | 0.7734 | 0.0098 | 0.2168 | Energy Ministry woos investors as PHDC signs Global Sphere deal for Petroleum Hub Phase Two - MyJoyOnline |
| 7 | positive | 0.7080 | 0.0085 | 0.2834 | PHDC signs $28bn deal for second phase of Ghana’s Petroleum Hub - CitiNewsroom.com |
| 8 | neutral | 0.2769 | 0.0123 | 0.7108 | Build connections with renters and buyers at the 2026 PHDC annual housing fair - City of Philadelphia (.gov) |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 8
- Label counts: positive=0, negative=0, neutral=8
- Mean probabilities: positive=0.0041, negative=0.0000, neutral=0.9959

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | President Mahama hails PHDC’s $28billion partnership for Phase 2 of Petroleum Hub Project - Graphic Online |
| 2 | neutral | Neutral | 0.0004 | 0.0000 | 0.9996 | PHDC signs $28 billion deal for second phase of Ghana's Petroleum Hub - GhanaWeb |
| 3 | neutral | Neutral | 0.0322 | 0.0000 | 0.9678 | Ghana’s PHDC advancing Phase 2 of multibillion-dollar downstream petroleum hub - Oil & Gas Journal |
| 4 | neutral | Neutral | 0.0003 | 0.0000 | 0.9997 | PHDC signs BOO deal to develop $28-B petroleum hub in Ghana - Hydrocarbon Processing |
| 5 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | PHDC signs US$28bn deal for Jomoro petroleum hub - Business & Financial Times |
| 6 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | Energy Ministry woos investors as PHDC signs Global Sphere deal for Petroleum Hub Phase Two - MyJoyOnline |
| 7 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | PHDC signs $28bn deal for second phase of Ghana’s Petroleum Hub - CitiNewsroom.com |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Build connections with renters and buyers at the 2026 PHDC annual housing fair - City of Philadelphia (.gov) |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 8
- Label counts: positive=8, negative=0, neutral=0
- Mean probabilities: positive=0.9976, negative=0.0005, neutral=0.0019

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9975 | 0.0004 | 0.0021 | President Mahama hails PHDC’s $28billion partnership for Phase 2 of Petroleum Hub Project - Graphic Online |
| 2 | positive | positive | 0.9980 | 0.0005 | 0.0015 | PHDC signs $28 billion deal for second phase of Ghana's Petroleum Hub - GhanaWeb |
| 3 | positive | positive | 0.9980 | 0.0005 | 0.0015 | Ghana’s PHDC advancing Phase 2 of multibillion-dollar downstream petroleum hub - Oil & Gas Journal |
| 4 | positive | positive | 0.9981 | 0.0006 | 0.0014 | PHDC signs BOO deal to develop $28-B petroleum hub in Ghana - Hydrocarbon Processing |
| 5 | positive | positive | 0.9978 | 0.0005 | 0.0017 | PHDC signs US$28bn deal for Jomoro petroleum hub - Business & Financial Times |
| 6 | positive | positive | 0.9981 | 0.0006 | 0.0013 | Energy Ministry woos investors as PHDC signs Global Sphere deal for Petroleum Hub Phase Two - MyJoyOnline |
| 7 | positive | positive | 0.9980 | 0.0005 | 0.0015 | PHDC signs $28bn deal for second phase of Ghana’s Petroleum Hub - CitiNewsroom.com |
| 8 | positive | positive | 0.9956 | 0.0002 | 0.0042 | Build connections with renters and buyers at the 2026 PHDC annual housing fair - City of Philadelphia (.gov) |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — PHDC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 11.350000381469727 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 11.4008
- 2026-11-29: 11.4034
- 2026-11-30: 11.3539
- 2026-12-01: 11.5442
- 2026-12-02: 11.5167
- 2026-12-03: 11.5377
- 2026-12-06: 11.5422
- 2026-12-07: 11.5386
- 2026-12-08: 11.5741
- 2026-12-09: 11.541
- 2026-12-10: 11.4891
- 2026-12-13: 11.4881
- 2026-12-14: 11.4325
- 2026-12-15: 11.4376
- 2026-12-16: 11.5937
- 2026-12-17: 11.5759
- 2026-12-20: 11.4938
- 2026-12-21: 11.7096
- 2026-12-22: 11.6771
- 2026-12-23: 11.5167
- 2026-12-24: 11.5296

**Change over the 21 sessions (last forecasted close vs last actual close): +1.58%**

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
News: 6 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- خلاف أبو فدك والحميداوي يشطر الكتائب.. مفاوضو جرف الصخر “في صدمة” - شبكة 964
- الزيدي يرسل العيون بدلاً من الجنرالات.. كواليس اتفاق أبو فدك الذي غير لجنة الجرف - شبكة 964
- فدك؛ ليست مجرد أرض، بل مفتاح لإعادة قراءة شرعية الخلافة - AhlulBayt News Agency (ABNA
- خاص.. اجتماع للزيدي والعامري والفياض و"أبو فدك" لاحتواء التصعيد مع كتائب حزب الله - شفق نيوز
- وسط أزمة التصعيد مع "الكتائب".. العامري والفياض و"أبو فدك" عند الزيدي - الترا العراق
- حشد الزيدي يختلف عن حشد أبو فدك بـ20 فقرة.. ضباط الجيش يقودون ألوية “المجاهدين”؟ - شبكة 964

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/PHDC-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- multilingual_positive: 0.17
- multilingual_negative: 0.32
- translated_positive: 0.08
- translated_negative: 0.23
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: none · confidence cap: 0.60
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_phdc.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_phdc.csv: last 11.34 on 2026-11-26
- openbb/PHDC_CA.csv: last 11.34 on 2026-11-26
- pandas-ta/indicators.csv: last 11.34 on 2026-11-26
- talib/indicators.csv: last 11.34 on 2026-11-26
- yahooquery/PHDC.CA.csv: last 11.35 on 2026-11-25
- Kronos forecast: 21 points, last 11.53 at 2026-12-24

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
- recommendation-unavailable: no profiles/PHDC.CA.recommendation.json
- reaction-profile-missing: no profiles/PHDC.CA.json
- sharia-row-missing: AAOIFI PHDC.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 PHDC.CA
- sharia-row-missing: FTSE PHDC.CA
- sharia-row-missing: ISLAMICLY PHDC.CA
- sharia-row-missing: MSCI PHDC.CA
- sharia-row-missing: MSCI_M PHDC.CA
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