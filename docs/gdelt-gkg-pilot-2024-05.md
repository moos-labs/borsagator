# GDELT GKG pilot, 2024-05 — join-quality report

Scope approved by Moos (Slack thread, 2026-11-26): pilot on 2024-05 only, alias table
(`evaluation/gdelt_alias_table.csv`) + restart-safe streaming filter
(`scripts/gdelt_gkg_filter.py`), join-quality per name reviewed here before any larger run.

## Coverage

- Range: 2024-05-01 00:00 through 2024-05-31 23:59 (UTC timestamps in filenames).
- Files processed: 5,952 of 5,952 (2,976 GKG + 2,976 translation stream), zero malformed, zero corrupt lines.
- Rows kept: 112,099 total
  - 111,812 via the Egyptian-outlet channel (SourceCommonName in the EG domain list; broad context corpus).
  - 287 via the alias channel (V2Organizations matched an alias), which is what join quality is measured on.
- Output: `/tmp/gdelt/out/matches.parquet` (13 MB, 112,099 rows) + `alias_hit_summary.csv`.
  `evaluation/gdelt_pilot_202405_alias_hit_summary.csv` is a committed copy of the summary.

## Join quality per name (alias channel, 287 rows, 349 ticker-row pairs)

A row can match more than one ticker (per-ticker pairing), so pairs exceed rows.
Verdicts were grounded by opening matched org strings and sampling URLs from `matches.jsonl`.

| Ticker | Real | False | Ambiguous | Days hit | Note |
|---|---|---|---|---|---|
| ETEL | 165 | 0 | 0 | 27 | Clean. Noisy org strings ("Telecom Egypt Ticker", "We Telecom Egypt") all refer to the company. |
| TMGH | 89 | 0 | 0 | 24 | Clean. Saudi/Oman strings are TMG regional-expansion news, still the same entity. |
| ORHD | 25 | 0 | 0 | 8 | Clean. |
| EFID | 15 | 0 | 0 | 5 | Clean. |
| SAUD | 4 | 7 | 8 | 6 | "Al Baraka Bank Pakistan/South Africa/Tunisia" false (foreign affiliates). Bare "Al Baraka Bank"/"Group" ambiguous (e.g. gfmag.com rankings, Sudan press). Only "…Egypt" is reliably real. |
| EFIH | 0 | 13 | 0 | 7 | All false. "E Finance" matches generic e-finance phrases worldwide (Bangladesh, Armenia, ministries). |
| PHDC | 0 | 8 | 0 | 2 | All false. Squash-club coverage ("Palm Hills Club", "Palm Hills Sports Club", academy). The known survey pattern. |
| ADIB | 3 | 0 | 0 | 3 | Real ("Menafn-" prefixes are GDELT artifacts). |
| CIRA | 0 | 3 | 0 | 3 | False. "Cira Center/Centre" is a Philadelphia building (US local news), not CIRA Education. |
| COMI | 2 | 0 | 0 | 2 | Real. |
| ARCC, FAIT, FAITA, JUFO | 1 each | 0 | 0 | 1 | Real. |
| MTIE | 0 | 1 | 0 | 1 | False ("Mm Group Of Companies" in unrelated offbeat story). |
| OCDI | 0 | 1 | 0 | 1 | False ("Sodic" substring in Indonesian press). |
| ORAS | 0 | 0 | 1 | 1 | Unverifiable single row. |

Totals: 307 real, 33 false, 9 ambiguous of 349 pairs. Precision on the alias channel is 88%
(307/349), 96% for tickers other than the five problem names below.

The other 21 of 38 tickers had zero alias hits in this month; that is expected for a single
month of English-language GKG org strings and is coverage, not false hits. Their rows still
arrive through the Egyptian-outlet channel.

## False-hit patterns to fix before the full run

1. `EFIH` alias "E Finance" is too generic — require co-occurrence (Egypt/digital-government
   context) or drop the alias and rely on "e-finance for Digital and Financial Investments"
   full-name variants.
2. `PHDC` — block "Palm Hills Club", "Palm Hills Sports Club", "Academy Palm Hills" (squash).
3. `SAUD` — restrict to "Al Baraka Bank Egypt" / "Al Baraka Egypt"; block country-suffixed
   affiliates (Pakistan, South Africa, Tunisia, Group).
4. `CIRA` — block "Cira Center"/"Cira Centre" (Philadelphia).
5. `OCDI` — bare "Sodic" substring needs word-boundary + Egypt/development context, or drop.
6. `MTIE` — "Mm Group" needs Egypt context.

## Recommendation

Full 2019–2026 run is viable: the streaming filter held restart-safe across sandbox restarts
at ~10 MB/s sustained, and the alias table yields high precision for the liquid names
(ETEL/TMGH/ORHD/EFID clean). Apply the six pattern fixes above first. BigQuery remains
parked. GDELT terms confirmed: no redistribution planned, research use only.

— Pilot run and report by Instinct, 2026-11-27 (commit on branch ins/data-002-gdelt-gkg-pilot-202405).
