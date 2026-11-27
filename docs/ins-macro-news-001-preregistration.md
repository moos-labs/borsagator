# INS-MACRO-NEWS-001 pre-registration: signal catalog, compression parameters, and rulings ledger

Status: PRE-REGISTERED on merge. Nothing in this document is built. Every parameter in section 6 is frozen once this PR merges; changing any of them afterwards is a new pre-registration, not a silent edit (Amendment-2 Ruling 3). No parameter below was tuned on outcomes; the sources are design reasoning and measured envelope throughput, not backtest results.

Provenance: Muhammad's directive (Slack C0C8EBZEF9U 1795737479.937289); design-note rulings (1795738518.965959); Amendment 1 (1795739343.851709); Amendment-1 rulings (1795739893.604769); Amendment 2 (1795739820.979279); Amendment-2 rulings (1795740749.670199). Design note and amendments delivered by email (Gmail 1a21a5283641f8c9, 1a21a6bc92911ea1, 1a21a72626d3ce7d). Panel consultation per INS-PANEL-001 at each step; theme names verified against the official GDELT GKG theme lookup (data.gdeltproject.org, 59,315 themes); ticker universe verified against evaluation/gdelt_alias_table.csv (38 tickers, 97 alias rows).

## 1. Scope

The training feed for the news-pattern learner is the full GDELT GKG stream inside a fixed, outcome-blind envelope. The envelope is the only row filter, defined once at ingest, and never touches prices or outcomes. The company-alias match is a derived signal column inside the feature matrix (a 38-dim one-hot per bag instance), never a row filter. Point-in-time: at each walk-forward cutoff the learner receives exactly the GKG rows timestamped up to that cutoff, as published; the 15:00 EET availability rule (EGX closes 14:30) binds every signal timestamp. The anomaly-only LLM routing is unaffected: the LLM classifies anomalies as features on rows and never selects which rows the learner sees.

## 2. Rulings ledger (settled, quoted from the ruling messages)

Amendment 1 (Slack 1795739893.604769):
- Event window [t-5, t-1], news strictly before the move (Groq's centered -5..+5 rejected as lookahead).
- Detection: 3-day CAR z >= 2.0 plus |CAR| >= 1.5% of 30-day realised vol.
- Holdouts: BOTH last 30 trading days per stock AND 20% of stocks per sector.
- v1 learner: Lightning's auditable bitmask dictionary (Nano's 27-combo logistic next; Groq's FIM + Bayesian deferred).
- Trust thresholds: >= 5 events per-stock pattern, >= 10 sector-pooled, >= 30 significant events for a stock's own model.
- Industry signal: ind_sig = clip(beta x theme_z, -3, 3) (the #836 clip shape) plus a 0.30 sector-exposure floor.
- Holm stands as FWER across the screen's 30 readings. Sector indices, not ETFs.

Amendment 2 (Slack 1795740749.670199):
- RULING 1: multiple-testing correction bites at the BAG-LEVEL statistic. The unit of inference is the bag; the family is the 30 readings and Holm across them applies unchanged. Per-pattern statistics are descriptive features inside the bag, not separate hypothesis tests. The guard against spurious patterns is the keep-rule harness on the bag-level statistic plus walk-forward validation and the holdouts, not a per-pattern Holm correction.
- RULING 2: v1 implements Groq's compression pipeline (dedup -> 384-d sentence embeddings -> average within (theme-family, tone-bucket) pairs -> HDBSCAN -> bag instance = centroid + count + mean tone + 38-dim alias one-hot). Singleton preservation is part of the implementation: HDBSCAN noise points are kept as singleton bags, so aggressive clustering cannot drop the marginal article. Cohere's, Nano's and Lightning's pipelines are deferred as valid alternatives.
- RULING 3: compression parameters are frozen and pre-registered here before any pattern mining, as part of the same pre-registration document as the signal catalog. No tuning on outcomes; parameter changes require a new pre-registration.
- Accepted as stated: outcome-blind envelope is the only row filter; point-in-time snapshots; anomaly-only LLM routing unaffected; the dictionary learner composes with MIL (the ~12 binary signal columns are computed per bag instance; the pattern hash accumulates over bag instances in [t-5, t-1]).

Also settled earlier (Moos ruling 2026-11-26 21:39, Slack 1795721991.717959, applied to the harness references below): coverage-CI width cap absolute <= 0.15 with no relaxation; effective-n report-only; bootstrap resamples whole cutoff clusters; Holm across the 30 readings; MIN_CUTOFFS raise-to-10 applies to future KEEP verdicts only.

## 3. Signal catalog (frozen v1)

Learning framing: multiple-instance learning with weak supervision over bags of pre-move news. Bag = the compressed instances in the look-back before a test point; bag label = the ruled abnormal-move indicator (3-day CAR z >= 2.0 plus the vol floor) in the following window. The label is generated after the bag is formed and never filters rows.

The dictionary learner (Amendment-1 ruling: Lightning's bitmask dictionary, 4096 possible patterns) computes the following 12 binary signal columns per bag instance. Columns 1, 2, 3, 6 and 7 are named in the ruled composition line ("theme spike present, alias one-hot, sector flag, z-spike flag, LLM anomaly"); columns 4, 5 and 8-12 complete the ~12-column bitmask and are specified by this document for review. On merge all twelve are frozen.

1. alias_present: the instance's 38-dim alias one-hot is non-zero (at least one of the 38 universe companies is named in the instance's source rows). Source: Amendment-2 ruling 2 / composition line.
2. sector_flag: the instance's dominant theme family maps to a sector in the exposure map (design note section c) with sector exposure >= the ruled 0.30 floor. Source: composition line + Amendment-1 floor.
3. theme_spike: the dominant theme family's daily volume z-score vs its trailing 30-day mean/std exceeds 2. Source: composition line; design note stage 2.
4. tone_negative: the instance's mean tone falls in bucket T1 or T2 (mean tone <= -1). Source: this document (completes the bitmask).
5. tone_positive: the instance's mean tone falls in bucket T4 or T5 (mean tone >= +1). Source: this document.
6. count_spike: the instance's (theme-family, tone-bucket) group count z-score vs its trailing 30-day mean/std exceeds 2. Aggregation, specified by this document: an instance built from several (theme-family, tone-bucket) groups takes the MAXIMUM of its member groups' z-scores, so count_spike is set when any member group spikes; a singleton has one group. Undefined member z-scores (for example too little trailing history) are skipped in the MAXIMUM; if a defined member exceeds 2 the signal is set even when another member is undefined; if ALL member scores are undefined, count_spike is not set (no evidence of a spike). These undefined-score rules are specified by this document. Source: composition line ("z-spike flag") + this document's aggregation rule.
7. llm_anomaly: the stage-3 LLM flagged at least one of the instance's source rows as anomalous (|z| > 2 tail routing). Source: composition line; design note stage 3.
8. llm_severity_high: the LLM severity score on flagged rows in the instance is >= 4 (of 1-5). Source: this document; design note stage 3 output schema.
9. geo_core: the instance's source rows carry a V2Locations hit in the core geo set (Egypt, Suez, Red Sea). Source: this document; design note stage 1.
10. singleton: the instance is a preserved singleton (an HDBSCAN noise point kept as its own bag instance). Source: this document; Amendment-2 ruling 2 singleton preservation.
11. large_instance: the instance's article count is >= 10. Source: this document.
12. multi_family: the instance's source rows span >= 2 theme families. Source: this document.

Pattern hash accumulates over the bag instances in [t-5, t-1]; per-stock activation at count >= 5, sector-pooled >= 10, own model at >= 30 significant events (ruled thresholds).

## 4. Compression pipeline v1 (ruled: Groq's pipeline, with singleton preservation)

Envelope throughput feeding it (measured by the shard agents after the #846 restart): ~50-90 envelope rows per 15-minute file, 192 files/day across both streams, so ~9,600-17,300 rows/day enter the training feed.

Stage 1, dedup (outcome-blind):
- Canonical URL hash + first-seen UTC across both GKG streams; later-language duplicates counted once (design note section e).
- Embedding dedup: cosine > 0.85 within a 24h window (design note stage 2).

Stage 2, embeddings:
- Model: bge-small-en-v1.5, 384 dimensions, via fastembed/onnx, CPU (design note stage 2, confirmed by Amendment-2 ruling 2). Vectors are L2-normalized, so Euclidean distance on them is monotone in cosine distance.

Stage 3, grouping:
- Average the normalized embeddings within (theme-family, tone-bucket) pairs, then re-normalize each group average to unit L2 norm (specified by this document: a mean of unit vectors is not unit length, and Stage 4 needs unit vectors for Euclidean to be cosine-equivalent). Expected ~200 groups/day (Groq's estimate, descriptive). Theme families are the verified list in section 5; tone buckets are the boundaries in section 6.

Stage 4, clustering:
- HDBSCAN over the group-average vectors. Frozen parameters: min_cluster_size = 5; min_samples = 1; metric = euclidean on the L2-normalized vectors (equivalent to cosine); cluster_selection_method = 'eom'; cluster_selection_epsilon = 0.0. Noise points are kept as singleton bags (ruled singleton preservation). Expected ~120 clusters/day (Groq's estimate, descriptive, not a target to tune toward).
- min_cluster_size, min_samples, the metric, cluster_selection_method and cluster_selection_epsilon are specified by this document (the rulings fixed the pipeline shape, not the numeric HDBSCAN settings); they are frozen on merge.

Stage 5, bag instance:
- Fields: centroid (384-d: the mean of the cluster's unit-length group vectors, re-normalized to unit L2 norm; the re-normalization is specified by this document, as in Stage 3) + count (articles in the instance) + mean tone (mean of the GDELT tone field over the instance's rows) + 38-dim alias one-hot (one bit per ticker in evaluation/gdelt_alias_table.csv). ~424 dims total. Source: Amendment-2 ruling 2, verbatim field list.
- Daily bag size: ~120 instances/day x ~424 dims expected (30-day walk-forward bag ~3,600 instances). The storage dtype is set at implementation, and the real size is measured and reported; no byte figure and no dtype is frozen here (specified by this document). Expected size, not a cap.

## 5. Theme-family list (verified against the official GDELT lookup)

The geo + theme-family envelope is the only row filter. Geo: V2Locations hits for Egypt / Suez / Red Sea / MENA. Theme families (real names from the official 59,315-theme lookup, archive usage counts in parentheses):

- Monetary/FX: ECON_CENTRALBANK (10.7M), ECON_INFLATION (10.4M), ECON_INTEREST_RATES (10.5M), ECON_CURRENCY_EXCHANGE_RATE (9.6M), ECON_CURRENCY_RESERVES (652k), EPU_POLICY_MONETARY_POLICY (2.0M), EPU_POLICY_CENTRAL_BANK (8.0M), EPU_CATS_SOVEREIGN_DEBT_CURRENCY_CRISES (4.3M), ECON_DEVELOPMENTORGS_INTERNATIONAL_MONETARY_FUND (2.1M), ECON_SUBSIDIES (5.8M), ECON_BUDGET_DEFICIT (4.5M), ECON_TAXATION (44M).
- Energy: ENV_OIL (35M), ECON_OILPRICE (9.7M), ENV_NATURALGAS (5.5M), ECON_NATGASPRICE (453k), ECON_GASOLINEPRICE (1.4M), WB_1627_ENERGY_SUBSIDIES (171k).
- Wheat/food: TAX_FOODSTAPLES_WHEAT (3.1M), TAX_FOODSTAPLES_GRAIN (3.5M), FOOD_SECURITY, AGRICULTURE.
- Red Sea/Suez/shipping: MARITIME (55M), MARITIME_INCIDENT (29M), MARITIME_PIRACY (2.5M), PIRACY (2.4M), MANMADE_DISASTER_MARITIME_DISASTER (18k). No SUEZ-specific theme exists; Suez/Red Sea is caught via the geo fields plus these families.
- Tourism: TOURISM (34.7M), WB_825_TOURISM (18.9M).
- Conflict/security: ARMEDCONFLICT, MILITARY, TERROR, BLOCKADE, POLITICAL_TURMOIL (7.8M), PROTEST (58M), STRIKE (9.4M), ELECTION (85M).
- Health: HEALTH_PANDEMIC (28M), WB_2167_PANDEMICS (46.6M), TAX_DISEASE_EPIDEMIC (10.7M).
- Disasters: NATURAL_DISASTER (72M), NATURAL_DISASTER_EARTHQUAKE (7.1M), NATURAL_DISASTER_FLOOD (6.5M).
- Policy umbrella (count features, not row filters): EPU_POLICY (385M), WB_696_PUBLIC_SECTOR_MANAGEMENT (277M).

The sector exposure map (38 tickers to sectors and driving families) is the verified table in the design note, section c; the universe is evaluation/gdelt_alias_table.csv.

## 6. Frozen parameter table

| Parameter | Value | Source |
| --- | --- | --- |
| Row filter (envelope) | geo (V2Locations Egypt/Suez/Red Sea/MENA) + theme-family list (section 5) | ruled: outcome-blind envelope, accepted as stated |
| Tone buckets | T1: tone <= -3; T2: -3 < tone <= -1; T3: -1 < tone < 1; T4: 1 <= tone < 3; T5: tone >= 3 (GDELT V2Tone field 1; filter already parses it, scripts/gdelt_gkg_filter.py:181-183,204,212) | specified by this document, frozen on merge |
| Embedding model | bge-small-en-v1.5, 384-d, fastembed/onnx, CPU, L2-normalized | ruled (Amendment-2 ruling 2; design note stage 2) |
| URL dedup | canonical URL hash + first-seen UTC, both streams | design note section e (accepted design) |
| Embedding dedup | cosine > 0.85 within 24h | design note stage 2 (accepted design) |
| Grouping | average within (theme-family, tone-bucket) pairs, each average re-normalized to unit L2 norm | averaging ruled (Amendment-2 ruling 2); re-normalization specified by this document, frozen on merge |
| HDBSCAN | min_cluster_size=5, min_samples=1, euclidean on L2-normalized vectors, cluster_selection_method='eom', cluster_selection_epsilon=0.0 | specified by this document, frozen on merge |
| Singleton preservation | HDBSCAN noise points kept as singleton bags | ruled (Amendment-2 ruling 2) |
| Bag-instance fields | centroid (384-d, unit L2 norm) + count + mean tone + 38-dim alias one-hot | ruled (Amendment-2 ruling 2, verbatim); centroid re-normalization specified by this document |
| Daily bag size | ~120 instances expected | ruled estimate (descriptive, not a cap) |
| Signal catalog | 12 binary columns per bag instance (section 3); count_spike takes the max z over an instance's member groups | ruled composition line + this document's completion and count_spike aggregation |
| Event window | [t-5, t-1] | ruled (Amendment 1) |
| Detection | 3-day CAR z >= 2.0 plus \|CAR\| >= 1.5% of 30-day realised vol | ruled (Amendment 1) |
| Availability cutoff | 15:00 EET on T for day T+1 features; lag sensitivity 0/1/2 days checked before fixing the lag | design note section d (accepted design) |
| Multiple testing | Holm (FWER) across the 30 readings, on the bag-level statistic | ruled (Amendment-2 ruling 1) |
| Keep-rule harness | RangeSkill cutoff-clustered CI lower bound > 0; coverage CI overlaps [0.75, 0.85] with the absolute 0.15 width cap; whole-cutoff-cluster bootstrap; MIN_ROWS=30, MIN_TICKERS=5, MIN_CUTOFFS=2 (raise-to-10 future-only) | settled rulings 2026-11-26 + Amendment-2 ruling 1 |
| Holdouts | last 30 trading days per stock AND 20% of stocks per sector | ruled (Amendment 1) |
| Trust thresholds | >= 5 per-stock pattern, >= 10 sector-pooled, >= 30 significant events for own model | ruled (Amendment 1) |
| Industry signal | ind_sig = clip(beta x theme_z, -3, 3) + 0.30 sector-exposure floor; sector indices, not ETFs | ruled (Amendment 1) |
| LLM routing | anomaly tail only (Groq llama-3.1-8b-instant primary, Gemini Flash fallback); classifies rows as features, never selects rows | design note stage 3 (accepted design); free-tier limits UNRESOLVED, verify at build time |

## 7. No-tuning clause

These parameters are frozen before any pattern mining. If any parameter needs to change, the change is a new pre-registration document, reviewed before implementation. No silent edits. Descriptive expectations (groups/day, clusters/day, bag size) are recorded so the implementation can be checked against them; a deviation is a finding to report, not a parameter to tune.

## 8. Verification statement

Prepared by Ins under INS-PANEL-001. Every load-bearing claim above traces to a ruling message (Slack timestamps in the provenance header), the repo (scripts/gdelt_gkg_filter.py; evaluation/gdelt_alias_table.csv; PR #836 clip shape), the official GDELT GKG theme lookup, or a measured shard-agent throughput figure. Items not fixed by any ruling (tone-bucket boundaries, HDBSCAN numeric parameters, dictionary columns 4, 5, 8-12, the count_spike aggregation rule, and the unit-norm re-normalization in Stages 3 and 5) are marked as specified by this document and enter review as new frozen values. Panel-fabricated theme names and tickers from the design round were excluded; the lists in section 5 are the verified ones. LLM free-tier rate limits remain UNRESOLVED pending verification at build time.
