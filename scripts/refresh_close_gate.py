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
    """
    affected = []
    for s in summaries:
        text = gate.merge_message_text(
            s.get("title") or "", s.get("body") or "",
            s.get("commit_messages") or [])
        if issue_number in gate.find_close_targets(text):
            affected.append(s)
    return affected


def latest_gate_run(token, repo, head_sha):
    """Latest pr-close-gate run for a head SHA, or None."""
    runs = api(
        "GET",
        f"/repos/{repo}/actions/workflows/{GATE_WORKFLOW}/runs"
        f"?head_sha={head_sha}&per_page=1",
        token)
    runs = runs.get("workflow_runs") or []
    return runs[0] if runs else None


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
            summaries.append({
                "number": pr["number"],
                "head_sha": pr["head_sha"],
                "title": detail["title"],
                "body": detail["body"],
                "commit_messages": gate.fetch_pr_commit_messages(
                    pr["number"], token, repo),
            })
        affected = affected_prs(summaries, issue_number)
        if not affected:
            print("refresh: no open PR targets #%d — nothing to re-run"
                  % issue_number)
            return 0
        for pr in affected:
            run = latest_gate_run(token, repo, pr["head_sha"])
            if run is None:
                print("refresh: PR #%d targets #%d but the gate never "
                      "ran on it — needs a push/edit to trigger"
                      % (pr["number"], issue_number))
                continue
            if run.get("status") != "completed":
                print("refresh: PR #%d gate run %s still %s — skipping, "
                      "the in-flight run re-evaluates"
                      % (pr["number"], run.get("id"),
                         run.get("status")))
                continue
            rerun_gate(token, repo, run["id"])
            print("refresh: re-ran gate run %s for PR #%d (was %s) — "
                  "re-evaluates #%d labels"
                  % (run["id"], pr["number"], run.get("conclusion"),
                     issue_number))
        return 0
    except Exception as e:  # noqa: BLE001 - loud failure, never silent
        print("::error::PR CLOSE GATE REFRESH FAILED: %s" % e)
        print("refresh: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
