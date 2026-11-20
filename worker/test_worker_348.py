#!/usr/bin/env python3
"""Regression tests for issue #348: harvest-egx dispatch uses
startswith — a leading-space job falls through like F9 did for
top30-enumerate (issue #346).

The #346 F9 fix tokenized the top30 dispatch on whitespace
(`(job["job"] or "").split()[:1] == ["top30-enumerate"]`). The
harvest-egx dispatch in _execute_body (~line 3738) and the
harvest-pointer selection in publish() (~line 1748) kept the old
`job["job"].startswith("harvest-egx")` check, so " harvest-egx
POUL.CA" fell through to parse_job -> [] and published an empty
run as done, and publish() skipped the harvest pointer refresh.

Every test below FAILS on base c0c145a2 and PASSES with the fix.
Fixtures are fresh (own temp root, own fake harvest output, own
local bare archive repo) — nothing is copied from
test_worker_346.py's fixtures. Stdlib only.

Run: python3 worker/test_worker_348.py (exit 0 = all pass).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator348-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
HARVEST_INVOKED = {"n": 0, "codes": []}

FAKE_DISCLOSURES = {"ticker": "POUL", "docs": ["doc-348-a", "doc-348-b"]}


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
    """Stub worker.sh for the dispatch tests: `python3 -m venv`
    creates a venv whose python is a symlink to the real
    interpreter; the harvester invocation is intercepted (no EGX
    contact, no playwright) and writes a fake disclosures.json
    into the run dir; everything else succeeds silently."""
    if cmd.startswith("python3 -m venv "):
        venv = Path(cmd[len("python3 -m venv "):].strip())
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        link = venv / "bin" / "python"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(sys.executable)
        return FakeResult(0)
    if "egx_harvest.py" in cmd:
        HARVEST_INVOKED["n"] += 1
        code = cmd.split()[-1]
        HARVEST_INVOKED["codes"].append(code)
        results = Path(cwd) / "results"
        results.mkdir(parents=True, exist_ok=True)
        (results / "disclosures.json").write_text(
            json.dumps(FAKE_DISCLOSURES), encoding="utf-8")
        return FakeResult(0)
    return FakeResult(0)


def real_sh(cmd, cwd=None, env=None, timeout=3600):
    """Run the command for real (publish tests only): the archive
    is a local bare repo, so git clone/push/ls-remote all work
    offline inside the temp root."""
    proc = subprocess.run(cmd, shell=True, cwd=cwd, env=env,
                          capture_output=True, text=True,
                          timeout=timeout)
    return FakeResult(proc.returncode, proc.stdout, proc.stderr)


def setup_release():
    """Minimal registry (registry() reads it before the harvest
    branch runs); CODE pre-exists so _ensure_update_checkout
    never clones."""
    code = worker.CODE
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(
        json.dumps({"tools": []}), encoding="utf-8")


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    return "fake-archive-sha-348"


def stub_mark_done(job, archive_sha):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive_sha"] = archive_sha


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


# --- The dispatch hole: mechanism -----------------------------------------

def test_old_startswith_missed_leading_space():
    job = " harvest-egx POUL.CA"
    check("348: old startswith dispatch missed the leading-space "
          "job (this is the hole)",
          job.startswith("harvest-egx") is False)
    check("348: tokenized dispatch sees harvest-egx as the first "
          "token",
          (job or "").split()[:1] == ["harvest-egx"])


# --- Dispatch: leading-space harvest job ----------------------------------

def test_leading_space_harvest_dispatches():
    before = HARVEST_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-348-leading-space",
        "job": " harvest-egx POUL.CA",
        "added": worker.now()})
    check("348: leading-space harvest job dispatches to "
          "run_harvest",
          HARVEST_INVOKED["n"] == before + 1)
    check("348: leading-space harvest job ran for POUL.CA",
          HARVEST_INVOKED["codes"][-1] == "POUL.CA")
    check("348: leading-space harvest job publishes an ok run, "
          "not an empty run as done",
          pub.get("manifest", {}).get("tools", {}).get(
              "egx-harvest") == "ok")
    check("348: leading-space harvest job marked done after "
          "publish",
          done.get("archive_sha") == "fake-archive-sha-348")


def test_clean_harvest_still_dispatches():
    before = HARVEST_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-348-clean",
        "job": "harvest-egx COMI.CA",
        "added": worker.now()})
    check("348-control: clean harvest job still dispatches",
          HARVEST_INVOKED["n"] == before + 1)
    check("348-control: clean harvest job ran for COMI.CA",
          HARVEST_INVOKED["codes"][-1] == "COMI.CA")
    check("348-control: clean harvest job publishes ok",
          pub.get("manifest", {}).get("tools", {}).get(
              "egx-harvest") == "ok")
    check("348-control: clean harvest job marked done",
          done.get("archive_sha") == "fake-archive-sha-348")


# --- Dispatch: bad jobs still land their named failure --------------------

def test_leading_space_bad_job_still_named():
    before = HARVEST_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-348-leading-space-bad",
        "job": " harvest-egx !!!",
        "added": worker.now()})
    check("348: leading-space bad job dispatches to the named "
          "bad-code failure (not an empty run as done)",
          pub.get("manifest", {}).get("tools", {}).get(
              "egx-harvest") == "bad-code")
    check("348: leading-space bad job never invokes the harvester",
          HARVEST_INVOKED["n"] == before)
    check("348: leading-space bad job still publishes + marks done",
          done.get("archive_sha") == "fake-archive-sha-348")


def test_clean_bad_job_still_named():
    before = HARVEST_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-348-clean-bad",
        "job": "harvest-egx !!!",
        "added": worker.now()})
    check("348-control: clean bad job still lands bad-code",
          pub.get("manifest", {}).get("tools", {}).get(
              "egx-harvest") == "bad-code")
    check("348-control: clean bad job never invokes the harvester",
          HARVEST_INVOKED["n"] == before)
    check("348-control: clean bad job still publishes + marks done",
          done.get("archive_sha") == "fake-archive-sha-348")


# --- publish(): the second site (harvest pointer) --------------------------
#
# Real publish() against a local bare repo (no network): the
# archive branch is cloned from a file path, pushed back to it,
# and verified with ls-remote/ls-tree. Each test gets a fresh
# bare repo and a fresh archive-push checkout.

def make_bare_archive():
    bare = _TMP / ("bare-348-%d.git" % len(
        list(_TMP.glob("bare-348-*.git"))))
    subprocess.run(["git", "init", "--bare", "-q", str(bare)],
                   check=True)
    seed = _TMP / ("seed-348-%d" % len(list(_TMP.glob("seed-348-*"))))
    subprocess.run(["git", "clone", "-q", str(bare), str(seed)],
                   check=True)
    subprocess.run(["git", "-C", str(seed), "checkout", "-q",
                    "-b", "archive"], check=True)
    (seed / "README").write_text("archive seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(seed), "add", "README"],
                   check=True)
    subprocess.run(["git", "-C", str(seed), "-c",
                    "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "seed"], check=True)
    subprocess.run(["git", "-C", str(seed), "push", "-q",
                    "origin", "archive"], check=True)
    shutil.rmtree(seed, ignore_errors=True)
    return bare


def harvest_results_dir(job_id):
    """A workdir as run_harvest leaves it: fake disclosures.json
    under egx-harvest/results/."""
    results_dir = worker.OUT / job_id
    res = results_dir / "egx-harvest" / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "disclosures.json").write_text(
        json.dumps(FAKE_DISCLOSURES), encoding="utf-8")
    (results_dir / "egx-harvest.log").write_text(
        "fake harvest log\n", encoding="utf-8")
    return results_dir


def run_publish(job_text, job_id):
    bare = make_bare_archive()
    os.environ["GATOR_BUS_URL"] = str(bare)
    shutil.rmtree(worker.ROOT / "archive-push", ignore_errors=True)
    worker.sh = real_sh
    try:
        results_dir = harvest_results_dir(job_id)
        manifest = {"job": {"id": job_id, "job": job_text},
                    "worker": "test-348", "started": worker.now(),
                    "tools": {"egx-harvest": "ok"}}
        # The real publish (main() stubs worker.publish for the
        # dispatch tests; REAL_PUBLISH holds the original).
        sha = REAL_PUBLISH(
            {"id": job_id, "job": job_text}, results_dir, manifest)
        return sha, worker.ROOT / "archive-push"
    finally:
        worker.sh = fake_sh


def pointer_in_archive(arch, code="POUL"):
    p = arch / "harvest" / f"{code}.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def test_publish_pointer_leading_space():
    sha, arch = run_publish(" harvest-egx POUL.CA",
                            "test-348-pub-leading")
    check("348-publish: leading-space harvest job publishes",
          isinstance(sha, str) and len(sha) == 40)
    check("348-publish: leading-space harvest job refreshes the "
          "harvest pointer",
          pointer_in_archive(arch) == FAKE_DISCLOSURES)
    shown = subprocess.run(
        ["git", "-C", str(arch), "show", "archive:harvest/POUL.json"],
        capture_output=True, text=True)
    check("348-publish: pointer reached the pushed archive commit",
          shown.returncode == 0
          and json.loads(shown.stdout) == FAKE_DISCLOSURES)


def test_publish_pointer_clean_job():
    sha, arch = run_publish("harvest-egx POUL.CA",
                            "test-348-pub-clean")
    check("348-publish-control: clean harvest job publishes",
          isinstance(sha, str) and len(sha) == 40)
    check("348-publish-control: clean harvest job refreshes the "
          "harvest pointer",
          pointer_in_archive(arch) == FAKE_DISCLOSURES)


def test_publish_pointer_skips_non_harvest():
    sha, arch = run_publish("sweep-lite POUL.CA",
                            "test-348-pub-nonharvest")
    check("348-publish-control: non-harvest job publishes",
          isinstance(sha, str) and len(sha) == 40)
    check("348-publish-control: non-harvest job leaves no "
          "harvest pointer",
          pointer_in_archive(arch) is None)


def main():
    global REAL_PUBLISH
    REAL_PUBLISH = worker.publish
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    test_old_startswith_missed_leading_space()
    test_leading_space_harvest_dispatches()
    test_clean_harvest_still_dispatches()
    test_leading_space_bad_job_still_named()
    test_clean_bad_job_still_named()
    test_publish_pointer_leading_space()
    test_publish_pointer_clean_job()
    test_publish_pointer_skips_non_harvest()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
