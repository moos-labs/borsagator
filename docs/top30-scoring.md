# Top-30 EGX disclosure-events evaluation — scoring specification (#283, stage 1)

Frozen scoring rules for the top-30 evaluation. Source: moos-labs/borsagator
issue #283, comment 7016564975 (INS-283-EVAL-DESIGN part 2, verified SOUND by
Moos 2026-11-19). The roster, quarter and extractor revision this spec
scores against are frozen in `evaluation/top30_manifest.json` (base commit
`424f4b3`). Any change to the manifest, the extractor or this spec is a new
frozen revision — scores are never recomputed silently under changed rules.

## 1. Cells

- A **cell** is one issuer × one event type.
- Event types: `dividend`, `earnings`, `board-decision`.
- FAIT/FAITA is **one issuer**: its two listings union source records,
  duplicate source ids are deduplicated before scoring, and it forms one
  cell per type, not two.
- POUL and COMI are **regression controls outside the 30**, scored the same
  way but reported separately; their pilot bar (111/111, field P/R 1.000)
  must be preserved.
- A cell with no gold events and no predicted events is reported as
  **zero-denominator N/A with the raw counts shown** (0/0/0) — never as a
  pass, never as a failure, never omitted.

## 2. Frozen event granularity (current implementation limit)

The extractor emits **at most one event per trigger type per document**
(`scripts/disclosure_events.py:701-714` — dividend / earnings /
board-decision dispatch). This is a limit of extractor revision
`disclosure-events/1.0.0` (schema v1, config hash `05efef83ce166443`),
**not** a property of the gold:

- If a source document carries two eligible facts of the same type (e.g.
  two dividends), the gold records two events and the extractor can at
  most emit one. The second gold event is a **FN**, and the per-cell
  report names the limit as its cause.
- The limit must never be used to define the second fact out of the gold,
  and never to merge two gold events into one.
- A document carrying one fact of each of two types yields up to two
  events (one per type); types never collapse into each other.

## 3. Gold

- Gold is built by **assisted census + human adjudication against sources**,
  including documents where extraction found nothing. Gold outputs are
  hidden during the initial census to reduce anchoring.
- Agreement between extractors is silver, not proof of recall; evidence
  offsets prove a quote exists, not its role or interpretation.
- Every gold event carries: `source_document_id` (`egx:<NewsID>`),
  `event_type`, `issuer`, and its fields (see §6). Within one source
  document, gold events of the same type carry **independently assigned
  within-document identities** (e.g. `gold_id`) so matching never depends
  on the predicted event's own claims.
- **Candidate status never grants a TP.** A predicted event whose
  `extraction_status` is `candidate` (or `verification_status` is anything
  other than `verified`) is not a TP even if every field matches gold.
  It counts as an unmatched emitted event (FP) and its gold counterpart,
  if any, as not correctly emitted (FN). See §4 and the
  `candidate-only` fixture in `scripts/test_top30_scorer_283.py`.

## 4. Matching (event level)

1. Group gold and predicted events by **same source document id** and
   **same event type**. Nothing matches across documents or across types.
2. Within a group, pair predicted events to gold events **one-to-one**:
   each gold event is used at most once. **Duplicates cannot reuse the
   same gold event** — a second predicted event paired to an already-used
   gold event is an FP (see the `duplicate-reuse` fixture).
3. Where a group holds more than one gold event of the same type,
   disambiguation uses coupon / period / meeting details (whichever the
   type carries). Disambiguation **must not require every predicted field
   correct** — a wrong date or NPAT is a field error on an identifiable
   event (§6), not a matching failure.
4. **Ambiguous pairings need adjudication, not a favourable automatic
   match.** If two or more gold events tie as the best match for one
   predicted event, the scorer leaves the predicted event unmatched (FP),
   leaves the tied gold events unmatched (FN), and flags the group
   `ambiguous` in the per-cell report for human adjudication. The scorer
   never breaks a tie in the direction that raises the score.
5. Issuer mismatch is a matching failure, not a field error: a predicted
   event attributed to the wrong issuer (title/body ticker disagreement,
   downgraded to candidate by the extractor) cannot match that issuer's
   gold.

## 5. Event-level counts

Per cell, over matched pairs plus unmatched events:

- **TP** — a correctly identified, human-confirmed emitted event: a
  predicted event paired one-to-one with a gold event of the same
  document and type, with `verification_status == verified`. (Field
  errors inside a TP are scored separately in §6; they do not unmake
  the event TP.)
- **FP** — an unmatched or incorrect emitted event: a predicted event
  with no gold counterpart, a duplicate reusing an already-matched gold
  event, a candidate masquerading as an event, or a predicted event left
  unmatched by an ambiguous tie (§4.4).
- **FN** — an eligible gold event not correctly emitted: a gold event
  with no verified predicted counterpart, including gold events missed
  because of the one-event-per-type-per-document limit (§2).

Precision and recall per cell, exact fractions (see §7):

- `P = TP / (TP + FP)`; `R = TP / (TP + FN)`.

## 6. Field-level scoring

- Fields are scored **independently** of the event match, with
  **end-to-end denominators across all gold events, including unmatched
  ones**. A field score computed over matched events only is diagnostic
  and must be labelled as such — it is never the reported field P/R.
- Per field, per gold event in the cell:
  - predicted value equals gold value (after §6 normalisation) → **TP**;
  - predicted value present but different → **1 FP + 1 FN** (a wrong
    predicted value is 1 FP + 1 FN — the rule already in
    `scripts/harness_issue109.py:142-163`);
  - gold value present, predicted missing/null → **FN**;
  - predicted value present, gold missing/null → **FP**
    (an unsupported extra).
- **Normalisation before comparison** (dates, units, tolerance first):
  dates to ISO `YYYY-MM-DD`; amounts as decimal strings
  (`Decimal`, never float); Arabic-Indic digits normalised; currency
  and scale (`one` / `thousand` / `million`) compared as part of the
  value. A sign is part of the value: predicted NPAT `100` against gold
  NPAT `-100` (a loss) is a **wrong value (1 FP + 1 FN)**, never a match
  on magnitude (see the `sign` fixture). A swapped pair of dates is two
  wrong values (see the `swapped-date` fixture): ex-date wrong and
  payout-date wrong, each 1 FP + 1 FN.
- The **record date is not in the EGX body** (pilot finding 1,
  `docs/disclosure-events.md`): the extractor records `record_date: null`
  with `derived_candidate` and the rule named `UNVALIDATED — candidate
  only, not a fact`. A derived candidate is never scored as a gold value
  and never as a predicted value; if gold later establishes a record
  date from a source that states it, the field is scored like any other.
- Scored fields by type:
  - **dividend:** `coupon`, `amount_per_share`, `ex_date`,
    `entitlement_end`, `payout_date`, `record_date`, `announced`.
  - **earnings:** `period_start`, `period_end`, `npat`, `npat_scale`,
    `npat_comparative`, `yoy_npat_pct`, `revenue`, `announced`.
  - **board-decision:** `meeting_date`, `assembly_date`,
    `assembly_time`, `subtype`, `state`, `announced`.
- Field P/R per cell are computed per field over the same TP/FP/FN rules
  and reported alongside the event P/R.

## 7. Acceptance

Per cell, **all four** must hold (event and field, precision and recall):

- event precision `P >= 0.95`, event recall `R >= 0.90`;
- field precision `P >= 0.95`, field recall `R >= 0.90`, per scored field.

Plus, evaluation-wide:

- **collection 100%** — every enumerated expected document archived;
  a missing record is a named failure, not an exclusion;
- **unresolved in-scope cases: zero** — an ambiguous pairing, a
  candidate that could be an event, or a collection gap blocks
  completion; it is never resolved by dropping the case;
- **candidates reported separately from verified TPs** in every report.

Arithmetic rules:

- Comparisons use **exact fractions** (`fractions.Fraction` in the
  reference scorer). **No rounding a failure into a pass**: 0.9499 is a
  fail; displaying `0.95` after rounding does not pass a cell.
- **Small cells get no exemption**: a 1-event cell that misses is a
  failed cell (R = 0/1), reported as such.
- **Zero denominators are N/A with raw counts shown**: e.g. a cell with
  TP=0, FP=0, FN=0 reports `P: N/A (0/0), R: N/A (0/0)` — never 0, never
  1.000, never a pass. A cell is N/A only when *every* denominator is
  zero; a cell where one side is N/A but the other is assessable is
  judged on the assessable side (TP=0, FP=0, FN=1 fails on recall,
  R = 0/1).
- Every report shows **raw counts** (TP/FP/FN) next to every P/R.

## 8. Per-cell report (required shape)

Each cell reports: collection status (enumerated / archived / missing,
named); event TP/FP/FN + P/R; field TP/FP/FN + P/R per scored field;
verified vs candidate counts; unresolved ledger (ambiguous pairings,
unresolved candidates, collection gaps — must be empty to complete);
and, where the §2 limit bit, the count of gold events unmatchable
because of it. Roll-ups (per issuer, per type, overall) are summaries
only — acceptance is per cell, never on a roll-up.

## 9. Reference implementation

`scripts/top30_scorer.py` implements §4–§7 exactly (one-to-one matching
within same source document and type, candidate-never-TP, duplicate
reuse as FP, ambiguous tie as unmatched + flagged, wrong value as
1 FP + 1 FN, end-to-end field denominators, exact-fraction acceptance).
Its negative controls live in `scripts/test_top30_scorer_283.py`
(swapped-date, sign, duplicate-reuse, candidate-only) and are wired
into `scripts/harness_issue109.py` (`--scorer`). If the spec and the
scorer ever disagree, **the spec wins** and the scorer is fixed.
