# Zipline-reloaded pilot - AAPL dual-SMA (50/200)

- Tool: zipline-reloaded (pip `zipline-reloaded`), bundle `csvdir`
- Data source: Yahoo chart API (direct via requests, no yfinance): https://query1.finance.yahoo.com/v8/finance/chart/AAPL?period1=1700179200&period2=1794787200&interval=1d&events=div,split
- Requested window (period1..period2, UTC dates): 2023-11-17 .. 2026-11-16
- Sessions fetched: 750 (2023-11-17 .. 2026-11-13)
- csvdir file: data/csvdir/daily/AAPL.csv (columns date,open,high,low,close,volume,dividend,split; loader derives start/end/auto-close metadata and exchange CSVDIR)
- Ingest: SUCCEEDED (`zipline ingest -b csvdir` equivalent, via zipline.data.bundles.ingest)
- Backtest window: 2024-09-20 .. 2026-11-13 (started after 210 warmup sessions)
- Strategy: dual SMA 50/200 on AAPL, long 100% when fast > slow, flat otherwise
- Capital base: 100000.0
- Final portfolio value (perf['portfolio_value'].iloc[-1]): 114233.84294
- Total return (final / capital_base - 1): 0.14233842940000008 (14.2338%)
