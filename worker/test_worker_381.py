#!/usr/bin/env python3
"""Regression tests for issue #381 (INS-373-374 finding 3, follow-up
to #371): empty-plan causes are conflated under one unknown-job
status, and a None (or non-string) job crashes parse_job.

Two gaps in the merged #376 fix (PR #376, squash `112e3785`):

1. `parse_job` returns [] for (a) malformed/unknown strings
   (`harvest-egx-poul`, bogus strings, empty string), (b) a
   `sweep-lite` whose trailing filter validation deliberately
   rejects it (`market=XX` -> empty plan), and (c) unknown
   category/tool selections — all three landed as the same
   `unknown-job` failure with nothing distinguishing them.
   Fix: the manifest keeps the single `unknown-job` umbrella status
   (test_worker_371 pins it) and records the cause beside it
   (`manifest["unknown_job_cause"]`: "empty-job" / "unknown-syntax"
   / "invalid-selection"), so a deliberately rejected selection is
   distinguished in the record from unknown syntax.

2. A None (or non-string) job crashed instead of failing closed:
   the special dispatches guard with `(job["job"] or "")` but
   `parse_job(job["job"], reg)` passed the raw value and parse_job
   did `job.split()` unguarded — None.split() raises AttributeError
   inside _execute_body after intent persistence, leaving an
   uncertain intent. Fix: normalize the `job` field once at the top
   of _execute_body — None becomes "" (empty job string, failed
   closed by the #371 branch); any other non-string type is
   rejected explicitly with a named `invalid-job-type` failure.
   The other unguarded uses in worker.py (publish()'s
   `job["job"].lower()`, the harvest-pointer guard, run_harvest's
   `.split()`, the `(job.get("job") or "").split()` kind checks)
   go through the same `job_text()` normalization.

Harness-first: FAILS on pristine main (None / non-string jobs raise
AttributeError out of _execute_body; no `unknown_job_cause` is
recorded) and PASSES on the fixed tree. Stdlib only.
publish/_mark_done are stubbed at the worker-module boundary while
_execute_body itself runs for real; git/network are stubbed (fake
sh).

Run: python3 worker/test_worker_381.py (exit 0 = all pass).
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator381-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


class FakeResult:
    def __init__(self, rc=0, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def fake_sh(cmd, cwd=None, env=None, timeout=3600):
    """Fake worker.sh: perform `rm -rf` for real; everything else
    (git, fetch, merge/compile/render hooks) succeeds with empty
    output — the bad-job paths must never reach a tool anyway."""
    if cmd.startswith("rm -rf "):
        shutil.rmtree(cmd[len("rm -rf "):].strip(), ignore_errors=True)
        return FakeResult(0)
    return FakeResult(0)


def setup_release():
    """Fake release checkout: a minimal registry with one active
    tool (registry() reads it before parse_job runs)."""
    code = worker.CODE
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(json.dumps({
        "tools": [{"id": "vectorbt", "status": "active",
                   "category": "technical", "markets": ["EGX"],
                   "command": "echo {ticker}",
                   "ref": "0" * 40,
                   "repo": "vectorbt-runner"}]}),
        encoding="utf-8")


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    return "fake-archive-sha-381"


def stub_mark_done(job, archive_sha):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive_sha"] = archive_sha


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


def test_none_job_fails_closed_named():
    pub, done = run_execute({
        "id": "test-381-null",
        "job": None,
        "added": worker.now()})
    check("None job: named unknown-job failure in the manifest, "
          "never an AttributeError out of _execute_body",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check("None job: cause recorded as empty-job",
          pub.get("manifest", {}).get("unknown_job_cause")
          == "empty-job")
    check("None job: raw None value stays recorded in the "
          "manifest as evidence",
          pub.get("manifest", {}).get("job", {}).get("job") is None)
    check("None job: still publishes + marks done-with-failure",
          pub.get("manifest") is not None
          and done.get("archive_sha") == "fake-archive-sha-381")


def test_non_string_job_rejected_with_named_failure():
    for raw in (123, ["sweep-lite", "POUL.CA"], {"kind": "sweep-lite"},
                True):
        pub, done = run_execute({
            "id": "test-381-type",
            "job": raw,
            "added": worker.now()})
        check(f"non-string job {raw!r}: named invalid-job-type "
              "failure, never an AttributeError",
              pub.get("manifest", {}).get("tools")
              == {"invalid-job-type": "invalid-job-type"})
        check(f"non-string job {raw!r}: raw value stays recorded "
              "in the manifest as evidence",
              pub.get("manifest", {}).get("job", {}).get("job")
              == raw)
        check(f"non-string job {raw!r}: still publishes + marks "
              "done-with-failure",
              done.get("archive_sha") == "fake-archive-sha-381")


def test_rejected_filter_distinguished_from_unknown_syntax():
    pub, done = run_execute({
        "id": "test-381-filter",
        "job": "sweep-lite POUL.CA market=XX",
        "added": worker.now()})
    check("sweep-lite with a deliberately rejected filter: keeps "
          "the unknown-job umbrella status (test_worker_371 pins "
          "it)",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check("sweep-lite with a deliberately rejected filter: cause "
          "is invalid-selection, not unknown syntax",
          pub.get("manifest", {}).get("unknown_job_cause")
          == "invalid-selection")
    check("sweep-lite with a deliberately rejected filter: still "
          "publishes + marks done-with-failure",
          done.get("archive_sha") == "fake-archive-sha-381")


def test_unknown_syntax_cause():
    pub, done = run_execute({
        "id": "test-381-syntax",
        "job": "harvest-egx-poul",
        "added": worker.now()})
    check("unknown syntax 'harvest-egx-poul': keeps the "
          "unknown-job umbrella status",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"})
    check("unknown syntax 'harvest-egx-poul': cause is "
          "unknown-syntax",
          pub.get("manifest", {}).get("unknown_job_cause")
          == "unknown-syntax")
    check("unknown syntax 'harvest-egx-poul': still publishes + "
          "marks done-with-failure",
          done.get("archive_sha") == "fake-archive-sha-381")


def test_empty_string_cause():
    pub, done = run_execute({
        "id": "test-381-empty",
        "job": "",
        "added": worker.now()})
    check("empty job string: unknown-job failure with cause "
          "empty-job",
          pub.get("manifest", {}).get("tools")
          == {"unknown-job": "unknown-job"}
          and pub.get("manifest", {}).get("unknown_job_cause")
          == "empty-job")
    check("empty job string: still publishes + marks "
          "done-with-failure",
          done.get("archive_sha") == "fake-archive-sha-381")


def test_parsers_never_raise_on_bad_types():
    reg = worker.registry()
    check("parse_job(None) returns [] instead of raising",
          worker.parse_job(None, reg) == [])
    check("parse_job(123) returns [] instead of raising",
          worker.parse_job(123, reg) == [])
    check("parse_job(['run']) returns [] instead of raising",
          worker.parse_job(["run"], reg) == [])
    check("parse_top30_job(None) returns None instead of raising",
          worker.parse_top30_job(None) is None)
    check("parse_top30_job(123) returns None instead of raising",
          worker.parse_top30_job(123) is None)
    check("parse_diag_egx_ab_job(None) returns None instead of "
          "raising",
          worker.parse_diag_egx_ab_job(None) is None)
    check("parse_diag_egx_ab_job(123) returns None instead of "
          "raising",
          worker.parse_diag_egx_ab_job(123) is None)
    check("job_text normalizes None to ''",
          worker.job_text({"job": None}) == "")
    check("job_text normalizes a non-string to ''",
          worker.job_text({"job": 123}) == "")
    check("job_text passes a real job string through unchanged",
          worker.job_text({"job": "sweep-lite POUL.CA"})
          == "sweep-lite POUL.CA")


def test_cause_classifier():
    check("classifier: '' -> empty-job",
          worker.classify_empty_plan("") == "empty-job")
    check("classifier: None -> empty-job",
          worker.classify_empty_plan(None) == "empty-job")
    check("classifier: 'bogus' -> unknown-syntax",
          worker.classify_empty_plan("bogus") == "unknown-syntax")
    check("classifier: 'run vectorbt' (missing ticker) -> "
          "unknown-syntax",
          worker.classify_empty_plan("run vectorbt")
          == "unknown-syntax")
    check("classifier: 'run bogus-tool POUL' -> "
          "invalid-selection",
          worker.classify_empty_plan("run bogus-tool POUL")
          == "invalid-selection")
    check("classifier: 'category bogus POUL' -> "
          "invalid-selection",
          worker.classify_empty_plan("category bogus POUL")
          == "invalid-selection")
    check("classifier: 'sweep-lite POUL badtoken' -> "
          "invalid-selection",
          worker.classify_empty_plan("sweep-lite POUL badtoken")
          == "invalid-selection")


def test_valid_jobs_still_parse():
    """Control: the gate is the EMPTY plan only — valid job strings
    must still parse to a non-empty plan (parse_job level; no tool
    is executed here)."""
    reg = worker.registry()
    check("control: 'run vectorbt POUL' still parses to a plan",
          worker.parse_job("run vectorbt POUL", reg)
          == [("vectorbt", "POUL")])
    check("control: 'sweep-lite POUL market=EGX' still parses to "
          "a plan",
          worker.parse_job("sweep-lite POUL market=EGX", reg)
          == [("vectorbt", "POUL")])


def main():
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    test_none_job_fails_closed_named()
    test_non_string_job_rejected_with_named_failure()
    test_rejected_filter_distinguished_from_unknown_syntax()
    test_unknown_syntax_cause()
    test_empty_string_cause()
    test_parsers_never_raise_on_bad_types()
    test_cause_classifier()
    test_valid_jobs_still_parse()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
