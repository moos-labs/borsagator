# Borsagator report — ORHD.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite ORHD.CA market=EGX · shape: sweep-lite ORHD.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/144735__sweep-lite-orhd-ca-market-egx__runw5-sweeplite-orhd-001 · archive commit: cfd5be79c741e24974dd987c982870f8c446ad67

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 9.28
Model range high at 11.14
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs price-forecast -0.21 (spread +0.61)
- price-forecast: -0.21
- technicals: +0.40
- sentiment: no data
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.063, technicals ×0.670
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: down -1.82% (range -7.28% … +3.63%, confidence 0.35)
- week: down -1.62% (range -10.59% … +7.35%, confidence 0.35)
- month: down -1.34% (range -20.10% … +17.41%, confidence 0.35)
Base price: 10.38 (egx-data/egxpy_orhd.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_orhd.csv: 10.38 on 2026-11-25
- openbb/ORHD_CA.csv: 9.98 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 9.98 on 2026-11-24 (stale)
- talib/indicators.csv: 9.98 on 2026-11-24 (stale)
- yahooquery/ORHD.CA.csv: 9.98 on 2026-11-23 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: ORHD.CA.csv_last_close, ORHD.CA.csv_last_date, rows_ORHD.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: ORHD_CA.csv_last_close, ORHD_CA.csv_last_date, rows_ORHD_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_orhd.csv_last_close, egxpy_orhd.csv_last_date, rows_egxpy_orhd.csv, symbol, ticker
# EGX data sources for ORHD — verdict

No POUL reference material applies to ORHD; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-06-29 → 2026-11-25
- Latest: 2026-11-25 close 10.38

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — ORHD.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 4681 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 9.98 |
| High | 9.98 |
| Low | 9.98 |
| Close | 9.98 |
| RSI(14) | 27.6204 |
| MACD | -1.4896 |
| MACD signal | -2.0659 |
| MACD histogram | 0.5763 |
| EMA(20) | 10.7688 |
| EMA(50) | 16.524 |
| EMA(200) | 26.2799 |
| ADX(14) | 56.8906 |
| Bollinger upper | 10.7645 |
| Bollinger mid | 10.114 |
| Bollinger lower | 9.4635 |
| Bollinger %B | 0.397 |
| ATR(14) | 0.5668 |
| Stochastic %K | 40.0868 |
| Stochastic %D | 52.1069 |

## Trend read (facts only)

- Close 9.98 is below EMA_20 10.7688 (-7.32%).
- Close 9.98 is below EMA_50 16.524 (-39.60%).
- Close 9.98 is below EMA_200 26.2799 (-62.02%).
- RSI(14) is 27.6204, in the oversold zone (<= 30).
- MACD -1.4896 is above its signal line -2.0659 (histogram 0.5763).
- Price sits at %B 0.397 of the Bollinger range (lower 9.4635, mid 10.114, upper 10.7645).
- ADX(14) is 56.8906, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 40.0868 is below %D 52.1069.
- ATR(14) is 0.5668 (5.68% of the close).

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
# Fundamentals (generic) — ORHD.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T14:46:26.891480+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 3650000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 9.979999542236328.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 24945.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 5550.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 31.64, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 28.29, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 22.25, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 31.46, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 9.4, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.6

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
# Kronos-small forecast — ORHD.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 9.979999542236328 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 10.0765
- 2026-11-25: 10.0602
- 2026-11-26: 10.0941
- 2026-11-29: 10.1017
- 2026-11-30: 10.0924
- 2026-12-01: 10.1536
- 2026-12-02: 10.2944
- 2026-12-03: 10.2351
- 2026-12-06: 10.2506
- 2026-12-07: 10.2053
- 2026-12-08: 10.1486
- 2026-12-09: 10.2192
- 2026-12-10: 10.1502
- 2026-12-13: 10.144
- 2026-12-14: 10.1278
- 2026-12-15: 10.1571
- 2026-12-16: 9.9676
- 2026-12-17: 10.0285
- 2026-12-20: 10.0475
- 2026-12-21: 10.0239
- 2026-12-22: 9.9439

**Change over the 21 sessions (last forecasted close vs last actual close): -0.36%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.

### financedatabase
Status: ok · exit code: 0
Summary keys: count, method, rows_egypt_equities.csv, rows_us_sector_equities.csv
No report for this tool.
### news-disclosure
Status: failed · exit code: 1
Summary keys: 
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
- news-disclosure (news): failed, exit 1
- {'detail': 'ERROR: no English headlines found for this ticker', 'status': 'failed', 'tool': 'finbert'}: failed
- {'detail': 'ERROR: no English headlines found for this ticker', 'status': 'failed', 'tool': 'finbert-tone'}: failed
- {'detail': 'ERROR: no English headlines found for this ticker', 'status': 'failed', 'tool': 'financial-roberta'}: failed
- {'detail': 'ERROR: no items fetched from any source', 'status': 'failed', 'tool': 'news-disclosure'}: failed

## News + disclosures

## News + disclosures
News: 0 · disclosures: 0 · identity scheme: resolved_url|title-date-hash

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/ORHD-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level unknown — the news tool was missing or failed; not “no risk”.
- news overlay unavailable — risk unassessed, confidence capped
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_orhd.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_orhd.csv: last 10.38 on 2026-11-25
- openbb/ORHD_CA.csv: last 9.98 on 2026-11-24
- pandas-ta/indicators.csv: last 9.98 on 2026-11-24
- talib/indicators.csv: last 9.98 on 2026-11-24
- yahooquery/ORHD.CA.csv: last 9.98 on 2026-11-23
- Kronos forecast: 21 points, last 9.94 at 2026-12-22

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 62 · forecasts: 117 · matured: 48 · pending: 57 · invalid: 12
No accuracy figure is published until n ≥ 30 matured forecasts (n = 48).

## Data-quality flags

## Data-quality flags
- witnesses-stale: common_date 2026-11-23 vs base_date 2026-11-25
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- degraded: partial-fleet (absent families: sentiment)
- news-file-missing: collected/news-disclosure/news.json
- disclosures-file-missing: collected/news-disclosure/disclosures.json
- recommendation-unavailable: no profiles/ORHD.CA.recommendation.json
- reaction-profile-missing: no profiles/ORHD.CA.json
- sharia-row-missing: AAOIFI ORHD.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 ORHD.CA
- sharia-row-missing: FTSE ORHD.CA
- sharia-row-missing: ISLAMICLY ORHD.CA
- sharia-row-missing: MSCI ORHD.CA
- sharia-row-missing: MSCI_M ORHD.CA
- sharia-table-missing: SP_SHARIAH
Degraded: {'absent_families': ['sentiment'], 'absent_tools': ['finbert', 'finbert-tone', 'financial-roberta', 'news-disclosure'], 'reason': 'partial-fleet'}

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