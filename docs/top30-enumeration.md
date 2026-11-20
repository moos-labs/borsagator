# Top-30 EGX enumeration — fixed-window enumeration + expected-document ledger (#283, stage 2)

Stage-2 implementation of the INS-283-ENUM-DESIGN five gates (issue
#283, comment 7019892536): enumeration → expected-document ledger;
corpus → immutable source evidence. Gold, scorer verdicts and the
per-cell report follow on the ledger + corpus and are NOT in this
step.

- Enumerator: `scripts/top30_enumerate.py` (stdlib only).
- Tests: `scripts/test_top30_enumerate_283.py` (18 controls, wired
  into `scripts/harness_issue109.py` `--scorer`).
- Ledger: `evaluation/top30_expected_docs.json` (schema v1).
- Fixture pilot: `scripts/top30_enumerate_fixtures/` (SIMULATED
  NewsSearch pages — never live EGX captures).

## 1. Fixed window and universe

- Window: **2026-08-19 → 2026-11-19, both endpoints inclusive**
  (the frozen quarter in `evaluation/top30_manifest.json`).
- Universe: the 30 issuers / 31 listings of the frozen manifest.
  POUL/COMI are regression controls outside the 30 and are
  enumerated the same way in pilot runs.
- Query: EGX NewsSearch per listing, ISIN-keyed, exactly the shape
  the harvester already uses (`worker/egx_harvest.py:206-208`):
  `/ar/NewsSearch.aspx?com=&word=&from=dd/mm/yyyy&to=dd/mm/yyyy&isin=<ISIN>&sec_id=20`.
- FAIT/FAITA is one issuer: its two listings union source records
  and duplicate source ids are deduplicated before scoring
  (manifest `cell_definition`); FAITA on its own is BLOCKED by B-02
  (no verified ISIN) and must never default to the FAIT ISIN.

## 2. Filter-semantics validation — NOT YET VALIDATED LIVE

Step 1 of stage 2 is to validate what the NewsSearch `from`/`to`
filter actually does, on a pilot issuer, before trusting any
capture. That validation has NOT been performed live, because live
EGX access fails from this VM (see §3). The protocol for the run
that can reach EGX (the worker, with its TSPD-trusted browser
profile) is:

1. **Inclusivity probe.** Query a 1-day window known from the pilot
   to contain a POUL disclosure (e.g. the 02/11/2026 dividend
   announcement, NewsID 296001 in fixtures) and the adjacent 1-day
   windows on each side; record whether the boundary dates are
   included or excluded.
2. **ISIN vs company-name agreement.** Run the same window once
   ISIN-keyed and once via the company dropdown (Arabic name); the
   two result sets must agree, or the disagreement is a named
   failure with both counts.
3. **Pagination control shape.** Record the actual next-page control
   on a multi-page result (ASP.NET `__doPostBack` form vs `page`
   parameter) and the exact "no results" marker text; the
   enumerator's terminal-state logic must be re-checked against
   the real control before a live run is called complete.
4. **Source total.** Record whether the result page reports a total
   result count and its exact label; when present it is the
   reconciliation denominator, when absent the terminal state is
   the evidence (last page with no next control + a following page
   adding no new ids).

Until that protocol runs live, every enumeration claim in the ledger
is probe-mode (not run) or fixture-mode (simulated).

## 3. Live-access probes from this VM (2026-11-19, all failed)

| Probe | Time (UTC) | Target | Result |
|---|---|---|---|
| curl | 2026-11-19 22:21:49 | `https://www.egx.com.eg/ar/` | http=000, 0 bytes, ~1.95 s |
| curl | 2026-11-19 22:21:49 | NewsSearch POUL pilot URL (from 19/08/2026, to 19/11/2026, isin EGS02051C018) | http=000, 0 bytes, ~1.61 s |
| curl -v | 2026-11-19 22:22:05 | `https://www.egx.com.eg/ar/` | TLS handshake completes, then "Empty reply from server" |
| urllib | 2026-11-19 22:22:05 | NewsSearch POUL pilot URL | `RemoteDisconnected: Remote end closed connection without response` |
| browser fetch | 2026-11-19 ~22:22 | NewsSearch POUL pilot URL | network error (DNS, timeout, or connection refused) |

This matches the known sandbox egress behaviour (direct TCP payload
blackholed; only the HTTP proxy for named hosts) plus EGX's F5 TSPD
defence, which drops non-trusted sessions. No live document was
retrieved, and none is claimed. The ledger therefore records every
issuer as `not_run` with the named failure
`egx_unreachable_from_vm` and the probe evidence above; the
enumerator's own probe (one POUL pilot request per run) is recorded
in the ledger's `live_access` field.

## 4. Terminal states and reconciliation

Per listing, pagination runs until one evidenced terminal state:

| Terminal state | Meaning |
|---|---|
| `empty` | First page evidences zero results (explicit empty marker, no next control). A genuine zero-activity result needs this evidence — never zero by default. |
| `exhausted` | Last page fetched: no next-page control and no further items. |
| `count_reconciled` | Collected unique NewsIDs equal the source-reported total. |
| `duplicate_page` | A page added no new ids (pagination looping or exhausted). |
| `failed` | Fetch failure, challenge shell, changing source total, or no terminal state within `MAX_PAGES` (200). A named failure, never a silent truncation. |

Reconciliation: when the source reports a total, collected unique
ids must equal it; a mismatch is a `count_mismatch` named failure
and the listing's status becomes `failed`. A changing total across
pages is the same failure. Duplicate NewsIDs across an issuer's
listings (FAIT/FAITA union) are deduplicated by source id.

## 5. Ledger schema (v1)

`evaluation/top30_expected_docs.json`:

- `manifest` (path, base_commit, frozen quarter), `window`,
  `enumerator` + version, `run_id`, `generated_at`, `mode`
  (`probe` | `live` | `fixtures`).
- `live_access`: `{reachable, probes: [{url, at, reachable, detail}]}`.
- `collection`: `{enumerated, archived, missing,
  enumeration_closed, pagination_complete}` — the same keys
  `scripts/top30_completion.py` validates (`_validate_collection`):
  a ratio of archived/enumerated = 100% is insufficient unless
  enumeration is closed and evidenced complete.
- `collection.missing` (issue #352, settled): a list of frozen
  ROUTE codes for routes that could not be enumerated — never
  document IDs, and never manufactured. The producer emits
  `missing=[]` and evidences blocked/failed routes in the
  listing/failure records (e.g. FAITA's B-02 named failure), so
  no later consumer may read `missing` as an exhaustive ledger
  of unarchived documents.
- `issuers[]`: per issuer `{issuer, listings[], enumeration_status,
  terminal_states, source_total, collected_count, documents[],
  failures[]}`.
- Per listing: `{code, issuer, isin, enumeration_status
  (enumerated | blocked | failed | not_run), terminal_state,
  source_total, pages_fetched, collected_ids, documents[],
  failures[]}`.
- Per document: `{source_document_id ("egx:<NewsID>"), url, title,
  announced_date, announced_date_source, listing, isin,
  first_seen_page, corpus: {status (not_captured | archived |
  partial | failed), body_sha256, body_hash_kind (full |
  clipped-body-sha256), body_chars, attachments[]}}`.
- `failures[]`: every named failure, with `kind`, `reason` and
  `evidence` (URL + timestamp). Missing records are named failures,
  not exclusions.

## 6. Corpus capture

`capture_document(fetcher, doc)` fetches the detail page and hashes
the FULL body (`body_hash_kind: "full"`). A clipped body is hashed
only as `clipped-body-sha256` with corpus status `partial` — a
clipped-body hash is NEVER presented as a full-document hash
(manifest rule). Attachment links follow the
`worker/attachment_capture.py` classification (`.pdf` href, or a
size-suffix anchor like "(64 KB)" that is not a detail/search page);
attachment fetch failures are recorded on the document and never
lose the body. Corpus capture runs only after enumeration closes;
in this step the corpus status of every ledger document is
`not_captured` (nothing was enumerated live).

## 7. Modes

- `probe` (default): one POUL pilot probe, then a ledger recording
  every issuer as `not_run` with the shared probe evidence. No
  doomed per-issuer requests, no invented documents.
- `live`: full enumeration. `--transport profile` (issue #346 F2)
  fetches through the TSPD-trusted browser session — the same
  persistent Chromium profile the harvester uses
  (`worker/egx-profile`, `ProfileFetcher` in
  `scripts/top30_enumerate.py`); plain HTTP (`--transport http`,
  the default) is for machines without the profile. Wiring proven
  by fixture/stub tests only — NOT yet verified live: no
  profile-backed enumeration against EGX has been observed, the
  §2 validation protocol has not run, and pagination still uses
  the URL form (`&page=N`) rather than driving the `__doPostBack`
  form. The first live sweep is the proof that remains.
- `fixtures`: enumeration against a directory of JSON files mapping
  URL → `{status, body}`. Used by the tests and the pilot ledger;
  pages are SIMULATED and labelled as such in the ledger.

## 8. Blockers carried (recorded, not routed around)

- **B-01 / B-03** — Arabic names outstanding (5 + 23 listings).
  ISIN-keyed enumeration proceeds; Arabic-name matching cannot rely
  on these rows until verified.
- **B-02** — FAITA ISIN missing. Holds the FAIT issuer verdict
  only; the FAITA listing is `blocked`, never enumerated under the
  FAIT ISIN.
- **B-05** — roster weights unverified (Ins-reported). Proceeds
  against the frozen universe with the provenance caveat; weights
  are not needed for the evaluation.

## 9. What is left (not this step)

- Live filter-semantics validation (§2 protocol) on the worker.
- The live enumeration run + corpus capture (full bodies +
  attachments with hashes) once EGX is reachable.
- Gold adjudication, scorer run, per-cell report (follow on the
  ledger + corpus, per the five gates).
