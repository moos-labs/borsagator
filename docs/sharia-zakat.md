# Zakat calculator (issue #173)

Borsagator's zakat calculator computes zakat al-mal on **one
share holding** under a **named, published method**, and
itemises every step: the inputs with their sources and dates,
the base and its components, the hawl and nisab tests, the
rate, and the amount.

> **Framing (binding).** Every output is a calculation under
> the named published method only — never a fatwa and never
> religious or investment advice.
>
> حساب زكاة وفق الطريقة المنشورة المذكورة فقط، محسوب من
> المدخلات المعروضة. ليس فتوى، وليس نصيحة دينية أو
> استثمارية.
>
> The framing lines and the method statement ship in English
> and Arabic at the top level of every result and on every
> benchmark row; final wording is reviewed under issue #77.
> **No user-facing accuracy claim ships off the back of the
> benchmark** (issues #77 / #79 rules).

## Pieces

| Piece | Path |
|---|---|
| Calculator + CLI | `scripts/sharia_zakat.py` |
| Method declarations (data, like the rule sets) | `scripts/sharia_zakat_methods/trading.json`, `scripts/sharia_zakat_methods/investment.json` |
| Stored worked cases (inputs + hand-derived expectations) | `scripts/sharia_zakat_fixtures/worked_cases.json` |
| Calculator tests | `scripts/test_sharia_zakat.py` (25 checks) |
| Benchmark runner (freeze + score) | `scripts/sharia_zakat_benchmark.py` |
| Benchmark tests | `scripts/test_sharia_zakat_benchmark.py` (6 checks) |
| Frozen source snapshots | `sharia/zakat-benchmark/sources/*.json` |
| Raw fetched pages (parser inputs) | `sharia/zakat-benchmark/raw/` |
| Benchmark reports | `sharia/zakat-benchmark/zakat-benchmark-<date>.json` / `.md` |

## The two methods

**TRADING — trade goods (market value).** Shares bought for
trading are ʿurūḍ al-tijāra: zakat at the method's rate on
the **market value at the valuation date** (the end of the
hawl), whatever was paid. Cash dividends received during the
hawl and still held are the holder's money and join the base
**when the holder declares them** — the calculator never
estimates unspent dividends it was not given. Sources:
IslamWeb fatwa 84386 (the Fiqh Assembly / Council of Senior
Scholars position), Dar Al-Ifta Egypt fatwa 2110, Kashif's
trader-zakat calculator, and the Tedawal / AskZakariya
worked examples. Almurakib's speculation formula adds
realised profits and available trading cash and deducts
realised losses — holder-level cash items, recorded as an
input-scope difference in the benchmark, not an arithmetic
one.

**INVESTMENT — share of the company's zakatable assets
(AAOIFI Std 35).** Shares held for long-term investment and
dividends are **not** zakat-able on market value under this
method. Following AAOIFI Sharia Standard No. 35 (Zakah),
zakat falls on the holder's share of the company's zakatable
assets — its cash, money owed to it (receivables) and stock
for sale — per share × shares held. Fixed assets are
excluded. The per-share base is computed from the screening
data model (issue #168): `(cash_and_liquid_assets +
accounts_receivable) / shares_outstanding`. Paid-out
dividends are **not** added to the share base: they are the
holder's cash, zakat-able with his money at his zakat date,
and retained earnings already sit inside the company's
zakatable assets — adding them would double-count. A
dividends figure passed under this method is reported as
excluded, with the rule, never silently dropped.

**Documented limitation (declared in the method file, not
hidden):** AAOIFI Std 35's zakatable assets also include
inventory, and company-level zakat bases deduct liabilities
due. The screening data model carries neither field yet, so
the computed base sums the components the model carries and
names the missing ones. Live wiring rides on issues #78 /
#110.

**Documented alternatives (recorded in the method files,
never blended into a number):**

- The **yield-only position** (majority of contemporary
  scholars; IslamWeb 84386, IslamQA 69912): where a
  company's assets are permanent, no zakat on the share
  itself — zakat on dividends received, 2.5% after a hawl
  from receipt. Not implemented as a selectable method in
  v1; the issue scopes intent (b) to the zakatable-assets
  method.
- The **estimation proxies**: NZF's 25% of market value and
  ZakatCalc's 30% (AAOIFI proxy), published for when the
  per-share figure cannot be found (Std 35 allows
  estimation for shares, art. 4/2/4). A proxy is an estimate
  of this method's base, not the base — where the figures
  exist the calculator uses them, and where they do not it
  returns `insufficient-data` rather than estimating. The
  benchmark prices the difference.
- **Almurakib's investment formula** as published sums
  market value + dividends + sale cash, which contradicts
  its own page's note and matches neither method above;
  recorded as published, flagged as an internal
  inconsistency in the source.

## Parameters — all explicit, none hidden

| Parameter | Rule |
|---|---|
| Rate | 2.5% on a lunar hawl; 2.577% on a Gregorian hawl (AAOIFI Std 35 raises the rate on the longer year — as cited by Amal Invest). The calendar is a case input, defaulting to lunar and echoed on the result. |
| Hawl | 354 days (lunar) / 365 (Gregorian), measured on the holding by default. A case may instead **declare** the hawl complete with a note — the published basis for shares bought with money whose hawl is already running (IslamWeb 69087). |
| Nisab | 85 g gold / 595 g silver (AAOIFI Std 35), grams overridable as an explicit input (e.g. NZF's 87.48 g variant — a test flips the exact-nisab case with it). The metal **price per gram is always an input** with source + date; the calculator holds no price. |
| Nisab test | Base **below** nisab → zakat 0, status `below-nisab`, reason stated. Base **exactly at** nisab → due. No nisab input → the amount is computed but the status is `nisab-not-provided`: published guidance judges nisab on all of the owner's zakatable wealth together, so the calculator does not fake a per-holding determination. |
| Price per share | An input with source + date (TRADING). The calculator does no market lookups. |
| Company figures | The snapshot's financials (INVESTMENT). Missing fields → `insufficient-data` with every missing input named; zakat is `null`, never a guessed figure. |

Statuses: `due` · `below-nisab` · `hawl-not-complete` ·
`insufficient-data` · `nisab-not-provided`.

## Run it

```bash
python3 scripts/sharia_zakat.py calculate \
    --ticker POUL.CA --method TRADING --shares 100 \
    --buy 2025-11-20 --valuation 2026-11-18 \
    --price 8.02 --price-source "ex-date close 2026-11-16" \
    --nisab-basis gold --nisab-price-per-gram 4000 \
    --currency EGP
python3 scripts/test_sharia_zakat.py
python3 scripts/sharia_zakat_benchmark.py freeze   # network
python3 scripts/sharia_zakat_benchmark.py score    # offline
python3 scripts/test_sharia_zakat_benchmark.py
```

## First benchmark run (2026-11-18) — what it measured

Internal gate: **15/15** stored worked cases reproduce from
their stored inputs.

| Source | Result |
|---|---|
| Tedawal (worked example) | **Matched exactly** — ours 5,000 SAR vs published 5,000 SAR, delta 0 |
| AskZakariya (worked example) | **Matched** — combined base 11,755 reproduces the published total; ours 293.875 vs published 293.88, delta −0.005 = the source's own 2-dp rounding |
| Almurakib (formulas) | Two **explained divergences** (trading: input scope; investment: their formula contradicts their own note — flagged, not followed) |
| NZF 25% proxy (via Amal Invest) | **Explained divergence** — proxy gives 6,250 on the ACME case vs 10,000 from the company's actual figures; the proxy is an estimation fallback, priced here |
| ZakatCalc 30% proxy | **Explained divergence** — 7,500 vs 10,000, same explanation |
| Kashif trader-zakat calculator | **Unavailable** — interactive tool, no published worked example or text formula on the pages read; attempts on record in the snapshot |
| Borsa Halal zakat calculator | **Unavailable** — FAQ fetch returned no extractable content in this run; the 2026-11-17 verified research read it live: calculators are offered, but no worked zakat example or numeric method is published there |

No comparison is a defect and none is left unexplained.
