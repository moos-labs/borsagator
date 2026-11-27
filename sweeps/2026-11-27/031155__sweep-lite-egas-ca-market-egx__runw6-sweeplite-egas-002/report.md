# Borsagator report — EGAS.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite EGAS.CA market=EGX · shape: sweep-lite EGAS.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/031155__sweep-lite-egas-ca-market-egx__runw6-sweeplite-egas-002 · archive commit: 5ba9772855872d8dc957af85e06a7ae27c732e59

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 42.28
Model range high at 53.88
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: sentiment +0.30 vs price-forecast -0.10 (spread +0.40)
- price-forecast: -0.10
- technicals: +0.15
- sentiment: +0.30
- fundamentals: -0.10
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -4.85% … +4.85%, confidence 0.30)
- week: flat +0.00% (range -12.07% … +12.07%, confidence 0.30)
- month: flat +0.00% (range -23.19% … +23.19%, confidence 0.30)
Base price: 48.08 (egx-data/egxpy_egas.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-24, base date 2026-11-26)
Witnesses stale: common date 2026-11-24 trails base date 2026-11-26.
- egx-data/egxpy_egas.csv: 48.08 on 2026-11-26
- openbb/EGAS_CA.csv: 48.58 on 2026-11-25 (stale)
- pandas-ta/indicators.csv: 48.58 on 2026-11-25 (stale)
- talib/indicators.csv: 48.58 on 2026-11-25 (stale)
- yahooquery/EGAS.CA.csv: 49.10 on 2026-11-24 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: EGAS.CA.csv_last_close, EGAS.CA.csv_last_date, rows_EGAS.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: EGAS_CA.csv_last_close, EGAS_CA.csv_last_date, rows_EGAS_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_egas.csv_last_close, egxpy_egas.csv_last_date, rows_egxpy_egas.csv, symbol, ticker
# EGX data sources for EGAS — verdict

No POUL reference material applies to EGAS; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-16 → 2026-11-26
- Latest: 2026-11-26 close 48.08

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — EGAS.CA

- Last session: **2026-11-25**
- Data used: 1931 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6423 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 49.1 |
| High | 49.5 |
| Low | 48.5 |
| Close | 48.58 |
| RSI(14) | 46.2593 |
| MACD | -0.465 |
| MACD signal | -0.7045 |
| MACD histogram | 0.2395 |
| EMA(20) | 49.2525 |
| EMA(50) | 50.9158 |
| EMA(200) | 50.0925 |
| ADX(14) | 29.6212 |
| Bollinger upper | 52.031 |
| Bollinger mid | 48.4565 |
| Bollinger lower | 44.882 |
| Bollinger %B | 0.5173 |
| ATR(14) | 2.4732 |
| Stochastic %K | 20.4608 |
| Stochastic %D | 25.7034 |

## Trend read (facts only)

- Close 48.58 is below EMA_20 49.2525 (-1.37%).
- Close 48.58 is below EMA_50 50.9158 (-4.59%).
- Close 48.58 is below EMA_200 50.0925 (-3.02%).
- RSI(14) is 46.2593, in the neutral zone (30-70).
- MACD -0.465 is above its signal line -0.7045 (histogram 0.2395).
- Price sits at %B 0.5173 of the Bollinger range (lower 44.882, mid 48.4565, upper 52.031).
- ADX(14) is 29.6212, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 20.4608 is below %D 25.7034.
- ATR(14) is 2.4732 (5.09% of the close).

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
# Fundamentals (generic) — EGAS.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T03:08:50.583630+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 144220000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 48.58000183105469.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 9001.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 312.26, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 1.89, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": -6.04, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 3.47, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 6.58, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 1.6, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.003, 

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 10
- Label counts: positive=2, negative=0, neutral=8
- Mean probabilities: positive=0.2697, negative=0.0342, neutral=0.6961

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0259 | 0.0521 | 0.9220 | Terry Palmer Obituary - The Press Democrat |
| 2 | neutral | 0.0250 | 0.1398 | 0.8352 | Vegas Golden Knights NHL Line Combinations - Daily Faceoff |
| 3 | neutral | 0.0295 | 0.0307 | 0.9398 | Las Vegas Grand Prix 2026: Race start time, how to watch, full schedule, predictions - TSN |
| 4 | neutral | 0.2069 | 0.0143 | 0.7788 | Ubisoft Reportedly Greenlights New Rainbow Six: Vegas Game After 18 Years Without a Another Installment - IGN |
| 5 | neutral | 0.0440 | 0.0136 | 0.9424 | PWHL unveils Las Vegas team name, logo as Vegas Vanguards - FOX5 Vegas |
| 6 | neutral | 0.3638 | 0.0106 | 0.6256 | EGAS, Cheiron Ink $42 Mn Natural Gas Exploration Agreement - Egypt Oil & Gas |
| 7 | positive | 0.8688 | 0.0115 | 0.1198 | Harry Reid International Airport [LAS]: Ultimate Terminal Guide - Upgraded Points |
| 8 | positive | 0.8484 | 0.0095 | 0.1421 | Egypt's EGAS And Cheiron Sign Gas Exploration Deal With Over $42M Investment Commitment - Forbes Middle East |
| 9 | neutral | 0.0315 | 0.0476 | 0.9209 | NHRA Las Vegas Results: Championship Battles Head to Pomona - Autoweek |
| 10 | neutral | 0.2534 | 0.0123 | 0.7343 | Review: This is the best steakhouse in Las Vegas, and beyond - Los Angeles Times |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 10
- Label counts: positive=1, negative=0, neutral=9
- Mean probabilities: positive=0.0896, negative=0.0003, neutral=0.9101

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0031 | 0.9969 | Terry Palmer Obituary - The Press Democrat |
| 2 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Vegas Golden Knights NHL Line Combinations - Daily Faceoff |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Las Vegas Grand Prix 2026: Race start time, how to watch, full schedule, predictions - TSN |
| 4 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Ubisoft Reportedly Greenlights New Rainbow Six: Vegas Game After 18 Years Without a Another Installment - IGN |
| 5 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | PWHL unveils Las Vegas team name, logo as Vegas Vanguards - FOX5 Vegas |
| 6 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | EGAS, Cheiron Ink $42 Mn Natural Gas Exploration Agreement - Egypt Oil & Gas |
| 7 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Harry Reid International Airport [LAS]: Ultimate Terminal Guide - Upgraded Points |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Egypt's EGAS And Cheiron Sign Gas Exploration Deal With Over $42M Investment Commitment - Forbes Middle East |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | NHRA Las Vegas Results: Championship Battles Head to Pomona - Autoweek |
| 10 | positive | Positive | 0.8955 | 0.0000 | 0.1045 | Review: This is the best steakhouse in Las Vegas, and beyond - Los Angeles Times |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 10
- Label counts: positive=4, negative=0, neutral=6
- Mean probabilities: positive=0.3995, negative=0.0004, neutral=0.6000

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0011 | 0.0007 | 0.9981 | Terry Palmer Obituary - The Press Democrat |
| 2 | neutral | neutral | 0.0022 | 0.0002 | 0.9976 | Vegas Golden Knights NHL Line Combinations - Daily Faceoff |
| 3 | neutral | neutral | 0.0002 | 0.0002 | 0.9996 | Las Vegas Grand Prix 2026: Race start time, how to watch, full schedule, predictions - TSN |
| 4 | positive | positive | 0.9976 | 0.0007 | 0.0017 | Ubisoft Reportedly Greenlights New Rainbow Six: Vegas Game After 18 Years Without a Another Installment - IGN |
| 5 | neutral | neutral | 0.0014 | 0.0003 | 0.9984 | PWHL unveils Las Vegas team name, logo as Vegas Vanguards - FOX5 Vegas |
| 6 | positive | positive | 0.9979 | 0.0007 | 0.0014 | EGAS, Cheiron Ink $42 Mn Natural Gas Exploration Agreement - Egypt Oil & Gas |
| 7 | neutral | neutral | 0.0014 | 0.0001 | 0.9985 | Harry Reid International Airport [LAS]: Ultimate Terminal Guide - Upgraded Points |
| 8 | positive | positive | 0.9981 | 0.0006 | 0.0013 | Egypt's EGAS And Cheiron Sign Gas Exploration Deal With Over $42M Investment Commitment - Forbes Middle East |
| 9 | neutral | neutral | 0.0005 | 0.0006 | 0.9989 | NHRA Las Vegas Results: Championship Battles Head to Pomona - Autoweek |
| 10 | positive | positive | 0.9950 | 0.0003 | 0.0047 | Review: This is the best steakhouse in Las Vegas, and beyond - Los Angeles Times |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — EGAS.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 49.099998474121094 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 48.832
- 2026-11-26: 48.4087
- 2026-11-29: 48.1495
- 2026-11-30: 47.6499
- 2026-12-01: 47.6815
- 2026-12-02: 47.8765
- 2026-12-03: 47.5042
- 2026-12-06: 48.1564
- 2026-12-07: 48.2725
- 2026-12-08: 47.6174
- 2026-12-09: 47.9528
- 2026-12-10: 47.7185
- 2026-12-13: 47.7957
- 2026-12-14: 47.7209
- 2026-12-15: 47.5528
- 2026-12-16: 47.4877
- 2026-12-17: 47.4366
- 2026-12-20: 47.2693
- 2026-12-21: 47.2392
- 2026-12-22: 46.9987
- 2026-12-23: 46.8287

**Change over the 21 sessions (last forecasted close vs last actual close): -4.63%**

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
News: 6 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- غازتك تعقد اجتماع جمعية عامة غير عادية بشركة إيـجـاس لتعديل بعض مواد النظام الأساسي لمواكبة التوسع في أنشطة الشركة - المستقبل اليوم
- «اتصالات مصر» و«إيجاس» تتعاونان في المدفوعات الرقمية وتطوير تطبيقات خدمات الغاز - البوابة نيوز
- «إيجاس» تطلق مبادرة Greener Today – Better Tomorrow لترشيد الطاقة وتعزيز الاستدامة - البوابة نيوز
- 42 مليون دولار لاستكشاف الغاز بشرق الإسكندرية.. اتفاقية جديدة بين "إيجاس" و"كايرون" - البوابة نيوز
- الرئيس الأسبق لـ إيجاس: أدعو لدمج وزارتي البترول والكهرباء.. وتخصيص 25% من مزيج الطاقة للفحم - عالم الطاقة
- NHRA Las Vegas Results: Championship Battles Head to Pomona - Autoweek

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/EGAS-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.05
- finbert_positive: 0.03
- multilingual_positive: 0.96
- multilingual_negative: 0.00
- translated_positive: 0.54
- translated_negative: 0.01
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- legal event: غازتك تعقد اجتماع جمعية عامة غير عادية بشركة إيـجـاس لتعديل بعض مواد النظام الأساسي لمواكب
- غازتك تعقد اجتماع جمعية عامة غير عادية بشركة إيـجـاس لتعديل بعض مواد النظام الأساسي لمواكب (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_egas.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_egas.csv: last 48.08 on 2026-11-26
- openbb/EGAS_CA.csv: last 48.58 on 2026-11-25
- pandas-ta/indicators.csv: last 48.58 on 2026-11-25
- talib/indicators.csv: last 48.58 on 2026-11-25
- yahooquery/EGAS.CA.csv: last 49.10 on 2026-11-24
- Kronos forecast: 21 points, last 46.83 at 2026-12-23

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
- recommendation-unavailable: no profiles/EGAS.CA.recommendation.json
- reaction-profile-missing: no profiles/EGAS.CA.json
- sharia-row-missing: AAOIFI EGAS.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 EGAS.CA
- sharia-row-missing: FTSE EGAS.CA
- sharia-row-missing: ISLAMICLY EGAS.CA
- sharia-row-missing: MSCI EGAS.CA
- sharia-row-missing: MSCI_M EGAS.CA
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