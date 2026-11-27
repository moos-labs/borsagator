# Round 88: regime-tilt cell scorer, pre-registration

Committed before any number is computed. Parent design: docs/round78_regime_macro_tilt_design.md (pre-registration stands, nothing in it is changed here). Brief: Slack C0C8EBZEF9U 1795820550.784839 (relayed by Main, not read by the agent). Additive: no ensemble.py, no frozen v2 value is edited, no verdict word or key outside the loop bar.

## Rule (from the round 78 design, sections 2 to 5)
- Regime at a cutoff: policy-rate path only, from evaluation/macro_series/cbe_decisions.json. The last decision with published_date strictly before the cutoff sets tightening (change_bps > 0), easing (< 0) or hold (= 0). This is the shadow's regime_from_decisions, imported, not re-implemented.
- Tilt: per horizon and regime, the frozen v2 half-width is multiplied by w_r from the grid {0.9, 1.0, 1.1}. w_r is chosen on training cells 1-47 only, by the same procedure for every regime: the lowest mean Winkler interval score (replay_band_candidates.row_is) over that regime's training rows. Ties go to 1.0. Clip to [0.9, 1.1] (the grid already lies inside it; the clip is applied anyway).
- Minimum group: a regime with fewer than 5 training rows at a horizon keeps w_r = 1.0 and is reported as not fitted.
- Training regime counts are printed first. If the training cells hold a single regime, the tilt is degenerate and the output says so: every other regime keeps 1.0 and no contrast between regimes exists.
- Descriptive run: cells 48-90, no verdict word or key. Clean scoring: cells 91+, counts only below 10 cutoff clusters (no coverage, skill or CI printed or written). The loop bar is benchmarks/loop_bar.py (copied unchanged from PR #945), so any future KEEP uses the same bar: RangeSkill cutoff-clustered CI lower bound > 0, coverage CI overlaps [0.75, 0.85] with width <= 0.15, and >= 10 cutoff clusters on every horizon.
- Every capture or row that does not enter a run is listed as excluded with its reason.
