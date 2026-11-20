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


def summary(number, title, body="", commits=None, sha="abc123",
            coverage_incomplete=False):
    return {"number": number, "head_sha": sha, "title": title,
            "body": body, "commit_messages": commits or [],
            "commit_coverage_incomplete": coverage_incomplete}


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


def run_main(issue, prs, runs_by_pr, token="tok", fail_rerun_ids=()):
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
    refresh.latest_gate_run = lambda t, r, sha, num: runs_by_pr.get(num)
    def fake_rerun(t, r, rid):
        if rid in fail_rerun_ids:
            raise RuntimeError(
                "HTTP 422: cannot re-run a run older than 30 days")
        calls.append(rid)
        return {}
    refresh.rerun_gate = fake_rerun
    gate.fetch_pr = lambda n, t, r="moos-labs/borsagator": {
        "title": next(p["title"] for p in prs if p["number"] == n),
        "body": next(p["body"] for p in prs if p["number"] == n),
        "commits": len(next(p["commit_messages"] for p in prs
                            if p["number"] == n))}
    def fake_commits(n, t, r="moos-labs/borsagator", expected_total=None):
        p = next(p for p in prs if p["number"] == n)
        if p.get("commit_coverage_incomplete"):
            raise gate.IncompleteCommitCoverage(
                "incomplete commit coverage for PR #%d" % n,
                fetched=p["commit_messages"], expected=300)
        return p["commit_messages"]
    gate.fetch_pr_commit_messages = fake_commits
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
        425, [summary(430, "Fix #425: docs")], {430: completed})
    check("main: completed run on affected PR is re-run",
          rc == 0 and calls == [111], "rc=%r calls=%r" % (rc, calls))
    # Unaffected PR: no re-run.
    rc, calls = run_main(
        425, [summary(431, "Docs", "Related to #425.")],
        {431: completed})
    check("main: unaffected PR is not re-run", rc == 0 and calls == [])
    # No gate run yet: noted, no re-run, still exit 0.
    rc, calls = run_main(
        425, [summary(430, "Fix #425: docs")], {})
    check("main: affected PR with no gate run exits 0, no re-run",
          rc == 0 and calls == [])
    # In-flight run: skipped, no re-run.
    rc, calls = run_main(
        425, [summary(430, "Fix #425: docs")],
        {430: {"id": 112, "status": "in_progress",
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


def test_latest_gate_run_selects_by_pr_number():
    # CodeRabbit on PR #433: two open PRs can share a head SHA, so
    # the newest run for the SHA can belong to the other PR. The
    # fake API returns the newest run first (PR #432's), then this
    # PR's older run. FAILING-BEFORE: the #432 code returns runs[0]
    # (PR #432's run) for PR #431.
    runs = {"workflow_runs": [
        {"id": 222, "status": "completed", "conclusion": "success",
         "pull_requests": [{"number": 432}]},
        {"id": 111, "status": "completed", "conclusion": "failure",
         "pull_requests": [{"number": 431}]},
    ]}
    old_api = refresh.api
    refresh.api = lambda m, p, t, body=None: runs
    try:
        run = refresh.latest_gate_run("tok", "moos-labs/borsagator",
                                      "abc123", 431)
        check("latest run: shared head SHA returns this PR's run",
              run is not None and run["id"] == 111,
              "got %r" % (run or {}).get("id"))
        run = refresh.latest_gate_run("tok", "moos-labs/borsagator",
                                      "abc123", 432)
        check("latest run: other PR still finds its own run",
              run is not None and run["id"] == 222)
        check("latest run: PR with no run returns None",
              refresh.latest_gate_run("tok", "moos-labs/borsagator",
                                      "abc123", 999) is None)
        refresh.api = lambda m, p, t, body=None: {"workflow_runs": []}
        check("latest run: no runs at all returns None",
              refresh.latest_gate_run("tok", "moos-labs/borsagator",
                                      "abc123", 431) is None)
    finally:
        refresh.api = old_api


def test_main_rerun_failure_continues():
    # CodeRabbit on PR #433: GitHub allows re-runs only within 30 days
    # of the initial run, so an old completed run fails the POST — and
    # the #432 code let that abort the whole loop through the outer
    # handler, leaving later PRs stale. FAILING-BEFORE: the #432 code
    # exits 1 with calls == [111] never attempted (the raise happens
    # on the first PR) — here the first PR's rerun fails and the
    # second must still be re-run, with exit 1 naming the failure.
    completed_a = {"id": 111, "status": "completed",
                   "conclusion": "success"}
    completed_b = {"id": 112, "status": "completed",
                   "conclusion": "failure"}
    rc, calls = run_main(
        425,
        [summary(430, "Fix #425: docs"),
         summary(431, "Fixes #425 in body", "Fixes #425.")],
        {430: completed_a, 431: completed_b},
        fail_rerun_ids=(111,))
    check("main: failed rerun continues to later PRs",
          calls == [112], "calls=%r" % (calls,))
    check("main: any failed rerun exits 1", rc == 1, "rc=%r" % rc)
    # All reruns succeeding still exits 0.
    rc, calls = run_main(
        425,
        [summary(430, "Fix #425: docs"),
         summary(431, "Fixes #425 in body", "Fixes #425.")],
        {430: completed_a, 431: completed_b})
    check("main: all reruns succeeding exits 0",
          rc == 0 and calls == [111, 112],
          "rc=%r calls=%r" % (rc, calls))


def test_main_incomplete_coverage_pr_is_affected():
    # CodeRabbit on PR #433 (finding 1), refresh side: a PR whose
    # commit set cannot be fetched completely must not be trusted as
    # clean — its gate is re-run so the gate itself fails closed.
    # The PR below has a clean title/body; only the coverage flag
    # makes it affected.
    completed = {"id": 111, "status": "completed", "conclusion": "success"}
    rc, calls = run_main(
        425,
        [summary(430, "Docs tidy", "Related to #425.",
                 commits=["Tidy docs."], coverage_incomplete=True)],
        {430: completed})
    check("main: incomplete-coverage PR is re-run (fail closed)",
          rc == 0 and calls == [111], "rc=%r calls=%r" % (rc, calls))
    check("affected: incomplete-coverage flag alone affects the PR",
          len(refresh.affected_prs(
              [summary(430, "Docs tidy", "Related to #425.",
                       coverage_incomplete=True)], 425)) == 1)


if __name__ == "__main__":
    test_affected_prs()
    test_main()
    test_latest_gate_run_selects_by_pr_number()
    test_main_rerun_failure_continues()
    test_main_incomplete_coverage_pr_is_affected()
    print("test_pr_close_gate_refresh_432: %d passed, %d failed"
          % (PASSED, len(FAILED)))
    if FAILED:
        print("FAILED: %s" % ", ".join(FAILED))
        sys.exit(1)
