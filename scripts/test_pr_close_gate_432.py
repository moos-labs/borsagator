#!/usr/bin/env python3
"""Tests for the #432 fix to scripts/check_pr_close_keywords.py.

Issue #432 (INS-REVIEW-008 follow-up): the #426 gate (PR #428) only
read the PR BODY, but GitHub's auto-close parser reads the message
that lands on main at merge — the squash/merge commit message, which
GitHub composes from the PR title, the PR body and (in this repo) the
branch commit messages:

  - PR #430 merged 2026-11-20T14:08:39Z with body "For #425" (no
    closing keyword, gate run 44750450985 green 14:07:29Z) but title
    "Fix #425: ..." and a single branch commit whose message was
    identical to title + body. The squash commit 44b031d2 reads
    "Fix #425: promotion docs ..." — GitHub parsed the closing keyword
    and #425 closed 14:08:41Z (2s after merge), reopened 14:08:54Z by
    borsagator[bot]. The gate passed a PR that auto-closed an
    unverified issue.
  - Repo merge settings (read 2026-11-20): squash + merge-commit +
    rebase all allowed; squash_merge_commit_message=COMMIT_MESSAGES,
    merge_commit_message=PR_TITLE. So the merge-time text is the union
    of title + body + branch commit messages, and the gate must scan
    that union.

Failing-before: on the #426 code these tests fail — main() ignores
PR_TITLE / PR_COMMIT_MESSAGES, so the #430 shape (clean body, closing
keyword in title/commit message) exits 0 while #425 is unverified.

Stdlib only, no network — main() is exercised in-process with a
monkeypatched label fetcher and PR_TITLE/PR_BODY/PR_COMMIT_MESSAGES.
Mirrors scripts/test_pr_close_gate_426.py.

Usage: python3 scripts/test_pr_close_gate_432.py
Exit 0 only when every test passes.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_pr_close_keywords as gate  # noqa: E402

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


REPO = "moos-labs/borsagator"

# The exact #430 shape (verified against the API 2026-11-20):
# body "For #425 ..." with no closing keyword; title and the single
# branch commit message both "Fix #425: ...".
TITLE_430 = "Fix #425: promotion docs stale about required status checks on worker-release"
BODY_430 = "For #425 \u2014 promotion docs stale about required status checks on `worker-release`."
COMMIT_430 = (
    "Fix #425: promotion docs stale about required status checks on worker-release\n"
    "\n"
    "- docs/promotion.md: promotion-gate no longer described as advisory."
)


def test_merge_message_text():
    check("merge text: title + body + commits joined",
          gate.merge_message_text("Fix #425: x", "For #425.", ["Fix #425: y"])
          == "Fix #425: x\n\nFor #425.\n\nFix #425: y")
    check("merge text: empty parts skipped",
          gate.merge_message_text("", "For #425.", [])
          == "For #425.")
    check("merge text: title-only keeps the keyword",
          gate.find_close_targets(
              gate.merge_message_text(TITLE_430, BODY_430, []), REPO)
          == [425])
    check("merge text: body-only finds nothing (#430 body)",
          gate.find_close_targets(
              gate.merge_message_text("", BODY_430, []), REPO) == [])
    check("merge text: #430 full shape targets #425",
          gate.find_close_targets(
              gate.merge_message_text(TITLE_430, BODY_430, [COMMIT_430]),
              REPO) == [425])
    check("merge text: commit-only keyword counts (rebase path)",
          gate.find_close_targets(
              gate.merge_message_text("Docs tidy", "No refs here.",
                                      ["Fixes #425."]), REPO) == [425])
    check("merge text: duplicates across title/body/commits deduped",
          gate.find_close_targets(
              gate.merge_message_text("Fix #425: x", "Fixes #425.",
                                      ["Fix #425."]), REPO) == [425])
    check("merge text: Related to everywhere still closes nothing",
          gate.find_close_targets(
              gate.merge_message_text("Related to #425", "Related to #425.",
                                      ["Related to #425."]), REPO) == [])


# --- main(): the #430 shape must FAIL while #425 is unverified. ---

def run_main(title, body, commits, labels_by_number):
    os.environ["PR_TITLE"] = title
    os.environ["PR_BODY"] = body
    os.environ["PR_COMMIT_MESSAGES"] = json.dumps(commits)
    os.environ.pop("PR_NUMBER", None)
    old = gate.fetch_issue_labels
    gate.fetch_issue_labels = lambda n, t, r=REPO: set(
        labels_by_number.get(n, []))
    try:
        return gate.main()
    finally:
        gate.fetch_issue_labels = old
        for k in ("PR_TITLE", "PR_BODY", "PR_COMMIT_MESSAGES"):
            os.environ.pop(k, None)


def test_main():
    # (a) FAILING-BEFORE case: the #430 shape — clean body, closing
    # keyword in title + commit message, #425 unverified. The #426
    # gate exited 0 here (run 44750450985 green 14:07:29Z) and the
    # merge auto-closed #425 70s later. The fixed gate must exit 1.
    check("main: #430 shape exits 1 while #425 unverified",
          run_main(TITLE_430, BODY_430, [COMMIT_430], {425: []}) == 1)
    # (b) PASSING-AFTER case: the same shape once #425 is verified.
    check("main: #430 shape exits 0 once #425 verified",
          run_main(TITLE_430, BODY_430, [COMMIT_430],
                   {425: ["verified"]}) == 0)
    # (c) Title-only keyword: body and commits clean.
    check("main: title-only keyword exits 1 while unverified",
          run_main(TITLE_430, "No refs here.", [], {425: []}) == 1)
    check("main: title-only keyword exits 0 once verified",
          run_main(TITLE_430, "No refs here.", [],
                   {425: ["verified"]}) == 0)
    # (d) Commit-message-only keyword (rebase / squash-COMMIT_MESSAGES).
    check("main: commit-only keyword exits 1 while unverified",
          run_main("Docs tidy", "No refs here.", ["Fixes #425."],
                   {425: []}) == 1)
    check("main: commit-only keyword exits 0 once verified",
          run_main("Docs tidy", "No refs here.", ["Fixes #425."],
                   {425: ["verified"]}) == 0)
    # (e) Clean everywhere still passes without any fetch.
    check("main: clean title/body/commits exits 0",
          run_main("Docs tidy", "Related to #425.",
                   ["Tidy docs."], {425: []}) == 0)
    # (f) Malformed PR_COMMIT_MESSAGES fails closed.
    os.environ["PR_TITLE"] = "Docs tidy"
    os.environ["PR_BODY"] = "No refs here."
    os.environ["PR_COMMIT_MESSAGES"] = "not-json{["
    os.environ.pop("PR_NUMBER", None)
    try:
        rc = gate.main()
    finally:
        for k in ("PR_TITLE", "PR_BODY", "PR_COMMIT_MESSAGES"):
            os.environ.pop(k, None)
    check("main: malformed PR_COMMIT_MESSAGES fails closed", rc == 1)


if __name__ == "__main__":
    test_merge_message_text()
    test_main()
    print("test_pr_close_gate_432: %d passed, %d failed"
          % (PASSED, len(FAILED)))
    if FAILED:
        print("FAILED: %s" % ", ".join(FAILED))
        sys.exit(1)
