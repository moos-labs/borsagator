# Borsagator report — MTIE.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite MTIE.CA market=EGX · shape: sweep-lite MTIE.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/142551__sweep-lite-mtie-ca-market-egx__runw5-sweeplite-mtie-001 · archive commit: b2ca76d14b4225e85a69acd5870852fcb92872ba

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 5.95
Model range high at 7.25
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: price-forecast +0.18 vs technicals -0.20 (spread +0.38)
- price-forecast: +0.18
- technicals: -0.20
- sentiment: -0.03
- fundamentals: +0.15
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.063, technicals ×0.670
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: down -4.44% (range -12.08% … +3.19%, confidence 0.30)
- week: down -2.18% (range -11.84% … +7.48%, confidence 0.30)
- month: up +2.43% (range -17.06% … +21.92%, confidence 0.30)
Base price: 6.75 (egx-data/egxpy_mtie.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_mtie.csv: 6.75 on 2026-11-25
- openbb/MTIE_CA.csv: 6.60 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 6.60 on 2026-11-24 (stale)
- talib/indicators.csv: 6.60 on 2026-11-24 (stale)
- yahooquery/MTIE.CA.csv: 6.28 on 2026-11-23 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: MTIE.CA.csv_last_close, MTIE.CA.csv_last_date, rows_MTIE.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: MTIE_CA.csv_last_close, MTIE_CA.csv_last_date, rows_MTIE_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_mtie.csv_last_close, egxpy_mtie.csv_last_date, rows_egxpy_mtie.csv, symbol, ticker
# EGX data sources for MTIE — verdict

No POUL reference material applies to MTIE; the series below is reported as fetched.

## egxpy — ok
- Rows: 2334 · Range: 2005-04-26 → 2026-11-25
- Latest: 2026-11-25 close 6.75

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — MTIE.CA

- Last session: **2026-11-24**
- Data used: 1931 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2370 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 6.28 |
| High | 6.9 |
| Low | 6.35 |
| Close | 6.6 |
| RSI(14) | 42.431 |
| MACD | -0.2706 |
| MACD signal | -0.2462 |
| MACD histogram | -0.0244 |
| EMA(20) | 6.8569 |
| EMA(50) | 7.3753 |
| EMA(200) | 8.026 |
| ADX(14) | 25.9904 |
| Bollinger upper | 7.5252 |
| Bollinger mid | 6.8585 |
| Bollinger lower | 6.1918 |
| Bollinger %B | 0.3061 |
| ATR(14) | 0.3671 |
| Stochastic %K | 14.6497 |
| Stochastic %D | 14.6165 |

## Trend read (facts only)

- Close 6.6 is below EMA_20 6.8569 (-3.75%).
- Close 6.6 is below EMA_50 7.3753 (-10.51%).
- Close 6.6 is below EMA_200 8.026 (-17.77%).
- RSI(14) is 42.431, in the neutral zone (30-70).
- MACD -0.2706 is below its signal line -0.2462 (histogram -0.0244).
- Price sits at %B 0.3061 of the Bollinger range (lower 6.1918, mid 6.8585, upper 7.5252).
- ADX(14) is 25.9904, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 14.6497 is above %D 14.6165.
- ATR(14) is 0.3671 (5.56% of the close).

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
# Fundamentals (generic) — MTIE.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T14:22:22.845435+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 2266000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 6.599999904632568.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 21163.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 1026.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 10.23, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 6.93, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 4.85, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 20.26, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 13.03, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.0

### finbert
Status: failed · exit code: 1
Summary keys: 
No report for this tool.
### finbert-tone
Status: failed · exit code: 1
Summary keys: 
No report for this tool.
### financial-roberta
Status: failed · exit code: 1
Summary keys: 
No report for this tool.
### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — MTIE.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 6.28000020980835 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 6.3132
- 2026-11-25: 6.3862
- 2026-11-26: 6.3912
- 2026-11-29: 6.4692
- 2026-11-30: 6.549
- 2026-12-01: 6.5287
- 2026-12-02: 6.5714
- 2026-12-03: 6.552
- 2026-12-06: 6.6714
- 2026-12-07: 6.6738
- 2026-12-08: 6.7049
- 2026-12-09: 6.7889
- 2026-12-10: 6.7888
- 2026-12-13: 6.8685
- 2026-12-14: 6.9505
- 2026-12-15: 6.859
- 2026-12-16: 6.8983
- 2026-12-17: 6.8627
- 2026-12-20: 6.9254
- 2026-12-21: 6.9598
- 2026-12-22: 6.9792

**Change over the 21 sessions (last forecasted close vs last actual close): +11.13%**

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
- finbert (sentiment): failed, exit 1
- finbert-tone (sentiment): failed, exit 1
- financial-roberta (sentiment): failed, exit 1
- kronos (forecast): ok, exit 0
- financedatabase (data): ok, exit 0
- news-disclosure (news): ok, exit 0
- {'detail': 'ERROR: no English headlines found for this ticker', 'status': 'failed', 'tool': 'finbert'}: failed
- {'detail': 'ERROR: no English headlines found for this ticker', 'status': 'failed', 'tool': 'finbert-tone'}: failed
- {'detail': 'ERROR: no English headlines found for this ticker', 'status': 'failed', 'tool': 'financial-roberta'}: failed

## News + disclosures

## News + disclosures
News: 34 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- متى يستعيد الذهب صعوده؟ خبراء يحددون مستويات التراجع - شبكة تواصل الإخبارية
- متى يزرع القمح ؟ رئيس مركز تغير المناخ يحدد الموعد الأنسب ويحذر من التبكير - اليوم السابع
- أموال القُصّر... متى يحتاج الولي إلى إذن المحكمة - السياسة
- متى نشرح لأولادنا سبب رفض طالبتهم ومتى نقول نفذ وخلاص؟.. فيديو - اليوم السابع
- متى تدخل محطة الضبعة الخدمة ومتى يبدأ سداد قرضها؟ وزير الكهرباء يجيب - جريدة المستقبل
- لجنة أهالي المخطوفين والمفقودين في لبنان: إلى متى نبقى رهينة الانتظار؟ - annahar.com
- متى ينتهي فصل الخريف 2026؟.. الموعد الفلكي - تليجراف مصر
- بعد التألق مع منتخب الناشئين.. متى ينتهى عقد أحمد صفوت مع الزمالك؟ - اليوم السابع
- متى يحين وقت شراء الذهب مجدداً؟ BCA تجيب - Investing.com
- متى يحق للمستهلك استبدال الأجهزة المنزلية أو استرداد قيمتها؟؟.. رئيس شعبة الأجهزة الكهربائية يُجيب - شبكة تواصل الإخبارية
- بين حسابات الفلك وتقلبات الطقس.. متى يبدأ فصل الشتاء رسمياً ومتى نشعر بلسعة البرد الحقيقية؟ - شبكة تواصل الإخبارية
- متى تنتهي رحلة هبوط أسعار الذهب في مصر؟ - اليوم السابع
- أنيس متّى: فلسطين قضية إنسانية تتجاوز الانتماءات.. وتحالف إعلامي مع غزة - المركز الفلسطيني للإعلام
- اعوجاج العمود الفقري لدى كبار السن- متى يحتاج إلى تدخل جراحي؟ - الكونسلتو
- مواعيد صرف مرتبات شهر نوفمبر 2026.. متى يبدأ الصرف؟ - اليوم السابع
- الإسهال الشتوي.. متى يشير إلى مشكلة صحية خطيرة؟ (تفاصيل) - الكونسلتو
- متي يستعيد الذهب بريقه؟ - CNBC عربية
- متى تكون تذاكر الطيران أرخص في السعودية؟ - أريبيان بزنس
- خدمة "أبشر سفر للزوار".. متى تصبح إلزامية بالسعودية؟ - أريبيان بزنس
- الموسم المُر للبطاطا الحلوة.. متى تنتهى أزمة الفائض؟ - جريدة البورصة
- متى أخر موعد لاسترداد ضريبة العقارات بالسعودية؟ - أريبيان بزنس
- معركة السيطرة على الكونغرس.. متى نعرف الفائز؟ - الجزيرة نت

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/MTIE-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- multilingual_positive: 0.10
- multilingual_negative: 0.11
- translated_positive: 0.08
- translated_negative: 0.12
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- earnings event: متى يستعيد الذهب صعوده؟ خبراء يحددون مستويات التراجع - شبكة تواصل الإخبارية
- متى يستعيد الذهب صعوده؟ خبراء يحددون مستويات التراجع - شبكة تواصل الإخبارية (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_mtie.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_mtie.csv: last 6.75 on 2026-11-25
- openbb/MTIE_CA.csv: last 6.60 on 2026-11-24
- pandas-ta/indicators.csv: last 6.60 on 2026-11-24
- talib/indicators.csv: last 6.60 on 2026-11-24
- yahooquery/MTIE.CA.csv: last 6.28 on 2026-11-23
- Kronos forecast: 21 points, last 6.98 at 2026-12-22

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
- degraded: partial-fleet (absent families: sentiment)
- recommendation-unavailable: no profiles/MTIE.CA.recommendation.json
- reaction-profile-missing: no profiles/MTIE.CA.json
- sharia-row-missing: AAOIFI MTIE.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 MTIE.CA
- sharia-row-missing: FTSE MTIE.CA
- sharia-row-missing: ISLAMICLY MTIE.CA
- sharia-row-missing: MSCI MTIE.CA
- sharia-row-missing: MSCI_M MTIE.CA
- sharia-table-missing: SP_SHARIAH
- Coercion failed: {'field': 'latest_disclosure_date', 'raw_value': '', 'reason': 'unparseable date', 'tool': 'news-disclosure'}
Degraded: {'absent_families': ['sentiment'], 'absent_tools': ['finbert', 'finbert-tone', 'financial-roberta'], 'reason': 'partial-fleet'}

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