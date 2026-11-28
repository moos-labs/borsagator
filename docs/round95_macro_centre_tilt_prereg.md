# Round 95: macro-proxy centre tilt (oil, USD/EGP, 91-day T-bill), pre-registration

Status: FROZEN REGISTRATION, written before any macro-tilt value is computed or scored. Origin: INS-IMPROVE-095 rank 2 (Moos Slack 1795836669.620899, relayed to the author, not read by the author). The three previously open decisions were filled by Moos (Slack 1795837518.314579, relayed to the author, not read by the author) and are recorded below as decided. Nothing in this commit is scored; no existing cell, frozen value or script is changed.

## Question

Does a fixed-rule shift of the band CENTRE from 0 to a small macro-proxy-based value, with the frozen v2 half-width unchanged, improve RangeSkill versus frozen v2 on the same rows? Extension of the merged round 78 regime tilt (#933). Width is untouched, so the coverage conditions stay those of frozen v2.

## Series (all three exist, with a point-in-time key)

| Series | Frequency | Source | Point-in-time key |
|---|---|---|---|
| Brent spot, USD/bbl | daily | FRED DCOILBRENTEU (EIA spot), https://fred.stlouisfed.org/series/DCOILBRENTEU, vintages at https://alfred.stlouisfed.org/series?seid=DCOILBRENTEU | observation date, usable at cutoff D only if observation date <= D minus 3 calendar days (EIA publishes with a lag; opened FRED page shows data through 2026-11-24 on 2026-11-28); the ALFRED vintage as of D is the check |
| USD/EGP, CBE interbank weighted average, weekly | weekly | evaluation/macro_series/usd_egp_interbank_weekly.csv (#939), CBE Monthly Statistical Bulletin Table 17 | row `published_date <= D` (first of the bulletin issue month) |
| 91-day T-bill accepted yield, weekly | weekly | evaluation/macro_series/tbill_91d_weekly.csv (#939), Table 15 | row `published_date <= D` |

Rules: a row is usable at cutoff D only if its key above is <= D. Rows read in the files show both short and long publication lags (a 2021-08-11 observation published 2021-12-01, a 2026-08-26 observation published 2026-09-01), so the rule reads the latest USABLE row at D, never the latest observation. No value is filled or interpolated. A missing signal is 0 (DECIDED, Moos) and every row with a missing signal is listed with the series and reason. The CBE bulletin basis is not the Mubasher price basis and is never mixed with it.

Not used: sovereign spread (no free daily point-in-time source found) and PMI (monthly, seasonally adjusted, revisable, history behind aggregators). Brent is the only oil series. Regional PMI was not checked.

## Rule (nothing fitted, no training cells used)

For each capture with cutoff D and each horizon:
1. For each series, signal x in {-1, 0, +1}: x = +1 if the latest usable value is more than THETA above the usable value 63 calendar days earlier (the latest usable row at D minus 63 days), x = -1 if more than THETA below, else 0. 63 days is about 9 weeks, fixed. THETA: Brent 5 percent, USD/EGP 2 percent, T-bill 100 basis points (absolute). DECIDED (Moos): THETA values and the 63-day window as stated. The reference value is the latest row usable at D with observed_date <= (observed_date of the latest usable row) minus 63 days.
2. Direction map, DECIDED (Moos): d_oil = -1, d_fx = +1, d_tbill = -1. The author did not choose these; the sources opened do not settle the sign.
3. Composite m = (d_oil x_oil + d_fx x_fx + d_tbill x_tbill) / 3, in [-1, 1].
4. Tilted centre c = S x m x v2_half(h) where v2_half(h) is the frozen v2 half-width for that row and horizon in percent (as computed by the existing scorer path). S = 0.10 (DECIDED, Moos), so the centre never moves more than 10 percent of the half-width, the same size as the round 78 clip. Band half-width is exactly frozen v2's.

Brent availability rule for 91+ scoring (explicit): the +3-day rule stays, exactly as registered in the Series table. A Brent observation is usable at cutoff D only if its observed date is on or before D minus 3 calendar days, and the stored published date is observed date + 3 days. This is the same rule the stored descriptive record (cells 48-90) was generated under, so that record matches the chosen rule and is NOT regenerated. Decision: Moos (Slack 1795849665.024479, relayed to the author, not read by the author). The ALFRED as-of-cutoff comparison (evaluation/macro_series/brent_alfred_vintage_check_cells48_90.md) found 0 revised values and a longer availability lag in the vintages; under vintage availability the Brent signal at the 2025-09-30 cutoff would be -1 instead of 0. That difference is recorded as a sensitivity only, not a rule change.

Arms: reference frozen v2 (centre 0), challenger tilt (centre c). One challenger, one S, one window. No grid, no second variant. Adding any needs a new registration and gets no cutoff already read.

## Data discipline

- Training: not used. Nothing is fitted, so cells 1-47 are not read for this item.
- Descriptive: cells 48-90 only. Counts first (rows with all three signals usable, rows with a missing signal, clusters per horizon, each excluded row listed one by one with its reason). Then descriptive RangeSkill (tilt minus frozen v2 on the same rows) and coverage with cutoff-clustered bootstrap, 5000 reps, seed 20261125, default reps only. No verdict word. Cells 48-90 hold 43 captures: 8 cutoff dates before any origin filter (no Chronos-2 pretraining rule applies to this item), 7 or 8 clusters per horizon depending on usable rows. The count is printed before any statistic.
- Clean scoring: untouched cells 91 and later only (and cutoffs of the forward weekly schedule if it is merged and dispatched, #953). Never cells 48-90.
- Independent unit: the cutoff date. Rows of one cutoff share the same three signals, so each cutoff has one signal triple; the effective number of distinct tilts is the number of distinct cutoff dates.

## Loop bar (the only gate)

A horizon is KEPT only when on untouched cells all of these hold:
1. RangeSkill (tilt versus frozen v2, same rows) cutoff-clustered 95 percent CI lower bound > 0.
2. The cutoff-clustered coverage 95 percent CI overlaps [0.75, 0.85] with width <= 0.15.
3. At least 10 cutoff clusters back the horizon.

Fewer than 10 clusters: COUNTS ONLY, no coverage, skill or CI printed or written. A KEEP is not an adoption. Cells 91+ currently hold 12 captures from 2 cutoffs before the origin filter, so no KEEP is possible on them yet; the read waits for clusters.

## Known limits

- Signal count: the composite takes at most 4 values per row after rounding to thirds, and many cutoffs share a signal state. The descriptive read has about 7 distinct tilts. Treat any 48-90 number as descriptive of those dates only.
- The USD/EGP and T-bill rows are weekly with a variable publication lag; the latest usable row at D can be months old. The rule reads what was knowable at D, which may be stale.
- Oil is global (Brent is not Egyptian). It is a proxy by assumption.
- Brent rows are stored with published_date = observed_date + 3 days by this rule (FRED CSV, not a vintage); the ALFRED vintage check was run for the 8 descriptive cutoffs (cells 48-90), 28 Nov 2026, using https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=DCOILBRENTEU&vintage_date=<cutoff> (fetched, opened as CSV). Result: REVISIONS none (4614 stored observations present in the as-of vintages, 0 values differ). AVAILABILITY differs: the as-of vintage lacks the most recent observations (up to 8 days before the cutoff in the cases seen, e.g. cutoff 2025-09-30 latest vintage observation 2025-09-22), so the +3-day rule is optimistic. Applying the same selection rule to the vintage rows changes the Brent signal at ONE cutoff, 2025-09-30 (stored 0, vintage -1); the other 7 are unchanged. The stored descriptive record uses the +3-day rule and was NOT regenerated: replacing it with vintage availability alters a registered rule, which is Moos's call. Check table: evaluation/macro_series/brent_alfred_vintage_check_cells48_90.md.

## Decisions (all filled by Moos, Slack 1795837518.314579, relayed, not read)

1. d_oil = -1, d_fx = +1, d_tbill = -1.
2. S = 0.10, window 63 days, THETA Brent 5 percent, USD/EGP 2 percent, T-bill 100 bp.
3. Missing signal = 0, each such row listed.
