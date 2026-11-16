# Cairo Poultry (EGX: POUL) — Fundamental Ratios

Source data: `data/poul_statements.csv` — figures extracted **only** from the verified 10-Nov-2026 buy-decision research (company earnings releases, EGX disclosures, post-merger special-purpose statements). No figure was invented; gaps in the CSV are gaps in the verified record.

## Computation path

- Headline ratios: **computed directly with pandas/plain Python from the verified CSV** (traceable line-by-line).
- FinanceToolkit manual-statements API attempt: **ok**. Its raw outcome is preserved in `ratios.json` under `financetoolkit_attempt`.

## Computed ratios

### FY2025 (year to 31 Dec 2025)

| Ratio | Value | Basis |
|---|---|---|
| gross_margin_pct | 29.12 | gross profit (release definition) / revenue |
| ebitda_margin_pct | 19.58 | adjusted EBITDA / revenue |
| operating_margin_vendor_pct | 16.86 | vendor operating income / revenue |
| net_margin_total_pct | 18.26 | total NPAT / revenue |
| net_margin_special_purpose_pct | 18.53 | special-purpose NPAT / consolidated revenue |
| roe_pct | 39.37 | total NPAT / total equity at 31-Dec-2025 (period-end, no average available) |
| roe_special_purpose_pct | 39.25 | special-purpose NPAT / special-purpose equity at end-2025 |
| roa_pct | 27.00 | total NPAT / total assets at 31-Dec-2025 (period-end) |
| asset_turnover_x | 1.48 | revenue / total assets (period-end) |
| equity_multiplier_x | 1.46 | total assets / total equity (period-end) |
| debt_to_equity_x | 0.03 | total debt / total equity at 31-Dec-2025 |
| net_cash_EGPm | 4,299.00 | cash & investments - total debt at 31-Dec-2025 |
| ocf_margin_pct | 17.94 | operating cash flow / revenue |
| capex_to_revenue_pct | 9.81 | capex / revenue |
| fcf_margin_pct | 8.13 | free cash flow / revenue |
| fcf_conversion_pct | 44.50 | free cash flow / total NPAT |
| net_interest_income_pct_of_npat | 23.39 | net interest income / total NPAT |
| asset_sale_gains_pct_of_npat | 5.48 | gains on sale of assets / total NPAT |
| eps_post_merger_shares_consol_EGP | 1.62 | total NPAT / 1,789,351,397 post-merger shares |
| eps_post_merger_shares_special_EGP | 1.64 | special-purpose NPAT / post-merger shares |
| bvps_post_merger_consol_EGP | 4.10 | consolidated equity end-2025 / post-merger shares |
| bvps_post_merger_special_EGP | 4.17 | special-purpose equity end-2025 / post-merger shares |
| net_cash_per_share_end2025_EGP | 2.40 | net cash end-2025 / post-merger shares |
| dupont_roe_check_pct | 39.35 | net margin x asset turnover x equity multiplier (should equal roe_pct) |

### FY2024 (partial — see coverage)

| Ratio | Value | Basis |
|---|---|---|
| operating_margin_vendor_pct | 17.09 | vendor operating income / revenue |
| net_margin_eps_basis_pct | 14.81 | EPS-basis net income (after appropriations) / revenue |
| fcf_margin_pct | 15.09 | free cash flow / revenue |

### H1 2026 (six months to 30 Jun 2026)

| Ratio | Value | Basis |
|---|---|---|
| gross_margin_pct | 23.83 | release gross profit / revenue (6 months) |
| ebitda_margin_pct | 13.76 | adjusted EBITDA / revenue (6 months) |
| operating_margin_pct | 11.77 | release operating profit / revenue (6 months) |
| net_margin_pct | 16.08 | total NPAT / revenue (6 months) |
| debt_to_equity_x | 0.04 | total debt / total equity at 30-Jun-2026 |
| net_cash_EGPm | 3,921.00 | cash & investments - total debt at 30-Jun-2026 (research rounds this to 3,922 from unrounded inputs) |
| net_cash_per_share_EGP | 2.19 | net cash 30-Jun-2026 / post-merger shares |
| net_interest_income_pct_of_npat | 32.04 | net interest income / total NPAT (6 months) |

### FY2025 dividend (coupon #42, paid 18 Nov 2026)

| Ratio | Value | Basis |
|---|---|---|
| payout_vs_consolidated_npat_pct | 117.64 | EGP 3,399.77m dividend / FY2025 consolidated NPAT 2,890 |
| payout_vs_special_purpose_npat_pct | 115.95 | dividend / FY2025 special-purpose NPAT 2,932 |
| dividend_pct_of_distributable_pool | 67.70 | dividend / special-purpose distributable pool 5,022 |
| dividend_yield_at_reference_price_pct | 19.00 | 1.90 / 10.00 reference price (one-off, non-recurring) |

### Valuation snapshot at EGP 10.00 reference price (research price, not live)

| Ratio | Value | Basis |
|---|---|---|
| market_cap_EGPm | 17,893.50 | 10.00 x 1,789,351,397 shares |
| pe_consolidated_npat_x | 6.19 | price / EPS on post-merger shares (consolidated NPAT) |
| pe_special_purpose_npat_x | 6.10 | price / EPS on post-merger shares (special-purpose NPAT) |
| pb_special_purpose_x | 2.40 | price / special-purpose BVPS end-2025 |
| pb_consolidated_x | 2.44 | price / consolidated BVPS end-2025 |
| ev_ebitda_fy2025_x | 4.51 | (market cap - net cash Jun-2026) / FY2025 adjusted EBITDA |

## Coverage — standard ratios that could NOT be computed

| Ratio | Missing line item / blocker |
|---|---|
| current_ratio / quick_ratio / cash_ratio | Current assets and current liabilities are not split out in any verified source figure. |
| interest_coverage_ratio | Only NET interest income (+676 FY25) is disclosed in the sources; gross interest expense is not verified. |
| inventory_turnover / receivables_turnover / payables_turnover / cash_conversion_cycle | Inventory, receivables and payables balances do not appear in the verified sources. |
| return_on_invested_capital (ROIC) | NOPAT cannot be derived: the effective tax charge is not verified (pre-tax profit is given only approximately, ~EGP 3,667m). |
| effective_tax_rate | Pre-tax profit is stated only approximately in the sources. |
| altman_z_score / piotroski_f_score | Require full balance-sheet detail (working capital, current items) and, for Piotroski, two full years of balance sheets; not available in verified form. |
| roe / roa FY2024 | FY2024 total equity and total assets are not verified (special-purpose FY2024 equity was not disclosed in the source). |
| roa H1_2026 | Total assets at 30-Jun-2026 are not stated in the sources (only total liabilities and equity). |
| dividend_payout_ratio FY2024 | No FY2024 dividend per share appears in the extracted verified sources. |
| dupont FY2024 / H1_2026 | Needs total assets and equity for the same period-end; missing for FY2024 and (assets) for Jun-2026. |

## Caveats

- Balance-sheet ratios use **period-end** balances (no averaged balances exist in the verified sources), so ROE/ROA are point-in-time variants.
- Gross profit and EBITDA follow the **company earnings-release definitions**; a vendor definition (COGS incl. depreciation) gives lower gross profit (FY25: 3,338 vs 4,609).
- FY2024 is thin: total NPAT is reported only as a conflicting range (2,387–2,420), and FY2024 equity/assets are unverified, so FY2024 return ratios are blocked rather than estimated.
- The 19.0% dividend yield is a **one-off** return of accumulated retained earnings (payout >100% of FY2025 profit) and is not repeatable at this size.
