# Structured bilingual EGX disclosure events — archive/shadow pilot (#109)

Archive/shadow pilot only. Events are produced and measured; NOTHING
feeds the live ensemble or the live report. No `#68` model change, no
`compile_model.py` touch, no worker wiring in this change.

## Contract (schema v1, `scripts/disclosure_events.py`)

- One record, EN + AR fields. `summary_en` is a deterministic template
  over structured facts (`template-v1`); English summaries never
  introduce a number or date that is not a structured field.
- Dates are semantically separate and role-bound: a date is only ever
  read next to the wording that gives it its role
  (`تاريخ التوزيع` → payout, `تاريخ نهاية الحق` → entitlement-end,
  `تاريخ تحريك الحدود السعرية` → ex-date). No positional fallback, no
  first-date-wins.
- Amounts/ratios are decimal **strings** (`Decimal`, never float); the
  raw reported text, currency and scale (`one` / `thousand` /
  `million`) travel with every amount.
- Field-level evidence on every field: verbatim span + character
  offsets, source URL, document revision (`clipped-body-sha256:` — the
  hash of the retained clipped body, labelled as such; it is NOT a
  full-document hash).
- Extraction and verification are separate states. Incomplete or
  ambiguous output is a `candidate` with reasons, never a verified
  event. A document whose facts live only in an unharvested PDF
  attachment yields a candidate, not silence.
- Identity is stable within a pinned document revision
  (`egx:<NewsID>` + type + payload identity). Cross-document
  duplicates get an explicit `possible_duplicate` link — never an
  automatic merge. The #131 tolerance (1.89 / 1.9 / 1.8999999998 is
  one coupon) is used for linking only.
- The extractor never derives a record date. See below.

## Pilot results (2026-11-19, harness `scripts/harness_issue109.py`)

- Fixtures: 19 cases (7 real EGX goldens + synthetic negatives),
  **111/111 checks pass**; field-level precision **1.000** and recall
  **1.000** (90 TP, 0 FP, 0 FN). Verification split over the
  single-doc fixtures: 11 verified, 4 unverified (candidates).
- Pristine control: the naive extractor (first number as a float
  amount, first date as every date, no candidate state, no digit
  normalisation) fails all 6 discriminating cases.
- Mutants: `role-swap` killed (6 failures), `round2dp` killed
  (13 failures); both exit 1.
- Determinism: byte-identical canonical events across hash seed and TZ.
- Shadow run over archived sweeps (archive head `9c955db`): 15
  distinct EGX disclosures in the quarter window (2026-08-19 to
  2026-11-19), **9 events** — 1 dividend, 5 earnings, 3 board
  decisions; 6 extracted/verified, 3 candidates. Legacy
  `detect_corporate_actions` finds the same 1 dividend and agrees on
  ex-date and DPS (1/1) — but the legacy ex-date is *derived*
  (entitlement-end + 1 day) while the pilot's is *verbatim* from
  `تاريخ تحريك الحدود السعرية`.
- Full report: run the harness; `pilot_accuracy.json` lands in the
  stage directory.

## Findings the pilot surfaced (not assumptions)

1. **Record date is not in the EGX body.** POUL coupon 42 (NewsID
   296893) states announcement 02/11/2026, entitlement-end 15/11/2026,
   ex-date 16/11/2026, payout 18/11/2026 — and no record date. The
   2026-11-17 in the issue brief is a T+2 settlement derivation, so
   the pilot records `record_date: null` with
   `derived_candidate: "2026-11-17"` and the rule named
   `UNVALIDATED — candidate only, not a fact`. The extractor must
   never promote it to a fact; the live-feed decision needs a source
   that states it (or a validated rule).
2. **Harvester `iso_date` bug, confirmed live.** COMI 297291/297289
   are stamped `2026-01-01` — the harvester read the period start
   (`من 01/01/2026`) as the publish date. The extractor's announced
   date comes from the standalone date line under the title
   (10/11/2026), which rescues both. The shadow window is computed
   on the announced date for exactly this reason. A harvester fix is
   a separate follow-up.
3. **Attachment gap is the binding constraint.** Revenue (both POUL
   and COMI earnings), the board-decision details (POUL 297436, COMI
   297278) and the record date all live in PDF attachments the
   harvest does not retain. The pilot measures what the harvested
   bodies contain; end-to-end recall against a full corpus would be
   lower until attachments are captured.
4. **Coverage is 2 tickers, not top-30.** The archive holds only
   POUL.CA and COMI.CA EGX sweeps in the window. The pilot measures
   those honestly; the top-30 universe needs more tickers harvested
   before the accuracy numbers generalise.

## `fetch_feed.py` line pins — VERIFIED (not taken on trust)

Checked 2026-11-19 against `news-disclosure-runner` at the pinned
`1d0ee7db23a82088025ac6905e8764af9e948de9`:

| Ins's pin | Verdict |
| --- | --- |
| `attach_egx_harvest` at `:235` | **Verified** — `def attach_egx_harvest(disc, ticker, days=30)` |
| re-clip to 6,000 chars at `:329` / `:354` | **Verified** — `it["body"] = best["body"][:6000]` (:329) and `"body": h["body"][:6000]` (:354) |
| translation-chain doc `:588–599` | **Verified** — three-path comment block (Cohere → NLLB → Opus-MT), chunked per-6 fallback |
| "no structured event extractor in the runner" | **Verified** — grep finds no dividend/coupon/ex-date/event extractor; only `earnings` inside a Google News query string |

The feed the pilot needs exists: `results/disclosures.json`,
`news.json`, `feed_summary.json`; EGX bodies arrive via the harvest
attach (clipped to 6,000 chars) or the #91 outright-add path.

## What this change does NOT do (follow-ups, not in this PR)

- No consumer switch, no `#26` feeding: the feed is recorded per
  sweep but nothing in the ensemble or the report consumes events
  yet — that is #281 / #280. The worker wiring itself landed in
  #278 (see "Live wiring" below); it changes no `#68` model field.
- No `#68` surfacing (that needs a strict D-7 version bump).
- No harvester fix for the `iso_date` bug; no attachment capture.
- No top-30 coverage until more tickers are harvested.
- `#109` is CLOSED (2026-11-19, on the live-feed decision alone —
  option A sweep-live); its follow-ups are #278 (this wiring),
  #279 (attachments), #280 (#68 surfacing), #281 (#26 feeding),
  #282 (#32 adapter) and #283 (top-30 coverage).

## Feeding #26 dividend-aware scoring (#281)

`scripts/ensemble.py` (`events_to_corporate_actions` +
`merge_corporate_actions`, wired into the corporate-actions section
of `main()`) feeds verified dividend events into the same #26
scoring the legacy text detection feeds. `scripts/merge.py` stages
the #278 feed file (`disclosure-events/<CODE>-events.json`) into
the staged sweep tree **before** invoking the ensemble, so the
ensemble (CWD = stage) reads it; the worker already extracts before
the merge, so no worker change was needed. The horizon marking, the
#130 ex-date-today Kronos rescale and the model tripwire consume
event actions exactly like legacy ones — the output shape is the
`detect_corporate_actions` action dict plus provenance.

### Field mapping (event field → scorer input)

| Disclosure-event field | Scorer input (`#26` action) | Notes |
|---|---|---|
| `event_type == "dividend"` | gate: only dividend events considered | Earnings / board events never feed scoring |
| `payload.amount_per_share.value` (Decimal string, EGP, scale `one`) | `dps` (float) | Same guard as legacy: `0 < dps < base`, EGP only |
| `payload.ex_date.value` | `ex_date` | **Verbatim** (`verbatim:تاريخ تحريك الحدود السعرية`), `date_basis: "verbatim:ex-date"` — the legacy path derives it as entitlement-end + 1 |
| `payload.entitlement_end.value` | `entitlement_end` | Carried as-is; the ex-date is never re-derived from it when the verbatim ex-date is present |
| `announced.value` | `announced` (provenance) | Recorded on the action; no date parsing depends on it |
| `payload.coupon_number` | `coupon_number` (provenance) | Identity only |
| `issuer.ticker` | ticker guard | Must match the sweep ticker when present; absent is accepted (the feed file is already per-ticker) |
| `verification_status == "verified"` **and** `extraction_status == "extracted"` | gate: both required | A candidate is never a verified event; an unverified (e.g. republication) extraction is not trusted to move the score |
| `payload.record_date` | **not fed** | The extractor never states one; its T+2 value is an unvalidated candidate, never a fact |
| `payload.payout_date` | **not fed** | A payout date is NOT an ex-date (#26) |

### Merge rule

An event action **supersedes** a legacy action for the same
distribution: same DPS within the #131 tolerance and the ex-dates
agree (or the legacy one is undated), or the legacy ex-date was
derived (`date_basis == "entitlement+1"`) and sits within one day
of the verbatim ex-date — the verbatim date corrects the
derivation. Anything else survives alongside: two genuinely
different coupons (same DPS, different ex-dates) stay two actions.
A missing or malformed feed file changes nothing — legacy detection
still stands, and a dead feed never loses a sweep.

### Proof (POUL coupon 42, NewsID 296893; sweep date 2026-11-15, base 10.00)

The real extractor on the real #109 golden yields one verified
event (DPS 1.8999999998, ex-date 2026-11-16 verbatim,
entitlement-end 2026-11-15, announced 2026-11-02). The real
ensemble on a minimal sweep dir:

| Run | `corporate_actions` | Horizon marks |
|---|---|---|
| A — legacy only (no events file) | 1 action, `date_basis: entitlement+1`, DPS 1.8999999998, ex 2026-11-16, mechanical −19.0% | day/week/month marked, mechanical −19.0% |
| B — events file present | 1 action (no double-count), `date_basis: verbatim:ex-date`, `source: disclosure-event`, same DPS / ex-date / mechanical % | identical marks and scores to A (net 0.45; expected +0.46% / +0.92% / +1.78%) |
| C — collected body blanked + events file | 1 action, identical to B | identical to B — the adjustment survives where legacy is blind |
| Control — no event, no dividend text | `[]`, horizons unmarked | — |

Reproducible: `scripts/test_ensemble_dividend_adapter_281.py`
(5 tests: mapping, all gates, merge supersede/keep-apart, the
three end-to-end runs above, the no-dividend control).

## Feeding #32 reaction profiles (#282)

`scripts/recommend.py` (`events_to_reaction_triggers` +
`select_reaction_nudge`, wired into `main()`) feeds verified
disclosure events into #32 reaction-profile selection. The consumer
is the daily recommendation glue, not the ensemble: it reads
`profiles/<TICKER>.json` (the reaction fit) and nudges the expected
week move by the fitted type's SHRUNK reaction × 0.5 decay when a
fresh event of a fitted type falls within 5 calendar days before
the ensemble's as-of date. A verified event **selects** the profile
type for the sessions after its announcement — it does not
re-weight anything (the nudge weight is unchanged; #282 is about
selection). The feed file (`disclosure-events/<CODE>-events.json`)
is already staged into the archived sweep dir by merge.py #280, so
`recommend.py` fetches it from the same sweep dir as the ensemble,
at the same pinned commit — no worker/merge change was needed. The
winning verified trigger is recorded on the recommendation JSON as
`reaction_trigger` (null on the legacy path); `compile_model.py`
copies only a whitelist of recommendation keys, so the extra key is
ignored downstream.

### Field mapping (event field → profile input)

| Disclosure-event field | Profile input | Notes |
|---|---|---|
| `event_type == "dividend"` | profile type `dividend` | |
| `event_type == "earnings"` | profile type `earnings` | |
| `event_type == "board_decision"` + `subtype == "egm_call"` / `"agm_call"` | profile type `governance` | The extractor's subtype already distinguishes an assembly call (governance) from the board's own decisions (management) — use it, never a guess |
| `event_type == "board_decision"` + `subtype == "board_decisions"` | profile type `management` | |
| `announced.value` | **session-alignment date** | The sessions after the announcement are the ones scored against the profile; the trigger is fresh when 0–5 calendar days before the ensemble's as-of date (the same window as the legacy path, about 3 trading sessions) |
| `event_id` | provenance | Recorded on the trigger and in the note |
| `issuer.ticker` | ticker guard | Must match the sweep ticker when present; absent is accepted (the feed file is already per-ticker) |
| `verification_status == "verified"` **and** `extraction_status == "extracted"` | gate: both required | Same gates as #281 — a candidate is never a verified event, and an unverified (e.g. republication) extraction is not trusted to move the call |
| any other event type / subtype | **not fed** | The mapping above is exhaustive by design; an event with no profile type never selects |
| event with no parseable announced date | **not fed** | No date, no alignment |

### Selection rule

Verified triggers are considered first, newest first: the first
fresh trigger whose profile type has a fitted shrunk value wins.
If no verified trigger qualifies — unfitted type, stale, future —
the legacy keyword-classified profile events are considered in the
same order (newest first, `"other"` never nudges, INS-R7-01), with
the exact legacy note text reproduced. A verified trigger wins over
a fresher keyword event of another type: provenance beats
recency. A missing or malformed feed file changes nothing — the
legacy path still stands, and a dead feed never loses a
recommendation.

### Proof (POUL, base 10.00, expected week +1.0%)

The real extractor on the real #109 golden yields verified events:
dividend (announced 2026-11-02, ev_bf7532c5c9185f9f113d, DPS
1.8999999998), 9M earnings (announced 2026-11-12,
ev_b89440084409130408c1), EGM call (announced 2026-11-08,
ev_c8f760b067890b8c30f3); the candidate board event is gated out.
The real `recommend.main()` on a stubbed archive (canned newest
ensemble + canned profile/feed fetches), real committed
`profiles/POUL.CA.json` (fitted types: dividend only, shrunk 3.46):

| Run | Feed | `nudge_pct` | Note / trigger |
|---|---|---|---|
| A — legacy only, as-of 2026-11-05 | none | +1.73 | "fresh dividend event (2026-11-02, 3d before the ensemble)…" — the baseline |
| B — verified dividend, as-of 2026-11-05 | real dividend event | +1.73 | "verified dividend disclosure event (2026-11-02, 3d before the ensemble, ev_bf7532c5c9185f9f113d)…" + `reaction_trigger` recorded — same profile, authoritative provenance |
| C — blind body, as-of 2026-11-05 | none, then real dividend event | 0.0 → +1.73 | Profile whose only fresh event is the AGM story keyword-classified "other" (mirroring the real 2026-10-19 AGM story the classifier left as "other"): legacy finds nothing; the verified event selects the profile |
| D — verified earnings, as-of 2026-11-13 | real earnings event | −1.00 | Crafted profile with fitted earnings (shrunk −2.0): the event selects the earnings profile |
| E — precedence, as-of 2026-11-05 | real dividend event | +1.73 | Profile with a fresher keyword earnings event (2026-11-03, fitted): the older verified dividend wins |
| F — verified EGM call, as-of 2026-11-09 | real EGM call + candidate board | +0.75 | Crafted profile with fitted governance (shrunk 1.5): the EGM call selects governance; the candidate board event is ignored |
| G — malformed feed, as-of 2026-11-05 | garbage / non-list events | +1.73 | Legacy path unchanged |
| Control — no event, no feed | none | 0.0 | No regression on event-free sweeps |

Reproducible: `scripts/test_recommend_event_adapter_282.py`
(16 tests: mapping, all gates, selection precedence/freshness/
fallback, the eight end-to-end runs above, the no-event control).
Failing-before on base main: 12 errors + 3 failures (the new
functions and the `reaction_trigger` key do not exist there).

## Attachment capture (#279, capture-only)

The harvest now captures the disclosure PDF itself
(`worker/attachment_capture.py`, wired into `worker/egx_harvest.py`,
archived by `worker/worker.py` `publish()`):

- Per disclosure, the detail page's anchors are scanned for
  attachment links (href ending `.pdf`, or anchor text ending with a
  size suffix like `(64 KB)` — the form real harvested bodies show);
  detail/search pages and `javascript:`/`mailto:` links are never
  followed. Each link is fetched in the same TSPD-trusted browser
  session and stored as `results/attachments/<NewsID>.pdf`
  (`<NewsID>_2.pdf`, … for further attachments, max 5 per item).
- The item carries `"attachments": [pointer, ...]` — one record per
  link, never an empty list: `{"status", "path", "sha256",
  "size_bytes", "source_url", "reason"}` with status `captured` /
  `no_attachment` / `fetch_failed` / `not_pdf` / `too_large` /
  `link_scan_failed`. A capture failure is recorded on the item; it
  never loses the harvested body and never fails the harvest.
- `publish()` copies the PDFs to `harvest/attachments/` next to the
  stable `harvest/<CODE>.json` pointer, so the pointer path
  `attachments/<NewsID>.pdf` resolves inside the archive. The same
  files also ride the wholesale results copy into `worker-runs/`.
- Verification property: `verify_attachment()` re-reads the stored
  file and checks its sha256 against the pointer;
  `fields_present_in_pdf()` checks the extracted field strings are
  present in the stored bytes. Tests
  (`worker/test_attachment_capture_279.py`, 24 checks, deterministic
  fixture PDF) prove this on the real COMI 297291 body: the extracted
  NPAT `63079356` / announced `2026-11-10` trace to `63,079,356` /
  `10/11/2026` in the stored PDF.
- Out of scope for #279 (see #301 below: candidate reporting with
  evidence exists now; promotion into events is still a separate
  stage): PDF-only field extraction (revenue, board details, record
  date from inside PDFs). The link rules were not verified against
  a live EGX detail page (egx.com.eg sits behind TSPD; no live fetch
  from the VM) — they are grounded in the harvested body text only,
  so the first live harvest should be checked for `captured` vs
  `no_attachment` rates before relying on coverage.

## PDF-text verification (#301, INS-299 follow-up)

`scripts/pdf_verify.py` (`verify` subcommand) verifies the fields
`disclosure_events.py` extracted from a harvested body against the
stored source PDF(s), and reports the fields only the PDF carries.
It replaces the byte-substring check above for field verification
(`fields_present_in_pdf()` stays as a capture-level aid only) and
does NOT adopt #299's scripts (`scripts/pdf_text.py` on branch
`279-attachment-capture` was a duplicate of #297 and was not merged).

- Engine: `scripts/pdf_text.py` reads text with pypdf (pinned in
  `requirements.txt`, layout mode — Arabic in logical order). A
  valid PDF with no text layer is `scanned` (OCR needed); a font
  without a ToUnicode mapping makes its Arabic labels
  inconclusive, never "missing"; no pypdf installed is
  `unsupported` (also inconclusive, never a pass or a fail).
- Role-aware: a value verifies only in the window after one of its
  own field labels (e.g. `صافي الربح` for NPAT, `تاريخ تحريك
  الحدود السعرية` for ex-date), cut off at the next label — so a
  swapped ex-date/payout date or current/comparative NPAT fails
  with `wrong_role` even though both values are in the PDF.
  Period start/end verify as one `من..إلى` range.
- Sign-aware numerics: a leading minus or parentheses mean a loss;
  positive 100 never matches (100) or -100. Tolerances are
  field-specific: dividend `amount_per_share` keeps the #131
  coupon rule (max(0.02, 1%)); earnings money needs exact Decimal
  equality; a PDF scale (`بالألف`/`بالمليون`) disagreeing with the
  event's scale is `scale_mismatch`.
- Contract: consumes the merged plural `attachments` pointers
  (never the singular `attachment` #299 expected). Each captured
  file is resolved strictly inside the archive root and hash-checked
  with `verify_attachment()` before it is read. Per-field evidence
  is page + verbatim quote + label + the pointer sha256.
- PDF-only fields — the rule: a field in the event type's table
  whose payload value is null, carried by the PDF with role
  evidence, is reported under `pdf_only_fields` as a candidate
  with evidence. It is never written into the event and never
  changes its status; promoting it is a separate stage.
- Statuses: `verified` / `partial` (some verified, rest merely
  absent) / `mismatch` (any field the PDF contradicts, even when
  others verify) / `missing` / `inconclusive` / `skipped`.
  The verifier never mutates an event and never upgrades
  `verification_status`. CLI exit codes: 0 = ≥1 verified, none
  failed; 1 = any partial/mismatch/missing/inconclusive; 2 = zero
  events, or zero events actually checked (all skipped) — zero exit
  is not successful coverage. Tests: `scripts/test_pdf_verify_301.py`
  (40 checks: role/swap negatives, sign/scale, plural attachments,
  hash/path cases, scanned/unmapped/unsupported, CLI exit codes).

## Live wiring (#278, option A sweep-live)

The feed is live worker-side (`worker/worker.py`, two phases around
the sweep's tool loop in `_execute_body`):

- **Phase 1 — pre-sweep refresh.** Before any tool runs,
  `refresh_disclosure_feed` force-refreshes the official EGX harvest
  for every in-scope ticker in the plan (POUL/COMI, v1) via
  `refresh_harvest`, so the news-disclosure tool's `ensure_harvest`
  serves the just-refreshed cache. Runs for scheduled (`sched-*`)
  and on-demand sweeps alike.
- **Phase 2 — extraction before the ensemble.** After the tool loop
  and before `maybe_merge`, `extract_disclosure_events` runs
  `scripts/disclosure_events.py extract` over each refreshed harvest
  (quarter window: 90 days ending on the sweep date) and writes
  `disclosure-events/<CODE>-events.json` into the run dir. Ordering
  and provenance are tied to one sweep id: the run manifest's
  `disclosure_feed` section and the run dir's `disclosure_feed.json`
  record sweep id, origin (`scheduled` / `on-demand`), mode
  (`sweep-live`), harvest timestamp, quarter window and per-ticker
  event counts. Both files ride the archive via `publish`.
- **"Live" means sweep-live only.** A disclosure published after
  market close is picked up by the next sweep's refresh, not pushed
  intraday. No intraday alerting is promised or built in v1
  (`intraday_alerting: false` in the feed record).

### Freshness / failure policy (defined, not silent)

- `refreshed` — harvest ran inside this sweep; extraction runs.
- `cached` — refresh failed but the on-box cache is still within 12 h
  (`DISCLOSURE_FRESH_HOURS`, same bound as `HARVEST_TTL_HOURS`);
  extraction runs, flagged cached with its age recorded.
- `failed` — refresh failed and there is no usable cache (absent or
  older than 12 h); extraction is **skipped** for that ticker — the
  sweep never extracts from stale input. Recorded in
  `manifest["disclosure_feed"]` and in `disclosure_feed_error.txt`
  in the run dir; the sweep itself still runs (fleet + ensemble are
  unaffected in v1 — nothing consumes events yet; #280/#281 own
  consumption), so a dead feed never loses a sweep.
- `extraction-failed` / `stale-input` — the extractor errored, its
  output failed validation (schema version, events list, document
  count vs the harvest), or the harvest changed / aged past the bound
  between the phases; no events file is kept for that ticker, the
  failure is recorded the same way, the sweep still runs.
- The extraction gate re-verifies the harvest phase 1 recorded (same
  `harvested_at`, still within the bound). A later refresh by the news
  tool's own `ensure_harvest` does **not** rescue a failed phase 1 —
  the feed consumes only what the pre-sweep refresh produced or
  validated; the next sweep re-extracts the full 90-day window, so
  skipping loses no disclosure. Note the bounds differ by design:
  the news tool still serves a cache up to 72 h (its matching is
  content-based); the disclosure feed refuses anything past 12 h.

### Deterministic replay proof

`worker/test_worker_278.py` (26 checks, stdlib only, no network)
replays the path on fixtures built from the #109 goldens: the POUL
coupon-42 document re-dated to a 19/11/2026 after-close publication
appears in the next sweep's events with announced `2026-11-19`
(standalone-date-line basis), and the COMI 297291 earnings document
(item date wrongly `2026-01-01`) extracts with announced
`2026-11-10`. The scheduled and the on-demand sweeps both prove the
`refresh → extract → merge → compile → render` order in the real
`_execute_body`. The same file fails on pristine main (the wiring
does not exist there).

## Surfacing in the Report Model — v2 (#280)

The events feed is surfaced in the Report Model under **strict D-7**:
`model_version=2`, schema `borsagator-report-model/2`. The contract
lives in one place — `scripts/report_model.py` (the single pinned
authority the compiler, the validator, the renderer and the delta
adapter all import) — and is frozen by the fixtures in
`scripts/report_model_fixtures/` and the tests in
`scripts/test_report_model_v2_280.py`.

- **Pipeline:** `merge.py` stages the feed file
  (`disclosure-events/<CODE>-events.json`, written by the worker's
  phase 2 into the run dir) into the staged sweep dir, next to the
  benchmark entrants. The compiler reads it from the sweep dir only;
  the worker's `maybe_compile` re-validates the emitted model with
  `--check-model` and `maybe_render` renders it — both from the same
  checkout, so producer and readers are pinned together by code SHA.
  A rollback stays compatible: v1 readers refuse v2 models (exit 2 /
  `model_schema_unsupported`) and v2 readers still accept frozen v1
  models. Nothing ever relabels v2 content as v1.
- **The block** (`disclosure_events`, one new top-level field):
  `status` (`valid` | `missing` | `unavailable` | `stale`), `source`
  (sweep-dir-relative feed path), the feed's own provenance
  (`feed_schema_version`, `extractor_version`, `config_hash`,
  `quarter`, `feed_report`), `events` (records verbatim from the
  feed — amounts are decimal strings, never floats; every field
  carries evidence pointers: `source_url`,
  `document_revision_id` (`clipped-body-sha256:…`), per-field
  spans), `counts` (derived from `events`), `reason` (null on
  valid). States are distinct and never conflated:
  - `missing` — no feed file for the ticker (Actions sweeps,
    pre-#278 runs). Normal state, no flag.
  - `unavailable` — a file exists but failed validation. Flagged;
    never partially surfaced.
  - `stale` — feed valid but its quarter window ends before the
    sweep date. Flagged; events still carried.
  - `valid` — feed read and validated. Zero events is a valid-empty
    state (recorded absence, not a gap).
  A v1 model carries no block: events were **not recorded** by that
  contract — the renderer says so, and the delta reports it as
  "not recorded", never as an empty events set and never as
  added/removed churn against a v2 model.
- **Version policy (one policy, everywhere):** exact tuples only —
  (1, `/1`) and (2, `/2`); mixed markers and unknown future versions
  are refused identically by `--check-model`, the renderer and the
  delta adapter. The no-bump schema-diff check refuses a model that
  carries a field its declared version does not define, even when
  its markers agree (a contract-field change without the required
  bump). The Sharia additive-v1 note is a **historical v1 exception
  only** — v1 models with or without `sharia` are both legal; it
  must never be copied into another silent v1 addition.
- **Determinism:** the v2 output is byte-identical across compiles
  of the same sweep dir (sorted keys, fixed float formatting, no
  wall-clock timestamps — the compiler's existing guarantees), and
  the legacy financial / Sharia / common-field behaviour is
  unchanged: a v2 compile of a sweep without a feed file differs
  from its v1 compile only in the two version markers and the new
  block.
- **Negative controls:** a mismatch (mixed markers, unknown
  version, malformed events) is refused by every consumer and, on
  the compile path, the #161 quarantine moves a previous model
  aside before any recompile is attempted — a refused recompile
  never leaves stale output looking current.
