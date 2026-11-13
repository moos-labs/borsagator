# FinRL A2C pilot — result

- **Tool:** FinRL 0.3.7 (`finrl`), A2C via FinRL's `DRLAgent` (stable-baselines3)
- **Ticker:** NVDA
- **Train window:** 2022-01-03 to 2023-12-30 (data_split end-exclusive: last train day before 2023-12-30)
- **Trade (backtest) window:** 2023-12-30 to 2024-06-29 (data_split end-exclusive: last trade day before 2024-06-29)
- **Total training timesteps:** 8000
- **Technical indicators (finrl.config.INDICATORS):** macd, boll_ub, boll_lb, rsi_30, cci_30, dx_30, close_30_sma, close_60_sma
- **hmax:** 100 shares per step; **buy/sell cost:** 0.1% each; **reward scaling:** 1e-4

## Backtest outcome (FinRL's own account-value output)

- **Initial portfolio value:** 1,000,000.00
- **Final portfolio value:** 1,238,811.26
- **Total return:** 23.88%

Rows in `account_value.csv`: 124 (one per trade-window step, from
FinRL `DRL_prediction`'s asset memory, paired with the trade env's dates).

> This is a short smoke-test training run (a few thousand timesteps on a
> single stock), not investment research: the agent is barely trained and
> the result mostly shows the pipeline works end to end.
