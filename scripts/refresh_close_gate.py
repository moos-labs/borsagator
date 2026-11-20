#!/usr/bin/env python3
"""Re-run the pr-close-gate when a target issue's labels change (#432 Gap 2).

The gate workflow (pr-close-gate.yml) triggers only on pull_request
events, so a 'verified' label change on a target issue never re-ran
it: removing 'verified' after a green run left a stale green (unsafe
— the merge would auto-close an unverified issue), adding it after a
red run left a stale red until the next PR push/edit. This script is
the refresh side: it runs on issues labeled/unlabeled (see
.github/workflows/pr-close-gate-refresh.yml), finds the open PRs whose
merge message targets the relabeled issue, and re-runs the latest
completed pr-close-gate run for each affected PR head, so the check on
the PR is re-evaluated against the fresh label state.

A re-run (not a new check run) is used deliberately: the re-run
re-fetches labels at run time and updates the PR's own close-gate
check, so there is no duplicate check-run name to confuse required
checks. Runs still in flight are skipped — the in-flight run fetches
labels when it starts, and a label change landing mid-run is a
seconds-wide race the next event re-triggers.

This script never blocks a merge itself: it only triggers re-runs.
API failure exits 1 so the workflow run shows failed in Actions.

Stdlib only. Usage in CI: GH_TOKEN, GITHUB_REPOSITORY and
ISSUE_NUMBER from the environment.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_pr_close_keywords as gate  # noqa: E402

API = "https://api.github.com"
DEFAULT_REPO = "moos-labs/borsagator"
GATE_WORKFLOW = "pr-close-gate.yml"


def api(method, path, token, body=None):
    """One authenticated GitHub API call; returns parsed JSON."""
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "borsagator-pr-close-gate-refresh",
        },
    )
    if data is not None:
        r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def list_open_prs(token, repo=DEFAULT_REPO):
    """Open PRs as {number, head_sha} dicts (paginated)."""
    prs, page = [], 1
    while True:
        batch = api("GET",
                    f"/repos/{repo}/pulls?state=open&per_page=100&page={page}",
                    token)
        if not batch:
            break
        prs.extend({"number": p["number"],
                    "head_sha": p["head"]["sha"]} for p in batch)
        if len(batch) < 100:
            break
        page += 1
    return prs


def affected_prs(summaries, issue_number):
    """PR summaries whose merge message targets `issue_number`.

    Each summary is {number, head_sha, title, body, commit_messages}.
    A summary flagged `commit_coverage_incomplete` is affected
    regardless of what its partial commit set shows: the unseen commits
    may carry the closing keyword, so the PR must be re-evaluated
    (fail closed) rather than treated as clean (CodeRabbit on #433).
    """
    affected = []
    for s in summaries:
        if s.get("commit_coverage_incomplete"):
            affected.append(s)
            continue
        text = gate.merge_message_text(
            s.get("title") or "", s.get("body") or "",
            s.get("commit_messages") or [])
        if issue_number in gate.find_close_targets(text):
            affected.append(s)
    return affected


def latest_gate_run(token, repo, head_sha, pr_number):
    """Latest pr-close-gate run for a head SHA belonging to PR number.

    Selected by the PR number in the run's `pull_requests` list, not
    by head_sha alone: two open PRs can share a head SHA (same branch
    PR'd to two bases), and the newest run for the SHA can then belong
    to the other PR — re-running it would re-evaluate the wrong PR
    while this PR's check stays stale (CodeRabbit on #433). The
    runs endpoint pages at 30, so a full page of the other PR's
    newer runs can hide this PR's run on a later page: follow pages
    until a matching run is found or a short page ends the list
    (CodeRabbit on #433, review 5995989212). Returns None when no
    run belongs to this PR number; the caller reports it.
    """
    page = 1
    while True:
        runs = api(
            "GET",
            f"/repos/{repo}/actions/workflows/{GATE_WORKFLOW}/runs"
            f"?head_sha={head_sha}&per_page=30&page={page}",
            token)
        batch = runs.get("workflow_runs") or []
        for run in batch:
            for pr in run.get("pull_requests") or []:
                if pr.get("number") == pr_number:
                    return run
        if len(batch) < 30:
            return None
        page += 1


def rerun_gate(token, repo, run_id):
    """Re-run a gate workflow run; returns the API response."""
    return api("POST", f"/repos/{repo}/actions/runs/{run_id}/rerun",
               token)


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    token = os.environ.get("GH_TOKEN", "")
    issue_number = os.environ.get("ISSUE_NUMBER")
    try:
        if not issue_number:
            raise RuntimeError("ISSUE_NUMBER is required")
        issue_number = int(issue_number)
        if not token:
            raise RuntimeError("GH_TOKEN is required")
        prs = list_open_prs(token, repo)
        summaries = []
        for pr in prs:
            detail = gate.fetch_pr(pr["number"], token, repo)
            incomplete = False
            try:
                commit_messages = gate.fetch_pr_commit_messages(
                    pr["number"], token, repo,
                    expected_total=detail.get("commits"))
            except gate.IncompleteCommitCoverage as e:
                # The partial set cannot prove the PR clean: flag it
                # affected so its gate is re-run and fails closed with
                # the diagnosis, instead of trusting the partial set.
                incomplete = True
                commit_messages = e.fetched
                print("refresh: PR #%d has %d commits but only %d were "
                      "fetchable (endpoint caps at 250) — treating as "
                      "affected, the re-run gate will fail closed"
                      % (pr["number"], e.expected, len(e.fetched)))
            summaries.append({
                "number": pr["number"],
                "head_sha": pr["head_sha"],
                "title": detail["title"],
                "body": detail["body"],
                "commit_messages": commit_messages,
                "commit_coverage_incomplete": incomplete,
            })
        affected = affected_prs(summaries, issue_number)
        if not affected:
            print("refresh: no open PR targets #%d — nothing to re-run"
                  % issue_number)
            return 0
        failed = []
        for pr in affected:
            run = latest_gate_run(token, repo, pr["head_sha"],
                                  pr["number"])
            if run is None:
                print("refresh: PR #%d targets #%d but no gate run "
                      "belongs to PR #%d — needs a push/edit to trigger"
                      % (pr["number"], issue_number, pr["number"]))
                continue
            if run.get("status") != "completed":
                print("refresh: PR #%d gate run %s still %s — skipping, "
                      "the in-flight run re-evaluates"
                      % (pr["number"], run.get("id"),
                         run.get("status")))
                continue
            try:
                rerun_gate(token, repo, run["id"])
            except Exception as e:  # noqa: BLE001 - per-PR, keep going
                # A rerun can fail per PR (e.g. the run is older than
                # GitHub's 30-day rerun window) — that must not stop
                # later PRs being refreshed (CodeRabbit on #433).
                failed.append(pr["number"])
                print("::error::refresh: re-run of gate run %s for "
                      "PR #%d failed: %s — PR #%d needs a push or edit "
                      "to create a fresh gate run"
                      % (run["id"], pr["number"], e, pr["number"]))
                print("refresh: re-run for PR #%d failed (%s) — "
                      "continuing with the remaining PRs"
                      % (pr["number"], e))
                continue
            print("refresh: re-ran gate run %s for PR #%d (was %s) — "
                  "re-evaluates #%d labels"
                  % (run["id"], pr["number"], run.get("conclusion"),
                     issue_number))
        if failed:
            print("refresh: %d PR(s) could not be refreshed: %s — each "
                  "needs a push or edit to create a fresh gate run"
                  % (len(failed),
                     ", ".join("#%d" % n for n in failed)))
            return 1
        return 0
    except Exception as e:  # noqa: BLE001 - loud failure, never silent
        print("::error::PR CLOSE GATE REFRESH FAILED: %s" % e)
        print("refresh: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
