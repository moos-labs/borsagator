# Borsagator report — TMGH.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite TMGH.CA market=EGX · shape: sweep-lite TMGH.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/202510__sweep-lite-tmgh-ca-market-egx__runw5-sweeplite-tmgh-001 · archive commit: beaf77ac5a3f8ffebdb7080ebfe42dc34b08b1b7

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 73.79
Model range high at 84.11
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: sentiment +0.44 vs technicals -0.20 (spread +0.64)
- price-forecast: +0.25
- technicals: -0.20
- sentiment: +0.44
- fundamentals: +0.15
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -2.63% … +2.63%, confidence 0.45)
- week: flat +0.00% (range -6.54% … +6.54%, confidence 0.45)
- month: flat +0.00% (range -12.56% … +12.56%, confidence 0.45)
Base price: 78.95 (egx-data/egxpy_tmgh.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_tmgh.csv: 78.95 on 2026-11-25
- openbb/TMGH_CA.csv: 78.06 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 78.06 on 2026-11-24 (stale)
- talib/indicators.csv: 78.06 on 2026-11-24 (stale)
- yahooquery/TMGH.CA.csv: 79.50 on 2026-11-23 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: TMGH.CA.csv_last_close, TMGH.CA.csv_last_date, rows_TMGH.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: TMGH_CA.csv_last_close, TMGH_CA.csv_last_date, rows_TMGH_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_tmgh.csv_last_close, egxpy_tmgh.csv_last_date, rows_egxpy_tmgh.csv, symbol, ticker
# EGX data sources for TMGH — verdict

No POUL reference material applies to TMGH; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-21 → 2026-11-25
- Latest: 2026-11-25 close 78.95

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — TMGH.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 4706 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 79.5 |
| High | 80.88 |
| Low | 77.77 |
| Close | 78.06 |
| RSI(14) | 35.3023 |
| MACD | -1.5124 |
| MACD signal | -1.3144 |
| MACD histogram | -0.198 |
| EMA(20) | 82.2286 |
| EMA(50) | 85.611 |
| EMA(200) | 86.7226 |
| ADX(14) | 24.7879 |
| Bollinger upper | 86.3443 |
| Bollinger mid | 81.7375 |
| Bollinger lower | 77.1307 |
| Bollinger %B | 0.1009 |
| ATR(14) | 2.4667 |
| Stochastic %K | 17.7214 |
| Stochastic %D | 34.3791 |

## Trend read (facts only)

- Close 78.06 is below EMA_20 82.2286 (-5.07%).
- Close 78.06 is below EMA_50 85.611 (-8.82%).
- Close 78.06 is below EMA_200 86.7226 (-9.99%).
- RSI(14) is 35.3023, in the neutral zone (30-70).
- MACD -1.5124 is below its signal line -1.3144 (histogram -0.198).
- Price sits at %B 0.1009 of the Bollinger range (lower 77.1307, mid 81.7375, upper 86.3443).
- ADX(14) is 24.7879, indicating a developing trend (20-25).
- Stochastic %K 17.7214 is below %D 34.3791.
- ATR(14) is 2.4667 (3.16% of the close).

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
# Fundamentals (generic) — TMGH.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T20:20:21.663326+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 2061000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 78.05999755859375.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 62495.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 14384.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 33.37, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 29.4, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 23.02, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 9.12, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 3.3, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.36

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 14
- Label counts: positive=6, negative=0, neutral=8
- Mean probabilities: positive=0.4070, negative=0.0309, neutral=0.5621

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.1291 | 0.0171 | 0.8538 | Billionaire Hisham Talaat Moustafa's TMG earns $271m in 9M - Billionaires.Africa |
| 2 | neutral | 0.0948 | 0.0238 | 0.8814 | Edita, Valu, TMG, and Bonyan report 9M earnings - EnterpriseAM |
| 3 | neutral | 0.0267 | 0.0775 | 0.8958 | Talaat Moustafa Group Holding Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 4 | positive | 0.9502 | 0.0257 | 0.0241 | TMG Q3 profit up 12.5% to EGP 5.06bn - Dailynewsegypt |
| 5 | positive | 0.9432 | 0.0257 | 0.0312 | Egypt’s TMG Profit Rises 19% To $280.5M In 9M 2026 As Real Estate Revenue Jumps 33% - Forbes Middle East |
| 6 | neutral | 0.0499 | 0.0290 | 0.9211 | TMG bets on recurring income for next growth phase - Daily News Egypt |
| 7 | neutral | 0.0416 | 0.0146 | 0.9438 | Investor Memo: The $200 Billion Question — Hisham Talaat Moustafa's TMG, Egypt's Four New Megaprojects, and Who Will Share the Proceeds - Billionaires.Africa |
| 8 | neutral | 0.2265 | 0.1526 | 0.6209 | Egyptian billionaire Hisham Talaat Moustafa's $200 billion TMG deal draws military interest - Billionaires.Africa |
| 9 | positive | 0.7921 | 0.0063 | 0.2016 | TMG invests in new-generation golf destinations to boost high-spending tourism - Identity Magazine |
| 10 | positive | 0.7840 | 0.0106 | 0.2053 | Egyptian billionaire Hisham Talaat Moustafa's TMG named world's best golf hospitality developer - Billionaires.Africa |
| 11 | positive | 0.5722 | 0.0195 | 0.4084 | Egypt, UAE sweep prestigious WGA among 80 competing nations - EIN News |
| 12 | positive | 0.7370 | 0.0112 | 0.2518 | TMG named world’s best golf developer, Madinaty tops Africa - Dailynewsegypt |
| 13 | neutral | 0.2410 | 0.0091 | 0.7498 | Egypt at heart of global golf: Madinaty selected for 2026 World Golf Awards - Egypt Today |
| 14 | neutral | 0.1102 | 0.0097 | 0.8801 | Thermal Energy International Inc. (TMG:CA) Presents at Planet MicroCap Showcase: Toronto 2026 - Slideshow - Seeking Alpha |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 14
- Label counts: positive=4, negative=0, neutral=10
- Mean probabilities: positive=0.2954, negative=0.0000, neutral=0.7045

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Billionaire Hisham Talaat Moustafa's TMG earns $271m in 9M - Billionaires.Africa |
| 2 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Edita, Valu, TMG, and Bonyan report 9M earnings - EnterpriseAM |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Talaat Moustafa Group Holding Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 4 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | TMG Q3 profit up 12.5% to EGP 5.06bn - Dailynewsegypt |
| 5 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Egypt’s TMG Profit Rises 19% To $280.5M In 9M 2026 As Real Estate Revenue Jumps 33% - Forbes Middle East |
| 6 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | TMG bets on recurring income for next growth phase - Daily News Egypt |
| 7 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Investor Memo: The $200 Billion Question — Hisham Talaat Moustafa's TMG, Egypt's Four New Megaprojects, and Who Will Share the Proceeds - Billionaires.Africa |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Egyptian billionaire Hisham Talaat Moustafa's $200 billion TMG deal draws military interest - Billionaires.Africa |
| 9 | neutral | Neutral | 0.0898 | 0.0000 | 0.9101 | TMG invests in new-generation golf destinations to boost high-spending tourism - Identity Magazine |
| 10 | neutral | Neutral | 0.1874 | 0.0004 | 0.8122 | Egyptian billionaire Hisham Talaat Moustafa's TMG named world's best golf hospitality developer - Billionaires.Africa |
| 11 | positive | Positive | 0.8363 | 0.0001 | 0.1636 | Egypt, UAE sweep prestigious WGA among 80 competing nations - EIN News |
| 12 | positive | Positive | 0.9963 | 0.0000 | 0.0037 | TMG named world’s best golf developer, Madinaty tops Africa - Dailynewsegypt |
| 13 | neutral | Neutral | 0.0006 | 0.0000 | 0.9994 | Egypt at heart of global golf: Madinaty selected for 2026 World Golf Awards - Egypt Today |
| 14 | neutral | Neutral | 0.0256 | 0.0000 | 0.9744 | Thermal Energy International Inc. (TMG:CA) Presents at Planet MicroCap Showcase: Toronto 2026 - Slideshow - Seeking Alpha |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 14
- Label counts: positive=10, negative=1, neutral=3
- Mean probabilities: positive=0.7136, negative=0.0618, neutral=0.2245

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9958 | 0.0003 | 0.0039 | Billionaire Hisham Talaat Moustafa's TMG earns $271m in 9M - Billionaires.Africa |
| 2 | positive | positive | 0.9952 | 0.0004 | 0.0044 | Edita, Valu, TMG, and Bonyan report 9M earnings - EnterpriseAM |
| 3 | neutral | neutral | 0.0005 | 0.0002 | 0.9993 | Talaat Moustafa Group Holding Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 4 | positive | positive | 0.9981 | 0.0009 | 0.0010 | TMG Q3 profit up 12.5% to EGP 5.06bn - Dailynewsegypt |
| 5 | positive | positive | 0.9983 | 0.0008 | 0.0009 | Egypt’s TMG Profit Rises 19% To $280.5M In 9M 2026 As Real Estate Revenue Jumps 33% - Forbes Middle East |
| 6 | positive | positive | 0.9982 | 0.0006 | 0.0013 | TMG bets on recurring income for next growth phase - Daily News Egypt |
| 7 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | Investor Memo: The $200 Billion Question — Hisham Talaat Moustafa's TMG, Egypt's Four New Megaprojects, and Who Will Share the Proceeds - Billionaires.Africa |
| 8 | negative | negative | 0.0122 | 0.8585 | 0.1293 | Egyptian billionaire Hisham Talaat Moustafa's $200 billion TMG deal draws military interest - Billionaires.Africa |
| 9 | positive | positive | 0.9982 | 0.0006 | 0.0012 | TMG invests in new-generation golf destinations to boost high-spending tourism - Identity Magazine |
| 10 | positive | positive | 0.9977 | 0.0008 | 0.0014 | Egyptian billionaire Hisham Talaat Moustafa's TMG named world's best golf hospitality developer - Billionaires.Africa |
| 11 | positive | positive | 0.9980 | 0.0009 | 0.0011 | Egypt, UAE sweep prestigious WGA among 80 competing nations - EIN News |
| 12 | positive | positive | 0.9979 | 0.0009 | 0.0013 | TMG named world’s best golf developer, Madinaty tops Africa - Dailynewsegypt |
| 13 | positive | positive | 0.9967 | 0.0004 | 0.0029 | Egypt at heart of global golf: Madinaty selected for 2026 World Golf Awards - Egypt Today |
| 14 | neutral | neutral | 0.0039 | 0.0002 | 0.9960 | Thermal Energy International Inc. (TMG:CA) Presents at Planet MicroCap Showcase: Toronto 2026 - Slideshow - Seeking Alpha |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — TMGH.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 79.5 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 80.0516
- 2026-11-25: 80.56
- 2026-11-26: 80.9232
- 2026-11-29: 81.0292
- 2026-11-30: 80.8816
- 2026-12-01: 81.6653
- 2026-12-02: 81.6522
- 2026-12-03: 81.6142
- 2026-12-06: 81.3938
- 2026-12-07: 82.1283
- 2026-12-08: 81.8081
- 2026-12-09: 82.4998
- 2026-12-10: 82.1412
- 2026-12-13: 81.703
- 2026-12-14: 82.1858
- 2026-12-15: 81.9427
- 2026-12-16: 82.0935
- 2026-12-17: 82.0128
- 2026-12-20: 82.5472
- 2026-12-21: 82.7409
- 2026-12-22: 82.36

**Change over the 21 sessions (last forecasted close vs last actual close): +3.60%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.

### financedatabase
Status: ok · exit code: 0
Summary keys: count, method, rows_egypt_equities.csv, rows_us_sector_equities.csv
No report for this tool.
### news-disclosure
Status: ok · exit code: 0
Summary keys: arabic_headlines, bodies_fetched, disclosure_count, egx_bodies_attached, egx_disclosures_added, egx_harvest_source, fetched_at, finbert_negative, finbert_neutral, finbert_positive, finbert_scored, latest_disclosure_date, latest_news_date, llm_provider, multilingual_negative, multilingual_neutral, multilingual_positive, multilingual_scored, news_count, ticker
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
News: 40 · disclosures: 3 · identity scheme: resolved_url|title-date-hash
- سهم طلعت مصطفى يرتفع 2.28% خلال تعاملات البورصة اليوم - جريدة البورصة
- سهم طلعت مصطفى يقفز بنسبة 2.28% خلال تعاملات البورصة اليوم - جريدة المال
- مع تهاوي بورصة مصر.. كيف جاء أداء "التجاري الدولي" و"طلعت مصطفى"؟ - Mubasher
- النائب عبدالرحمن بشاري يبحث مع هشام طلعت مصطفى أولوية توظيف أبناء الأقصر ودعم مشروعات التنمية - الوكالة نيوز
- فى سوق المشتقات.. الكبار يراهنون على أسعار "طلعت مصطفى" وCIB حتى 2027 - اليوم السابع
- تراجع العقود المستقبلية لـ EGX30 و"طلعت مصطفى" هامشيًا.. وانخفاض البنك التجاري الدولي بنسب تتخطى 1% اليوم - مجلة البوصلة الاقتصادية
- طلعت مصطفى تفتح جبهة استثمارية جديدة في العراق.. مدينة عمرانية بـ43 ألف وحدة ومبيعات مستهدفة 18.8 مليار دولار - https://www.youlyou.com/
- استثمارات طلعت مصطفى القابضة في العراق تستهدف مدينة ببغداد تضم 43 ألف وحدة - صحيفة اخبارنا
- طلعت مصطفى القابضة تعلن ترسيخ استثماراتها في السوق العراقية - النيل نيوز
- محفظة استثمارات تتخطى الحدود.. طلعت مصطفى القابضة ترسخ أقدامها في قلب العراق - صدى البلد
- ريادة تتخطى الحدود.. طلعت مصطفى القابضة تنقل تجربة مدنها الذكية العالمية إلى العراق - إقرأ نيوز
- سفير العراق في القاهرة يبحث مع الرئيس التنفيذي لمجموعة طلعت مصطفى فرص التعاون والاستثمار في العراق - وزارة الخارجية العراقية
- طلعت مصطفى تستقبل وفدا من المطورين العقاريين العُمانيين في مدينة نور - https://www.youlyou.com/
- 24 ٪ نموًا فى إيرادات «طلعت مصطفى».. والمبيعات تسجل 290 مليار جنيه - المصري اليوم
- Billionaire Hisham Talaat Moustafa's TMG earns $271m in 9M - Billionaires.Africa
- تسليمات مجموعة طلعت مصطفى تقفز 70% في أول 9 أشهر من 2026 - ايكونومي بلس
- "ساوث ميد" يستحوذ على 45% من مبيعات "طلعت مصطفى" في الأشهر الـ9 الأولى من 2026 - ايكونومي بلس
- Edita, Valu, TMG, and Bonyan report 9M earnings - EnterpriseAM
- أرباح “طلعت مصطفى” تقفز إلى 15 مليار جنيه خلال 9 أشهر.. والإيرادات تسجل 47.6 مليار جنيه بنمو 24% - 25H
- Talaat Moustafa Group Holding Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com
- هشام طلعت مصطفى: الطلب القوي على مجتمعاتنا العمرانية والقدرة على التنفيذ يدعمان مرحلة جديدة من النمو - بوابة الأهرام
- ارتفاع أصول «طلعت مصطفى» إلى 507.9 مليار جنيه بنهاية سبتمبر 2026 - بوابة التكنولوجيا المالية
- مجموعة طلعت مصطفى القابضة (TMGH.CA) تعلن نتائج أعمالها المجمعة عن 9 أشهر
- مجموعة طلعت مصطفى القابضة (TMGH.CA) تعلن نتائج أعمالها غير المجمعة عن 9 أشهر
- مجموعة طلعت مصطفى القابضة (TMGH.CA) - قرارات مجلس إدارة الشركة

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/TMGH-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.04
- finbert_positive: 0.08
- multilingual_positive: 0.76
- multilingual_negative: 0.01
- translated_positive: 0.55
- translated_negative: 0.04
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
Chart: egx-data/egxpy_tmgh.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_tmgh.csv: last 78.95 on 2026-11-25
- openbb/TMGH_CA.csv: last 78.06 on 2026-11-24
- pandas-ta/indicators.csv: last 78.06 on 2026-11-24
- talib/indicators.csv: last 78.06 on 2026-11-24
- yahooquery/TMGH.CA.csv: last 79.50 on 2026-11-23
- Kronos forecast: 21 points, last 82.36 at 2026-12-22

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 85 · forecasts: 186 · matured: 48 · pending: 126 · invalid: 12
No accuracy figure is published until n ≥ 30 matured forecasts (n = 48).

## Data-quality flags

## Data-quality flags
- summary-format-diff: news-disclosure (parsed-identical, bytes differ from the canonical indent=2 form)
- witnesses-stale: common_date 2026-11-23 vs base_date 2026-11-25
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/TMGH.CA.recommendation.json
- reaction-profile-missing: no profiles/TMGH.CA.json
- sharia-row-missing: AAOIFI TMGH.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 TMGH.CA
- sharia-row-missing: FTSE TMGH.CA
- sharia-row-missing: ISLAMICLY TMGH.CA
- sharia-row-missing: MSCI TMGH.CA
- sharia-row-missing: MSCI_M TMGH.CA
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