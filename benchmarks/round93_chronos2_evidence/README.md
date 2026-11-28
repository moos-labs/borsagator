Round 93, experiment E (Chronos-2 zero-shot quantile band) evidence.

- quantiles_91plus/<cutoff>/<capture>/quantiles.json: the 12 outputs of
  benchmarks/run_chronos2_quantiles.py (this branch, code head 26a6e702d)
  for cells 91-102, run with --allow-verdict-cells.
- describe_cells48_90.json: output of benchmarks/score_tsfm_control.py
  describe (#954 head 2159a0948), cells 48-90, centre zero, 5000 reps,
  seed 20261125. Descriptive only, no verdict.
- score_cells91plus_counts.json: output of the same scorer, score mode,
  cells 91+. COUNTS ONLY (1 cutoff cluster after the origin rule).
Additive evidence, no code change.
