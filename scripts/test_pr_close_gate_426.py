#!/usr/bin/env python3
"""Tests for scripts/check_pr_close_keywords.py (issue #426).

Stdlib only, no network — the pure checks take plain strings and a fake
label fetcher; main() is exercised in-process with a monkeypatched
fetcher and PR_BODY. Mirrors the repo convention
(scripts/test_promote.py): a check() harness, exit 0 only when every
test passes.

Failing-before: on pristine main this file cannot even be collected —
the gate module does not exist, so a "Fixes #420" PR body closes the
unverified issue at merge with nothing to stop it (proven live by the
#420/#421 timelines: close 2-3s after merge, card to Released only
after the close). These tests assert the gate that did not exist.

Usage: python3 scripts/test_pr_close_gate_426.py
Exit 0 only when every test passes.
"""
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


# --- Parsing: which bodies would auto-close an issue at merge? ---

def test_parse():
    check("parse: Fixes #420",
          gate.find_close_targets("Fixes #420.", REPO) == [420])
    check("parse: lowercase + comma list",
          gate.find_close_targets("fixes #420, #421", REPO) == [420, 421])
    check("parse: and-list",
          gate.find_close_targets("Fixes #420 and #421", REPO) == [420, 421])
    check("parse: Closes / Resolves variants",
          gate.find_close_targets("Closes #420\nResolves #421", REPO)
          == [420, 421])
    check("parse: colon form",
          gate.find_close_targets("Fixes: #420", REPO) == [420])
    check("parse: same-repo owner/repo#N",
          gate.find_close_targets("Fixes moos-labs/borsagator#420", REPO)
          == [420])
    check("parse: full issue URL",
          gate.find_close_targets(
              "Fixes https://github.com/moos-labs/borsagator/issues/420",
              REPO) == [420])
    check("parse: Related to does NOT close",
          gate.find_close_targets("Related to #420", REPO) == [])
    check("parse: keyword without a following ref does NOT close",
          gate.find_close_targets("Fixes the bug in #420", REPO) == [])
    check("parse: other-repo ref ignored",
          gate.find_close_targets("Fixes other-org/other-repo#1", REPO)
          == [])
    check("parse: no keyword, no targets",
          gate.find_close_targets("See #420 for context.", REPO) == [])
    check("parse: duplicates deduped",
          gate.find_close_targets("Fixes #420\nFixes #420", REPO) == [420])
    check("parse: real #422 body line",
          gate.find_close_targets(
              "Fixes #420. Do not merge without review.", REPO) == [420])
    check("parse: real #424 body line",
          gate.find_close_targets("Fixes #421.", REPO) == [421])


# --- Gate decision: an unverified close target must be deferred. ---

def fake_fetch(labels_by_number):
    def fetch(number):
        return set(labels_by_number.get(number, []))
    return fetch


def test_gate_decision():
    # (a) FAILING-BEFORE case: the #420 shape — "Fixes #420" while #420
    # is unverified. On the old code there was no gate and the merge
    # closed it (12:06:20Z, 3s after PR #422 merged). The gate must
    # block it.
    allowed, blocked = gate.check_targets(
        [420], fake_fetch({420: []}))
    check("gate: unverified #420 blocked",
          allowed == [] and blocked == [420],
          "allowed=%r blocked=%r" % (allowed, blocked))

    # (b) PASSING-AFTER case: the same issue once verified may close.
    allowed, blocked = gate.check_targets(
        [420], fake_fetch({420: ["verified"]}))
    check("gate: verified #420 allowed",
          allowed == [420] and blocked == [])

    # Mixed: only the unverified one is named as blocked.
    allowed, blocked = gate.check_targets(
        [420, 421], fake_fetch({420: ["verified"], 421: []}))
    check("gate: mixed targets block only the unverified one",
          allowed == [420] and blocked == [421],
          "allowed=%r blocked=%r" % (allowed, blocked))

    # No targets: nothing to block.
    allowed, blocked = gate.check_targets([], fake_fetch({}))
    check("gate: no targets passes", allowed == [] and blocked == [])

    # The blocked message names the issue and the remedy.
    msg = gate.blocked_message([420, 421])
    check("gate: blocked message names issues + remedy",
          "#420" in msg and "#421" in msg
          and "Related to #N" in msg and "verified_closeout" in msg, msg)


# --- main(): end-to-end decision with a fake fetcher, no network. ---

def run_main(body, labels_by_number):
    os.environ["PR_BODY"] = body
    os.environ.pop("PR_NUMBER", None)
    old = gate.fetch_issue_labels
    gate.fetch_issue_labels = lambda n, t, r=REPO: set(
        labels_by_number.get(n, []))
    try:
        return gate.main()
    finally:
        gate.fetch_issue_labels = old
        os.environ.pop("PR_BODY", None)


def test_main():
    check("main: unverified close target exits 1",
          run_main("Fixes #420.", {420: []}) == 1)
    check("main: verified close target exits 0",
          run_main("Fixes #420.", {420: ["verified"]}) == 0)
    check("main: no closing keyword exits 0 without any fetch",
          run_main("Related to #420.", {420: []}) == 0)
    check("main: missing PR_NUMBER and PR_BODY fails closed",
          _main_without_env() == 1)


def _main_without_env():
    os.environ.pop("PR_BODY", None)
    os.environ.pop("PR_NUMBER", None)
    return gate.main()


if __name__ == "__main__":
    test_parse()
    test_gate_decision()
    test_main()
    print("test_pr_close_gate_426: %d passed, %d failed"
          % (PASSED, len(FAILED)))
    if FAILED:
        print("FAILED: %s" % ", ".join(FAILED))
        sys.exit(1)
