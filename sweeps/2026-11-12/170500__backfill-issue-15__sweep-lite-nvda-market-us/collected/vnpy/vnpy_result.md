# VeighNa (vnpy) backtest result

- Symbol: AAPL (Exchange.NASDAQ, daily bars, Yahoo chart API)
- Strategy: DoubleMaStrategy (built-in, vnpy_ctastrategy.strategies.double_ma_strategy; default setting fast_window=10, slow_window=20)
- Window: 2023-11-01 to 2026-10-31
- Capital: 1000000
- Bars loaded: 752

## Headline statistics (exactly as returned by calculate_statistics())

- total_return: -0.008322004638672276
- sharpe_ratio: -0.43582822596923493
- max_drawdown: -151.3000048828544

Also from the same dict: max_ddpercent: -0.015129411197996307,
end_balance: 999916.7799536133,
total_trade_count: 45.

The full statistics dict is in `statistics.json`. Note the built-in
DoubleMaStrategy trades a fixed volume of 1, so with size=1 the PnL
scale is that of a single share; the statistics are the engine's own
output for that setting, not a sized portfolio allocation.
