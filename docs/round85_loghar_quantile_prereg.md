# Round 85, challenger 2: log-HAR volatility with a quantile-regression band width (pre-registration)

Written and committed before any number of this challenger is computed. Additive only: nothing edits scripts/ensemble.py or any frozen value.

## Question
Log-HAR as a plain width input (replay_log_har.py, #769) was worse than frozen v2 on every horizon. The new part here is the width map: instead of half = k x sigma_har x sqrt(sessions) x RISK_MULT with a Winkler-fitted k, the half-width is a fitted conditional quantile of the realised absolute move given the log-HAR forecast.

## Spec (fixed here)
- Volatility forecast: unchanged replay_log_har.har_daily_sigma (Parkinson rv, lags 1/5/22, per-capture OLS refit on pre-cutoff history, Duan smearing, 120-observation minimum, rows without a forecast excluded).
- unit = replay_band_candidates.half_pct(sigma_har, horizon, 1.0, RISK_MULT), in percentage points.
- Quantile layer, per horizon: ln(max(|realised move|, 0.01 pp)) = a + b ln(unit) fitted by linear quantile regression at tau = 0.80 (the middle of the [0.75, 0.85] coverage band). Quantiles commute with the monotone log, so exp(a + b ln unit) is the conditional 0.80 quantile of |move|.
- Half-width = exp(a) x unit^b. Band is symmetric around 0, as in v2.
- Solver: exact pinball-loss minimum over all lines through two training points (stdlib, no iteration); ties go to the smaller |b - 1|, then the smaller a. Fewer than 8 training rows on a horizon means no fit and the horizon is not scored.
- Nothing else is fitted. tau, the 0.01 floor and the minimum row count are fixed above.

## Fit window
Training cells 1-47 only. The (a, b) per horizon are written once to evaluation/loghar_quantile_frozen.json and then frozen. No refit.

## Scoring and keep rule (cells 91+ only)
One scoring of the frozen file on untouched cells >= 91. Per horizon: RangeSkill (vs naive) cutoff-clustered 95% CI lower bound > 0, AND the cutoff-clustered 95% coverage CI overlaps [0.75, 0.85] with width <= 0.15, AND at least 10 cutoff clusters. KEEP needs every horizon to pass. Fewer than 10 cutoff clusters on any horizon means counts only, no KEEP and no REJECT.

## Descriptive runs (cells 48-102)
Numbers only: coverage, RangeSkill, cutoff CIs, rows and clusters per horizon, next to frozen v2 and next to plain log-HAR with its Winkler-fitted k (control). No verdict word or key. Cells 48-90 never enter a verdict.

## Reading
No KEEP is an adoption by itself; adoption is measured relative to frozen v2 on the same rows. A quantile layer that does not beat plain log-HAR in training is reported as that.

## Addendum (robustness handling, after review, no scored number changed)
- The width is computed as exp(a + b ln unit), one exponential, so a near-constant training unit cannot overflow exp(a) before the multiplication.
- If the training unit is constant on a horizon (no two distinct x), the slope is not identified. Then b is fixed at 1 and a is the tau = 0.80 pinball optimum of ln|move| - ln unit (ties to the smaller a). The horizon is fitted, not dropped. Re-fitting the frozen file with this change reproduces the same (a, b) on every horizon.
