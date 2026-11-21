#!/usr/bin/env python3
"""Issue #450: sh_group must not let a descendant survive the
timeout just because the group leader died.

Round 4's kill loop SIGTERMs the group and breaks as soon as
communicate() returns — which happens when the leader is reaped
and the pipes close. A descendant that ignores SIGTERM *and*
redirects its descriptors lets both happen while it lives on,
free to overlap a later job on the shared checkout. The timeout
path must verify the group is empty (killpg(pgid, 0)) and
SIGKILL whatever remains before TimeoutExpired propagates.

Checks:
  - a normal command returns its rc and output (unchanged);
  - a plain timeout still raises TimeoutExpired;
  - the detached, SIGTERM-ignoring descendant is DEAD once the
    timeout returns (the round-4 code leaves it alive);
  - the descendant never reaches its delayed side effect.

Run: python3 test_worker_450_shgroup.py (exit 0 = all pass).
"""

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("GATOR_ROOT",
                      str(HERE / "_tmp_450_shgroup"))
sys.path.insert(0, str(HERE))
import _test_tmp  # noqa: E402,F401  (atexit cleanup, #388)
import worker  # noqa: E402

CHECKS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, cond):
    if cond:
        CHECKS["pass"] += 1
        print("pass:", name)
    else:
        CHECKS["fail"] += 1
        FAILURES.append(name)
        print("FAIL:", name)


def pid_alive(pid):
    """Alive = a live process, not a zombie (a killed orphan can
    linger as an unreaped zombie entry; kill(pid, 0) lies)."""
    try:
        stat = Path("/proc/%d/stat" % pid).read_text()
        state = stat.rsplit(")", 1)[1].split()[0]
        return state not in ("Z", "X")
    except (FileNotFoundError, IndexError):
        return False


def test_normal_and_plain_timeout():
    r = worker.sh_group("echo hello-450", timeout=30)
    check("normal command: rc 0 with output",
          r.returncode == 0 and "hello-450" in r.stdout)
    raised = False
    try:
        worker.sh_group("sleep 30", timeout=1)
    except subprocess.TimeoutExpired:
        raised = True
    check("plain timeout raises TimeoutExpired", raised)


def test_detached_ignoring_descendant_dies():
    out = Path(os.environ["GATOR_ROOT"]) / "out"
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "descendant-touched"
    pidfile = out / "descendant-pid"
    for p in (marker, pidfile):
        if p.exists():
            p.unlink()
    # The descendant ignores SIGTERM and detaches its descriptors
    # (so the leader's pipes close when the leader dies); the
    # leader itself honours SIGTERM and dies at once.
    cmd = ("(trap '' TERM; sleep 20; touch %s) "
           "</dev/null >/dev/null 2>&1 & echo $! > %s; sleep 30"
           % (shlex.quote(str(marker)), shlex.quote(str(pidfile))))
    t0 = time.time()
    raised = False
    try:
        worker.sh_group(cmd, timeout=1)
    except subprocess.TimeoutExpired:
        raised = True
    elapsed = time.time() - t0
    check("detached descendant: timeout raised, bounded",
          raised and elapsed < 20)
    pid = int(pidfile.read_text().strip())
    check("detached descendant: dead once the timeout returns "
          "(round-4 sh_group left it alive)",
          not pid_alive(pid))
    time.sleep(3)
    check("detached descendant: never reached its side effect",
          not marker.exists())


def main():
    test_normal_and_plain_timeout()
    test_detached_ignoring_descendant_dies()
    print()
    if FAILURES:
        print("%d passed, %d FAILED: %s"
              % (CHECKS["pass"], CHECKS["fail"], ", ".join(FAILURES)))
        return 1
    print("%d passed" % CHECKS["pass"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
