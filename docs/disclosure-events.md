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

## Attachment capture (#279, capture-only)

At harvest time the harvester follows each disclosure's attachment
link where the source offers one and stores the PDF under the
archive, with a stable pointer from the event:

- **Discovery** (`worker/egx_harvest.py` + `worker/attachment_capture.py`):
  every anchor on the detail page is collected; links whose href
  carries `.pdf` (before any query string / fragment / parameter)
  are downloaded through the same trusted Playwright session that
  loaded the page, so TSPD trust carries over. At most 3 PDFs per
  disclosure; each must be ≤ 25 MiB and start with the `%PDF`
  magic, or it is refused.
- **Storage:** `attachments/<NewsID>/<file>.pdf`, relative to the
  directory holding `disclosures.json` — so the same pointer
  resolves in the run dir (which rides the archive wholesale via
  `publish`), in the on-box cache (`ROOT/harvest/attachments/`,
  mirrored by `worker._sync_harvest_attachments` whenever a fresh
  harvest is cached) and in any copy of the harvest. The archive
  root's `harvest/<CODE>.json` pointer stays JSON-only, as before.
- **Pointer:** each harvested item carries `attachment`
  (`status`, `files[]` with `url` / `path` / `sha256` / `bytes` /
  `content_type`, `failures[]`, `reason`, `captured_at`), and each
  extracted event carries the same record verbatim. Statuses:
  `captured` | `no_attachment` (nothing offered) |
  `fetch_failed` (offered but not stored — reason named) |
  `not_recorded` (item harvested before #279). A capture failure
  never fails the harvest. The pointer is attached to events after
  `_finish`, so `event_revision_id` is unchanged, and the v2
  report-model validator accepts the additive top-level key (no
  closed key set at event level; only the payload has one).
- **Verification** (`scripts/disclosure_events.py verify <events.json>
  --attachments-dir <harvest-dir>`, `scripts/pdf_text.py`):
  re-reads each event's stored PDF and checks the already-extracted
  fields reproduce from it (coupon / amount within the #131
  tolerance / dates in ISO or dd/mm/yyyy form / NPAT figures).
  Per-event status: `reproduced` | `partial` | `missing` |
  `skipped` (no stored PDF / no checkable token) | `unreadable`
  (file absent or no extractable text). Exit 1 when any captured
  event fails to reproduce. This is a verification property of the
  capture — it extracts no new PDF-only fields.
- **Explicitly out of #279** (recorded scope decision): extracting
  PDF-only fields (revenue, board details, record date from inside
  PDFs) — a separate follow-up if wanted.

## What this change does NOT do (follow-ups, not in this PR)

- No consumer switch, no `#26` feeding: the feed is recorded per
  sweep but nothing in the ensemble or the report consumes events
  yet — that is #281 / #280. The worker wiring itself landed in
  #278 (see "Live wiring" below); it changes no `#68` model field.
- No `#68` surfacing (that needs a strict D-7 version bump).
- No harvester fix for the `iso_date` bug (fixed separately, #274).
  Attachment capture is #279 (see above).
- No top-30 coverage until more tickers are harvested.
- `#109` is CLOSED (2026-11-19, on the live-feed decision alone —
  option A sweep-live); its follow-ups are #278 (this wiring),
  #279 (attachments), #280 (#68 surfacing), #281 (#26 feeding),
  #282 (#32 adapter) and #283 (top-30 coverage).

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
