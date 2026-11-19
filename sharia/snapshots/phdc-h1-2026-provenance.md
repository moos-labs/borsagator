# PHDC.CA — H1-2026 snapshot provenance (issue #326; rebuilt under issue #330)

## Source document (PRIMARY)
- Palm Hills Developments Company S.A.E — **Periodic Consolidated Financial Statements on 30 June 2026, together with Limited Review Report** (auditor: Mostafa Shawki — Forvis Mazars). English translation, originally issued in Arabic. Statements authorized for issue by the board on 17 August 2026 (note 6); EGX filing date 18 August 2026.
- URL: https://foudalens.com/disclosures/PHDC.CA/financial_statement/2026-08-18_293547_2.pdf (the `_1.pdf` attachment of the same filing is the Arabic original of the same consolidated statements).
- Local copy: `~/workspace/issue326-work/harvest/PHDC/phdc-h1-2026_293547_2.pdf` — 70 pages, fully scanned images (no text layer); all figures below were read from the rendered statement/note pages and cross-tied to printed totals.
- sha256: `f17b9e284c35fd0c36eb117480391191c455edd09ae9d6347e7f9b59b4f912c4`
- Unit: exact Egyptian pounds (EGP) as printed — NOT thousands.
- Basis: CONSOLIDATED only. Income statement = six months 1 Jan–30 Jun 2026; balance sheet at 30 June 2026 with 31 December 2025 comparatives.

## Field locations and mapping decisions (H1-2026)

- **total_revenue = 19,528,117,727** — face of the consolidated statement of income, "Revenues" (note 64), six-months column. (Ties to the company's H1-2026 reporting of EGP 19.53 billion revenue.)
- **non_compliant_revenue = 978,800,027** — REBUILT under the issue #330 extraction rule (rule v1.0.0, `scripts/sharia_snapshot.py`): interest-type income wherever presented. Per-line classification (machine-readable in `phdc-h1-2026-interest-income-lines.json`, stored on the snapshot as `non_compliant_revenue_breakdown`):
  | Statement line | Presented in | Amount (EGP) | Treatment |
  |---|---|---|---|
  | Credit interest and Returns on investments Measured at Amortized cost | Other revenues (income statement face, note 31-d) | 455,606,067 | INCLUDE — the company's interest-income line |
  | Amortization of discount on notes receivables | Other revenues (income statement face) | 523,193,960 | INCLUDE — discount unwinding on customer notes, implicit interest on deferred payments |
  | Gains on financial investments at FVPL | Other revenues (income statement face) | 15,253,619 | EXCLUDE — fair-value gain, not interest |
  | Transfer fees and delay penalties | Revenues / other activities revenues (note 64) | 547,790,260 | EXCLUDE — service fees, not interest |
  - Income % = 978,800,027 / 19,528,117,727 = **5.01%** (was 2.33% as harvested: 455,606,067, the interest-income line only — kept on the snapshot as `non_compliant_revenue_as_harvested`). The three other-revenues lines sum to the printed "Total other revenues" 994,053,646. ✓
- **interest_bearing_debt = 26,338,697,273** — bank debt only, leases EXCLUDED:
  - Loans – long-term (note 51): 10,236,280,237
  - Loans – current portion (note 51): 650,151,650 (loans total per note 51: 10,886,431,887)
  - Credit facilities (note 50 — the note itself captions this balance "Banks overdraft"): 13,922,422,891
  - Banks – credit balances (note 49, overdraft balances): 1,529,842,495
  - Excluded: lease contract liabilities 63,263,828 (ST) + 78,329,645 (LT) = 141,593,473 (note 55); notes payable 4,778,461,505 (ST) + 4,016,714,644 (LT) (land/supplier notes, not bank debt); land purchase liabilities 29,612,533 + 47,134,741 (note 56); **Joint Share Arrangement 1,831,705,748 (ST) + 3,530,990,688 (LT) = 5,362,696,436 (note 58) — EXCLUDED and FLAGGED**: per note 58 this is the project partners' (land owners') net share under the participation system, payable for land value and external facilities per annual payment schedules — a co-development partner obligation, not a bank loan/bond; if central policy treats partner financing as debt, add 5,362,696,436 (debt would be 31,701,393,709). Also excluded: other long-term liabilities – Residents' Association 34,337,384,836 (residents'/maintenance-related, note 63) and obligations for checks received from clients 1,728,980,776 (note 54, the mirror of undelivered-units notes receivable).
- **interest_bearing_assets = 15,063,444,558**:
  - Financial investments at amortized cost (note 47 — "investment in treasury bills and bonds", purchase-price basis, avg. return ≈19%): 13,016,407,445 (current; no non-current balance)
  - Bank deposits inside cash & equivalents (note 48): deposits–EGP 2,500,000 + deposits–foreign currency 2,044,537,113 = 2,047,037,113
- **cash_and_liquid_assets = 5,757,209,793** — the rest of cash & cash equivalents: note 48 total 7,804,246,906 (banks current accounts EGP 5,051,856,306 + FC 524,696,277 + deposits 2,047,037,113 + cash on hand 189,479,645 − ECL 8,822,435) minus the bank-deposits bucket above. Buckets are disjoint and sum to the cash note total. Investments at FVPL (179,503,696) are not cash and are excluded from both buckets.
- **total_assets = 194,767,286,727** — face of the consolidated financial position. Cross-tie: non-current 67,800,794,295 + current 126,966,492,432 = 194,767,286,727; equity 20,633,908,214 + non-current liabilities 52,289,409,914 + current liabilities 121,843,968,599 = 194,767,286,727. ✓
- **accounts_receivable = 113,022,009,391**:
  - Accounts receivable (note 44): 35,055,008,362
  - Notes receivable – long term (note 41): 55,707,502,096
  - Notes receivable – short term (note 41): 20,530,518,157
  - Notes receivable for undelivered units – long term (note 42): 1,033,560,158
  - Notes receivable for undelivered units – short term (note 42): 695,420,618
  - Excluded: debtors and other debit balances 14,932,335,834 (note 45 — commissions paid in advance, Residents' Association, deposits, prepaid expenses, etc.), suppliers – advance payments 10,490,853,035, due from related parties 346,267,799, works in progress 23,915,930,580 (inventory, not receivables). Off-balance-sheet notes receivable for post-2022 undelivered units (note 72, nominal EGP 116.5bn) are NOT in the statements and are not counted.
- **shares_outstanding = 2,859,914,173** — note 60 (Capital): issued and paid-up capital EGP 5,719,828,346 distributed over 2,859,914,173 shares at EGP 2 par. (The EPS note 71 uses a time-weighted average of 2,835,542,374 shares, net of treasury shares; the issued count is used here for consistency with the other snapshots.)
- **activity: permissible** — Note 2 (Company's purpose): real-estate investment and development in the New Cities and New Urban Communities (residential compounds, resorts, villas, touristic villages, leasing, integrated projects). Real-estate development is a permissible activity.

## Adjacent period — FY2025 (31 Dec 2025, from the H1-2026 comparative column)
File: `phdc-fy2025-balances.json`
- total_assets 172,129,812,858 (non-current 65,900,163,274 + current 106,229,649,584; equity+L tie ✓)
- interest_bearing_debt 24,069,463,226 = loans LT 10,543,120,329 + loans current 1,250,040,023 + credit facilities 11,337,531,976 + banks-credit balances 938,770,898 (leases 102,620,443 excluded; joint share arrangement 6,973,738,224 excluded as above)
- interest_bearing_assets 11,007,374,216 = amortized-cost investments 9,581,528,351 + bank deposits in cash 1,425,845,865 (2,500,000 + 1,423,345,865)
- cash_and_liquid_assets 7,993,680,294 = cash total 9,419,526,159 − 1,425,845,865
- accounts_receivable 103,510,901,065 = accounts receivable 28,118,116,247 + notes LT 54,801,316,199 + notes ST 18,137,718,924 + undelivered LT 1,518,490,219 + undelivered ST 935,259,476

## Adjacent period — 9M-2026 (30 Sep 2026)
File: `phdc-9m-2026-balances.json`
- Source: Palm Hills Developments periodic **consolidated** financial statements for the nine months ended 30 September 2026 (Arabic original; auditor Mostafa Shawki — Forvis Mazars), FoudaLens/EGX filing dated 16 November 2026: https://foudalens.com/disclosures/PHDC.CA/financial_statement/2026-11-16_298017_1.pdf — local copy `~/workspace/issue326-work/harvest/PHDC/phdc-9m-2026_298017_1.pdf`, 71 pages, sha256 `98ddfae6474543f7e784e6327e7aa1262fd2f0568bd46c49640fe7ee6fc8fb1b`. Unit: exact EGP. (The same filing's other attachments are the 9M earnings release — summary balance sheet in EGP thousands only — and the standalone statements; neither was used for these items. The statement totals cross-tie to the earnings-release summary: total assets EGP 217,280,540 thousand.)
- total_assets 217,280,539,537 (non-current 78,150,479,934 + current 139,130,059,603; equity 22,085,631,911 + LT liabilities 59,204,102,809 + current liabilities 135,990,804,817 ✓)
- interest_bearing_debt 28,697,132,819 = loans LT 11,235,053,165 + loans current portion 861,658,430 (note 51) + credit facilities 15,237,645,915 (note 50) + banks-credit balances 1,362,775,309 (note 49: local 1,265,623,968 + FC 97,151,341). Leases (58,129,029 + 82,873,916), notes payable, land-purchase creditors and the joint share arrangement (1,709,595,534 + 2,628,489,933) excluded on the same basis as H1.
- interest_bearing_assets 15,969,790,833 = financial investments at amortized cost (treasury bills and bonds, note 47) 14,275,083,394 + bank deposits inside cash (note 48) 1,694,707,439 (2,500,000 + 1,692,207,439)
- cash_and_liquid_assets 7,793,604,073 = cash & equivalents total 9,488,311,512 (note 48: current accounts 6,797,442,257 + 862,126,641, deposits 1,694,707,439, cash on hand 145,638,449, total 9,499,914,786 − ECL 11,603,274) − 1,694,707,439
- accounts_receivable 124,009,321,628 = accounts receivable 35,093,100,194 + notes receivable LT 65,673,025,454 + notes receivable ST 21,759,234,412 + undelivered-units notes LT 873,387,778 + ST 610,573,790
