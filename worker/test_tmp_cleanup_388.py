#!/usr/bin/env python3
"""Regression test for issue #388: worker-test tempdirs must not leak
into /tmp.

Before #388 every worker test script created its scratch area with a
bare ``tempfile.mkdtemp`` at module level and never removed it. On
this VM /tmp is a 512M tmpfs, so one full suite run leaked ~400 MB
(``test148-`` 185M + ``test149-`` 187M + ``test160-`` 34M, plus the
``gator*-test-`` / ``wdi157-`` dirs) and filled the disk, failing
unrelated tests with ENOSPC / empty logs.

The fix (``worker/_test_tmp.py``) routes every scratch dir through a
tracked ``mkdtemp`` that removes it at interpreter exit via
``atexit`` -- on clean exit, on ``sys.exit`` and on unhandled
exceptions alike. This test proves that contract with throwaway
child processes, then proves it end to end by running a real worker
test file and asserting it leaves no residue behind.

Run: python3 worker/test_tmp_cleanup_388.py (exit 0 = all pass).
Stdlib only, no network. The child probes create only tiny empty
dirs in the real temp base and remove them again.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import _test_tmp  # noqa: E402

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}: {name}"
          + (f" — {detail}" if detail and not ok else ""))
    return ok


CHILD = r"""
import sys
from pathlib import Path
import _test_tmp
mode = sys.argv[1]
d = _test_tmp.mkdtemp(prefix="gator388-probe-")
(Path(d) / "marker.txt").write_text("probe")
if mode == "nested":
    inner = _test_tmp.mkdtemp(prefix="inner-", dir=str(d))
    (Path(inner) / "inner.txt").write_text("inner")
print(d, flush=True)
if mode == "fail":
    sys.exit(1)
if mode == "raise":
    raise RuntimeError("injected failure")
"""


def run_probe(mode, keep=False):
    """Run a child that creates a tracked tempdir and exits per mode.
    Returns (returncode, dirpath)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_HERE) + os.pathsep + env.get("PYTHONPATH", "")
    if keep:
        env["GATOR_TEST_KEEP_TMP"] = "1"
    else:
        env.pop("GATOR_TEST_KEEP_TMP", None)
    r = subprocess.run([sys.executable, "-c", CHILD, mode],
                       capture_output=True, text=True, env=env, timeout=60)
    created = r.stdout.strip().splitlines()
    return r, Path(created[0]) if created else None


# --- 1. Clean exit removes the tracked dir -------------------------
r, d = run_probe("ok")
check("clean exit: tracked tempdir removed",
      r.returncode == 0 and d is not None and not d.exists(),
      f"rc={r.returncode} dir={d} stderr={r.stderr.strip()[-200:]}")

# --- 2. Failing exit (sys.exit(1)) still removes it ---------------
r, d = run_probe("fail")
check("failing exit: tracked tempdir removed",
      r.returncode == 1 and d is not None and not d.exists(),
      f"rc={r.returncode} dir={d}")

# --- 3. Unhandled exception still removes it -----------------------
r, d = run_probe("raise")
check("unhandled exception: tracked tempdir removed",
      r.returncode != 0 and d is not None and not d.exists(),
      f"rc={r.returncode} dir={d}")

# --- 4. A nested dir inside a tracked dir goes with its parent ----
# (the nested dir lives inside d, so d being gone proves it too)
r, d = run_probe("nested")
check("nested tempdir removed with its tracked parent",
      r.returncode == 0 and d is not None and not d.exists(),
      f"rc={r.returncode} dir={d}")

# --- 5. GATOR_TEST_KEEP_TMP=1 keeps the dir for debugging ---------
r, d = run_probe("ok", keep=True)
kept = d is not None and d.exists()
check("GATOR_TEST_KEEP_TMP=1 keeps the tempdir for inspection",
      r.returncode == 0 and kept, f"rc={r.returncode} dir={d}")
if d is not None:
    shutil.rmtree(d, ignore_errors=True)

# --- 6. The helper itself: mkdtemp/track return usable Paths ------
own = _test_tmp.mkdtemp(prefix="gator388-self-")
check("mkdtemp returns an existing Path",
      isinstance(own, Path) and own.is_dir())
check("track returns the same Path it was given",
      _test_tmp.track(own) == own)
# (own is removed by the atexit handler when this process exits.)

# --- 7. End to end: a real worker test leaves no residue -----------
# test_worker_357.py is the fastest script-style worker test with a
# module-level tempdir; run it with a private temp base and assert no
# new gator357-f2-test-* dir survives it.
# The child gets its own base (not the shared default tempdir) so a
# concurrent test-357 run cannot create/remove dirs between the two
# globs and cause a false failure. The child env also drops
# GATOR_TEST_KEEP_TMP: if the parent runs with it set (to keep its
# own scratch dir for inspection), the child would retain its dir
# and the residue assertion would fail by design. The parent env is
# left untouched, so its own scratch dir stays available.
env = os.environ.copy()
env.pop("GATOR_TEST_KEEP_TMP", None)
base = _test_tmp.mkdtemp(prefix="gator388-e2e-")
env["TMPDIR"] = str(base)
before = set(base.glob("gator357-f2-test-*"))
r = subprocess.run([sys.executable, "worker/test_worker_357.py"],
                   cwd=str(REPO), capture_output=True, text=True,
                   env=env, timeout=120)
after = set(base.glob("gator357-f2-test-*"))
check("real worker test (357) passes", r.returncode == 0,
      f"rc={r.returncode} out={r.stdout.strip()[-200:]} "
      f"err={r.stderr.strip()[-200:]}")
check("real worker test (357) leaves no tempdir residue",
      after == before, f"new={sorted(str(p) for p in after - before)}")

failed = [c for c in CHECKS if not c[1]]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
sys.exit(1 if failed else 0)
