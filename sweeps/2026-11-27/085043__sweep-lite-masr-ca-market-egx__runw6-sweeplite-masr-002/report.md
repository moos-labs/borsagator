# Borsagator report — MASR.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite MASR.CA market=EGX · shape: sweep-lite MASR.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/085043__sweep-lite-masr-ca-market-egx__runw6-sweeplite-masr-002 · archive commit: 3546cb18bf21a42e6c0eb60509f6d6f3c5758381

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 5.40
Model range high at 7.30
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs technicals -0.30 (spread +0.70)
- price-forecast: +0.14
- technicals: -0.30
- sentiment: -0.16
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -6.04% … +6.04%, confidence 0.30)
- week: flat +0.00% (range -15.03% … +15.03%, confidence 0.30)
- month: flat +0.00% (range -28.88% … +28.88%, confidence 0.30)
Base price: 6.35 (egx-data/egxpy_masr.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-25, base date 2026-11-26)
Witnesses stale: common date 2026-11-25 trails base date 2026-11-26.
- egx-data/egxpy_masr.csv: 6.35 on 2026-11-26
- openbb/MASR_CA.csv: 6.35 on 2026-11-26
- pandas-ta/indicators.csv: 6.35 on 2026-11-26
- talib/indicators.csv: 6.35 on 2026-11-26
- yahooquery/MASR.CA.csv: 6.23 on 2026-11-25 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: MASR.CA.csv_last_close, MASR.CA.csv_last_date, rows_MASR.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: MASR_CA.csv_last_close, MASR_CA.csv_last_date, rows_MASR_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_masr.csv_last_close, egxpy_masr.csv_last_date, rows_egxpy_masr.csv, symbol, ticker
# EGX data sources for MASR — verdict

No POUL reference material applies to MASR; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-07-22 → 2026-11-26
- Latest: 2026-11-26 close 6.35

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — MASR.CA

- Last session: **2026-11-26**
- Data used: 1931 rows (2019-01-01 → 2026-11-26), after dropping rows before 2019-01-01; 6538 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 6.23 |
| High | 6.35 |
| Low | 6.19 |
| Close | 6.35 |
| RSI(14) | 42.3043 |
| MACD | -0.1983 |
| MACD signal | -0.1774 |
| MACD histogram | -0.0209 |
| EMA(20) | 6.5881 |
| EMA(50) | 6.9275 |
| EMA(200) | 6.7004 |
| ADX(14) | 20.9512 |
| Bollinger upper | 7.1577 |
| Bollinger mid | 6.6345 |
| Bollinger lower | 6.1113 |
| Bollinger %B | 0.2281 |
| ATR(14) | 0.2804 |
| Stochastic %K | 28.2282 |
| Stochastic %D | 25.4254 |

## Trend read (facts only)

- Close 6.35 is below EMA_20 6.5881 (-3.61%).
- Close 6.35 is below EMA_50 6.9275 (-8.34%).
- Close 6.35 is below EMA_200 6.7004 (-5.23%).
- RSI(14) is 42.3043, in the neutral zone (30-70).
- MACD -0.1983 is below its signal line -0.1774 (histogram -0.0209).
- Price sits at %B 0.2281 of the Bollinger range (lower 6.1113, mid 6.6345, upper 7.1577).
- ADX(14) is 20.9512, indicating a developing trend (20-25).
- Stochastic %K 28.2282 is above %D 25.4254.
- ATR(14) is 0.2804 (4.42% of the close).

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

Data: Yahoo chart API (direct), 2189 sessions, 2018-01-01 → 2026-11-26 (Africa/Cairo).

## (1) Daily returns from 2026-09-28 (window start 2026-09-28)

- Sessions: 42 (41 daily returns)
- Close: 9.7100 → 6.8300
- Cumulative return: -29.66%
- Sharpe: -2.8831
- Sortino: -3.1275
- Max drawdown: -34.66%
- Volatility (annualised): 66.46%
- Daily win rate: 41.5%
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
- Data: 2438 rows, 2017-01-02 → 2026-11-26 (first close 3.6559998989105225, last close 6.829999923706055)
- Attempts: POUL.CA via yf_download_ignore_tz (0 rows), POUL.CA via yf_ticker_history (0 rows), POUL.CA via yahoo_chart_api (2438 rows)

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
# Fundamentals (generic) — MASR.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T08:42:34.604370+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 2135000000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 6.349999904632568.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 11710.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 3157.0, "basis": "vendor income statement"}, "gross_margin_pct": {"value": 59.97, "basis": "vendor gross profit / revenue"}, "operating_margin_pct": {"value": 39.01, "basis": "vendor operating income / revenue"}, "net_margin_pct": {"value": 26.96, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 25.01, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 7.29, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 31
- Label counts: positive=2, negative=13, neutral=16
- Mean probabilities: positive=0.0921, negative=0.3938, neutral=0.5141

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.1352 | 0.0079 | 0.8569 | Orange Egypt Doubles Customer Donations to Ahl Masr Burn Hospital Through Orange Cash - Sponsored - Advertising - Ahram Online |
| 2 | neutral | 0.0235 | 0.0278 | 0.9487 | Roundhill Space & Technology ETF (MARS) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 3 | neutral | 0.0779 | 0.0282 | 0.8939 | Rights Group Calls on Egypt to Reverse Mada Masr Shutdown - allAfrica.com |
| 4 | negative | 0.0317 | 0.6075 | 0.3608 | Egypt Court Hears Mada Masr Appeal as Editor Faces Retrial - https://streamlinefeed.co.ke/ |
| 5 | negative | 0.0156 | 0.8245 | 0.1599 | Egypt: Authorities must reverse decision to close Mada Masr and drop all charges against its editor in chief Lina Attalah - Amnesty International |
| 6 | positive | 0.5129 | 0.1472 | 0.3399 | Bruno Mars shares heartbreaking post announcing father’s dead - Nine.com.au |
| 7 | neutral | 0.0415 | 0.0593 | 0.8991 | Bruno Mars' father, Peter Hernandez, passes away; singer shares emotional tribute - ANI News |
| 8 | neutral | 0.0314 | 0.0514 | 0.9172 | Bruno Mars shares news of father Peter Hernandez's death - The News International |
| 9 | negative | 0.0122 | 0.8854 | 0.1024 | Egyptian court suspends retrial of Mada Masr editor Lina Attalah - The National |
| 10 | neutral | 0.0467 | 0.2812 | 0.6721 | "The world cannot afford to lose the vital reporting that Mada Masr provides." - Progressive International |
| 11 | neutral | 0.0354 | 0.0499 | 0.9147 | Mada Masr’s Lina Attalah due to appear before court in Egypt - Al Jazeera |
| 12 | negative | 0.0141 | 0.8543 | 0.1316 | Egypt court suspends trial of Mada Masr editor Lina Attalah - Africanews |
| 13 | neutral | 0.0290 | 0.0615 | 0.9095 | The Sham Case Against Mada Masr - Columbia Journalism Review |
| 14 | neutral | 0.0420 | 0.2740 | 0.6840 | ‘I’m not ready to go to jail’: co-founder of Egypt’s last independent media outlet faces prison - The Guardian |
| 15 | positive | 0.9429 | 0.0177 | 0.0394 | Madinet Masr stock: 9M sales rise 25% to EGP 45.4 billion - ad-hoc-news.de |
| 16 | negative | 0.0484 | 0.6430 | 0.3086 | Egypt’s Mada Masr Chief Lina Attalah’s Trial Postponed - Egyptian Streets |
| 17 | neutral | 0.0986 | 0.1894 | 0.7120 | Egypt’s independent press fights to survive as Mada Masr editor returns to court - The Straits Times |
| 18 | negative | 0.0492 | 0.6282 | 0.3226 | Cairo’s shut down of Mada Masr ‘an unprecedented attack’ on free press, says editor-in-chief - CNN |
| 19 | negative | 0.0209 | 0.7746 | 0.2044 | ‘We are not the problem,’ editor of news outlet that Egyptian court ordered to close tells AP - AP News |
| 20 | neutral | 0.0584 | 0.0460 | 0.8956 | Why Mada Masr and Lina Attalah’s fight matters for press freedom - The New Arab |
| 21 | neutral | 0.2496 | 0.0090 | 0.7414 | Fighting to Expand the Margins of Journalism in Egypt - Drop Site News |
| 22 | neutral | 0.1179 | 0.0193 | 0.8628 | Zamalek SC vs Masr Lel Taamen Lineups \| Egypt Cup · 6 Nov 2026 - YSscores |
| 23 | negative | 0.0212 | 0.6289 | 0.3499 | Egypt: Mada Masr faces closure, editor risks prison - Amnesty International Canada |
| 24 | negative | 0.0327 | 0.8684 | 0.0989 | Egypt’s crackdown on independent media reaches Mada Masr as editor faces trial - Global Voices |
| 25 | neutral | 0.0585 | 0.4119 | 0.5296 | Egypt’s Supreme Judicial Council rejects claims of trial irregularities in Mada Masr case - Courts & Law - Egypt - Ahram Online |
| 26 | negative | 0.0138 | 0.9387 | 0.0475 | Egyptian authorities have ordered independent news outlet Mada Masr to shut down and fined its Editor-in-Chief Lina Attalah after a court convicted her of managing an unlicensed website. The outlet insisted it first applied for a media license in 2018, but for y - Facebook |
| 27 | negative | 0.0105 | 0.9762 | 0.0133 | Equitas SFB shares tank 17% as CEO exit mars Q2 show, down 27% in 2 days - Business Standard |
| 28 | negative | 0.0105 | 0.9278 | 0.0617 | Egyptian court orders closure of news site Mada Masr and fines editor Lina Attalah, sparking international outcry - International Consortium of Investigative Journalists - ICIJ |
| 29 | neutral | 0.0291 | 0.0178 | 0.9531 | Zamalek - Misr Insurance 3-2 - Flashscore.co.za |
| 30 | neutral | 0.0339 | 0.0454 | 0.9207 | How to host your neighbours this October and have a Halloween to remember - Daily Hive |
| 31 | negative | 0.0094 | 0.9054 | 0.0852 | Egypt: Court orders to shut down investigative media outlet Mada Masr - International Federation of Journalists - IFJ |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 31
- Label counts: positive=2, negative=3, neutral=26
- Mean probabilities: positive=0.0647, negative=0.1246, neutral=0.8108

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0026 | 0.0000 | 0.9973 | Orange Egypt Doubles Customer Donations to Ahl Masr Burn Hospital Through Orange Cash - Sponsored - Advertising - Ahram Online |
| 2 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Roundhill Space & Technology ETF (MARS) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 3 | neutral | Neutral | 0.0000 | 0.0002 | 0.9998 | Rights Group Calls on Egypt to Reverse Mada Masr Shutdown - allAfrica.com |
| 4 | neutral | Neutral | 0.0001 | 0.0009 | 0.9990 | Egypt Court Hears Mada Masr Appeal as Editor Faces Retrial - https://streamlinefeed.co.ke/ |
| 5 | neutral | Neutral | 0.0000 | 0.0009 | 0.9991 | Egypt: Authorities must reverse decision to close Mada Masr and drop all charges against its editor in chief Lina Attalah - Amnesty International |
| 6 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Bruno Mars shares heartbreaking post announcing father’s dead - Nine.com.au |
| 7 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Bruno Mars' father, Peter Hernandez, passes away; singer shares emotional tribute - ANI News |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Bruno Mars shares news of father Peter Hernandez's death - The News International |
| 9 | neutral | Neutral | 0.0002 | 0.3335 | 0.6663 | Egyptian court suspends retrial of Mada Masr editor Lina Attalah - The National |
| 10 | negative | Negative | 0.0002 | 0.9989 | 0.0009 | "The world cannot afford to lose the vital reporting that Mada Masr provides." - Progressive International |
| 11 | neutral | Neutral | 0.0000 | 0.0070 | 0.9930 | Mada Masr’s Lina Attalah due to appear before court in Egypt - Al Jazeera |
| 12 | neutral | Neutral | 0.0001 | 0.0340 | 0.9658 | Egypt court suspends trial of Mada Masr editor Lina Attalah - Africanews |
| 13 | neutral | Neutral | 0.0008 | 0.1381 | 0.8611 | The Sham Case Against Mada Masr - Columbia Journalism Review |
| 14 | neutral | Neutral | 0.0000 | 0.0004 | 0.9996 | ‘I’m not ready to go to jail’: co-founder of Egypt’s last independent media outlet faces prison - The Guardian |
| 15 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Madinet Masr stock: 9M sales rise 25% to EGP 45.4 billion - ad-hoc-news.de |
| 16 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Egypt’s Mada Masr Chief Lina Attalah’s Trial Postponed - Egyptian Streets |
| 17 | neutral | Neutral | 0.0001 | 0.0432 | 0.9567 | Egypt’s independent press fights to survive as Mada Masr editor returns to court - The Straits Times |
| 18 | neutral | Neutral | 0.0000 | 0.0248 | 0.9751 | Cairo’s shut down of Mada Masr ‘an unprecedented attack’ on free press, says editor-in-chief - CNN |
| 19 | neutral | Neutral | 0.0000 | 0.0055 | 0.9944 | ‘We are not the problem,’ editor of news outlet that Egyptian court ordered to close tells AP - AP News |
| 20 | neutral | Neutral | 0.0003 | 0.0090 | 0.9906 | Why Mada Masr and Lina Attalah’s fight matters for press freedom - The New Arab |
| 21 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Fighting to Expand the Margins of Journalism in Egypt - Drop Site News |
| 22 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Zamalek SC vs Masr Lel Taamen Lineups \| Egypt Cup · 6 Nov 2026 - YSscores |
| 23 | negative | Negative | 0.0001 | 0.8631 | 0.1369 | Egypt: Mada Masr faces closure, editor risks prison - Amnesty International Canada |
| 24 | neutral | Neutral | 0.0000 | 0.0006 | 0.9994 | Egypt’s crackdown on independent media reaches Mada Masr as editor faces trial - Global Voices |
| 25 | neutral | Neutral | 0.0000 | 0.0010 | 0.9989 | Egypt’s Supreme Judicial Council rejects claims of trial irregularities in Mada Masr case - Courts & Law - Egypt - Ahram Online |
| 26 | neutral | Neutral | 0.0004 | 0.3865 | 0.6131 | Egyptian authorities have ordered independent news outlet Mada Masr to shut down and fined its Editor-in-Chief Lina Attalah after a court convicted her of managing an unlicensed website. The outlet insisted it first applied for a media license in 2018, but for y - Facebook |
| 27 | negative | Negative | 0.0000 | 1.0000 | 0.0000 | Equitas SFB shares tank 17% as CEO exit mars Q2 show, down 27% in 2 days - Business Standard |
| 28 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Egyptian court orders closure of news site Mada Masr and fines editor Lina Attalah, sparking international outcry - International Consortium of Investigative Journalists - ICIJ |
| 29 | neutral | Neutral | 0.0001 | 0.0006 | 0.9993 | Zamalek - Misr Insurance 3-2 - Flashscore.co.za |
| 30 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | How to host your neighbours this October and have a Halloween to remember - Daily Hive |
| 31 | neutral | Neutral | 0.0000 | 0.0127 | 0.9873 | Egypt: Court orders to shut down investigative media outlet Mada Masr - International Federation of Journalists - IFJ |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 31
- Label counts: positive=5, negative=13, neutral=13
- Mean probabilities: positive=0.1575, negative=0.4026, neutral=0.4399

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9981 | 0.0007 | 0.0012 | Orange Egypt Doubles Customer Donations to Ahl Masr Burn Hospital Through Orange Cash - Sponsored - Advertising - Ahram Online |
| 2 | neutral | neutral | 0.0005 | 0.0002 | 0.9993 | Roundhill Space & Technology ETF (MARS) Stock Price, News, Quote & History - Yahoo! Finance Canada |
| 3 | positive | positive | 0.8905 | 0.0005 | 0.1091 | Rights Group Calls on Egypt to Reverse Mada Masr Shutdown - allAfrica.com |
| 4 | neutral | neutral | 0.0009 | 0.0594 | 0.9397 | Egypt Court Hears Mada Masr Appeal as Editor Faces Retrial - https://streamlinefeed.co.ke/ |
| 5 | neutral | neutral | 0.0024 | 0.0005 | 0.9971 | Egypt: Authorities must reverse decision to close Mada Masr and drop all charges against its editor in chief Lina Attalah - Amnesty International |
| 6 | negative | negative | 0.0002 | 0.9912 | 0.0085 | Bruno Mars shares heartbreaking post announcing father’s dead - Nine.com.au |
| 7 | neutral | neutral | 0.0004 | 0.0033 | 0.9963 | Bruno Mars' father, Peter Hernandez, passes away; singer shares emotional tribute - ANI News |
| 8 | negative | negative | 0.0004 | 0.9133 | 0.0863 | Bruno Mars shares news of father Peter Hernandez's death - The News International |
| 9 | negative | negative | 0.0085 | 0.6293 | 0.3622 | Egyptian court suspends retrial of Mada Masr editor Lina Attalah - The National |
| 10 | neutral | neutral | 0.0387 | 0.0003 | 0.9610 | "The world cannot afford to lose the vital reporting that Mada Masr provides." - Progressive International |
| 11 | neutral | neutral | 0.0004 | 0.0054 | 0.9942 | Mada Masr’s Lina Attalah due to appear before court in Egypt - Al Jazeera |
| 12 | neutral | neutral | 0.1025 | 0.0230 | 0.8746 | Egypt court suspends trial of Mada Masr editor Lina Attalah - Africanews |
| 13 | negative | negative | 0.0027 | 0.8623 | 0.1351 | The Sham Case Against Mada Masr - Columbia Journalism Review |
| 14 | negative | negative | 0.0002 | 0.9980 | 0.0018 | ‘I’m not ready to go to jail’: co-founder of Egypt’s last independent media outlet faces prison - The Guardian |
| 15 | positive | positive | 0.9982 | 0.0009 | 0.0009 | Madinet Masr stock: 9M sales rise 25% to EGP 45.4 billion - ad-hoc-news.de |
| 16 | negative | negative | 0.0003 | 0.9983 | 0.0014 | Egypt’s Mada Masr Chief Lina Attalah’s Trial Postponed - Egyptian Streets |
| 17 | neutral | neutral | 0.0037 | 0.0004 | 0.9958 | Egypt’s independent press fights to survive as Mada Masr editor returns to court - The Straits Times |
| 18 | negative | negative | 0.0004 | 0.9989 | 0.0007 | Cairo’s shut down of Mada Masr ‘an unprecedented attack’ on free press, says editor-in-chief - CNN |
| 19 | neutral | neutral | 0.0059 | 0.0010 | 0.9932 | ‘We are not the problem,’ editor of news outlet that Egyptian court ordered to close tells AP - AP News |
| 20 | neutral | neutral | 0.0008 | 0.0004 | 0.9988 | Why Mada Masr and Lina Attalah’s fight matters for press freedom - The New Arab |
| 21 | positive | positive | 0.9977 | 0.0005 | 0.0019 | Fighting to Expand the Margins of Journalism in Egypt - Drop Site News |
| 22 | neutral | neutral | 0.0006 | 0.0004 | 0.9990 | Zamalek SC vs Masr Lel Taamen Lineups \| Egypt Cup · 6 Nov 2026 - YSscores |
| 23 | negative | negative | 0.0003 | 0.9980 | 0.0017 | Egypt: Mada Masr faces closure, editor risks prison - Amnesty International Canada |
| 24 | negative | negative | 0.0005 | 0.9985 | 0.0011 | Egypt’s crackdown on independent media reaches Mada Masr as editor faces trial - Global Voices |
| 25 | positive | positive | 0.8225 | 0.0008 | 0.1767 | Egypt’s Supreme Judicial Council rejects claims of trial irregularities in Mada Masr case - Courts & Law - Egypt - Ahram Online |
| 26 | negative | negative | 0.0004 | 0.9984 | 0.0012 | Egyptian authorities have ordered independent news outlet Mada Masr to shut down and fined its Editor-in-Chief Lina Attalah after a court convicted her of managing an unlicensed website. The outlet insisted it first applied for a media license in 2018, but for y - Facebook |
| 27 | negative | negative | 0.0003 | 0.9990 | 0.0007 | Equitas SFB shares tank 17% as CEO exit mars Q2 show, down 27% in 2 days - Business Standard |
| 28 | negative | negative | 0.0003 | 0.9989 | 0.0007 | Egyptian court orders closure of news site Mada Masr and fines editor Lina Attalah, sparking international outcry - International Consortium of Investigative Journalists - ICIJ |
| 29 | neutral | neutral | 0.0007 | 0.0004 | 0.9989 | Zamalek - Misr Insurance 3-2 - Flashscore.co.za |
| 30 | neutral | neutral | 0.0037 | 0.0002 | 0.9962 | How to host your neighbours this October and have a Halloween to remember - Daily Hive |
| 31 | negative | negative | 0.0009 | 0.9979 | 0.0011 | Egypt: Court orders to shut down investigative media outlet Mada Masr - International Federation of Journalists - IFJ |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — MASR.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-25 — 41 sessions
- Context supplied to Kronos: 41 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 6.230000019073486 on 2026-11-25
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-26: 6.2087
- 2026-11-29: 6.249
- 2026-11-30: 6.2574
- 2026-12-01: 6.2995
- 2026-12-02: 6.272
- 2026-12-03: 6.3096
- 2026-12-06: 6.4357
- 2026-12-07: 6.4463
- 2026-12-08: 6.4576
- 2026-12-09: 6.4349
- 2026-12-10: 6.4363
- 2026-12-13: 6.4498
- 2026-12-14: 6.4738
- 2026-12-15: 6.4313
- 2026-12-16: 6.3941
- 2026-12-17: 6.3713
- 2026-12-20: 6.3661
- 2026-12-21: 6.5551
- 2026-12-22: 6.5725
- 2026-12-23: 6.5626
- 2026-12-24: 6.6301

**Change over the 21 sessions (last forecasted close vs last actual close): +6.42%**

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
- أسعار الذهب في مصر اليوم الجمعة 27 نوفمبر 2026.. تحديث عيار 21 - CNN الاقتصادية
- الجنيه الذهب يرتفع 640 جنيهًا في مصر.. السعر يسجل 45040 مع قفزة الأوقية - اليوم السابع
- ارتفاع أم استقرار.. أسعار الذهب في مصر اليوم الجمعة 27 نوفمبر 2026 - اليوم السابع
- كارثة الوراق تهز مصر.. ماذا تكشف ردود الفعل على حريق صهريج الوقود؟ - DW.com
- الجنيه الذهب اليوم الجمعة في مصر عند 45040 جنيهًا - اليوم السابع
- جريمة قتل بدافع «الشرف» تُثير جدلاً في مصر - الشرق الأوسط
- مأساة هزّت مصر! 31 قتيلاً... من المسؤول؟ - DW.com
- سعر الذهب اليوم في مصر يرتفع بحلول التعاملات المسائية - Masrawy
- "حريق دائري الوراق".. تضامن عربي مع مصر وتعازٍ لأسر الضحايا - الشرق للأخبار
- ما ترتيب مصر في معدل وفيات الطرق؟ رقم صادم - Masrawy
- مصر.. النيابة تعلن ضبط المتهم بالتسبب في حادث "حريق دائري الوراق" - الشرق للأخبار
- بالصور والفيديو.. مشاهد من "حريق دائري الوراق" في مصر - الشرق للأخبار
- Roundhill Space & Technology ETF (MARS) Stock Price, News, Quote & History - Yahoo! Finance Canada
- مصر تعلن الحصيلة النهائية لحادث "دائري الوراق".. والنيابة تحقق في أسبابه - الشرق للأخبار
- وفاة 31 جراء حريق بعد انقلاب شاحنة على طريق في مصر - Reuters
- مصر.. قتلى ومصابون وسيارات متفحمة بحريق دائري الوراق - سكاي نيوز عربية
- مصر.. ضحايا ومصابون في حريق بالوراق أعلى الطريق الدائري بالجيزة - الشرق للأخبار
- على رأسها مصر.. المنتخبات المتأهلة لدور 32 في كأس العالم للناشئين - اليوم السابع
- "وجعكم وجعنا".. تضامن عربي واسع مع مصر عقب فاجعة شاحنة البترول في الوراق - الجزيرة نت
- أسعار الذهب اليوم فى مصر قبل إغلاق التداولات بالصاغة - اليوم السابع
- مصر.. انفجار وسط السيارات يوثق بداية مأساة الوراق - سكاي نيوز عربية
- مصر: توقيف شخص يشتبه في تسببه بحادث انقلاب شاحنة أوقع 31 قتيلا - France 24

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/MASR-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.06
- finbert_positive: 0.31
- multilingual_positive: 0.24
- multilingual_negative: 0.43
- translated_positive: 0.23
- translated_negative: 0.36
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- earnings event: أسعار الذهب في مصر اليوم الجمعة 27 نوفمبر 2026.. تحديث عيار 21 - CNN الاقتصادية
- legal event: جريمة قتل بدافع «الشرف» تُثير جدلاً في مصر - الشرق الأوسط
- earnings event: مصر.. النيابة تعلن ضبط المتهم بالتسبب في حادث "حريق دائري الوراق" - الشرق للأخبار
- أسعار الذهب في مصر اليوم الجمعة 27 نوفمبر 2026.. تحديث عيار 21 - CNN الاقتصادية (truncated title — see the archived news file for full text)
- جريمة قتل بدافع «الشرف» تُثير جدلاً في مصر - الشرق الأوسط (truncated title — see the archived news file for full text)
- مصر.. النيابة تعلن ضبط المتهم بالتسبب في حادث "حريق دائري الوراق" - الشرق للأخبار (truncated title — see the archived news file for full text)
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_masr.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_masr.csv: last 6.35 on 2026-11-26
- openbb/MASR_CA.csv: last 6.35 on 2026-11-26
- pandas-ta/indicators.csv: last 6.35 on 2026-11-26
- talib/indicators.csv: last 6.35 on 2026-11-26
- yahooquery/MASR.CA.csv: last 6.23 on 2026-11-25
- Kronos forecast: 21 points, last 6.63 at 2026-12-24

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
- witnesses-stale: common_date 2026-11-25 vs base_date 2026-11-26
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-unavailable: no profiles/MASR.CA.recommendation.json
- reaction-profile-missing: no profiles/MASR.CA.json
- sharia-row-missing: AAOIFI MASR.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 MASR.CA
- sharia-row-missing: FTSE MASR.CA
- sharia-row-missing: ISLAMICLY MASR.CA
- sharia-row-missing: MSCI MASR.CA
- sharia-row-missing: MSCI_M MASR.CA
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