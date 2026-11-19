# Borsagator report — POUL.CA (2026-11-19)

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Job: sweep-lite POUL.CA market=EGX · shape: sweep-lite POUL.CA market=EGX · market: EGX
Model: borsagator-report-model/1 · sweep: sweeps/2026-11-19/075206__sweep-lite-poul-ca-market-egx__runmanual-sweep-lite-2026-11-19-002 · archive commit: a66cee2f02914f27f2d36fcb67cfb32cacfe9b80

## Technical Support / Resistance Levels

## Technical Support / Resistance Levels
Technical Support Level at 6.74
Technical Resistance Level at 10.82
Basis: week horizon range_low_pct / range_high_pct (expected_move_pct +/- half-range, % of base)
> This is a description of a computed model output, not a recommendation to buy, sell, or hold any security. You must make your own investment decisions.
Recommendation not available for this sweep.

## Family scores

## Family scores
Families disagree: price-forecast +0.40 vs sentiment -0.02 (spread +0.42)
- price-forecast: +0.40
- technicals: +0.40
- sentiment: -0.02
- fundamentals: +0.40
- agent: no data
Applied weights (ledger): agent ×1.000, fundamentals ×1.000, price-forecast ×0.503, sentiment ×1.069, technicals ×0.717
Confidence basis: calibrated (ledger skill factors applied)

## What changed

## What changed
First sweep of this ticker + job shape — nothing to compare against yet.

## Horizons + price

## Horizons + price
- day: up +6.84% (range -7.99% … +21.67%, confidence 0.30)
- week: up +14.02% (range -12.46% … +40.49%, confidence 0.30)
- month: up +16.84% (range -35.34% … +69.03%, confidence 0.30)
Base price: 7.70 (egx-data/egxpy_poul.csv, 2026-11-18)
Price cross-check: agree (common date 2026-11-16, base date 2026-11-18)
Witnesses stale: common date 2026-11-16 trails base date 2026-11-18.
- egx-data/egxpy_poul.csv: 7.70 on 2026-11-18
- openbb/POUL_CA.csv: 7.57 on 2026-11-17 (stale)
- pandas-ta/indicators.csv: 7.57 on 2026-11-17 (stale)
- talib/indicators.csv: 7.57 on 2026-11-17 (stale)
- yahooquery/POUL.CA.csv: 8.02 on 2026-11-16 (stale)

## Reaction profile

## Reaction profile
Built at 2026-11-14T23:44:23Z · walk-forward train 3 / test 6 · hits 0 · baseline hits 0
- dividend: median +5d +5.93% (n=None)
- earnings: median +5d — (n=None)
- management: median +5d — (n=None)
- other: median +5d +0.95% (n=None)
Events: 22 recorded.

## Per-tool sections

## Per-tool sections
### yahooquery
Status: ok · exit code: 0
Summary keys: POUL.CA.csv_last_close, POUL.CA.csv_last_date, rows_POUL.CA.csv
No report for this tool.
### openbb
Status: ok · exit code: 0
Summary keys: POUL_CA.csv_last_close, POUL_CA.csv_last_date, rows_POUL_CA.csv
No report for this tool.
### egx-data
Status: ok · exit code: 0
Summary keys: egxpy_poul.csv_last_close, egxpy_poul.csv_last_date, rows_egxpy_poul.csv, symbol, ticker
# EGX data sources for POUL — verdict

Reference (Yahoo chart API): latest close 2026-11-09 = **9.99**. Reference ex-day opens (Investing, real opens): 2019-07-15 → 5.05, 2021-05-18 → 2.85, 2024-10-22 → 12.3, 2026-04-27 → 34.8.

## egxpy — ok
- Rows: 3000 · Range: 2014-06-11 → 2026-11-18
- Latest: 2026-11-18 close 7.7 (matches Yahoo 9.99: False)

| Ex-date | Investing open | Source open | Prior close (source) | Verdict |
|---|---|---|---|---|
| 2019-07-15 | 5.05 | 1.347526 | 1.347526 | matches prior close (Yahoo-style, not a real open) |
| 2021-05-18 | 2.85 | 0.79441674 | 0.79441674 | matches prior close (Yahoo-style, not a real open) |
| 2024-10-22 | 12.3 | 3.3213669 | 3.3213669 | matches prior close (Yahoo-style, not a real open) |
| 2026-04-27 | 34.8 | 9.46521784 | 9.46521784 | matches prior close (Yahoo-style, not a real open) |


## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.

### pandas-ta
Status: ok · exit code: 0
Summary keys: adx_14, atr_14, bb_lower, bb_mid, bb_pctb, bb_upper, close, date, drop_before, ema_20, ema_200, ema_50, first_date_used, high, indicators.csv_last_close, indicators.csv_last_date, last_date, low, macd, macd_hist
# Technical snapshot — POUL.CA

- Last session: **2026-11-17**
- Data used: 1924 rows (2019-01-01 → 2026-11-17), after dropping rows before 2019-01-01; 6524 rows fetched in total.

## Latest values

| Item | Value |
|---|---:|
| Open | 8.02 |
| High | 8.09 |
| Low | 7.51 |
| Close | 7.57 |
| RSI(14) | 17.2302 |
| MACD | -2.0931 |
| MACD signal | -2.6155 |
| MACD histogram | 0.5224 |
| EMA(20) | 10.401 |
| EMA(50) | 16.7439 |
| EMA(200) | 26.6439 |
| ADX(14) | 53.6397 |
| Bollinger upper | 10.9907 |
| Bollinger mid | 9.612 |
| Bollinger lower | 8.2333 |
| Bollinger %B | -0.2405 |
| ATR(14) | 0.7019 |
| Stochastic %K | 28.9238 |
| Stochastic %D | 58.3842 |

## Trend read (facts only)

- Close 7.57 is below EMA_20 10.401 (-27.22%).
- Close 7.57 is below EMA_50 16.7439 (-54.79%).
- Close 7.57 is below EMA_200 26.6439 (-71.59%).
- RSI(14) is 17.2302, in the oversold zone (<= 30).
- MACD -2.0931 is above its signal line -2.6155 (histogram 0.5224).
- Price sits at %B -0.2405 of the Bollinger range (lower 8.2333, mid 9.612, upper 10.9907).
- ADX(14) is 53.6397, indicating a strong trend by the standard ADX scale (>= 25).
- Stochastic %K 28.9238 is below %D 58.3842.
- ATR(14) is 0.7019 (9.27% of the close).

## Notes

- Source: Yahoo Finance chart API (raw daily OHLC, not dividend-adjusted), fetched directly — yfinance is not used because it crashes on Africa/Cairo DST timestamps.
- Indicators computed with pandas-ta-classic.

### talib
Status: ok · exit code: 0
Summary keys: indicators.csv_last_close, indicators.csv_last_date, last_close, last_date, rows_fetched, rows_indicators.csv, rows_used, ticker
No report for this tool.
### quantstats
Status: ok · exit code: 0
Summary keys: exchange_tz, ohlc.csv_last_close, rows, rows_ohlc.csv, source, ticker
# QuantStats report — POUL.CA

Data: Yahoo chart API (direct), 2182 sessions, 2018-01-01 → 2026-11-17 (Africa/Cairo).

## (1) Daily returns from 2026-09-28 (window start 2026-09-28)

- Sessions: 35 (34 daily returns)
- Close: 9.7100 → 7.5700
- Cumulative return: -22.04%
- Sharpe: -2.2940
- Sortino: -2.5282
- Max drawdown: -26.50%
- Volatility (annualised): 68.98%
- Daily win rate: 41.2%
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
- Data: 2431 rows, 2017-01-02 → 2026-11-17 (first close 3.6559998989105225, last close 7.570000171661377)
- Attempts: POUL.CA via yf_download_ignore_tz (0 rows), POUL.CA via yf_ticker_history (0 rows), POUL.CA via yahoo_chart_api (2431 rows)

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
Summary keys: company, input_csv
# Cairo Poultry (EGX: POUL) — Fundamental Ratios

Source data: `data/poul_statements.csv` — figures extracted **only** from the verified 10-Nov-2026 buy-decision research (company earnings releases, EGX disclosures, post-merger special-purpose statements). No figure was invented; gaps in the CSV are gaps in the verified record.

## Computation path

- Headline ratios: **computed directly with pandas/plain Python from the verified CSV** (traceable line-by-line).
- FinanceToolkit manual-statements API attempt: **ok**. Its raw outcome is preserved in `ratios.json` under `financetoolkit_attempt`.

## Computed ratios

### FY2025 (year to 31 Dec 2025)

| Ratio | Value | Basis |
|---|---|---|
| gross_margin_pct | 29.12 | gross profit (release definition) / revenue |
| ebitda_margin_pct | 19.58 | adjusted EBITDA / revenue |
| operating_margin_vendor_pct | 16.86 | vendor operating income / revenue |
| net_margin_total_pct | 18.26 | total NPAT / revenue |
| net_margin_special_purpose_pct | 18.53 | special-purpose NPAT / consolidated revenue |
| roe_pct | 39.37 | total NPAT / total equity at 31-Dec-2025 (period-end, no average available) |
| roe_special_purpose_pct | 39.25 | special-purpose NPAT / special-purpose equity at end-2025 |
| roa_pct | 27.00 | total NPAT / total assets at 31-Dec-2025 (period-end) |
| asset_turnover_x | 1.48 | revenue / total assets (period-end) |
| equity_multiplier_x | 1.46 | total assets / total equity (period-end) |
| debt_to_equity_x | 0.03 | total debt / total equity at 31-Dec-2025 |
| net_cash_EGPm | 4,299.00 | cash & investments - total debt at 31-Dec-2025 |
| ocf_margin_pct | 17.94 | operating cash flow / revenue |
| capex_to_revenue_pct | 9.81 | capex / revenue |
| fcf_margin_pct | 8.13 | free cash flow / revenue |
| fcf_conversion_pct | 44.50 | free cash flow / total NPAT |
| net_interest_income_pct_of_npat | 23.39 | net interest income / total NPAT |
| asset_sale_gains_pct_of_npat | 5.48 | gains on sale of assets / total NPAT |
| eps_post_merger_shares_consol_EGP | 1.62 | total NPAT / 1,789,351,397 post-merger shares |
| eps_post_merger_shares_special_EGP | 1.64 | special-purpose NPAT / post-merger shares |
| bvps_post_merger_consol_EGP | 4.10 | consolidated equity end-2025 / post-merger shares |
| bvps_post_merger_special_EGP | 4.17 | special-purpose equity end-2025 / post-merger shares |
| net_cash_per_share_end2025_EGP | 2.40 | net cash end-2025 / post-merger shares |
| dupont_roe_check_pct | 39.35 | net margin x asset turnover x equity multiplier (should equal roe_pct) |

### FY2024 (partial — see coverage)

| Ratio | Value | Basis |
|---|---|---|
| operating_margin_vendor_pct | 17.09 | vendor operating income / revenue |
| net_margin_eps_basis_pct | 14.81 | EPS-basis net income (after appropriations) / revenue |
| fcf_margin_pct | 15.09 | free cash flow / revenue |

### H1 2026 (six months to 30 Jun 2026)

| Ratio | Value | Basis |
|---|---|---|
| gross_margin_pct | 23.83 | release gross profit / revenue (6 months) |
| ebitda_margin_pct | 13.76 | adjusted EBITDA / revenue (6 months) |
| operating_margin_pct | 11.77 | release operating profit / revenue (6 months) |
| net_margin_pct | 16.08 | total NPAT / revenue (6 months) |
| debt_to_equity_x | 0.04 | total debt / total equity at 30-Jun-2026 |
| net_cash_EGPm | 3,921.00 | cash & investments - total debt at 30-Jun-2026 (research rounds this to 3,922 from unrounded inputs) |
| net_cash_per_share_EGP | 2.19 | net cash 30-Jun-2026 / post-merger shares |
| net_interest_income_pct_of_npat | 32.04 | net interest income / total NPAT (6 months) |

### FY2025 dividend (coupon #42, paid 18 Nov 2026)

| Ratio | Value | Basis |
|---|---|---|
| payout_vs_consolidated_npat_pct | 117.64 | EGP 3,399.77m dividend / FY2025 consolidated NPAT 2,890 |
| payout_vs_special_purpose_npat_pct | 115.95 | dividend / FY2025 special-purpose NPAT 2,932 |
| dividend_pct_of_distributable_pool | 67.70 | dividend / special-purpose distributable pool 5,022 |
| dividend_yield_at_reference_price_pct | 19.00 | 1.90 / 10.00 reference price (one-off, non-recurring) |

### Valuation snapshot at EGP 10.00 reference price (research price, not live)

| Ratio | Value | Basis |
|---|---|---|
| market_cap_EGPm | 17,893.50 | 10.00 x 1,789,351,397 shares |
| pe_consolidated_npat_x | 6.19 | price / EPS on post-merger shares (consolidated NPAT) |
| pe_special_purpose_npat_x | 6.10 | price / EPS on post-merger shares (special-purpose NPAT) |
| pb_special_purpose_x | 2.40 | price / special-purpose BVPS end-2025 |
| pb_consolidated_x | 2.44 | price / consolidated BVPS end-2025 |
| ev_ebitda_fy2025_x | 4.51 | (market cap - net cash Jun-2026) / FY2025 adjusted EBITDA |

## Coverage — standard ratios that could NOT be computed

| Ratio | Missing line item / blocker |
|---|---|
| current_ratio / quick_ratio / cash_ratio | Current assets and current liabilities are not split out in any verified source figure. |
| interest_coverage_ratio | Only NET interest income (+676 FY25) is disclosed in the sources; gross interest expense is not verified. |
| inventory_turnover / receivables_turnover / payables_turnover / cash_conversion_cycle | Inventory, receivables and payables balances do not appear in the verified sources. |
| return_on_invested_capital (ROIC) | NOPAT cannot be derived: the effective tax charge is not verified (pre-tax profit is given only approximately, ~EGP 3,667m). |
| effective_tax_rate | Pre-tax profit is stated only approximately in the sources. |
| altman_z_score / piotroski_f_score | Require full balance-sheet detail (working capital, current items) and, for Piotroski, two full years of balance sheets; not available in verified form. |
| roe / roa FY2024 | FY2024 total equity and total assets are not verified (special-purpose FY2024 equity was not disclosed in the source). |
| roa H1_2026 | Total assets at 30-Jun-2026 are not stated in the sources (only total liabilities and equity). |
| dividend_payout_ratio FY2024 | No FY2024 dividend per share appears in the extracted verified sources. |
| dupont FY2024 / H1_2026 | Needs total assets and equity for the same period-end; missing for FY2024 and (assets) for Jun-2026. |

## Caveats

- Balance-sheet ratios use **period-end** balances (no averaged balances exist in the verified sources), so ROE/ROA are point-in-time variants.
- Gross profit and EBITDA follow the **company earnings-release definitions**; a vendor definition (COGS incl. depreciation) gives lower gross profit (FY25: 3,338 vs 4,609).
- FY2024 is thin: total NPAT is reported only as a conflicting range (2,387–2,420), and FY2024 equity/assets are unverified, so FY2024 return ratios are blocked rather than estimated.
- The 19.0% dividend yield is a **one-off** return of accumulated retained earnings (payout >100% of FY2025 profit) and is not repeatable at this size.

### finbert
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT sentiment — live

- Model: `ProsusAI/finbert` (CPU)
- Texts scored: 14
- Label counts: positive=0, negative=2, neutral=12
- Mean probabilities: positive=0.0442, negative=0.1467, neutral=0.8091

| # | Predicted | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|--------|--------|--------|------|
| 1 | neutral | 0.1197 | 0.0185 | 0.8617 | Russian House in Cairo Opens Agricultural Innovation Festival for 100 Egyptian Students - Sada Elbalad English |
| 2 | neutral | 0.0291 | 0.0313 | 0.9395 | Rand Paul - Britannica |
| 3 | negative | 0.0075 | 0.9603 | 0.0322 | Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de |
| 4 | neutral | 0.0306 | 0.0273 | 0.9421 | Videos - Cathedral Phantoms (Los Angeles, CA) Football - MaxPreps |
| 5 | neutral | 0.0589 | 0.0365 | 0.9047 | Rebels Poul Andersen scores overtime winner against Hurricanes - rdnewsnow.com |
| 6 | neutral | 0.0753 | 0.0182 | 0.9065 | St. Paul High School (Santa Fe Springs, CA) Flag Football - MaxPreps |
| 7 | neutral | 0.0464 | 0.0190 | 0.9347 | Paul Mbong - Player profile 26/27 - Transfermarkt |
| 8 | neutral | 0.0455 | 0.0289 | 0.9255 | Cairo Poultry Q3 Consol Profit EGP 152 Million - TradingView |
| 9 | neutral | 0.0359 | 0.0217 | 0.9424 | Videos - Croatan Cougars (Newport, NC) Basketball - MaxPreps |
| 10 | neutral | 0.0596 | 0.0200 | 0.9204 | Cairo Poultry stock: board backs EGP 1.9 dividend proposal - ad-hoc-news.de |
| 11 | neutral | 0.0265 | 0.0520 | 0.9215 | Paul Kagame \| Biography, Education, & Facts - Britannica |
| 12 | neutral | 0.0251 | 0.0312 | 0.9437 | All About Paul McCartney’s 5 Children, Heather, Mary, Stella, James and Beatrice - People.com |
| 13 | neutral | 0.0319 | 0.0645 | 0.9036 | Childcare paedophile Ashley Paul Griffith extradited to NSW - ABC News & Headlines – Australian Broadcasting Corporation |
| 14 | negative | 0.0273 | 0.7241 | 0.2486 | Billionaire Paul Tudor Jones warns AI and IPOs could hit stocks hard in 2027. Protect your nest egg now - Yahoo Finance |

### finbert-tone
Status: ok · exit code: 0
Summary keys: count, label, model
# FinBERT-tone sentiment

- Model: `yiyanghkust/finbert-tone` (CPU)
- id2label: `{0: 'Neutral', 1: 'Positive', 2: 'Negative'}`
- Texts scored: 14
- Label counts: positive=1, negative=1, neutral=12
- Mean probabilities: positive=0.0715, negative=0.0733, neutral=0.8552

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | neutral | Neutral | 0.0002 | 0.0000 | 0.9998 | Russian House in Cairo Opens Agricultural Innovation Festival for 100 Egyptian Students - Sada Elbalad English |
| 2 | neutral | Neutral | 0.0001 | 0.0030 | 0.9969 | Rand Paul - Britannica |
| 3 | negative | Negative | 0.0149 | 0.9804 | 0.0048 | Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de |
| 4 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Videos - Cathedral Phantoms (Los Angeles, CA) Football - MaxPreps |
| 5 | positive | Positive | 0.9852 | 0.0001 | 0.0147 | Rebels Poul Andersen scores overtime winner against Hurricanes - rdnewsnow.com |
| 6 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | St. Paul High School (Santa Fe Springs, CA) Flag Football - MaxPreps |
| 7 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Paul Mbong - Player profile 26/27 - Transfermarkt |
| 8 | neutral | Neutral | 0.0000 | 0.0007 | 0.9993 | Cairo Poultry Q3 Consol Profit EGP 152 Million - TradingView |
| 9 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Videos - Croatan Cougars (Newport, NC) Basketball - MaxPreps |
| 10 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Cairo Poultry stock: board backs EGP 1.9 dividend proposal - ad-hoc-news.de |
| 11 | neutral | Neutral | 0.0000 | 0.0001 | 0.9999 | Paul Kagame \| Biography, Education, & Facts - Britannica |
| 12 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | All About Paul McCartney’s 5 Children, Heather, Mary, Stella, James and Beatrice - People.com |
| 13 | neutral | Neutral | 0.0000 | 0.0000 | 1.0000 | Childcare paedophile Ashley Paul Griffith extradited to NSW - ABC News & Headlines – Australian Broadcasting Corporation |
| 14 | neutral | Neutral | 0.0009 | 0.0417 | 0.9574 | Billionaire Paul Tudor Jones warns AI and IPOs could hit stocks hard in 2027. Protect your nest egg now - Yahoo Finance |

### financial-roberta
Status: ok · exit code: 0
Summary keys: count, label, model
# RoBERTa financial sentiment — live

- Model: `soleimanian/financial-roberta-large-sentiment` (CPU)
- id2label: `{0: 'negative', 1: 'neutral', 2: 'positive'}`
- Texts scored: 14
- Label counts: positive=3, negative=3, neutral=8
- Mean probabilities: positive=0.2143, negative=0.2118, neutral=0.5740

| # | Predicted | Raw label | P(pos) | P(neg) | P(neu) | Text |
|---|-----------|-----------|--------|--------|--------|------|
| 1 | positive | positive | 0.9974 | 0.0004 | 0.0022 | Russian House in Cairo Opens Agricultural Innovation Festival for 100 Egyptian Students - Sada Elbalad English |
| 2 | neutral | neutral | 0.0009 | 0.0006 | 0.9985 | Rand Paul - Britannica |
| 3 | negative | negative | 0.0003 | 0.9989 | 0.0008 | Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de |
| 4 | neutral | neutral | 0.0004 | 0.0002 | 0.9994 | Videos - Cathedral Phantoms (Los Angeles, CA) Football - MaxPreps |
| 5 | positive | positive | 0.9950 | 0.0004 | 0.0046 | Rebels Poul Andersen scores overtime winner against Hurricanes - rdnewsnow.com |
| 6 | neutral | neutral | 0.0006 | 0.0004 | 0.9990 | St. Paul High School (Santa Fe Springs, CA) Flag Football - MaxPreps |
| 7 | neutral | neutral | 0.0005 | 0.0003 | 0.9991 | Paul Mbong - Player profile 26/27 - Transfermarkt |
| 8 | neutral | neutral | 0.0042 | 0.0002 | 0.9955 | Cairo Poultry Q3 Consol Profit EGP 152 Million - TradingView |
| 9 | neutral | neutral | 0.0006 | 0.0002 | 0.9992 | Videos - Croatan Cougars (Newport, NC) Basketball - MaxPreps |
| 10 | positive | positive | 0.9977 | 0.0005 | 0.0018 | Cairo Poultry stock: board backs EGP 1.9 dividend proposal - ad-hoc-news.de |
| 11 | neutral | neutral | 0.0003 | 0.0002 | 0.9994 | Paul Kagame \| Biography, Education, & Facts - Britannica |
| 12 | neutral | neutral | 0.0004 | 0.0003 | 0.9993 | All About Paul McCartney’s 5 Children, Heather, Mary, Stella, James and Beatrice - People.com |
| 13 | negative | negative | 0.0007 | 0.9675 | 0.0318 | Childcare paedophile Ashley Paul Griffith extradited to NSW - ABC News & Headlines – Australian Broadcasting Corporation |
| 14 | negative | negative | 0.0005 | 0.9945 | 0.0051 | Billionaire Paul Tudor Jones warns AI and IPOs could hit stocks hard in 2027. Protect your nest egg now - Yahoo Finance |

### kronos
Status: ok · exit code: 0
Summary keys: forecast.csv_last_close, forecast.csv_last_date, rows_forecast.csv
# Kronos-small forecast — POUL.CA

- Model: `NeoQuasar/Kronos-small` with tokenizer `NeoQuasar/Kronos-Tokenizer-base` (CPU inference, seed 42, T=1.0, top_p=0.9, sample_count=1)
- Data source: yahooquery (yfinance is never used for Cairo tickers — Africa/Cairo DST crash; rows before 2019-01-01 dropped as corrupted)
- Context window used: 2026-09-28 to 2026-11-16 — 34 sessions
- Preferred post-merger context (from 2026-09-28) was accepted; no fallback needed.
- Last actual close: 8.020000457763672 on 2026-11-16
- Forecast horizon: next 21 sessions (Sun–Thu calendar; exchange holidays not modelled)

## Forecasted close path

- 2026-11-17: 8.4299
- 2026-11-18: 8.9487
- 2026-11-19: 8.9395
- 2026-11-22: 8.8856
- 2026-11-23: 9.2327
- 2026-11-24: 9.369
- 2026-11-25: 9.8036
- 2026-11-26: 9.8889
- 2026-11-29: 9.7787
- 2026-11-30: 9.8965
- 2026-12-01: 9.7372
- 2026-12-02: 9.8596
- 2026-12-03: 9.5399
- 2026-12-06: 9.6317
- 2026-12-07: 9.5663
- 2026-12-08: 9.7705
- 2026-12-09: 9.5258
- 2026-12-10: 9.2792
- 2026-12-13: 9.3683
- 2026-12-14: 9.2834
- 2026-12-15: 9.2756

**Change over the 21 sessions (last forecasted close vs last actual close): +15.66%**

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
News: 32 · disclosures: 10 · identity scheme: resolved_url|title-date-hash
- أسهم الأغذية في مصر: فوديكو تقفز 25% بعد حكم نهائي والقاهرة للدواجن توزع 1.9 جنيه - Investing.com
- الموسيقي العالمي بول ديفيس في مهرجان القاهرة: الصوت جزء من الحكاية السينمائية - الهيئة الوطنية للإعلام
- “سيساكو” و”بول ديفيز” يتصدران فعاليات أيام القاهرة لصناعة السينما - وطنى
- بول ديفيز بمهرجان القاهرة السينمائى: حولت إنذارات السيارات إلى موسيقى - اليوم السابع
- Russian House in Cairo Opens Agricultural Innovation Festival for 100 Egyptian Students - Sada Elbalad English
- بول ديفيز بالقاهرة السينمائى: اكتشفت شغفى بتصميم الصوت فى سن الـ15 - اليوم السابع
- بول ديفيز بمهرجان القاهرة السينمائي: تصميم الصوت ساعد في إقناع المنتجين برؤية مخرجة We Need to Talk About Kevin - اليوم السابع
- بول ديفيز بمهرجان القاهرة السينمائي: ديفيد لينش مصدر إلهامي وأستعين باللوحات الفنية - اليوم السابع
- بول ديفيس في ندوة بمهرجان القاهرة السينمائي.. مهندس الصوت البريطاني يكشف كيفية توظيف المؤثرات - أهل مصر
- القاهرة للدواجن تتصدر الأسهم الأكثر تراجعًا بالبورصة بخسائر 17% - شبكة تواصل الإخبارية
- القاهرة للدواجن تتصدر الأسهم الأكثر انخفاضا بالبورصة المصرية بنسبة 17% - https://www.youlyou.com/
- سقوط مفاجئ لأسهم المضاربات بأكثر من 2%.. والقاهرة للدواجن تقود التراجع بالبورصة - اليوم السابع
- Cairo Poultry stock: Nine-month profit drops 38.3% - ad-hoc-news.de
- البورصة تسمح بتحرك سعر سهم القاهرة للدواجن 35.19% هبوطاً وتحدد 27.09% للإيقاف المؤقت - مجلة البوصلة الاقتصادية
- بورصة مصر تعلن الحدود السعرية لتحركات سهم "القاهرة للدواجن" - Mubasher
- اليوم.. نهاية حق الحصول على التوزيع النقدي لـ القاهرة للدواجن - مجلة البوصلة الاقتصادية
- اليوم.. نهاية حق توزيع 1.9 جنيه لسهم "القاهرة للدواجن" - جريدة البورصة
- رغم ارتفاع الإيرادات.. أرباح القاهرة للدواجن تهبط 39% بأول 9 شهور من 2026 - https://www.youlyou.com/
- القاهرة للدواجن تسجل 1.43 مليار جنيه أرباحًا خلال 9 أشهر - عالم المال
- أرباح القاهرة للدواجن تنخفض إلى 1.4 مليار جنيه في 9 أشهر - مجلة البوصلة الاقتصادية
- أرباح القاهرة للدواجن تهبط 39.1% خلال 9 أشهر رغم نمو الإيرادات إلى 12.6 مليار جنيه - جريدة المال
- Cairo Poultry Q3 Consol Profit EGP 152 Million - TradingView
- العنوان: القاهرة للدواجن (POUL.CA) دعوة الجمعية العامة غير العادية المقرر انعقادها في 30/11/2026 في تمام الساعة 03:00 مساءًاسم الشركة: القاهرة ل - معلومات مباشر
- القاهرة للدواجن (POUL.CA) تعلن نتائج أعمالها المجمعة عن 9 أشهر
- القاهرة للدواجن (POUL.CA) تعلن نتائج أعمالها غير المجمعة عن 9 أشهر
- القاهرة للدواجن (POUL.CA) - قرارات مجلس إدارة الشركة
- القاهرة للدواجن (POUL.CA) - بيان من الهيئة العامة للرقابة المالية
- القاهرة للدواجن (POUL.CA) - محضر اجتماع الجمعية العامة العادية (موثق)
- القاهرة للدواجن (POUL.CA) تعلن عن توزيع نقدي
- القاهرة للدواجن (POUL.CA) - قرار لجنة القيد
- القاهرة للدواجن (POUL.CA) - قرار لجنة القيد
- القاهرة للدواجن (POUL.CA) - محضر اجتماع الجمعية العامة العادية (غير موثق)

## Sentiment + fundamentals

## Sentiment + fundamentals
- finbert_negative: 0.35
- finbert_positive: 0.05
- multilingual_positive: 0.51
- multilingual_negative: 0.03
- translated_positive: 0.15
- translated_negative: 0.26
- finbert: 
- finbert-tone: 
- financial-roberta: 
Company: 
Valuation ratios are not carried in the model — no corrected-valuation callout in this report.

## Risks

## Risks
Risk level: shock · confidence cap: 0.30
- earnings event: القاهرة للدواجن تتصدر الأسهم الأكثر تراجعًا بالبورصة بخسائر 17% - شبكة تواصل الإخبارية
- القاهرة للدواجن تتصدر الأسهم الأكثر تراجعًا بالبورصة بخسائر 17% - شبكة تواصل الإخبارية (truncated title — see the archived news file for full text)
- Corporate action: dividend · ex-date: 2026-11-16 · DPS: 1.8999999998
Kronos ex-date rescale state not recorded.

## Price chart

## Price chart
Chart: egx-data/egxpy_poul.csv price tail (30 points) + Kronos forecast cone (see HTML).
- egx-data/egxpy_poul.csv: last 7.70 on 2026-11-18
- openbb/POUL_CA.csv: last 7.57 on 2026-11-17
- pandas-ta/indicators.csv: last 7.57 on 2026-11-17
- talib/indicators.csv: last 7.57 on 2026-11-17
- yahooquery/POUL.CA.csv: last 8.02 on 2026-11-16
- Kronos forecast: 21 points, last 9.28 at 2026-12-15

## LLM provenance

## LLM provenance
Model not recorded (pre-#74 run).

## Ledger pin

## Ledger pin
Ledger counts — sweeps: 48 · forecasts: 75 · matured: 22 · pending: 47 · invalid: 6
No accuracy figure is published until n ≥ 30 matured forecasts (n = 22).

## Data-quality flags

## Data-quality flags
- witnesses-stale: common_date 2026-11-16 vs base_date 2026-11-18
- tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA
- recommendation-stale: profile as_of 2026-11-13 base 10.15 != sweep 2026-11-19 base 7.7
- sharia-insufficient-data: AAOIFI
- sharia-table-missing: DJIM
- sharia-insufficient-data: EGX33
- sharia-insufficient-data: FTSE
- sharia-insufficient-data: ISLAMICLY
- sharia-insufficient-data: MSCI
- sharia-insufficient-data: MSCI_M
- sharia-table-missing: SP_SHARIAH

## Provenance

## Provenance
Provenance: merged by worker · compiler: scripts/compile_model.py · model: borsagator-report-model/1
Viewer: <unassigned>

---

Borsagator is not an investment adviser. This report is a computational output, not a recommendation to buy or sell. Verdicts are computed by the named analysis tools from public data; past performance does not predict future results. You decide — and you carry the risk. Securities involve risk of loss. You may lose money.

Borsagator sells a computed report, not advice and not a managed service. The report shows what a fixed set of named analysis tools computed from public market data on a stated date. No person reviews your finances, no recommendation is tailored to you, and nothing in the report is a personal recommendation to buy, sell, or hold any security. Markets move; the tools can be wrong, data can be stale or corrected, and a reported figure can be superseded. Outputs are generated by automated tools with known limitations. Accuracy is not guaranteed. Past measured accuracy does not predict future results. You pay for the computation and delivery of the report, not for any outcome. Use of this product does not create an advisory or fiduciary relationship. Do not spend money you cannot afford to lose on the basis of any report. Data sources: listed per report; data may be delayed or incomplete.

### Arabic disclaimer

بورساجاتور ليست مستشارًا استثماريًا. هذا التقرير ناتج حسابي، وليس توصية بشراء أو بيع. التوصيات محسوبة بواسطة أدوات التحليل المذكورة من بيانات عامة؛ الأداء السابق لا يتنبأ بالنتائج المستقبلية. القرار قرارك — والمخاطرة عليك. الأوراق المالية تنطوي على مخاطر خسارة. قد تخسر مالك.

بورساجاتور تبيع تقريرًا محسوبًا، لا استشارة ولا خدمة إدارة. يعرض التقرير ما حسبته مجموعة ثابتة من أدوات التحليل المذكورة من بيانات سوق عامة في تاريخ محدد. لا يراجع أي شخص وضعك المالي، ولا توجد توصية مخصصة لك، ولا شيء في التقرير توصية شخصية بشراء أو بيع أو الاحتفاظ بأي ورقة مالية. الأسواق تتحرك؛ والأدوات قد تخطئ، والبيانات قد تكون قديمة أو مصححة، والأرقام قد تُستبدل. النواتج مولّدة بأدوات آلية لها قيود معروفة. الدقة غير مضمونة. الدقة المقاسة السابقة لا تتنبأ بالنتائج المستقبلية. أنت تدفع مقابل حساب التقرير وتسليمه، لا مقابل أي نتيجة. استخدام هذا المنتج لا ينشئ علاقة استشارية أو ائتمانية. لا تنفق مالًا لا تستطيع تحمل خسارته بناءً على أي تقرير. مصادر البيانات: تُذكر في كل تقرير؛ وقد تكون البيانات متأخرة أو غير مكتملة.

_Deterministic glue over the ensemble + reaction fit — research tooling, not financial advice._

Viewer: <unassigned>