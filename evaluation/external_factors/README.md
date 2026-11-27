# External factor closes (INS-IMPROVE-001 round 26)

Source: Yahoo chart API v8 via `scripts/fetch_ohlcv_store.py --start 2014-01-01
--tickers 'EGP=X' EEM 'BZ=F' 'GC=F'`, fetched 2026-11-27. Raw (unadjusted) close,
date = exchange-local session date. Bars with a null high, low or close were skipped by
the fetch script (EGP=X 9, BZ=F 6, GC=F 5, EEM 0 over the full history). Files here keep
`date,close` and are cut at 2023-12-28 (the screen end), so no later bar is stored.

| File | Symbol | Meaning |
|---|---|---|
| EGP_X.csv | EGP=X | USD/EGP market quote (not the CBE official rate) |
| EEM.csv | EEM | iShares MSCI Emerging Markets ETF |
| BZ_F.csv | BZ=F | Brent crude futures (continuous front month) |
| GC_F.csv | GC=F | Gold futures (continuous front month) |

Point-in-time rule used by the screens: a cutoff on date D uses only closes dated
strictly before D.
