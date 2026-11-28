# Round 100: index-event data check (named partial) and parked gap

Status: data check only. No pre-registration, no scoring, nothing built. Research from public pages, opened this round unless marked "snippet only".

## Panel in the archive cells
The 15 cutoff dates in cells 1-90 (2023-12-29 to 2026-09-30, mostly quarterly) hold the names COMI, ETEL, HRHO, SWDY, TMGH and NVDA (HRHO absent on 2026-09-30). NVDA is a US name with no EGX index events. The 8-ticker harvest set (adds ABUK, AMOC, POUL) is a different list; ABUK, AMOC and POUL are not in these cells.

## EGX index events touching those names (add/delete, opened sources)
| Review | Announced / effective | Event | Source opened |
|---|---|---|---|
| Feb 2025 | 2025-01-30 / 2025-02-02 | Elsewedy Electric (SWDY) removed from EGX30 (article ties it to the Electra free-float purchase, so confounded) and from EGX33 | https://www.egypttoday.com/Article/3/138063/EGX-completes-semi-annual-review-reveals-26-moves-across-main and https://www.businesstodayegypt.com/Article/3/5955/Orascom-Development-RAMEDA-EgyptAlum-and-more-join-EGX30-in-bourse%E2%80%99s |
| Aug 2025 | 2025-07-29 / 2025-08-03 | Elsewedy Electric (SWDY) ADDED to EGX70 EWI (Additions #1) and to EGX100 EWI (Additions #1); Alexandria Mineral Oils (AMOC, not a cell panel name) ADDED to EGX33 Shariah (Additions #3). Direction read from the page's row-wise Additions/Deletions pairing; the fetched text is flattened, so the pairing is read from the row order and the numbered rows (the EGX70 row reads "1 ELSWEDY ELECTRIC / 1 Al Baraka Bank Egypt") | https://mondovisione.com/media-and-resources/news/the-egyptian-exchange-egx-announces-the-semi-annual-review-of-its-market-indic-2025730/ |
| Sep 2026 | 2026-08-16 / 2026-09-01 | EGX35-LV, columns Additions / Deletions: SWDY ADDED (Additions #11); ETEL REMOVED (Deletions #12); ABUK REMOVED (Deletions #10, not a cell name). ETEL's removal is also named in the EnterpriseAM text | https://mondovisione.com/news/the-egyptian-exchange-egx-announces-the-semi-annual-review-of-its-market-indic-2026816/ and https://enterpriseam.com/egypt/2026/08/18/egx-announces-index-reshuffle-as-updated-rules-take-effect/ |
EGX30, EGX70 EWI, EGX100 EWI, EGX33 and EGX35-LV full tables read for Feb 2026 (https://mondovisione.com/_assets/files/press_release_indices_feb_2026_english_english.pdf): none of the cell names. EGX30 lists with names read for Feb 2024, Aug 2024 and Sep 2026: none of the cell names.

## Overlap with the cutoffs
Realised dates are the repo's own (SWDY closes, EGX trades Sunday to Thursday). A pair is flagged by the ANNOUNCEMENT date if its realised window includes it, and by the EFFECTIVE date if it includes that.
- Feb 2025 (announced 2025-01-30, effective 2025-02-02; the EGX notice says "effective on Sunday, 2 February 2025", and 2025-02-01 was a Saturday): the SWDY 2024-12-31 month pair realises 2025-02-02, which is the effective date itself, so it covers both dates and stays flagged. Flagged (SWDY removed from EGX30 and EGX33, confounded by the Electra purchase). This corrects the first draft, which said the window ended about 2025-01-30 with no effective-date overlap.
- Aug 2025 (announced 2025-07-29, effective 2025-08-03): the SWDY 2025-06-30 month pair realises 2025-08-03, so it covers both dates. Flagged (SWDY ADDED to EGX70 EWI and EGX100 EWI). Day (2025-07-01) and week (2025-07-09) pairs end before the announcement.
- Sep 2026 (announced 2026-08-16, effective 2026-09-01), cutoff 2026-08-14 in cells 48-90 (descriptive window only): the month pairs realise 2026-09-14, so ETEL (removed) and SWDY (ADDED, sign opposite to ETEL) are flagged on both dates; the day pairs realise 2026-08-16 (announcement date itself) and the week pairs 2026-08-20.
- Cells 1-47: TWO flagged pairs, both SWDY month pairs (2024-12-31 and 2025-06-30), with opposite event directions (removal, addition). This replaces the first draft's "no flagged pair found". The conclusion that a signed tilt cannot be fit on cells 1-47 still holds, now for a different reason: two flagged pairs, one name, opposite signs, one confounded, far below any fit gate. Other cell names (COMI, ETEL, HRHO, TMGH, NVDA) have no flagged training pair.

## Not done
- Feb 2025 and Aug 2024 and Feb 2024 index tables (EGX PDFs: www.egx.com.eg resets the connection, see below; the press pages opened carry no tables or only names I grepped for).
- MSCI Egypt review lists: not opened. Snippet only: https://www.msci.com/eqb/gimi/stdindex/MSCI_Nov25_STPublicList.pdf and https://english.ahram.org.eg/NewsContent/3/12/551892/Business/Economy/MSCI-index-review-takes-effect-on-Egyptian-Exchang.aspx (opened; it states the effect date and trading volume but lists no Egyptian names).
- Jul/Aug 2023 EGX tables: press page opened, no tables.

## Reading
By construction the route is counts-only: 6 cell-name index events (SWDY: EGX30 and EGX33 removal in Feb 2025, EGX70 EWI and EGX100 EWI addition in Aug 2025; ETEL removal and SWDY addition in EGX35-LV in Sep 2026) across 3 reviews with events, all on two cell names, and only 2 flagged training pairs (both SWDY month). The descriptive window holds 2 flagged names on 1 cutoff with opposite signs. The index-regime decisions for the 2026 changes in cadence (announcement at least two weeks before effect, effective first working day of the month, EnterpriseAM 2026-07-13, snippet only) would matter for a point-in-time rule.

## Parked gap: insider and major-shareholder dealing forms
Parked by Moos (Slack 1795849347.431379, relayed, not read): "blocked on EGX bulletin/press access; revisit if a clean access route appears". Facts at parking time: https://www.egx.com.eg/downloads/Bulletins/63907_1.pdf and https://www.egx.com.eg/ar/NewsDetails.aspx?NewsID=298099 fail from the research host with `curl: (56) OpenSSL SSL_read: Connection reset by peer, errno 104`; the same fetch through the web fetch tool returns an empty record or CRAWL_EMPTY_CONTENT. The harvested disclosure set holds 55 items, none a dealing form (8 board-and-shareholder-structure forms only), about Nov 2026 only. No further work is planned on this item.
