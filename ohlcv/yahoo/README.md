# OHLCV store — Yahoo chart API (source: Yahoo)

Canonical daily OHLCV store for the #768 BEAST MODE historical-data collection (item 2).
One CSV per ticker: `date,high,low,close,volume,adjclose`.

- Fetched: 2026-11-26 by the borsagator-cycle run (script `scripts/fetch_ohlcv_store.py`, PR #787),
  `python3 scripts/fetch_ohlcv_store.py --out ohlcv/yahoo` (default tickers: the 6 scored
  tickers + the 34-name EGX33 freeze in `sharia/benchmark/sources/egx33.json`).
- Source: Yahoo chart API v8 (`query1.finance.yahoo.com`), stdlib urllib, no key.
- Open is NOT stored: Yahoo's EGX open equals the previous close on ~98% of bars (data-agent finding), so it is synthetic.
- Close is the raw (unadjusted) close; adjclose is kept as a separate column.
- Bars with a null high, low or close are skipped and counted; duplicate dates keep the last;
  dates are the exchange-local session date (API timestamp shifted by the reported gmtoffset).
- All files end 2026-11-25; all rows sorted by date; no null high/low/close rows.

Tickers: 37 files, 107244 data rows in total.

| Ticker | First | Last | Rows |
|---|---|---|---|
| ACGC.CA | 2014-01-02 | 2026-11-25 | 3180 |
| ADIB.CA | 2014-01-02 | 2026-11-25 | 3183 |
| AMOC.CA | 2014-01-02 | 2026-11-25 | 3180 |
| ARCC.CA | 2014-05-18 | 2026-11-25 | 3089 |
| ATQA.CA | 2014-10-26 | 2026-11-25 | 2986 |
| CLHO.CA | 2016-11-15 | 2026-11-25 | 2462 |
| COMI.CA | 2014-01-02 | 2026-11-25 | 3184 |
| EFID.CA | 2015-04-02 | 2026-11-25 | 2863 |
| EFIH.CA | 2021-10-20 | 2026-11-25 | 1237 |
| EGAL.CA | 2014-01-02 | 2026-11-25 | 3181 |
| EGAS.CA | 2014-01-02 | 2026-11-25 | 3182 |
| ETEL.CA | 2014-01-02 | 2026-11-25 | 3183 |
| ETRS.CA | 2014-01-02 | 2026-11-25 | 3181 |
| FAITA.CA | 2014-01-02 | 2026-11-25 | 3182 |
| FAIT.CA | 2014-01-02 | 2026-11-25 | 3181 |
| HRHO.CA | 2014-01-02 | 2026-11-25 | 3186 |
| ICFC.CA | 2018-09-02 | 2026-11-25 | 2014 |
| IFAP.CA | 2014-01-02 | 2026-11-25 | 3181 |
| ISPH.CA | 2017-12-12 | 2026-11-25 | 2203 |
| JUFO.CA | 2014-01-02 | 2026-11-25 | 3180 |
| LCSW.CA | 2014-01-02 | 2026-11-25 | 3183 |
| MASR.CA | 2014-01-02 | 2026-11-25 | 3184 |
| MCQE.CA | 2014-01-02 | 2026-11-25 | 3181 |
| MPCO.CA | 2014-01-02 | 2026-11-25 | 3181 |
| MTIE.CA | 2017-04-11 | 2026-11-25 | 2371 |
| NVDA | 2014-01-02 | 2026-11-25 | 3245 |
| OCDI.CA | 2014-01-02 | 2026-11-25 | 3186 |
| ORAS.CA | 2021-08-10 | 2026-11-25 | 1286 |
| ORHD.CA | 2014-01-02 | 2026-11-25 | 3178 |
| ORWE.CA | 2014-01-02 | 2026-11-25 | 3181 |
| PHDC.CA | 2014-01-02 | 2026-11-25 | 3184 |
| RACC.CA | 2017-10-03 | 2026-11-25 | 2254 |
| RMDA.CA | 2019-12-11 | 2026-11-25 | 1686 |
| SAUD.CA | 2014-01-02 | 2026-11-25 | 3182 |
| SKPC.CA | 2014-01-02 | 2026-11-25 | 3184 |
| SWDY.CA | 2014-01-02 | 2026-11-25 | 3180 |
| TMGH.CA | 2014-01-02 | 2026-11-25 | 3180 |

## Gaps

- `GOUR.CA`: Yahoo returns HTTP 404 (no series) — GOUR is one of the 6 EGX33-freeze codes
  still lacking a verified ISIN (CLHO, FAITA, GOUR, ICFC, LCSW, RACC); the other five fetch
  fine from Yahoo. GOUR needs a primary-source check before it can join the store.
