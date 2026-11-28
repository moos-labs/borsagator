# Round 93: forward cutoff schedule, registration (draft for Moos)

Status: REGISTRATION (the three open points of the first draft are decided below, per Moos in Slack 1795829375.713939, relayed to the author, not read by the author). Nothing here is scored, no capture is dispatched
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
- First cutoff: the first such Thursday whose cutoff session closes strictly
  after the merge date of this document. The date is written into the
  schedule file by the cycle at the first dispatch and never edited
  afterwards. A holiday Thursday moves to the previous session, and the move
  is logged. The moved session must itself close after the merge date: if the
  move would land on or before the merge date, that Thursday is not the first
  cutoff and the first cutoff is the following Thursday (or its moved session,
  under the same test). Later cutoffs are unchanged by this rule.
- Universe: the 36 EGX names of the Yahoo store (ohlcv/yahoo, the 37 files
  minus NVDA). NVDA is not in this schedule. A name with fewer than 120 bars
  before a cutoff, or with no close on the cutoff session, is excluded for
  that cutoff and listed one by one with the reason. Nothing is imputed.
- Horizons: day (1 session), week (5), month (21), as in every earlier scorer.
- Month horizon is scored on every 4th cutoff only: cutoffs number 1, 5, 9, 13 and so on (cutoff 1 is the first one). Day and week are scored on every weekly cutoff. All cutoffs are still captured, so the 4th-cutoff subset is fixed by number, never chosen after seeing results.
- Cell numbering: from 103, one cell per (ticker, cutoff) capture, ordered by
  cutoff date then ticker ascending. Cells 91-102 are not reused or renumbered.
- Clustering unit: the cutoff date (for month, the month-scored cutoff dates).
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

One scoring, at the time the month horizon has 10 matured clusters. Month
clusters are cutoffs 1, 5, ..., 37; the 10th (cutoff 37) matures 21 sessions
after its cutoff, so the read is about 41 weeks after the first cutoff. All
three horizons are read at that moment (day and week then have far more than 10
clusters). Before then only counts are printed: rows, clusters, exclusions
listed one by one. No RangeSkill, coverage or CI is printed or written, and no
interim result is looked at. Fewer than 10 matured month clusters at that
moment means COUNTS ONLY and the read waits for the next month cluster.

## Decided points

1. Month overlap: decided, month scored on every 4th cutoff, by nominal
   spacing (4 weeks between month-scored cutoffs). This is not changed to
   session counting. With no session closures in the 4 weeks, consecutive
   month-scored cutoffs are 20 sessions apart and their 21-session windows
   share at most 1 session. That holds only without closures. Each closure
   (holiday, or a holiday Thursday moved to an earlier session) between two
   consecutive month-scored cutoffs lowers the session distance between them
   by one, so their windows share one more session per closure. A cutoff moved
   from a closed Thursday to the Wednesday before shortens the gap before it
   by one session (that pair shares 2). The gap after it is one session longer
   because it starts a day earlier, and shorter by one because the closed
   Thursday lies inside it, so it stays 20 apart (that pair shares 1, not 0).
   The overlap is calculated from the actual session dates, not from the
   nominal spacing. No cutoff is added, moved or dropped to repair the
   overlap, and the month-scored set stays fixed by cutoff number. The
   shared-session count of each consecutive month-scored pair is reported with
   the read, never gating.
2. Holm: as written in "Test family and Holm": one-sided cluster bootstrap p,
   Holm step-down at 0.05 over the family of 6, plus the loop CI conditions.
3. The paired delta (challenger minus frozen v2) on the same rows is reported
   with its cutoff-clustered CI and never gates. The loop bar is the gate.

## Known limits

- Pretraining. Chronos-2 has no documented cutoff or EGX exclusion, and the
  dataset list (appendix Table 6 of arXiv 2510.15821) was not read, so
  whether EGX or Yahoo series are in the training data is UNVERIFIED. Forward
  cutoffs (December 2026 onward) are over a year after the model release
  (2025-10-20 per the amazon-science/chronos-forecasting README), hence after
  any plausible training window.
- The 4th-cutoff rule makes the month read slow (about 41 weeks). Day and week
  could be read earlier but are held to the same single scoring.
