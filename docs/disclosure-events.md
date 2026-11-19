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

- No live-feed decision, no consumer switch, no `#26` feeding.
  Extraction-before-ensemble for same-cycle effect needs worker-side
  ordering — repo side only here; worker wiring is an explicit
  follow-up, no promotion was run.
- No `#68` surfacing (that needs a strict D-7 version bump).
- No harvester fix for the `iso_date` bug; no attachment capture.
- No top-30 coverage until more tickers are harvested.
- `#109` stays OPEN: close needs the pilot accuracy numbers reviewed
  and the live-feed decision taken.
