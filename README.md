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

## Phase 1 scope

The 13 proven core tools (data, technicals, stats, fundamentals, sentiment,
forecast, agent) and the `sweep` / `run` job types. Market-routing presets,
scheduled sweeps and email pings are phase 2.
