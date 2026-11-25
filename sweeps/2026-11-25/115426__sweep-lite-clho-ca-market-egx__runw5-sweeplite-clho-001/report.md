# Borsagator report — CLHO.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite CLHO.CA market=EGX · shape: sweep-lite CLHO.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/115426__sweep-lite-clho-ca-market-egx__runw5-sweeplite-clho-001 · archive commit: bdbeb979f0d0acb8cbaf6af4f821b1743acb85bd

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 13.38
Model range high at 15.11
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: technicals +0.45 vs sentiment -0.36 (spread +0.81)
- price-forecast: -0.33
- technicals: +0.45
- sentiment: -0.36
- fundamentals: -0.35
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.068, technicals ×0.679
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.23% (range -3.24% … +3.71%, confidence 0.45)
- week: flat -0.64% (range -6.68% … +5.39%, confidence 0.45)
- month: down -3.76% (range -16.46% … +8.94%, confidence 0.45)
Base price: 14.34 (egx-data/egxpy_clho.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_clho.csv: 14.34 on 2026-11-25
- openbb/CLHO_CA.csv: 14.13 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 14.13 on 2026-11-24 (stale)
- talib/indicators.csv: 14.13 on 2026-11-24 (stale)
- yahooquery/CLHO.CA.csv: 14.13 on 2026-11-23 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: CLHO.CA.csv_last_close, CLHO.CA.csv_last_date, rows_CLHO.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: CLHO_CA.csv_last_close, CLHO_CA.csv_last_date, rows_CLHO_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_clho.csv_last_close, egxpy_clho.csv_last_date, rows_egxpy_clho.csv, symbol, ticker
# EGX data sources for CLHO — verdict

No POUL reference material applies to CLHO; the series below is reported as fetched.

## egxpy — ok
- Rows: 2575 · Range: 2016-04-14 → 2026-11-25
- Latest: 2026-11-25 close 14.34

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — CLHO.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2461 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 14.13 |
| High | 14.13 |
| Low | 14.13 |
| Close | 14.13 |
| RSI(14) | 49.6905 |
| MACD | -0.0873 |
| MACD signal | -0.1686 |
| MACD histogram | 0.0813 |
| EMA(20) | 14.0572 |
| EMA(50) | 14.5713 |
| EMA(200) | 14.478 |
| ADX(14) | 25.6758 |
| Bollinger upper | 14.8007 |
| Bollinger mid | 13.892 |
| Bollinger lower | 12.9833 |
| Bollinger %B | 0.6309 |
| ATR(14) | 0.5465 |
| Stochastic %K | 51.3863 |
| Stochastic %D | 50.1195 |

## Trend read (facts only)

- Close 14.13 is above EMA_20 14.0572 (+0.52%).
- Close 14.13 is below EMA_50 14.5713 (-3.03%).
- Close 14.13 is below EMA_200 14.478 (-2.40%).
- RSI(14) is 49.6905, in the neutral zone (30-70).
- MACD -0.0873 is above its signal line -0.1686 (histogram 0.0813).
- Price sits at %B 0.6309 of the Bollinger range (lower 12.9833, mid 13.892, upper 14.8007).
- ADX(14) is 25.6758, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 51.3863 is above %D 50.1195.
- ATR(14) is 0.5465 (3.87% of the close).

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
# Fundamentals (generic) — CLHO.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T11:51:01.504678+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 1449000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 14.130000114440918.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 7227.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 669.82, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 39.55, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 20.62, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 9.27, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 16.58, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 6.54, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.91

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 1
- Label counts: positive=0, negative=0, neutral=1
- Mean probabilities: positive=0.0182, negative=0.3017, neutral=0.6801

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0182 | 0.3017 | 0.6801 | Cleopatra Hospitals stock flags delay in financial statements - ad-hoc-news.de |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 1
- Label counts: positive=0, negative=0, neutral=1
- Mean probabilities: positive=0.0000, negative=0.0599, neutral=0.9400

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0599 | 0.9400 | Cleopatra Hospitals stock flags delay in financial statements - ad-hoc-news.de |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 1
- Label counts: positive=0, negative=1, neutral=0
- Mean probabilities: positive=0.0002, negative=0.9985, neutral=0.0012

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | negative | negative | 0.0002 | 0.9985 | 0.0012 | Cleopatra Hospitals stock flags delay in financial statements - ad-hoc-news.de |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — CLHO.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 14.130000114440918 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 14.3755
- 2026-11-25: 14.3244
- 2026-11-26: 14.2007
- 2026-11-29: 14.1506
- 2026-11-30: 14.2034
- 2026-12-01: 14.155
- 2026-12-02: 14.2201
- 2026-12-03: 14.0179
- 2026-12-06: 14.1498
- 2026-12-07: 14.0775
- 2026-12-08: 14.0991
- 2026-12-09: 14.0328
- 2026-12-10: 13.9985
- 2026-12-13: 13.8391
- 2026-12-14: 13.8747
- 2026-12-15: 13.7565
- 2026-12-16: 13.8243
- 2026-12-17: 13.7302
- 2026-12-20: 13.5873
- 2026-12-21: 13.5906
- 2026-12-22: 13.6514

**Change over the 21 sessions (last forecasted close vs last actual close): -3.39%**

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
News: 30 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- علي جمعة: من أيقن أن الوجود كله لله لم ير نفسه مالكا متسلطا بل عبدا مستخلفا - صدى البلد
- «المحل كله قدامك خذ اللي أنت عايزه».. عراقي يفاجئ مصريًا بطلب الطعام ويجسد كرم أهل العراق - موقع بصراحة الإخباري
- الخطيب في وداع المطران خضر: خسارته للبنان كلّه وندعو إلى وحدة اللبنانيين - الديار
- لنشد عضدنا بجيشنا ؛ فالعالم كله خطر ..! - أفريكا نيوز
- Cleopatra Hospitals stock flags delay in financial statements - ad-hoc-news.de
- رحلات الخطوط التركية إلى خمس وجهات تتراجع.. والبلقان ليس كله سواء - تركيا عاجل
- عمرو الليثي: ضياع الأمانة ضياع للمجتمع كله.. وعزة النفس أخت شقيقة للأمانة - موقع بصراحة الإخباري
- لبنان كلّه بفستان... إطلالة بيرلا تحمل رسالة - Lebanon Debate
- من أضاع لغته أضاع مفتاح بيته وإن ملك مفاتيح العالم كله - جريدة الشرق
- صوته كله خشوع وشجن.. برنامج دولة التلاوة يحتفي بالشيخ محمد ساعى نصر الجرزاوى - اليوم السابع
- "كله متصور".. مرتضى منصور يرد على نفي حسام حسن تسليم صور طليقته - خبرني - ننقل لك أخبار الأردن والعالم بموثوقية وتميّز
- إلهام شاهين: مهرجان القاهرة السينمائي «عمري كله».. يجمع عشقي للسينما ومصر - دار المعارف
- إلهام شاهين: قضيت عمري كله في السينما.. وأتمنى تقديم عمل تاريخي عن الملكة حتشبسوت - بوابة الشروق
- كانت بتعزم الكاست كله.. رانيا فريد شوقي تستعيد أجمل ذكرياتها مع خيرية أحمد في ذكرى رحيلها - elmaser.com
- العالم كله يراهن على وول ستريت.. ماذا لو سقط السوق الأميركي؟ - العربي الجديد
- صقر واحد يغير طريق العمر كله.. متى تتحول سماء سيناء إلى منجم ذهب صور - سودان اندبندنت
- أحمد داش: العالمية الحقيقية هي توصيل فكر بلدي للعالم كله.. فيديو خاص - صدى البلد
- العالم كله يسأل أين ذهبت التبرعات التى دخلت غزة - أمد للإعلام
- «كله كان برضاهم».. دفاع صاحب «بيت فاطم» يرد على اتهامات الاتجار بالبشر وهتك عرض 4 فتيات - المصري اليوم
- وائل عبد العزيز يعلن انفصاله للمرة الثالثة: «عمري كله أنصاص مشاوير» - المصري اليوم
- حسام موافي: المرأة ليست نصف المجتمع بل المجتمع كله.. والأم صاحبة الدور الأكبر في تربية الأجيال - جريدة النهار المصرية
- رمضان عبد المعز: الخير كله بيد الله في كل أقداره - شبكة تواصل الإخبارية

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/CLHO-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.30
- finbert_positive: 0.02
- multilingual_positive: 0.43
- multilingual_negative: 0.34
- translated_positive: 0.09
- translated_negative: 0.20
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
Chart: egx-data/egxpy_clho.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_clho.csv: last 14.34 on 2026-11-25
- openbb/CLHO_CA.csv: last 14.13 on 2026-11-24
- pandas-ta/indicators.csv: last 14.13 on 2026-11-24
- talib/indicators.csv: last 14.13 on 2026-11-24
- yahooquery/CLHO.CA.csv: last 14.13 on 2026-11-23
- Kronos forecast: 21 points, last 13.65 at 2026-12-22

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 53 · forecasts: 90 · matured: 45 · pending: 36 · invalid: 9
No accuracy figure is published until n ≥ 30 matured forecasts (n = 45).

## Data-quality flags

## Data-quality flags
- summary-format-diff: news-disclosure (parsed-identical, bytes differ from the canonical indent=2 form)
- witnesses-stale: common_date 2026-11-23 vs base_date 2026-11-25
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/CLHO.CA.recommendation.json
- reaction-profile-missing: no profiles/CLHO.CA.json
- sharia-row-missing: AAOIFI CLHO.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 CLHO.CA
- sharia-row-missing: FTSE CLHO.CA
- sharia-row-missing: ISLAMICLY CLHO.CA
- sharia-row-missing: MSCI CLHO.CA
- sharia-row-missing: MSCI_M CLHO.CA
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