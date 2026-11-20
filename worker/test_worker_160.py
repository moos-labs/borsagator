#!/usr/bin/env python3
"""Regression test for issue #160 (panel round 12, F16): heartbeat
code_sha reports the checkout HEAD, not the running code.

On unmodified main, heartbeat() sets code_sha from
update_checkout_sha() — the /opt/gator/release checkout's HEAD — and
self_update() swallows a failed me.write_bytes / os.execv with
`except Exception: pass` (UPDATE_ERROR stays None), so the heartbeat
claims the new SHA while old code runs.

This test exercises the REAL self_update + heartbeat path (only the
bus push is stubbed; the release checkout is a local bare repo, so no
network and no live worker):
  1. heartbeat code_sha is the hash of the RUNNING worker.py bytes,
     not the release checkout's tip, even when the checkout holds
     different bytes.
  2. A forced write_bytes failure sets UPDATE_ERROR and the heartbeat
     carries update_error (instead of silently claiming the new SHA).
  3. A forced execv failure (the issue's proof bar) leaves the
     heartbeat reporting the OLD running-code hash plus an update
     error — even though the new bytes are already on disk.
  4. Happy path: when the checkout's worker.py matches the running
     bytes, self_update leaves UPDATE_ERROR None.

Run: python3 worker/test_worker_160.py   (stdlib only, no network)
Fails on unmodified main at check 1 (code_sha == checkout tip) and
checks 2-3 (UPDATE_ERROR stays None); passes on the fix.
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp  # noqa: E402  (atexit cleanup of scratch dirs, #388)
TMP = _test_tmp.mkdtemp(prefix="test160-")


def git(*args, cwd=None):
    r = subprocess.run(["git"] + list(args), cwd=cwd,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()


# --- fixture: bare repo + a worker-release tip whose worker.py differs
# from the running copy (one appended comment line = a promotion).
bare = TMP / "bare.git"
git("clone", "--bare", "-q", str(REPO), str(bare))
work = TMP / "work"
git("clone", "-q", str(bare), str(work))
git("checkout", "-q", "-b", "worker-release", cwd=work)
wp = work / "worker" / "worker.py"
wp.write_text(wp.read_text() + "\n# promotion tip: one-line change\n")
git("add", "worker/worker.py", cwd=work)
git("-c", "user.email=t@t", "-c", "user.name=t",
    "commit", "-qm", "promotion tip", cwd=work)
git("push", "-q", "origin", "worker-release", cwd=work)
TIP = git("rev-parse", "HEAD", cwd=work)
NEW_BYTES = (work / "worker" / "worker.py").read_bytes()

# A second worker-release branch whose worker.py is IDENTICAL to the
# running copy (only a README line changes) — for the happy-path check.
# NOTE: the bare clone holds only committed content, so the branch must
# carry this checkout's (possibly uncommitted) fixed worker.py bytes
# explicitly, or the happy path would see differing bytes and execv.
# Branch from HEAD (not "main": a single-branch clone of the PR has no
# local main) — the fixture only needs a tip whose worker.py matches
# the running copy.
git("checkout", "-q", "-b", "worker-release-same", "HEAD", cwd=work)
(work / "worker" / "worker.py").write_bytes(
    (REPO / "worker" / "worker.py").read_bytes())
readme = work / "README.md"
readme.write_text(readme.read_text() + "\n<!-- same-worker test tip -->\n")
git("add", "worker/worker.py", "README.md", cwd=work)
git("-c", "user.email=t@t", "-c", "user.name=t",
    "commit", "-qm", "same worker tip", cwd=work)
git("push", "-q", "origin", "worker-release-same", cwd=work)

# --- the "running" worker.py: a copy of this checkout's file.
running_dir = TMP / "running"
running_dir.mkdir()
me = running_dir / "worker.py"
me.write_bytes((REPO / "worker" / "worker.py").read_bytes())
OLD_SHA = hashlib.sha256(me.read_bytes()).hexdigest()
assert OLD_SHA != hashlib.sha256(NEW_BYTES).hexdigest()

# --- fake GATOR_ROOT: CODE cloned at the new tip; BUS a plain dir
# (in production sync_bus creates it; heartbeat only mkdirs queue/).
gator = TMP / "gator"
(gator / "bus").mkdir(parents=True)
git("clone", "-q", "--branch", "worker-release", "--single-branch",
    str(bare), str(gator / "release"))
os.environ["GATOR_ROOT"] = str(gator)

spec = importlib.util.spec_from_file_location("worker160", me)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
worker.CODE = gator / "release"
worker.push_bus = lambda msg: False  # no bus remote in the test


def heartbeat_payload():
    worker.heartbeat()
    return json.loads((worker.BUS / "queue" / "heartbeat.json").read_text())


CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}: {name}"
          + (f" — {detail}" if detail and not ok else ""))
    return ok


# 1. code_sha is the running-code hash, not the checkout tip.
p = heartbeat_payload()
check("code_sha is the running-code hash, not the checkout tip",
      p.get("code_sha") == OLD_SHA,
      f"code_sha={p.get('code_sha', '')[:12]} running={OLD_SHA[:12]} "
      f"checkout-tip={TIP[:12]}")
check("checkout_sha still reports the checkout HEAD",
      p.get("checkout_sha") == TIP,
      f"checkout_sha={p.get('checkout_sha', '')[:12]} tip={TIP[:12]}")
check("code_sha_kind names the hash",
      p.get("code_sha_kind") == "sha256-running-bytes",
      f"code_sha_kind={p.get('code_sha_kind')!r}")

# 2. Forced write_bytes failure: UPDATE_ERROR set, heartbeat carries it,
#    and code_sha still reports the OLD running code.
worker.UPDATE_ERROR = None
real_write_bytes = pathlib.Path.write_bytes


def failing_write_bytes(self, data):
    if Path(self).resolve() == me.resolve():
        raise PermissionError("simulated read-only running file")
    return real_write_bytes(self, data)


pathlib.Path.write_bytes = failing_write_bytes
try:
    worker.self_update()
finally:
    pathlib.Path.write_bytes = real_write_bytes
check("failed write sets UPDATE_ERROR",
      worker.UPDATE_ERROR is not None
      and "self-update failed to adopt" in worker.UPDATE_ERROR,
      f"UPDATE_ERROR={worker.UPDATE_ERROR!r}")
p = heartbeat_payload()
check("heartbeat carries update_error after failed write",
      "update_error" in p, f"payload keys={sorted(p)}")
check("heartbeat still reports old running code after failed write",
      p.get("code_sha") == OLD_SHA,
      f"code_sha={p.get('code_sha', '')[:12]} running={OLD_SHA[:12]}")
check("running file bytes unchanged after failed write",
      hashlib.sha256(me.read_bytes()).hexdigest() == OLD_SHA)

# 3. Forced execv failure (issue's proof bar): the write lands the new
#    bytes on disk, the exec fails, and the heartbeat must still report
#    the OLD code (import-time hash) plus an update error.
worker.UPDATE_ERROR = None
real_execv = os.execv


def failing_execv(path, argv):
    raise OSError("simulated execv failure")


os.execv = failing_execv
try:
    worker.self_update()
finally:
    os.execv = real_execv
check("failed execv sets UPDATE_ERROR",
      worker.UPDATE_ERROR is not None
      and "self-update failed to adopt" in worker.UPDATE_ERROR,
      f"UPDATE_ERROR={worker.UPDATE_ERROR!r}")
check("new bytes are on disk after failed execv",
      hashlib.sha256(me.read_bytes()).hexdigest()
      == hashlib.sha256(NEW_BYTES).hexdigest())
p = heartbeat_payload()
check("heartbeat reports OLD code after failed execv, not new disk bytes",
      p.get("code_sha") == OLD_SHA,
      f"code_sha={p.get('code_sha', '')[:12]} running={OLD_SHA[:12]}")
check("heartbeat carries update_error after failed execv",
      "update_error" in p, f"payload keys={sorted(p)}")

# 4. Happy path: checkout worker.py identical to the running bytes —
#    self_update is a no-op and leaves UPDATE_ERROR None. (A separate
#    CODE checkout on the worker-release-same branch, whose tip changes
#    only the README, so its worker.py matches the running copy.)
git("clone", "-q", "--branch", "worker-release-same", "--single-branch",
    str(bare), str(gator / "release-same"))
worker.CODE = gator / "release-same"
worker.UPDATE_BRANCH = "worker-release-same"
me.write_bytes((REPO / "worker" / "worker.py").read_bytes())
worker.UPDATE_ERROR = None
worker.self_update()
check("identical bytes: UPDATE_ERROR stays None",
      worker.UPDATE_ERROR is None, f"UPDATE_ERROR={worker.UPDATE_ERROR!r}")

print()
failed = [c for c in CHECKS if not c[1]]
print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
sys.exit(1 if failed else 0)
