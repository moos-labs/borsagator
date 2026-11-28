# Round 100: index-event data check (named partial) and parked gap

Status: data check only. No pre-registration, no scoring, nothing built. Research from public pages, opened this round unless marked "snippet only".

## Panel in the archive cells
The 15 cutoff dates in cells 1-90 (2023-12-29 to 2026-09-30, mostly quarterly) hold the names COMI, ETEL, HRHO, SWDY, TMGH and NVDA (HRHO absent on 2026-09-30). NVDA is a US name with no EGX index events. The 8-ticker harvest set (adds ABUK, AMOC, POUL) is a different list; ABUK, AMOC and POUL are not in these cells.

## EGX index events touching those names (add/delete, opened sources)
| Review | Announced / effective | Event | Source opened |
|---|---|---|---|
| Feb 2025 | 2025-01-30 / 2025-02-01 | Elsewedy Electric (SWDY) removed from EGX30 (article ties it to the Electra free-float purchase, so confounded) and from EGX33 | https://www.egypttoday.com/Article/3/138063/EGX-completes-semi-annual-review-reveals-26-moves-across-main and https://www.businesstodayegypt.com/Article/3/5955/Orascom-Development-RAMEDA-EgyptAlum-and-more-join-EGX30-in-bourse%E2%80%99s |
| Aug 2025 | 2025-07-29 / 2025-08-03 | AMOC removed from EGX33 (not a cell panel name) | https://mondovisione.com/media-and-resources/news/the-egyptian-exchange-egx-announces-the-semi-annual-review-of-its-market-indic-2025730/ |
| Sep 2026 | 2026-08-16 / 2026-09-01 | ETEL and SWDY (and ABUK, not a cell name) removed from EGX35-LV. ETEL is named in the EnterpriseAM text; SWDY's and ABUK's placement is from the page's 13+13 layout, whose second block also holds the three EnterpriseAM-named drop-outs, so it is strongly supported but the column is not labelled on the page | https://mondovisione.com/news/the-egyptian-exchange-egx-announces-the-semi-annual-review-of-its-market-indic-2026816/ and https://enterpriseam.com/egypt/2026/08/18/egx-announces-index-reshuffle-as-updated-rules-take-effect/ |
EGX30, EGX70 EWI, EGX100 EWI, EGX33 and EGX35-LV full tables read for Feb 2026 (https://mondovisione.com/_assets/files/press_release_indices_feb_2026_english_english.pdf): none of the cell names. EGX30 lists with names read for Feb 2024, Aug 2024 and Sep 2026: none of the cell names.

## Overlap with the cutoffs
- Feb 2025: the 2024-12-31 cutoff month horizon ends about 2025-01-30, the announcement date, before the 2025-02-01 effective date. No effective-date overlap.
- Sep 2026: the 2026-08-14 cutoff (cells 48-90) horizons cover the 2026-08-16 announcement and the 2026-09-01 effective date for the month horizon, so ETEL and SWDY would be flagged there, in the descriptive window only.
- Cells 1-47: no flagged pair found from the opened sources. A signed tilt cannot be fit on cells 1-47 for lack of any flagged training pair, and the descriptive window holds at most 2 flagged names on 1 cutoff.

## Not done
- Feb 2025 and Aug 2024 and Feb 2024 index tables (EGX PDFs: www.egx.com.eg resets the connection, see below; the press pages opened carry no tables or only names I grepped for).
- MSCI Egypt review lists: not opened. Snippet only: https://www.msci.com/eqb/gimi/stdindex/MSCI_Nov25_STPublicList.pdf and https://english.ahram.org.eg/NewsContent/3/12/551892/Business/Economy/MSCI-index-review-takes-effect-on-Egyptian-Exchang.aspx (opened; it states the effect date and trading volume but lists no Egyptian names).
- Jul/Aug 2023 EGX tables: press page opened, no tables.

## Reading
By construction the route is counts-only: 3 cell-name events found across about 6 reviews, none in a training cell, none at a usable horizon in cells 1-47. The index-regime decisions for the 2026 changes in cadence (announcement at least two weeks before effect, effective first working day of the month, EnterpriseAM 2026-07-13, snippet only) would matter for a point-in-time rule.

## Parked gap: insider and major-shareholder dealing forms
Parked by Moos (Slack 1795849347.431379, relayed, not read): "blocked on EGX bulletin/press access; revisit if a clean access route appears". Facts at parking time: https://www.egx.com.eg/downloads/Bulletins/63907_1.pdf and https://www.egx.com.eg/ar/NewsDetails.aspx?NewsID=298099 fail from the research host with `curl: (56) OpenSSL SSL_read: Connection reset by peer, errno 104`; the same fetch through the web fetch tool returns an empty record or CRAWL_EMPTY_CONTENT. The harvested disclosure set holds 55 items, none a dealing form (8 board-and-shareholder-structure forms only), about Nov 2026 only. No further work is planned on this item.
