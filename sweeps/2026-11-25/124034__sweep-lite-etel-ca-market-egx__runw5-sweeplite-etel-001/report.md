# Borsagator report — ETEL.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite ETEL.CA market=EGX · shape: sweep-lite ETEL.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/124034__sweep-lite-etel-ca-market-egx__runw5-sweeplite-etel-001 · archive commit: cf521e842e9644c29766522f391a67bf93b8a6e0

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 128.18
Model range high at 155.64
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: sentiment +0.36 vs price-forecast +0.05 (spread +0.32)
- price-forecast: +0.05
- technicals: +0.30
- sentiment: +0.36
- fundamentals: +0.15
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.068, technicals ×0.679
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.25% (range -5.55% … +6.04%, confidence 0.30)
- week: up +1.29% (range -8.51% … +11.09%, confidence 0.30)
- month: up +1.55% (range -19.57% … +22.68%, confidence 0.30)
Base price: 140.10 (egx-data/egxpy_etel.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_etel.csv: 140.10 on 2026-11-25
- openbb/ETEL_CA.csv: 141.00 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 141.00 on 2026-11-24 (stale)
- talib/indicators.csv: 141.00 on 2026-11-24 (stale)
- yahooquery/ETEL.CA.csv: 139.98 on 2026-11-23 (stale)

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
- Rows: 3000 · Range: 2014-07-21 → 2026-11-25
- Latest: 2026-11-25 close 140.1

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — ETEL.CA

- Last session: **2026-11-24**
- Data used: 1929 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 5218 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 139.98 |
| High | 142.5 |
| Low | 139.5 |
| Close | 141.0 |
| RSI(14) | 58.572 |
| MACD | 2.2083 |
| MACD signal | 1.1188 |
| MACD histogram | 1.0896 |
| EMA(20) | 135.5899 |
| EMA(50) | 131.84 |
| EMA(200) | 107.932 |
| ADX(14) | 19.6861 |
| Bollinger upper | 147.5444 |
| Bollinger mid | 131.8045 |
| Bollinger lower | 116.0646 |
| Bollinger %B | 0.7921 |
| ATR(14) | 5.8148 |
| Stochastic %K | 72.1779 |
| Stochastic %D | 71.3132 |

## Trend read (facts only)

- Close 141.0 is above EMA_20 135.5899 (+3.99%).
- Close 141.0 is above EMA_50 131.84 (+6.95%).
- Close 141.0 is above EMA_200 107.932 (+30.64%).
- RSI(14) is 58.572, in the neutral zone (30-70).
- MACD 2.2083 is above its signal line 1.1188 (histogram 1.0896).
- Price sits at %B 0.7921 of the Bollinger range (lower 116.0646, mid 131.8045, upper 147.5444).
- ADX(14) is 19.6861, indicating a weak / no clear trend (< 20).
- Stochastic %K 72.1779 is above %D 71.3132.
- ATR(14) is 5.8148 (4.12% of the close).

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
# Fundamentals (generic) — ETEL.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T12:33:32.707592+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 1707000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 141.0.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 106673.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 20371.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 42.03, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 27.71, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 19.1, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 31.99, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 9.02, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 1

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 27
- Label counts: positive=10, negative=0, neutral=17
- Mean probabilities: positive=0.3681, negative=0.0308, neutral=0.6012

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.2711 | 0.0086 | 0.7203 | Syria and Egypt explore telecom cooperation and digital infrastructure projects - Telecompaper |
| 2 | neutral | 0.0236 | 0.0452 | 0.9312 | Tamer El Mahdi - The CEO Magazine |
| 3 | neutral | 0.0554 | 0.0164 | 0.9282 | The Wedding of Shlomo Baitman and Chana Etel Derkach Has Taken Place! Mazel Tov! - djc.com.ua |
| 4 | neutral | 0.0283 | 0.0387 | 0.9330 | Telecom Egypt SAE (CAI:ETEL) (Q3 2026) Earnings Call Highlights: - GuruFocus |
| 5 | positive | 0.9357 | 0.0150 | 0.0493 | Q3 2026 Results: Telecom Egypt Delivers Strong 9M 2026 Results as Strategy Execution Progresses - WebWire |
| 6 | positive | 0.9469 | 0.0201 | 0.0330 | Telecom Egypt's Net Profit Rises 44% to EGP 24.4 Billion - CairoScene |
| 7 | positive | 0.9438 | 0.0188 | 0.0374 | Telecom Egypt Revenue Rises 19% to EGP 93.6 Billion in 9M 2026 - TechAfrica News |
| 8 | neutral | 0.1159 | 0.0120 | 0.8722 | Telecom Egypt Joins MSCI Global Standard Index for Emerging Markets - Sada Elbalad English |
| 9 | neutral | 0.0307 | 0.0352 | 0.9342 | Telecom Egypt (EGS48031C016.CA) Q3 FY2026 earnings call transcript - Yahoo Finance |
| 10 | positive | 0.9561 | 0.0177 | 0.0263 | ETEL: Revenue, profit, and cash flow surged as digital infrastructure investment advanced - TradingView |
| 11 | neutral | 0.0260 | 0.0971 | 0.8769 | Telecom Egypt Company Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 12 | neutral | 0.0340 | 0.0157 | 0.9503 | REG - Telecom Egypt S.A.E - TE Announced Q3 2026 FS & Earnings Release - TradingView |
| 13 | positive | 0.9569 | 0.0151 | 0.0280 | Telecom Egypt's revenue increases 19% in Q3, EBITDA margin expands to 46% - Telecompaper |
| 14 | neutral | 0.0576 | 0.0156 | 0.9268 | Arab Contractors FC vs WE SC live score, H2H and lineups - Sofascore |
| 15 | positive | 0.8028 | 0.0068 | 0.1904 | Telecom Egypt Partners Suez Canal Zone to Expand Digital Services - TechAfrica News |
| 16 | neutral | 0.2379 | 0.2872 | 0.4749 | SCZone brings in Telecom Egypt to end network downtime for factories and terminals across its ports and zones - EnterpriseAM |
| 17 | positive | 0.7545 | 0.0074 | 0.2381 | Telecom Egypt pushes beyond connectivity - ITWeb Africa |
| 18 | positive | 0.9089 | 0.0092 | 0.0818 | SCZone, Telecom Egypt sign deal to upgrade digital services - Egyptian Gazette |
| 19 | neutral | 0.0703 | 0.0135 | 0.9162 | Telecom Egypt outlines 2027 financial targets - Africa Business Communities |
| 20 | neutral | 0.0759 | 0.0113 | 0.9128 | Telecom Egypt Board Approves The 2027 Budget With KPI Guidance - TradingView |
| 21 | positive | 0.5174 | 0.0299 | 0.4527 | Telecom Egypt approves 2027 budget with low double-digit revenue growth guidance - Telecompaper |
| 22 | neutral | 0.0710 | 0.0152 | 0.9138 | Telecom Egypt Appoints Ashraf Abdeen as Executive Vice President, Chief International and Wholesale Officer - Telecom Review Africa |
| 23 | neutral | 0.2653 | 0.0111 | 0.7236 | Egypt committed to state asset sales after Banque du Caire’s record IPO: Madbouly - Economy - Business - Ahram Online |
| 24 | positive | 0.5686 | 0.0175 | 0.4139 | Prices for fixed-line internet packages in Egypt following the doubling of the base package - Egypt Independent |
| 25 | neutral | 0.0435 | 0.0146 | 0.9419 | Telecom news: KCOM, Ofcom, Egypt Submarine Cable, Virgin Media O2 - TelecomLead |
| 26 | neutral | 0.1063 | 0.0242 | 0.8694 | Banque du Caire’s EGP 36.4 bln flotation puts Egypt’s landmark IPOs in perspective - Economy - Business - Ahram Online |
| 27 | neutral | 0.1334 | 0.0117 | 0.8549 | The 5 Largest Telecom Groups In Arab Markets In 2026 - Forbes Middle East |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 27
- Label counts: positive=7, negative=1, neutral=19
- Mean probabilities: positive=0.2662, negative=0.0371, neutral=0.6967

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | Syria and Egypt explore telecom cooperation and digital infrastructure projects - Telecompaper |
| 2 | neutral | Neutral | 0.0000 | 0.0032 | 0.9967 | Tamer El Mahdi - The CEO Magazine |
| 3 | neutral | Neutral | 0.0000 | 0.0011 | 0.9989 | The Wedding of Shlomo Baitman and Chana Etel Derkach Has Taken Place! Mazel Tov! - djc.com.ua |
| 4 | neutral | Neutral | 0.0004 | 0.0000 | 0.9996 | Telecom Egypt SAE (CAI:ETEL) (Q3 2026) Earnings Call Highlights: - GuruFocus |
| 5 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Q3 2026 Results: Telecom Egypt Delivers Strong 9M 2026 Results as Strategy Execution Progresses - WebWire |
| 6 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Telecom Egypt's Net Profit Rises 44% to EGP 24.4 Billion - CairoScene |
| 7 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Telecom Egypt Revenue Rises 19% to EGP 93.6 Billion in 9M 2026 - TechAfrica News |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt Joins MSCI Global Standard Index for Emerging Markets - Sada Elbalad English |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt (EGS48031C016.CA) Q3 FY2026 earnings call transcript - Yahoo Finance |
| 10 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | ETEL: Revenue, profit, and cash flow surged as digital infrastructure investment advanced - TradingView |
| 11 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt Company Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 12 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | REG - Telecom Egypt S.A.E - TE Announced Q3 2026 FS & Earnings Release - TradingView |
| 13 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Telecom Egypt's revenue increases 19% in Q3, EBITDA margin expands to 46% - Telecompaper |
| 14 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Arab Contractors FC vs WE SC live score, H2H and lineups - Sofascore |
| 15 | neutral | Neutral | 0.0045 | 0.0000 | 0.9955 | Telecom Egypt Partners Suez Canal Zone to Expand Digital Services - TechAfrica News |
| 16 | negative | Negative | 0.0000 | 0.9968 | 0.0032 | SCZone brings in Telecom Egypt to end network downtime for factories and terminals across its ports and zones - EnterpriseAM |
| 17 | neutral | Neutral | 0.2171 | 0.0006 | 0.7824 | Telecom Egypt pushes beyond connectivity - ITWeb Africa |
| 18 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | SCZone, Telecom Egypt sign deal to upgrade digital services - Egyptian Gazette |
| 19 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt outlines 2027 financial targets - Africa Business Communities |
| 20 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt Board Approves The 2027 Budget With KPI Guidance - TradingView |
| 21 | positive | Positive | 0.9923 | 0.0000 | 0.0077 | Telecom Egypt approves 2027 budget with low double-digit revenue growth guidance - Telecompaper |
| 22 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom Egypt Appoints Ashraf Abdeen as Executive Vice President, Chief International and Wholesale Officer - Telecom Review Africa |
| 23 | neutral | Neutral | 0.0002 | 0.0001 | 0.9998 | Egypt committed to state asset sales after Banque du Caire’s record IPO: Madbouly - Economy - Business - Ahram Online |
| 24 | positive | Positive | 0.9726 | 0.0000 | 0.0274 | Prices for fixed-line internet packages in Egypt following the doubling of the base package - Egypt Independent |
| 25 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Telecom news: KCOM, Ofcom, Egypt Submarine Cable, Virgin Media O2 - TelecomLead |
| 26 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | Banque du Caire’s EGP 36.4 bln flotation puts Egypt’s landmark IPOs in perspective - Economy - Business - Ahram Online |
| 27 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | The 5 Largest Telecom Groups In Arab Markets In 2026 - Forbes Middle East |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 27
- Label counts: positive=14, negative=1, neutral=12
- Mean probabilities: positive=0.5093, negative=0.0369, neutral=0.4538

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9957 | 0.0003 | 0.0040 | Syria and Egypt explore telecom cooperation and digital infrastructure projects - Telecompaper |
| 2 | neutral | neutral | 0.0007 | 0.0004 | 0.9989 | Tamer El Mahdi - The CEO Magazine |
| 3 | neutral | neutral | 0.1061 | 0.0005 | 0.8933 | The Wedding of Shlomo Baitman and Chana Etel Derkach Has Taken Place! Mazel Tov! - djc.com.ua |
| 4 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | Telecom Egypt SAE (CAI:ETEL) (Q3 2026) Earnings Call Highlights: - GuruFocus |
| 5 | positive | positive | 0.9984 | 0.0007 | 0.0010 | Q3 2026 Results: Telecom Egypt Delivers Strong 9M 2026 Results as Strategy Execution Progresses - WebWire |
| 6 | positive | positive | 0.9982 | 0.0008 | 0.0010 | Telecom Egypt's Net Profit Rises 44% to EGP 24.4 Billion - CairoScene |
| 7 | positive | positive | 0.9982 | 0.0009 | 0.0009 | Telecom Egypt Revenue Rises 19% to EGP 93.6 Billion in 9M 2026 - TechAfrica News |
| 8 | positive | positive | 0.9975 | 0.0006 | 0.0019 | Telecom Egypt Joins MSCI Global Standard Index for Emerging Markets - Sada Elbalad English |
| 9 | neutral | neutral | 0.0004 | 0.0002 | 0.9995 | Telecom Egypt (EGS48031C016.CA) Q3 FY2026 earnings call transcript - Yahoo Finance |
| 10 | positive | positive | 0.9983 | 0.0008 | 0.0010 | ETEL: Revenue, profit, and cash flow surged as digital infrastructure investment advanced - TradingView |
| 11 | neutral | neutral | 0.0008 | 0.0002 | 0.9990 | Telecom Egypt Company Reports Earnings Results for the Third Quarter and Nine Months Ended September 30, 2026 - www.marketscreener.com |
| 12 | neutral | neutral | 0.0057 | 0.0001 | 0.9942 | REG - Telecom Egypt S.A.E - TE Announced Q3 2026 FS & Earnings Release - TradingView |
| 13 | positive | positive | 0.9982 | 0.0008 | 0.0010 | Telecom Egypt's revenue increases 19% in Q3, EBITDA margin expands to 46% - Telecompaper |
| 14 | neutral | neutral | 0.0006 | 0.0003 | 0.9992 | Arab Contractors FC vs WE SC live score, H2H and lineups - Sofascore |
| 15 | positive | positive | 0.9978 | 0.0005 | 0.0016 | Telecom Egypt Partners Suez Canal Zone to Expand Digital Services - TechAfrica News |
| 16 | positive | positive | 0.9973 | 0.0004 | 0.0023 | SCZone brings in Telecom Egypt to end network downtime for factories and terminals across its ports and zones - EnterpriseAM |
| 17 | positive | positive | 0.9966 | 0.0003 | 0.0031 | Telecom Egypt pushes beyond connectivity - ITWeb Africa |
| 18 | positive | positive | 0.9979 | 0.0006 | 0.0015 | SCZone, Telecom Egypt sign deal to upgrade digital services - Egyptian Gazette |
| 19 | neutral | neutral | 0.0588 | 0.0002 | 0.9410 | Telecom Egypt outlines 2027 financial targets - Africa Business Communities |
| 20 | positive | positive | 0.9976 | 0.0005 | 0.0019 | Telecom Egypt Board Approves The 2027 Budget With KPI Guidance - TradingView |
| 21 | negative | negative | 0.0011 | 0.9837 | 0.0152 | Telecom Egypt approves 2027 budget with low double-digit revenue growth guidance - Telecompaper |
| 22 | neutral | neutral | 0.0006 | 0.0001 | 0.9992 | Telecom Egypt Appoints Ashraf Abdeen as Executive Vice President, Chief International and Wholesale Officer - Telecom Review Africa |
| 23 | positive | positive | 0.9979 | 0.0006 | 0.0015 | Egypt committed to state asset sales after Banque du Caire’s record IPO: Madbouly - Economy - Business - Ahram Online |
| 24 | positive | positive | 0.5244 | 0.0009 | 0.4747 | Prices for fixed-line internet packages in Egypt following the doubling of the base package - Egypt Independent |
| 25 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | Telecom news: KCOM, Ofcom, Egypt Submarine Cable, Virgin Media O2 - TelecomLead |
| 26 | neutral | neutral | 0.0024 | 0.0001 | 0.9975 | Banque du Caire’s EGP 36.4 bln flotation puts Egypt’s landmark IPOs in perspective - Economy - Business - Ahram Online |
| 27 | neutral | neutral | 0.0796 | 0.0009 | 0.9195 | The 5 Largest Telecom Groups In Arab Markets In 2026 - Forbes Middle East |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — ETEL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 139.97999572753906 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 139.8627
- 2026-11-25: 139.0486
- 2026-11-26: 139.4409
- 2026-11-29: 139.8805
- 2026-11-30: 141.5168
- 2026-12-01: 140.379
- 2026-12-02: 140.4429
- 2026-12-03: 141.141
- 2026-12-06: 142.0935
- 2026-12-07: 141.3077
- 2026-12-08: 141.5857
- 2026-12-09: 140.9499
- 2026-12-10: 142.3571
- 2026-12-13: 142.6683
- 2026-12-14: 142.1299
- 2026-12-15: 142.6083
- 2026-12-16: 142.3264
- 2026-12-17: 142.4471
- 2026-12-20: 139.8626
- 2026-12-21: 139.8356
- 2026-12-22: 141.463

**Change over the 21 sessions (last forecasted close vs last actual close): +1.06%**

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
News: 40 · disclosures: 11 · identity scheme: resolved_url|title-date-hash
- Syria and Egypt explore telecom cooperation and digital infrastructure projects - Telecompaper
- Tamer El Mahdi - The CEO Magazine
- شكوي وبيان رسمي من الترسانة ضد حكم مباراة المصرية للاتصالات.. ماذا حدث؟ - Masrawy
- 6 أسهم ترتفع وتخالف الاتجاه الهابط لبورصة مصر.. منها المصرية للاتصالات - Mubasher
- سلة الزمالك تفوز على المصرية للاتصالات في دوري المرتبط - الموقع الرسمي للنادي الزمالك
- نتيجة مباراة ناشئو سلة الزمالك تحت 16 سنة أمام المصرية للاتصالات في دوري المرتبط - الموقع الرسمي للنادي الزمالك
- سلة الزمالك رجال تواجه المصرية للاتصالات غدًا في دوري المرتبط - الموقع الرسمي للنادي الزمالك
- ناشئين سلة الزمالك يواجهون المصرية للاتصالات غدًا في دوري المرتبط - الموقع الرسمي للنادي الزمالك
- المصرية للاتصالات يهزم الترسانة في عقر داره ويرتقي بجدول الترتيب - Masrawy
- المصرية للاتصالات: إنشاء شبكة ألياف ضوئية تغطي مدينة نيفيرا بالكامل - بوابة الشروق
- المصرية للاتصالات: نعمل مع مستثمري نيفيرا لتقديم حلول تكنولوجية متكاملة - اليوم السابع
- مدينة ذكية بخدمات متكاملة| المصرية للاتصالات تقود التحول التكنولوجي في «نيفيرا» - بوابة أخبار اليوم الإلكترونية
- المصرية للاتصالات تتولى إنشاء شبكة ألياف ضوئية وتقديم خدمات رقمية بمشروع «نيفيرا» - جريدة حابي
- من الألياف الضوئية إلى الحوسبة السحابية.. المصرية للاتصالات تبني منظومة رقمية متكاملة في «نيفيرا» - اليوم السابع
- المصرية للاتصالات تتولى البنية الرقمية لمشروع نيفيرا وتربطه بأوروبا وأمريكا - Masrawy
- «المصرية للاتصالات» شريك التكنولوجيا لمشروع «نيفيرا مصر» - المصري اليوم
- كيف تخطط المصرية للاتصالات للتحول من صافي الدين إلى صافي النقدية خلال 5 سنوات؟ - اليوم السابع
- 700 مليون دولار سنويًا.. كيف تؤمن المصرية للاتصالات احتياجاتها الدولارية؟ - اليوم السابع
- Telecom Egypt SAE (CAI:ETEL) (Q3 2026) Earnings Call Highlights: - GuruFocus
- «المصرية للاتصالات» تخفض أرصدة القروض والتسهيلات الائتمانية إلى 56.7 مليار جنيه بنهاية سبتمبر 2026 - جريدة المال
- Q3 2026 Results: Telecom Egypt Delivers Strong 9M 2026 Results as Strategy Execution Progresses - WebWire
- بالأرقام.. المصرية للاتصالات من طفرة الأرباح إلى تطوير البنية التحتية وقفزة السهم 150% - اليوم السابع
- العنوان: المصرية للاتصالات (ETEL.CA) قرارات مجلس ادارة الشركةاسم الشركة: المصرية للاتصالاتكود الترقيم الدولي: EGS48031C016كود رويترز: - Mubasher
- العنوان : المصرية للاتصالات (ETEL.CA) - بيان من الشركةاسم الشركة: المصرية للاتصالاتكود الترقيم الدولي: EGS48031C016كود رويترز: ETEL. - Mubasher
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
- finbert_negative: 0.02
- finbert_positive: 0.47
- multilingual_positive: 0.57
- multilingual_negative: 0.06
- translated_positive: 0.34
- translated_negative: 0.08
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- management event: Tamer El Mahdi - The CEO Magazine
- earnings event: شكوي وبيان رسمي من الترسانة ضد حكم مباراة المصرية للاتصالات.. ماذا حدث؟ - Masrawy
- Tamer El Mahdi - The CEO Magazine (truncated title — see the archived news file for full text)
- شكوي وبيان رسمي من الترسانة ضد حكم مباراة المصرية للاتصالات.. ماذا حدث؟ - Masrawy (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_etel.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_etel.csv: last 140.10 on 2026-11-25
- openbb/ETEL_CA.csv: last 141.00 on 2026-11-24
- pandas-ta/indicators.csv: last 141.00 on 2026-11-24
- talib/indicators.csv: last 141.00 on 2026-11-24
- yahooquery/ETEL.CA.csv: last 139.98 on 2026-11-23
- Kronos forecast: 21 points, last 141.46 at 2026-12-22

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