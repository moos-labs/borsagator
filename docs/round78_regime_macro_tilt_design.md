# Round 78 (a): regime-switching macro tilt, design and pre-registration

Written and committed BEFORE any macro series is assembled or any score is computed. Descriptive shadow only: no verdict word or key, no ensemble.py or frozen-value edits, never a keep claim by itself. Source: Moos Slack 1795791773.917879 (thread 1795787323.708359, read by the agent). Status: DESIGN + PRE-REGISTRATION + validating scaffold. No macro value is in this change.

## 1. Series to assemble (not yet collected; every value must carry a source)
| Series | Frequency | Source type to use | Point-in-time key |
|---|---|---|---|
| CBE policy decisions | event | the verified 47-event calendar on main (evaluation/macro_event/calendar_primary.json) plus the rate stated in each CBE MPC press release | release date of the press release |
| CPI (headline urban, YoY) | monthly | CAPMAS release, cross-read with the CBE inflation table | the CAPMAS release date, not the reference month |
| USD/EGP | daily | CBE published exchange-rate page, or the Mubasher/Yahoo basis already used for prices (basis named per row, never mixed) | the observation date |
| 91-day T-bill yield | per auction | CBE auction results | the auction result date |

Rules: a row needs `value`, `observed_date`, `published_date`, `source_url`, `source_name`. A row missing any of them is rejected, never filled. A value is usable at as_of D only if `published_date <= D` (point in time). No value is taken from memory. The scaffold below enforces this; the collection itself is the next step and is NOT done in round 78.

## 2. Regime input (rule-based first, fixed before fitting)
Markov-switching is rejected for the first pass (two cells of 47 cannot identify transition parameters; fitting also needs the series). Rule-based regime, three states from the policy-rate path only, computed from the calendar-linked press releases:
- tightening: the last decision at or before as_of raised the rate;
- easing: the last decision lowered it;
- hold: the last decision left it unchanged.
A second flag is reserved for later pre-registration (inflation momentum from CPI YoY vs its value 3 releases earlier). It is not used in the first pass.

## 3. Tilt (acts on frozen v2 only, shadow)
For each capture, regime r(as_of) picks a multiplier on the frozen v2 half-width: w_r in {tightening, easing, hold}; and an optional centre shift c_r (percentage points, centre only). Both are estimated on TRAINING cells 1 to 47 only, by the same procedure for every regime, chosen from a pre-registered grid (width multipliers 0.9, 1.0, 1.1; centre shifts 0). First pass uses width only; centre is reserved. Ties go to 1.0 (no change). The width multiplier is clipped to [0.9, 1.1] so no regime can move a band edge by more than 10 percent of the half-width. Frozen v2 is never edited; the challenger is computed beside it.

## 4. Data discipline
Training: cells 1 to 47. Descriptive only: cells 48 to 90. Untouched, clean scoring: cells 91 and later (cells end at 102 on main per the round-78 brief; the scorer must re-count). The independent unit is the cutoff date (cluster). The regime is read at the cutoff, so it is known before the forecast.

## 5. Keep rule (pre-registered, loop bar)
KEEP only if, on ALL horizons (day, week, month) on untouched cells: (a) RangeSkill of the tilt versus frozen v2 on the same rows has a cutoff-clustered 95 percent CI lower bound above 0, AND (b) the coverage CI overlaps [0.75, 0.85] with width at most 0.15, AND (c) at least 10 cutoff clusters back the horizon. Fewer than 10 clusters: no KEEP is possible, counts only. No KEEP is an adoption by itself.

## 6. First pass (descriptive)
Counts only below the gate: the scaffold prints (rows with a usable regime, rows without one, clusters per regime and horizon) and computes no statistic until a horizon has at least 10 cutoff clusters on untouched cells. There is no verdict word or key.

## 7. Known limits
- Three regimes on about 13 cutoffs is thin; the 10-cluster bar may be unreachable per regime, which the counts will show.
- The macro series do not yet exist in the repo; until they do, the scaffold reports "no macro series" and exits with counts.
- Release times of events are unsettled (rounds 75 to 77); the regime uses decision DATE and press-release date, so a same-day decision counts from the next session when the release time is unknown.
