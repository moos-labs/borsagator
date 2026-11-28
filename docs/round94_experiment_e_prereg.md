# Round 94: experiment E, zero-shot quantile control arms (Chronos-2, TimesFM 2.5), pre-registration

Written and committed BEFORE any Chronos-2 or TimesFM inference on any capture. Doc only: no code, no data read, no quantile file exists for this note. Source: INS-IMPROVE-163 report and Moos's acceptance and rulings in Slack thread 1795858029.067639 (ts 1795874872.740309, read by me; the 164 dispatch is ts 1795875395.271239, read by me). Frozen v2, scripts/ensemble.py and every frozen value are untouched.

## Status
- CONTROL ARM ONLY. Both models are control arms. Neither is a verdict arm and neither can produce a KEEP.
- Ruling (Moos, 163 acceptance, read): cells 91+ are NOT verdict-eligible for experiment E. No model output is scored on cells 91+, and no 91+ capture is read for E.
- Reason: neither source states a pretraining cutoff for finance or equity series, and neither states that EGX data is excluded (Chronos-2 paper arXiv 2510.15821 and model card; TimesFM 2.5 card, https://huggingface.co/google/timesfm-2.5-200m-pytorch). Whether EGX or Yahoo series are in either corpus is UNVERIFIED (Chronos-2 Table 6 was not read).
- Relation to PR #954 (docs/round93_chronos2_prereg.md, open, not merged, relayed state from my read of the branch): that note scores Chronos-2 on cells 91+ with an origin rule after 2025-10-20. This note replaces the verdict-scoring part for experiment E. The two differ on scope, so #954 needs amending before its scorer's `score` mode is used for E. That is Moos's call; this note does not edit #954.

## Models
- Chronos-2 (amazon/chronos-2, 119,477,664 params, Apache-2.0), package chronos-forecasting 2.3.2, native quantile levels include 0.1 and 0.9.
- TimesFM 2.5 (google/timesfm-2.5-200m-pytorch, 231,289,280 params, Apache-2.0), package timesfm 3.0.2, native outputs mean plus 0.1 to 0.9 in steps of 0.1.
- Zero-shot only. No tuning, no fine-tuning, no covariates, no index, no news, no prompt or hyperparameter search. The model weights revision (the Hugging Face commit hash of the files actually loaded) and both package versions are recorded in every output file. Reason (mine): the Chronos-2 repo shows lastModified 2026-06-05, so the weights at run time may differ from the release.
- Unverified and carried: TimesFM PyPI API against the card's example, torch CPU runtime on the review workspace (1 CPU, about 1 GB RAM, no torch). The runtime check is made on a date with no capture, not on a capture. Runs use a separate environment (python >= 3.10, torch CPU); the stdlib harness is not changed.

## Input (fixed)
- Series: the capture's own price.csv closes dated on or before the base date, nothing later. The last 512 sessions as context. A capture with fewer than 512 closes up to the base date is EXCLUDED and listed with reason "context under 512" (my choice, no padding, no shorter context).
- One forecast per capture per model over 21 steps. Horizons 1, 5 and 21 sessions read steps 1, 5 and 21 of that one forecast.

## Mapping to the frozen v2 band format (fixed)
- Quantiles 0.1 and 0.9 of the model's forecast close at step h. Percent move = 100 x (quantile close / last close - 1).
- range_low_pct = the 0.1 move, range_high_pct = the 0.9 move. The band is the model's own and is not centred on 0 (v2 is centred on 0 with half-width k x sigma60 x sqrt(sessions) x RISK_MULT, k = 1.15, 1.28, 1.20 for day, week, month). No RISK_MULT, no rescaling, no re-centring is applied to the model band (my choice).
- Rows excluded and listed individually with reason: a non-finite quantile, a 0.1 quantile above the 0.9 quantile ("crossed"), or a quantile that rounds equal to the last close at both ends ("collapsed"). Nothing is repaired or imputed.
- TimesFM: quantile crossing fix on, continuous quantile head on, as in its card example; the output position of 0.1 and 0.9 is asserted against the stated level order in a test before use.

## Scope and rows
- Descriptive scope: cells 48-90, captures with an origin (base date) before 2025-10-20 only. Cells 91+ are never read for E. Cells 1-47 are not used.
- Rows: the same (capture, horizon) rows the repo's R.build_rows returns for v2 on those cells, after the model-side exclusions above. v2 and both models are scored on the SAME rows: a row dropped for one is dropped for all three.
- Counts first, before any statistic: captures, rows per horizon, cutoff clusters, tickers, and every excluded capture or row listed individually with its reason. I have not read the cell calendar or the archive for this note, so these counts are UNKNOWN until the runner prints them.

## Outputs (descriptive, per model, per horizon, same rows as v2)
1. Mean band width in percentage points (range_high_pct minus range_low_pct), model and v2, and the mean paired difference (model minus v2).
2. Coverage counts: number of rows whose realised move lies inside the band, over the number of rows, model and v2. Counts, not a pass/fail against 0.75 to 0.85.
3. Winkler interval score, using the same function (bs.winkler_is) and the same alpha the existing scorers apply to v2, on the same rows; mean per model and mean paired difference (model minus v2).
- Intervals: 95% two-sided percentile bootstrap, resampling CUTOFF DATES with replacement (every row of a drawn cutoff date carried with it), 5000 repetitions, seed 20261125, for the three paired mean differences. Only these default-rep intervals are quoted.
- No verdict word anywhere in the output or the PR: no keep, adopt, pass, fail, win, better, worse. No loop-bar test is applied. No decision follows from these numbers by itself.

## Guards
- The runner and scorer refuse any capture with a base date on or after 2025-10-20 and any cell above 90. A refused capture is listed, never silently skipped.
- No quantile file is opened before this note is committed. The numbers are not used to change any choice above; a change needs an amendment committed before the next run.
- An existing runner branch (ins/round93-chronos2-runner) and scorer branch (ins/round93-chronos2-e, PR #954) were seen by name and file list only; I have not reviewed their code for this note. Their origin rule (strictly after 2025-10-20) conflicts with this note's scope (before 2025-10-20) and must be changed to match before use for E.

## Choices that are mine, not Moos's
Direct 0.1/0.9 band with no RISK_MULT and no centring; 512-closes exclusion (no short context); model-side exclusion reasons "crossed", "collapsed", "non-finite", "context under 512"; recording the weights revision hash; paired differences as the bootstrapped statistics; same-rows rule across v2 and both models; refusing base dates on or after 2025-10-20 in the tooling.
