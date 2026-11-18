# Promoting to `worker-release` — frozen-candidate process (issue #145)

## Why

`worker-release` is the branch the worker runs with the keys in its
environment (D2). Only reviewed code may reach it. Promotion PRs used
to be opened **from live `main`** — PR #144's head drifted
`32704d7f` → `8f1d76a` → `134322f` under review as guard heartbeats
landed on `main`, and with `dismiss_stale_reviews` off an approval
survives head changes, so anything landing on `main` before merge
promoted unreviewed. The worker's ancestry guard cannot catch this:
a merge commit is a descendant of the current release tip by
construction. PR #144 was later merged with zero recorded reviews.

The fix is structural: the candidate is **frozen** before review, so
there is nothing left to drift.

## The process (the only compliant path)

1. **Review a commit on `main`.** Note its full 40-hex SHA — that
   SHA, and only that SHA, is the candidate.
2. **Open the promotion PR from a frozen branch:**
   `python3 scripts/promote.py open --sha <reviewed-sha> --title "..." --body-file <file>`
   This creates branch `promote/<sha-12>` pinned to exactly that SHA
   (refusing to reuse the name for a different SHA), and opens the PR
   `promote/<sha-12>` → `worker-release` with a
   `Reviewed-SHA: <sha>` trailer in its body. Never open a promotion
   PR from `main`, and never commit to a `promote/*` branch after it
   is created — if the candidate must change, that is a *new*
   candidate: review the new SHA and open a new frozen branch.
3. **Verify before merging:**
   `python3 scripts/promote.py verify --pr <N>`
   Passes only if the PR is open, its base is `worker-release`, its
   head branch is the frozen branch (not `main`), and its head SHA
   equals the reviewed SHA. Any drift fails loudly; re-freeze instead
   of merging.
4. **Merge through the gate:**
   `python3 scripts/promote.py merge --pr <N>`
   Re-runs the pre-merge gate, merges with method "merge", then
   checks the merge commit's second parent == the reviewed SHA. On
   any mismatch it exits non-zero and the promotion must **not** be
   recorded. (For a squash/fast-forward merge the recorded pre-merge
   head SHA is checked instead.)
5. **Record the promotion** in the promotion log (see below) only
   after step 4 passes, or run
   `python3 scripts/promote.py record --pr <N>` to re-verify a merged
   PR and print its log row. A merge whose SHA does not match the
   reviewed SHA is never recorded as a promotion.

The `promotion-gate` workflow runs the same check on every PR to
`worker-release` (head ≠ `main`, head SHA == `Reviewed-SHA:` trailer).
It is advisory until added to worker-release's required status
checks — see "Branch protection" below.

## What NOT to do

- Do not open a promotion PR from `main` (the old
  `open_pr_steps56_step6.py` / `open_pr_canary_revert.py` pattern is
  superseded by `scripts/promote.py open`).
- Do not merge a promotion PR with the generic `merge_pr_164.py`
  pattern — it performs no frozen-candidate check. Use
  `scripts/promote.py merge`.
- Do not force-push, reset, or rewrite `worker-release` or any
  `promote/*` branch. The worker refuses non-descendant tips, and a
  rewritten frozen branch breaks the SHA equality the gate checks.

## Why the worker cannot enforce this

`worker/worker.py` `self_update` only knows the release tip must be
a descendant of the running code (or equal to `GATOR_PIN_SHA`). It
has no source for the reviewed SHA, so it cannot tell a reviewed
descendant from an unreviewed one. Enforcement therefore lives at
promotion time (this script + the gate workflow), where the reviewed
SHA is known.

## Branch protection (recorded 2026-11-17, read-only)

- `worker-release`: PR required, `required_approving_review_count`
  0 (Muhammad's 2026-11-17 instruction — Moos merges without his
  review), `dismiss_stale_reviews: false`, `enforce_admins: true`,
  no force pushes, no deletions, **no required status checks**.
- `main`: **unprotected** (protection API returns 404) at the same
  read. That is outside #145's scope, but it is why the frozen
  branch matters: `main` can move at any time, so a promotion PR
  tracking it is never stable.

Recommendations for the cycle to apply deliberately (not changed by
the #145 fix itself):

1. Add `promotion-gate` (the `frozen-candidate` job) as a **required
   status check** on `worker-release`, so a PR that fails the gate
   cannot merge even from the web UI.
2. Once (1) is in place, set `dismiss_stale_reviews: true` on
   `worker-release`. It is safe now — frozen branches never receive
   heartbeat commits, so there is no churn to dismiss approvals —
   and it closes the stale-approval hole for any future PR that
   does change head.
3. Consider protecting `main` (PR + review) as a separate decision;
   #145 does not depend on it.

## Promotion log

Every promotion is recorded in
`hidden_files/issue-65/promotion-log.md` (outside this repo) with
time, merged SHA, source PR, promoter, and adoption evidence. Only
promotions that passed the step-4/5 checks are recorded.
