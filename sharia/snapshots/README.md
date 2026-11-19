# Sharia snapshots (issue #172 / #326, rebuilt under #330)

Company financial snapshots consumed by the Sharia engine
(`scripts/sharia_engine.py`): one JSON per ticker per statement
period, plus a provenance file recording where every field came from.

## The #330 extraction rule

`non_compliant_revenue` is the sum of every interest-type income line
in the statements, classified per line — implemented in
`scripts/sharia_snapshot.py` (rule v1.0.0), tested in
`scripts/test_sharia_snapshot.py`:

1. Inside the finance-income line/note: the interest components only
   (the pre-#330 treatment, unchanged).
2. Outside finance income: every interest-type line — income from
   financial investments at amortised cost in other income, and
   amortisation/unwinding of discount on notes receivable in other
   revenues — plus any similar line, each with its basis recorded.

Not interest-type, excluded with the reason recorded: fair-value
gains (FVPL / FVOCI), gains on sale of investments, and the
present-value discount line inside a finance-income note. See the
rule module's open note on the TMGH vs PHDC discount lines (same
economics, different presentation, treated differently by the rule
because of where they are presented).

## Files

| File | What it is |
|---|---|
| `tmgh-h1-2026-snapshot.json` | TMGH.CA H1-2026 snapshot, rebuilt under #330 |
| `tmgh-h1-2026-interest-income-lines.json` | The harvested statement lines the rebuild sums |
| `tmgh-h1-2026-provenance.md` | Source document + per-line classification table |
| `phdc-h1-2026-snapshot.json` | PHDC.CA H1-2026 snapshot, rebuilt under #330 |
| `phdc-h1-2026-interest-income-lines.json` | The harvested statement lines the rebuild sums |
| `phdc-h1-2026-provenance.md` | Source document + per-line classification table |

## Rebuilt figures (evidence: #326 run 1)

| Ticker | As harvested | Rebuilt (#330) | Income ratio as harvested → rebuilt |
|---|---|---|---|
| TMGH.CA | 958,318,757 | 3,051,097,835 | 3.17% → **10.11%** |
| PHDC.CA | 455,606,067 | 978,800,027 | 2.33% → **5.01%** |

Each snapshot keeps the as-harvested numerator as
`financials.non_compliant_revenue_as_harvested` and the per-line
classification as `non_compliant_revenue_breakdown`, so #326 run 2
can re-measure both bases from one file. All other fields are
identical to the #326 originals.

## Rebuild

```bash
python3 scripts/sharia_snapshot.py rebuild \
  --snapshot sharia/snapshots/tmgh-h1-2026-snapshot.json \
  --lines sharia/snapshots/tmgh-h1-2026-interest-income-lines.json \
  --out /tmp/tmgh-rebuilt.json
python3 scripts/test_sharia_snapshot.py
```
