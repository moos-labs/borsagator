# Borsagator report — FAIT.CA (2026-11-27)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite FAIT.CA market=EGX · shape: sweep-lite FAIT.CA market=EGX · market: EGX
Model: borsagator-report-model/2 · sweep: sweeps/2026-11-27/034145__sweep-lite-fait-ca-market-egx__runw6-sweeplite-fait-002 · archive commit: a62379f808d07cd46f9bcc880ee4178389da3e40

## Model range (from the forecast)

## Model range (from the forecast)
Model range low at 44.28
Model range high at 50.68
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: fundamentals +0.40 vs price-forecast -0.37 (spread +0.77)
- price-forecast: -0.37
- technicals: +0.30
- sentiment: +0.06
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×1.000, sentiment ×1.000, technicals ×1.000
Confidence basis: frozen v2 (factors 1.0 until n>=30 per family, #594)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: flat +0.00% (range -2.71% … +2.71%, confidence 0.45)
- week: flat +0.00% (range -6.75% … +6.75%, confidence 0.45)
- month: flat +0.00% (range -12.96% … +12.96%, confidence 0.45)
Base price: 47.48 (egx-data/egxpy_fait.csv, 2026-11-26)
Price cross-check: agree (common date 2026-11-24, base date 2026-11-26)
Witnesses stale: common date 2026-11-24 trails base date 2026-11-26.
- egx-data/egxpy_fait.csv: 47.48 on 2026-11-26
- openbb/FAIT_CA.csv: 46.15 on 2026-11-25 (stale)
- pandas-ta/indicators.csv: 46.15 on 2026-11-25 (stale)
- talib/indicators.csv: 46.15 on 2026-11-25 (stale)
- yahooquery/FAIT.CA.csv: 45.85 on 2026-11-24 (stale)

## Reaction profile

## Reaction profile
No reaction profile for this ticker — no nudge applied.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: FAIT.CA.csv_last_close, FAIT.CA.csv_last_date, rows_FAIT.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: FAIT_CA.csv_last_close, FAIT_CA.csv_last_date, rows_FAIT_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_fait.csv_last_close, egxpy_fait.csv_last_date, rows_egxpy_fait.csv, symbol, ticker
# EGX data sources for FAIT — verdict

No POUL reference material applies to FAIT; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-06-29 → 2026-11-26
- Latest: 2026-11-26 close 47.48

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — FAIT.CA

- Last session: **2026-11-25**
- Data used: 1930 rows (2019-01-01 → 2026-11-25), after dropping rows before 2019-01-01; 6113 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 45.85 |
| High | 46.7 |
| Low | 45.32 |
| Close | 46.15 |
| RSI(14) | 58.6795 |
| MACD | 0.5855 |
| MACD signal | 0.4519 |
| MACD histogram | 0.1336 |
| EMA(20) | 44.9488 |
| EMA(50) | 44.1302 |
| EMA(200) | 39.6737 |
| ADX(14) | 19.7987 |
| Bollinger upper | 47.3075 |
| Bollinger mid | 44.6325 |
| Bollinger lower | 41.9575 |
| Bollinger %B | 0.7836 |
| ATR(14) | 1.4896 |
| Stochastic %K | 65.5392 |
| Stochastic %D | 61.8288 |

## Trend read (facts only)

- Close 46.15 is above EMA_20 44.9488 (+2.67%).
- Close 46.15 is above EMA_50 44.1302 (+4.58%).
- Close 46.15 is above EMA_200 39.6737 (+16.32%).
- RSI(14) is 58.6795, in the neutral zone (30-70).
- MACD 0.5855 is above its signal line 0.4519 (histogram 0.1336).
- Price sits at %B 0.7836 of the Bollinger range (lower 41.9575, mid 44.6325, upper 47.3075).
- ADX(14) is 19.7987, indicating a weak / no clear trend (< 20).
- Stochastic %K 65.5392 is above %D 61.8288.
- ATR(14) is 1.4896 (3.23% of the close).

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
# Fundamentals (generic) — FAIT.CA

Source: StockAnalysis.com EGX pages, fetched 2026-11-27T03:38:19.384814+00:00. Vendor statement basis; per-share figures computed here, never copied.

Shares: 637850000.0 (vendor shares outstanding (may lag corporate actions)). Live price: 46.150001525878906.

Periods: TTM, FY2025, FY2024, FY2023, FY2022, FY2021. Latest FY block: {"revenue_EGPm": {"value": 12018.0, "basis": "vendor income statement"}, "net_income_EGPm": {"value": 4304.0, "basis": "vendor income statement"}, "net_margin_pct": {"value": 35.81, "basis": "vendor net income / revenue"}, "roe_pct": {"value": 9.72, "basis": "vendor net income / period-end shareholders' equity"}, "roa_pct": {"value": 1.63, "basis": "vendor net income / period-end total assets"}, "debt_to_equity_x": {"value": 0.003, "basis": "vendor total debt / equity"}, "ocf_margin_pct": {"value": -35.87, "basis": "operating cash flow / revenue"}, "fcf_margin_pct": {"value": -55.65, "basis": 

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 10
- Label counts: positive=0, negative=1, neutral=9
- Mean probabilities: positive=0.1219, negative=0.1784, neutral=0.6996

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.0577 | 0.0176 | 0.9248 | Kedjevara - Ça Fait Mal (Mp3 Download) - TrendyHipHop |
| 2 | neutral | 0.0177 | 0.4699 | 0.5124 | Dylan Larkin's agent breaks down trade between Canadiens, Red Wings - Sportsnet.ca |
| 3 | neutral | 0.1400 | 0.0177 | 0.8423 | La conjointe de PSPP publie une rare photo de famille et ça fait grandement réagir - Monde de Stars |
| 4 | negative | 0.0180 | 0.9249 | 0.0571 | California sues OpenAI over safety concerns after rogue agent hacking - The Guardian |
| 5 | neutral | 0.3249 | 0.0383 | 0.6367 | Team Canada wins silver at IIHF Women’s World Championship - Canadian Olympic Committee |
| 6 | neutral | 0.1395 | 0.0252 | 0.8353 | Gilonne Guigonnat : « je suis vraiment contente, ça a payé donc c'est cool ! » - ski-nordique.net |
| 7 | neutral | 0.0415 | 0.1012 | 0.8573 | What the Jensen Huang scandal means for Trump and his administration - CBC |
| 8 | neutral | 0.1156 | 0.0825 | 0.8019 | Culture minister insists Canada will eventually force streaming giants to pay fair share for CanCon - CTV News |
| 9 | neutral | 0.1169 | 0.0114 | 0.8717 | Kamik relaunches back to its roots: Canada's original Bad Weather Boot company - PR Newswire Canada |
| 10 | neutral | 0.2477 | 0.0956 | 0.6568 | Ottawa wants us all to have emergency supplies for 3 days. The good news is, that number hasn't changed - CBC |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 10
- Label counts: positive=1, negative=1, neutral=8
- Mean probabilities: positive=0.1001, negative=0.1068, neutral=0.7931

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Kedjevara - Ça Fait Mal (Mp3 Download) - TrendyHipHop |
| 2 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Dylan Larkin's agent breaks down trade between Canadiens, Red Wings - Sportsnet.ca |
| 3 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | La conjointe de PSPP publie une rare photo de famille et ça fait grandement réagir - Monde de Stars |
| 4 | negative | Negative | 0.0000 | 0.9980 | 0.0020 | California sues OpenAI over safety concerns after rogue agent hacking - The Guardian |
| 5 | positive | Positive | 1.0000 | 0.0000 | 0.0000 | Team Canada wins silver at IIHF Women’s World Championship - Canadian Olympic Committee |
| 6 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Gilonne Guigonnat : « je suis vraiment contente, ça a payé donc c'est cool ! » - ski-nordique.net |
| 7 | neutral | Neutral | 0.0000 | 0.0661 | 0.9339 | What the Jensen Huang scandal means for Trump and his administration - CBC |
| 8 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Culture minister insists Canada will eventually force streaming giants to pay fair share for CanCon - CTV News |
| 9 | neutral | Neutral | 0.0001 | 0.0000 | 0.9999 | Kamik relaunches back to its roots: Canada's original Bad Weather Boot company - PR Newswire Canada |
| 10 | neutral | Neutral | 0.0008 | 0.0034 | 0.9959 | Ottawa wants us all to have emergency supplies for 3 days. The good news is, that number hasn't changed - CBC |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 10
- Label counts: positive=6, negative=2, neutral=2
- Mean probabilities: positive=0.5591, negative=0.1911, neutral=0.2498

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | neutral | 0.0006 | 0.0004 | 0.9990 | Kedjevara - Ça Fait Mal (Mp3 Download) - TrendyHipHop |
| 2 | neutral | neutral | 0.0005 | 0.0003 | 0.9992 | Dylan Larkin's agent breaks down trade between Canadiens, Red Wings - Sportsnet.ca |
| 3 | positive | positive | 0.7734 | 0.0004 | 0.2262 | La conjointe de PSPP publie une rare photo de famille et ça fait grandement réagir - Monde de Stars |
| 4 | negative | negative | 0.0009 | 0.9952 | 0.0039 | California sues OpenAI over safety concerns after rogue agent hacking - The Guardian |
| 5 | positive | positive | 0.9976 | 0.0008 | 0.0017 | Team Canada wins silver at IIHF Women’s World Championship - Canadian Olympic Committee |
| 6 | positive | positive | 0.9750 | 0.0002 | 0.0248 | Gilonne Guigonnat : « je suis vraiment contente, ça a payé donc c'est cool ! » - ski-nordique.net |
| 7 | negative | negative | 0.0006 | 0.9130 | 0.0864 | What the Jensen Huang scandal means for Trump and his administration - CBC |
| 8 | positive | positive | 0.9813 | 0.0002 | 0.0184 | Culture minister insists Canada will eventually force streaming giants to pay fair share for CanCon - CTV News |
| 9 | positive | positive | 0.9911 | 0.0003 | 0.0086 | Kamik relaunches back to its roots: Canada's original Bad Weather Boot company - PR Newswire Canada |
| 10 | positive | positive | 0.8704 | 0.0002 | 0.1294 | Ottawa wants us all to have emergency supplies for 3 days. The good news is, that number hasn't changed - CBC |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — FAIT.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, samples=32 draws aggregated per step by median; forecast.csv also carries close_p10/close_p90 across draws)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-24 — 40 sessions
- Context supplied to Kronos: 40 sessions, no truncation needed (max_context=512; upstream predict() normalises over all supplied bars but attends over only the last max_context — borsagator #436)
- Upstream Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (pinned target: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`)
- Hugging Face revisions: model `NeoQuasar/Kronos-small` @ 901c26c1332695a2a8f243eb2f37243a37bea320; tokenizer `NeoQuasar/Kronos-Tokenizer-base` @ 0e0117387f39004a9016484a186a908917e22426
- Dependency versions: torch 2.15.0+cpu, pandas 2.2.2, numpy 2.5.5, transformers not installed, yahooquery 2.4.1
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 45.849998474121094 on 2026-11-24
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-25: 45.7852
- 2026-11-26: 45.7182
- 2026-11-29: 45.7661
- 2026-11-30: 45.86
- 2026-12-01: 45.9238
- 2026-12-02: 45.8546
- 2026-12-03: 45.8829
- 2026-12-06: 46.0031
- 2026-12-07: 45.7209
- 2026-12-08: 45.5418
- 2026-12-09: 45.2232
- 2026-12-10: 45.3844
- 2026-12-13: 45.4931
- 2026-12-14: 45.0848
- 2026-12-15: 44.9992
- 2026-12-16: 45.0165
- 2026-12-17: 44.7769
- 2026-12-20: 44.8299
- 2026-12-21: 44.5352
- 2026-12-22: 44.5529
- 2026-12-23: 44.3169

**Change over the 21 sessions (last forecasted close vs last actual close): -3.34%**

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
News: 14 · disclosures: 0 · identity scheme: resolved_url|title-date-hash
- بالفيديو.. غويري يسجل مجددا ويمنح مارسيليا انتصارا ثمينا - Awras
- يتعاون سكان كومونة نغوين فيت خاي لبناء سدود ترابية "لحماية الأراضي والطرق". - Vietnam.vn
- Un mot, une histoire - Le mot de Philippe Jaenada: «Pignouf» - Le français facile avec RFI
- Dylan Larkin's agent breaks down trade between Canadiens, Red Wings - Sportsnet.ca
- Le jeu vidéo GTA fait son grand retour! - Le français facile avec RFI
- شارك أكثر من 700 عامل وشاب من كا ماو في المهرجان الثقافي لعام 2026. - Vietnam.vn
- أزمة الطماطم تجمع الوزير بالمنتجين - Hespress
- What the Jensen Huang scandal means for Trump and his administration - CBC
- «ولادة ملكة»: العرض الأخير في لو بوتي جيمناز يوم 19 نوفمبر - Sortir à Paris
- Industrie automobile : Stellantis fait d'Alger son nouveau pôle stratégique pour dix pays africains - El Watan
- محامون يلاحقون وزير الداخلية الفرنسي - Hespress
- توقيف مهاجرين غير نظاميين داخل المنازل يثير جدلا حقوقيا في بلجيكا - Hespress
- Ottawa wants us all to have emergency supplies for 3 days. The good news is, that number hasn't changed - CBC
- "البيجيدي" يدفع بمصادرة المنافع والحرمان من التوظيف لمنع تنازع المصالح - Hespress

## Disclosure events

## Disclosure events
Disclosure events: 0 (0 confirmed, 0 candidates) · status: missing
Reason: no disclosure-events/FAIT-events.json in sweep dir

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.12
- finbert_positive: 0.14
- multilingual_positive: 0.27
- multilingual_negative: 0.45
- translated_positive: 0.20
- translated_negative: 0.25
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
Chart: egx-data/egxpy_fait.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_fait.csv: last 47.48 on 2026-11-26
- openbb/FAIT_CA.csv: last 46.15 on 2026-11-25
- pandas-ta/indicators.csv: last 46.15 on 2026-11-25
- talib/indicators.csv: last 46.15 on 2026-11-25
- yahooquery/FAIT.CA.csv: last 45.85 on 2026-11-24
- Kronos forecast: 21 points, last 44.32 at 2026-12-23

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
- recommendation-unavailable: no profiles/FAIT.CA.recommendation.json
- reaction-profile-missing: no profiles/FAIT.CA.json
- sharia-row-missing: AAOIFI FAIT.CA
- sharia-table-missing: DJIM
- sharia-row-missing: EGX33 FAIT.CA
- sharia-row-missing: FTSE FAIT.CA
- sharia-row-missing: ISLAMICLY FAIT.CA
- sharia-row-missing: MSCI FAIT.CA
- sharia-row-missing: MSCI_M FAIT.CA
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