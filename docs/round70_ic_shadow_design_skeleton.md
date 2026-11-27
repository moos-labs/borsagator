# Round 70 (b-design): cross-sectional excess-return / IC-first shadow, design skeleton

DESIGN ONLY. No implementation, no scoring, no statistic computed. Descriptive; no verdict word. Source: Moos Slack 1795783578.144969 (item 2a), relayed to the author. Thresholds were accepted by Moos (Slack 1795783947.799179, thread 1795783578.144969): wide date >= 20 tickers; date bootstrap B=2000, seed 70; gate 20 wide dates with matured day AND week; pass = mean-IC CI lower bound > 0 at both horizons with n_dates >= 20. He added the 2-family ensemble net_score as a third signal (descriptive only) and skipped the grid IC (ledger only).

## Question
Do the existing per-ticker signals (technicals net_score, sentiment family value) rank tickers by next-window excess return within a date? An IC-first check asks this before any forecast change. It needs no new data and no index series.

## Data facts that shape the design (counted on main, not scored)
- Backtest grid, cells 1-47: 8 cutoffs, 1-7 tickers per cutoff (median 6). Cells 91+: 2 cutoffs, 6 tickers each. A rank correlation over 6 names takes coarse values, so IC on the grid is descriptive at best and cannot support a pass leg.
- Forward ledger: 13 as_of dates, but only 3 are wide (36, 27 and 9 tickers); the other 10 hold 1-2 tickers. Cross-sectional IC needs the wide dates.

## Unit and statistic (proposed)
- Unit: a wide as_of date = at least 20 distinct tickers with a clean (matured, dividend_gap null) row and a non-null signal, per horizon (day, week).
- Excess return = ticker realised_move_pct minus the mean realised_move_pct of that date's clean tickers (cross-sectional demeaning, no index needed).
- Per-date IC = Spearman rank correlation of signal vs excess return (average ranks for ties). Two signals, scored separately: technicals net_score and sentiment value (no magnitude weight beyond rank).
- Statistic per signal and horizon: mean IC over wide dates, plus ICIR = mean IC / sample sd of IC.
- Interval: percentile bootstrap resampling dates, B=2000, seed 70, 95%.

## Gate and pass leg (proposed)
- Run gate: at least 20 wide dates with matured rows at BOTH day and week. Below the gate the scorer prints counts only.
- Pass leg per signal: mean-IC CI lower bound > 0 at BOTH day and week, with n_dates >= 20. ICIR is reported, not gated.
- Today: 3 wide dates, most without matured week rows; the gate is far off (not estimated here).

## What a pass would and would not mean
A pass supports a centre/tilt shadow experiment only. It is not a RangeSkill gain and not a keep. Any candidate built on it goes through the loop-bar keep rule on untouched data: RangeSkill cutoff-clustered CI lower bound > 0 AND coverage CI overlaps 0.75-0.85, at least 10 cutoffs for a KEEP. No width or volatility change, Kronos stays at weight 0, no ensemble or frozen edits.

## Decisions (Moos, 1795783947.799179)
1. Thresholds as proposed above.
2. Ensemble net_score is a third signal, descriptive only: a diagnostic of the current centre, not a new route.
3. Grid IC skipped; the design is ledger-only.
Scorer: benchmarks/ic_shadow.py (branch ins/round70-ic-shadow-scorer). Signals: families.technicals, families.sentiment, net_score. Ties and zero signal values stay in the ranks (rank IC). Below the gate it prints counts only.
