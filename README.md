# 🐊 Borsagator

**The aggregator for the moos-labs stock-analysis fleet.**

One job in — every tool dispatched — one merged digest out.

Borsagator is a central orchestrator repo. The fleet is ~36 public
single-tool runner repos under [moos-labs](https://github.com/moos-labs)
(vectorbt, TradingAgents, FinBERT, Kronos, Qlib, …), each driven by a
`COMMANDS` Actions variable and a `workflow_dispatch` workflow that uploads a
`results` artifact. Borsagator drives them all at once:

1. You set a job — the `JOB` variable here, or the workflow's job input:
   `sweep POUL.CA` (all phase-1 tools) or `run tradingagents POUL.CA` (one tool).
2. Borsagator sets each selected child's `COMMANDS` from
   [`registry/tools.json`](registry/tools.json) — with the ticker and date
   substituted — and appends a small emitter that makes the child write a
   standard `results/summary.json` digest of its own run.
3. It dispatches each child, waits, downloads the `results` artifacts, and
   **restores every child's original `COMMANDS`** afterwards.
4. The per-tool summaries are merged into one digest — a `digest` artifact
   plus a GitHub issue in this repo — with each tool's verdict preserved.
   Borsagator never averages the tools into one score; disagreements stay
   visible.

## Security model

Borsagator's credential is a **GitHub App owned by the moos-labs org**,
installed on **selected repositories only** (this repo + the fleet runners —
never org-wide, because the org hosts other projects), with exactly two
repository permissions:

- **Actions — read & write** (dispatch workflows, read runs, download artifacts)
- **Actions variables — read & write** (set and restore `COMMANDS`)

No contents, no secrets, no administration. Each workflow run mints a fresh
one-hour installation token from the app credentials; the child repos' own
API keys stay in org secrets, a plane this app never touches.

## Jobs

| Job | Meaning |
|---|---|
| `sweep <ticker>` | All active tools (the whole fleet — long) |
| `sweep-lite <ticker>` | All active tools except the `agent` category (the expensive LLM runs) |
| `sweep[-lite] <ticker> market=EGX` | Sweep with an extra market filter (also accepts `no-agent`) |
| `category <name> <ticker>` | One category: `data`, `technicals`, `stats`, `backtest`, `fundamentals`, `sentiment`, `forecast`, `agent` |
| `market <EGX\|US> <ticker>` | Tools whose registry `markets` include that market |
| `run <tool> <ticker>` | A single tool — the only way to run a `manual`-status tool |

The registry covers all 36 fleet tools. Tools with status `manual`
(backtesting-py, superalgos, fingpt, egx-mcp) are excluded from sweeps for
documented upstream reasons (see their registry notes) and run only when
named explicitly.

## Scheduled sweep

The workflow also runs on a schedule — **Sun–Thu 06:15 UTC** (08:15 Cairo in
winter, 09:15 in summer; always before the EGX 10:00 open) — using the
`JOB_SCHEDULED` repository variable, set to `sweep-lite POUL.CA market=EGX`.
Manual dispatches use the job input, falling back to the `JOB` variable.

## Scope

Phase 1 (built): the 13 proven core tools, the summary contract, digest
issues. Phase 2 (built): job routing (`sweep-lite` / `category` / `market`),
the scheduled pre-market sweep, and a digest watch that reports each new
scheduled digest and sends an email ping.
