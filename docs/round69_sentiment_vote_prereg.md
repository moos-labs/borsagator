# Round 69 (a): sentiment direction vote, pre-registration

Written and committed BEFORE the scorer was run on any ledger row. Descriptive scoring of a vote only; no verdict word, not a RangeSkill candidate by itself, never a width input. Source: Moos Slack 1795782740.762559 (thread 1795782526.668949), and the round 68/69 findings that sentiment magnitude does not support a range input.

## Data
`ledger/ledger.json` `forecasts_detail` on main. A row is eligible when: status is `matured`, `dividend_gap` is null, `horizons` is day or week, `families.sentiment` exists and is not 0, and `realized_direction` is up or down. Month rows are excluded (they mature too late). Invalid and pending rows are never scored.

## Unit
The independent unit is the as_of DATE (tickers on one date share one market move). Rows within a date stay in the pooled count; the bootstrap resamples whole dates.

## Arm 1: sign vote
Vote = sign of the sentiment family value. No magnitude weight. Agreement = vote equals realised_direction. Statistic per horizon: pooled agreement share over eligible rows.

## Arm 2: cross-sectional rank vote
Per as_of date and horizon, take every row with a sentiment value, status not invalid and `dividend_gap` null (maturity does not matter for the universe). Sort ascending by sentiment, ties broken by ticker name. With n rows and k = n // 3: the bottom k vote down, the top k vote up, the middle abstain. A date needs n >= 6, otherwise it contributes no votes. Only votes on matured eligible rows are scored. Statistic per horizon: pooled agreement share of the votes.

## Run gate
The scorer reports agreement only when at least 30 distinct as_of dates hold a matured eligible row at BOTH day and week. Below 30 it prints counts only (so nobody peeks at the statistic early).

## Interval and pass condition
Percentile bootstrap, resampling dates with replacement, B = 2000, seed 69, 95% interval, one per arm and horizon. Pass leg for an arm: the CI lower bound of agreement is above 0.5 at BOTH day and week, with n_dates >= 30 at each. Outputs carry only these booleans.

## Use if it passes
Centre/direction input only, never width. Any implementation as a forecast candidate runs under the loop-bar keep rule (RangeSkill cutoff-clustered CI lower bound > 0 AND coverage CI overlaps 0.75-0.85, at least 10 cutoffs for a KEEP), on untouched data only. Passing this vote check is not a keep.

## State at registration
The ledger has 13 distinct as_of dates; 8 have matured day rows and 6 have matured week rows. The run is expected to wait about 17 more dates (an estimate, roughly mid-December).
