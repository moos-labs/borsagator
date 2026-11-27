# Borsagator report — EFIH.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite EFIH.CA market=EGX · shape: sweep-lite EFIH.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/030440__sweep-lite-efih-ca-market-egx__runw6-sweeplite-efih-002 · archive commit: ae8d10d4c2a8f96ea2bd6de441fb10e437f15a9c

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 22.60
Model range high at 26.62
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: sentiment +0.69 vs fundamentals -0.35 (spread +1.04)
- price-forecast: -0.05
- technicals: +0.30
- sentiment: +0.69
- fundamentals: -0.35
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -3.27% … +3.27%, confidence 0.60)
- week: flat +0.00% (range -8.15% … +8.15%, confidence 0.60)
- month: flat +0.00% (range -15.65% … +15.65%, confidence 0.54)
Base price: 24.61 (egx-data/egxpy_efih.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-24, base date 2026-11-26)
Witnesses stale: common date 2026-11-24 trails base date 2026-11-26.
- egx-data/egxpy_efih.csv: 24.61 on 2026-11-26
- openbb/EFIH_CA.csv: 25.00 on 2026-11-25 (stale)
- pandas-ta/indicators.csv: 25.00 on 2026-11-25 (stale)
- talib/indicators.csv: 25.00 on 2026-11-25 (stale)
- yahooquery/EFIH.CA.csv: 25.29 on 2026-11-24 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: EFIH.CA.csv_last_close, EFIH.CA.csv_last_date, rows_EFIH.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: EFIH_CA.csv_last_close, EFIH_CA.csv_last_date, rows_EFIH_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_efih.csv_last_close, egxpy_efih.csv_last_date, rows_egxpy_efih.csv, symbol, ticker
# EGX data sources for EFIH — verdict

No POUL reference material applies to EFIH; the series below is reported as fetched.

## egxpy — ok
- Rows: 1239 · Range: 2021-10-19 → 2026-11-26
- Latest: 2026-11-26 close 24.61

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — EFIH.CA

- Last session: **2026-11-25**
- Data used: 1237 rows (2021-10-20 → 2026-11-25), after dropping rows before 2019-01-01; 1237 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 25.29 |
| High | 25.28 |
| Low | 24.81 |
| Close | 25.0 |
| RSI(14) | 56.9856 |
| MACD | 0.4865 |
| MACD signal | 0.416 |
| MACD histogram | 0.0705 |
| EMA(20) | 24.3626 |
| EMA(50) | 23.8188 |
| EMA(200) | 21.9566 |
| ADX(14) | 13.8215 |
| Bollinger upper | 26.1047 |
| Bollinger mid | 24.1865 |
| Bollinger lower | 22.2683 |
| Bollinger %B | 0.712 |
| ATR(14) | 0.9952 |
| Stochastic %K | 66.5926 |
| Stochastic %D | 67.1362 |

## Trend read (facts only)

- Close 25.0 is above EMA_20 24.3626 (+2.62%).
- Close 25.0 is above EMA_50 23.8188 (+4.96%).
- Close 25.0 is above EMA_200 21.9566 (+13.86%).
- RSI(14) is 56.9856, in the neutral zone (30-70).
- MACD 0.4865 is above its signal line 0.416 (histogram 0.0705).
- Price sits at %B 0.712 of the Bollinger range (lower 22.2683, mid 24.1865, upper 26.1047).
- ADX(14) is 13.8215, indicating a weak / no clear trend (< 20).
- Stochastic %K 66.5926 is below %D 67.1362.
- ATR(14) is 0.9952 (3.98% of the close).

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

Data: Yahoo chart API (direct), 2188 sessions, 2018-01-01 → 2026-11-25 (Africa/Cairo).

## (1) Daily returns from 2026-09-28 (window start 2026-09-28)

- Sessions: 41 (40 daily returns)
- Close: 9.7100 → 6.7300
- Cumulative return: -30.69%
- Sharpe: -3.0684
- Sortino: -3.3172
- Max drawdown: -34.66%
- Volatility (annualised): 67.06%
- Daily win rate: 40.0%
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
- Data: 2437 rows, 2017-01-02 → 2026-11-25 (first close 3.6559998989105225, last close 6.730000019073486)
- Attempts: POUL.CA via yf_download_ignore_tz (0 rows), POUL.CA via yf_ticker_history (0 rows), POUL.CA via yahoo_chart_api (2437 rows)

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
# Fundamentals (generic) — EFIH.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T03:01:44.099030+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 3467000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 25.0.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 6773.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 1943.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 56.02, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 37.43, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 28.69, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 22.12, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 16.32, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 1
- Label counts: positive=1, negative=0, neutral=0
- Mean probabilities: positive=0.9301, negative=0.0120, neutral=0.0579

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | positive | 0.9301 | 0.0120 | 0.0579 | EFIH: 9M net profit reached EGP2.216bn as shareholders approved the Tamweely acquisition - TradingView |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 1
- Label counts: positive=1, negative=0, neutral=0
- Mean probabilities: positive=0.9997, negative=0.0000, neutral=0.0003

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | Positive | 0.9997 | 0.0000 | 0.0003 | EFIH: 9M net profit reached EGP2.216bn as shareholders approved the Tamweely acquisition - TradingView |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 1
- Label counts: positive=1, negative=0, neutral=0
- Mean probabilities: positive=0.9980, negative=0.0008, neutral=0.0012

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9980 | 0.0008 | 0.0012 | EFIH: 9M net profit reached EGP2.216bn as shareholders approved the Tamweely acquisition - TradingView |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — EFIH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 25.290000915527344 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 25.3966
- 2026-11-26: 25.1327
- 2026-11-29: 24.9512
- 2026-11-30: 24.9885
- 2026-12-01: 25.0631
- 2026-12-02: 25.0038
- 2026-12-03: 25.0184
- 2026-12-06: 24.9469
- 2026-12-07: 24.8605
- 2026-12-08: 24.8104
- 2026-12-09: 24.7791
- 2026-12-10: 24.7651
- 2026-12-13: 24.5908
- 2026-12-14: 24.3064
- 2026-12-15: 24.4664
- 2026-12-16: 24.4569
- 2026-12-17: 24.4213
- 2026-12-20: 24.4112
- 2026-12-21: 24.1746
- 2026-12-22: 24.3691
- 2026-12-23: 24.2893

**Change over the 21 sessions (last forecasted close vs last actual close): -3.96%**

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
News: 3 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- جوَّك | كيف تترجم الإفيه المصري إلى لغات أخرى دون أن يفقد طرافته؟ - بقلم جوَّك آداب - جوَّك
- نادر صلاح الدين: كوميديا الموقف أصعب من الإفيه، ولكل نجم مدرسته الخاصة في صناعة الضحك - فيتو
- أشرف عبدالباقي يكشف آليات الإفيه الكوميدي ويتحدث عن مسرح مصر - جريدة المال

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/EFIH-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- multilingual_positive: 0.04
- multilingual_negative: 0.21
- translated_positive: 0.04
- translated_negative: 0.16
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
Chart: egx-data/egxpy_efih.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_efih.csv: last 24.61 on 2026-11-26
- openbb/EFIH_CA.csv: last 25.00 on 2026-11-25
- pandas-ta/indicators.csv: last 25.00 on 2026-11-25
- talib/indicators.csv: last 25.00 on 2026-11-25
- yahooquery/EFIH.CA.csv: last 25.29 on 2026-11-24
- Kronos forecast: 21 points, last 24.29 at 2026-12-23

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
- witnesses-stale: common_date 2026-11-24 vs base_date 2026-11-26
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/EFIH.CA.recommendation.json
- reaction-profile-missing: no profiles/EFIH.CA.json
- sharia-row-missing: AAOIFI EFIH.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 EFIH.CA
- sharia-row-missing: FTSE EFIH.CA
- sharia-row-missing: ISLAMICLY EFIH.CA
- sharia-row-missing: MSCI EFIH.CA
- sharia-row-missing: MSCI_M EFIH.CA
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