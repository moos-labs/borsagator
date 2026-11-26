# Borsagator report — ADIB.CA (2026-11-26)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite ADIB.CA market=EGX · shape: sweep-lite ADIB.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-26/232510__sweep-lite-adib-ca-market-egx__runw6-sweeplite-adib-002 · archive commit: b82d5962fa5459cb254efd3d306369c60253d09f

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 41.66
Model range high at 50.30
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs technicals -0.30 (spread +0.70)
- price-forecast: +0.08
- technicals: -0.30
- sentiment: +0.25
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -3.77% … +3.77%, confidence 0.30)
- week: flat +0.00% (range -9.39% … +9.39%, confidence 0.30)
- month: flat +0.00% (range -18.05% … +18.05%, confidence 0.30)
Base price: 45.98 (egx-data/egxpy_adib.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-24, base date 2026-11-26)
Witnesses stale: common date 2026-11-24 trails base date 2026-11-26.
- egx-data/egxpy_adib.csv: 45.98 on 2026-11-26
- openbb/ADIB_CA.csv: 45.93 on 2026-11-25 (stale)
- pandas-ta/indicators.csv: 45.93 on 2026-11-25 (stale)
- talib/indicators.csv: 45.93 on 2026-11-25 (stale)
- yahooquery/ADIB.CA.csv: 46.15 on 2026-11-24 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: ADIB.CA.csv_last_close, ADIB.CA.csv_last_date, rows_ADIB.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: ADIB_CA.csv_last_close, ADIB_CA.csv_last_date, rows_ADIB_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_adib.csv_last_close, egxpy_adib.csv_last_date, rows_egxpy_adib.csv, symbol, ticker
# EGX data sources for ADIB — verdict

No POUL reference material applies to ADIB; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-16 → 2026-11-26
- Latest: 2026-11-26 close 45.98

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — ADIB.CA

- Last session: **2026-11-25**
- Data used: 1932 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6536 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 46.15 |
| High | 46.5 |
| Low | 45.5 |
| Close | 45.93 |
| RSI(14) | 42.7208 |
| MACD | -0.4521 |
| MACD signal | -0.2271 |
| MACD histogram | -0.225 |
| EMA(20) | 47.2471 |
| EMA(50) | 48.1016 |
| EMA(200) | 45.3151 |
| ADX(14) | 28.6098 |
| Bollinger upper | 50.6187 |
| Bollinger mid | 47.6205 |
| Bollinger lower | 44.6223 |
| Bollinger %B | 0.2181 |
| ATR(14) | 1.5346 |
| Stochastic %K | 27.8798 |
| Stochastic %D | 27.0994 |

## Trend read (facts only)

- Close 45.93 is below EMA_20 47.2471 (-2.79%).
- Close 45.93 is below EMA_50 48.1016 (-4.51%).
- Close 45.93 is above EMA_200 45.3151 (+1.36%).
- RSI(14) is 42.7208, in the neutral zone (30-70).
- MACD -0.4521 is below its signal line -0.2271 (histogram -0.225).
- Price sits at %B 0.2181 of the Bollinger range (lower 44.6223, mid 47.6205, upper 50.6187).
- ADX(14) is 28.6098, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 27.8798 is above %D 27.0994.
- ATR(14) is 1.5346 (3.34% of the close).

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
# Fundamentals (generic) — ADIB.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-26T23:21:03.639618+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 1200000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 45.93000030517578.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 22040.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 12589.0, "basis": "vendor income statement"}, "net_margin_pct": {"value": 57.12, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 36.35, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 3.63, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.299, "basis": "vendor total debt / equity"}, "ocf_margin_pct": {"value": -260.19, "basis": "operating cash flow / revenue"}, "fcf_margin_pct": {"value": -262.1, "basis

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 30
- Label counts: positive=12, negative=3, neutral=15
- Mean probabilities: positive=0.3996, negative=0.0941, neutral=0.5063

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | positive | 0.8178 | 0.0089 | 0.1733 | ADIB raises $500m in perpetual sukuk to support growth strategy - The National |
| 2 | positive | 0.9380 | 0.0130 | 0.0490 | ADIB raises $500 million in US dollar-denominated tier-one perpetual sukuk; demand exceeds initial offer by over three times - www.wam.ae |
| 3 | positive | 0.8190 | 0.0100 | 0.1710 | ADIB raises $500m in AT1 sukuk as investor demand tops $1.5 billion - Khaleej Times |
| 4 | positive | 0.8123 | 0.0134 | 0.1742 | ADIB raises $500M in oversubscribed AT1 perpetual sukuk at 7% - Dealroom |
| 5 | neutral | 0.0441 | 0.0298 | 0.9261 | The things that can wait — Nahrizul Adib Kadri - Malay Mail |
| 6 | neutral | 0.0423 | 0.0316 | 0.9261 | What came home on Fridays — Nahrizul Adib Kadri - Malay Mail |
| 7 | positive | 0.9157 | 0.0158 | 0.0685 | ADIB-Egypt named Global Finance’s best Islamic financial institution in Egypt for 9th year - Daily News Egypt |
| 8 | positive | 0.7349 | 0.0140 | 0.2511 | ADIB Ventures and DIFC Innovation Hub announce winner of ADIB SME innovation challenge - Zawya |
| 9 | positive | 0.7987 | 0.0232 | 0.1781 | Al Wasl beat Al Nasr 2–0 in ADIB Cup derby - Sharjah24 |
| 10 | neutral | 0.3766 | 0.0386 | 0.5849 | United and Sharjah draw 1–1 in ADIB Cup - Sharjah24 |
| 11 | neutral | 0.3249 | 0.0562 | 0.6189 | Kalba and Shabab Al Ahli draw 1–1 in ADIB Cup - Sharjah24 |
| 12 | positive | 0.8497 | 0.0204 | 0.1299 | Al Jazira beat Bani Yas 1–0 in ADIB Cup - Sharjah24 |
| 13 | positive | 0.8145 | 0.0208 | 0.1647 | Al Wahda beat Khorfakkan 3–1 in ADIB Cup - Sharjah24 |
| 14 | positive | 0.6581 | 0.0428 | 0.2990 | Al Ain claim first ADIB Cup win of the season - Sharjah24 |
| 15 | positive | 0.5440 | 0.0361 | 0.4199 | Al Dhafra beat Ajman for first ADIB Cup win - Sharjah24 |
| 16 | neutral | 0.2639 | 0.0090 | 0.7270 | Aldar and ADIB Launch Co-Branded Darna Covered Cards in Abu Dhabi - The Fintech Times |
| 17 | negative | 0.0113 | 0.9187 | 0.0701 | Selangor defender Adib falls victim to concert ticket scam - NST Online |
| 18 | neutral | 0.4260 | 0.0088 | 0.5652 | How to build smart savings habits with ADIB for long-term financial security - Gulf News |
| 19 | positive | 0.4966 | 0.0082 | 0.4953 | ADIB launches ADIB Arrive proposition for new residents in the UAE - The Paypers |
| 20 | neutral | 0.0953 | 0.0113 | 0.8934 | ADIB Launches ‘ADIB Arrive’ to Streamline Banking for New UAE Residents - FF News |
| 21 | neutral | 0.4676 | 0.0159 | 0.5165 | ADIB opens $476 million rights issue, FAB acquires Yasira and Qatar eases SME lending rules - The Asian Banker |
| 22 | neutral | 0.0628 | 0.0096 | 0.9276 | Subscription to ADIB’s new shares as part of its AED1.75 billion rights issue to begin on 10 November - www.wam.ae |
| 23 | neutral | 0.0418 | 0.0141 | 0.9441 | ADIB’s Dh1.75 billion rights issue opens on Nov 10 - Gulf News |
| 24 | neutral | 0.2277 | 0.0082 | 0.7641 | ADIB adds real-time EGP transfers to Egypt via Visa Direct - The Paypers |
| 25 | neutral | 0.1847 | 0.0092 | 0.8062 | ADIB Launches UAE’s First 24/7 Real-Time EGP Transfers to Egypt via Visa Direct - FF News |
| 26 | negative | 0.0306 | 0.6407 | 0.3288 | Surgeon to mediate over alleged rape - The Australian |
| 27 | negative | 0.0548 | 0.6647 | 0.2806 | Former Queensland premier Annastacia Palaszczuk’s ex-partner Reza Adib’s bail altered for Gold Coast rape charges - SMH.com.au |
| 28 | neutral | 0.0663 | 0.0961 | 0.8376 | Gold Coast surgeon Reza Adib fronts court - The Australian |
| 29 | neutral | 0.0263 | 0.0203 | 0.9534 | ADIB rights trading period for AED 1.75 billion rights issue begins on 4 November - www.wam.ae |
| 30 | neutral | 0.0403 | 0.0148 | 0.9449 | Adib opens trading for Dh1.75 billion rights issue; key dates investors should know - Khaleej Times |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 30
- Label counts: positive=2, negative=0, neutral=28
- Mean probabilities: positive=0.0676, negative=0.0020, neutral=0.9303

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0022 | 0.0000 | 0.9978 | ADIB raises $500m in perpetual sukuk to support growth strategy - The National |
| 2 | neutral | Neutral | 0.0020 | 0.0000 | 0.9980 | ADIB raises $500 million in US dollar-denominated tier-one perpetual sukuk; demand exceeds initial offer by over three times - www.wam.ae |
| 3 | neutral | Neutral | 0.0011 | 0.0000 | 0.9989 | ADIB raises $500m in AT1 sukuk as investor demand tops $1.5 billion - Khaleej Times |
| 4 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | ADIB raises $500M in oversubscribed AT1 perpetual sukuk at 7% - Dealroom |
| 5 | neutral | Neutral | 0.0000 | 0.0005 | 0.9995 | The things that can wait — Nahrizul Adib Kadri - Malay Mail |
| 6 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | What came home on Fridays — Nahrizul Adib Kadri - Malay Mail |
| 7 | neutral | Neutral | 0.0004 | 0.0000 | 0.9996 | ADIB-Egypt named Global Finance’s best Islamic financial institution in Egypt for 9th year - Daily News Egypt |
| 8 | positive | Positive | 0.9997 | 0.0000 | 0.0003 | ADIB Ventures and DIFC Innovation Hub announce winner of ADIB SME innovation challenge - Zawya |
| 9 | neutral | Neutral | 0.0001 | 0.0001 | 0.9998 | Al Wasl beat Al Nasr 2–0 in ADIB Cup derby - Sharjah24 |
| 10 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | United and Sharjah draw 1–1 in ADIB Cup - Sharjah24 |
| 11 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Kalba and Shabab Al Ahli draw 1–1 in ADIB Cup - Sharjah24 |
| 12 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Al Jazira beat Bani Yas 1–0 in ADIB Cup - Sharjah24 |
| 13 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Al Wahda beat Khorfakkan 3–1 in ADIB Cup - Sharjah24 |
| 14 | neutral | Neutral | 0.0042 | 0.0002 | 0.9956 | Al Ain claim first ADIB Cup win of the season - Sharjah24 |
| 15 | neutral | Neutral | 0.1100 | 0.0002 | 0.8898 | Al Dhafra beat Ajman for first ADIB Cup win - Sharjah24 |
| 16 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | Aldar and ADIB Launch Co-Branded Darna Covered Cards in Abu Dhabi - The Fintech Times |
| 17 | neutral | Neutral | 0.0000 | 0.0005 | 0.9995 | Selangor defender Adib falls victim to concert ticket scam - NST Online |
| 18 | positive | Positive | 0.8505 | 0.0002 | 0.1494 | How to build smart savings habits with ADIB for long-term financial security - Gulf News |
| 19 | neutral | Neutral | 0.0363 | 0.0000 | 0.9636 | ADIB launches ADIB Arrive proposition for new residents in the UAE - The Paypers |
| 20 | neutral | Neutral | 0.0015 | 0.0000 | 0.9985 | ADIB Launches ‘ADIB Arrive’ to Streamline Banking for New UAE Residents - FF News |
| 21 | neutral | Neutral | 0.0009 | 0.0000 | 0.9990 | ADIB opens $476 million rights issue, FAB acquires Yasira and Qatar eases SME lending rules - The Asian Banker |
| 22 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Subscription to ADIB’s new shares as part of its AED1.75 billion rights issue to begin on 10 November - www.wam.ae |
| 23 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | ADIB’s Dh1.75 billion rights issue opens on Nov 10 - Gulf News |
| 24 | neutral | Neutral | 0.0173 | 0.0000 | 0.9827 | ADIB adds real-time EGP transfers to Egypt via Visa Direct - The Paypers |
| 25 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | ADIB Launches UAE’s First 24/7 Real-Time EGP Transfers to Egypt via Visa Direct - FF News |
| 26 | neutral | Neutral | 0.0028 | 0.0582 | 0.9390 | Surgeon to mediate over alleged rape - The Australian |
| 27 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Former Queensland premier Annastacia Palaszczuk’s ex-partner Reza Adib’s bail altered for Gold Coast rape charges - SMH.com.au |
| 28 | neutral | Neutral | 0.0000 | 0.0009 | 0.9991 | Gold Coast surgeon Reza Adib fronts court - The Australian |
| 29 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | ADIB rights trading period for AED 1.75 billion rights issue begins on 4 November - www.wam.ae |
| 30 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Adib opens trading for Dh1.75 billion rights issue; key dates investors should know - Khaleej Times |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 31
- Label counts: positive=18, negative=2, neutral=11
- Mean probabilities: positive=0.5949, negative=0.0655, neutral=0.3396

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9983 | 0.0006 | 0.0012 | ADIB raises $500m in perpetual sukuk to support growth strategy - The National |
| 2 | positive | positive | 0.9982 | 0.0008 | 0.0010 | ADIB raises $500 million in US dollar-denominated tier-one perpetual sukuk; demand exceeds initial offer by over three times - www.wam.ae |
| 3 | positive | positive | 0.9982 | 0.0007 | 0.0012 | ADIB raises $500m in AT1 sukuk as investor demand tops $1.5 billion - Khaleej Times |
| 4 | positive | positive | 0.9981 | 0.0006 | 0.0013 | ADIB raises $500M in oversubscribed AT1 perpetual sukuk at 7% - Dealroom |
| 5 | neutral | neutral | 0.0004 | 0.0003 | 0.9993 | The things that can wait — Nahrizul Adib Kadri - Malay Mail |
| 6 | neutral | neutral | 0.0004 | 0.0006 | 0.9990 | What came home on Fridays — Nahrizul Adib Kadri - Malay Mail |
| 7 | positive | positive | 0.9979 | 0.0010 | 0.0010 | ADIB-Egypt named Global Finance’s best Islamic financial institution in Egypt for 9th year - Daily News Egypt |
| 8 | positive | positive | 0.9980 | 0.0007 | 0.0013 | ADIB Ventures and DIFC Innovation Hub announce winner of ADIB SME innovation challenge - Zawya |
| 9 | positive | positive | 0.9983 | 0.0008 | 0.0009 | Abu Dhabi Islamic Bank Egypt stock: 9-month profit rises 22.8% - ad-hoc-news.de |
| 10 | positive | positive | 0.9288 | 0.0046 | 0.0666 | Al Wasl beat Al Nasr 2–0 in ADIB Cup derby - Sharjah24 |
| 11 | neutral | neutral | 0.0606 | 0.0019 | 0.9375 | United and Sharjah draw 1–1 in ADIB Cup - Sharjah24 |
| 12 | neutral | neutral | 0.0035 | 0.0324 | 0.9641 | Kalba and Shabab Al Ahli draw 1–1 in ADIB Cup - Sharjah24 |
| 13 | positive | positive | 0.9962 | 0.0011 | 0.0027 | Al Jazira beat Bani Yas 1–0 in ADIB Cup - Sharjah24 |
| 14 | positive | positive | 0.9975 | 0.0009 | 0.0016 | Al Wahda beat Khorfakkan 3–1 in ADIB Cup - Sharjah24 |
| 15 | positive | positive | 0.9981 | 0.0008 | 0.0010 | Al Ain claim first ADIB Cup win of the season - Sharjah24 |
| 16 | positive | positive | 0.9979 | 0.0008 | 0.0013 | Al Dhafra beat Ajman for first ADIB Cup win - Sharjah24 |
| 17 | positive | positive | 0.9979 | 0.0005 | 0.0016 | Aldar and ADIB Launch Co-Branded Darna Covered Cards in Abu Dhabi - The Fintech Times |
| 18 | negative | negative | 0.0002 | 0.9986 | 0.0012 | Selangor defender Adib falls victim to concert ticket scam - NST Online |
| 19 | neutral | neutral | 0.4788 | 0.0003 | 0.5209 | How to build smart savings habits with ADIB for long-term financial security - Gulf News |
| 20 | positive | positive | 0.9971 | 0.0003 | 0.0026 | ADIB launches ADIB Arrive proposition for new residents in the UAE - The Paypers |
| 21 | positive | positive | 0.9980 | 0.0006 | 0.0014 | ADIB Launches ‘ADIB Arrive’ to Streamline Banking for New UAE Residents - FF News |
| 22 | positive | positive | 0.9980 | 0.0006 | 0.0014 | ADIB opens $476 million rights issue, FAB acquires Yasira and Qatar eases SME lending rules - The Asian Banker |
| 23 | neutral | neutral | 0.0009 | 0.0002 | 0.9989 | Subscription to ADIB’s new shares as part of its AED1.75 billion rights issue to begin on 10 November - www.wam.ae |
| 24 | neutral | neutral | 0.0006 | 0.0002 | 0.9992 | ADIB’s Dh1.75 billion rights issue opens on Nov 10 - Gulf News |
| 25 | positive | positive | 0.9947 | 0.0003 | 0.0050 | ADIB adds real-time EGP transfers to Egypt via Visa Direct - The Paypers |
| 26 | positive | positive | 0.9978 | 0.0007 | 0.0015 | ADIB Launches UAE’s First 24/7 Real-Time EGP Transfers to Egypt via Visa Direct - FF News |
| 27 | neutral | neutral | 0.0009 | 0.0013 | 0.9978 | Surgeon to mediate over alleged rape - The Australian |
| 28 | negative | negative | 0.0009 | 0.9776 | 0.0215 | Former Queensland premier Annastacia Palaszczuk’s ex-partner Reza Adib’s bail altered for Gold Coast rape charges - SMH.com.au |
| 29 | neutral | neutral | 0.0051 | 0.0002 | 0.9947 | Adib opens trading for Dh1.75 billion rights issue; key dates investors should know - Khaleej Times |
| 30 | neutral | neutral | 0.0004 | 0.0011 | 0.9985 | Gold Coast surgeon Reza Adib fronts court - The Australian |
| 31 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | ADIB rights trading period for AED 1.75 billion rights issue begins on 4 November - www.wam.ae |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — ADIB.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 46.150001525878906 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 46.0468
- 2026-11-26: 45.9933
- 2026-11-29: 46.1154
- 2026-11-30: 46.0483
- 2026-12-01: 45.84
- 2026-12-02: 46.1395
- 2026-12-03: 46.6546
- 2026-12-06: 46.5046
- 2026-12-07: 46.3629
- 2026-12-08: 46.5088
- 2026-12-09: 46.5742
- 2026-12-10: 47.0256
- 2026-12-13: 46.8027
- 2026-12-14: 46.9198
- 2026-12-15: 46.4266
- 2026-12-16: 46.9186
- 2026-12-17: 46.9973
- 2026-12-20: 46.7508
- 2026-12-21: 46.61
- 2026-12-22: 46.5302
- 2026-12-23: 46.7053

**Change over the 21 sessions (last forecasted close vs last actual close): +1.20%**

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
News: 40 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- ADIB raises $500m in perpetual sukuk to support growth strategy - The National
- منير أديب: مخاوف أوروبا من الإخوان تحولت لحقائق بعد تغلغلها بالمؤسسات.. - حفريات
- منير أديب: أوروبا بدأت تدرك خطورة الإخوان بعد التحذيرات المصرية - اليوم السابع
- عمرو أديب عن حريق دائري الوراق: كارثة بكل المقاييس.. والظلام على الطريق مرعب - الرئيس نيوز
- عمرو أديب عن حريق دائري الوراق: الظلام على الطريق مرعب والسيارات تسير بلا حساب - أهل مصر
- عمرو أديب بعد حادث دائري الوراق: خسائر الطرق في مصر مرعبة وأعدادها غريبة - فيتو
- عمرو أديب يعلق على حادث الوراق: الظلام على الطريق الدائري مرعب - Masrawy
- عمرو أديب عن حريق الوراق: «أستخدم امتداد هذا الطريق يوميًا.. والظلام فيه مرعب» - المصري اليوم
- 1.8 تريليون جنيه حجم المصرفية الإسلامية في مصر.. و«ADIB» يتصدر - شبكة تواصل الإخبارية
- منير أديب: العواصم الأوروبية أدركت أن الإرهابية تمثل خطرًا على أمنها (فيديو) - مبتدا
- عمرو أديب يهاجم الأهلي بعد هزيمته أمام بيراميدز 2-0 ويطالب ببقاء عموتة - شبكة تواصل الإخبارية
- القطيف - القلعة: الأديب والشاعر الحاج محمد سعيد ابن الشيخ علي ابو الحسن الخنيزي في ذمة الله - alqhat.com
- عمرو أديب يعلّق على سقوط الأهلي أمام بيراميدز ويوجه رسالة مهمة بشأن مستقبل عموتة - شبكة تواصل الإخبارية
- عمرو أديب يهاجم لاعبي الأهلي: «مستواهم زي الزفت.. والدلع زاد عن حده» - ايجي بودكاست
- عمرو أديب بعد مباراة بيراميدز: ليه النادي الأهلي ميجبش حسام وإبراهيم حسن؟ - أهل مصر
- عمرو أديب بعد الفوز على الأهلي: بيراميدز قدموا كل فنون كرة القدم - أهل مصر
- عمرو أديب يهاجم لاعبي الأهلي: فين روح الفانلة الحمراء؟ - https://www.youlyou.com/
- عمرو أديب بعد خسارة الأهلي أمام بيراميدز: الفريق السماوي يستحق لقب الدوري.. وتمسكوا بعموتة (فيديو) - أهل مصر
- عمرو أديب: الأهلي من سيئ إلى أسوأ.. وحال جمهوره يصعب عليك - أهل مصر
- عمرو أديب يفتح النار على الأهلي بعد السقوط أمام بيراميدز.. فماذا قال؟ - elmaser.com
- عمرو أديب لـ إدارة النادي الأهلي بعد مباراة بيراميدز: "اوعوا تمشوا عموتة.. خلوه عشان الشرط الجزائي" - أهل مصر
- عمرو أديب ينتقد الإعجاب بـ حسن أحمديان: غدا سيظهر لنا شاب جديد يقنعنا بيهودية فلسطين! - المصري اليوم

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/ADIB-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.02
- finbert_positive: 0.85
- multilingual_positive: 0.24
- multilingual_negative: 0.55
- translated_positive: 0.11
- translated_negative: 0.29
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- earnings event: ADIB raises $500m in perpetual sukuk to support growth strategy - The National
- earnings event: عمرو أديب بعد حادث دائري الوراق: خسائر الطرق في مصر مرعبة وأعدادها غريبة - فيتو
- earnings event: عمرو أديب يعلق على حادث الوراق: الظلام على الطريق الدائري مرعب - Masrawy
- ADIB raises $500m in perpetual sukuk to support growth strategy - The National (truncated title — see the archived news file for full text)
- عمرو أديب بعد حادث دائري الوراق: خسائر الطرق في مصر مرعبة وأعدادها غريبة - فيتو (truncated title — see the archived news file for full text)
- عمرو أديب يعلق على حادث الوراق: الظلام على الطريق الدائري مرعب - Masrawy (truncated title — see the archived news file for full text)
- عمرو أديب عن حريق الوراق: «أستخدم امتداد هذا الطريق يوميًا.. والظلام فيه مرعب» - المصري ال (truncated title — see the archived news file for full text)
- 1.8 تريليون جنيه حجم المصرفية الإسلامية في مصر.. و«ADIB» يتصدر - شبكة تواصل الإخبارية (truncated title — see the archived news file for full text)
- عمرو أديب يهاجم الأهلي بعد هزيمته أمام بيراميدز 2-0 ويطالب ببقاء عموتة - شبكة تواصل الإخبا (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_adib.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_adib.csv: last 45.98 on 2026-11-26
- openbb/ADIB_CA.csv: last 45.93 on 2026-11-25
- pandas-ta/indicators.csv: last 45.93 on 2026-11-25
- talib/indicators.csv: last 45.93 on 2026-11-25
- yahooquery/ADIB.CA.csv: last 46.15 on 2026-11-24
- Kronos forecast: 21 points, last 46.71 at 2026-12-23

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 91 · forecasts: 204 · matured: 48 · pending: 144 · invalid: 12
No accuracy figure is published until n ≥ 30 matured forecasts (n = 48).

## Data-quality flags

## Data-quality flags
- witnesses-stale: common_date 2026-11-24 vs base_date 2026-11-26
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/ADIB.CA.recommendation.json
- reaction-profile-missing: no profiles/ADIB.CA.json
- sharia-row-missing: AAOIFI ADIB.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 ADIB.CA
- sharia-row-missing: FTSE ADIB.CA
- sharia-row-missing: ISLAMICLY ADIB.CA
- sharia-row-missing: MSCI ADIB.CA
- sharia-row-missing: MSCI_M ADIB.CA
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