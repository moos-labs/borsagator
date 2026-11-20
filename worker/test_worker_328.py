#!/usr/bin/env python3
"""Regression + entry-point tests for issue #328 (worker entry point
for the live top-30 enumeration).

The wiring under test (worker/worker.py):
  parse_top30_job — `top30-enumerate [--mode live|probe|fixtures]
    [--fixtures DIR]` parses to a non-empty plan; anything else
    fails closed (None). parse_job (the registry grammar) still
    returns [] for the string — the registry has no enumeration
    tool — which is why _execute_body dispatches this kind before
    parse_job, like harvest-egx.
  run_top30_enumerate — runs the REAL scripts/top30_enumerate.py
    in the egx-harvest playwright venv, writes the ledger +
    frozen required-cells file + validation record under
    workdir/top30/, and validates the ledger fail-closed against
    the frozen manifest and the #283 gates re-check flags.
  _validate_top30_ledger — an honest failure ledger passes; a
    dishonest one (closure over failures, missing route, FAITA
    defaulted, clipped body as full hash, complete/pass verdict
    from collection-only output) fails.
  build_top30_required_cells — the frozen 90-cell universe
    (30 issuers x 3 event types; FAIT/FAITA is ONE issuer).
  _execute_body top30 branch — publishes via the stubbed publish
    and marks done only on a successful publish, like harvest-egx.

Deterministic replay (no live EGX needed): the fixtures-mode run
uses the REAL fixture pages (scripts/top30_enumerate_fixtures/ —
SIMULATED NewsSearch pages for POUL/COMI only, so the other 29
issuers fail with the named "no fixture for URL" failure and the
ledger is honestly open). The probe-mode run uses the REAL
enumerator probe (one pilot request; fails fast where EGX is
unreachable, and either way the ledger is honest). git/venv are
stubbed; publish/_mark_done are stubbed at the worker-module
boundary while _execute_body itself runs for real.

Harness-first: FAILS on pristine main (worker has no
parse_top30_job / run_top30_enumerate — AttributeError — and
_execute_body publishes an empty run as done) and PASSES on the
fixed tree. Stdlib only.

Run: python3 worker/test_worker_328.py (exit 0 = all pass).
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator328-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
ENUMERATOR_INVOKED = {"n": 0}


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
    """Fake worker.sh: perform `rm -rf` for real; `python3 -m venv`
    creates a venv whose python is a symlink to the real
    interpreter (so the REAL enumerator runs); the enumerator
    invocation itself runs for real via subprocess; everything
    else (pip install, playwright install, git) succeeds."""
    if cmd.startswith("rm -rf "):
        shutil.rmtree(cmd[len("rm -rf "):].strip(), ignore_errors=True)
        return FakeResult(0)
    if "top30_enumerate.py" in cmd:
        ENUMERATOR_INVOKED["n"] += 1
        proc = subprocess.run(cmd, shell=True, cwd=cwd, env=env,
                              capture_output=True, text=True,
                              timeout=timeout)
        return FakeResult(proc.returncode, proc.stdout, proc.stderr)
    if cmd.startswith("python3 -m venv "):
        venv = Path(cmd[len("python3 -m venv "):].strip())
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        link = venv / "bin" / "python"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(sys.executable)
        return FakeResult(0)
    return FakeResult(0)


def setup_release():
    """Fake release checkout: the REAL enumerator + manifest +
    fixtures, and a minimal registry (registry() reads it before
    the top30 branch runs)."""
    code = worker.CODE
    (code / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy(_REPO / "scripts" / "top30_enumerate.py",
                code / "scripts" / "top30_enumerate.py")
    (code / "evaluation").mkdir(parents=True, exist_ok=True)
    shutil.copy(_REPO / "evaluation" / "top30_manifest.json",
                code / "evaluation" / "top30_manifest.json")
    (code / "registry").mkdir(parents=True, exist_ok=True)
    (code / "registry" / "tools.json").write_text(json.dumps({
        "tools": []}), encoding="utf-8")


def stub_publish(job, results_dir, manifest):
    PUBLISH_SEEN.clear()
    PUBLISH_SEEN["job"] = job
    PUBLISH_SEEN["manifest"] = json.loads(json.dumps(manifest))
    wd = Path(results_dir)
    PUBLISH_SEEN["ledger"] = (wd / "top30"
                              / "top30_expected_docs.json").is_file()
    PUBLISH_SEEN["cells"] = (wd / "top30"
                             / "top30_required_cells.json").is_file()
    PUBLISH_SEEN["validation"] = (wd / "top30"
                                  / "top30-validation.json").is_file()
    return "fake-archive-sha-328"


def stub_mark_done(job, archive_sha):
    MARK_DONE_SEEN.clear()
    MARK_DONE_SEEN["job"] = job
    MARK_DONE_SEEN["archive_sha"] = archive_sha


def real_manifest():
    return json.loads(
        (_REPO / "evaluation" / "top30_manifest.json").read_text(
            encoding="utf-8"))


def real_probe_ledger():
    return json.loads(
        (_REPO / "evaluation" / "top30_expected_docs.json").read_text(
            encoding="utf-8"))


def test_parse():
    plan = worker.parse_top30_job("top30-enumerate")
    check("parse: bare job parses to a non-empty plan",
          plan == {"kind": "top30-enumerate", "mode": "live",
                   "fixtures": None})
    check("parse: probe mode",
          worker.parse_top30_job("top30-enumerate --mode probe")
          == {"kind": "top30-enumerate", "mode": "probe",
              "fixtures": None})
    check("parse: fixtures mode with dir",
          worker.parse_top30_job(
              "top30-enumerate --mode fixtures --fixtures /x/y")
          == {"kind": "top30-enumerate", "mode": "fixtures",
              "fixtures": "/x/y"})
    for bad in ("", "sweep-lite POUL.CA",
                "top30-enumerate --bogus",
                "top30-enumerate --mode bogus",
                "top30-enumerate --mode fixtures",
                "top30-enumerate --fixtures /x/y",
                "top30-enumerate --mode live --fixtures /x/y",
                "top30-enumerate extra",
                "top30-enumerate --mode",
                "top30-enumeratex"):
        check("parse: rejects %r" % bad,
              worker.parse_top30_job(bad) is None)
    check("parse: old parse_job still returns [] (registry has no "
          "enumeration tool — the _execute_body branch is what "
          "dispatches it)",
          worker.parse_job("top30-enumerate",
                           {"tools": []}) == [])


def test_required_cells():
    manifest = real_manifest()
    doc, cells = worker.build_top30_required_cells(manifest)
    check("required cells: 30 issuers x 3 types = 90",
          doc["count"] == 90 and len(cells) == 90)
    check("required cells: FAIT/FAITA is ONE issuer (3 cells, not 6)",
          sum(1 for c in cells if c["issuer"] == "FAIT") == 3)
    doc2, _ = worker.build_top30_required_cells(manifest)
    check("required cells: sha256 stable across builds",
          doc["sha256"] == doc2["sha256"] and len(doc["sha256"]) == 64)
    check("required cells: cell ids are issuer:event_type",
          {"issuer": "TMGH", "event_type": "dividend",
           "cell_id": "TMGH:dividend"} in cells)
    check("required cells: frozen window recorded",
          doc["window"] == {"start": "2026-08-19", "end": "2026-11-19",
                            "inclusive": True})


def test_validate_honest_probe_ledger():
    manifest = real_manifest()
    ok, reasons = worker._validate_top30_ledger(
        real_probe_ledger(), manifest, "probe")
    check("validate: committed honest probe ledger passes",
          ok and reasons == [])


def test_validate_dishonest_ledgers():
    manifest = real_manifest()
    base = real_probe_ledger()

    led = copy.deepcopy(base)
    led["collection"]["enumeration_closed"] = True
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: closure claimed over 31 failures fails",
          not ok and any("enumeration_closed=True" in r
                         for r in reasons))

    # Issue #340, variant A: clear the TOP-LEVEL failures list and
    # set every listing's terminal_state to exhausted, but KEEP
    # FAITA's listing-level B-02 failure. Before the fix this
    # returned (True, []): the closure check never inspected
    # per-listing failures.
    led = copy.deepcopy(base)
    led["collection"]["enumeration_closed"] = True
    led["collection"]["pagination_complete"] = True
    led["failures"] = []
    for irec in led["issuers"]:
        for lrec in irec["listings"]:
            lrec["terminal_state"] = "exhausted"
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: closure claimed over a kept listing-level "
          "failure fails (#340 variant A)",
          not ok and any("listing-level failure" in r
                         for r in reasons))

    # Issue #340, blocked-status arm: same closure claim with
    # FAITA's B-02 failure kept, but FAITA's enumeration_status
    # set to blocked. The listing-level-failure reason also fires
    # here; the assertion pins the blocked-status reason itself.
    led = copy.deepcopy(base)
    led["collection"]["enumeration_closed"] = True
    led["collection"]["pagination_complete"] = True
    led["failures"] = []
    for irec in led["issuers"]:
        for lrec in irec["listings"]:
            lrec["terminal_state"] = "exhausted"
            if lrec["code"] == "FAITA":
                lrec["enumeration_status"] = "blocked"
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: closure claimed over a blocked listing fails "
          "(#340 blocked arm)",
          not ok and any("enumeration_status is blocked" in r
                         for r in reasons))

    led = copy.deepcopy(base)
    del led["issuers"][0]["listings"][0]
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: missing listing route fails",
          not ok and any("missing from ledger" in r for r in reasons))

    led = copy.deepcopy(base)
    for irec in led["issuers"]:
        for lrec in irec["listings"]:
            if lrec["code"] == "FAITA":
                lrec["enumeration_status"] = "enumerated"
                lrec["failures"] = []
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: FAITA enumerated fails (B-02: never default "
          "to the FAIT ISIN)",
          not ok and any("FAITA enumerated" in r for r in reasons))

    led = copy.deepcopy(base)
    for irec in led["issuers"]:
        for lrec in irec["listings"]:
            if lrec["code"] == "FAITA":
                lrec["failures"] = []
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: FAITA without its B-02 named failure fails",
          not ok and any("B-02-missing-isin" in r for r in reasons))

    led = copy.deepcopy(base)
    led["issuers"][0]["documents"] = [{
        "source_document_id": "egx:1", "url": "https://x",
        "title": "t", "announced_date": None,
        "announced_date_source": None, "listing": "TMGH",
        "isin": "EGS691S1C011", "first_seen_page": 1,
        "corpus": {"status": "archived",
                   "body_sha256": "a" * 64,
                   "body_hash_kind": "clipped-body-sha256",
                   "body_chars": 100, "attachments": []}}]
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: clipped body presented as a full hash fails",
          not ok and any("clipped body" in r for r in reasons))

    led = copy.deepcopy(base)
    led["window"]["end"] = "2026-11-20"
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: rolling/frozen window mismatch fails",
          not ok and any("frozen" in r for r in reasons))

    led = copy.deepcopy(base)
    led["complete"] = True
    ok, reasons = worker._validate_top30_ledger(led, manifest, "probe")
    check("validate: complete claim from collection-only output "
          "fails",
          not ok and any("collection-only" in r for r in reasons))

    ok, reasons = worker._validate_top30_ledger(
        {"not": "a ledger"}, manifest, "probe")
    check("validate: malformed ledger fails without raising",
          not ok and reasons)


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


def test_entry_point_fixtures_end_to_end():
    fixtures = str(_REPO / "scripts" / "top30_enumerate_fixtures")
    before = ENUMERATOR_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-328-fixtures",
        "job": "top30-enumerate --mode fixtures --fixtures "
               + fixtures,
        "added": worker.now()})
    check("entry point (fixtures): enumerator actually ran",
          ENUMERATOR_INVOKED["n"] == before + 1)
    check("entry point (fixtures): published",
          pub.get("manifest", {}).get("tools", {}).get(
              "top30-enumerate") == "ok")
    check("entry point (fixtures): ledger + cells + validation "
          "archived",
          pub.get("ledger") and pub.get("cells")
          and pub.get("validation"))
    wd = worker.OUT / "test-328-fixtures" / "top30"
    ledger = json.loads(
        (wd / "top30_expected_docs.json").read_text(encoding="utf-8"))
    check("entry point (fixtures): ledger mode is fixtures "
          "(simulated pages, never live)",
          ledger["mode"] == "fixtures")
    check("entry point (fixtures): enumeration honestly open "
          "(fixtures cover POUL/COMI only)",
          ledger["collection"]["enumeration_closed"] is False)
    faita = [l for i in ledger["issuers"] for l in i["listings"]
             if l["code"] == "FAITA"][0]
    check("entry point (fixtures): FAITA carried as named blocked "
          "route",
          faita["enumeration_status"] == "blocked" and any(
              f.get("kind") == "B-02-missing-isin"
              for f in faita["failures"]))
    validation = json.loads(
        (wd / "top30-validation.json").read_text(encoding="utf-8"))
    check("entry point (fixtures): validation record valid, 90 "
          "required cells",
          validation["valid"] is True
          and validation["required_cells_count"] == 90)
    check("entry point (fixtures): done marked only after publish",
          done.get("archive_sha") == "fake-archive-sha-328")


def test_entry_point_probe_end_to_end():
    before = ENUMERATOR_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-328-probe",
        "job": "top30-enumerate --mode probe",
        "added": worker.now()})
    check("entry point (probe): enumerator actually ran (dry run, "
          "no per-issuer EGX requests)",
          ENUMERATOR_INVOKED["n"] == before + 1)
    check("entry point (probe): status ok with honest open ledger",
          pub.get("manifest", {}).get("tools", {}).get(
              "top30-enumerate") == "ok")
    wd = worker.OUT / "test-328-probe" / "top30"
    ledger = json.loads(
        (wd / "top30_expected_docs.json").read_text(encoding="utf-8"))
    check("entry point (probe): ledger mode probe, all issuers "
          "not_run, closed False",
          ledger["mode"] == "probe"
          and ledger["collection"]["enumeration_closed"] is False
          and all(i["enumeration_status"] == "not_run"
                  for i in ledger["issuers"]))
    check("entry point (probe): done marked after publish",
          done.get("archive_sha") == "fake-archive-sha-328")


def test_live_mode_missing_profile_fails_closed():
    assert not (worker.ROOT / "egx-profile").exists()
    before = ENUMERATOR_INVOKED["n"]
    wd = _TMP / "live-profile-check"
    wd.mkdir(parents=True, exist_ok=True)
    res = worker.run_top30_enumerate(
        {"id": "test-328-live", "job": "top30-enumerate"}, wd)
    check("live mode without the TSPD-trusted profile fails closed "
          "as profile-missing (no doomed EGX requests)",
          res == {"top30-enumerate": "profile-missing"})
    check("live mode without profile: enumerator never invoked",
          ENUMERATOR_INVOKED["n"] == before)
    check("live mode without profile: no ledger written",
          not (wd / "top30" / "top30_expected_docs.json").exists())


def test_bad_job_publishes_failure_manifest():
    pub, done = run_execute({
        "id": "test-328-badjob",
        "job": "top30-enumerate --bogus",
        "added": worker.now()})
    check("bad job string: named bad-job failure in the manifest",
          pub.get("manifest", {}).get("tools", {}).get(
              "top30-enumerate") == "bad-job")
    check("bad job string: still publishes + marks done (done "
          "means executed + archived, as for harvest-egx)",
          done.get("archive_sha") == "fake-archive-sha-328")


def main():
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    test_parse()
    test_required_cells()
    test_validate_honest_probe_ledger()
    test_validate_dishonest_ledgers()
    test_entry_point_fixtures_end_to_end()
    test_entry_point_probe_end_to_end()
    test_live_mode_missing_profile_fails_closed()
    test_bad_job_publishes_failure_manifest()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
