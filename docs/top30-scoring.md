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
- Quarter date eligibility is frozen in the manifest
  (`evaluation/top30_manifest.json`, `$.quarter.date_eligibility`):
  source-adjudicated announced date, start 2026-08-19 inclusive, end
  2026-11-19 inclusive — an extraction error cannot choose its own
  recall denominator.

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

1. Group gold and predicted events by **same source document id**,
   **same event type** and **same issuer**. Nothing matches across
   documents, across types, or across issuers. Issuer is part of the
   grouping key, not assumed from prepartitioning.
2. Within a group, pair predicted events to gold events **one-to-one**:
   each gold event is used at most once. **Duplicates cannot reuse the
   same gold event** — a second predicted event paired to an already-used
   gold event is an FP (see the `duplicate-reuse` fixture).
3. Matching is **order-independent**: within a group the scorer takes a
   **maximum-total-agreement** one-to-one assignment, where agreement is
   the count of scored fields equal after §6 normalisation, and a pair
   is eligible only with agreement ≥ 1 (the event must be identifiable
   by coupon / period / meeting details, whichever the type carries).
   Disambiguation **must not require every predicted field correct** —
   a wrong date or NPAT is a field error on an identifiable event (§6),
   not a matching failure. A predicted event is matched only when it is
   paired to the **same** gold event in **every** maximum-agreement
   assignment (a forced pair); identical duplicate predicted events are
   interchangeable, so one of them takes the gold and the rest are FPs.
   Being paired to one gold in some optima and **unmatched in others
   is not a forced pair either** — such an event is left unmatched
   (FP) and flagged ambiguous, with `unmatched_in_an_optimum` recorded
   so adjudication knows the event may equally be no event at all, not
   just the other gold (issue #313). Groups of 8–15 events per side
   use the same rule computed exactly, not greedily: the maximum total
   agreement comes from the assignment problem (Hungarian algorithm),
   and partner sets across all optima are recovered by re-solving the
   reduced problems (a pair is in some optimum iff its agreement plus
   the optimum without that pred and gold equals the full optimum).
   The result depends only on the event multisets, never on predicted
   input order (see the `order-permutation` fixtures).
4. **Ambiguous pairings need adjudication, not a favourable automatic
   match.** If a predicted event is paired to two or more different
   gold events across maximum-agreement assignments, or if two or more
   differing predicted events tie for one gold event, the scorer leaves
   the predicted event(s) unmatched (FP), leaves the gold events
   unmatched (FN), and flags the group `ambiguous` in the per-cell
   report for human adjudication. The scorer never breaks a tie in the
   direction that raises the score.
5. **Groups over 15 events per side are rejected into adjudication,
   never approximated.** Realistic groups are 1–3 events (the
   extractor emits at most one event per type per document, §2); a
   group this large is a pathological input. No pair is matched, every
   predicted event is an FP, every gold event an FN, and every
   predicted event is flagged ambiguous with `oversize_group` set. The
   former canonical-greedy large-group fallback
   (`_match_group_greedy`) is deleted (issue #313): no greedy
   approximation exists anywhere in the matcher.
6. Issuer mismatch is a matching failure, not a field error: a predicted
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
  the typed canonicalisation contract below. Dates to ISO `YYYY-MM-DD`;
  amounts as decimal strings (`Decimal`, never float); Arabic-Indic
  digits normalised; currency and scale (`one` / `thousand` / `million`
  / `billion`) compared as part of the value. A sign is part of the
  value: predicted NPAT `100` against gold NPAT `-100` (a loss) is a
  **wrong value (1 FP + 1 FN)**, never a match on magnitude (see the
  `sign` fixture). A swapped pair of dates is two wrong values (see the
  `swapped-date` fixture): ex-date wrong and payout-date wrong, each
  1 FP + 1 FN.

### Canonicalisation contract (typed, per field)

| Field(s) | Canonical form | Tolerance |
|---|---|---|
| `ex_date`, `entitlement_end`, `payout_date`, `record_date`, `announced`, `period_start`, `period_end`, `meeting_date`, `assembly_date` | ISO `YYYY-MM-DD`. Accepts ISO, `D/M/YYYY`, `D-M-YYYY`, `YYYY/MM/DD`; Arabic-Indic digits (U+0660–0669, U+06F0–06F9) normalised to ASCII; validated as a real calendar date | exact (0) |
| `amount_per_share`, `npat`, `npat_comparative`, `revenue` | `(Decimal in base units, CURRENCY)`: value × scale factor (`one` 1, `thousand` 10³, `million` 10⁶, `billion` 10⁹); bare numbers read as EGP; currency compared as part of the value, so EGP never equals USD | exact (0) |
| `yoy_npat_pct` | `Decimal` (sign preserved; parentheses mean negative, Arabic loss reporting) | exact (0) |
| `assembly_time` | `HH:MM` (24h); accepts `HH:MM`, `HH:MM:SS`, `HH:MM AM/PM` | exact (0) |
| `subtype`, `state`, `npat_scale` | lowercased, whitespace-collapsed string | exact (0) |
| `coupon` and all other fields | stripped string | exact (0) |

Tolerances are **zero for every field by design**: exact equality after
canonicalisation. Any future non-zero tolerance is a spec change, not a
scorer change — the reference scorer records the table above and
implements it exactly.

**Extractor adapter.** The extractor's native date/money values are
nested objects (`scripts/disclosure_events.py` `_date_field` /
`_money_field`: `{"value", "basis", "evidence", ...}` and
`{"value", "currency", "scale", "raw", "evidence"}`); the scorer
flattens them explicitly: a date object contributes its `value`
(a `None` value stays `None` — a derived candidate is never a value),
a money object contributes `(value × scale, currency)`. Flat scalars
(gold, or flat predicted values) use the same canonical forms with
scale `one` and currency defaulting to EGP.
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

The reference scorer implements this full verdict: `accepted` in
`score_cell` requires the event verdict AND every assessable scored
field's verdict (a field whose denominators are both zero in the cell
is N/A for that field and does not gate acceptance); `field_verdicts`
reports the per-field verdicts. A cell whose event P/R pass but any
scored field fails is NOT accepted.

Plus, evaluation-wide:

- **collection 100%** — every enumerated expected document archived;
  a missing record is a named failure, not an exclusion;
- **unresolved in-scope cases: zero** — an ambiguous pairing, a
  candidate that could be an event, or a collection gap blocks
  completion; it is never resolved by dropping the case;
- **candidates reported separately from verified TPs** in every report.

### Completion is separate from acceptance (issue #314, INS-314)

`accepted` is a per-cell threshold result only — True/False/None,
provisional before completion, never final acceptance. Completion is
separate state, computed by `scripts/top30_completion.py` on top of
the unchanged scorer (`evaluate_completion`):

- **`complete`**: required enumeration/capture and gold/adjudication
  finished, no unresolved in-scope cases. Missing or unknown gate
  inputs fail closed (incomplete, never a pass).
- **Final outcome**: `incomplete` / `complete-pass` / `complete-fail`
  / `complete-N/A`. A fully adjudicated evaluation can be complete
  even when quality fails (complete-fail). An entirely N/A evaluation
  is complete-N/A, never a quality pass. A final pass requires
  completion plus every assessable required cell passing.
- **Collection** (`collection` state: `enumerated` / `archived` /
  `missing` (named) / `enumeration_closed` / `pagination_complete`):
  a ratio of archived/enumerated = 100% is insufficient unless
  enumeration itself is closed and evidenced complete across the
  frozen universe/window — otherwise an unfinished enumerator could
  declare success over its current subset. Partial collection names
  missing documents and blocks completion; event FNs are never
  invented for a missing document whose gold events are unknown
  (collection and event denominators differ).
- **Unresolved ledger**: built from the scorer's matching records
  (every `ambiguous` entry, including `oversize_group` and
  sometimes-unmatched records) PLUS unresolved candidate/source-gold
  decisions, relevant field uncertainty, and collection/enumeration
  failures — never from `ambiguous == []` alone (a candidate sits in
  `unmatched_predicted`). Ledger entries carry stable IDs tied to the
  frozen run/input digests, never array position or a gold-ID list.
  IDs are distinct per frozen prediction occurrence: N identical
  predictions yield N distinct IDs (an occurrence index is folded
  into the hashed detail), so one decision over one ID can never
  clear N entries. The mandatory ambiguity/candidate/collection
  ledger is derived internally by `evaluate_completion` from the
  scorer outputs and the collection state: an omitted, empty or
  truncated caller ledger never passes while such cases exist, and
  a frozen required-cell set must be supplied whenever cells are
  present (without it, omitted universe members are undetectable).
  Collection counts must be non-negative; a cell's `accepted` must
  be exactly True/False/None (by identity — `1`/`0` are not
  verdicts).
- **Scope**: an out-of-scope ambiguity blocks only until an
  evidence-backed scope decision exists; the entry is retained with
  the exclusion reason. Scope is the frozen roster +
  date/document/event rules + adjudications, not an arbitrary
  caller-supplied `in_scope=False`. Unknown scope blocks.
- **Fields**: a resolved wrong field contributes its FP/FN and
  threshold failure (complete-fail), not perpetual incompleteness. An
  unresolved required gold/source-field interpretation blocks
  completion. A documented absent/N/A field follows the frozen N/A
  policy (named per cell, e.g. `record_date` where the EGX body
  never states it).
- **Adjudication**: decisions persist evidence, affected stable IDs,
  run/input revisions and superseded decisions. Count-changing
  decisions (pairing) apply only through the explicit adjudication
  adapter (`apply_adjudication`) and a re-score; merely marking an
  entry resolved, a stale/wrong-run decision, conflicting decisions,
  or an unresolved supersession all fail closed. A pairing joins
  only events from the same source document, issuer and event type
  (the frozen same-document matching rule — membership in the
  unmatched lists plus field agreement is not enough). A decision
  resolves only a ledger entry of a compatible kind: ambiguity by
  pairing / reject_event / duplicate; candidate by reject_event /
  duplicate; field by field; scope by scope; gold by field / scope;
  collection entries by no decision at all — they close only when
  the collection state shows the document archived. An ambiguous or
  candidate case argued out of scope is recorded as its own
  kind=`scope` ledger entry and resolved by a scope decision there.
  Frozen predictions are never edited into correct answers: a
  resolved candidate cannot gain a TP by status rewriting.
- **Per-cell blocking**: `per_cell.blocked` reflects the global
  collection state as well as unresolved ledger entries — an
  unknown, unfinished or partial collection blocks every cell, so
  report truth never depends on whether the caller remembered to
  build a ledger.
- **No report runner exists at this pin**: collection state and
  adjudication records have the schemas/interfaces defined here and
  in `top30_completion.py`, and `cell_report` builds the §8 per-cell
  report (collection, counts, verified vs candidate counts,
  unresolved ledger, `complete` + outcome) for the future runner to
  call. The gate itself is fully testable without live collection —
  the gate cannot invent missing evidence, so unknown inputs stay
  incomplete.

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
the separate completion state (`complete` + final outcome
`incomplete` / `complete-pass` / `complete-fail` / `complete-N/A`,
alongside the scorer's provisional `accepted` — a threshold pass is
never reported as a completed evaluation); and, where the §2 limit
bit, the count of gold events unmatchable because of it. The report's
`unresolved_candidates` counts unresolved candidate ledger entries
for the cell (derived from the effective ledger, so a resolved
candidate no longer counts); the raw candidate-output count is kept
separately as `candidate_outputs`. Roll-ups
(per issuer, per type, overall) are summaries only — acceptance is
per cell, never on a roll-up, and a roll-up cannot rescue a failed,
blocked or unproven cell.

## 9. Reference implementation

`scripts/top30_scorer.py` implements §4–§7 exactly (order-independent
maximum-agreement matching within same source document, type and
issuer; candidate-never-TP; duplicate reuse as FP; ambiguous tie as
unmatched + flagged; forced pair only when paired to the same gold in
every optimum, including being matched (not unmatched) in every
optimum; groups of 8–15 events per side solved exactly via the
assignment problem, groups over 15 rejected into adjudication with
`oversize_group` and no greedy fallback anywhere; wrong value as 1 FP
+ 1 FN; end-to-end field denominators; exact-fraction full acceptance;
typed canonicalisation contract with the extractor adapter). Its
negative controls live in
`scripts/test_top30_scorer_283.py`
(swapped-date, sign, duplicate-reuse, candidate-only, plus the #305
controls: full-verdict assertions, separated candidate/extracted
status controls, missing/unknown-status rejection, multi-event
permutation tests, issuer/schema/currency/scale controls, plus the
#313 controls: the forced-pair counterexample, the forced-pair-holds
case, the 8-event exact-beats-greedy case, the oversize-group
adjudication case, and the random-group matching property test) and are
wired into `scripts/harness_issue109.py` (`--scorer`). The completion
gate lives in `scripts/top30_completion.py` (separate `complete` +
final outcome over the unchanged scorer; unresolved ledger from
matching records + candidates + field/collection inputs; frozen
collection/ledger/adjudication schemas; fail-closed adjudication
adapter; mandatory ledger derived internally and distinct IDs per
prediction occurrence, same-document/issuer/type pairing,
decision/entry-kind compatibility, non-negative collection counts,
exact `accepted` domain, per-cell blocking from global collection
failures — issue #322) and its negative controls live in
`scripts/test_top30_completion_314.py` (Ins's 8 required regression
cases: contested group, candidate / sometimes-unmatched / oversize,
collection gaps, out-of-scope, fields, adjudication applied vs
merely marked, roll-ups, empty cells — plus the
`accepted`-unchanged and §8-report-shape controls, plus the #322
regressions: omitted/empty/truncated ledger, mandatory required-cell
set, multiplicity IDs, per-cell blocking, cross-document pairing,
decision-kind compatibility, collection-entries-by-evidence-only,
negative counts, malformed `accepted`, ledger-derived candidate
reporting), also wired into
`scripts/harness_issue109.py` (`--scorer`). If the spec and the
scorer ever disagree, **the spec wins** and the scorer is fixed.

## 10. Input boundaries

Scoring inputs fail closed, never fail open:

- A predicted event with a missing or unknown `extraction_status`
  (`extracted` / `candidate`) or `verification_status` (`verified` /
  `unverified`) is rejected with `ValueError` — there is no default
  status.
- An event with a missing or unknown `event_type`, a missing
  `source_document_id` or a missing `issuer` is rejected.
- A gold event carrying a prediction-only status is rejected: gold
  never carries `extraction_status` / `verification_status`.
