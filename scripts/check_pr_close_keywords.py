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
and BLOCKS THE MERGE while the text GitHub will parse for auto-close
at merge — the PR title, the PR body AND the branch commit messages —
carries a closing keyword (``Fixes`` / ``Closes`` / ``Resolves`` and
variants) referencing an issue in this repo that does NOT yet carry the
``verified`` label. The close is therefore deferred, not repaired
after the fact. Scanning the body alone was the #432 bypass: PR #430
merged 2026-11-20T14:08:39Z with body "For #425" (gate green
14:07:29Z) but title "Fix #425: ..." and a branch commit message
identical to title + body; the squash commit 44b031d2 reads
"Fix #425: ..." and #425 closed 14:08:41Z, reopened 14:08:54Z by
borsagator[bot]. The title/body/commit union is the merge-time text
for this repo's settings (squash + merge-commit + rebase all allowed;
squash_merge_commit_message=COMMIT_MESSAGES, merge_commit_message=
PR_TITLE — read 2026-11-20).

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
PR_NUMBER to skip the API fetch (labels are still read from the API);
PR_TITLE and PR_COMMIT_MESSAGES (a JSON list of commit-message
strings) default to empty when unset, so a body-only local check
keeps working.
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
    """Issue numbers in `repo` a PR's merge message would auto-close.

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


def _api_get(url, token):
    """GET a GitHub API URL, returning (parsed JSON, Link header)."""
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "borsagator-pr-close-gate",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read()), resp.headers.get("Link") or ""


def fetch_pr(number, token, repo=DEFAULT_REPO):
    """PR title + body + commit count from the API (never the event
    payload — see #198). The `commits` count is the ground truth the
    commit-fetch coverage check compares against (see #433)."""
    pr, _ = _api_get(f"{API}/repos/{repo}/pulls/{number}", token)
    return {"title": pr.get("title") or "", "body": pr.get("body") or "",
            "commits": pr.get("commits")}


class IncompleteCommitCoverage(RuntimeError):
    """The PR-commits endpoint could not return every commit.

    Carries the partial message list in `fetched` and the PR's total
    commit count in `expected`, so callers can fail closed on the
    partial set instead of silently treating it as complete.
    """

    def __init__(self, message, fetched, expected):
        super().__init__(message)
        self.fetched = fetched
        self.expected = expected


def fetch_pr_commit_messages(number, token, repo=DEFAULT_REPO,
                             expected_total=None):
    """Messages of every commit on the PR, following pagination.

    These land on main under rebase, and under squash when the repo's
    squash message is COMMIT_MESSAGES (this repo's setting) — so they
    are part of the text GitHub parses for auto-close at merge.

    Coverage: the list-PR-commits endpoint returns at most 250 commits,
    even with pagination (docs.github.com/en/rest/pulls/pulls), and
    answers 200 with a shorter array rather than saying it stopped —
    so pagination alone cannot prove completeness. When
    `expected_total` (the PR object's `commits` count) is given and
    fewer messages were fetched, raise IncompleteCommitCoverage so the
    caller fails closed instead of passing a PR whose commit 251 might
    carry the closing keyword (CodeRabbit on PR #433).
    """
    messages = []
    url = (f"{API}/repos/{repo}/pulls/{number}/commits"
           "?per_page=100")
    while url:
        page, link = _api_get(url, token)
        messages.extend(c.get("commit", {}).get("message") or ""
                        for c in page)
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
    if (expected_total is not None
            and len(messages) < expected_total):
        raise IncompleteCommitCoverage(
            "incomplete commit coverage for PR #%s: fetched %d of %d "
            "commits (the list-PR-commits endpoint caps at 250) — "
            "cannot prove no later commit carries a closing keyword"
            % (number, len(messages), expected_total),
            fetched=messages, expected=expected_total)
    return messages


def merge_message_text(title, body, commit_messages):
    """The text GitHub parses for auto-close when this PR merges.

    The union of the PR title, the PR body and the branch commit
    messages: the squash message is composed from the title plus the
    commit messages (this repo: squash_merge_commit_message=
    COMMIT_MESSAGES), a merge commit carries the PR title
    (merge_commit_message=PR_TITLE), and rebase lands each commit
    message verbatim. Empty parts are skipped.
    """
    parts = [title or "", body or ""]
    parts.extend(commit_messages or [])
    return "\n\n".join(p for p in parts if p)


def fetch_pr_body(number, token, repo=DEFAULT_REPO):
    """PR body from the API (kept for callers that only need the body)."""
    return fetch_pr(number, token, repo)["body"]


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    token = os.environ.get("GH_TOKEN", "")
    title = os.environ.get("PR_TITLE")
    body = os.environ.get("PR_BODY")
    commits_env = os.environ.get("PR_COMMIT_MESSAGES")
    number = os.environ.get("PR_NUMBER")
    try:
        if body is None:
            if not number:
                raise RuntimeError(
                    "PR_NUMBER (or PR_BODY for a local check) is required")
            if not token:
                raise RuntimeError("GH_TOKEN is required")
            print("close-gate: fetching PR #%s from the API" % number)
            pr = fetch_pr(number, token, repo)
            title = pr["title"]
            body = pr["body"]
            if pr.get("commits") is None:
                raise RuntimeError(
                    "PR #%s object carries no commit count — cannot "
                    "establish commit coverage, failing closed" % number)
            commit_messages = fetch_pr_commit_messages(
                number, token, repo, expected_total=pr["commits"])
        else:
            title = title or ""
            if commits_env:
                commit_messages = json.loads(commits_env)
                if (not isinstance(commit_messages, list)
                        or not all(isinstance(m, str)
                                   for m in commit_messages)):
                    raise ValueError(
                        "PR_COMMIT_MESSAGES must be a JSON list of strings")
            else:
                commit_messages = []
        # The gate scans the merge message (title + body + commit
        # messages), not the body alone — see #432: the closing keyword
        # that auto-closed #425 lived in PR #430's title and commit
        # message, while its body said only "For #425".
        text = merge_message_text(title, body, commit_messages)
        targets = find_close_targets(text, repo)
        if not targets:
            print("close-gate: no closing keyword references in the "
                  "merge message %s — pass" % repo)
            return 0
        print("close-gate: closing keyword(s) in the merge message "
              "target %s"
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
