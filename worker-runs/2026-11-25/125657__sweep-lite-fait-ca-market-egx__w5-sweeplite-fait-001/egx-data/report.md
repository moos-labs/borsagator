# EGX data sources for FAIT — verdict

No POUL reference material applies to FAIT; the series below is reported as fetched.

## egxpy — ok
- Rows: 3000 · Range: 2014-06-26 → 2026-11-25
- Latest: 2026-11-25 close 46.15

## borsa — no_history
- API surface: REST API exposes quotes only (/v1/quote/{symbol}, /v1/quotes, /v1/stocks, /v1/health); Fetcher protocol = fetch_quote. No history/OHLC endpoint exists in the published API.
- Failure/finding: Borsa is a quote service by design: no historical OHLC endpoint or library function exists, so it cannot provide ex-day opens or any price history. Demo-service probe results above show its live surface.
