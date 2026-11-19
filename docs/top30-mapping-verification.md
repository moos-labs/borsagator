# #283 stage 2 — top-30 mapping verification (B-01–B-04)

Checked **2026-11-19**. Method and per-issuer record for the stage-2 mapping
verification. The manifest (`evaluation/top30_manifest.json`, `stage2_verification`)
is the machine-readable record; this document is the human-readable audit trail.

## Method

A value counts as verified only against a **primary source**:

1. An **EGX disclosure header** as republished by Mubasher
   (`english.mubasher.info`) or Okaz (`okazinvest.com`) — the header carries
   `Company Name / ISIN Code / Reuters Code` verbatim from the EGX filing.
2. The **Investor Protection Fund** (`ipf.eg`) official fund-members list —
   the statutory Egyptian fund's member table (ISIN + legal name per member).
   Used for re-confirmation where no disclosure header was located in this run;
   those rows say so explicitly.

Aggregator values (coindataflow, Finnhub, FoudaLens, StockAnalysis, Decypha,
TradingView) were used **only as candidates to re-confirm, never as the
verifying source**. Nothing was guessed, defaulted, or zero-filled.

Every ISIN written into the manifest passed **ISO 6166 check-digit validation**
(Luhn on the letter-expanded form), run locally on 2026-11-19. The check caught
one real error — see AMOC below.

## Results by blocker

| Blocker | Stage 1 | After this run |
|---|---|---|
| B-01 (5 issuers, no ISIN/name source) | 5 issuers, nothing sourced | **ISIN + English name resolved for all 5**; Arabic names still open |
| B-02 (14 listings missing ISIN) | 14 missing | **13 resolved**; only FAITA remains |
| B-03 (23 listings missing Arabic name) | 23 missing | **0 resolved** — still open (see below) |
| B-04 (9 aggregator ISINs) | 9 unconfirmed | **All 9 re-confirmed — RESOLVED** |
| B-05 (weights) | unverified | untouched (out of scope for this run) |

Counts now: **30 of 31 listings carry a verified ISIN** (only FAITA missing);
**3 of 31 listings carry a verified Arabic name** (TMGH, ETEL, AMOC; controls
POUL, COMI make 5 rows with Arabic names in the file).

## Verified ISINs (new or re-confirmed)

### From EGX disclosure headers (Mubasher / Okaz)

| Code | ISIN | English name (as in header) | Header source |
|---|---|---|---|
| EFIH | EGS743O1C013 | E-Finance For Digital and Financial Investements SAE | Mubasher, Release Regarding a Disclosure Form (Art. 29 EGX Listing Rules) — https://english.mubasher.info/news/4544706/E-Finance-For-Digital-and-Financial-Investements-SAE-EFIH-CA-Release-Regarding-a-Disclosure-Form/ |
| EFID | EGS305I1C011 | Edita Food Industries S.A.E | Okaz, FY2024 business results release — https://www.okazinvest.com/okaz/newDetails.aspx?id=1045552&nb=2 (corroborated by IPF row 128) |
| PHDC | EGS655L1C012 | Palm Hills Development Company | Mubasher, BoD decisions 16 Nov 2025 — https://english.mubasher.info/news/4525194/Palm-Hills-Development-Company-PHDC-CA-Board-of-Directors-Decisions/ (corroborated by IPF row 150) |
| RMDA | EGS381B1C015 | Tenth Of Ramadan Pharmaceutical Industries & Diagnostic - Rameda | Mubasher, FY2024 consolidated results — https://english.mubasher.info/news/4424672/Tenth-Of-Ramadan-Pharmaceutical-Industries-Diagnostic-Rameda-RMDA-CA-Reports-Year-Ended-31-12-2024-Consolidated-Results/ (corroborated by IPF row 219) |
| CIRA | EGS65541C012 | Cairo for Investment and Real Estate Development – Seera Education | Okaz, explanatory statement re CIRA Care — https://www.okazinvest.com/okaz/newDetails.aspx?id=1017126&nb=2 (header name truncated in the page rendering; full name per IPF row 87) |
| EGAL | EGS3E181C010 | Egypt Aluminum | Mubasher, Release Responding to EGX Inquiries — https://english.mubasher.info/news/3403631/Release-from-Egypt-Aluminum-EGAL-CA-Responding-to-EGX-Inquiries/ |
| MCQE | EGS3C391C017 | Misr Cement (Qena) | Mubasher, Corporate Governance Report FY2023 — https://english.mubasher.info/news/4264327/Misr-Cement-Qena-MCQE-CA-Corporate-Governance-Report/ |
| MASR | EGS65571C019 | Medinet MASR Housing | Mubasher — https://english.mubasher.info/news/4547202/Release-from-Medinet-MASR-Housing-MASR-CA-/ and Okaz — https://www.okazinvest.com/okaz/newDetails.aspx?id=1034645&nb=2 |
| OLFI | EGS30AL1C012 | Obour Land For Food Industries | Mubasher, FY2025 standalone results — https://english.mubasher.info/news/4552622/Obour-Land-For-Food-Industries-OLFI-CA-Reports-Year-Ended-31-12-2025-Standalone-Results/ |
| ARCC | EGS3C0O1C016 | Arabian Cement Company | Mubasher, Corporate Governance Report FY2022 (20 Mar 2023) — https://english.mubasher.info/news/4092584/Arabian-Cement-Company-ARCC-CA-Corporate-Governance-Report/ (corroborated by IPF row 63) |
| MTIE | EGS75011C014 | MM Group Industrial & International Trade (In Kind) | Mubasher, BoD decisions 16 Nov 2025 — https://english.mubasher.info/news/4525099/MM-Group-Industrial-International-Trade-In-Kind-MTIE-CA-Board-of-Directors-Decisions/ |
| ATQA | EGS3D0C1C018 | Misr National Steel - Ataqa | Mubasher, BoD & shareholders-structure disclosure (period ended 30/09/2024) — https://english.mubasher.info/news/4352391/Misr-National-Steel-Ataqa-ATQA-CA-Disclosure-Form-for-the-BoD-the-Shareholders-Structure/ |

### From the IPF official fund-members list (https://ipf.eg/en/fund-members/)

| Code | ISIN | IPF name (row) | Note |
|---|---|---|---|
| ADIB | EGS60111C019 | Abu Dhabi Islamic Bank (40) | B-04 re-confirm; matches coindataflow value exactly |
| ORAS | EGS95001C011 | Orascom Construction PLC (200) | B-04 re-confirm; matches coindataflow value exactly |
| FAIT | EGS60321C014 | Faisal Islamic Bank (45) | B-04 re-confirm; matches coindataflow value exactly |
| SKPC | EGS380S1C017 | Sidi Kerir Petrochemicals Company (8) | B-04 re-confirm; matches coindataflow value exactly |
| ISPH | EGS512O1C012 | Ibn Sina Pharma (44) | B-04 re-confirm; matches coindataflow value exactly |
| JUFO | EGS30901C010 | Juhayna Food Industries (123) | B-04 re-confirm; matches coindataflow value exactly |
| ORHD | EGS70321C012 | Orascom Development Egypt (142) | B-04 re-confirm; matches coindataflow value exactly (current name) |
| ORWE | EGS33041C012 | Oriental Carpet Weavers (130) | B-04 re-confirm; matches coindataflow value exactly |
| ETRS | EGS42051C010 | Egyptian Transport and Trade Services (Egytrans) (66) | B-04 re-confirm; matches coindataflow value exactly |
| IFAP | EGS07061C012 | International Agricultural Crops (22) | B-02; confirms the aggregator candidate |
| SAUD | EGS60101C010 | Al Baraka Bank Egypt (159) | B-02; no EGX header located in this run |
| ACGC | EGS32221C011 | Arabic cotton ginning (56) | B-02; no EGX header located in this run |
| MPCO | EGS02091C014 | Mansoura Poultry (198) | B-02; no EGX header located in this run |
| EGAS | EGS39011C019 | Egypt Gas (68) | B-02; no EGX header located in this run |
| OCDI | EGS65851C015 | 6th of October Development and Investment (SODIC) (152) | B-01; no EGX header located in this run — IPF only, corroborated by Decypha/TradingView (aggregators). An EGX-header re-confirmation is still desirable. |

## AMOC correction — stage-1 "verified" ISIN was wrong

The manifest's stage-1 AMOC ISIN, `EGS3E2B1C018` (from
`worker/egx_harvest.py` `EGX_COMPANIES`), **fails ISO 6166 check-digit
validation** — it cannot be a valid ISIN. The IPF list gives AMOC as
`EGS380P1C010` (row 103, Alexandria Mineral Oils Company – AMOC), whose check
digit is valid. The manifest now carries `EGS380P1C010`.

**Follow-up required (not done here):** `worker/egx_harvest.py`
`EGX_COMPANIES` still carries the wrong value. `worker/` was out of scope for
this task, so the harvester was not touched — fixing it is a separate step,
and any harvest using the old value would query the wrong ISIN. TMGH and ETEL
(the other two harvester-verified rows) pass check-digit validation and agree
with IPF, so only AMOC is affected.

## Still blocked

- **B-01, Arabic names only (5):** EFID, PHDC, RMDA, OCDI, CIRA. ISIN +
  English name are done; each Arabic legal name still needs an EGX Arabic
  disclosure header or the EGX company page.
- **B-02, FAITA only:** the USD listing of Faisal Islamic Bank. Its ISIN
  differs from FAIT (`EGS60321C014`) and was not found: no EGX disclosure
  header located, it is not a separate IPF member, and Finnhub/Musaffa list
  the USD ticker without an ISIN. Do NOT default to the FAIT ISIN. Next: an
  EGX header for the FAITA (USD) listing, or the issuer/FRA listing record
  for the USD shares.
- **B-03, Arabic names (23 listings):** EFIH, ADIB, ORAS, FAIT, FAITA, SKPC,
  EGAL, ISPH, JUFO, MCQE, ORHD, MASR, ORWE, OLFI, ARCC, IFAP, MTIE, ATQA,
  SAUD, ACGC, MPCO, EGAS, ETRS. No EGX Arabic disclosure header was located
  for any of them in this run (Arabic Mubasher/Okaz searches returned no
  header pages). Decypha profile pages show Arabic names for several issuers,
  but that is aggregator data and was **not** recorded as verified. Next: EGX
  Arabic disclosure headers, or the issuers' own official Arabic filings.
- **B-05, weights:** untouched; needs a readable dated 2026-02-01 EGX33
  roster with weights.

## Name variants recorded

Where the EGX header name differs from the stage-1 aggregator name, the
manifest now carries the header name and the stage-1 value is noted in the
listing's `verification.note`: EGAL ("Egypt Aluminum Company SAE" →
"Egypt Aluminum"), MCQE ("Misr Cement Company SAE" → "Misr Cement (Qena)"),
MASR ("Madinet Masr for Housing and Development SAE" → "Medinet MASR
Housing"), MTIE ("MM Group for Industry and International Trade SAE" →
"MM Group Industrial & International Trade (In Kind)"), ATQA ("Misr National
Steel SAE" → "Misr National Steel - Ataqa"). IPF spelling variants are noted
the same way (e.g. OLFI "Crossing Land", MPCO "Mansoura", ORWE "Oriental
Carpet Weavers", IPF "Egyptian National Steel" for ATQA).
