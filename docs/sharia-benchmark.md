# Sharia accuracy benchmark (issue #172)

Borsagator's Sharia engine screens a ticker's **own published
financials** under a named standard. This benchmark measures how the
engine's verdicts compare with the published classifications of the
sources that use each standard — it never copies their verdicts into
the engine.

> **Framing (binding).** Every output of this benchmark is a
> per-standard **screening result** — "screened under standard X" —
> never a fatwa and never religious or investment advice.
>
> نتيجة فحص وفق المعيار المذكور فقط، محسوبة من القوائم المالية المنشورة
> للشركة. ليست فتوى، وليست نصيحة دينية أو استثمارية.
>
> **No user-facing accuracy claim ships off the back of this
> benchmark** (issue #77 framing; the same no-accuracy-marketing rule
> that governs issue #79's line).

## Pieces

| Piece | Path |
|---|---|
| Benchmark runner (freeze + score) | `scripts/sharia_benchmark.py` |
| Tests | `scripts/test_sharia_benchmark.py` |
| Frozen source snapshots | `sharia/benchmark/sources/*.json` |
| Raw fetched artifacts (parser inputs) | `sharia/benchmark/raw/` |
| Benchmark reports | `sharia/benchmark/benchmark-<date>.json` / `.md` |

## Comparisons

| Source | Their standard | Our configuration |
|---|---|---|
| Musaffa | AAOIFI, 36-month average market value | AAOIFI, `denominator_variant=avg36m` |
| Faisal Securities | AAOIFI, spot market cap | AAOIFI, `denominator_variant=spot` |
| Ostool Securities | EGX33 (adopted verbatim) | EGX33 |
| EGX33 index membership | EGX33 (ground truth) | EGX33 |

Purification: our AAOIFI purification ratio vs the per-stock figures
the sources publish — Ostool's prohibited-income % column (the
non-compliant revenue share that AAOIFI-style purification applies),
with Musaffa and Nour Borsa as witnesses where their figures are
publicly reachable.

## Freeze discipline

Same discipline as issue #79. `freeze` snapshots each source's
published classification once, with the **source URL and retrieval
date on every row**; `score` runs against the frozen snapshots,
never against a moving page. Re-freeze deliberately when a source
republishes; re-score whenever a rule set or an input pipeline
changes:

```bash
python3 scripts/sharia_benchmark.py freeze            # network step
python3 scripts/sharia_benchmark.py score             # offline
python3 scripts/test_sharia_benchmark.py
```

The engine itself stays offline; only the freeze step touches the
network, and only public pages/PDFs. The Ostool PDF is converted
with the system `pdftotext -layout` (poppler); its column mapping
was pinned against the PDF header by word x-positions
(`pdftotext -bbox`): in layout order a row reads verdict,
prohibited-income %, liquid-assets %, interest-loans %,
interest-deposits %, total assets, average market value. The PDF
binary is not committed; its sha256 and byte size are recorded in
the snapshot, and the extracted layout text is the frozen artifact.

## Honesty rules

- A source whose current list cannot be fetched from a public
  page/PDF is recorded `status: "unavailable"` with **what was
  tried** — never fabricated, never scraped behind a login, and the
  aggregator's blended verdict is never used as a single source's
  verdict.
- Our `insufficient-data` verdicts are counted in their **own
  bucket** — never as agreement, never as disagreement.
- Agreement % is **null** when there are no determinate pairs; a
  percentage over zero pairs would be a fabricated accuracy figure.
- A disagreement's likely driver is labelled a **hypothesis** unless
  read directly off the published inputs, and the disagreement table
  marks rows `unexplained` rather than inventing a cause.
- EGX33 non-membership derived from a complete frozen constituent
  list is labelled **derived** on the row.

## First run (2026-11-18) — what it measured

Covered universe: **POUL.CA only**, and its fleet inputs carry just
shares outstanding plus the Nov 2026 dividend event — no balance
sheet yet (that wiring is issues #78/#110). Every source checked
classifies POUL as non-compliant (Musaffa: NOT HALAL, Nov 2026;
Ostool: غير متوافق, 2026-08-04; EGX33: not a constituent), and our
engine returns `insufficient-data` under all three configurations,
naming the missing inputs. So the first benchmark's measured result
is: **0 determinate pairs, agreement null, 0 purification pairs** —
with Ostool's published POUL percentages (interest-bearing deposits
40.0% vs the 33% limit; prohibited income 5.5% vs the 5% limit)
recorded as a labelled hypothesis for what our EGX33 screen should
find once the inputs land, and Ostool's 5.5% recorded as the
purification figure awaiting our ratio.

Faisal's report PDF could not be retrieved with the tooling
available to the first freeze (its snapshot records exactly what
was tried; the parser is implemented and unit-tested, ready for
the next freeze). Nour Borsa's per-stock data sits behind its
login, so it is recorded as an unavailable purification witness.
