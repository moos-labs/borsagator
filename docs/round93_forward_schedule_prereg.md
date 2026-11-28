# Round 93: forward cutoff schedule, registration (draft for Moos)

Status: DRAFT registration. Nothing here is scored, no capture is dispatched
by this document, and no existing cell, frozen value or script is changed.
Origin: INS-IMPROVE-093 rank 2 (Slack 1795828567.090869, relayed to the
author, not read by the author). Written before any forward cutoff exists.

## Why

Cells 91+ hold 12 rows in 2 cutoff clusters. The loop rule needs >= 10
clusters, so no route can be kept under the current cadence. This document
does not change any model. It fixes a forward schedule so that clusters
accrue on windows no earlier work has touched.

## Schedule (registered)

- One cutoff per week. The cutoff is the last EGX session of the week
  (Thursday; EGX trades Sunday to Thursday), taken at that session's close.
- First cutoff: the first such Thursday strictly after the merge date of
  this document. The date is written into the schedule file by the cycle at
  the first dispatch and never edited afterwards. A holiday Thursday moves
  to the previous session, and the move is logged.
- Universe: the 36 EGX names of the Yahoo store (ohlcv/yahoo, the 37 files
  minus NVDA). NVDA is not in this schedule. A name with fewer than 120 bars
  before a cutoff, or with no close on the cutoff session, is excluded for
  that cutoff and listed one by one with the reason. Nothing is imputed.
- Horizons: day (1 session), week (5), month (21), as in every earlier scorer.
- Cell numbering: from 103, one cell per (ticker, cutoff) capture, ordered by
  cutoff date then ticker ascending. Cells 91-102 are not reused or renumbered.
- Clustering unit: the cutoff date.
- Captures: the capture dispatch is the cycle's. This document asks for
  none and writes none.

## Compared arms (declared now, closed)

- Reference: frozen v2, untouched.
- Challenger A: Chronos-2 zero-shot quantile band, centre 0, half-width
  (q90 - q10) / 2 x RISK_MULT, RISK_MULT = 1.0, nothing fitted.
- Challenger B: the same model and quantiles, centre = q50, same half-width,
  RISK_MULT = 1.0.
- No challenger is added after the first cutoff. Adding one needs a new
  registration and a new schedule, and the added arm gets no cutoff that was
  already captured.

Challenger A and B are the arms of experiment E (benchmarks/score_tsfm_control.py,
#772). B needs a scorer change that is not made here. Neither arm is scored
on a forward cell before its scorer change is merged and its inference route
is confirmed.

## Test family and Holm

Family size is fixed at 6: 2 challengers x 3 horizons. Each test is the
cutoff-clustered bootstrap of RangeSkill (vs naive) for the challenger, 5000
reps, seed 20261125, resampling cutoff dates. The one-sided p is the share of
reps with RangeSkill <= 0. Holm step-down at 0.05 over the 6 p-values.

A (challenger, horizon) is KEPT only when all of these hold on the matured
forward cells:
1. RangeSkill cutoff-clustered 95% CI lower bound > 0 and it is Holm-rejected
   within the family of 6.
2. The cutoff-clustered 95% coverage CI overlaps [0.75, 0.85] with width
   <= 0.15.
3. At least 10 matured cutoff clusters.

Reported with every read, never gating: the paired delta of RangeSkill
(challenger minus frozen v2) on the same rows with its cutoff-clustered CI.
A KEEP is not an adoption. It justifies a forward-ledger test only.

## First read

One scoring, at the time the month horizon has 10 matured clusters (the 10th
cutoff plus 21 sessions, about 14 weeks after the first cutoff). All three
horizons are read at that moment. Before then only counts are printed: rows,
clusters, exclusions listed one by one. No RangeSkill, coverage or CI is
printed or written, and no interim result is looked at. Fewer than 10 clusters
at that moment means COUNTS ONLY and the read waits for the next cluster.

## Known limits and open decisions for Moos

1. Overlap. Weekly cutoffs make consecutive month windows share 16 of 21
   sessions, so month-horizon clusters are serially dependent and the
   cutoff-clustered CI will be too narrow. Week and day windows do not
   overlap. Option (not chosen here): score the month horizon on every 4th
   cutoff only, which needs 10 such cutoffs, about 40 weeks.
2. Holm over p-values from a one-sided bootstrap is my drafting choice. The
   loop rule itself is CI based. If the family should be corrected another
   way (for example wider CIs), say so before the first cutoff.
3. The paired delta against v2 is reported, not gating. Moos's earlier rule
   that a keep is relative to frozen v2 on the same rows could make it
   gating. This draft does not decide that.
4. Pretraining overlap. Chronos-2 has no documented cutoff or EGX
   exclusion. Forward cutoffs (December 2026 onward) are over a year after the model release, hence after
   any plausible training window. The release date is 2025-10-20 per the
   amazon-science/chronos-forecasting README.
