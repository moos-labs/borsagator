# Borsagator report — ADIB.CA (2026-11-25)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite ADIB.CA market=EGX · shape: sweep-lite ADIB.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-25/111021__sweep-lite-adib-ca-market-egx__runw5-sweeplite-adib-001 · archive commit: fa8e081ca3fc7110536a6f5387e815165459bca6

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 42.80
Model range high at 50.22
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs technicals -0.30 (spread +0.70)
- price-forecast: +0.06
- technicals: -0.30
- sentiment: +0.07
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.500, sentiment ×1.068, technicals ×0.679
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat -0.45% (range -5.03% … +4.12%, confidence 0.30)
- week: flat +0.43% (range -7.58% … +8.44%, confidence 0.30)
- month: up +1.47% (range -16.41% … +19.35%, confidence 0.30)
Base price: 46.31 (egx-data/egxpy_adib.csv, 2026-11-25)
Price cross-check: agree (common date 2026-11-23, base date 2026-11-25)
Witnesses stale: common date 2026-11-23 trails base date 2026-11-25.
- egx-data/egxpy_adib.csv: 46.31 on 2026-11-25
- openbb/ADIB_CA.csv: 46.15 on 2026-11-24 (stale)
- pandas-ta/indicators.csv: 46.15 on 2026-11-24 (stale)
- talib/indicators.csv: 46.15 on 2026-11-24 (stale)
- yahooquery/ADIB.CA.csv: 46.43 on 2026-11-23 (stale)

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
- Rows: 3000 · Range: 2014-07-15 → 2026-11-25
- Latest: 2026-11-25 close 46.31

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — ADIB.CA

- Last session: **2026-11-24**
- Data used: 1931 rows (2019-01-01 → 2026-11-24), after dropping rows before 2019-01-01; 6535 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 46.43 |
| High | 47.0 |
| Low | 46.15 |
| Close | 46.15 |
| RSI(14) | 43.5712 |
| MACD | -0.3823 |
| MACD signal | -0.1708 |
| MACD histogram | -0.2115 |
| EMA(20) | 47.3857 |
| EMA(50) | 48.1902 |
| EMA(200) | 45.3089 |
| ADX(14) | 28.2478 |
| Bollinger upper | 50.5928 |
| Bollinger mid | 47.649 |
| Bollinger lower | 44.7052 |
| Bollinger %B | 0.2454 |
| ATR(14) | 1.5758 |
| Stochastic %K | 27.6572 |
| Stochastic %D | 26.0514 |

## Trend read (facts only)

- Close 46.15 is below EMA_20 47.3857 (-2.61%).
- Close 46.15 is below EMA_50 48.1902 (-4.23%).
- Close 46.15 is above EMA_200 45.3089 (+1.86%).
- RSI(14) is 43.5712, in the neutral zone (30-70).
- MACD -0.3823 is below its signal line -0.1708 (histogram -0.2115).
- Price sits at %B 0.2454 of the Bollinger range (lower 44.7052, mid 47.649, upper 50.5928).
- ADX(14) is 28.2478, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 27.6572 is above %D 26.0514.
- ATR(14) is 1.5758 (3.41% of the close).

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
# Fundamentals (generic) — ADIB.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-25T11:06:12.286109+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 1200000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 46.150001525878906.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 22040.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 12589.0, "basis": "vendor income statement"}, "net_margin_pct": {"value": 57.12, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 36.35, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 3.63, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.299, "basis": "vendor total debt / equity"}, "ocf_margin_pct": {"value": -260.19, "basis": "operating cash flow / revenue"}, "fcf_margin_pct": {"value": -262.1, "basis

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 27
- Label counts: positive=6, negative=5, neutral=16
- Mean probabilities: positive=0.2387, negative=0.1515, neutral=0.6098

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0441 | 0.0298 | 0.9261 | The things that can wait — Nahrizul Adib Kadri - Malay Mail |
| 2 | neutral | 0.0825 | 0.0337 | 0.8838 | THIS MORNING: ADIB eyes AT1 sukuk + Emaar Properties clears conditions for construction arm takeover - EnterpriseAM |
| 3 | neutral | 0.0370 | 0.0169 | 0.9460 | Skandinaviska Enskilda Banken AB (SEBA.HM) options chain - Yahoo Finance Australia |
| 4 | neutral | 0.0496 | 0.0252 | 0.9253 | Match Highlights Al-Dhafra - Ajman \| ADIB Cup \| Yalla Shoot - YSscores |
| 5 | positive | 0.9157 | 0.0158 | 0.0685 | ADIB-Egypt named Global Finance’s best Islamic financial institution in Egypt for 9th year - Daily News Egypt |
| 6 | neutral | 0.1348 | 0.0144 | 0.8508 | Abu Dhabi Islamic Bank announces results of SME Innovation Challenge - Big News Network.com |
| 7 | positive | 0.8748 | 0.0265 | 0.0987 | Abu Dhabi Islamic Bank Egypt stock: 9-month profit rises 22.8% - ad-hoc-news.de |
| 8 | neutral | 0.0377 | 0.0554 | 0.9069 | Malaf El Yawm Season 1 Andira Al-Zuhairi - Adib Zakhour - MTV Lebanon |
| 9 | neutral | 0.0444 | 0.0330 | 0.9226 | Al-Wahda 3-1 Khorfakkan: Result, Goals and Stats \| ADIB Cup - YSscores |
| 10 | neutral | 0.0328 | 0.0524 | 0.9147 | Abu Dhabi Islamic Bank - Egypt - S.A.E (ADIB.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 11 | negative | 0.0113 | 0.9187 | 0.0701 | Selangor defender Adib falls victim to concert ticket scam - NST Online |
| 12 | negative | 0.0230 | 0.5026 | 0.4744 | It all points to institutional failures - Adib Saani on recurring cocaine seizures linked to Ghana - Adomonline.com |
| 13 | neutral | 0.1512 | 0.0104 | 0.8384 | UAE Business: ADIB launches ‘ADIB Arrive’ for new UAE residents - Gulf Daily News (Bahrain) |
| 14 | neutral | 0.0953 | 0.0113 | 0.8934 | ADIB Launches ‘ADIB Arrive’ to Streamline Banking for New UAE Residents - FF News |
| 15 | neutral | 0.0418 | 0.0141 | 0.9441 | ADIB’s Dh1.75 billion rights issue opens on Nov 10 - Gulf News |
| 16 | neutral | 0.1847 | 0.0092 | 0.8062 | ADIB Launches UAE’s First 24/7 Real-Time EGP Transfers to Egypt via Visa Direct - FF News |
| 17 | positive | 0.5904 | 0.0082 | 0.4013 | ADIB becomes the first bank in the UAE to offer 24/7 real-time EGP transfers to bank accounts across Egypt through Visa Direct - Zawya |
| 18 | negative | 0.0548 | 0.6647 | 0.2806 | Former Queensland premier Annastacia Palaszczuk’s ex-partner Reza Adib’s bail altered for Gold Coast rape charges - SMH.com.au |
| 19 | neutral | 0.0305 | 0.0203 | 0.9492 | ADIB rights trading period for AED 1.75bln rights Issue begins on 4 November - Zawya |
| 20 | neutral | 0.0403 | 0.0148 | 0.9449 | Adib opens trading for Dh1.75 billion rights issue; key dates investors should know - Khaleej Times |
| 21 | negative | 0.0415 | 0.5581 | 0.4004 | Reza Adib fronts Gold Coast court over rape charges - The Courier Mail |
| 22 | neutral | 0.0257 | 0.0216 | 0.9527 | ADIB rights trading period for rights issue begins on 4 November - Zawya |
| 23 | neutral | 0.0520 | 0.0760 | 0.8721 | Beirut cocaine seizure: NACOC's damage control raises more questions than answers - Adib Saani - Modern Ghana |
| 24 | negative | 0.0151 | 0.9034 | 0.0816 | Beirut Cocaine Bust: Adib Saani accuses NACOC of damage control - GhanaWeb |
| 25 | positive | 0.9411 | 0.0149 | 0.0440 | ADIB adds 200,000 customers and a first-of-its-kind open finance licence as nine-month profit climbs to AED 6.4 billion - The Fintech Times |
| 26 | positive | 0.9559 | 0.0171 | 0.0271 | ADIB sustains strong growth momentum in first nine months, with profit before tax Up 6% to AED 6.4 billion - www.wam.ae |
| 27 | positive | 0.9370 | 0.0210 | 0.0420 | ADIB Q3 profit before tax rises 6% to Dh6.4 billion as financing surges - Khaleej Times |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 27
- Label counts: positive=4, negative=2, neutral=21
- Mean probabilities: positive=0.1485, negative=0.0679, neutral=0.7837

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0005 | 0.9995 | The things that can wait — Nahrizul Adib Kadri - Malay Mail |
| 2 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | THIS MORNING: ADIB eyes AT1 sukuk + Emaar Properties clears conditions for construction arm takeover - EnterpriseAM |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Skandinaviska Enskilda Banken AB (SEBA.HM) options chain - Yahoo Finance Australia |
| 4 | neutral | Neutral | 0.0029 | 0.0000 | 0.9970 | Match Highlights Al-Dhafra - Ajman \| ADIB Cup \| Yalla Shoot - YSscores |
| 5 | neutral | Neutral | 0.0004 | 0.0000 | 0.9996 | ADIB-Egypt named Global Finance’s best Islamic financial institution in Egypt for 9th year - Daily News Egypt |
| 6 | neutral | Neutral | 0.0001 | 0.0001 | 0.9998 | Abu Dhabi Islamic Bank announces results of SME Innovation Challenge - Big News Network.com |
| 7 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Abu Dhabi Islamic Bank Egypt stock: 9-month profit rises 22.8% - ad-hoc-news.de |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Malaf El Yawm Season 1 Andira Al-Zuhairi - Adib Zakhour - MTV Lebanon |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Al-Wahda 3-1 Khorfakkan: Result, Goals and Stats \| ADIB Cup - YSscores |
| 10 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Abu Dhabi Islamic Bank - Egypt - S.A.E (ADIB.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 11 | neutral | Neutral | 0.0000 | 0.0005 | 0.9995 | Selangor defender Adib falls victim to concert ticket scam - NST Online |
| 12 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | It all points to institutional failures - Adib Saani on recurring cocaine seizures linked to Ghana - Adomonline.com |
| 13 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | UAE Business: ADIB launches ‘ADIB Arrive’ for new UAE residents - Gulf Daily News (Bahrain) |
| 14 | neutral | Neutral | 0.0015 | 0.0000 | 0.9985 | ADIB Launches ‘ADIB Arrive’ to Streamline Banking for New UAE Residents - FF News |
| 15 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | ADIB’s Dh1.75 billion rights issue opens on Nov 10 - Gulf News |
| 16 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | ADIB Launches UAE’s First 24/7 Real-Time EGP Transfers to Egypt via Visa Direct - FF News |
| 17 | neutral | Neutral | 0.0031 | 0.0000 | 0.9969 | ADIB becomes the first bank in the UAE to offer 24/7 real-time EGP transfers to bank accounts across Egypt through Visa Direct - Zawya |
| 18 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Former Queensland premier Annastacia Palaszczuk’s ex-partner Reza Adib’s bail altered for Gold Coast rape charges - SMH.com.au |
| 19 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | ADIB rights trading period for AED 1.75bln rights Issue begins on 4 November - Zawya |
| 20 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Adib opens trading for Dh1.75 billion rights issue; key dates investors should know - Khaleej Times |
| 21 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Reza Adib fronts Gold Coast court over rape charges - The Courier Mail |
| 22 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | ADIB rights trading period for rights issue begins on 4 November - Zawya |
| 23 | negative | Negative | 0.0002 | 0.9983 | 0.0015 | Beirut cocaine seizure: NACOC's damage control raises more questions than answers - Adib Saani - Modern Ghana |
| 24 | negative | Negative | 0.0002 | 0.8326 | 0.1673 | Beirut Cocaine Bust: Adib Saani accuses NACOC of damage control - GhanaWeb |
| 25 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | ADIB adds 200,000 customers and a first-of-its-kind open finance licence as nine-month profit climbs to AED 6.4 billion - The Fintech Times |
| 26 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | ADIB sustains strong growth momentum in first nine months, with profit before tax Up 6% to AED 6.4 billion - www.wam.ae |
| 27 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | ADIB Q3 profit before tax rises 6% to Dh6.4 billion as financing surges - Khaleej Times |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 27
- Label counts: positive=10, negative=6, neutral=11
- Mean probabilities: positive=0.3767, negative=0.2213, neutral=0.4020

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0004 | 0.0003 | 0.9993 | The things that can wait — Nahrizul Adib Kadri - Malay Mail |
| 2 | positive | positive | 0.9944 | 0.0003 | 0.0053 | THIS MORNING: ADIB eyes AT1 sukuk + Emaar Properties clears conditions for construction arm takeover - EnterpriseAM |
| 3 | neutral | neutral | 0.0008 | 0.0003 | 0.9990 | Skandinaviska Enskilda Banken AB (SEBA.HM) options chain - Yahoo Finance Australia |
| 4 | neutral | neutral | 0.0006 | 0.0004 | 0.9990 | Match Highlights Al-Dhafra - Ajman \| ADIB Cup \| Yalla Shoot - YSscores |
| 5 | positive | positive | 0.9979 | 0.0010 | 0.0010 | ADIB-Egypt named Global Finance’s best Islamic financial institution in Egypt for 9th year - Daily News Egypt |
| 6 | neutral | neutral | 0.1789 | 0.0008 | 0.8203 | Abu Dhabi Islamic Bank announces results of SME Innovation Challenge - Big News Network.com |
| 7 | positive | positive | 0.9983 | 0.0008 | 0.0009 | Abu Dhabi Islamic Bank Egypt stock: 9-month profit rises 22.8% - ad-hoc-news.de |
| 8 | neutral | neutral | 0.0006 | 0.0005 | 0.9990 | Malaf El Yawm Season 1 Andira Al-Zuhairi - Adib Zakhour - MTV Lebanon |
| 9 | neutral | neutral | 0.0032 | 0.0005 | 0.9964 | Al-Wahda 3-1 Khorfakkan: Result, Goals and Stats \| ADIB Cup - YSscores |
| 10 | neutral | neutral | 0.0007 | 0.0002 | 0.9992 | Abu Dhabi Islamic Bank - Egypt - S.A.E (ADIB.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada |
| 11 | negative | negative | 0.0002 | 0.9986 | 0.0012 | Selangor defender Adib falls victim to concert ticket scam - NST Online |
| 12 | negative | negative | 0.0002 | 0.9988 | 0.0010 | It all points to institutional failures - Adib Saani on recurring cocaine seizures linked to Ghana - Adomonline.com |
| 13 | positive | positive | 0.9977 | 0.0005 | 0.0019 | UAE Business: ADIB launches ‘ADIB Arrive’ for new UAE residents - Gulf Daily News (Bahrain) |
| 14 | positive | positive | 0.9980 | 0.0006 | 0.0014 | ADIB Launches ‘ADIB Arrive’ to Streamline Banking for New UAE Residents - FF News |
| 15 | neutral | neutral | 0.0006 | 0.0002 | 0.9992 | ADIB’s Dh1.75 billion rights issue opens on Nov 10 - Gulf News |
| 16 | positive | positive | 0.9978 | 0.0007 | 0.0015 | ADIB Launches UAE’s First 24/7 Real-Time EGP Transfers to Egypt via Visa Direct - FF News |
| 17 | positive | positive | 0.9977 | 0.0006 | 0.0018 | ADIB becomes the first bank in the UAE to offer 24/7 real-time EGP transfers to bank accounts across Egypt through Visa Direct - Zawya |
| 18 | negative | negative | 0.0009 | 0.9776 | 0.0215 | Former Queensland premier Annastacia Palaszczuk’s ex-partner Reza Adib’s bail altered for Gold Coast rape charges - SMH.com.au |
| 19 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | ADIB rights trading period for AED 1.75bln rights Issue begins on 4 November - Zawya |
| 20 | neutral | neutral | 0.0051 | 0.0002 | 0.9947 | Adib opens trading for Dh1.75 billion rights issue; key dates investors should know - Khaleej Times |
| 21 | negative | negative | 0.0003 | 0.9938 | 0.0058 | Reza Adib fronts Gold Coast court over rape charges - The Courier Mail |
| 22 | neutral | neutral | 0.0003 | 0.0002 | 0.9995 | ADIB rights trading period for rights issue begins on 4 November - Zawya |
| 23 | negative | negative | 0.0004 | 0.9987 | 0.0009 | Beirut cocaine seizure: NACOC's damage control raises more questions than answers - Adib Saani - Modern Ghana |
| 24 | negative | negative | 0.0005 | 0.9973 | 0.0023 | Beirut Cocaine Bust: Adib Saani accuses NACOC of damage control - GhanaWeb |
| 25 | positive | positive | 0.9983 | 0.0008 | 0.0010 | ADIB adds 200,000 customers and a first-of-its-kind open finance licence as nine-month profit climbs to AED 6.4 billion - The Fintech Times |
| 26 | positive | positive | 0.9983 | 0.0009 | 0.0008 | ADIB sustains strong growth momentum in first nine months, with profit before tax Up 6% to AED 6.4 billion - www.wam.ae |
| 27 | positive | positive | 0.9982 | 0.0008 | 0.0010 | ADIB Q3 profit before tax rises 6% to Dh6.4 billion as financing surges - Khaleej Times |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — ADIB.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-23 — 39 sessions
- Context supplied to Kronos: 39 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 46.43000030517578 on 2026-11-23
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-24: 46.0754
- 2026-11-25: 46.3305
- 2026-11-26: 46.5954
- 2026-11-29: 46.4738
- 2026-11-30: 46.7164
- 2026-12-01: 46.6752
- 2026-12-02: 46.6786
- 2026-12-03: 46.6282
- 2026-12-06: 46.7525
- 2026-12-07: 46.6348
- 2026-12-08: 47.1104
- 2026-12-09: 46.9019
- 2026-12-10: 47.0397
- 2026-12-13: 46.8135
- 2026-12-14: 47.0708
- 2026-12-15: 46.962
- 2026-12-16: 46.8454
- 2026-12-17: 47.0086
- 2026-12-20: 46.8393
- 2026-12-21: 46.8382
- 2026-12-22: 46.8002

**Change over the 21 sessions (last forecasted close vs last actual close): +0.80%**

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
News: 34 · disclosures: 1 · identity scheme: resolved_url|title-date-hash
- منير أديب: العواصم الأوروبية أدركت أن الإرهابية تمثل خطرًا على أمنها (فيديو) - مبتدا
- عمرو أديب يهاجم الأهلي بعد هزيمته أمام بيراميدز 2-0 ويطالب ببقاء عموتة - شبكة تواصل الإخبارية
- القطيف - القلعة: الأديب والشاعر الحاج محمد سعيد ابن الشيخ علي ابو الحسن الخنيزي في ذمة الله - alqhat.com
- عمرو أديب بعد هزيمة الأهلي أمام بيراميدز: «ندائي للإدارة والجماهير.. أوعوا تمشوا عموتة» - موقع الحرية الإخباري
- عمرو أديب يهاجم لاعبي الأهلي: «مستواهم زي الزفت.. والدلع زاد عن حده» - ايجي بودكاست
- عمرو أديب يهاجم لاعبي الأهلي: فين روح الفانلة الحمراء؟ - https://www.youlyou.com/
- عمرو أديب بعد خسارة الأهلي أمام بيراميدز: الفريق السماوي يستحق لقب الدوري.. وتمسكوا بعموتة (فيديو) - أهل مصر
- عمرو أديب: الأهلي من سيئ إلى أسوأ.. وحال جمهوره يصعب عليك - أهل مصر
- عمرو أديب يفتح النار على الأهلي بعد السقوط أمام بيراميدز.. فماذا قال؟ - elmaser.com
- عمرو أديب يحذر من تصاعد الانتقادات الأمريكية لمصر تحت شعار حقوق الإنسان - جريدة المستقبل
- منير أديب: مخاوف أوروبا من الإخوان تحولت لحقائق بعد تغلغلها بالمؤسسات.. فيديو - اليوم السابع
- عمرو أديب: مذكرات بايدن تكشف موقف السيسي من تهجير الفلسطينيين إلى مصر - المصري اليوم
- عمرو أديب: مفيش حاجة قفزت زي الجبنة البيضاء.. والدماطي يربط ارتفاع أسعارها بـ«بروتين بوم» وأدوية التخسيس - المصري اليوم
- عمرو أديب عن الموجة المنتشرة: «اللي اتلسع من كورونا بينفخ في أي دور برد» - أهل مصر
- منير أديب: مخاوف أوروبا من الإخوان تحولت لحقائق ومصر واجهت التنظيم مبكرًا - مبتدا
- هل اختفى الشتاء هذا العام؟.. عمرو أديب يسأل والأرصاد ترد - Masrawy
- أديب: 4250 أمريكيًا أصبحوا مليونيرات ومليارديرات في ساعات بسبب "كلود" - Masrawy
- عمرو أديب: الإنسان تاني أذكى مخلوق في العالم والشمبانزي الثالث - المصري اليوم
- «لو وصل 39 أو 40 هنزل اشتري».. عمرو أديب يكشف السعر الذي ينتظره في سوق الذهب - المصري اليوم
- هل تهدد الاتفاقية التركية الليبية الحقوق البحرية المصرية؟.. عمرو أديب يوضح - Masrawy
- مصر: منع الصحفي عبد الحليم قنديل من الظهور يثير جدلا بين نقابة الصحفيين ومجلس الإعلام وعمرو أديب - مونت كارلو الدولية
- قنديل يثير أزمة في مصر.. قرار بمنعه من الظهور إعلاميا وعمرو أديب يعتذر - عربي21
- Abu Dhabi Islamic Bank - Egypt - S.A.E (ADIB.CA) Seasonal Returns Chart - Yahoo Finance - Yahoo! Finance Canada

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/ADIB-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.03
- finbert_positive: 0.24
- multilingual_positive: 0.23
- multilingual_negative: 0.54
- translated_positive: 0.19
- translated_negative: 0.28
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- management event: عمرو أديب يهاجم الأهلي بعد هزيمته أمام بيراميدز 2-0 ويطالب ببقاء عموتة - شبكة تواصل الإخبا
- management event: عمرو أديب بعد خسارة الأهلي أمام بيراميدز: الفريق السماوي يستحق لقب الدوري.. وتمسكوا بعموتة
- عمرو أديب يهاجم الأهلي بعد هزيمته أمام بيراميدز 2-0 ويطالب ببقاء عموتة - شبكة تواصل الإخبا (truncated title — see the archived news file for full text)
- عمرو أديب بعد خسارة الأهلي أمام بيراميدز: الفريق السماوي يستحق لقب الدوري.. وتمسكوا بعموتة (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_adib.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_adib.csv: last 46.31 on 2026-11-25
- openbb/ADIB_CA.csv: last 46.15 on 2026-11-24
- pandas-ta/indicators.csv: last 46.15 on 2026-11-24
- talib/indicators.csv: last 46.15 on 2026-11-24
- yahooquery/ADIB.CA.csv: last 46.43 on 2026-11-23
- Kronos forecast: 21 points, last 46.80 at 2026-12-22

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