# GDELT shard outputs: transfer-route options (options only, no decision)

INS-IMPROVE-001 round 25 item 3 (brief: Muhammad's Slack message
1795738752.880149). The route is Muhammad's call. This lists what each route
can carry, what is verified, and what is not.

## How big are the outputs

Verified inputs: the pilot (docs/gdelt-gkg-pilot-2024-05.md) wrote 112,099
rows to a 13 MB parquet, about 116 bytes per row compressed. Progress
figures from the shard agents (relayed, not read by me): rows per file
processed are about 14.0 (2020: 27,200 / 1,944), 17.0 (2021: 40,497 /
2,376), 15.8 (2025: 32,144 / 2,040), 16.4 (2026: 26,704 / 1,631).

Estimate per yearly shard, clearly an estimate: 63,000 to 69,000 files x
14 to 17 rows = about 0.9 to 1.2 million rows. Eight shards: about 7 to 9
million rows.
- Parquet from `--finalize` at the pilot ratio: roughly 0.10 to 0.14 GB per
  shard, about 1 GB total. The pilot ratio came from a different row mix
  (the new run applies the six fixes), so treat it as order of magnitude.
- Raw `matches.jsonl`: NOT measured. At 0.5 to 1 KB per row it would be 0.5
  to 1.2 GB per shard. `du -sh out/matches.jsonl` in each shard settles it in
  one command.

## Routes

| Route | Fits | Verified facts | Not verified |
|---|---|---|---|
| Google Drive upload, ins.sherbeeny@gmail.com (the shard 2020 folder `gdelt-full-shard-2020` already exists) | parquet and jsonl | The account has a 15 GiB quota (16,106,127,360 bytes) with 17.8 MB used. The upload action takes a file path. | The upload action's maximum file size; a 0.1 GB parquet should be tried first. Whether every shard environment can upload from its output path. |
| GitHub release assets on moos-labs/borsagator | parquet and jsonl | Each asset must be under 2 GiB; no limit on total release size or bandwidth (docs.github.com, about-releases). | Whether each shard environment has a `gh` or curl route; some shard agents report no git or shell action. Needs the vault GitHub credential in each shard. |
| Commit parquet to a git branch | parquet only, split | GitHub blocks files over 100 MiB and warns over 50 MiB (docs.github.com, about-large-files). Quarterly parquet parts would be about 25 to 35 MB. | It bloats repo history permanently; not recommended unless the data is small and stable. |
| Gmail attachment | no | Personal Gmail limit is 25 MB (support.google.com/mail/answer/6584). Smaller than one shard. | n/a |
| Leave in place and transfer later | any | Nothing moves. | Shard sandboxes restart from saved files (seen at 1:50 and 2:19); no durability guarantee is documented, so a lost box means a shard re-scan of about a day. |

## Cost
All routes are free at these sizes. Drive counts against the Ins account's
15 GiB; a release counts against nothing. Bandwidth: shards already pull
about 56 MB/s aggregate from data.gdeltproject.org (shard agents'
estimate); uploads of about 1 GB total are small by comparison.

## What I would check first if a route is chosen
1. Per shard: `du -sh` of out/ and the finalized parquet.
2. One 0.1 GB parquet through the chosen route, checksummed on both ends.
3. Whether each shard environment can reach the route at all.
