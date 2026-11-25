# Borsagator report — EFID.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite EFID.CA market=EGX · shape: sweep-lite EFID.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/120234__sweep-lite-efid-ca-market-egx__runw5-sweeplite-efid-001 · archive commit: ab7dcfcfa4bf3e2dabf6292509b1a14ba66c3199

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 18.17
Model range high at 23.20
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: sentiment +0.62 vs price-forecast -0.32 (spread +0.95)
- price-forecast: -0.32
- technicals: +0.45
- sentiment: +0.62
- fundamentals: -0.10
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.068, technicals ×0.679
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat -0.04% (range -7.06% … +6.97%, confidence 0.30)
- week: flat +0.13% (range -12.03% … +12.30%, confidence 0.30)
- month: down -4.40% (range -30.78% … +21.99%, confidence 0.30)
Base price: 20.66 (egx-data/egxpy_efid.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_efid.csv: 20.66 on 2026-11-25
- openbb/EFID_CA.csv: 20.40 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 20.40 on 2026-11-24 (stale)
- talib/indicators.csv: 20.40 on 2026-11-24 (stale)
- yahooquery/EFID.CA.csv: 20.40 on 2026-11-23 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: EFID.CA.csv_last_close, EFID.CA.csv_last_date, rows_EFID.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: EFID_CA.csv_last_close, EFID_CA.csv_last_date, rows_EFID_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_efid.csv_last_close, egxpy_efid.csv_last_date, rows_egxpy_efid.csv, symbol, ticker
# EGX data sources for EFID — verdict

No POUL reference material applies to EFID; the series below is reported as fetched.

## egxpy — ok
- Rows: 2824 · Range: 2015-04-02 → 2026-11-25
- Latest: 2026-11-25 close 20.66

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — EFID.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 2862 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 20.4 |
| High | 20.4 |
| Low | 20.4 |
| Close | 20.4 |
| RSI(14) | 53.7627 |
| MACD | 0.1878 |
| MACD signal | -0.0702 |
| MACD histogram | 0.258 |
| EMA(20) | 19.8349 |
| EMA(50) | 21.0619 |
| EMA(200) | 24.7604 |
| ADX(14) | 25.8634 |
| Bollinger upper | 21.6436 |
| Bollinger mid | 19.4055 |
| Bollinger lower | 17.1674 |
| Bollinger %B | 0.7222 |
| ATR(14) | 0.8426 |
| Stochastic %K | 68.8765 |
| Stochastic %D | 74.804 |

## Trend read (facts only)

- Close 20.4 is above EMA_20 19.8349 (+2.85%).
- Close 20.4 is below EMA_50 21.0619 (-3.14%).
- Close 20.4 is below EMA_200 24.7604 (-17.61%).
- RSI(14) is 53.7627, in the neutral zone (30-70).
- MACD 0.1878 is above its signal line -0.0702 (histogram 0.258).
- Price sits at %B 0.7222 of the Bollinger range (lower 17.1674, mid 19.4055, upper 21.6436).
- ADX(14) is 25.8634, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 68.8765 is below %D 74.804.
- ATR(14) is 0.8426 (4.13% of the close).

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
# Fundamentals (generic) — EFID.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T12:00:25.353361+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 2084000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 20.399999618530273.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 20915.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 2521.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 34.24, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 17.59, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 12.05, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 41.38, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 17.1, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 7
- Label counts: positive=3, negative=0, neutral=4
- Mean probabilities: positive=0.5042, negative=0.0292, neutral=0.4666

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.2256 | 0.0131 | 0.7613 | Edita Food Industries S.A.E (CAI:EFID) Q3 2026 Earnings Call Highlights: Record Revenue of EGP7. ... By GuruFocus - Investing.com Canada |
| 2 | positive | 0.9478 | 0.0142 | 0.0381 | EFID: Record Q3 revenue and strong volumes support continued growth despite cost and capacity pressures - TradingView |
| 3 | neutral | 0.0332 | 0.0595 | 0.9073 | Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal returns chart - Yahoo Finance Singapore |
| 4 | neutral | 0.0284 | 0.0463 | 0.9254 | Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 5 | neutral | 0.4198 | 0.0082 | 0.5720 | These Are the Best RFID-blocking Wallets For Travelers, According to T+L Editors - Travel + Leisure |
| 6 | positive | 0.9225 | 0.0444 | 0.0332 | Edita’s Q3 profit jumps 41.5% on record sales - Daily News Egypt |
| 7 | positive | 0.9522 | 0.0185 | 0.0293 | EFID: 9M profit reached EGP 2.61bn as capacity investment expands amid rising risks - TradingView |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 7
- Label counts: positive=5, negative=0, neutral=2
- Mean probabilities: positive=0.7142, negative=0.0000, neutral=0.2857

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Edita Food Industries S.A.E (CAI:EFID) Q3 2026 Earnings Call Highlights: Record Revenue of EGP7. ... By GuruFocus - Investing.com Canada |
| 2 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | EFID: Record Q3 revenue and strong volumes support continued growth despite cost and capacity pressures - TradingView |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal returns chart - Yahoo Finance Singapore |
| 4 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 5 | positive | Positive | 0.9997 | 0.0000 | 0.0003 | These Are the Best RFID-blocking Wallets For Travelers, According to T+L Editors - Travel + Leisure |
| 6 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Edita’s Q3 profit jumps 41.5% on record sales - Daily News Egypt |
| 7 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | EFID: 9M profit reached EGP 2.61bn as capacity investment expands amid rising risks - TradingView |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 7
- Label counts: positive=5, negative=0, neutral=2
- Mean probabilities: positive=0.6656, negative=0.0005, neutral=0.3339

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9980 | 0.0006 | 0.0014 | Edita Food Industries S.A.E (CAI:EFID) Q3 2026 Earnings Call Highlights: Record Revenue of EGP7. ... By GuruFocus - Investing.com Canada |
| 2 | positive | positive | 0.9983 | 0.0007 | 0.0010 | EFID: Record Q3 revenue and strong volumes support continued growth despite cost and capacity pressures - TradingView |
| 3 | neutral | neutral | 0.0006 | 0.0002 | 0.9992 | Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal returns chart - Yahoo Finance Singapore |
| 4 | neutral | neutral | 0.0008 | 0.0002 | 0.9991 | Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 5 | positive | positive | 0.6648 | 0.0006 | 0.3346 | These Are the Best RFID-blocking Wallets For Travelers, According to T+L Editors - Travel + Leisure |
| 6 | positive | positive | 0.9982 | 0.0008 | 0.0010 | Edita’s Q3 profit jumps 41.5% on record sales - Daily News Egypt |
| 7 | positive | positive | 0.9981 | 0.0007 | 0.0012 | EFID: 9M profit reached EGP 2.61bn as capacity investment expands amid rising risks - TradingView |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — EFID.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 20.399999618530273 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 20.4419
- 2026-11-25: 20.3532
- 2026-11-26: 20.4242
- 2026-11-29: 20.4697
- 2026-11-30: 20.3461
- 2026-12-01: 20.1552
- 2026-12-02: 19.9746
- 2026-12-03: 19.8542
- 2026-12-06: 19.7228
- 2026-12-07: 19.5377
- 2026-12-08: 19.7756
- 2026-12-09: 19.638
- 2026-12-10: 19.5221
- 2026-12-13: 19.4211
- 2026-12-14: 19.3519
- 2026-12-15: 19.3217
- 2026-12-16: 19.3163
- 2026-12-17: 19.2441
- 2026-12-20: 19.097
- 2026-12-21: 19.0641
- 2026-12-22: 19.0769

**Change over the 21 sessions (last forecasted close vs last actual close): -6.49%**

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
News: 4 · disclosures: 2 · identity scheme: resolved_url|title-date-hash
- Edita Food Industries S.A.E (CAI:EFID) Q3 2026 Earnings Call Highlights: Record Revenue of EGP7. ... By GuruFocus - Investing.com Canada
- إيديتا للصناعات الغذائية تعلن نتائج الربع الثالث من عام 2026 - جريدة المال
- إيديتا تحقق أعلى إيرادات فصلية في تاريخها بـ7.3 مليار جنيه بالربع الثالث 2026 - https://www.youlyou.com/
- أرباح إيديتا تقفز 54% إلى 2.4 مليار جنيه بأول 9 شهور من 2026 - https://www.youlyou.com/
- Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal returns chart - Yahoo Finance Singapore
- Edita Food Industries Company (S.A.E) (EFID.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/EFID-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.04
- finbert_positive: 0.10
- multilingual_positive: 0.94
- multilingual_negative: 0.00
- translated_positive: 0.95
- translated_negative: 0.02
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- earnings event: Edita Food Industries S.A.E (CAI:EFID) Q3 2026 Earnings Call Highlights: Record Revenue of
- Edita Food Industries S.A.E (CAI:EFID) Q3 2026 Earnings Call Highlights: Record Revenue of (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_efid.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_efid.csv: last 20.66 on 2026-11-25
- openbb/EFID_CA.csv: last 20.40 on 2026-11-24
- pandas-ta/indicators.csv: last 20.40 on 2026-11-24
- talib/indicators.csv: last 20.40 on 2026-11-24
- yahooquery/EFID.CA.csv: last 20.40 on 2026-11-23
- Kronos forecast: 21 points, last 19.08 at 2026-12-22

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 53 · forecasts: 90 · matured: 45 · pending: 36 · invalid: 9
No accuracy figure is published until n ≥ 30 matured forecasts (n = 45).

## Data-quality flags

## Data-quality flags
- witnesses-stale: common_date 2026-11-23 vs base_date 2026-11-25
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/EFID.CA.recommendation.json
- reaction-profile-missing: no profiles/EFID.CA.json
- sharia-row-missing: AAOIFI EFID.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 EFID.CA
- sharia-row-missing: FTSE EFID.CA
- sharia-row-missing: ISLAMICLY EFID.CA
- sharia-row-missing: MSCI EFID.CA
- sharia-row-missing: MSCI_M EFID.CA
- sharia-table-missing: SP_SHARIAH

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