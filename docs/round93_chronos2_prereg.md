# Round 93: Chronos-2 zero-shot control arms (experiment E), pre-registration

Written and committed BEFORE any Chronos-2 inference on a verdict cell. No
quantiles.json for cells 48-90 or 91+ exists when this is committed. Origin:
INS-IMPROVE-093 (Slack 1795829375.713939, relayed to the author, not read by
the author). Scorer: benchmarks/score_tsfm_control.py (#772, changed in this
PR). Frozen v2, scripts/ensemble.py and every frozen value are untouched.

## What is tested

Two control arms from the same model and the same quantiles, nothing fitted:
- Arm A (zero): band centre 0, half = (q90 - q10) / 2 x RISK_MULT.
- Arm B (q50): band centre = q50, same half-width.
RISK_MULT = 1.0 for both. It is fixed, not tuned, and not a parameter of the
scoring command beyond the recorded row multiplier `mult` that every earlier
scorer applies. Quantiles are the model's own 0.10 / 0.50 / 0.90 levels of the
cumulative return in percent over 1 / 5 / 21 sessions from the base close,
from closes dated on or before the base date only (the capture's own price.csv,
no covariates, no index, no news).

Reference: frozen v2 on the same rows. Naive is the RangeSkill baseline.

## Pretraining overlap rule

Chronos-2 is Apache-2.0 (github.com/amazon-science/chronos-forecasting,
huggingface.co/amazon/chronos-2). Its training data is subsets of the Chronos
and GIFT-Eval pretraining corpora plus synthetic data (model card, arXiv
2510.15821 section 4). No training cutoff is stated and no statement says EGX or
Yahoo series are excluded. Whether EGX series are in the training data is
UNVERIFIED (appendix Table 6 was not read). Release date: 2025-10-20.
Mitigation, registered here: only origins strictly after 2025-10-20 enter any
scoring. The scorer enforces it (`--min-origin`, default 2025-10-20, and it
refuses an earlier value). Every dropped row is listed with its reason.

## Counts before any descriptive read (printed here, from the archive tip
2c96d0377, built with the repo's own R.build_rows, no inference involved)

- Cells 48-90: 43 captures, 129 rows. After the origin rule: 41 captures,
  123 rows (41 per horizon), 7 cutoff clusters (2025-12-31, 2026-02-13,
  2026-03-31, 2026-05-15, 2026-06-30, 2026-08-14, 2026-09-30), 6 tickers
  (COMI, ETEL, HRHO, SWDY, TMGH, NVDA). The only dropped origin is 2025-09-30
  (2 captures, 6 rows).
- Cells 91+: 12 captures, 36 rows, 2 cutoffs (2025-08-15, 2025-11-14). After the
  origin rule only 2025-11-14 remains: 6 captures, 18 rows, 6 per horizon,
  1 cutoff cluster.

## Windows

- Descriptive: cells 48-90 only. The scorer's `describe` mode refuses any range
  outside 48-90 and defaults to 48-90. It prints the counts first, then
  coverage, RangeSkill and CIs as descriptive, no verdict.
- Scoring: cells 91+ only (`score` mode refuses lower cells). Under the loop
  bar a read needs >= 10 cutoff clusters on every horizon. With 1 eligible
  cluster it prints COUNTS ONLY and writes no coverage, skill or CI. A keep
  decision on cells 91+ is therefore not reachable from the current data. The
  forward schedule (PR #953, docs/round93_forward_schedule_prereg.md)
  is the surface where a keep can be read.

## Loop bar (unchanged, from benchmarks/loop_bar.py)

Per horizon: RangeSkill (vs naive) cutoff-clustered 95% CI lower bound > 0, AND
the cutoff-clustered 95% coverage CI overlaps [0.75, 0.85] with width <= 0.15,
AND >= 10 cutoff clusters. Bootstrap defaults: 5000 reps, seed 20261125; only
default-rep CIs are quoted. A KEEP is not an adoption. At best it justifies a
forward-ledger test.

## Inference

Inference is LLM-free and writes one collected/chronos-2/quantiles.json per
capture in the scorer's format. It is run only after this document is committed.
It runs once per capture (one 21-step forecast gives all three horizons).
No quantile file is looked at before the scorer reads it. Whether bf16 inference
fits the review workspace (1 CPU, 1 GB RAM) is checked on a date with no
verdict cell, not on a verdict capture.
