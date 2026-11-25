# Borsagator report — ARCC.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite ARCC.CA market=EGX · shape: sweep-lite ARCC.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/112926__sweep-lite-arcc-ca-market-egx__runw5-sweeplite-arcc-001 · archive commit: 48bde45207a7d2f8a87ced25d6dcaa54e0ad0f49

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 59.20
Model range high at 73.15
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs technicals -0.45 (spread +0.85)
- price-forecast: -0.12
- technicals: -0.45
- sentiment: -0.20
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.068, technicals ×0.679
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat -0.67% (range -6.67% … +5.33%, confidence 0.30)
- week: flat -0.53% (range -11.02% … +9.95%, confidence 0.30)
- month: down -0.97% (range -25.30% … +23.36%, confidence 0.30)
Base price: 66.53 (egx-data/egxpy_arcc.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_arcc.csv: 66.53 on 2026-11-25
- openbb/ARCC_CA.csv: 67.03 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 67.03 on 2026-11-24 (stale)
- talib/indicators.csv: 67.03 on 2026-11-24 (stale)
- yahooquery/ARCC.CA.csv: 66.09 on 2026-11-23 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: ARCC.CA.csv_last_close, ARCC.CA.csv_last_date, rows_ARCC.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: ARCC_CA.csv_last_close, ARCC_CA.csv_last_date, rows_ARCC_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_arcc.csv_last_close, egxpy_arcc.csv_last_date, rows_egxpy_arcc.csv, symbol, ticker
# EGX data sources for ARCC — verdict

No POUL reference material applies to ARCC; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-13 → 2026-11-25
- Latest: 2026-11-25 close 66.53

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — ARCC.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 3088 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 66.09 |
| High | 68.0 |
| Low | 66.51 |
| Close | 67.03 |
| RSI(14) | 49.6957 |
| MACD | 0.0685 |
| MACD signal | 0.1325 |
| MACD histogram | -0.064 |
| EMA(20) | 67.1021 |
| EMA(50) | 67.1514 |
| EMA(200) | 60.1467 |
| ADX(14) | 15.0021 |
| Bollinger upper | 71.5918 |
| Bollinger mid | 66.681 |
| Bollinger lower | 61.7702 |
| Bollinger %B | 0.5355 |
| ATR(14) | 2.7402 |
| Stochastic %K | 30.3773 |
| Stochastic %D | 37.5242 |

## Trend read (facts only)

- Close 67.03 is below EMA_20 67.1021 (-0.11%).
- Close 67.03 is below EMA_50 67.1514 (-0.18%).
- Close 67.03 is above EMA_200 60.1467 (+11.44%).
- RSI(14) is 49.6957, in the neutral zone (30-70).
- MACD 0.0685 is below its signal line 0.1325 (histogram -0.064).
- Price sits at %B 0.5355 of the Bollinger range (lower 61.7702, mid 66.681, upper 71.5918).
- ADX(14) is 15.0021, indicating a weak / no clear trend (< 20).
- Stochastic %K 30.3773 is below %D 37.5242.
- ATR(14) is 2.7402 (4.09% of the close).

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
# Fundamentals (generic) — ARCC.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T11:27:21.583035+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 374870000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 67.02999877929688.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 12447.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 3581.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 40.64, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 36.92, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 28.77, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 77.13, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 40.77, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 11
- Label counts: positive=1, negative=4, neutral=6
- Mean probabilities: positive=0.0749, negative=0.3483, neutral=0.5769

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0211 | 0.0344 | 0.9446 | ARCC Nov 2026 15.000 put (ARCC261120P00015000) stock price, news, quote and history - Yahoo Finance UK |
| 2 | neutral | 0.0295 | 0.0454 | 0.9252 | Here is What to Know Beyond Why Ares Capital Corporation (ARCC) is a Trending Stock - Yahoo Finance |
| 3 | neutral | 0.0250 | 0.0423 | 0.9328 | Ares Capital Corporation (ARCC) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 4 | negative | 0.0295 | 0.8916 | 0.0789 | Ares Capital: The Dividend Squeeze Is On - Seeking Alpha |
| 5 | positive | 0.5253 | 0.0107 | 0.4640 | Ares Capital: The Rich Grow Richer (NASDAQ:ARCC) - Seeking Alpha |
| 6 | neutral | 0.0381 | 0.1149 | 0.8470 | ARCC Students Staging 'Pride and Prejudice' - City of Coon Rapids, MN (.gov) |
| 7 | negative | 0.0100 | 0.9634 | 0.0266 | ARCC Misses on Q3 Earnings as Income Falls, Announces MidCap Buyout - Yahoo Finance |
| 8 | neutral | 0.0343 | 0.0638 | 0.9020 | Ares Capital (ARCC) Q3 2026 Earnings Call Transcript - The Motley Fool |
| 9 | neutral | 0.0768 | 0.0220 | 0.9012 | Ares Capital (ARCC) Q3 Earnings: Taking a Look at Key Metrics Versus Estimates - Yahoo Finance |
| 10 | negative | 0.0105 | 0.9648 | 0.0247 | Ares Capital stock dips as slower transaction environment hits Q3 earnings (ARCC:NASDAQ) - Seeking Alpha |
| 11 | negative | 0.0235 | 0.6777 | 0.2988 | Ares Capital (ARCC) Q3 Earnings and Revenues Miss Estimates - Yahoo Finance |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 11
- Label counts: positive=0, negative=3, neutral=8
- Mean probabilities: positive=0.0001, negative=0.2740, neutral=0.7259

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | ARCC Nov 2026 15.000 put (ARCC261120P00015000) stock price, news, quote and history - Yahoo Finance UK |
| 2 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Here is What to Know Beyond Why Ares Capital Corporation (ARCC) is a Trending Stock - Yahoo Finance |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Ares Capital Corporation (ARCC) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 4 | neutral | Neutral | 0.0002 | 0.0135 | 0.9863 | Ares Capital: The Dividend Squeeze Is On - Seeking Alpha |
| 5 | neutral | Neutral | 0.0008 | 0.0001 | 0.9991 | Ares Capital: The Rich Grow Richer (NASDAQ:ARCC) - Seeking Alpha |
| 6 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | ARCC Students Staging 'Pride and Prejudice' - City of Coon Rapids, MN (.gov) |
| 7 | negative | Negative | 0.0000 | 1.0000 | 0.0000 | ARCC Misses on Q3 Earnings as Income Falls, Announces MidCap Buyout - Yahoo Finance |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 0.9999 | Ares Capital (ARCC) Q3 2026 Earnings Call Transcript - The Motley Fool |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Ares Capital (ARCC) Q3 Earnings: Taking a Look at Key Metrics Versus Estimates - Yahoo Finance |
| 10 | negative | Negative | 0.0001 | 0.9997 | 0.0002 | Ares Capital stock dips as slower transaction environment hits Q3 earnings (ARCC:NASDAQ) - Seeking Alpha |
| 11 | negative | Negative | 0.0000 | 1.0000 | 0.0000 | Ares Capital (ARCC) Q3 Earnings and Revenues Miss Estimates - Yahoo Finance |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 11
- Label counts: positive=1, negative=3, neutral=7
- Mean probabilities: positive=0.0867, negative=0.2726, neutral=0.6407

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | ARCC Nov 2026 15.000 put (ARCC261120P00015000) stock price, news, quote and history - Yahoo Finance UK |
| 2 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | Here is What to Know Beyond Why Ares Capital Corporation (ARCC) is a Trending Stock - Yahoo Finance |
| 3 | neutral | neutral | 0.0013 | 0.0002 | 0.9985 | Ares Capital Corporation (ARCC) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 4 | positive | positive | 0.9423 | 0.0003 | 0.0574 | Ares Capital: The Dividend Squeeze Is On - Seeking Alpha |
| 5 | neutral | neutral | 0.0071 | 0.0003 | 0.9926 | Ares Capital: The Rich Grow Richer (NASDAQ:ARCC) - Seeking Alpha |
| 6 | neutral | neutral | 0.0008 | 0.0005 | 0.9987 | ARCC Students Staging 'Pride and Prejudice' - City of Coon Rapids, MN (.gov) |
| 7 | negative | negative | 0.0003 | 0.9984 | 0.0014 | ARCC Misses on Q3 Earnings as Income Falls, Announces MidCap Buyout - Yahoo Finance |
| 8 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | Ares Capital (ARCC) Q3 2026 Earnings Call Transcript - The Motley Fool |
| 9 | neutral | neutral | 0.0007 | 0.0004 | 0.9989 | Ares Capital (ARCC) Q3 Earnings: Taking a Look at Key Metrics Versus Estimates - Yahoo Finance |
| 10 | negative | negative | 0.0003 | 0.9986 | 0.0011 | Ares Capital stock dips as slower transaction environment hits Q3 earnings (ARCC:NASDAQ) - Seeking Alpha |
| 11 | negative | negative | 0.0003 | 0.9988 | 0.0009 | Ares Capital (ARCC) Q3 Earnings and Revenues Miss Estimates - Yahoo Finance |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — ARCC.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 66.08999633789062 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 66.2411
- 2026-11-25: 66.3394
- 2026-11-26: 66.1372
- 2026-11-29: 66.296
- 2026-11-30: 66.5973
- 2026-12-01: 66.4001
- 2026-12-02: 66.5372
- 2026-12-03: 66.4155
- 2026-12-06: 66.7677
- 2026-12-07: 66.5743
- 2026-12-08: 66.8457
- 2026-12-09: 65.9868
- 2026-12-10: 66.3731
- 2026-12-13: 66.1564
- 2026-12-14: 65.5947
- 2026-12-15: 65.4974
- 2026-12-16: 65.3329
- 2026-12-17: 65.5904
- 2026-12-20: 64.6042
- 2026-12-21: 64.828
- 2026-12-22: 64.7639

**Change over the 21 sessions (last forecasted close vs last actual close): -2.01%**

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
News: 12 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- "آرك إنفستمنت" تفوّت مكاسب بـ10.7 مليون دولار بعد بيع أسهم "إنفيديا" - المشهد العربي
- ARCC Nov 2026 15.000 put (ARCC261120P00015000) stock price, news, quote and history - Yahoo Finance UK
- Here is What to Know Beyond Why Ares Capital Corporation (ARCC) is a Trending Stock - Yahoo Finance
- Ares Capital Corporation (ARCC) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada
- ون بيس على ديزني+: آرك إيغ هيد يصل مدبلجًا بالفرنسية في ديسمبر 2026. - Sortir à Paris
- Ares Capital: The Dividend Squeeze Is On - Seeking Alpha
- Ares Capital: The Rich Grow Richer (NASDAQ:ARCC) - Seeking Alpha
- ARCC Misses on Q3 Earnings as Income Falls, Announces MidCap Buyout - Yahoo Finance
- Ares Capital (ARCC) Q3 2026 Earnings Call Transcript - The Motley Fool
- Ares Capital (ARCC) Q3 Earnings: Taking a Look at Key Metrics Versus Estimates - Yahoo Finance
- Ares Capital stock dips as slower transaction environment hits Q3 earnings (ARCC:NASDAQ) - Seeking Alpha
- Ares Capital (ARCC) Q3 Earnings and Revenues Miss Estimates - Yahoo Finance

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/ARCC-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.37
- finbert_positive: 0.08
- multilingual_positive: 0.62
- multilingual_negative: 0.01
- translated_positive: 0.03
- translated_negative: 0.49
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- earnings event: "آرك إنفستمنت" تفوّت مكاسب بـ10.7 مليون دولار بعد بيع أسهم "إنفيديا" - المشهد العربي
- "آرك إنفستمنت" تفوّت مكاسب بـ10.7 مليون دولار بعد بيع أسهم "إنفيديا" - المشهد العربي (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_arcc.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_arcc.csv: last 66.53 on 2026-11-25
- openbb/ARCC_CA.csv: last 67.03 on 2026-11-24
- pandas-ta/indicators.csv: last 67.03 on 2026-11-24
- talib/indicators.csv: last 67.03 on 2026-11-24
- yahooquery/ARCC.CA.csv: last 66.09 on 2026-11-23
- Kronos forecast: 21 points, last 64.76 at 2026-12-22

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
- recommendation-unavailable: no profiles/ARCC.CA.recommendation.json
- reaction-profile-missing: no profiles/ARCC.CA.json
- sharia-row-missing: AAOIFI ARCC.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 ARCC.CA
- sharia-row-missing: FTSE ARCC.CA
- sharia-row-missing: ISLAMICLY ARCC.CA
- sharia-row-missing: MSCI ARCC.CA
- sharia-row-missing: MSCI_M ARCC.CA
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