# TMGH.CA — H1-2026 snapshot provenance (issue #326; rebuilt under issue #330)

## Source document (PRIMARY)
- Talaat Mostafa Group Holding Company "TMG Holding" (S.A.E) and subsidiaries — **Interim Consolidated Financial Statements for the three and six months periods ended 30 June 2026**, together with review report (EY / RSM Egypt). Translation of consolidated financial statements originally issued in Arabic. Approved/issued 12 August 2026 (note 1).
- EGX filing date on FoudaLens mirror: 13 August 2026 (the two attachments under that filing, `2026-08-13_292932_1.pdf` / `_2.pdf`, are the SEPARATE statements in English/Arabic; the consolidated English text used here is the company's own published copy of the same EGX disclosure).
- URL used: https://talaatmoustafa.com/upload/TMG%20Cons.%20FS%2030%20June%202026%20-%20English.pdf
- Local copy: `~/workspace/issue326-work/harvest/TMGH/tmgh-h1-2026-cons-official.pdf` — 59 pages.
- sha256: `cf7ae78ee67d12870879579a1cddf4c2c35d401fc3738aeec950c8826042bdb3`
- Unit: exact Egyptian pounds (LE) as printed — NOT thousands.
- Basis: CONSOLIDATED only. Income statement = cumulative six months ended 30 June 2026; balance sheet at 30 June 2026 with 31 December 2025 comparatives.
- Note: PDF pages 5–6 (statement of financial position, liabilities side, and statement of profit or loss) are scanned images with no text layer; those figures were read from the rendered pages and cross-tied to printed totals and to the text-layer notes (see cross-ties).

## Field locations and mapping decisions (H1-2026)

- **total_revenue = 30,192,000,051** — Note 32 "Revenue and cost of activity": revenue from sold units 16,967,164,530 + revenue from hotels operation 7,512,931,711 + revenue from activities with periodic yields and service activities 5,711,903,810 = printed "Total Revenue" 30,192,000,051. Same three lines on the face of the P&L (six-months column). Cross-tie: segment report total revenues 30,192,000,051; company H1-2026 reporting "consolidated revenue EGP 30.2 billion".
- **non_compliant_revenue = 3,051,097,835** — REBUILT under the issue #330 extraction rule (rule v1.0.0, `scripts/sharia_snapshot.py`): interest-type income wherever presented. Per-line classification (machine-readable in `tmgh-h1-2026-interest-income-lines.json`, stored on the snapshot as `non_compliant_revenue_breakdown`):
  | Statement line | Presented in | Amount (EGP) | Treatment |
  |---|---|---|---|
  | Credit interest – banks current accounts | Finance income (note 35) | 498,042,773 | INCLUDE — finance-income interest |
  | Time deposits interest | Finance income (note 35) | 460,275,984 | INCLUDE — finance-income interest |
  | Present value discount | Finance income (note 35) | 78,975,498 | EXCLUDE — present-value discount line inside the finance-income note; leg 1 of the rule counts the note's interest components only (see the rule's open note) |
  | Income from financial investment at amortized cost | Other income (note 33) | 2,092,779,078 | INCLUDE — amortised-cost investment yield, counted wherever presented |
  | Income from financial investments at FVPL | Other income (note 33) | 6,420,152 | EXCLUDE — fair-value gain, not interest |
  | Income from financial investments at FVOCI | Other income (note 33) | 948,774 | EXCLUDE — fair-value gain, not interest |
  | Profit from sale of FVPL investments | Other income (note 33) | 1,328,391 | EXCLUDE — disposal gain, not interest |
  - Income % = 3,051,097,835 / 30,192,000,051 = **10.11%** (was 3.17% as harvested: 958,318,757, the two finance-income interest lines only — kept on the snapshot as `non_compliant_revenue_as_harvested`). Finance income total as printed: 1,037,294,255.
  - The #326 FLAG is resolved by this rebuild: the note-33 amortised-cost yield IS in the numerator now, per the #330 rule.
- **interest_bearing_debt = 16,492,964,319** — Statement of financial position (note 25), leases EXCLUDED:
  - Loans – non-current: 13,813,502,647
  - Loans – current: 1,017,893,996
  - Credit facilities (current): 1,661,567,676
  - Excluded lease liabilities: non-current 271,690,659 + current 242,220,730.
  - Cross-tie: liquidity-risk note loans total 14,831,396,643 = 13,813,502,647 + 1,017,893,996.
- **interest_bearing_assets = 47,705,429,930**:
  - Note 12 "Time deposits and financial assets at amortized cost" (net of ECL): current 19,273,183,703 (treasury bills 17,466,034,383 + government bonds 1,324,898,138 + time deposits 482,490,800 − ECL 239,618) + non-current 9,393,854,717 (government bonds 7,522,516,547 + time deposits 1,871,551,580 − ECL 213,410) = 28,667,038,420.
  - Plus interest-bearing items inside cash & equivalents (note 21): time deposits <3 months 19,038,391,510 (treasury bills <3 months: nil at 30 Jun 2026).
- **cash_and_liquid_assets = 28,067,869,160** — the rest of cash & cash equivalents: note 21 total 47,106,260,670 (cash on hand 204,562,664 + current accounts 27,993,707,442 + time deposits <3m 19,038,391,510 − ECL 122,171,924 − bank overdrafts 8,229,022) minus the time deposits <3m bucketed into interest-bearing assets (19,038,391,510). Buckets are disjoint and sum to the cash note total. ECL and overdraft deductions are left in this residual bucket.
- **total_assets = 477,897,880,180** — face of the statement of financial position. Cross-tie: non-current 146,558,803,342 + current 331,339,076,838 = 477,897,880,180; equity 167,323,649,581 + non-current liabilities 68,764,768,633 + current liabilities 241,809,461,966 = 477,897,880,180. ✓
- **accounts_receivable = 37,776,654,990**:
  - Trade and notes receivables (note 17, net): 24,007,117,462 (trade receivable 4,738,036,143 + notes receivable 21,284,528,290 − present-value discount 1,799,491,700 − ECL 215,955,271)
  - Notes receivable for undelivered units (note 18-1): 13,769,537,528
  - Properties under development / work in progress / inventories are NOT receivables and are excluded.
- **shares_outstanding = 2,060,653,786** — issued and paid-up capital LE 20,606,537,860 at LE 10 par (note 22); equals the weighted average shares in the EPS note 38 (2,060,653,786).
- **activity: permissible** — Note 1 (group overview) and note 32 segment report: real estate development, hotels operation, and activities with periodic yields/services. Real-estate development and hospitality are permissible activities; no prohibited main activity.

## Adjacent period — FY2025 (31 Dec 2025, from the H1-2026 comparative column)
File: `tmgh-fy2025-balances.json`
- total_assets 436,222,206,712 (tie: 137,029,490,911 + 299,192,715,801; equity+L: 157,708,140,765 + 59,206,111,254 + 219,307,954,693 ✓)
- interest_bearing_debt 11,802,204,458 = loans non-current 9,737,728,639 + loans current 791,101,496 + credit facilities 1,273,374,323 (leases excluded: 274,305,998 + 46,571,846)
- interest_bearing_assets 54,994,741,404 = note 12 current 20,085,613,712 + non-current 8,978,073,992 + in-cash time deposits <3m 24,883,078,755 + in-cash treasury bills <3m 1,047,974,945
- cash_and_liquid_assets 18,915,460,637 = cash total 44,846,514,337 − 25,931,053,700 interest-bearing-in-cash
- accounts_receivable 37,641,907,272 = trade and notes receivables 21,716,321,258 + notes receivable for undelivered units 15,925,586,014

## Adjacent period — 9M-2026 (30 Sep 2026)
File: `tmgh-9m-2026-balances.json`
- Source: TMG Holding interim consolidated financial statements for the three and nine months ended 30 September 2026 (review report dated Cairo, 12 November 2026), FoudaLens/EGX filing dated 15 November 2026: https://foudalens.com/disclosures/TMGH.CA/financial_statement/2026-11-15_297746_2.pdf
- Local copy: `~/workspace/issue326-work/harvest/TMGH/tmgh-9m-2026-cons-fl.pdf`, sha256 `1ba341aff04b59e1e4e8c13663410f4142d2fff3c441d8e99645d61a2a083baa`. Unit: exact LE.
- total_assets 507,907,873,806 (face of BS; non-current 153,350,831,281 + current 354,557,042,525 ✓)
- interest_bearing_debt 17,272,906,642 — note 26: loans current 1,371,760,894 + loans non-current 13,821,438,174 + facilities 2,079,707,574 (printed total 17,272,906,642; ties to the 9M-2026 earnings release "total debt EGP 17.3 billion"). Leases excluded.
- interest_bearing_assets 45,388,205,084 = time deposits non-current (note 12) 1,870,623,452 + financial assets at amortized cost non-current (note 13) 7,471,747,160 + time deposits current 581,305,905 + financial assets at amortized cost current 14,265,071,056 + in-cash (note 22) time deposits <3m 21,189,964,249 + treasury bills <3m 9,493,262. (In the 9M presentation the old combined note 12 is split into notes 12/13; balances are the BS-face net amounts.)
- cash_and_liquid_assets 34,605,634,827 = cash & equivalents total 55,805,092,338 − 21,199,457,511 interest-bearing-in-cash.
- accounts_receivable 35,116,990,284 = trade and notes receivables 25,083,130,002 + notes receivable for undelivered units 10,033,860,282.
