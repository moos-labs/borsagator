#!/usr/bin/env python3
"""Frozen-candidate promotion to worker-release (issue #145).

The bug (F1, panel round 12): promotion PRs were opened FROM live
`main` (PR #144: head drifted 32704d7f -> 8f1d76a -> 134322f under
review as guard heartbeats landed on main). With
`dismiss_stale_reviews` OFF an approval survives head changes, so
any commit landing on main before merge promotes unreviewed — and
the worker's ancestry guard passes, because a merge commit is a
descendant of the current release tip. That defeats D2's
"unreviewed code never runs with the keys in its environment."

The fix is structural, not a review-count tweak (worker-release
now requires 0 approving reviews, so review settings are moot
there anyway):

1. A promotion PR is opened from a dedicated branch
   `promote/<reviewed-sha-12>` pinned to the EXACT reviewed SHA —
   never from live `main`. The branch cannot drift: nothing else
   ever commits to it, so the head at merge time is the head that
   was reviewed.
2. The reviewed SHA is recorded in the PR body as a
   `Reviewed-SHA: <40-hex>` trailer.
3. `verify` (pre-merge gate) refuses the merge unless the PR head
   SHA == the reviewed SHA, the head branch is the frozen branch
   (not `main`), and the base is `worker-release`.
4. `merge` runs the gate, merges with method "merge", then checks
   the merge commit's second parent == the reviewed SHA. On any
   mismatch it exits non-zero and refuses to record the promotion.
5. `record` (post-merge) re-verifies the merged PR and prints the
   promotion-log row to append — nothing is recorded as a promotion
   unless the merged SHA matches the reviewed SHA.

The worker's own ancestry guard (worker/worker.py `self_update`)
cannot enforce this: it has no source for the reviewed SHA, it
only knows the release tip is a descendant of the running code.
The enforcement point is therefore here, at promotion time, plus
the `promotion-gate` workflow, which fails any PR to
worker-release whose head is `main` or whose head SHA differs
from the `Reviewed-SHA:` trailer in its body.

GitHub API calls use the same dynamic_credentials surrogate
pattern as the issue-65 helper scripts. The pure checks
(`verify_pr_frozen`, `verify_merge`, `parse_reviewed_sha`) take
plain dicts and are covered by scripts/test_promote.py with no
network.

Usage:
  python3 scripts/promote.py open   --sha <reviewed-sha> --title T [--body B | --body-file F]
  python3 scripts/promote.py verify --pr N [--sha <reviewed-sha>]
  python3 scripts/promote.py merge  --pr N [--sha <reviewed-sha>]
  python3 scripts/promote.py record --pr N [--sha <reviewed-sha>]
Exit 0 only when the requested step passes; any gate failure exits 1.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request

BASE = "https://api.github.com"
REPO_PATH = "/repos/moos-labs/borsagator"
REPO = "moos-labs/borsagator"
BASE_BRANCH = "worker-release"
SHA_RE = re.compile(r"[0-9a-f]{40}")
TRAILER_RE = re.compile(r"^Reviewed-SHA:\s*([0-9a-f]{40})\s*$", re.MULTILINE)


def frozen_branch_name(sha):
    """Dedicated frozen-candidate branch for a reviewed SHA."""
    return "promote/%s" % sha[:12]


def reviewed_sha_trailer(sha):
    return "Reviewed-SHA: %s" % sha


def parse_reviewed_sha(body):
    """Reviewed SHA from a PR body's Reviewed-SHA trailer, or None."""
    if not body:
        return None
    m = TRAILER_RE.search(body)
    return m.group(1) if m else None


def verify_pr_frozen(pr, reviewed_sha):
    """Pre-merge gate: the PR must be exactly the frozen candidate.

    Returns a list of violations (empty = pass). Checks, in order:
    reviewed SHA well-formed; PR open; base is worker-release;
    head branch is the frozen branch (never live main); head SHA
    equals the reviewed SHA (no drift); PR mergeable.
    """
    violations = []
    if not reviewed_sha or not SHA_RE.fullmatch(reviewed_sha):
        violations.append(
            "no valid reviewed SHA (need Reviewed-SHA: <40-hex> "
            "trailer or --sha)")
        return violations
    if pr.get("state") != "open":
        violations.append("PR is not open (state=%s)" % pr.get("state"))
    base = pr.get("base") or {}
    if base.get("ref") != BASE_BRANCH:
        violations.append(
            "base is %r, not %r" % (base.get("ref"), BASE_BRANCH))
    head = pr.get("head") or {}
    head_ref = head.get("ref")
    if head_ref == "main":
        violations.append(
            "head branch is live main — promotion PRs must come from "
            "a frozen promote/<sha> branch (issue #145)")
    elif head_ref != frozen_branch_name(reviewed_sha):
        violations.append(
            "head branch is %r, not the frozen branch %r"
            % (head_ref, frozen_branch_name(reviewed_sha)))
    head_sha = head.get("sha")
    if head_sha != reviewed_sha:
        violations.append(
            "head SHA %s != reviewed SHA %s — candidate drifted; "
            "re-freeze from the reviewed SHA" % (head_sha, reviewed_sha))
    if pr.get("mergeable") is False:
        violations.append("PR is not mergeable")
    return violations


def verify_merge(pr, merge_commit, reviewed_sha, pre_merge_head_sha=None):
    """Post-merge gate: the merged SHA must be the reviewed SHA.

    For a "merge"-method merge commit (two parents) the second
    parent is the PR head, so it must equal the reviewed SHA. For
    a squash/fast-forward merge (one parent) the merge commit
    itself cannot prove the head, so the pre-merge head SHA
    recorded by the merger must be supplied and must equal the
    reviewed SHA. Returns a list of violations (empty = pass).
    """
    violations = []
    if not reviewed_sha or not SHA_RE.fullmatch(reviewed_sha):
        violations.append("no valid reviewed SHA")
        return violations
    if not pr.get("merged"):
        violations.append("PR is not merged")
        return violations
    parents = [p.get("sha") for p in (merge_commit or {}).get("parents", [])]
    if len(parents) == 2:
        if parents[1] != reviewed_sha:
            violations.append(
                "merge commit second parent %s != reviewed SHA %s — "
                "unreviewed code was merged" % (parents[1], reviewed_sha))
    elif len(parents) == 1:
        if pre_merge_head_sha is None:
            violations.append(
                "single-parent merge commit: pre-merge head SHA was not "
                "recorded, so the merged content cannot be tied to the "
                "reviewed SHA — refuse to record")
        elif pre_merge_head_sha != reviewed_sha:
            violations.append(
                "pre-merge head SHA %s != reviewed SHA %s — unreviewed "
                "code was merged" % (pre_merge_head_sha, reviewed_sha))
    else:
        violations.append(
            "merge commit has %d parents, expected 1 or 2" % len(parents))
    return violations


def promotion_log_row(pr, reviewed_sha, merge_sha):
    return "| %s | `%s` | PR #%s (frozen `%s`, reviewed `%s`) |" % (
        (pr.get("merged_at") or "")[:19].replace("T", " "),
        merge_sha or "",
        pr.get("number"),
        (pr.get("head") or {}).get("ref"),
        reviewed_sha)


# --- GitHub API (surrogate pattern, as in the issue-65 scripts) ---

def make_req():
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    try:
        from dynamic_credentials import (  # noqa: E402
            add_surrogate_to_request, read_response_body)
    except ImportError as e:
        print("GitHub auth unavailable (dynamic_credentials import "
              "failed: %s); refusing to call the API" % e,
              file=sys.stderr)
        sys.exit(2)

    def req(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(BASE + path, data=data, method=method)
        add_surrogate_to_request(r, "custom.github",
                                 allowed_hosts=["api.github.com"])
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = read_response_body(resp)
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode() if hasattr(e, "read") else ""
            return e.code, {"error": raw[:500]}

    return req


def get_pr(req, number):
    st, pr = req("GET", "%s/pulls/%s" % (REPO_PATH, number))
    assert st == 200, pr
    return pr


def reviewed_sha_for(req, pr, sha_arg):
    if sha_arg:
        return sha_arg
    return parse_reviewed_sha(pr.get("body") or "")


def cmd_open(req, args):
    sha = args.sha.lower()
    assert SHA_RE.fullmatch(sha), "--sha must be a full 40-hex commit SHA"
    st, commit = req("GET", "%s/git/commits/%s" % (REPO_PATH, sha))
    assert st == 200, commit
    print("reviewed commit exists:", sha)
    branch = frozen_branch_name(sha)
    st, ref = req("GET", "%s/git/ref/heads/%s" % (REPO_PATH, branch))
    if st == 200:
        existing = ref["object"]["sha"]
        assert existing == sha, (
            "frozen branch %s already points at %s, not the reviewed "
            "SHA %s — refuse to reuse it" % (branch, existing, sha))
        print("frozen branch already exists at the reviewed SHA:", branch)
    elif st == 404:
        st, ref = req("POST", "%s/git/refs" % REPO_PATH,
                      {"ref": "refs/heads/%s" % branch, "sha": sha})
        assert st == 201, ref
        print("frozen branch created:", branch, "at", sha)
    else:
        raise AssertionError(ref)
    st, pulls = req(
        "GET", "%s/pulls?state=open&head=%s:%s&base=%s"
        % (REPO_PATH, REPO.split("/")[0], branch, BASE_BRANCH))
    assert st == 200, pulls
    assert not pulls, ("an open %s -> %s PR already exists (#%s) — stop"
                       % (branch, BASE_BRANCH, pulls[0]["number"]))
    body = args.body or ""
    if args.body_file:
        with open(args.body_file) as f:
            body = f.read()
    body = body.rstrip() + "\n\n" + reviewed_sha_trailer(sha) + "\n"
    st, pr = req("POST", "%s/pulls" % REPO_PATH,
                 {"title": args.title, "head": branch,
                  "base": BASE_BRANCH, "body": body})
    assert st == 201, pr
    print("PR created:", pr["number"])
    print("URL:", pr.get("html_url"))
    print("head:", pr["head"]["sha"], "branch:", pr["head"]["ref"],
          "base:", pr["base"]["sha"])
    assert pr["head"]["sha"] == sha, "created PR head != reviewed SHA — stop"
    return 0


def cmd_verify(req, args):
    pr = get_pr(req, args.pr)
    sha = reviewed_sha_for(req, pr, args.sha)
    violations = verify_pr_frozen(pr, sha)
    print("PR #%s head=%s branch=%s base=%s reviewed=%s"
          % (pr["number"], (pr.get("head") or {}).get("sha"),
             (pr.get("head") or {}).get("ref"),
             (pr.get("base") or {}).get("ref"), sha))
    if violations:
        print("FROZEN-CANDIDATE GATE FAILED:")
        for v in violations:
            print("  -", v)
        return 1
    print("FROZEN-CANDIDATE GATE PASSED: head == reviewed SHA", sha)
    return 0


def cmd_merge(req, args):
    pr = get_pr(req, args.pr)
    sha = reviewed_sha_for(req, pr, args.sha)
    violations = verify_pr_frozen(pr, sha)
    if violations:
        print("REFUSING TO MERGE — frozen-candidate gate failed:")
        for v in violations:
            print("  -", v)
        return 1
    pre_merge_head = (pr.get("head") or {}).get("sha")
    st, out = req("PUT", "%s/pulls/%s/merge" % (REPO_PATH, args.pr),
                  {"merge_method": "merge"})
    assert st == 200 and out.get("merged"), out
    merge_sha = out.get("sha")
    print("MERGED sha:", merge_sha)
    st, commit = req("GET", "%s/git/commits/%s" % (REPO_PATH, merge_sha))
    assert st == 200, commit
    violations = verify_merge(
        {"merged": True, "number": args.pr}, commit, sha, pre_merge_head)
    if violations:
        print("POST-MERGE CHECK FAILED — do NOT record this as a "
              "promotion:")
        for v in violations:
            print("  -", v)
        return 1
    print("POST-MERGE CHECK PASSED: merged SHA is the reviewed SHA", sha)
    print("promotion-log row:")
    print(promotion_log_row(
        {"merged_at": out.get("merged_at") or pr.get("merged_at") or "",
         "number": args.pr,
         "head": {"ref": frozen_branch_name(sha)}}, sha, merge_sha))
    return 0


def cmd_record(req, args):
    pr = get_pr(req, args.pr)
    sha = reviewed_sha_for(req, pr, args.sha)
    if not pr.get("merged"):
        print("PR #%s is not merged — nothing to record" % args.pr)
        return 1
    merge_sha = pr.get("merge_commit_sha")
    st, commit = req("GET", "%s/git/commits/%s" % (REPO_PATH, merge_sha))
    assert st == 200, commit
    head_sha = (pr.get("head") or {}).get("sha")
    violations = verify_merge(pr, commit, sha, head_sha)
    if violations:
        print("REFUSING TO RECORD PROMOTION — post-merge check failed:")
        for v in violations:
            print("  -", v)
        return 1
    print("PROMOTION VERIFIED: merged SHA is the reviewed SHA", sha)
    print("promotion-log row:")
    print(promotion_log_row(pr, sha, merge_sha))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Frozen-candidate promotion to worker-release (#145)")
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open", help="open a promotion PR from a frozen branch")
    o.add_argument("--sha", required=True, help="exact reviewed commit SHA")
    o.add_argument("--title", required=True)
    o.add_argument("--body", default="")
    o.add_argument("--body-file", default="")
    v = sub.add_parser("verify", help="pre-merge frozen-candidate gate")
    v.add_argument("--pr", required=True)
    v.add_argument("--sha", default="")
    m = sub.add_parser("merge", help="gate, merge, then verify the merge")
    m.add_argument("--pr", required=True)
    m.add_argument("--sha", default="")
    r = sub.add_parser("record", help="verify a merged PR and print its log row")
    r.add_argument("--pr", required=True)
    r.add_argument("--sha", default="")
    args = p.parse_args(argv)
    req = make_req()
    fn = {"open": cmd_open, "verify": cmd_verify,
          "merge": cmd_merge, "record": cmd_record}[args.cmd]
    return fn(req, args)


if __name__ == "__main__":
    sys.exit(main())
