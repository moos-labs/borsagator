# Round 68 route 2: index-regime flag, pre-registration

Written and committed BEFORE any correlation was computed. Descriptive only. No verdict, no keep rule, not v2-relative. Source: Moos Slack 1795782106.527319 (relayed to the author, read there via the thread 1795781625.091709 dispatch of the same round).

## Question
Does the trailing 21-session return of the ticker's market index at the cutoff line up with the sign of the ticker's realised move?

## Fixed design
- Cells: backtest/cells/cell1..47 only (training block). Cells 48-90 and 91+ are not read by the script in the default run.
- Unit: one ticker-cutoff cell. Row per horizon (day 1, week 5, month 21 sessions).
- Index: `.CA` tickers use the EGX30 close series from Mubasher (`evaluation/index_regime/EGX30_mubasher_close.csv`); all others use S&P 500 from Yahoo `^GSPC` (`GSPC_yahoo_close.csv`). Yahoo `^EGX30` returns not-found, so it is not used. Mubasher and Yahoo bars are never mixed inside one series.
- x = ln(index close at the last index session on or before the cutoff date / index close 21 sessions earlier). Needs 21 prior sessions, otherwise the cell is dropped.
- y = the ticker's realised_move_pct from the buy-and-hold row of the cell (same realised close the scorer used). Rows flagged with a dividend_gap are excluded; rows with realised move exactly 0 are dropped from sign agreement only.
- Statistics per horizon: n, Spearman rank correlation of x vs y (average ranks for ties), sign agreement share of sign(x) vs sign(y) (x == 0 dropped), and a cutoff-clustered bootstrap 95% CI for the Spearman (resample cutoff dates with replacement, B=2000, seed 68).
- Index coverage: per training cell, whether the index series reaches 21 sessions before the cutoff and covers the cutoff; cells lacking it are listed.

## Pre-stated threshold for the untouched (91+) extension
The 91+ extension runs ONLY IF, at BOTH the week and the month horizon on cells 1-47:
1. n >= 30 cells with a usable x and y,
2. Spearman >= 0.20,
3. sign agreement >= 0.60, and
4. the cutoff-clustered bootstrap CI lower bound for the Spearman > 0.

The day horizon is reported but is not part of the threshold. The training block has 8 cutoffs, fewer than the 10 a KEEP needs, so even a cleared threshold is only permission to look at 91+, not a keep.
If any criterion is not met, the extension is not run and cells 91+ are not read.
