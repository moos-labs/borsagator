# Zipline-reloaded pilot - AAPL dual-SMA (50/200)

- Tool: zipline-reloaded (pip `zipline-reloaded`), bundle `csvdir`
- Data source: Yahoo chart API (direct via requests, no yfinance): https://query1.finance.yahoo.com/v8/finance/chart/AAPL?period1=1699920000&period2=1794528000&interval=1d&events=div,split
- Requested window (period1..period2, UTC dates): 2023-11-14 .. 2026-11-13
- Sessions fetched: 752 (2023-11-14 .. 2026-11-12)
- csvdir file: data/csvdir/daily/AAPL.csv (columns date,open,high,low,close,volume,dividend,split; loader derives start/end/auto-close metadata and exchange CSVDIR)
- Ingest: SUCCEEDED (`zipline ingest -b csvdir` equivalent, via zipline.data.bundles.ingest)
- Backtest window: 2024-09-17 .. 2026-11-12 (started after 210 warmup sessions)
- Strategy: dual SMA 50/200 on AAPL, long 100% when fast > slow, flat otherwise
- Capital base: 100000.0
- Final portfolio value (perf['portfolio_value'].iloc[-1]): 115904.05154500002
- Total return (final / capital_base - 1): 0.1590405154500003 (15.9041%)
