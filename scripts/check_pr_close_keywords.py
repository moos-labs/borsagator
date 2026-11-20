#!/usr/bin/env python3
"""PR close-keyword gate — the PREVENTIVE fix for issue #426.

Background (verified against the #420/#421 timelines via the Issues API):
a PR body saying ``Fixes #N`` auto-closes issue N the moment the PR
merges — BEFORE any verification. For #420: PR #422 merged 12:06:17Z
and #420 closed 12:06:20Z (3s later, actor moos-sherbo, the merger);
the card moved to Released only at 12:06:22Z, i.e. AFTER the close, via
the built-in Item-closed workflow. Same for #421: PR #424 merged
12:36:44Z, #421 closed 12:36:46Z, card moved 12:36:48Z. #402 and #406
show the identical pattern (close 1s after the merge commit reference).
The trigger was the PR closing keyword — NOT the project auto-close on
card move. The built-in auto-close never fired first in any of these
cases, and board_sync.py's verification gate could only REACT (reopen
and revert) after the unverified close had already happened.

This gate runs on pull_request (see .github/workflows/pr-close-gate.yml)
and BLOCKS THE MERGE while the PR body carries a closing keyword
(``Fixes`` / ``Closes`` / ``Resolves`` and variants) referencing an issue
in this repo that does NOT yet carry the ``verified`` label. The close
is therefore deferred, not repaired after the fact:

  - No closing keyword, or every referenced issue verified -> exit 0.
  - Any referenced issue unverified -> exit 1, naming the issue(s) and
    the remedy: use ``Related to #N`` (a link, not a close) and close
    the issue only through the verified close-out procedure
    (scripts/verified_closeout.py: evidence comment, then the
    ``verified`` label, then close). Re-running the gate after the
    label lands passes.
  - API failure or a referenced issue that cannot be read -> exit 1
    (fail closed, with a ::error:: annotation), following the
    promotion-gate precedent: a red gate must be diagnosable from the
    check-run annotations without downloading run logs.

References to issues in OTHER repos are ignored: this gate cannot
verify them, and closing them is outside this repo's board.

Stdlib only, no network in the pure functions (tests inject a fake
label fetcher). Usage in CI: GH_TOKEN, GITHUB_REPOSITORY and PR_NUMBER
from the environment. For a local check, set PR_BODY instead of
PR_NUMBER to skip the API fetch for the PR body (labels are still
read from the API).
"""
import json
import os
import re
import sys
import urllib.request

API = "https://api.github.com"
DEFAULT_REPO = "moos-labs/borsagator"
VERIFIED_LABEL = "verified"

CLOSE_KEYWORDS = (
    r"close", r"closes", r"closed",
    r"fix", r"fixes", r"fixed",
    r"resolve", r"resolves", r"resolved",
)

# One issue reference: bare #N, owner/repo#N, or a full issue URL.
_REF = (
    r"(?:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)#(?P<num1>\d+)"
    r"|https://github\.com/(?P<owner2>[A-Za-z0-9_.-]+)/(?P<repo2>[A-Za-z0-9_.-]+)"
    r"/issues/(?P<num2>\d+)"
    r"|#(?P<num3>\d+))"
)
# Same reference shape without named groups (the outer pattern embeds
# it twice, which would redefine the group names).
_REF_PLAIN = (
    r"(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#\d+"
    r"|https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+"
    r"|#\d+)"
)
_SEP = r"(?:\s*(?:,|\band\b)\s*)?"
# A closing keyword, then one or more references separated by commas/and.
_CLOSE_RE = re.compile(
    r"\b(?:" + "|".join(CLOSE_KEYWORDS) + r")\b\s*:?\s*"
    r"(?P<refs>" + _REF_PLAIN + r"(?:" + _SEP + _REF_PLAIN + r")*)",
    re.IGNORECASE,
)
_REF_RE = re.compile(_REF)


def _ref_number(match, repo):
    """Issue number if this reference points at our repo, else None."""
    owner = match.group("owner") or match.group("owner2")
    name = match.group("repo") or match.group("repo2")
    if owner is not None and f"{owner}/{name}".lower() != repo.lower():
        return None
    num = match.group("num1") or match.group("num2") or match.group("num3")
    return int(num)


def find_close_targets(body, repo=DEFAULT_REPO):
    """Issue numbers in `repo` a PR body would auto-close at merge.

    Only references directly following a closing keyword count:
    ``Related to #420`` links without closing and is ignored, as is
    ``Fixes the bug in #420`` (no reference follows the keyword).
    """
    targets = set()
    for m in _CLOSE_RE.finditer(body or ""):
        for ref in _REF_RE.finditer(m.group("refs")):
            num = _ref_number(ref, repo)
            if num is not None:
                targets.add(num)
    return sorted(targets)


def fetch_issue_labels(number, token, repo=DEFAULT_REPO):
    """Label names on an issue, via the REST API. Raises on failure."""
    r = urllib.request.Request(
        f"{API}/repos/{repo}/issues/{number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "borsagator-pr-close-gate",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        issue = json.loads(resp.read())
    return {l["name"] for l in issue.get("labels", [])}


def check_targets(targets, fetch_labels):
    """Split close targets into (allowed, blocked) by the verified label.

    `fetch_labels(number)` returns the issue's label names. A target is
    blocked when it lacks `verified`: its close must be deferred until
    the verified close-out procedure has run. Returns (allowed, blocked)
    as sorted lists of issue numbers.
    """
    allowed, blocked = [], []
    for number in targets:
        labels = fetch_labels(number)
        if VERIFIED_LABEL in labels:
            allowed.append(number)
        else:
            blocked.append(number)
    return sorted(allowed), sorted(blocked)


def blocked_message(blocked):
    return (
        "PR close-gate: closing keyword(s) would auto-close unverified "
        "issue(s) %s at merge. Use 'Related to #N' instead of "
        "'Fixes #N' and close only via the verified close-out procedure "
        "(scripts/verified_closeout.py: evidence comment, then the "
        "'verified' label, then close). Re-run after the label lands."
        % ", ".join("#%d" % n for n in blocked)
    )


def fetch_pr_body(number, token, repo=DEFAULT_REPO):
    """PR body from the API (never the event payload — see #198)."""
    r = urllib.request.Request(
        f"{API}/repos/{repo}/pulls/{number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "borsagator-pr-close-gate",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read()).get("body") or ""


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    token = os.environ.get("GH_TOKEN", "")
    body = os.environ.get("PR_BODY")
    number = os.environ.get("PR_NUMBER")
    try:
        if body is None:
            if not number:
                raise RuntimeError(
                    "PR_NUMBER (or PR_BODY for a local check) is required")
            if not token:
                raise RuntimeError("GH_TOKEN is required")
            print("close-gate: fetching PR #%s from the API" % number)
            body = fetch_pr_body(number, token, repo)
        targets = find_close_targets(body, repo)
        if not targets:
            print("close-gate: no closing keyword references %s — pass"
                  % repo)
            return 0
        print("close-gate: closing keyword(s) target %s"
              % ", ".join("#%d" % n for n in targets))
        allowed, blocked = check_targets(
            targets, lambda n: fetch_issue_labels(n, token, repo))
        for n in allowed:
            print("close-gate: #%d is verified — close allowed" % n)
        if blocked:
            msg = blocked_message(blocked)
            print("::error::%s" % msg)
            print(msg)
            return 1
        print("close-gate: all close targets verified — pass")
        return 0
    except Exception as e:  # noqa: BLE001 - fail closed, with a diagnosis
        print("::error::PR CLOSE GATE FAILED: %s" % e)
        print("close-gate: API/lookup failure — failing closed: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
