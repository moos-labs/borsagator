#!/usr/bin/env python3
"""Shared tempdir bookkeeping for the worker test scripts (#388).

Every worker test script creates its scratch area with
``tempfile.mkdtemp`` at module level and -- until #388 -- never
removed it. On this VM /tmp is a 512M tmpfs, so one full suite run
leaked ~100s of MB and filled the disk (``test_worker_149`` ENOSPC,
later tests rc=120 with empty logs).

Usage: create scratch dirs through :func:`mkdtemp` (a tracked
``tempfile.mkdtemp`` returning a ``Path``) or register an existing
path with :func:`track`. All tracked dirs are removed at interpreter
exit (``atexit`` -- runs on normal exit, ``sys.exit`` and unhandled
exceptions alike), even when the test fails. Nested dirs created
inside a tracked dir (``tempfile.mkdtemp(dir=_TMP)``) need no
separate registration: removing the parent removes them.

Set ``GATOR_TEST_KEEP_TMP=1`` to skip cleanup while debugging a
failing test; the dirs are then left in place for inspection.

Import pattern (works as a script, under pytest and under unittest;
the test files are standalone scripts, so the helper cannot rely on
``sys.path`` already containing this directory)::

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _test_tmp
    _TMP = _test_tmp.mkdtemp(prefix="gatorNNN-test-")
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

_TRACKED = []


def track(path):
    """Register *path* for removal at interpreter exit; return it as a Path."""
    p = Path(path)
    _TRACKED.append(p)
    return p


def mkdtemp(prefix=None, dir=None):
    """``tempfile.mkdtemp`` that cleans itself up at exit. Returns a Path."""
    return track(tempfile.mkdtemp(prefix=prefix, dir=dir))


def _cleanup(_rmtree=shutil.rmtree, _getenv=os.environ.get):
    # Bound at definition time: at interpreter shutdown module globals
    # may already be torn down.
    if _getenv("GATOR_TEST_KEEP_TMP"):
        return
    for path in reversed(_TRACKED):
        _rmtree(path, ignore_errors=True)


atexit.register(_cleanup)
