#!/usr/bin/env python3
"""Tests for scripts/refresh_close_gate.py (issue #432, Gap 2).

The gate workflow triggers only on pull_request events, so a label
change on a target issue never re-ran it: removing 'verified' after
green left a stale green, adding it after red left a stale red. The
refresh script re-runs the latest completed gate run for each open PR
whose merge message targets the relabeled issue.

Stdlib only, no network — main() is exercised in-process with
monkeypatched API functions. Mirrors scripts/test_pr_close_gate_426.py.

Usage: python3 scripts/test_pr_close_gate_refresh_432.py
Exit 0 only when every test passes.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refresh_close_gate as refresh  # noqa: E402

PASSED = 0
FAILED = []


def check(name, cond, detail=""):
    global PASSED
    if cond:
        PASSED += 1
        print("PASS %s" % name)
    else:
        FAILED.append(name)
        print("FAIL %s %s" % (name, detail))


def summary(number, title, body="", commits=None, sha="abc123"):
    return {"number": number, "head_sha": sha, "title": title,
            "body": body, "commit_messages": commits or []}


def test_affected_prs():
    check("affected: title keyword targets the relabeled issue",
          refresh.affected_prs(
              [summary(430, "Fix #425: docs")], 425)
          == [summary(430, "Fix #425: docs")])
    check("affected: body keyword targets the relabeled issue",
          len(refresh.affected_prs(
              [summary(431, "Docs", "Fixes #425.")], 425)) == 1)
    check("affected: commit keyword targets the relabeled issue",
          len(refresh.affected_prs(
              [summary(431, "Docs", "", ["Fixes #425."])], 425)) == 1)
    check("affected: PR targeting another issue is not affected",
          refresh.affected_prs(
              [summary(431, "Fix #426: gate")], 425) == [])
    check("affected: PR with no keywords is not affected",
          refresh.affected_prs(
              [summary(431, "Docs", "Related to #425.")], 425) == [])
    check("affected: only the targeting PR is returned",
          [s["number"] for s in refresh.affected_prs(
              [summary(431, "Fix #425: x"),
               summary(432, "Fix #426: y"),
               summary(433, "Docs")], 425)] == [431])


def run_main(issue, prs, runs_by_sha, token="tok"):
    os.environ["ISSUE_NUMBER"] = str(issue) if issue is not None else ""
    os.environ["GH_TOKEN"] = token
    os.environ.pop("GITHUB_REPOSITORY", None)
    calls = []
    old_list = refresh.list_open_prs
    old_run = refresh.latest_gate_run
    old_rerun = refresh.rerun_gate
    import check_pr_close_keywords as gate
    old_fetch_pr = gate.fetch_pr
    old_fetch_commits = gate.fetch_pr_commit_messages
    refresh.list_open_prs = lambda t, r="moos-labs/borsagator": prs
    refresh.latest_gate_run = lambda t, r, sha: runs_by_sha.get(sha)
    refresh.rerun_gate = lambda t, r, rid: calls.append(rid) or {}
    gate.fetch_pr = lambda n, t, r="moos-labs/borsagator": {
        "title": next(p["title"] for p in prs if p["number"] == n),
        "body": next(p["body"] for p in prs if p["number"] == n)}
    gate.fetch_pr_commit_messages = lambda n, t, r="moos-labs/borsagator": \
        next(p["commit_messages"] for p in prs if p["number"] == n)
    try:
        return refresh.main(), calls
    finally:
        refresh.list_open_prs = old_list
        refresh.latest_gate_run = old_run
        refresh.rerun_gate = old_rerun
        gate.fetch_pr = old_fetch_pr
        gate.fetch_pr_commit_messages = old_fetch_commits
        os.environ.pop("ISSUE_NUMBER", None)
        os.environ.pop("GH_TOKEN", None)


def test_main():
    completed = {"id": 111, "status": "completed", "conclusion": "success"}
    # Stale green: PR targeting #425, gate run completed success —
    # a 'verified' removal must re-run it.
    rc, calls = run_main(
        425, [summary(430, "Fix #425: docs")], {"abc123": completed})
    check("main: completed run on affected PR is re-run",
          rc == 0 and calls == [111], "rc=%r calls=%r" % (rc, calls))
    # Unaffected PR: no re-run.
    rc, calls = run_main(
        425, [summary(431, "Docs", "Related to #425.")],
        {"abc123": completed})
    check("main: unaffected PR is not re-run", rc == 0 and calls == [])
    # No gate run yet: noted, no re-run, still exit 0.
    rc, calls = run_main(
        425, [summary(430, "Fix #425: docs")], {})
    check("main: affected PR with no gate run exits 0, no re-run",
          rc == 0 and calls == [])
    # In-flight run: skipped, no re-run.
    rc, calls = run_main(
        425, [summary(430, "Fix #425: docs")],
        {"abc123": {"id": 112, "status": "in_progress",
                    "conclusion": None}})
    check("main: in-flight run is skipped", rc == 0 and calls == [])
    # No open PR targets the issue: exit 0, no re-run.
    rc, calls = run_main(425, [], {})
    check("main: no targeting PR exits 0", rc == 0 and calls == [])
    # Missing ISSUE_NUMBER fails closed.
    os.environ.pop("ISSUE_NUMBER", None)
    os.environ["GH_TOKEN"] = "tok"
    try:
        rc = refresh.main()
    finally:
        os.environ.pop("GH_TOKEN", None)
    check("main: missing ISSUE_NUMBER exits 1", rc == 1)


if __name__ == "__main__":
    test_affected_prs()
    test_main()
    print("test_pr_close_gate_refresh_432: %d passed, %d failed"
          % (PASSED, len(FAILED)))
    if FAILED:
        print("FAILED: %s" % ", ".join(FAILED))
        sys.exit(1)
