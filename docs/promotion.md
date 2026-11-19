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

## Deploying helper changes to archive: atomic, idempotent (issue #232)

The archive branch runs scripts/worker_digest_issue.py from its own
copy, so every helper change needs a deploy after the merge to main.
The one-off deploy scripts this replaces created the archive commit
but did not move the branch ref atomically (#223: commit 610cbfd
existed while the ref still read 2f7248a, repaired by a manual
PATCH). The only compliant deploy path is now:

    python3 scripts/deploy_archive.py --repo-dir . \
        --main-sha REVIEWED_SHA

Pass the REVIEWED merge SHA as --main-sha (full 40-hex; symbolic
revs are rejected): the deploy source is an immutable commit, never
whatever main happens to point at. What it
guarantees (the full contract is in the script docstring):

1. **Exact compare-and-swap ref move.** The deploy commit's parent
   is pinned to the ref value read at fetch time and the move is a
   push with --force-with-lease=REF:OLD: the server rejects unless
   the ref still equals OLD, including against rewinds and rewrites
   that a plain non-forced push (a mere ancestor check) would
   silently accept. On rejection the helper reconciles, rebuilds on
   the new parent and retries (bounded by --max-attempts, default
   3); exhaustion is red and it never force-pushes. Rejected
   attempts leave their locally built deploy commits as temporary
   unreachable objects in the local clone until git gc; the
   remote never carries them.
2. **Lost-response reconciliation.** A failed push can still have
   landed (and a push timeout is the same class), so every failed
   push is reconciled by re-reading the remote before concluding or
   retrying: landed means verify and finish. Otherwise only
   reachability is claimed: the attempt SHA is not reachable from
   the observed tip, and the record retains each attempt's SHA,
   server message and observed head. A moved observed tip is
   contention (retry); an unmoved one is transport/protection/auth,
   red without retry. No failure is ever classified from the exit
   code alone. Each attempt is recorded BEFORE its push (attempted
   SHA, expected OLD, then push result), so if the push AND the
   reconciliation re-read both fail, the run is nonzero with
   result "unknown" and the attempted SHA, expected OLD and push
   error survive in the record with the observed tip null.
3. **Preflight before effect.** The deploy commit's scope and
   content are asserted locally before any push; a malformed deploy
   commit is never published. The record destination is created and
   append-proven before any push too, so an unwritable record path
   stops the deploy before anything happens.
4. **Idempotence.** If the archive tip's helper blob already equals
   the source blob, the run is a no-op and creates no commit
   object, so a re-run can never leave a dangling commit.
5. **Post-deploy assert, strict equality.** After the push, the
   remote is re-read: the ref must read EXACTLY the pushed commit,
   git diff OLD..NEW --name-only must be exactly
   scripts/worker_digest_issue.py, and the helper blob must equal
   the source blob. Any other observed tip, even a benign data
   commit landing a second later, is red verify-failed naming the
   expected SHA and the exact observed tip; the repair is a re-run
   after writers quiesce, never a force-push.
6. **Deployment record.** Every run, including every error path,
   appends one JSON line to the record file (default
   hidden_files/deploys.jsonl under --repo-dir) linking the source
   commit SHA and whether it was pinned, the source helper blob,
   the old and new archive SHAs, the attempt count and the result
   (deployed, noop, cas-exhausted, push-rejected, preflight-failed,
   verify-failed, bootstrap-required, unknown, error), and prints
   the same line on stdout. If the append itself fails after an effect, the
   run goes nonzero with record_write_failed true and the printed
   line is the surviving evidence. It is a local append log, not a
   distributed ledger: a crash between push and append can lose a
   line, and the next run's re-read of the remote is the backstop.

The deploy-guard workflow alarms on helper-blob drift between main
and archive, always running its guard code checked out from main
(see .github/workflows/deploy-guard.yml and
scripts/check_helper_blob_parity.py); red between a helper-landing
merge and the deploy is expected. Its triggers are pushes to main,
an hourly schedule and manual workflow_dispatch: per GitHub's
push-event semantics a push runs the workflow file as it exists on
the pushed ref, and this file exists only on main, so archive
pushes intentionally have no push trigger. They are covered by the
schedule and dispatch, and parity flips green on the next
main-side run after a deploy, not at push time. worker-release is excluded from
the default parity refs by deliberate scope (it legitimately lags
main between reviewed promotions); assert all three paths with
--refs origin/main origin/worker-release origin/archive when a
promotion should have completed. Regression coverage is
scripts/test_deploy_archive_232.py.
