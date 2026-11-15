# Zipline-reloaded pilot - AAPL dual-SMA (50/200)

- Tool: zipline-reloaded (pip `zipline-reloaded`), bundle `csvdir`
- Data source: Yahoo chart API (direct via requests, no yfinance): https://query1.finance.yahoo.com/v8/finance/chart/AAPL?period1=1700092800&period2=1794700800&interval=1d&events=div,split
- Requested window (period1..period2, UTC dates): 2023-11-16 .. 2026-11-15
- Sessions fetched: 751 (2023-11-16 .. 2026-11-13)
- csvdir file: data/csvdir/daily/AAPL.csv (columns date,open,high,low,close,volume,dividend,split; loader derives start/end/auto-close metadata and exchange CSVDIR)
- Ingest: SUCCEEDED (`zipline ingest -b csvdir` equivalent, via zipline.data.bundles.ingest)
- Backtest window: 2024-09-19 .. 2026-11-13 (started after 210 warmup sessions)
- Strategy: dual SMA 50/200 on AAPL, long 100% when fast > slow, flat otherwise
- Capital base: 100000.0
- Final portfolio value (perf['portfolio_value'].iloc[-1]): 113233.68891499998
- Total return (final / capital_base - 1): 0.13233688914999986 (13.2337%)
