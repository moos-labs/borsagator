# Borsagator report — AMOC.CA (2026-11-26)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite AMOC.CA market=EGX · shape: sweep-lite AMOC.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-26/233106__sweep-lite-amoc-ca-market-egx__runw6-sweeplite-amoc-002 · archive commit: b2c8efdbd1effe7d38a8c666fb1c47665268346d

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 10.94
Model range high at 13.06
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: price-forecast +0.47 vs sentiment -0.23 (spread +0.70)
- price-forecast: +0.47
- technicals: -0.20
- sentiment: -0.23
- fundamentals: +0.15
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -3.54% … +3.54%, confidence 0.45)
- week: flat +0.00% (range -8.80% … +8.80%, confidence 0.45)
- month: flat +0.00% (range -16.91% … +16.91%, confidence 0.45)
Base price: 12.00 (egx-data/egxpy_amoc.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-24, base date 2026-11-26)
Witnesses stale: common date 2026-11-24 trails base date 2026-11-26.
- egx-data/egxpy_amoc.csv: 12.00 on 2026-11-26
- openbb/AMOC_CA.csv: 11.90 on 2026-11-25 (stale)
- pandas-ta/indicators.csv: 11.90 on 2026-11-25 (stale)
- talib/indicators.csv: 11.90 on 2026-11-25 (stale)
- yahooquery/AMOC.CA.csv: 12.25 on 2026-11-24 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: AMOC.CA.csv_last_close, AMOC.CA.csv_last_date, rows_AMOC.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: AMOC_CA.csv_last_close, AMOC_CA.csv_last_date, rows_AMOC_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_amoc.csv_last_close, egxpy_amoc.csv_last_date, rows_egxpy_amoc.csv, symbol, ticker
# EGX data sources for AMOC — verdict

No POUL reference material applies to AMOC; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-22 → 2026-11-26
- Latest: 2026-11-26 close 12.0

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — AMOC.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5068 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 12.25 |
| High | 12.29 |
| Low | 11.73 |
| Close | 11.9 |
| RSI(14) | 32.2554 |
| MACD | -0.2612 |
| MACD signal | -0.1134 |
| MACD histogram | -0.1478 |
| EMA(20) | 12.9712 |
| EMA(50) | 12.8969 |
| EMA(200) | 10.613 |
| ADX(14) | 13.1315 |
| Bollinger upper | 14.2619 |
| Bollinger mid | 13.172 |
| Bollinger lower | 12.0821 |
| Bollinger %B | -0.0835 |
| ATR(14) | 0.5477 |
| Stochastic %K | 8.2003 |
| Stochastic %D | 8.3101 |

## Trend read (facts only)

- Close 11.9 is below EMA_20 12.9712 (-8.26%).
- Close 11.9 is below EMA_50 12.8969 (-7.73%).
- Close 11.9 is above EMA_200 10.613 (+12.13%).
- RSI(14) is 32.2554, in the neutral zone (30-70).
- MACD -0.2612 is below its signal line -0.1134 (histogram -0.1478).
- Price sits at %B -0.0835 of the Bollinger range (lower 12.0821, mid 13.172, upper 14.2619).
- ADX(14) is 13.1315, indicating a weak / no clear trend (< 20).
- Stochastic %K 8.2003 is below %D 8.3101.
- ATR(14) is 0.5477 (4.60% of the close).

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
# Fundamentals (generic) — AMOC.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-26T23:26:14.292246+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 1292000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 11.899999618530273.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 37623.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 1488.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 6.63, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 3.78, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 3.96, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 27.44, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 14.41, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.00

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 13
- Label counts: positive=1, negative=2, neutral=10
- Mean probabilities: positive=0.1182, negative=0.2486, neutral=0.6332

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0409 | 0.1201 | 0.8389 | Scientist puts risk of Atlantic current system collapse at 50% — Health Policy Watch - UA.NEWS |
| 2 | negative | 0.0208 | 0.7355 | 0.2437 | AMOC Risks Running AMOK: Putting Europe Into Deep Freeze and Disrupting Monsoon Patterns in Africa and Asia - Health Policy Watch |
| 3 | neutral | 0.0379 | 0.0380 | 0.9240 | Atlantic Meridional Overturning Circulation (AMOC) \| Thermohaline, Effects, Collapse, & Facts - Britannica |
| 4 | neutral | 0.0566 | 0.3627 | 0.5807 | Why the ‘cold blob’ may collapse the weather system as we know it - The Independent |
| 5 | negative | 0.0390 | 0.9170 | 0.0440 | Study records 10% weakening of AMOC in 2004–2026 — The Hill - UA.NEWS |
| 6 | neutral | 0.0265 | 0.3786 | 0.5949 | The AMOC ocean current could collapse. If it does, it could change Chicago's weather for 1,000 years. - CBS News |
| 7 | neutral | 0.0329 | 0.0661 | 0.9010 | Iceland Runs Crisis Exercise for AMOC Ocean Current Collapse - Gizmodo |
| 8 | neutral | 0.0176 | 0.0898 | 0.8926 | Weather threat rocks the world - News.com.au |
| 9 | neutral | 0.0215 | 0.2932 | 0.6853 | AMOC collapse: the major climate threat missing from almost every country's adaptation plans - yourweather.co.uk \| Meteored |
| 10 | positive | 0.9421 | 0.0153 | 0.0426 | AMOC Delivers 2.5 fold Profit Growth in 9M 2026 - Egypt Oil & Gas |
| 11 | neutral | 0.1614 | 0.0133 | 0.8253 | The Climate Question \| AMOC: How the changing Atlantic could reshape our world - BBC |
| 12 | neutral | 0.1042 | 0.0888 | 0.8070 | Almost no country plans for a collapse of the Atlantic current that keeps Europe mild, study finds - Nacionale |
| 13 | neutral | 0.0357 | 0.1132 | 0.8511 | Key Atlantic currents could collapse this century, but the risk is missing from almost all national climate plans – new study - The Conversation |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 13
- Label counts: positive=1, negative=9, neutral=3
- Mean probabilities: positive=0.0785, negative=0.5925, neutral=0.3290

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | negative | Negative | 0.0193 | 0.7064 | 0.2743 | Scientist puts risk of Atlantic current system collapse at 50% — Health Policy Watch - UA.NEWS |
| 2 | negative | Negative | 0.0000 | 1.0000 | 0.0000 | AMOC Risks Running AMOK: Putting Europe Into Deep Freeze and Disrupting Monsoon Patterns in Africa and Asia - Health Policy Watch |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Atlantic Meridional Overturning Circulation (AMOC) \| Thermohaline, Effects, Collapse, & Facts - Britannica |
| 4 | negative | Negative | 0.0001 | 0.9985 | 0.0014 | Why the ‘cold blob’ may collapse the weather system as we know it - The Independent |
| 5 | neutral | Neutral | 0.0000 | 0.0000 | 0.9999 | Study records 10% weakening of AMOC in 2004–2026 — The Hill - UA.NEWS |
| 6 | negative | Negative | 0.0001 | 0.6831 | 0.3168 | The AMOC ocean current could collapse. If it does, it could change Chicago's weather for 1,000 years. - CBS News |
| 7 | negative | Negative | 0.0001 | 0.5055 | 0.4944 | Iceland Runs Crisis Exercise for AMOC Ocean Current Collapse - Gizmodo |
| 8 | negative | Negative | 0.0000 | 0.9980 | 0.0020 | Weather threat rocks the world - News.com.au |
| 9 | negative | Negative | 0.0009 | 0.9740 | 0.0251 | AMOC collapse: the major climate threat missing from almost every country's adaptation plans - yourweather.co.uk \| Meteored |
| 10 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | AMOC Delivers 2.5 fold Profit Growth in 9M 2026 - Egypt Oil & Gas |
| 11 | negative | Negative | 0.0000 | 0.8829 | 0.1170 | The Climate Question \| AMOC: How the changing Atlantic could reshape our world - BBC |
| 12 | neutral | Neutral | 0.0000 | 0.0003 | 0.9997 | Almost no country plans for a collapse of the Atlantic current that keeps Europe mild, study finds - Nacionale |
| 13 | negative | Negative | 0.0000 | 0.9533 | 0.0467 | Key Atlantic currents could collapse this century, but the risk is missing from almost all national climate plans – new study - The Conversation |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 13
- Label counts: positive=1, negative=9, neutral=3
- Mean probabilities: positive=0.0849, negative=0.6907, neutral=0.2243

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | negative | negative | 0.0002 | 0.9950 | 0.0048 | Scientist puts risk of Atlantic current system collapse at 50% — Health Policy Watch - UA.NEWS |
| 2 | negative | negative | 0.0003 | 0.9990 | 0.0007 | AMOC Risks Running AMOK: Putting Europe Into Deep Freeze and Disrupting Monsoon Patterns in Africa and Asia - Health Policy Watch |
| 3 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | Atlantic Meridional Overturning Circulation (AMOC) \| Thermohaline, Effects, Collapse, & Facts - Britannica |
| 4 | negative | negative | 0.0002 | 0.9982 | 0.0016 | Why the ‘cold blob’ may collapse the weather system as we know it - The Independent |
| 5 | negative | negative | 0.0012 | 0.9978 | 0.0010 | Study records 10% weakening of AMOC in 2004–2026 — The Hill - UA.NEWS |
| 6 | negative | negative | 0.0002 | 0.9970 | 0.0028 | The AMOC ocean current could collapse. If it does, it could change Chicago's weather for 1,000 years. - CBS News |
| 7 | negative | negative | 0.0002 | 0.9983 | 0.0014 | Iceland Runs Crisis Exercise for AMOC Ocean Current Collapse - Gizmodo |
| 8 | negative | negative | 0.0002 | 0.9989 | 0.0008 | Weather threat rocks the world - News.com.au |
| 9 | negative | negative | 0.0002 | 0.9950 | 0.0048 | AMOC collapse: the major climate threat missing from almost every country's adaptation plans - yourweather.co.uk \| Meteored |
| 10 | positive | positive | 0.9982 | 0.0008 | 0.0010 | AMOC Delivers 2.5 fold Profit Growth in 9M 2026 - Egypt Oil & Gas |
| 11 | neutral | neutral | 0.0002 | 0.0006 | 0.9992 | The Climate Question \| AMOC: How the changing Atlantic could reshape our world - BBC |
| 12 | neutral | neutral | 0.1019 | 0.0007 | 0.8974 | Almost no country plans for a collapse of the Atlantic current that keeps Europe mild, study finds - Nacionale |
| 13 | negative | negative | 0.0004 | 0.9982 | 0.0014 | Key Atlantic currents could collapse this century, but the risk is missing from almost all national climate plans – new study - The Conversation |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — AMOC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 12.25 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 12.3502
- 2026-11-26: 12.3798
- 2026-11-29: 12.4733
- 2026-11-30: 12.5328
- 2026-12-01: 12.5915
- 2026-12-02: 12.6242
- 2026-12-03: 12.6532
- 2026-12-06: 12.6652
- 2026-12-07: 12.8263
- 2026-12-08: 12.9014
- 2026-12-09: 12.9376
- 2026-12-10: 12.9656
- 2026-12-13: 13.005
- 2026-12-14: 13.1017
- 2026-12-15: 13.1421
- 2026-12-16: 13.2158
- 2026-12-17: 13.2053
- 2026-12-20: 13.1574
- 2026-12-21: 13.2767
- 2026-12-22: 13.239
- 2026-12-23: 13.3194

**Change over the 21 sessions (last forecasted close vs last actual close): +8.73%**

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
News: 4 · disclosures: 6 · identity scheme: resolved_url|title-date-hash
- MubasherInfo - Mubasher
- «علوم الإسكندرية» تطلق مبادرة لتلبية احتياجات المصانع محلياً وتفعيل منصة رقمية للأبحاث - المصري اليوم
- مكاسب بالمليارات في البورصة.. "أموك" والإسكندرية للحاويات يقودان قطار الأرباح - اليوم السابع
- AMOC Delivers 2.5 fold Profit Growth in 9M 2026 - Egypt Oil & Gas
- الاسكندرية للزيوت المعدنية (AMOC.CA) - محضر اجتماع الجمعية العامة غير العادية (غير موثق)
- الاسكندرية للزيوت المعدنية (AMOC.CA) تعلن نتائج أعمالها المستقلة عن الفترة: من 01/01/2026 إلى 30/09/2026
- الاسكندرية للزيوت المعدنية (AMOC.CA) تعلن نتائج أعمالها المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026
- الاسكندرية للزيوت المعدنية (AMOC.CA) - قرارات مجلس إدارة الشركة
- الاسكندرية للزيوت المعدنية (AMOC.CA) - ملخص قرارات الجمعية العامة غير العادية
- الاسكندرية للزيوت المعدنية (AMOC.CA) - قرارات مجلس إدارة الشركة

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/AMOC-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.03
- finbert_positive: 0.49
- multilingual_positive: 0.33
- multilingual_negative: 0.01
- translated_positive: 0.18
- translated_negative: 0.03
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
Chart: egx-data/egxpy_amoc.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_amoc.csv: last 12.00 on 2026-11-26
- openbb/AMOC_CA.csv: last 11.90 on 2026-11-25
- pandas-ta/indicators.csv: last 11.90 on 2026-11-25
- talib/indicators.csv: last 11.90 on 2026-11-25
- yahooquery/AMOC.CA.csv: last 12.25 on 2026-11-24
- Kronos forecast: 21 points, last 13.32 at 2026-12-23

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
- recommendation-unavailable: no profiles/AMOC.CA.recommendation.json
- reaction-profile-missing: no profiles/AMOC.CA.json
- sharia-row-missing: AAOIFI AMOC.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 AMOC.CA
- sharia-row-missing: FTSE AMOC.CA
- sharia-row-missing: ISLAMICLY AMOC.CA
- sharia-row-missing: MSCI AMOC.CA
- sharia-row-missing: MSCI_M AMOC.CA
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