# Zakat calculator benchmark — 2026-11-18

> Zakat calculation under the named published method only, computed from the inputs shown. This is not a fatwa, and not religious or investment advice.
>
> حساب زكاة وفق الطريقة المنشورة المذكورة فقط، محسوب من المدخلات المعروضة. ليس فتوى، وليس نصيحة دينية أو استثمارية.

Internal correctness gate: **15/15** stored worked cases reproduce from their stored inputs.

| Source | Kind | Verdict | Ours | Published | Delta |
|---|---|---|---:|---:|---:|
| tedawal | numeric | matched | 5000.0 | 5000.0 | 0.0 |
| askzakariya | numeric | matched | 293.875 | 293.88 | -0.005 |
| almurakib | formula | explained-divergence | — | — | — |
| almurakib | formula | explained-divergence | — | — | — |
| amal_nzf | numeric-proxy | explained-divergence | 10000.0 | 6250.0 | 3750.0 |
| zakatcalc | numeric-proxy | explained-divergence | 10000.0 | 7500.0 | 2500.0 |
| kashif | numeric | unavailable | — | — | — |
| borsa_halal | numeric | unavailable | — | — | — |

## Explanations

### tedawal — matched

Identical method and inputs: market value 200,000 SAR x 2.5%, nisab 24,650 SAR (85 g x 290) below the base.

### askzakariya — matched

Combined base 9,380 + 2,375 = 11,755 reproduces the published total exactly; 11,755 x 2.5% = 293.875 vs the published 293.88 -- the 0.005 delta is the source's own rounding to 2 decimal places, not a method difference. Judged per holding, the SPUS case alone is below the declared nisab parameter (2,375 < 6,800) and returns 0: the nisab is a wealth-level test, which is why the comparison aggregates, as the published example does.

### almurakib — explained-divergence

Almurakib's speculation base = market value + realised profits - realised losses + available cash. The shared term (market value at the zakat day, nisab 85 g gold, full Hijri hawl, 2.5%) is identical to our TRADING method. Their extra terms are holder-level cash items, not share value: our calculator takes the holding plus declared held dividends, and the owner's other cash joins his zakat on his own zakat date. Input-scope difference, not an arithmetic difference.

### almurakib — explained-divergence

Almurakib's investment formula, as published, sums market value + dividends (received and accrued) + sale cash. That contradicts the page's own note ('the full market value is NOT zakat-ed as in speculation; the dividends are') and matches neither our INVESTMENT method (AAOIFI Std 35 zakatable assets per share) nor the yield-only position. Recorded as published and flagged as an internal inconsistency in the source; not followed and not silently 'corrected'.

### amal_nzf — explained-divergence

The 25% figure is an ESTIMATION proxy for this method's base, published for when the per-share zakatable-assets figure cannot be found (NZF's own condition; AAOIFI Std 35 allows estimation for shares, art. 4/2/4). The ACME fixture carries the company's actual figures, so our calculator applies the method itself (base 400,000 -> 10,000) instead of estimating it from market value. A proxy is not the base; the delta prices the estimation error the proxy accepts.

### zakatcalc — explained-divergence

The 30% figure is an ESTIMATION proxy for this method's base, published for when the per-share zakatable-assets figure cannot be found (NZF's own condition; AAOIFI Std 35 allows estimation for shares, art. 4/2/4). The ACME fixture carries the company's actual figures, so our calculator applies the method itself (base 400,000 -> 10,000) instead of estimating it from market value. A proxy is not the base; the delta prices the estimation error the proxy accepts.

### kashif — unavailable

Kashif's trader zakat is the TRADING method family (trade goods at market value); with no published worked example, the numeric witnesses for that method in this run are Tedawal and AskZakariya.

Attempts on record:
- The kasheif.com homepage was reachable and is cached raw; its tools section names calculators, and Kashif's FAQ (read live in this series' 2026-11-17 source research) states a trader-zakat calculator is offered. The calculator itself is an interactive web tool: this runner cannot operate interactive tools, and no worked example or text formula for the trader calculator is published on the pages read -- so no like-for-like numeric comparison could be run. Recorded, not simulated.

### borsa_halal — unavailable

No published worked example exists to compare against; recorded as unavailable rather than simulated.

Attempts on record:
- GET https://www.borsahalal.com/faq via the browser reader (2026-11-18): the page returned no extractable content.
- The same FAQ was read live in this series' 2026-11-17 source research: it states the platform offers purification and zakat calculators under AAOIFI and S&P Shariah standards, and publishes no numeric thresholds and no worked zakat example.
- Not re-attempted by this freeze: two reads are on record and a third automated attempt would add no information. The calculator itself is interactive and, per the earlier research, its stock pages sit behind a login this benchmark never uses.

