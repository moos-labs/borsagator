# Borsagator report — ETEL.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite ETEL.CA market=EGX · shape: sweep-lite ETEL.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/032111__sweep-lite-etel-ca-market-egx__runw6-sweeplite-etel-002 · archive commit: 26d63078d24ece96705ab9e7e6b028d364a3a275

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 119.39
Model range high at 152.41
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: sentiment +0.35 vs price-forecast +0.08 (spread +0.27)
- price-forecast: +0.08
- technicals: +0.30
- sentiment: +0.35
- fundamentals: +0.15
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -4.88% … +4.88%, confidence 0.30)
- week: flat +0.00% (range -12.15% … +12.15%, confidence 0.30)
- month: flat +0.00% (range -23.34% … +23.34%, confidence 0.30)
Base price: 135.90 (egx-data/egxpy_etel.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-24, base date 2026-11-26)
Witnesses stale: common date 2026-11-24 trails base date 2026-11-26.
- egx-data/egxpy_etel.csv: 135.90 on 2026-11-26
- openbb/ETEL_CA.csv: 139.20 on 2026-11-25 (stale)
- pandas-ta/indicators.csv: 139.20 on 2026-11-25 (stale)
- talib/indicators.csv: 139.20 on 2026-11-25 (stale)
- yahooquery/ETEL.CA.csv: 141.00 on 2026-11-24 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: ETEL.CA.csv_last_close, ETEL.CA.csv_last_date, rows_ETEL.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: ETEL_CA.csv_last_close, ETEL_CA.csv_last_date, rows_ETEL_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_etel.csv_last_close, egxpy_etel.csv_last_date, rows_egxpy_etel.csv, symbol, ticker
# EGX data sources for ETEL — verdict

No POUL reference material applies to ETEL; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-22 → 2026-11-26
- Latest: 2026-11-26 close 135.9

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — ETEL.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 5219 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 141.0 |
| High | 141.28 |
| Low | 138.51 |
| Close | 139.2 |
| RSI(14) | 55.7887 |
| MACD | 2.2101 |
| MACD signal | 1.337 |
| MACD histogram | 0.8731 |
| EMA(20) | 135.9337 |
| EMA(50) | 132.1286 |
| EMA(200) | 108.2431 |
| ADX(14) | 18.8858 |
| Bollinger upper | 148.2939 |
| Bollinger mid | 132.4445 |
| Bollinger lower | 116.5951 |
| Bollinger %B | 0.7131 |
| ATR(14) | 5.5973 |
| Stochastic %K | 70.8455 |
| Stochastic %D | 70.8131 |

## Trend read (facts only)

- Close 139.2 is above EMA_20 135.9337 (+2.40%).
- Close 139.2 is above EMA_50 132.1286 (+5.35%).
- Close 139.2 is above EMA_200 108.2431 (+28.60%).
- RSI(14) is 55.7887, in the neutral zone (30-70).
- MACD 2.2101 is above its signal line 1.337 (histogram 0.8731).
- Price sits at %B 0.7131 of the Bollinger range (lower 116.5951, mid 132.4445, upper 148.2939).
- ADX(14) is 18.8858, indicating a weak / no clear trend (< 20).
- Stochastic %K 70.8455 is above %D 70.8131.
- ATR(14) is 5.5973 (4.02% of the close).

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
# Fundamentals (generic) — ETEL.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T03:13:09.196483+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 1707000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 139.1999969482422.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 106673.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 20371.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 42.03, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 27.71, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 19.1, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 31.99, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 9.02, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 1

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 28
- Label counts: positive=9, negative=0, neutral=19
- Mean probabilities: positive=0.3404, negative=0.0327, neutral=0.6269

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.1365 | 0.0158 | 0.8477 | Telecom Egypt CEO highlights social impact of digital infrastructure through healthcare initiatives - Tech Review Africa |
| 2 | positive | 0.9086 | 0.0081 | 0.0833 | Telecom Egypt signs deals to expand paediatric dialysis, remote burn care - Dailynewsegypt |
| 3 | neutral | 0.2711 | 0.0086 | 0.7203 | Syria and Egypt explore telecom cooperation and digital infrastructure projects - Telecompaper |
| 4 | neutral | 0.0236 | 0.0452 | 0.9312 | Tamer El Mahdi - The CEO Magazine |
| 5 | neutral | 0.0554 | 0.0164 | 0.9282 | The Wedding of Shlomo Baitman and Chana Etel Derkach Has Taken Place! Mazel Tov! - djc.com.ua |
| 6 | neutral | 0.0494 | 0.0856 | 0.8650 | Grand Theft Auto VI ends 13-year wait as Egyptian gamers hunt for a place to play - Society - Egypt - Ahram Online |
| 7 | neutral | 0.0384 | 0.0461 | 0.9154 | Inside the telecom fortunes of two African billionaires - Business News Nigeria |
| 8 | positive | 0.9357 | 0.0150 | 0.0493 | Q3 2026 Results: Telecom Egypt Delivers Strong 9M 2026 Results as Strategy Execution Progresses - WebWire |
| 9 | positive | 0.9469 | 0.0201 | 0.0330 | Telecom Egypt's Net Profit Rises 44% to EGP 24.4 Billion - CairoScene |
| 10 | positive | 0.9438 | 0.0188 | 0.0374 | Telecom Egypt Revenue Rises 19% to EGP 93.6 Billion in 9M 2026 - TechAfrica News |
| 11 | neutral | 0.0307 | 0.0352 | 0.9342 | Telecom Egypt (EGS48031C016.CA) Q3 FY2026 earnings call transcript - Yahoo Finance |
| 12 | neutral | 0.0260 | 0.0971 | 0.8769 | Telecom Egypt Company Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 13 | positive | 0.9569 | 0.0151 | 0.0280 | Telecom Egypt's revenue increases 19% in Q3, EBITDA margin expands to 46% - Telecompaper |
| 14 | positive | 0.8028 | 0.0068 | 0.1904 | Telecom Egypt Partners Suez Canal Zone to Expand Digital Services - TechAfrica News |
| 15 | neutral | 0.2379 | 0.2872 | 0.4749 | SCZone brings in Telecom Egypt to end network downtime for factories and terminals across its ports and zones - EnterpriseAM |
| 16 | neutral | 0.3418 | 0.0102 | 0.6481 | Telecom Egypt showcases latest digital, tech solutions at Cairo ICT 2026 - Egyptian Gazette |
| 17 | positive | 0.7545 | 0.0074 | 0.2381 | Telecom Egypt pushes beyond connectivity - ITWeb Africa |
| 18 | neutral | 0.0703 | 0.0135 | 0.9162 | Telecom Egypt outlines 2027 financial targets - Africa Business Communities |
| 19 | positive | 0.5174 | 0.0299 | 0.4527 | Telecom Egypt approves 2027 budget with low double-digit revenue growth guidance - Telecompaper |
| 20 | neutral | 0.0759 | 0.0113 | 0.9128 | Telecom Egypt Board Approves The 2027 Budget With KPI Guidance - TradingView |
| 21 | neutral | 0.1195 | 0.0097 | 0.8708 | Egypt selects Beheira for cash-subsidy pilot starting January 2027 - Society - Egypt - Ahram Online |
| 22 | neutral | 0.0710 | 0.0152 | 0.9138 | Telecom Egypt Appoints Ashraf Abdeen as Executive Vice President, Chief International and Wholesale Officer - Telecom Review Africa |
| 23 | neutral | 0.2653 | 0.0111 | 0.7236 | Egypt committed to state asset sales after Banque du Caire’s record IPO: Madbouly - Economy - Business - Ahram Online |
| 24 | positive | 0.5686 | 0.0175 | 0.4139 | Prices for fixed-line internet packages in Egypt following the doubling of the base package - Egypt Independent |
| 25 | neutral | 0.0435 | 0.0146 | 0.9419 | Telecom news: KCOM, Ofcom, Egypt Submarine Cable, Virgin Media O2 - TelecomLead |
| 26 | neutral | 0.0590 | 0.0338 | 0.9072 | Lines Under the Sea: The Politics of the Middle East’s Data Corridors - The Cairo Review of Global Affairs |
| 27 | neutral | 0.1334 | 0.0117 | 0.8549 | The 5 Largest Telecom Groups In Arab Markets In 2026 - Forbes Middle East |
| 28 | neutral | 0.1468 | 0.0091 | 0.8441 | Egypt’s NTRA Trains 37 Participants From 15 Countries on Telecom Equipment Approval - TechAfrica News |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 28
- Label counts: positive=6, negative=1, neutral=21
- Mean probabilities: positive=0.2239, negative=0.0358, neutral=0.7403

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt CEO highlights social impact of digital infrastructure through healthcare initiatives - Tech Review Africa |
| 2 | neutral | Neutral | 0.0675 | 0.0001 | 0.9324 | Telecom Egypt signs deals to expand paediatric dialysis, remote burn care - Dailynewsegypt |
| 3 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | Syria and Egypt explore telecom cooperation and digital infrastructure projects - Telecompaper |
| 4 | neutral | Neutral | 0.0000 | 0.0032 | 0.9967 | Tamer El Mahdi - The CEO Magazine |
| 5 | neutral | Neutral | 0.0000 | 0.0011 | 0.9989 | The Wedding of Shlomo Baitman and Chana Etel Derkach Has Taken Place! Mazel Tov! - djc.com.ua |
| 6 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Grand Theft Auto VI ends 13-year wait as Egyptian gamers hunt for a place to play - Society - Egypt - Ahram Online |
| 7 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Inside the telecom fortunes of two African billionaires - Business News Nigeria |
| 8 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Q3 2026 Results: Telecom Egypt Delivers Strong 9M 2026 Results as Strategy Execution Progresses - WebWire |
| 9 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Telecom Egypt's Net Profit Rises 44% to EGP 24.4 Billion - CairoScene |
| 10 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Telecom Egypt Revenue Rises 19% to EGP 93.6 Billion in 9M 2026 - TechAfrica News |
| 11 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt (EGS48031C016.CA) Q3 FY2026 earnings call transcript - Yahoo Finance |
| 12 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt Company Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 13 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Telecom Egypt's revenue increases 19% in Q3, EBITDA margin expands to 46% - Telecompaper |
| 14 | neutral | Neutral | 0.0045 | 0.0000 | 0.9955 | Telecom Egypt Partners Suez Canal Zone to Expand Digital Services - TechAfrica News |
| 15 | negative | Negative | 0.0000 | 0.9968 | 0.0032 | SCZone brings in Telecom Egypt to end network downtime for factories and terminals across its ports and zones - EnterpriseAM |
| 16 | neutral | Neutral | 0.0143 | 0.0000 | 0.9857 | Telecom Egypt showcases latest digital, tech solutions at Cairo ICT 2026 - Egyptian Gazette |
| 17 | neutral | Neutral | 0.2171 | 0.0006 | 0.7824 | Telecom Egypt pushes beyond connectivity - ITWeb Africa |
| 18 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt outlines 2027 financial targets - Africa Business Communities |
| 19 | positive | Positive | 0.9923 | 0.0000 | 0.0077 | Telecom Egypt approves 2027 budget with low double-digit revenue growth guidance - Telecompaper |
| 20 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt Board Approves The 2027 Budget With KPI Guidance - TradingView |
| 21 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Egypt selects Beheira for cash-subsidy pilot starting January 2027 - Society - Egypt - Ahram Online |
| 22 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt Appoints Ashraf Abdeen as Executive Vice President, Chief International and Wholesale Officer - Telecom Review Africa |
| 23 | neutral | Neutral | 0.0002 | 0.0001 | 0.9998 | Egypt committed to state asset sales after Banque du Caire’s record IPO: Madbouly - Economy - Business - Ahram Online |
| 24 | positive | Positive | 0.9726 | 0.0000 | 0.0274 | Prices for fixed-line internet packages in Egypt following the doubling of the base package - Egypt Independent |
| 25 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom news: KCOM, Ofcom, Egypt Submarine Cable, Virgin Media O2 - TelecomLead |
| 26 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Lines Under the Sea: The Politics of the Middle East’s Data Corridors - The Cairo Review of Global Affairs |
| 27 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | The 5 Largest Telecom Groups In Arab Markets In 2026 - Forbes Middle East |
| 28 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Egypt’s NTRA Trains 37 Participants From 15 Countries on Telecom Equipment Approval - TechAfrica News |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 28
- Label counts: positive=15, negative=1, neutral=12
- Mean probabilities: positive=0.5255, negative=0.0356, neutral=0.4389

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0017 | 0.0001 | 0.9982 | Telecom Egypt CEO highlights social impact of digital infrastructure through healthcare initiatives - Tech Review Africa |
| 2 | positive | positive | 0.9981 | 0.0006 | 0.0013 | Telecom Egypt signs deals to expand paediatric dialysis, remote burn care - Dailynewsegypt |
| 3 | positive | positive | 0.9957 | 0.0003 | 0.0040 | Syria and Egypt explore telecom cooperation and digital infrastructure projects - Telecompaper |
| 4 | neutral | neutral | 0.0007 | 0.0004 | 0.9989 | Tamer El Mahdi - The CEO Magazine |
| 5 | neutral | neutral | 0.1061 | 0.0005 | 0.8933 | The Wedding of Shlomo Baitman and Chana Etel Derkach Has Taken Place! Mazel Tov! - djc.com.ua |
| 6 | positive | positive | 0.9735 | 0.0004 | 0.0262 | Grand Theft Auto VI ends 13-year wait as Egyptian gamers hunt for a place to play - Society - Egypt - Ahram Online |
| 7 | neutral | neutral | 0.0018 | 0.0003 | 0.9979 | Inside the telecom fortunes of two African billionaires - Business News Nigeria |
| 8 | positive | positive | 0.9984 | 0.0007 | 0.0010 | Q3 2026 Results: Telecom Egypt Delivers Strong 9M 2026 Results as Strategy Execution Progresses - WebWire |
| 9 | positive | positive | 0.9982 | 0.0008 | 0.0010 | Telecom Egypt's Net Profit Rises 44% to EGP 24.4 Billion - CairoScene |
| 10 | positive | positive | 0.9982 | 0.0009 | 0.0009 | Telecom Egypt Revenue Rises 19% to EGP 93.6 Billion in 9M 2026 - TechAfrica News |
| 11 | neutral | neutral | 0.0004 | 0.0002 | 0.9995 | Telecom Egypt (EGS48031C016.CA) Q3 FY2026 earnings call transcript - Yahoo Finance |
| 12 | neutral | neutral | 0.0008 | 0.0002 | 0.9990 | Telecom Egypt Company Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 13 | positive | positive | 0.9982 | 0.0008 | 0.0010 | Telecom Egypt's revenue increases 19% in Q3, EBITDA margin expands to 46% - Telecompaper |
| 14 | positive | positive | 0.9978 | 0.0005 | 0.0016 | Telecom Egypt Partners Suez Canal Zone to Expand Digital Services - TechAfrica News |
| 15 | positive | positive | 0.9973 | 0.0004 | 0.0023 | SCZone brings in Telecom Egypt to end network downtime for factories and terminals across its ports and zones - EnterpriseAM |
| 16 | neutral | neutral | 0.0039 | 0.0001 | 0.9960 | Telecom Egypt showcases latest digital, tech solutions at Cairo ICT 2026 - Egyptian Gazette |
| 17 | positive | positive | 0.9966 | 0.0003 | 0.0031 | Telecom Egypt pushes beyond connectivity - ITWeb Africa |
| 18 | neutral | neutral | 0.0588 | 0.0002 | 0.9410 | Telecom Egypt outlines 2027 financial targets - Africa Business Communities |
| 19 | negative | negative | 0.0011 | 0.9837 | 0.0152 | Telecom Egypt approves 2027 budget with low double-digit revenue growth guidance - Telecompaper |
| 20 | positive | positive | 0.9976 | 0.0005 | 0.0019 | Telecom Egypt Board Approves The 2027 Budget With KPI Guidance - TradingView |
| 21 | positive | positive | 0.9907 | 0.0002 | 0.0091 | Egypt selects Beheira for cash-subsidy pilot starting January 2027 - Society - Egypt - Ahram Online |
| 22 | neutral | neutral | 0.0006 | 0.0001 | 0.9992 | Telecom Egypt Appoints Ashraf Abdeen as Executive Vice President, Chief International and Wholesale Officer - Telecom Review Africa |
| 23 | positive | positive | 0.9979 | 0.0006 | 0.0015 | Egypt committed to state asset sales after Banque du Caire’s record IPO: Madbouly - Economy - Business - Ahram Online |
| 24 | positive | positive | 0.5244 | 0.0009 | 0.4747 | Prices for fixed-line internet packages in Egypt following the doubling of the base package - Egypt Independent |
| 25 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | Telecom news: KCOM, Ofcom, Egypt Submarine Cable, Virgin Media O2 - TelecomLead |
| 26 | neutral | neutral | 0.0005 | 0.0002 | 0.9993 | Lines Under the Sea: The Politics of the Middle East’s Data Corridors - The Cairo Review of Global Affairs |
| 27 | neutral | neutral | 0.0796 | 0.0009 | 0.9195 | The 5 Largest Telecom Groups In Arab Markets In 2026 - Forbes Middle East |
| 28 | positive | positive | 0.9965 | 0.0004 | 0.0031 | Egypt’s NTRA Trains 37 Participants From 15 Countries on Telecom Equipment Approval - TechAfrica News |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 141.0 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 140.6295
- 2026-11-26: 140.8082
- 2026-11-29: 141.8722
- 2026-11-30: 142.6152
- 2026-12-01: 142.6441
- 2026-12-02: 143.1198
- 2026-12-03: 144.1849
- 2026-12-06: 144.2824
- 2026-12-07: 143.8088
- 2026-12-08: 144.4756
- 2026-12-09: 144.4381
- 2026-12-10: 144.9977
- 2026-12-13: 145.0571
- 2026-12-14: 143.7168
- 2026-12-15: 143.4585
- 2026-12-16: 142.7545
- 2026-12-17: 142.3541
- 2026-12-20: 142.6931
- 2026-12-21: 140.8827
- 2026-12-22: 140.3548
- 2026-12-23: 138.7034

**Change over the 21 sessions (last forecasted close vs last actual close): -1.63%**

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
News: 40 · disclosures: 10 · identity scheme: resolved_url|title-date-hash
- Fact box: Warraq ring road accident draws EGP 318 million in donations - Society - Egypt - Ahram Online
- Egypt mobile operators to match donations for Warraq fire victims - Society - Egypt - Ahram Online
- المصرية للاتصالات تنعى ضحايا حادث الوراق وتضاعف تبرعات WE Pay لدعم المصابين | أموال الغد - اخبارك نت
- المصرية للاتصالات تضاعف تبرعات عملائها عبر WE Pay لدعم ضحايا ومصابي حريق الوراق - مجلة أرقام
- «المصرية للاتصالات» تضاعف تبرعات عملاء «WE PAY» لدعم مصابي حادث دائري الوراق - followict
- «المصرية للاتصالات» تتحمل تكاليف الأدوية والمستلزمات الطبية لمصابي حادث الوراق - جريدة المال
- وزير الاتصالات يطلق مبادرة لمضاعفة تبرعات المواطنين بالتعاون مع شركات المحمول الأربعة.. جنيه المواطن قصاد جنيه من الشركة.. والمصرية للاتصالات تساهم فى توفير الأدوية والأجهزة والمستلزمات اللازمة للمستشفيات - اليوم السابع
- المصرية للاتصالات تضاعف تبرعات عملائها عبر WE Pay لدعم مصابي حادث الوراق - موقع الموقع
- المصرية للاتصالات توفر الأدوية والأجهزة الضرورية للمستشفيات بعد حادث الدائري - الاستاد الرياضي
- المصرية للاتصالات تضاعف تبرعات عملاء WE Pay لدعم ضحايا حادث دائري الوراق - الأسبوع
- المصرية للاتصالات تضاعف تبرعات عملائها لدعم مصابي حادث الطريق الدائري - صدى البلد
- المصرية للاتصالات تنعى ضحايا حريق دائري الوراق - فيتو
- لدعم ضحايا حادث دائري الوراق.. المصرية للاتصالات تضاعف تبرعات عملائها عبر WE Pay بثلاثة مستشفيات وتمد وزارة الصحة بالمستلزمات الطبية اللازمة - أهل مصر
- المصرية للاتصالات تنعى ضحايا حادث الوراق وتضاعف تبرعات WE Pay لدعم المصابين - اليوم السابع
- المصرية للاتصالات تضاعف تبرعات عملائها عبر WE Pay لدعم ضحايا حريق الوراق - جريدة النهار المصرية
- رئيسة «المصرية للاتصالات» تحدد مهارات المستقبل: التفكير النقدي والتواصل الإنساني سر التميز بعصر الأتمتة - بوابة الغد
- Egypt signs cooperation protocol to establish AI-powered Educational Republic platform - Tech Review Africa
- «المصرية للاتصالات» تضاعف تبرعات عملاء «WE PAY» لصالح مصابي حادث الطريق الدائري - بوابة التكنولوجيا المالية
- Telecom Egypt CEO highlights social impact of digital infrastructure through healthcare initiatives - Tech Review Africa
- Orange Egypt Doubles Customer Donations to Ahl Masr Burn Hospital Through Orange Cash - Sponsored - Advertising - Ahram Online
- هل تقود البنية التحتية الرقمية سهم المصرية إلى مستويات جديدة؟ - https://www.youlyou.com/
- انطلاق النسخة الـ5 من«قمة المرأة المصرية 2026» بحضور وزيرالمالية - الأخبار المسائى
- العنوان: المصرية للاتصالات (ETEL.CA) قرارات مجلس ادارة الشركةاسم الشركة: المصرية للاتصالاتكود الترقيم الدولي: EGS48031C016كود رويترز: - Mubasher
- بيان من المصرية للاتصالات (ETEL.CA) بخصوص إطارها التنظيمي
- المصرية للاتصالات (ETEL.CA) - تقرير الجهاز المركزي للمحاسبات
- بيان من المصرية للاتصالات (ETEL.CA) بخصوص نتائج أعمال الشركة
- المصرية للاتصالات (ETEL.CA) تعلن نتائج أعمالها المجمعة عن الفترة: من 01/01/2026 إلى 30/09/2026
- المصرية للاتصالات (ETEL.CA) تعلن نتائج أعمالها المستقلة عن الفترة: من 01/01/2026 إلى 30/09/2026
- المصرية للاتصالات (ETEL.CA) - قرارات مجلس إدارة الشركة
- بيان من المصرية للاتصالات (ETEL.CA) بخصوص أحد الأخبار المنشورة
- بيان من المصرية للاتصالات (ETEL.CA) بخصوص إطارها التنظيمي
- المصرية للاتصالات (ETEL.CA) - قرارات مجلس إدارة الشركة

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/ETEL-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.08
- finbert_positive: 0.39
- multilingual_positive: 0.69
- multilingual_negative: 0.01
- translated_positive: 0.33
- translated_negative: 0.03
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- management event: Telecom Egypt CEO highlights social impact of digital infrastructure through healthcare in
- earnings event: قفزة قياسية.. أرباح المصرية للاتصالات WE تصعد لـ 24.4 مليار جنيه - شبكة تواصل الإخبارية
- earnings event: هل أصبح سهم المصرية للاتصالات أكثر جاذبية بعد نمو الأرباح وتراجع المديونية؟ - www.youlyou.
- Telecom Egypt CEO highlights social impact of digital infrastructure through healthcare in (truncated title — see the archived news file for full text)
- قفزة قياسية.. أرباح المصرية للاتصالات WE تصعد لـ 24.4 مليار جنيه - شبكة تواصل الإخبارية (truncated title — see the archived news file for full text)
- هل أصبح سهم المصرية للاتصالات أكثر جاذبية بعد نمو الأرباح وتراجع المديونية؟ - www.youlyou. (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_etel.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_etel.csv: last 135.90 on 2026-11-26
- openbb/ETEL_CA.csv: last 139.20 on 2026-11-25
- pandas-ta/indicators.csv: last 139.20 on 2026-11-25
- talib/indicators.csv: last 139.20 on 2026-11-25
- yahooquery/ETEL.CA.csv: last 141.00 on 2026-11-24
- Kronos forecast: 21 points, last 138.70 at 2026-12-23

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
- recommendation-unavailable: no profiles/ETEL.CA.recommendation.json
- reaction-profile-missing: no profiles/ETEL.CA.json
- sharia-row-missing: AAOIFI ETEL.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 ETEL.CA
- sharia-row-missing: FTSE ETEL.CA
- sharia-row-missing: ISLAMICLY ETEL.CA
- sharia-row-missing: MSCI ETEL.CA
- sharia-row-missing: MSCI_M ETEL.CA
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