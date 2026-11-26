#!/usr/bin/env python3
"""Tests for issue #502: deploy-guard correlation/target inputs
and the relay's evidence matching.

The workflows are GitHub Actions YAML, so — as with the repo's
other workflow-level guarantees — these are structural checks on
the workflow files themselves, plus a functional check of the
evidence-matching rule simulated in shell against fixture
evidence documents:

  deploy-guard.yml:
  - declares correlation_id + target_sha workflow_dispatch
    inputs;
  - checks out the target explicitly and verifies the actual
    HEAD equals it before running the parity check;
  - emits evidence (run id, correlation, target, verified HEAD)
    as a run artifact named by the correlation id;
  - never treats the run's head_sha as the target (with
    dispatch --ref main, head_sha is the workflow ref).

  ledger-publish-relay.yml:
  - dispatches deploy-guard with -f correlation_id and
    -f target_sha=<the verified merge commit>;
  - matches the evidence artifact's run id / correlation /
    target / verified HEAD against the dispatch before setting
    evidence=verified;
  - uses the recovered wording ONLY when the heartbeat status
    is ok AND the evidence is verified; an ok envelope with
    unverified evidence gets the NOT-confirmed wording.

Run: python3 scripts/test_deploy_guard_502.py (exit 0 = pass).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.path.abspath(__file__)).parent.parent
DEPLOY = (ROOT / ".github" / "workflows" / "deploy-guard.yml") \
    .read_text(encoding="utf-8")
RELAY = (ROOT / ".github" / "workflows"
         / "ledger-publish-relay.yml").read_text(encoding="utf-8")

PASSED = 0


def check(name, cond):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}")
        raise SystemExit(1)


def test_deploy_guard_structure():
    check("deploy: correlation_id input declared",
          "correlation_id:" in DEPLOY)
    check("deploy: target_sha input declared",
          "target_sha:" in DEPLOY)
    check("deploy: target checked out explicitly",
          'git checkout -q --detach "$TARGET"' in DEPLOY)
    check("deploy: actual HEAD verified against the target",
          '"$ACTUAL" != "$TARGET"' in DEPLOY
          and "refusing to verify the wrong commit" in DEPLOY)
    check("deploy: evidence artifact uploaded by correlation",
          "actions/upload-artifact@v4" in DEPLOY
          and "deploy-guard-evidence-${{ steps.target.outputs."
          "correlation_id }}" in DEPLOY.replace("\n", " "))
    check("deploy: evidence carries run/correlation/target/head",
          all(k in DEPLOY for k in
              ("run_id", "correlation_id", "target_sha",
               "verified_head")))
    check("deploy: head_sha never used as target evidence",
          "github.head_sha" not in DEPLOY
          and ".head_sha" not in DEPLOY)


def test_relay_structure():
    check("relay: dispatch passes correlation + target inputs",
          '-f correlation_id="$CORRELATION"' in RELAY
          and '-f target_sha="$MERGE_SHA"' in RELAY)
    check("relay: correlation is unique per relay run + slot",
          'CORRELATION="relay-${{ github.run_id }}-$RUN_ID"'
          in RELAY)
    check("relay: evidence artifact matched before verified",
          "deploy-guard-evidence-$CORRELATION" in RELAY
          and '"$EV_TARGET" = "$MERGE_SHA"' in RELAY
          and '"$EV_HEAD" = "$MERGE_SHA"' in RELAY
          and '"$EV_CORR" = "$CORRELATION"' in RELAY
          and '"$EV_RUN" = "$RUN_ID"' in RELAY)
    check("relay: recovered wording requires verified evidence",
          '"$HB_STATUS" = "ok" ] && [ "$DG_EVIDENCE" = '
          '"verified" ]' in RELAY)
    check("relay: ok + unverified gets NOT-confirmed wording",
          "recovery is NOT confirmed" in RELAY)


def _match(ev, run_id, corr, merge_sha):
    """The relay's matching rule, restated for the fixtures."""
    return (ev.get("run_id") == run_id
            and ev.get("correlation_id") == corr
            and ev.get("target_sha") == merge_sha
            and ev.get("verified_head") == merge_sha)


def test_evidence_matching_fixtures():
    merge = "a" * 40
    good = {"run_id": "4242", "correlation_id": "relay-9-slot-1",
            "target_sha": merge, "verified_head": merge,
            "parity": "success"}
    check("match: exact evidence verifies",
          _match(good, "4242", "relay-9-slot-1", merge))
    for name, ev in [
            ("wrong run", {**good, "run_id": "9999"}),
            ("wrong correlation",
             {**good, "correlation_id": "relay-8-slot-1"}),
            ("wrong target", {**good, "target_sha": "b" * 40}),
            ("head != target (ref, not target)",
             {**good, "verified_head": "c" * 40}),
            ("missing fields", {"run_id": "4242"})]:
        check(f"match: {name} does not verify",
              not _match(ev, "4242", "relay-9-slot-1", merge))
    # The fixture documents round-trip through jq exactly as the
    # relay reads them.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "evidence.json"
        p.write_text(json.dumps(good))
        out = subprocess.run(
            ["jq", "-r", ".verified_head", str(p)],
            capture_output=True, text=True, timeout=30)
        check("match: evidence JSON is jq-readable as the relay "
              "reads it", out.stdout.strip() == merge)


def test_515_review_fixes():
    # PR #515 review round (INS-REVIEW-089/092 + CodeRabbit):
    # structural checks for the blocker fixes in the workflows.
    check("515: deploy parity compares the verified target "
          "(HEAD), not origin/main",
          "--refs HEAD origin/archive" in DEPLOY)
    check("515: relay recheck fetch fails closed",
          "git fetch origin main || return 1" in RELAY)
    check("515: relay blob listing is captured, not process-"
          "substituted",
          'STAGE_LISTING=$(git ls-tree -r "$STAGE_SHA"' in RELAY
          and 'done <<< "$STAGE_LISTING"' in RELAY
          and "process substitution" in RELAY)
    check("515: relay refuses an empty staged listing",
          "lists no ledger content" in RELAY)
    check("515: relay fetches the staging branch before "
          "verifying", 'refs/remotes/origin/$BRANCH' in RELAY
          and "BRANCH: ${{ steps.resolve.outputs.branch }}"
          in RELAY)
    check("515: later-main inspection is non-fatal",
          'MAIN_HB=$(git show origin/main:ledger/'
          'guard-heartbeat.json 2>/dev/null || echo "")' in RELAY
          .replace("\n", " ") or
          '2>/dev/null || echo "")' in RELAY
          and "later main state unavailable" in RELAY)
    check("515: deploy run selected by correlation artifact, "
          "not timestamp alone",
          "for CAND in $CANDIDATES" in RELAY
          and 'select(.status==\\"completed\\")' in RELAY)
    check("515: verified evidence can replace an unverified "
          "comment (update in place)",
          "-X PATCH" in RELAY
          and "issues/comments/$EXISTING" in RELAY
          and "already carries this merge with the current body"
          in RELAY)
    check("515: assess scope check sees both sides of a "
          "rename", "--no-renames --name-only" in RELAY
          and "core.quotepath=false" in RELAY)


def test_093_review_fixes():
    # INS-REVIEW-093: landing verification binds the merge and
    # the frozen manifest, and freshness is validated against
    # the actual first-parent state.
    check("093: merge must have exactly two parents",
          'PARENT_COUNT=$(echo "$PARENTS" | wc -w)' in RELAY
          and '"$PARENT_COUNT" -ne 3' in RELAY)
    check("093: second parent must be the staged commit",
          '"$STAGE_PARENT" != "$STAGE_SHA"' in RELAY)
    check("093: frozen manifest from the staged commit's base",
          'diff --no-renames --name-only "$STAGE_SHA^" '
          '"$STAGE_SHA"' in RELAY)
    check("093: manifest deletions must be absent at the merge",
          "--diff-filter=D" in RELAY
          and "still present at merge" in RELAY)
    check("093: introduced paths are a subset of the manifest",
          'diff --no-renames --name-only "$FIRST_PARENT" '
          '"$MERGE_SHA"' in RELAY
          and "unexpected introduced path" in RELAY
          and "SUBSET of the manifest" in RELAY)
    check("093: freshness validated against the actual first "
          "parent before success wording",
          '--main-ref "$FIRST_PARENT"' in RELAY
          and RELAY.index('--main-ref "$FIRST_PARENT"')
          < RELAY.index("Publication verified at the original "
                        "merge commit"))


def _step_body(text, name):
    """Return the YAML block of one workflow step (from its
    `- name:` line to the next step at the same indent)."""
    start = text.index(f"- name: {name}")
    nxt = text.find("\n      - name:", start + 1)
    return text[start:] if nxt == -1 else text[start:nxt]


def test_105_app_token_narrowing():
    # INS-REVIEW-105 item 5: the Borsagator App token is pinned
    # to the full commit SHA of the action's v1 tag and minted
    # in fresh mode — a new PR and a reused PR both end at the
    # merge, so the mint is not conditioned on pr_number. The
    # App token is used for exactly the two operations whose
    # actor identity matters: CREATING the PR and MERGING it.
    # Since 2026-11-25 the merge-gate-approval ruleset requires
    # an approving review on main; GITHUB_TOKEN can neither
    # approve nor bypass it, so the merge runs as the App, an
    # always-bypass actor in that ruleset (PR #739, proven by
    # relay run 45788015824 merging PR #741 as borsagator[bot]).
    # Every other step runs on GITHUB_TOKEN, and reconciled /
    # non-fresh runs never touch the App key.
    check("105: app-token action pinned to the full v1 commit",
          "actions/create-github-app-token@"
          "d72941d797fd3113feb6b93fd0dec494b13a2547" in RELAY)
    check("105: no mutable app-token tag remains",
          "create-github-app-token@v1" not in RELAY)
    check("105: mint runs in fresh mode (new or reused PR)",
          "id: apptoken\n        if: steps.assess.outputs.mode "
          "== 'fresh'" in RELAY)
    check("105: only PR creation and merge use the App token",
          RELAY.count("steps.apptoken.outputs.token") == 2
          and "steps.apptoken.outputs.token"
          in _step_body(RELAY, "Open the PR")
          and "steps.apptoken.outputs.token"
          in _step_body(RELAY, "Merge the PR"))


def main():
    test_105_app_token_narrowing()
    test_093_review_fixes()
    test_deploy_guard_structure()
    test_relay_structure()
    test_evidence_matching_fixtures()
    test_515_review_fixes()
    print(f"\n{PASSED} checks passed")


if __name__ == "__main__":
    main()
