# Borsagator report — RMDA.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite RMDA.CA market=EGX · shape: sweep-lite RMDA.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/101919__sweep-lite-rmda-ca-market-egx__runw6-sweeplite-rmda-002 · archive commit: 8226998ff2a1454c03f2feb0fc3723db28a98c88

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 4.52
Model range high at 5.50
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: price-forecast +0.13 vs fundamentals -0.35 (spread +0.48)
- price-forecast: +0.13
- technicals: -0.20
- sentiment: +0.04
- fundamentals: -0.35
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -3.97% … +3.97%, confidence 0.35)
- week: flat +0.00% (range -9.87% … +9.87%, confidence 0.35)
- month: flat +0.00% (range -18.97% … +18.97%, confidence 0.35)
Base price: 5.01 (egx-data/egxpy_rmda.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-25, base date 2026-11-26)
Witnesses stale: common date 2026-11-25 trails base date 2026-11-26.
- egx-data/egxpy_rmda.csv: 5.01 on 2026-11-26
- openbb/RMDA_CA.csv: 5.01 on 2026-11-26
- pandas-ta/indicators.csv: 5.01 on 2026-11-26
- talib/indicators.csv: 5.01 on 2026-11-26
- yahooquery/RMDA.CA.csv: 5.05 on 2026-11-25 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: RMDA.CA.csv_last_close, RMDA.CA.csv_last_date, rows_RMDA.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: RMDA_CA.csv_last_close, RMDA_CA.csv_last_date, rows_RMDA_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_rmda.csv_last_close, egxpy_rmda.csv_last_date, rows_egxpy_rmda.csv, symbol, ticker
# EGX data sources for RMDA — verdict

No POUL reference material applies to RMDA; the series below is reported as fetched.

## egxpy — ok
- Rows: 1700 · Range: 2019-11-27 → 2026-11-26
- Latest: 2026-11-26 close 5.01

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — RMDA.CA

- Last session: **2026-11-26**
- Data used: 1687 rows (2019-12-11 → 2026-11-26), after dropping rows before 2019-01-01; 1687 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 5.05 |
| High | 5.08 |
| Low | 4.96 |
| Close | 5.01 |
| RSI(14) | 41.0427 |
| MACD | -0.0779 |
| MACD signal | -0.0419 |
| MACD histogram | -0.0359 |
| EMA(20) | 5.208 |
| EMA(50) | 5.3383 |
| EMA(200) | 5.0791 |
| ADX(14) | 23.9809 |
| Bollinger upper | 5.7751 |
| Bollinger mid | 5.275 |
| Bollinger lower | 4.7749 |
| Bollinger %B | 0.2351 |
| ATR(14) | 0.2134 |
| Stochastic %K | 14.5834 |
| Stochastic %D | 15.2472 |

## Trend read (facts only)

- Close 5.01 is below EMA_20 5.208 (-3.80%).
- Close 5.01 is below EMA_50 5.3383 (-6.15%).
- Close 5.01 is below EMA_200 5.0791 (-1.36%).
- RSI(14) is 41.0427, in the neutral zone (30-70).
- MACD -0.0779 is below its signal line -0.0419 (histogram -0.0359).
- Price sits at %B 0.2351 of the Bollinger range (lower 4.7749, mid 5.275, upper 5.7751).
- ADX(14) is 23.9809, indicating a developing trend (20-25).
- Stochastic %K 14.5834 is below %D 15.2472.
- ATR(14) is 0.2134 (4.26% of the close).

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
# Fundamentals (generic) — RMDA.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T10:18:02.216644+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 2000000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 5.010000228881836.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 4096.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 268.61, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 48.39, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 23.5, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 6.56, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 12.15, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 5.03, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 1.09,

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 2
- Label counts: positive=0, negative=0, neutral=2
- Mean probabilities: positive=0.1492, negative=0.0233, neutral=0.8274

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0472 | 0.0229 | 0.9299 | Alexandra Andrew, Wife of Michael Andrew, Shares Their Relocation Back to California on Instagram - SwimSwam |
| 2 | neutral | 0.2513 | 0.0237 | 0.7250 | Michael Andrew Races at Legends of Coaching Meet (SCY) for FAST; Clocks 19.15 50 FR, 52.28 100 BR - SwimSwam |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 2
- Label counts: positive=0, negative=0, neutral=2
- Mean probabilities: positive=0.0000, negative=0.0000, neutral=1.0000

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Alexandra Andrew, Wife of Michael Andrew, Shares Their Relocation Back to California on Instagram - SwimSwam |
| 2 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Michael Andrew Races at Legends of Coaching Meet (SCY) for FAST; Clocks 19.15 50 FR, 52.28 100 BR - SwimSwam |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 2
- Label counts: positive=0, negative=0, neutral=2
- Mean probabilities: positive=0.0010, negative=0.0002, neutral=0.9987

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0011 | 0.0002 | 0.9987 | Alexandra Andrew, Wife of Michael Andrew, Shares Their Relocation Back to California on Instagram - SwimSwam |
| 2 | neutral | neutral | 0.0009 | 0.0003 | 0.9988 | Michael Andrew Races at Legends of Coaching Meet (SCY) for FAST; Clocks 19.15 50 FR, 52.28 100 BR - SwimSwam |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — RMDA.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 5.050000190734863 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 5.1133
- 2026-11-29: 5.0773
- 2026-11-30: 5.1706
- 2026-12-01: 5.1632
- 2026-12-02: 5.159
- 2026-12-03: 5.1028
- 2026-12-06: 5.1457
- 2026-12-07: 5.1202
- 2026-12-08: 5.1315
- 2026-12-09: 5.1488
- 2026-12-10: 5.0906
- 2026-12-13: 5.0995
- 2026-12-14: 5.1356
- 2026-12-15: 5.0932
- 2026-12-16: 5.1741
- 2026-12-17: 5.0846
- 2026-12-20: 5.0764
- 2026-12-21: 5.0816
- 2026-12-22: 5.1265
- 2026-12-23: 5.153
- 2026-12-24: 5.1659

**Change over the 21 sessions (last forecasted close vs last actual close): +2.30%**

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
- finbert (sentiment): ok, exit 0
- finbert-tone (sentiment): ok, exit 0
- financial-roberta (sentiment): ok, exit 0
- kronos (forecast): ok, exit 0
- financedatabase (data): ok, exit 0
- news-disclosure (news): failed, exit 1
- {'detail': 'ERROR: no items fetched from any source', 'status': 'failed', 'tool': 'news-disclosure'}: failed

## News + disclosures

## News + disclosures
News: 0 · disclosures: 0 · identity scheme: resolved_url|title-date-hash

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/RMDA-events.json in sweep dir

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
Chart: egx-data/egxpy_rmda.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_rmda.csv: last 5.01 on 2026-11-26
- openbb/RMDA_CA.csv: last 5.01 on 2026-11-26
- pandas-ta/indicators.csv: last 5.01 on 2026-11-26
- talib/indicators.csv: last 5.01 on 2026-11-26
- yahooquery/RMDA.CA.csv: last 5.05 on 2026-11-25
- Kronos forecast: 21 points, last 5.17 at 2026-12-24

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
- degraded: partial-fleet (absent families: —)
- news-file-missing: collected/news-disclosure/news.json
- disclosures-file-missing: collected/news-disclosure/disclosures.json
- recommendation-unavailable: no profiles/RMDA.CA.recommendation.json
- reaction-profile-missing: no profiles/RMDA.CA.json
- sharia-row-missing: AAOIFI RMDA.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 RMDA.CA
- sharia-row-missing: FTSE RMDA.CA
- sharia-row-missing: ISLAMICLY RMDA.CA
- sharia-row-missing: MSCI RMDA.CA
- sharia-row-missing: MSCI_M RMDA.CA
- sharia-table-missing: SP_SHARIAH
Degraded: {'absent_families': [], 'absent_tools': ['news-disclosure'], 'reason': 'partial-fleet'}

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