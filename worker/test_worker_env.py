#!/usr/bin/env python3
"""Regression tests for issue #146: a filtered tool env must never
be merged back into the full parent env.

The bug: sh() did `e = dict(os.environ); e.update(env)`, so the
ENV_DENY_FOR_TOOLS filtering in run_tool (which strips GATOR_BUS_URL)
was undone at the final subprocess boundary and the bus
write-credential reached every tool process — tools have dumped env
in debug logs before, and results are pushed to a public archive.

All credential values here are clearly-fake sentinels, never real
secrets. Run: python3 worker/test_worker_env.py (exit 0 = all pass).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import worker

SENTINEL = "SENTINEL-BUS-URL-VALUE"
PASSED = 0


def check(name, cond):
    global PASSED
    assert cond, name
    PASSED += 1
    print(f"pass: {name}")


def filtered_env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in worker.ENV_DENY_FOR_TOOLS}
    if extra:
        env.update(extra)
    return env


def main():
    os.environ["GATOR_BUS_URL"] = SENTINEL
    os.environ["GATOR_PARENT_ONLY"] = "parent-only-value"

    # 1. sh(): a denied key present in the parent env must not reach
    # the child even when the caller passes the filtered env.
    r = worker.sh("printenv GATOR_BUS_URL || echo ABSENT",
                  env=filtered_env())
    check("sh() child does not see GATOR_BUS_URL",
          r.stdout.strip() == "ABSENT")

    # 2. sh_bash(): the exact path run_tool uses for tools.
    r = worker.sh_bash("printenv GATOR_BUS_URL || echo ABSENT",
                       env=filtered_env())
    check("sh_bash() child does not see GATOR_BUS_URL",
          r.stdout.strip() == "ABSENT")

    # 3. Generality: every ENV_DENY_FOR_TOOLS entry is kept out, not
    # just GATOR_BUS_URL. Prove it with a second, temporary entry.
    worker.ENV_DENY_FOR_TOOLS.add("GATOR_TEST_DENY")
    os.environ["GATOR_TEST_DENY"] = "SENTINEL-SECOND-DENY"
    try:
        r = worker.sh("printenv GATOR_TEST_DENY || echo ABSENT",
                      env=filtered_env())
        check("sh() child does not see a second denied key",
              r.stdout.strip() == "ABSENT")
    finally:
        worker.ENV_DENY_FOR_TOOLS.discard("GATOR_TEST_DENY")
        os.environ.pop("GATOR_TEST_DENY", None)

    # 4. A supplied env is the COMPLETE env: a parent-only var that
    # the caller did not pass must not leak through either. (Note:
    # run_tool's filtered env is a full copy of os.environ, so in
    # production this var WOULD be passed — this check proves the
    # boundary itself no longer merges, using a deliberately partial
    # supplied env.)
    partial = filtered_env()
    partial.pop("GATOR_PARENT_ONLY", None)
    r = worker.sh("printenv GATOR_PARENT_ONLY || echo ABSENT",
                  env=partial)
    check("sh() does not merge parent-only vars back in",
          r.stdout.strip() == "ABSENT")

    # 5. Supplied vars still reach the child (the env is used, not
    # dropped).
    r = worker.sh("printenv GATOR_TOOL_MARKER || echo ABSENT",
                  env=filtered_env({"GATOR_TOOL_MARKER": "marker-value"}))
    check("sh() passes supplied vars through",
          r.stdout.strip() == "marker-value")

    # 6. Fail closed: a supplied env that (wrongly) contains a denied
    # key must raise at the boundary instead of spawning the child.
    try:
        worker.sh("true", env={"GATOR_BUS_URL": SENTINEL})
    except AssertionError as e:
        check("sh() raises on a denied key in the supplied env",
              "GATOR_BUS_URL" in str(e))
    else:
        raise AssertionError("sh() did not raise on denied key")

    # 7. The guard helper itself (also used by maybe_merge's direct
    # subprocess.run call) rejects a denied env.
    try:
        worker._assert_no_denied({"GATOR_BUS_URL": SENTINEL})
    except AssertionError:
        check("_assert_no_denied rejects a denied env", True)
    else:
        raise AssertionError("_assert_no_denied did not raise")

    # 8. Worker-internal behaviour is preserved: with no env
    # supplied, the parent env still flows through (git/bus plumbing
    # runs as the worker itself, not as a tool).
    r = worker.sh("printenv GATOR_PARENT_ONLY || echo ABSENT")
    check("sh() with env=None still passes the parent env",
          r.stdout.strip() == "parent-only-value")

    print(f"\n{PASSED}/8 passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
