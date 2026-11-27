# Round 85, challenger 1: adaptive conformal with a coverage lever (pre-registration)

Written and committed before any number of this challenger is computed. Additive only: nothing edits scripts/ensemble.py or any frozen value.

## Question
The existing ACI layer over frozen v2 (benchmarks/replay_aci_conformal.py) fixes the target miscoverage ALPHA at 0.20. It costs RangeSkill on every descriptive run. This round makes ALPHA the explicit lever and asks whether the coverage and skill trade-off can be tuned, not whether ACI works.

## Lever (fixed here)
- ALPHA grid, target miscoverage: 0.15, 0.20, 0.25, 0.30 (target coverage 0.85, 0.80, 0.75, 0.70). ALPHA is both the starting level and the feedback target of the ACI update.
- Everything else is unchanged from replay_aci_conformal.py: GAMMA 0.05, clip 0.02 to 0.50, 35-day maturity guard, MIN_HIST 12, pooled tickers, conformity score |realised move| / frozen v2 half-width, band = q x frozen v2 half-width.
- No other parameter is fitted.

## Selection (training cells 1-47 only)
Walk-forward replay on target cells 1-47 (history from earlier cutoffs only). Per horizon, among grid values whose pooled training coverage lies in [0.75, 0.85], pick the one with the highest training RangeSkill vs naive; ties go to the larger ALPHA. If no grid value has training coverage in [0.75, 0.85], pick the value whose coverage is closest to 0.80; ties go to the larger ALPHA. The selection is written once to evaluation/aci_lever_selected.json and then frozen. No refit after it.

## Scoring and keep rule (cells 91+ only)
One scoring of the frozen selection on untouched cells >= 91. Per horizon: RangeSkill (vs naive) cutoff-clustered 95% CI lower bound > 0, AND the cutoff-clustered 95% coverage CI overlaps [0.75, 0.85] with width <= 0.15, AND at least 10 cutoff clusters on that horizon. KEEP needs every horizon to pass. Fewer than 10 cutoff clusters on any horizon means counts only, no KEEP and no REJECT. Same bootstrap clustering and seed as the other scorers (replay_band_candidates._boot).

## Descriptive runs (cells 48-102)
All four grid values, numbers only: coverage, RangeSkill, cutoff CI, rows, clusters per horizon. No verdict word or key. Cells 48-90 never enter a verdict.

## Reading the lever
The trade-off table is the deliverable of the training and descriptive runs: coverage and RangeSkill per ALPHA per horizon. A lever that moves coverage without raising skill above frozen v2 is a finding, not an adoption. No KEEP is an adoption by itself; adoption is measured relative to frozen v2 on the same rows.
