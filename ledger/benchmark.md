# 🐊 Borsagator — forward quality benchmark (issue #79)

Source: `moos-labs/borsagator` branch `archive` (tree 7e4d71c9, commit 7e4d71c9). Sweeps archived: 91 (47 with a benchmark freeze).

**Benchmark rows: 819 · matured: 78 · pending: 705 · invalid: 36 · excluded gap-flagged: 0**

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

## Band calibration (issue #593)

Per-cell fit of the calibration layer (trailing 30 clean matured rows per cell; centre correction b = median realised - expected, width factor k = 85th percentile of |residual - b| / half, shrunk toward the horizon pool). A cell ships uncalibrated until it or its pool reaches n >= 10.

| Ticker | Horizon | n | n_eff | Coverage (as published) | Coverage (calibrated, in-window) | k | b (pp) | Basis |
|---|---|---|---|---|---|---|---|---|
| NVDA | day | 1 | 1 | 1.000 | 1.000 | 1.080 | -8.47 | pool |
| POUL.CA | day | 20 | 20 | 0.450 | 0.850 | 1.088 | -8.51 | cell |
| POUL.CA | week | 15 | 3 | 1.000 | 0.800 | 2.000 | -22.03 | cell |

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
- sweeps/2026-11-25/121054__sweep-lite-efih-ca-market-egx__runw5-sweeplite-efih-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/121054__sweep-lite-efih-ca-market-egx__runw5-sweeplite-efih-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/121852__sweep-lite-egal-ca-market-egx__runw5-sweeplite-egal-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/121852__sweep-lite-egal-ca-market-egx__runw5-sweeplite-egal-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/122721__sweep-lite-egas-ca-market-egx__runw5-sweeplite-egas-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/122721__sweep-lite-egas-ca-market-egx__runw5-sweeplite-egas-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/124034__sweep-lite-etel-ca-market-egx__runw5-sweeplite-etel-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/124034__sweep-lite-etel-ca-market-egx__runw5-sweeplite-etel-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/124806__sweep-lite-etrs-ca-market-egx__runw5-sweeplite-etrs-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/124806__sweep-lite-etrs-ca-market-egx__runw5-sweeplite-etrs-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/125656__sweep-lite-fait-ca-market-egx__runw5-sweeplite-fait-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/125656__sweep-lite-fait-ca-market-egx__runw5-sweeplite-fait-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/130440__sweep-lite-faita-ca-market-egx__runw5-sweeplite-faita-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/130440__sweep-lite-faita-ca-market-egx__runw5-sweeplite-faita-001: family-fundamentals absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/130440__sweep-lite-faita-ca-market-egx__runw5-sweeplite-faita-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001: family-price-forecast absent (no-kronos-csv) — no rows
- sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001: family-technicals absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001: kronos-alone absent (no-kronos-csv) — no rows
- sweeps/2026-11-25/131220__sweep-lite-gour-ca-market-egx__runw5-sweeplite-gour-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/131935__sweep-lite-icfc-ca-market-egx__runw5-sweeplite-icfc-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/131935__sweep-lite-icfc-ca-market-egx__runw5-sweeplite-icfc-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/132652__sweep-lite-ifap-ca-market-egx__runw5-sweeplite-ifap-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/132652__sweep-lite-ifap-ca-market-egx__runw5-sweeplite-ifap-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/133518__sweep-lite-isph-ca-market-egx__runw5-sweeplite-isph-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/133518__sweep-lite-isph-ca-market-egx__runw5-sweeplite-isph-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/134241__sweep-lite-jufo-ca-market-egx__runw5-sweeplite-jufo-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/134241__sweep-lite-jufo-ca-market-egx__runw5-sweeplite-jufo-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/135002__sweep-lite-lcsw-ca-market-egx__runw5-sweeplite-lcsw-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/135002__sweep-lite-lcsw-ca-market-egx__runw5-sweeplite-lcsw-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/135953__sweep-lite-masr-ca-market-egx__runw5-sweeplite-masr-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/135953__sweep-lite-masr-ca-market-egx__runw5-sweeplite-masr-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/140917__sweep-lite-mcqe-ca-market-egx__runw5-sweeplite-mcqe-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/140917__sweep-lite-mcqe-ca-market-egx__runw5-sweeplite-mcqe-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/141625__sweep-lite-mpco-ca-market-egx__runw5-sweeplite-mpco-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/141625__sweep-lite-mpco-ca-market-egx__runw5-sweeplite-mpco-001: family-sentiment absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/141625__sweep-lite-mpco-ca-market-egx__runw5-sweeplite-mpco-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/142551__sweep-lite-mtie-ca-market-egx__runw5-sweeplite-mtie-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/142551__sweep-lite-mtie-ca-market-egx__runw5-sweeplite-mtie-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/143311__sweep-lite-ocdi-ca-market-egx__runw5-sweeplite-ocdi-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/143311__sweep-lite-ocdi-ca-market-egx__runw5-sweeplite-ocdi-001: family-sentiment absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/143311__sweep-lite-ocdi-ca-market-egx__runw5-sweeplite-ocdi-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/144023__sweep-lite-olfi-ca-market-egx__runw5-sweeplite-olfi-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/144023__sweep-lite-olfi-ca-market-egx__runw5-sweeplite-olfi-001: family-sentiment absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/144023__sweep-lite-olfi-ca-market-egx__runw5-sweeplite-olfi-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/144735__sweep-lite-orhd-ca-market-egx__runw5-sweeplite-orhd-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/144735__sweep-lite-orhd-ca-market-egx__runw5-sweeplite-orhd-001: family-sentiment absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/144735__sweep-lite-orhd-ca-market-egx__runw5-sweeplite-orhd-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/145515__sweep-lite-orwe-ca-market-egx__runw5-sweeplite-orwe-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/145515__sweep-lite-orwe-ca-market-egx__runw5-sweeplite-orwe-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/150344__sweep-lite-phdc-ca-market-egx__runw5-sweeplite-phdc-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/150344__sweep-lite-phdc-ca-market-egx__runw5-sweeplite-phdc-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/151150__sweep-lite-racc-ca-market-egx__runw5-sweeplite-racc-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/151150__sweep-lite-racc-ca-market-egx__runw5-sweeplite-racc-001: raw-llm-cohere absent (llm-key-absent) — no rows
- sweeps/2026-11-25/195201__sweep-lite-rmda-ca-market-egx__runw5-sweeplite-rmda-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/195201__sweep-lite-rmda-ca-market-egx__runw5-sweeplite-rmda-001: family-price-forecast absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/201240__sweep-lite-saud-ca-market-egx__runw5-sweeplite-saud-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/201240__sweep-lite-saud-ca-market-egx__runw5-sweeplite-saud-001: family-price-forecast absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/201513__sweep-lite-skpc-ca-market-egx__runw5-sweeplite-skpc-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/201513__sweep-lite-skpc-ca-market-egx__runw5-sweeplite-skpc-001: family-price-forecast absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/201513__sweep-lite-skpc-ca-market-egx__runw5-sweeplite-skpc-001: family-sentiment absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/202510__sweep-lite-tmgh-ca-market-egx__runw5-sweeplite-tmgh-001: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/202510__sweep-lite-tmgh-ca-market-egx__runw5-sweeplite-tmgh-001: family-price-forecast absent (family-did-not-vote) — no rows
- sweeps/2026-11-25/214314__sweep-poul-ca-market-egx__runmanual-sweep-2026-11-25-cohere65: family-price-forecast absent (family-did-not-vote) — no rows
- sweeps/2026-11-26/074217__sweep-lite-poul-ca-market-egx__runsched-2026-11-26: family-agent absent (family-did-not-vote) — no rows
- sweeps/2026-11-26/074217__sweep-lite-poul-ca-market-egx__runsched-2026-11-26: family-price-forecast absent (family-did-not-vote) — no rows
- 36 benchmark row(s) invalidated (validation mismatch or the issue-#87 guard) — never scored: buy-and-hold POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; buy-and-hold POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; buy-and-hold POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-fundamentals POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-fundamentals POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-fundamentals POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-price-forecast POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-price-forecast POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-price-forecast POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-sentiment POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-sentiment POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-sentiment POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-technicals POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-technicals POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; family-technicals POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; kronos-alone POUL.CA as of 2026-11-22 (day) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; kronos-alone POUL.CA as of 2026-11-22 (week) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; kronos-alone POUL.CA as of 2026-11-22 (month) from sweeps/2026-11-22/062207__sweep-lite-poul-ca-market-egx__runsched-2026-11-22; buy-and-hold POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; buy-and-hold POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; buy-and-hold POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-fundamentals POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-fundamentals POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-fundamentals POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-price-forecast POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-price-forecast POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-price-forecast POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-sentiment POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-sentiment POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-sentiment POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-technicals POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-technicals POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; family-technicals POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; kronos-alone POUL.CA as of 2026-11-24 (day) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; kronos-alone POUL.CA as of 2026-11-24 (week) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24; kronos-alone POUL.CA as of 2026-11-24 (month) from sweeps/2026-11-24/062345__sweep-lite-poul-ca-market-egx__runsched-2026-11-24

_The ensemble is the reference row: the table is symmetric and fixed-order, and every cell is published as scored._
