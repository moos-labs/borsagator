# NautilusTrader — official example backtest result

- **Example run:** the project's own `examples/backtest/fx_ema_cross_audusd_ticks.py`
  at release tag **v1.221.0** (the installed `nautilus_trader` version), with the
  minimal CI adaptations documented in `scripts/nautilus_example.py`.
- **Strategy:** the project's own example strategy `EMACross`
  (`nautilus_trader.examples.strategies.ema_cross`), fast EMA 10 / slow EMA 20,
  trade size 1,000,000, as configured in the official example.
- **Data:** the project's own packaged test data — TrueFX AUD/USD quote ticks
  (`tests/test_data/truefx/audusd-ticks.csv` at tag v1.221.0), loaded via
  `TestDataProvider.read_csv_ticks` and `QuoteTickDataWrangler`, exactly as in
  the official example; plus the packaged `short-term-interest.csv` used by the
  example's FX rollover interest module.
- **Instrument traded:** AUD/USD.SIM (venue SIM, margin account, USD base)

## Figures exactly as the engine reported them

- **Order fills (rows in the engine's own order fills report):** 96
- **Positions (rows in the engine's own positions report):** 48
- **Account report first row:** index `2020-01-30 15:28:09.820000+00:00`, total = 1000000.00 USD
- **Account report last row:** index `2020-01-31 20:59:54.501000+00:00`, total = 997060.90 USD

## Engine account report (verbatim)

Full report saved in `account_report.txt`. First and last rows:

```text
                                       total locked        free currency account_id account_type base_currency margins  reported info
2020-01-30 15:28:09.820000+00:00  1000000.00   0.00  1000000.00      USD    SIM-001       MARGIN           USD      []      True   {}
                                      total locked       free currency account_id account_type base_currency margins  reported info
2020-01-31 20:59:54.501000+00:00  997060.90   0.00  997060.90      USD    SIM-001       MARGIN           USD      []     False   {}
```

## Engine order fills report

Full report saved in `order_fills_report.txt` (96 rows).

## Engine positions report

Full report saved in `positions_report.txt` (48 rows).

All figures above are quoted exactly as the NautilusTrader BacktestEngine
reported them; nothing was recomputed by this script beyond counting the
rows of the engine's own fills/positions reports and reading the first/last
rows of the engine's own account report.
