# Borsagator report — EGAL.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite EGAL.CA market=EGX · shape: sweep-lite EGAL.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/030746__sweep-lite-egal-ca-market-egx__runw6-sweeplite-egal-002 · archive commit: f839924802376e062bd7a57a1bd6513cc2b50bd4

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 264.80
Model range high at 320.20
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs technicals -0.20 (spread +0.60)
- price-forecast: +0.12
- technicals: -0.20
- sentiment: +0.14
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -3.80% … +3.80%, confidence 0.30)
- week: flat +0.00% (range -9.47% … +9.47%, confidence 0.30)
- month: flat +0.00% (range -18.19% … +18.19%, confidence 0.30)
Base price: 292.50 (egx-data/egxpy_egal.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-24, base date 2026-11-26)
Witnesses stale: common date 2026-11-24 trails base date 2026-11-26.
- egx-data/egxpy_egal.csv: 292.50 on 2026-11-26
- openbb/EGAL_CA.csv: 293.35 on 2026-11-25 (stale)
- pandas-ta/indicators.csv: 293.35 on 2026-11-25 (stale)
- talib/indicators.csv: 293.35 on 2026-11-25 (stale)
- yahooquery/EGAL.CA.csv: 302.00 on 2026-11-24 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: EGAL.CA.csv_last_close, EGAL.CA.csv_last_date, rows_EGAL.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: EGAL_CA.csv_last_close, EGAL_CA.csv_last_date, rows_EGAL_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_egal.csv_last_close, egxpy_egal.csv_last_date, rows_egxpy_egal.csv, symbol, ticker
# EGX data sources for EGAL — verdict

No POUL reference material applies to EGAL; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-06-10 → 2026-11-26
- Latest: 2026-11-26 close 292.5

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — EGAL.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6534 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 298.0 |
| High | 299.0 |
| Low | 292.02 |
| Close | 293.35 |
| RSI(14) | 36.7946 |
| MACD | -4.991 |
| MACD signal | -3.7889 |
| MACD histogram | -1.2021 |
| EMA(20) | 308.9033 |
| EMA(50) | 317.417 |
| EMA(200) | 298.3431 |
| ADX(14) | 27.4966 |
| Bollinger upper | 329.5612 |
| Bollinger mid | 309.7875 |
| Bollinger lower | 290.0138 |
| Bollinger %B | 0.0844 |
| ATR(14) | 9.1961 |
| Stochastic %K | 13.7956 |
| Stochastic %D | 18.568 |

## Trend read (facts only)

- Close 293.35 is below EMA_20 308.9033 (-5.04%).
- Close 293.35 is below EMA_50 317.417 (-7.58%).
- Close 293.35 is below EMA_200 298.3431 (-1.67%).
- RSI(14) is 36.7946, in the neutral zone (30-70).
- MACD -4.991 is below its signal line -3.7889 (histogram -1.2021).
- Price sits at %B 0.0844 of the Bollinger range (lower 290.0138, mid 309.7875, upper 329.5612).
- ADX(14) is 27.4966, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 13.7956 is below %D 18.568.
- ATR(14) is 9.1961 (3.13% of the close).

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
# Fundamentals (generic) — EGAL.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T03:05:45.336077+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 412500000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 293.3500061035156.

Periods: TTM, FY2026, FY2025, FY2024, FY2023, FY2022. Latest FY block: {"revenue_EGPm": {"value": 53137.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 15491.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 37.75, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 36.45, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 29.15, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 45.71, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 36.4, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 40
- Label counts: positive=11, negative=4, neutral=25
- Mean probabilities: positive=0.3027, negative=0.1220, neutral=0.5753

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0243 | 0.0247 | 0.9510 | Agnico Eagle Mines Limited (AEM.TO) stock price, news, quote and history - Yahoo Finance UK |
| 2 | neutral | 0.2194 | 0.0169 | 0.7637 | Why Did Agnico Eagle Mines (TSX:AEM) Surge 2.664% on November 25, 2026? - kalkine.ca |
| 3 | negative | 0.0464 | 0.7561 | 0.1974 | How a Drop in Gold Weighed on Agnico Eagle Mines (TSX:AEM) on the S&P/TSX Composite (24 Nov 2026) - kalkine.ca |
| 4 | neutral | 0.2667 | 0.1166 | 0.6167 | Agnico Eagle Mines Limited (TSX:AEM): Large-Cap Value Stock in Focus as S&P/TSX Composite Index Investors Weigh the Next Move - kalkine.ca |
| 5 | negative | 0.0117 | 0.9626 | 0.0257 | Agnico Eagle Mines Limited (TSX:AEM) Stock Declines 2.88%: Gold Market Volatility and Mining Cost Concerns Weigh on Investor Sentiment - kalkine.ca |
| 6 | neutral | 0.0533 | 0.0136 | 0.9331 | What Is Tungsten Eagle Testing With Its Liberty Ridge Drill Program in Nevada? - Kalkine Media |
| 7 | positive | 0.9270 | 0.0359 | 0.0371 | Why Agnico Eagle Mines Limited (TSX:AEM) Climbed on the S&P/TSX Composite as Gold Bounced Back From a One-Year Low (23 Nov 2026) - kalkine.ca |
| 8 | neutral | 0.0229 | 0.0275 | 0.9496 | Agnico Eagle Mines Limited (AEM.TO) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 9 | neutral | 0.0229 | 0.0277 | 0.9495 | Eagle Nuclear Energy Corp. (NUCL) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 10 | neutral | 0.0934 | 0.0280 | 0.8786 | Agnico Eagle Mines Limited (TSX:AEM): Why This Large Cap Growth Stock Is Trending on the S&P/TSX Composite Index Today - kalkine.ca |
| 11 | neutral | 0.0206 | 0.0319 | 0.9474 | Eagle Plains Resources Ltd. (EPL.V) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 12 | neutral | 0.1491 | 0.0078 | 0.8431 | Kestrel could fund C$5 million in exploration as part of earning 60% of a B.C. copper-and-gold project. - Stock Titan |
| 13 | neutral | 0.1497 | 0.0094 | 0.8408 | An 11-kilometer gold trend may extend toward older finds, but no link is proven. Eagle Plains and Earthwise applied for more land. - Stock Titan |
| 14 | neutral | 0.2368 | 0.0181 | 0.7451 | Why Did Agnico Eagle Mines (TSX:AEM) Surge 6.143% on November 23, 2026? - kalkine.ca |
| 15 | negative | 0.0078 | 0.9720 | 0.0202 | Agnico Eagle Mines stock drops more than 3% after ongoing selling pressure and lack of sustained support - Traders Union |
| 16 | positive | 0.8566 | 0.0213 | 0.1221 | S&P/TSX Composite: Agnico Eagle Mines Limited (TSX:AEM) — Large Cap Value Stock in Focus as Investors Track the Next Catalyst - kalkine.ca |
| 17 | negative | 0.0140 | 0.9642 | 0.0218 | Agnico Eagle Mines Limited (TSX:AEM) Stock Falls 2.08%: Gold Price Volatility, Mining Costs and Valuation Concerns Raise Downside Risks - kalkine.ca |
| 18 | neutral | 0.0428 | 0.0499 | 0.9073 | Agnico Eagle Stock: The Cash Flow Behind the Gold-Price Headlines - The Motley Fool Canada |
| 19 | neutral | 0.0850 | 0.0203 | 0.8947 | Glen Eagle Resources (TSXV:GER) in Focus: TSXV Composite Small-Cap Growth Stock Trends on AGM results and Cobra Oro extension - kalkine.ca |
| 20 | neutral | 0.3217 | 0.0107 | 0.6676 | S&P/TSX Composite Focus: Agnico Eagle Mines Limited (TSX:AEM) — Large Cap Growth Stock Why Traders and Long-Term Investors Are Watching This Name - kalkine.ca |
| 21 | neutral | 0.2387 | 0.0113 | 0.7500 | American Eagle Gold Corp. (TSXV:AE) — TSXV Small-Cap Growth Stock in Focus as the Next Catalyst Comes Into View - kalkine.ca |
| 22 | neutral | 0.4425 | 0.0105 | 0.5470 | Can Agnico Eagle Mines (TSX:AEM) Keep Returning Cash as Gold Prices Lift Free Cash Flow? - kalkine.ca |
| 23 | neutral | 0.0389 | 0.0175 | 0.9436 | American Eagle Gold Corp. AE in Focus: The Latest Market Catalyst Investors Are Watching on November 12, 2026 (TSXV:AE) - kalkine.ca |
| 24 | positive | 0.9299 | 0.0462 | 0.0239 | Agnico Eagle (TSX:AEM) Stock Rallies 9.45% as Gold Rebounds and Strong Free Cash Flow Underpins Shareholder Returns - kalkine.ca |
| 25 | neutral | 0.1909 | 0.0104 | 0.7987 | Eagle Nuclear's 92% Noble Plains Uranium Takeover Premium Implies 54% in Current Stock Math - the deep dive |
| 26 | neutral | 0.0462 | 0.0185 | 0.9353 | Agnico Eagle Mines (TSX:AEM): Why This Canadian Stock Is Drawing Attention on 4 November 2026 - kalkine.ca |
| 27 | neutral | 0.0449 | 0.0626 | 0.8925 | Agnico Eagle Mines (TSX:AEM): Why Gold Mining Revenue Per Employee Draws Attention as Production Shifts - kalkine.ca |
| 28 | neutral | 0.0549 | 0.0182 | 0.9269 | Rick Rule's Top Picks: Franco Nevada, Wheaton Precious Metals & Agnico Eagle - BNN Bloomberg |
| 29 | positive | 0.9095 | 0.0098 | 0.0807 | Agnico Eagle: Soaring Above The Peer Group (Rating Upgrade) - Seeking Alpha |
| 30 | neutral | 0.0481 | 0.0283 | 0.9236 | Agnico Eagle Mines Limited (TSX:AEM): What Could Move the Stock After the Latest Market Developments? - kalkine.ca |
| 31 | positive | 0.7016 | 0.0077 | 0.2906 | Agnico Eagle: Superior Super Major Strategy (NYSE:AEM) - Seeking Alpha |
| 32 | positive | 0.9142 | 0.0114 | 0.0743 | Agnico Eagle: Strong Operations, But Hard To See Further Upside (NYSE:AEM) - Seeking Alpha |
| 33 | positive | 0.6137 | 0.0119 | 0.3743 | Agnico Eagle Mines Stock: Revenue Per Employee Signals Scalable Operations and Long-Term Investment Potential - kalkine.ca |
| 34 | neutral | 0.0632 | 0.0137 | 0.9231 | Agnico Eagle Mines Limited (TSX:AEM) Rallies Into Focus: What Could Move the Stock Next? - kalkine.ca |
| 35 | positive | 0.9526 | 0.0210 | 0.0265 | Agnico Eagle Mines Limited (TSX:AEM) Climbs 5.69% as Positive Momentum Strengthens Investor Interest - kalkine.ca |
| 36 | positive | 0.8246 | 0.0358 | 0.1396 | Agnico Eagle (TSX:AEM): Gold Exposure and October Earnings Countdown Put TSX Miner in Focus - kalkine.ca |
| 37 | neutral | 0.0408 | 0.0258 | 0.9334 | Agnico Eagle Mines (AEM) Laps the Stock Market: Here's Why - Yahoo Finance |
| 38 | positive | 0.8579 | 0.0570 | 0.0851 | Most Actively Traded Canadian Stocks: Agnico Eagle Mines Limited (TSX:AEM) Draws Heavy Trading as Investors Assess Market Momentum - kalkine.ca |
| 39 | neutral | 0.1295 | 0.0113 | 0.8592 | Agnico Eagle Earnings: Gold Margins and Project Execution Shape the Investment Outlook - kalkine.ca |
| 40 | positive | 0.4941 | 0.3357 | 0.1702 | Agnico Eagle Mines stock forecast: Reversal setup emerges near C$261.34 resistance - Traders Union |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 31
- Label counts: positive=9, negative=1, neutral=21
- Mean probabilities: positive=0.3020, negative=0.0532, neutral=0.6449

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Agnico Eagle Mines Limited (AEM.TO) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 2 | neutral | Neutral | 0.0135 | 0.0021 | 0.9844 | Agnico Eagle Mines stock price prediction: Consolidation expected with upside capped below resistance - Traders Union |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Agnico Eagle Mines Limited (AEM.TO) stock price, news, quote and history - Yahoo Finance UK |
| 4 | neutral | Neutral | 0.3333 | 0.0551 | 0.6116 | Why Did Agnico Eagle Mines (TSX:AEM) Surge 2.664% on November 25, 2026? - kalkine.ca |
| 5 | neutral | Neutral | 0.0000 | 0.0033 | 0.9967 | How a Drop in Gold Weighed on Agnico Eagle Mines (TSX:AEM) on the S&P/TSX Composite (24 Nov 2026) - kalkine.ca |
| 6 | positive | Positive | 0.9956 | 0.0000 | 0.0044 | Could Agnico Eagle (TSX:AEM) Lead The Next Gold Stocks Rally? - Kalkine Media |
| 7 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Royal Gold, Inc. (RGLD) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 8 | neutral | Neutral | 0.0011 | 0.0000 | 0.9989 | Agnico Eagle Mines Limited (TSX:AEM): Large-Cap Value Stock in Focus as S&P/TSX Composite Index Investors Weigh the Next Move - kalkine.ca |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | American Eagle options signal 13% move around Dec. 2 earnings By Investing.com - Investing.com Canada |
| 10 | negative | Negative | 0.0000 | 1.0000 | 0.0000 | Agnico Eagle Mines Limited (TSX:AEM) Stock Declines 2.88%: Gold Market Volatility and Mining Cost Concerns Weigh on Investor Sentiment - kalkine.ca |
| 11 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | What Is Tungsten Eagle Testing With Its Liberty Ridge Drill Program in Nevada? - Kalkine Media |
| 12 | positive | Positive | 0.9953 | 0.0013 | 0.0034 | Why Agnico Eagle Mines Limited (TSX:AEM) Climbed on the S&P/TSX Composite as Gold Bounced Back From a One-Year Low (23 Nov 2026) - kalkine.ca |
| 13 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Pan American Silver Corp. (PAAS) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 14 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Eagle Nuclear Energy Corp. (NUCL) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 15 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Pan American Silver Corp. (PAAS.TO) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 16 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Wheaton Precious Metals Corp. (WPM) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 17 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Agnico Eagle Mines Limited (TSX:AEM): Why This Large Cap Growth Stock Is Trending on the S&P/TSX Composite Index Today - kalkine.ca |
| 18 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Eagle Plains Resources Ltd. (EPL.V) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 19 | positive | Positive | 0.9624 | 0.0016 | 0.0360 | Why Did Agnico Eagle Mines (TSX:AEM) Surge 6.143% on November 23, 2026? - kalkine.ca |
| 20 | positive | Positive | 0.9989 | 0.0000 | 0.0011 | What's behind Agnico Eagle Mines's latest 6.1% stock surge? - Traders Union |
| 21 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Agnico Eagle (AEM) Stock May Be 26% Undervalued As Hiring Plans Expand - Yahoo Finance |
| 22 | neutral | Neutral | 0.0007 | 0.0000 | 0.9993 | Victory Capital Stockholders Approve Stock Issuance, Clearing Key Milestone Toward First Eagle Acquisition - Yahoo Finance |
| 23 | neutral | Neutral | 0.0039 | 0.0002 | 0.9959 | Agnico Eagle Stock: The Cash Flow Behind the Gold-Price Headlines - The Motley Fool Canada |
| 24 | positive | Positive | 0.9997 | 0.0000 | 0.0003 | Eagle Bancorp (EGBN) Stock Fair Value Rises After Analyst Target Increases - Yahoo Finance |
| 25 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | What Makes Eagle Bancorp (EGBN) a Strong Momentum Stock: Buy Now? - Yahoo Finance |
| 26 | neutral | Neutral | 0.0003 | 0.0234 | 0.9763 | Why Did Agnico Eagle Stock Fall? - Yahoo Finance |
| 27 | neutral | Neutral | 0.0557 | 0.4495 | 0.4948 | How Investors Are Reacting To Agnico Eagle Mines Stock Higher Costs And Lower Output - Yahoo Finance |
| 28 | neutral | Neutral | 0.0010 | 0.1114 | 0.8876 | Is Agnico Eagle Mines Stock A Real Bargain? - Yahoo Finance |
| 29 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | American Eagle Outfitters (AEO) Stock Slides as Market Rises: Facts to Know Before You Trade - Yahoo Finance |
| 30 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Eagle Materials (EXP) Stock May Be 42% Undervalued On Cash Flow - Yahoo Finance |
| 31 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Agnico Eagle Earnings: Improved on the Stronger Gold Price, but Volumes Softer and Unit Costs Higher - Morningstar |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 31
- Label counts: positive=11, negative=7, neutral=13
- Mean probabilities: positive=0.3483, negative=0.2298, neutral=0.4219

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0005 | 0.0002 | 0.9992 | Agnico Eagle Mines Limited (AEM.TO) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 2 | neutral | neutral | 0.0037 | 0.2860 | 0.7103 | Agnico Eagle Mines stock price prediction: Consolidation expected with upside capped below resistance - Traders Union |
| 3 | neutral | neutral | 0.0005 | 0.0003 | 0.9992 | Agnico Eagle Mines Limited (AEM.TO) stock price, news, quote and history - Yahoo Finance UK |
| 4 | positive | positive | 0.9973 | 0.0008 | 0.0020 | Why Did Agnico Eagle Mines (TSX:AEM) Surge 2.664% on November 25, 2026? - kalkine.ca |
| 5 | negative | negative | 0.0005 | 0.8474 | 0.1521 | How a Drop in Gold Weighed on Agnico Eagle Mines (TSX:AEM) on the S&P/TSX Composite (24 Nov 2026) - kalkine.ca |
| 6 | positive | positive | 0.9960 | 0.0003 | 0.0037 | Could Agnico Eagle (TSX:AEM) Lead The Next Gold Stocks Rally? - Kalkine Media |
| 7 | neutral | neutral | 0.0005 | 0.0002 | 0.9993 | Royal Gold, Inc. (RGLD) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 8 | neutral | neutral | 0.0010 | 0.0002 | 0.9989 | Agnico Eagle Mines Limited (TSX:AEM): Large-Cap Value Stock in Focus as S&P/TSX Composite Index Investors Weigh the Next Move - kalkine.ca |
| 9 | positive | positive | 0.8667 | 0.0006 | 0.1326 | American Eagle options signal 13% move around Dec. 2 earnings By Investing.com - Investing.com Canada |
| 10 | negative | negative | 0.0003 | 0.9989 | 0.0009 | Agnico Eagle Mines Limited (TSX:AEM) Stock Declines 2.88%: Gold Market Volatility and Mining Cost Concerns Weigh on Investor Sentiment - kalkine.ca |
| 11 | neutral | neutral | 0.0007 | 0.0002 | 0.9990 | What Is Tungsten Eagle Testing With Its Liberty Ridge Drill Program in Nevada? - Kalkine Media |
| 12 | positive | positive | 0.9978 | 0.0009 | 0.0012 | Why Agnico Eagle Mines Limited (TSX:AEM) Climbed on the S&P/TSX Composite as Gold Bounced Back From a One-Year Low (23 Nov 2026) - kalkine.ca |
| 13 | neutral | neutral | 0.0005 | 0.0002 | 0.9993 | Pan American Silver Corp. (PAAS) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 14 | neutral | neutral | 0.0005 | 0.0003 | 0.9992 | Eagle Nuclear Energy Corp. (NUCL) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 15 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | Pan American Silver Corp. (PAAS.TO) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 16 | neutral | neutral | 0.0005 | 0.0002 | 0.9993 | Wheaton Precious Metals Corp. (WPM) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 17 | neutral | neutral | 0.0010 | 0.0002 | 0.9989 | Agnico Eagle Mines Limited (TSX:AEM): Why This Large Cap Growth Stock Is Trending on the S&P/TSX Composite Index Today - kalkine.ca |
| 18 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | Eagle Plains Resources Ltd. (EPL.V) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 19 | positive | positive | 0.9975 | 0.0008 | 0.0018 | Why Did Agnico Eagle Mines (TSX:AEM) Surge 6.143% on November 23, 2026? - kalkine.ca |
| 20 | positive | positive | 0.9950 | 0.0003 | 0.0048 | What's behind Agnico Eagle Mines's latest 6.1% stock surge? - Traders Union |
| 21 | negative | negative | 0.0003 | 0.9949 | 0.0047 | Agnico Eagle (AEM) Stock May Be 26% Undervalued As Hiring Plans Expand - Yahoo Finance |
| 22 | positive | positive | 0.9981 | 0.0007 | 0.0012 | Victory Capital Stockholders Approve Stock Issuance, Clearing Key Milestone Toward First Eagle Acquisition - Yahoo Finance |
| 23 | neutral | neutral | 0.0005 | 0.0002 | 0.9994 | Agnico Eagle Stock: The Cash Flow Behind the Gold-Price Headlines - The Motley Fool Canada |
| 24 | positive | positive | 0.9978 | 0.0006 | 0.0015 | Eagle Bancorp (EGBN) Stock Fair Value Rises After Analyst Target Increases - Yahoo Finance |
| 25 | positive | positive | 0.9750 | 0.0002 | 0.0249 | What Makes Eagle Bancorp (EGBN) a Strong Momentum Stock: Buy Now? - Yahoo Finance |
| 26 | negative | negative | 0.0002 | 0.9972 | 0.0026 | Why Did Agnico Eagle Stock Fall? - Yahoo Finance |
| 27 | negative | negative | 0.0003 | 0.9985 | 0.0013 | How Investors Are Reacting To Agnico Eagle Mines Stock Higher Costs And Lower Output - Yahoo Finance |
| 28 | positive | positive | 0.9682 | 0.0005 | 0.0313 | Is Agnico Eagle Mines Stock A Real Bargain? - Yahoo Finance |
| 29 | negative | negative | 0.0002 | 0.9930 | 0.0068 | American Eagle Outfitters (AEO) Stock Slides as Market Rises: Facts to Know Before You Trade - Yahoo Finance |
| 30 | negative | negative | 0.0003 | 0.9980 | 0.0017 | Eagle Materials (EXP) Stock May Be 42% Undervalued On Cash Flow - Yahoo Finance |
| 31 | positive | positive | 0.9956 | 0.0017 | 0.0027 | Agnico Eagle Earnings: Improved on the Stronger Gold Price, but Volumes Softer and Unit Costs Higher - Morningstar |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — EGAL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 302.0 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 298.6719
- 2026-11-26: 300.2704
- 2026-11-29: 298.6579
- 2026-11-30: 297.5635
- 2026-12-01: 298.3966
- 2026-12-02: 300.3364
- 2026-12-03: 298.2523
- 2026-12-06: 298.548
- 2026-12-07: 302.4845
- 2026-12-08: 300.9496
- 2026-12-09: 300.6785
- 2026-12-10: 300.8575
- 2026-12-13: 302.8244
- 2026-12-14: 300.6749
- 2026-12-15: 300.0858
- 2026-12-16: 300.1799
- 2026-12-17: 302.2452
- 2026-12-20: 301.3808
- 2026-12-21: 300.808
- 2026-12-22: 302.6248
- 2026-12-23: 299.5266

**Change over the 21 sessions (last forecasted close vs last actual close): -0.82%**

## Caveat

Independent evaluations show Kronos direction accuracy near coin-flip — this forecast is a research lens, not a trading signal. Kronos is a sampling model: reruns can differ. Do not trade on this output alone.

### financedatabase
Status: ok · exit code: 0
Summary keys: count, method, rows_egypt_equities.csv, rows_us_sector_equities.csv
No report for this tool.
### news-disclosure
Status: ok · exit code: 0
Summary keys: arabic_headlines, bodies_fetched, disclosure_count, egx_bodies_attached, egx_disclosures_added, fetched_at, finbert_negative, finbert_neutral, finbert_positive, finbert_scored, latest_disclosure_date, latest_news_date, llm_provider, news_count, ticker, tool, top_headline, translation_provider
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
News: 31 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- Agnico Eagle Mines Limited (AEM.TO) Stock Price, News, Quote & History - Yahoo! Finance Canada
- Agnico Eagle Mines stock price prediction: Consolidation expected with upside capped below resistance - Traders Union
- Agnico Eagle Mines Limited (AEM.TO) stock price, news, quote and history - Yahoo Finance UK
- Why Did Agnico Eagle Mines (TSX:AEM) Surge 2.664% on November 25, 2026? - kalkine.ca
- How a Drop in Gold Weighed on Agnico Eagle Mines (TSX:AEM) on the S&P/TSX Composite (24 Nov 2026) - kalkine.ca
- Could Agnico Eagle (TSX:AEM) Lead The Next Gold Stocks Rally? - Kalkine Media
- Royal Gold, Inc. (RGLD) Stock Price, News, Quote & History - Yahoo! Finance Canada
- Agnico Eagle Mines Limited (TSX:AEM): Large-Cap Value Stock in Focus as S&P/TSX Composite Index Investors Weigh the Next Move - kalkine.ca
- American Eagle options signal 13% move around Dec. 2 earnings By Investing.com - Investing.com Canada
- Agnico Eagle Mines Limited (TSX:AEM) Stock Declines 2.88%: Gold Market Volatility and Mining Cost Concerns Weigh on Investor Sentiment - kalkine.ca
- What Is Tungsten Eagle Testing With Its Liberty Ridge Drill Program in Nevada? - Kalkine Media
- Why Agnico Eagle Mines Limited (TSX:AEM) Climbed on the S&P/TSX Composite as Gold Bounced Back From a One-Year Low (23 Nov 2026) - kalkine.ca
- Pan American Silver Corp. (PAAS) Stock Price, News, Quote & History - Yahoo! Finance Canada
- Eagle Nuclear Energy Corp. (NUCL) Stock Price, News, Quote & History - Yahoo! Finance Canada
- Pan American Silver Corp. (PAAS.TO) Stock Price, News, Quote & History - Yahoo! Finance Canada
- Wheaton Precious Metals Corp. (WPM) Stock Price, News, Quote & History - Yahoo! Finance Canada
- Agnico Eagle Mines Limited (TSX:AEM): Why This Large Cap Growth Stock Is Trending on the S&P/TSX Composite Index Today - kalkine.ca
- Eagle Plains Resources Ltd. (EPL.V) Stock Price, News, Quote & History - Yahoo! Finance Canada
- Why Did Agnico Eagle Mines (TSX:AEM) Surge 6.143% on November 23, 2026? - kalkine.ca
- What's behind Agnico Eagle Mines's latest 6.1% stock surge? - Traders Union
- Agnico Eagle (AEM) Stock May Be 26% Undervalued As Hiring Plans Expand - Yahoo Finance
- Victory Capital Stockholders Approve Stock Issuance, Clearing Key Milestone Toward First Eagle Acquisition - Yahoo Finance

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/EGAL-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.18
- finbert_positive: 0.20
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- earnings event: Agnico Eagle Mines Limited (AEM.TO) Stock Price, News, Quote & History - Yahoo! Finance Ca
- earnings event: Agnico Eagle Mines Limited (AEM.TO) stock price, news, quote and history - Yahoo Finance U
- earnings event: American Eagle options signal 13% move around Dec. 2 earnings By Investing.com - Investing
- Agnico Eagle Mines Limited (AEM.TO) Stock Price, News, Quote & History - Yahoo! Finance Ca (truncated title — see the archived news file for full text)
- Agnico Eagle Mines Limited (AEM.TO) stock price, news, quote and history - Yahoo Finance U (truncated title — see the archived news file for full text)
- American Eagle options signal 13% move around Dec. 2 earnings By Investing.com - Investing (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_egal.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_egal.csv: last 292.50 on 2026-11-26
- openbb/EGAL_CA.csv: last 293.35 on 2026-11-25
- pandas-ta/indicators.csv: last 293.35 on 2026-11-25
- talib/indicators.csv: last 293.35 on 2026-11-25
- yahooquery/EGAL.CA.csv: last 302.00 on 2026-11-24
- Kronos forecast: 21 points, last 299.53 at 2026-12-23

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
- recommendation-unavailable: no profiles/EGAL.CA.recommendation.json
- reaction-profile-missing: no profiles/EGAL.CA.json
- sharia-row-missing: AAOIFI EGAL.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 EGAL.CA
- sharia-row-missing: FTSE EGAL.CA
- sharia-row-missing: ISLAMICLY EGAL.CA
- sharia-row-missing: MSCI EGAL.CA
- sharia-row-missing: MSCI_M EGAL.CA
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