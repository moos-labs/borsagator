# 🐊 Borsagator — forward quality benchmark (issue #79)

Source: `moos-labs/borsagator` branch `archive` (tree 12c8085e, commit 12c8085e). Sweeps archived: 62 (18 with a benchmark freeze).

**Benchmark rows: 321 · matured: 78 · pending: 207 · invalid: 36 · excluded gap-flagged: 0**

Quality gate: no quality claim for any (entrant, horizon) cell with fewer than 10 matured forecasts — such cells show their count and the gate wording only. Public accuracy claims need n ≥ 30 matured forecasts (D4).

## day (matured only)

| Entrant | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| ensemble | 21 | 0.0 | 11.29 | 0.476 |
| buy-and-hold | n=7 — below the n≥10 gate, no claim | — | — | — |
| family-agent | n=0 — below the n≥10 gate, no claim | — | — | — |
| family-fundamentals | n=7 — below the n≥10 gate, no claim | — | — | — |
| family-price-forecast | n=7 — below the n≥10 gate, no claim | — | — | — |
| family-sentiment | n=7 — below the n≥10 gate, no claim | — | — | — |
| family-technicals | n=7 — below the n≥10 gate, no claim | — | — | — |
| kronos-alone | n=7 — below the n≥10 gate, no claim | — | — | — |
| raw-llm-cohere | n=0 — below the n≥10 gate, no claim | — | — | — |

## week (matured only)

| Entrant | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| ensemble | 15 | 0.0 | 18.28 | 1.0 |
| buy-and-hold | n=6 — below the n≥10 gate, no claim | — | — | — |
| family-agent | n=0 — below the n≥10 gate, no claim | — | — | — |
| family-fundamentals | n=6 — below the n≥10 gate, no claim | — | — | — |
| family-price-forecast | n=6 — below the n≥10 gate, no claim | — | — | — |
| family-sentiment | n=6 — below the n≥10 gate, no claim | — | — | — |
| family-technicals | n=6 — below the n≥10 gate, no claim | — | — | — |
| kronos-alone | n=6 — below the n≥10 gate, no claim | — | — | — |
| raw-llm-cohere | n=0 — below the n≥10 gate, no claim | — | — | — |

## month (matured only)

| Entrant | n | Direction hit rate | Mean |error| (pp) | Range coverage |
|---|---|---|---|---|
| ensemble | n=0 — below the n≥10 gate, no claim | — | — | — |
| buy-and-hold | n=0 — below the n≥10 gate, no claim | — | — | — |
| family-agent | n=0 — below the n≥10 gate, no claim | — | — | — |
| family-fundamentals | n=0 — below the n≥10 gate, no claim | — | — | — |
| family-price-forecast | n=0 — below the n≥10 gate, no claim | — | — | — |
| family-sentiment | n=0 — below the n≥10 gate, no claim | — | — | — |
| family-technicals | n=0 — below the n≥10 gate, no claim | — | — | — |
| kronos-alone | n=0 — below the n≥10 gate, no claim | — | — | — |
| raw-llm-cohere | n=0 — below the n≥10 gate, no claim | — | — | — |

## Benchmark gaps & notes

- sweeps/2026-11-18/123709__sweep-lite-poul-ca-market-egx__runsched-2026-11-18: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-18/123709__sweep-lite-poul-ca-market-egx__runsched-2026-11-18: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-18/140522__sweep-poul-ca-market-egx__runmanual-sweep-2026-11-18-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-18/140522__sweep-poul-ca-market-egx__runmanual-sweep-2026-11-18-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-18/202544__sweep-lite-poul-ca-market-egx__runmanual-sweep-lite-2026-11-18-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-18/202544__sweep-lite-poul-ca-market-egx__runmanual-sweep-lite-2026-11-18-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-18/222037__sweep-lite-poul-ca-market-egx__runmanual-sweep-lite-2026-11-19-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-18/222037__sweep-lite-poul-ca-market-egx__runmanual-sweep-lite-2026-11-19-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-19/062255__sweep-lite-poul-ca-market-egx__runsched-2026-11-19: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-19/062255__sweep-lite-poul-ca-market-egx__runsched-2026-11-19: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-19/075206__sweep-lite-poul-ca-market-egx__runmanual-sweep-lite-2026-11-19-002: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-19/075206__sweep-lite-poul-ca-market-egx__runmanual-sweep-lite-2026-11-19-002: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-23/062543__sweep-lite-poul-ca-market-egx__runsched-2026-11-23: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-23/062543__sweep-lite-poul-ca-market-egx__runsched-2026-11-23: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/063413__sweep-lite-poul-ca-market-egx__runsched-2026-11-25: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/063413__sweep-lite-poul-ca-market-egx__runsched-2026-11-25: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/110009__sweep-lite-acgc-ca-market-egx__runw5-sweeplite-acgc-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/110009__sweep-lite-acgc-ca-market-egx__runw5-sweeplite-acgc-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/111021__sweep-lite-adib-ca-market-egx__runw5-sweeplite-adib-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/111021__sweep-lite-adib-ca-market-egx__runw5-sweeplite-adib-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/112115__sweep-lite-amoc-ca-market-egx__runw5-sweeplite-amoc-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/112115__sweep-lite-amoc-ca-market-egx__runw5-sweeplite-amoc-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/112926__sweep-lite-arcc-ca-market-egx__runw5-sweeplite-arcc-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/112926__sweep-lite-arcc-ca-market-egx__runw5-sweeplite-arcc-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/113637__sweep-lite-atqa-ca-market-egx__runw5-sweeplite-atqa-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/113637__sweep-lite-atqa-ca-market-egx__runw5-sweeplite-atqa-001: family-sentiment absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/113637__sweep-lite-atqa-ca-market-egx__runw5-sweeplite-atqa-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/114458__sweep-lite-cira-ca-market-egx__runw5-sweeplite-cira-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/114458__sweep-lite-cira-ca-market-egx__runw5-sweeplite-cira-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/115426__sweep-lite-clho-ca-market-egx__runw5-sweeplite-clho-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/115426__sweep-lite-clho-ca-market-egx__runw5-sweeplite-clho-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/120234__sweep-lite-efid-ca-market-egx__runw5-sweeplite-efid-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/120234__sweep-lite-efid-ca-market-egx__runw5-sweeplite-efid-001: raw-llm-cohere absent (llm-key-absent) — no rows
- 36 benchmark row(s) invalidated (validation mismatch or the issue-#87 guard) — never scored: buy-and-hold POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; buy-and-hold POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; buy-and-hold POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-fundamentals POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-fundamentals POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-fundamentals POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-price-forecast POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-price-forecast POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-price-forecast POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-sentiment POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-sentiment POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-sentiment POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-technicals POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-technicals POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-technicals POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; kronos-alone POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; kronos-alone POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; kronos-alone POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; buy-and-hold POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; buy-and-hold POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; buy-and-hold POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-fundamentals POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-fundamentals POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-fundamentals POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-price-forecast POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-price-forecast POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-price-forecast POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-sentiment POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-sentiment POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-sentiment POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-technicals POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-technicals POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-technicals POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; kronos-alone POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; kronos-alone POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; kronos-alone POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24

_The ensemble is the reference row: the table is symmetric and fixed-order, and every cell is published as scored._
