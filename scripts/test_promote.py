#!/usr/bin/env python3
"""Tests for scripts/promote.py (issue #145, frozen-candidate promotion).

Stdlib only, no network — the pure checks take plain dicts, and the
CLI commands run against a FakeReq that replays canned GitHub API
responses. Mirrors the repo convention (scripts/test_benchmark79.py).

Usage: python3 scripts/test_promote.py
Exit 0 only when every test passes.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import promote  # noqa: E402

REVIEWED = "e19e769d4011bc6cd9afe486c2237161a1d32ef2"
OTHER = "134322f0" + "0" * 32
BASE_TIP = "66c9c92ebff78e955bb9134459f971bcc77225a7"

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


def frozen_pr(head_sha=REVIEWED, head_ref=None, base="worker-release",
              state="open", mergeable=True, body=None):
    return {
        "number": 165, "state": state, "merged": False,
        "head": {"sha": head_sha,
                 "ref": head_ref or promote.frozen_branch_name(REVIEWED)},
        "base": {"ref": base, "sha": BASE_TIP},
        "mergeable": mergeable,
        "body": body if body is not None else
                "Promotes one commit.\n\nReviewed-SHA: %s\n" % REVIEWED,
    }


# --- pure checks ---

check("branch-name", promote.frozen_branch_name(REVIEWED) ==
      "promote/e19e769d4011")
check("trailer", promote.reviewed_sha_trailer(REVIEWED) ==
      "Reviewed-SHA: " + REVIEWED)
check("parse-trailer", promote.parse_reviewed_sha(
    "text\n\nReviewed-SHA: %s\n" % REVIEWED) == REVIEWED)
check("parse-trailer-missing",
      promote.parse_reviewed_sha("no trailer here") is None)
check("parse-trailer-short",
      promote.parse_reviewed_sha("Reviewed-SHA: abc123") is None)

check("verify-pass",
      promote.verify_pr_frozen(frozen_pr(), REVIEWED) == [])
check("verify-drifted",
      any("!= reviewed SHA" in v for v in
          promote.verify_pr_frozen(frozen_pr(head_sha=OTHER), REVIEWED)),
      "drifted head must fail")
check("verify-from-main",
      any("live main" in v for v in promote.verify_pr_frozen(
          frozen_pr(head_ref="main"), REVIEWED)),
      "head from main must fail")
check("verify-wrong-branch",
      any("frozen branch" in v for v in promote.verify_pr_frozen(
          frozen_pr(head_ref="promote/deadbeefcafe"), REVIEWED)),
      "non-frozen branch must fail")
check("verify-wrong-base",
      any("base is" in v for v in promote.verify_pr_frozen(
          frozen_pr(base="main"), REVIEWED)),
      "wrong base must fail")
check("verify-closed",
      any("not open" in v for v in promote.verify_pr_frozen(
          frozen_pr(state="closed"), REVIEWED)),
      "closed PR must fail")
check("verify-unmergeable",
      any("not mergeable" in v for v in promote.verify_pr_frozen(
          frozen_pr(mergeable=False), REVIEWED)),
      "unmergeable PR must fail")
check("verify-no-sha",
      promote.verify_pr_frozen(frozen_pr(), None) != [],
      "missing reviewed SHA must fail")

# The exact #144 shape: PR opened from main whose head drifted past
# the reviewed SHA (32704d7f -> 134322f) must fail the gate twice over.
pr144 = {"number": 144, "state": "open", "merged": False,
         "head": {"sha": OTHER,
                  "ref": "main"},
         "base": {"ref": "worker-release", "sha": BASE_TIP},
         "mergeable": True, "body": ""}
v144 = promote.verify_pr_frozen(pr144, "32704d7f" + "0" * 32)
check("verify-pr144-shape", len(v144) >= 2 and
      any("live main" in v for v in v144) and
      any("!= reviewed SHA" in v for v in v144), str(v144))

merged_pr = frozen_pr()
merged_pr.update({"merged": True, "merged_at": "2026-11-17T19:00:00Z",
                  "merge_commit_sha": "m" * 40})
merge_commit = {"sha": "m" * 40,
                "parents": [{"sha": BASE_TIP}, {"sha": REVIEWED}]}
check("verify-merge-pass",
      promote.verify_merge(merged_pr, merge_commit, REVIEWED,
                           REVIEWED) == [])
check("verify-merge-wrong-parent",
      any("second parent" in v for v in promote.verify_merge(
          merged_pr, {"parents": [{"sha": BASE_TIP}, {"sha": OTHER}]},
          REVIEWED, REVIEWED)),
      "merge of unreviewed head must fail")
check("verify-merge-unmerged",
      promote.verify_merge(frozen_pr(), merge_commit, REVIEWED) != [],
      "unmerged PR must fail record")
check("verify-merge-squash-pass",
      promote.verify_merge(
          merged_pr, {"parents": [{"sha": BASE_TIP}]}, REVIEWED,
          REVIEWED) == [])
check("verify-merge-squash-drifted",
      promote.verify_merge(
          merged_pr, {"parents": [{"sha": BASE_TIP}]}, REVIEWED,
          OTHER) != [],
      "squash of drifted head must fail")
check("verify-merge-squash-unrecorded",
      any("not recorded" in v for v in promote.verify_merge(
          merged_pr, {"parents": [{"sha": BASE_TIP}]}, REVIEWED, None)),
      "squash without recorded pre-merge head must fail")
check("verify-merge-three-parents",
      promote.verify_merge(
          merged_pr,
          {"parents": [{"sha": "a" * 40}, {"sha": "b" * 40},
                      {"sha": "c" * 40}]}, REVIEWED, REVIEWED) != [])

# --- CLI commands against a fake API ---

class FakeReq:
    """Minimal canned GitHub API: GET PR / commit, PUT merge."""
    def __init__(self, pr, merge_sha="f" * 40):
        self.pr = dict(pr)
        self.merge_sha = merge_sha
        self.calls = []

    def __call__(self, method, path, body=None):
        self.calls.append((method, path))
        if method == "GET" and path.endswith("/pulls/165"):
            return 200, dict(self.pr)
        if method == "GET" and "/git/commits/" in path:
            sha = path.rsplit("/", 1)[-1]
            if sha == self.merge_sha:
                return 200, {"sha": sha, "parents": [
                    {"sha": BASE_TIP}, {"sha": REVIEWED}]}
            return 200, {"sha": sha}
        if method == "PUT" and path.endswith("/merge"):
            self.pr["merged"] = True
            self.pr["merge_commit_sha"] = self.merge_sha
            return 200, {"merged": True, "sha": self.merge_sha,
                         "message": "merged",
                         "merged_at": "2026-11-17T19:00:00Z"}
        return 404, {"error": "unexpected %s %s" % (method, path)}


def ns(**kw):
    return argparse.Namespace(**kw)


fake = FakeReq(frozen_pr())
check("cmd-verify-pass",
      promote.cmd_verify(fake, ns(pr="165", sha=REVIEWED)) == 0)
fake = FakeReq(frozen_pr(head_sha=OTHER))
check("cmd-verify-drifted-refuses",
      promote.cmd_verify(fake, ns(pr="165", sha=REVIEWED)) == 1)
fake = FakeReq(frozen_pr())
check("cmd-merge-pass",
      promote.cmd_merge(fake, ns(pr="165", sha=REVIEWED)) == 0)
check("cmd-merge-called-put",
      any(m == "PUT" for m, _ in fake.calls))
fake = FakeReq(frozen_pr(head_sha=OTHER))
check("cmd-merge-drifted-refuses",
      promote.cmd_merge(fake, ns(pr="165", sha=REVIEWED)) == 1 and
      not any(m == "PUT" for m, _ in fake.calls),
      "drifted PR must never reach the merge call")
merged = frozen_pr()
merged.update({"merged": True, "merged_at": "2026-11-17T19:00:00Z",
               "merge_commit_sha": "f" * 40})
fake = FakeReq(merged)
check("cmd-record-pass",
      promote.cmd_record(fake, ns(pr="165", sha=REVIEWED)) == 0)
fake = FakeReq(frozen_pr())
check("cmd-record-unmerged-refuses",
      promote.cmd_record(fake, ns(pr="165", sha=REVIEWED)) == 1)

print("\n%d passed, %d failed" % (PASSED, len(FAILED)))
if FAILED:
    print("failed:", FAILED)
    sys.exit(1)
print("ALL TESTS PASSED")
