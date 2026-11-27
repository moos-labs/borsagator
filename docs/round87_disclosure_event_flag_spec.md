# Round 87, rank 2: issuer disclosure-event flag, forward only (spec and point-in-time check)

Spec only. No fit, no score, nothing computed on existing cells. The only code is the point-in-time check (benchmarks/disclosure_pit_check.py, tests in scripts/test_disclosure_pit_check.py).

## Why forward only
The structured-events pilot (docs/disclosure-events.md, scripts/disclosure_events.py, schema v1) covers 2026-08-19 to 2026-11-19, 9 events. Every captured cell has a cutoff from 2023-12-29 to 2026-09-30, so there is no cell with a full event record behind it to fit on. Cells 1-102 are not used.

## Event schema (frozen at schema_version 1, extractor disclosure-events/1.0.0)
The flag reads only these fields of a record: `event_id`, `event_type`, `subtype`, `issuer`, `announced` (a date, no time of day), `verification_status`, `extraction_status`, `stale`, `source_url`, `document_revision_id`, and one role-bound forward date from `payload` (entitlement-end, payout or ex-date for a dividend; any other event type contributes only if it carries a role-bound forward date). Only `verification_status` verified and `stale` false records enter. Candidates and stale records are counted and never flag.

## What a flag means
An event can flag a window only if the date it points to lies in the future of the cutoff and was announced before the cutoff. A results release or a board decision is announced when it happens, so it is not known ahead and cannot flag its own window. Only a record that announces a later date (a board-meeting notice, an AGM, an entitlement-end or ex-date) can.

## Point-in-time rule (implemented in the check)
For cutoff date c, horizon end e (the h-th Egyptian business day after c, Sunday to Thursday, holidays ignored) and a record with announced date a and forward date f:
- usable only if a < c (strict, because `announced` carries no time of day, so a same-day announcement cannot be shown to precede the close of the cutoff day);
- flags only if c < f <= e;
- a record with a missing `announced` or missing forward date never flags and is counted.

## Accumulation and later steps (not run here)
- Each sweep appends events. A cell enters the fit only when its cutoff date is on or after the first sweep date with a full event record for the issuer.
- Fit (later, forward cells only): two multipliers per horizon (flagged, unflagged) on frozen v2 under the mean-width constraint, as in round 87 rank 1. Minimum 5 flagged and 5 unflagged training rows per horizon, else not fitted.
- Loop bar on untouched cells only: RangeSkill cutoff-clustered CI lower bound > 0 AND coverage CI overlapping [0.75, 0.85] with width <= 0.15 AND at least 10 cutoff clusters. Fewer than 10: counts only.
- Pre-registration of the fit is committed before any forward cell is scored.
