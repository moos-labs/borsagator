# Round 147 s.6: crypto conversion-cost sourcing (INS-IMPROVE-161), fee table, sampler, collection plan

Descriptive sourcing only. No conversion edge is computed. Cost cells in the s.6 matrix stay EMPTY, reason "cost not sourced", until the fee schedule is complete for the route used AND the spread distribution below has landed. Source of the request: Moos Slack 1795872813.532359 (read).

## 1. Taker-fee schedules (dated 2026-11-28 13:34 UTC; machine-readable copy: evaluation/crypto_fee_schedules.json)
Kraken Pro spot (https://www.kraken.com/pro/fees, read 2026-11-28): taker 0.80% at Tier 1 ($0+ 30-day spot volume), 0.60% Tier 2 ($2.5K+), 0.38% Tier 3 ($10K+), 0.35% Tier 4 ($25K+), 0.30% Tier 5 ($50K+), down to 0.05% at Tier 17. Maker is 0.40% at Tier 1. All 17 tiers are in the JSON.
Coinbase Advanced spot (blog dated 2026-09-16, https://www.coinbase.com/blog/were-lowering-fees-for-many-active-traders-on-coinbase-advanced, read 2026-11-28): US entry-level tier 0.50% maker and 0.90% taker; EU/UK 0.25%/0.50%; Brazil, India and other international 0.09%/0.10%; top VIP8 tier 0bps/2bps. Advanced tiers start at $10,000 of qualifying volume.
NOT OBTAINED for Coinbase: the full tier table, and the rate below $10,000 volume (what a small account would pay). The help page (https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees) tells the user to sign in, and https://www.coinbase.com/advanced-fees returned no content. No number is guessed. The user's tier and jurisdiction are unverified for both venues.
Not checked for either venue: convenience or instant-buy fees and spread markups, stablecoin and FX pair schedules, deposit and withdrawal fees, and any EGP on/off-ramp. A taker fee plus a top-of-book spread is still not an executable cost (size impact, and the route to EGP are outside it).

## 2. Spread sampler
scripts/sample_crypto_spreads.py (stdlib). One run appends one JSONL row per venue and pair (Coinbase Exchange and Kraken, BTC-USD and ETH-USD) to evaluation/crypto_spread_samples.jsonl: ts_utc, venue, pair, bid, ask, mid, spread_bp = (ask-bid)/mid x 1e4, venue_time (Coinbase only). A fetch failure, a non-positive quote or a crossed book is written as a row with "error" and no spread; nothing is dropped or imputed. First snapshot taken 2026-11-28T13:34:35Z (4 rows).
Summary: `--summarise PATH` prints counts per series and prints spread percentiles (5, 25, 50, 75, 95, 99, nearest rank) only when a series holds at least 168 valid samples; below that it prints counts only.

## 3. Seven-day collection plan
- Cadence: one snapshot per hour for at least 7 days (168 hourly snapshots; 672 rows over 4 series), appended to the same JSONL file. The first sample is the one above; the hourly clock runs from there.
- Runner: NOT arranged by this change. Someone must run the sampler hourly (a scheduled job); until a runner exists only the first snapshot exists. This is an open item for Moos and the parent.
- Gaps: a missed hour is a missing sample, listed by timestamp in the summary run, never filled.
- Report at the end: per venue and pair, n valid, n error, first and last timestamp, and the spread percentiles above in bp. Report the Coinbase and Kraken series separately; do not pool venues.
- Still needed before any cost cell is filled: the Coinbase sub-$10K rate and the user's actual tier at each venue, the cost of the EGP route, and a decision on which venue and order type the route uses. No edge until then.
