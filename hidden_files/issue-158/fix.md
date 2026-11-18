# Issue #158 — fix record

Panel round 12, F14 (OpenRouter leg, Medium, WSJF 4.5). Milestone M0.

- **Issue:** https://github.com/moos-labs/borsagator/issues/158
- **PR:** https://github.com/moos-labs/borsagator/pull/192
- **Branch:** `fix-158-venv-deps-reinstall-on-ref-change`
- **Fix commit:** `43f5eba`
- **Merge commit:** `cdc4ba9cda8ade1f4e37656c6c746862a9f72f95`
  (merged 2026-11-18T01:49:42Z by moos-sherbo; #158 auto-closed by
  "Closes #158", board card verified in Released)

## The defect

`worker/worker.py` `run_tool` installed `requirements.txt` only inside
`if not py.exists()` — i.e. only when the venv was first created. A
promoted ref that changed `requirements.txt` reused the old venv's
deps, and the venv/pip return codes were unchecked, so a failed
install still ran the tool against wrong/missing deps (ImportError,
or silently wrong versions producing wrong numbers).

## The fix (`worker/worker.py`, `run_tool`)

- The venv records the sha256 of the requirements it was built from
  in `.gator-requirements-sha` inside the venv (existing
  `_sha256_file` helper; empty string when there is no
  `requirements.txt`). When the recorded hash differs from the pinned
  ref's current `requirements.txt`, the venv is recreated from scratch
  and deps are reinstalled — a full recreate, so a dep *removed* from
  `requirements.txt` disappears too.
- `python3 -m venv` failure returns `"venv-failed"`; a zero return
  code that yields no interpreter is also `"venv-failed"` (never run
  the tool against the system python with the venv's PATH prefix
  missing). A pip failure returns `"deps-failed"` with the pip output
  tail (last 4000 chars) as the log. In both cases the tool is never
  run — the failure is loud in the manifest + `<tool>.log` via
  `_execute`, which already gates the archive copy on
  `status == "ok"` (issue #147), so no code change was needed there.
- A failed install leaves no marker, so the next run retries the
  install. A venv built by the old code has no marker, so it is
  rebuilt on its next run (one-time migration, no manual cleanup).

## The test (`worker/test_worker_158.py`)

27 checks, stdlib only, no network — `worker.sh` is stubbed, the
runner clones are plain directories under a temp `GATOR_ROOT`
(same harness shape as `test_worker_147.py`):

- first run installs the pinned ref's deps and records the hash;
  unchanged requirements are not reinstalled;
- a requirements bump reinstalls the new deps and recreates the venv;
- a failed pip install returns `deps-failed`, does not run the tool,
  surfaces the pip error, leaves no marker, and a retry succeeds;
- a failed venv creation (and a lying rc 0 with no interpreter)
  returns `venv-failed` and runs neither pip nor the tool;
- no `requirements.txt` means no pip call and no reinstall;
- a pre-fix venv (python, no marker) is rebuilt.

**Discrimination check (harness-first):** on the pre-fix code the
suite fails 12/25 — no reinstall on a requirements bump, a failed
pip/venv still runs the tool and returns `ok`. After the fix:
**27/27 passed**.

**No regressions:** all other worker suites still green on the
merged tree — #147 18/18, #148 10/10, #149 17/17, #160 12/12,
env 8/8, #157 17/17. `worker.py` compiles clean. The #147 harness
needed one small update: its fake `sh` now simulates venv creation
(creates `venv/bin/python`), which the fix relies on.

**Post-merge verification:** fresh clone of main at `cdc4ba9`,
`test_worker_158.py` 27/27 green, `test_worker_147.py` 18/18 green.

## Residuals noticed, not filed

- `pip install -r requirements.txt` against an existing venv would
  have left removed deps installed; the fix recreates the venv
  instead, so this is closed by the fix rather than filed.
- The marker is a plain file inside the venv dir; a hand-deleted
  marker triggers a (harmless, one-off) reinstall. Not a defect.
- Nothing else in the `run_tool` path looked wrong while working
  here; the `sh()` return-code checks on the git fetch/checkout
  steps were already in place.
