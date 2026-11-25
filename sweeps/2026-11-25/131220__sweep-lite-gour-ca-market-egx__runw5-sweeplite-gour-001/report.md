# Borsagator report — GOUR.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite GOUR.CA market=EGX · shape: sweep-lite GOUR.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001 · archive commit: dd748ceb94f6983d1eeaf998568eb0ca71618d43

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 12.40
Model range high at 14.54
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.30 vs sentiment +0.23 (spread +0.07)
- price-forecast: no data
- technicals: no data
- sentiment: +0.23
- fundamentals: +0.30
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.068, technicals ×0.679
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.42% (range -4.19% … +5.03%, confidence 0.60)
- week: flat +0.73% (range -7.25% … +8.72%, confidence 0.60)
- month: up +1.98% (range -15.50% … +19.47%, confidence 0.60)
Base price: 13.37 (egx-data/egxpy_gour.csv, 2026-11-25)
Price cross-check: single-source (common date None, base date 2026-11-25)
- egx-data/egxpy_gour.csv: 13.37 on 2026-11-25

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: 
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: 
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_gour.csv_last_close, egxpy_gour.csv_last_date, rows_egxpy_gour.csv, symbol, ticker
# EGX data sources for GOUR — verdict

No POUL reference material applies to GOUR; the series below is reported as fetched.

## egxpy — ok
- Rows: 192 · Range: 2026-02-10 → 2026-11-25
- Latest: 2026-11-25 close 13.37

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: ticker, verdict
# Technical snapshot — GOUR.CA

## Data verdict

NO DATA: GOUR.CA returned no rows from the Yahoo chart API on this runner.

### talib
Status: ok · exit code: 0
Summary keys: 
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
# Fundamentals (generic) — GOUR.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T13:10:44.041910+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 400000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: None.

Periods: TTM, FY2025, FY2024, FY2023, FY2022. Latest FY block: {"revenue_EGPm": {"value": 2878.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 189.74, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 32.88, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 9.66, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 6.59, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 69.1, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 17.85, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.776

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 3
- Label counts: positive=0, negative=0, neutral=3
- Mean probabilities: positive=0.1394, negative=0.0249, neutral=0.8357

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0520 | 0.0183 | 0.9297 | Jammu and Kashmir Bank MD to address investors at Emerging India CEO Conference - scanx.trade |
| 2 | neutral | 0.3366 | 0.0283 | 0.6351 | SpaceX stock could see massive buying on Nasdaq 100 rebalance: will SPCX rally? - Invezz |
| 3 | neutral | 0.0296 | 0.0280 | 0.9424 | Donald Ervin Gour Obituary (2026) - Bridgewater, MA - Chapman Funerals & Cremations - Bridgewater - Legacy \| Obituary |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 3
- Label counts: positive=1, negative=0, neutral=2
- Mean probabilities: positive=0.3325, negative=0.0001, neutral=0.6674

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Jammu and Kashmir Bank MD to address investors at Emerging India CEO Conference - scanx.trade |
| 2 | positive | Positive | 0.9976 | 0.0001 | 0.0023 | SpaceX stock could see massive buying on Nasdaq 100 rebalance: will SPCX rally? - Invezz |
| 3 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Donald Ervin Gour Obituary (2026) - Bridgewater, MA - Chapman Funerals & Cremations - Bridgewater - Legacy \| Obituary |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 3
- Label counts: positive=1, negative=0, neutral=2
- Mean probabilities: positive=0.3327, negative=0.0003, neutral=0.6669

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0006 | 0.0002 | 0.9992 | Jammu and Kashmir Bank MD to address investors at Emerging India CEO Conference - scanx.trade |
| 2 | positive | positive | 0.9974 | 0.0005 | 0.0021 | SpaceX stock could see massive buying on Nasdaq 100 rebalance: will SPCX rally? - Invezz |
| 3 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | Donald Ervin Gour Obituary (2026) - Bridgewater, MA - Chapman Funerals & Cremations - Bridgewater - Legacy \| Obituary |

### kronos
Status: failed · exit code: 1
Summary keys: 
No report for this tool.
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
- kronos (forecast): failed, exit 1
- financedatabase (data): ok, exit 0
- news-disclosure (news): ok, exit 0
- {'detail': 'RuntimeError: All data sources failed: yahooquery: yahooquery returned no rows \\| yahoo-chart-api: 404 Client Error: Not Found for url: https://query1.finance.yahoo.com/v8/finance/chart/GOUR.CA?period1', 'status': 'failed', 'tool': 'kronos'}: failed

## News + disclosures

## News + disclosures
News: 7 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- جوري بكر تكشف تفاصيل شخصيتها في مسلسل "حرب باردة" (خاص) - تليجراف مصر
- جوري بكر تخطف الأنظار بإطلالة جريئة مثيرة تجمع بين الذهبي والأسود (صور) - elmaser.com
- جوري بكر تعلن وفاة خالتها بكلمات مؤثرة - ايجي بودكاست
- إف سي ديلا جوري ضد دينامو تبليسي النتيجة المباشرة, المواجهات المباشرة والتشكيلات - Sofascore
- عبير صبري وجوري بكر تتعاقدان على بطولة مسلسل في سبيل الحب - القاهرة 24
- جوري قطان: “غيب ويختفي حِسك.. وإنت بداخلِي موجود” - عدن اوبزيرفر
- نجاح أم نفوذ وعلاقات؟ رسالة حادة من جوري بكر حول التكريمات - عكاظ

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/GOUR-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- multilingual_positive: 0.38
- multilingual_negative: 0.01
- translated_positive: 0.07
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
Chart: egx-data/egxpy_gour.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_gour.csv: last 13.37 on 2026-11-25

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
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- degraded: partial-fleet (absent families: price-forecast)
- recommendation-unavailable: no profiles/GOUR.CA.recommendation.json
- reaction-profile-missing: no profiles/GOUR.CA.json
- sharia-row-missing: AAOIFI GOUR.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 GOUR.CA
- sharia-row-missing: FTSE GOUR.CA
- sharia-row-missing: ISLAMICLY GOUR.CA
- sharia-row-missing: MSCI GOUR.CA
- sharia-row-missing: MSCI_M GOUR.CA
- sharia-table-missing: SP_SHARIAH
- Coercion failed: {'field': 'latest_disclosure_date', 'raw_value': '', 'reason': 'unparseable date', 'tool': 'news-disclosure'}
Degraded: {'absent_families': ['price-forecast'], 'absent_tools': ['kronos'], 'reason': 'partial-fleet'}

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