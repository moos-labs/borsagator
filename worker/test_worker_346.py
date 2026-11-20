#!/usr/bin/env python3
"""Regression tests for issue #346 (INS-339-POSTMERGE-REVIEW):
top-30 validator + dispatch gaps found in Ins's post-merge review
of the #328 fix (PR #339) and verified by Moos with executable
probes (21/21, ~/workspace/tick0409_verify339.py, main tip
977b216e, which already carries the #340 fix).

Findings, in the issue's fix order:
  F7 — malformed manifest reference raises AttributeError in the
    validator (string/list manifest), breaking the never-raises
    contract and escaping through _execute_body before publication.
  F9 — parser/dispatcher disagreement: " top30-enumerate --mode
    probe" (leading space) parses but never dispatches; falls
    through to parse_job -> [] and publishes an empty run as done.
  F4 — summary reconciliation: archived=555 vs enumerated=2,
    enumerated=999, or an invented missing-document ID all
    validate; the summary is never reconciled against the records.
  F5 — route provenance: a TMGH listing carrying ETEL's ISIN, a
    document under FAIT claiming the blocked FAITA route, a
    document under TMGH claiming the ETEL route, or a document
    claiming a nonexistent ZZZZ route all validate.
  F6 — route universe / duplicates: an invented 32nd route, or
    duplicate TMGH records, validate (seen[code] overwrites).
  F8 — corpus hash shape: archived with a 2-char or non-hex
    body_sha256 validates.
  F2 — persistent-profile transport absent: run_top30_enumerate
    only checks the profile dir exists; the enumerator fetches
    via urllib, never the Chromium profile session.

Every test below FAILS on base 977b216e and PASSES with the fix.
Honest controls (committed probe ledger passes; #340 variant-A
ledger still fails closed) guard against regressions. Stdlib only.

Run: python3 worker/test_worker_346.py (exit 0 = all pass).
"""
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gator346-test-"))
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))

import worker  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "top30_enumerate_346",
    str(_REPO / "scripts" / "top30_enumerate.py"))
ENUM = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ENUM)

PASSED = 0
PUBLISH_SEEN = {}
MARK_DONE_SEEN = {}
ENUMERATOR_INVOKED = {"n": 0}
COMMANDS_SEEN = []


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
    """Same fake worker.sh as test_worker_328.py: `rm -rf` for real;
    `python3 -m venv` creates a venv whose python is a symlink to
    the real interpreter (so the REAL enumerator runs); the
    enumerator invocation itself runs for real via subprocess;
    everything else (pip install, playwright install, git)
    succeeds."""
    COMMANDS_SEEN.append(cmd)
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
    return "fake-archive-sha-346"


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


# --- Synthetic manifest/ledger (Moos's tick0409_verify339.py shape,
# with listing ISINs + document attribution, as the real producer
# writes them) -----------------------------------------------------------

MANIFEST = {
    "base_commit": "testbase123",
    "frozen_at": "2026-11-19",
    "event_types": ["dividend", "earnings", "board"],
    "issuers": [
        {"issuer": "TMGH",
         "listings": [{"code": "TMGH", "isin": "EGS000000001"}]},
        {"issuer": "ETEL",
         "listings": [{"code": "ETEL", "isin": "EGS000000002"}]},
        {"issuer": "FAIT",
         "listings": [{"code": "FAIT", "isin": "EGS000000003"},
                      {"code": "FAITA", "isin": None}]},
    ],
}


def listing(code, isin=None, status="enumerated", terminal="exhausted",
            failures=None):
    return {"code": code, "isin": isin,
            "enumeration_status": status,
            "terminal_state": terminal, "failures": failures or []}


def doc(doc_id, status="archived", kind="full", sha="a" * 64,
        listing_code=None, isin=None, attachments=None):
    corpus = {"status": status, "body_hash_kind": kind,
              "body_sha256": sha}
    if attachments is not None:
        corpus["attachments"] = attachments
    d = {"source_document_id": doc_id, "corpus": corpus}
    if listing_code:
        d["listing"] = listing_code
    if isin:
        d["isin"] = isin
    return d


def baseline():
    """Honest incomplete ledger: 2 documents enumerated + archived,
    FAITA named as the missing (blocked) route. Must PASS."""
    return {
        "schema_version": 1,
        "window": {"start": worker.TOP30_WINDOW_START,
                   "end": worker.TOP30_WINDOW_END},
        "mode": "fixtures",
        "manifest": {"base_commit": "testbase123"},
        "collection": {"enumerated": 2, "archived": 2,
                       "missing": ["FAITA"],
                       "enumeration_closed": False,
                       "pagination_complete": False},
        "failures": [{"kind": "B-02-missing-isin", "route": "FAITA"}],
        "issuers": [
            {"issuer": "TMGH",
             "listings": [listing("TMGH", "EGS000000001")],
             "documents": [doc("TMGH-doc-1", listing_code="TMGH",
                               isin="EGS000000001")]},
            {"issuer": "ETEL",
             "listings": [listing("ETEL", "EGS000000002")],
             "documents": [doc("ETEL-doc-1", listing_code="ETEL",
                               isin="EGS000000002")]},
            {"issuer": "FAIT",
             "listings": [listing("FAIT", "EGS000000003"),
                          listing("FAITA", None, status="blocked",
                                  terminal="blocked",
                                  failures=[{"kind":
                                             "B-02-missing-isin"}])],
             "documents": []},
        ],
    }


def validate(led, manifest=None, mode="fixtures"):
    return worker._validate_top30_ledger(
        led, manifest if manifest is not None else MANIFEST, mode)


def test_honest_baseline_passes():
    ok, reasons = validate(baseline())
    check("baseline: honest incomplete ledger passes", ok and not reasons)


# --- F7: malformed manifest reference never raises ------------------------

def test_f7_malformed_manifest_never_raises():
    for bad in ("not-a-dict", ["x"], 123, None):
        led = baseline()
        led["manifest"] = bad
        ok, reasons = validate(led)
        check("F7: manifest %r fails closed without raising"
              % (bad,),
              ok is False and any("manifest" in r for r in reasons))
    led = baseline()
    del led["manifest"]
    ok, reasons = validate(led)
    check("F7-control: manifest missing fails closed, no crash",
          ok is False and any("manifest" in r for r in reasons))
    ok, reasons = worker._validate_top30_ledger(
        baseline(), ["not", "a", "dict"], "fixtures")
    check("F7: non-dict manifest param fails closed, no crash",
          ok is False and reasons)


def test_malformed_battery_never_raises():
    variants = []
    led = baseline()
    led["collection"] = "not-a-dict"
    variants.append(("collection as string", led))
    led = baseline()
    led["collection"]["missing"] = "FAITA"
    variants.append(("missing as string", led))
    led = baseline()
    led["collection"]["enumerated"] = "2"
    variants.append(("enumerated as string", led))
    led = baseline()
    led["issuers"] = {"TMGH": []}
    variants.append(("issuers as dict", led))
    led = baseline()
    led["issuers"][0] = "not-a-dict"
    variants.append(("issuer record as string", led))
    led = baseline()
    led["issuers"][0]["listings"] = "TMGH"
    variants.append(("listings as string", led))
    led = baseline()
    led["issuers"][0]["listings"] = ["not-a-dict"]
    variants.append(("listing record as string", led))
    led = baseline()
    led["issuers"][0]["documents"] = "TMGH-doc-1"
    variants.append(("documents as string", led))
    led = baseline()
    led["issuers"][0]["documents"] = ["not-a-dict"]
    variants.append(("document record as string", led))
    led = baseline()
    led["issuers"][0]["documents"][0]["corpus"] = "archived"
    variants.append(("corpus as string", led))
    led = baseline()
    led["issuers"][0]["documents"][0]["corpus"]["attachments"] = "oops"
    variants.append(("attachments as string", led))
    led = baseline()
    led["failures"] = "B-02"
    variants.append(("failures as string", led))
    led = baseline()
    led["window"] = "2026-08-19 -> 2026-11-19"
    variants.append(("window as string", led))
    for name, bad_led in variants:
        ok, reasons = validate(bad_led)
        check("malformed battery: %s fails closed without raising"
              % name, ok is False and reasons)
    for bad_ledger in ([], "not-a-ledger", None):
        ok, reasons = validate(bad_ledger)
        check("malformed battery: ledger %r fails closed, no raise"
              % (bad_ledger,), ok is False and reasons)


# --- F9: parser/dispatcher disagreement ------------------------------------

def test_f9_leading_space_parses_and_dispatches():
    job = " top30-enumerate --mode probe"
    plan = worker.parse_top30_job(job)
    check("F9: parser accepts leading-space job",
          plan == {"kind": "top30-enumerate", "mode": "probe",
                   "fixtures": None})
    # The dispatch half of F9 is pinned by the two end-to-end
    # tests below (they fail on base: the job falls through to
    # parse_job -> [] and publishes an empty run as done). This
    # pins the bug's mechanism: the old split(" ", 1) dispatch
    # saw "" as the first token, not "top30-enumerate".
    check("F9: old split(' ', 1) dispatch missed the leading-space "
          "job (first token is '')",
          job.split(" ", 1)[0] == "")


def run_execute(job):
    PUBLISH_SEEN.clear()
    MARK_DONE_SEEN.clear()
    worker._execute_body(job)
    return PUBLISH_SEEN, MARK_DONE_SEEN


def test_f9_leading_space_job_runs_end_to_end():
    fixtures = str(_REPO / "scripts" / "top30_enumerate_fixtures")
    before = ENUMERATOR_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-346-leading-space",
        "job": " top30-enumerate --mode fixtures --fixtures "
               + fixtures,
        "added": worker.now()})
    check("F9: leading-space job dispatches (enumerator ran)",
          ENUMERATOR_INVOKED["n"] == before + 1)
    check("F9: leading-space job publishes an ok run, not an "
          "empty run as done",
          pub.get("manifest", {}).get("tools", {}).get(
              "top30-enumerate") == "ok")
    wd = worker.OUT / "test-346-leading-space" / "top30"
    ledger = json.loads(
        (wd / "top30_expected_docs.json").read_text(encoding="utf-8"))
    check("F9: leading-space job ledger is the fixtures run",
          ledger["mode"] == "fixtures")
    check("F9: leading-space job marked done after publish",
          done.get("archive_sha") == "fake-archive-sha-346")


def test_f9_leading_space_bad_job_still_named():
    before = ENUMERATOR_INVOKED["n"]
    pub, done = run_execute({
        "id": "test-346-leading-space-bad",
        "job": " top30-enumerate --bogus",
        "added": worker.now()})
    check("F9: leading-space bad job dispatches to the named "
          "bad-job failure (not an empty run as done)",
          pub.get("manifest", {}).get("tools", {}).get(
              "top30-enumerate") == "bad-job")
    check("F9: leading-space bad job never invokes the enumerator",
          ENUMERATOR_INVOKED["n"] == before)
    check("F9: leading-space bad job still publishes + marks done",
          done.get("archive_sha") == "fake-archive-sha-346")


# --- F4: summary reconciliation -------------------------------------------

def test_f4_summary_reconciliation():
    led = baseline()
    led["collection"]["archived"] = 555
    ok, reasons = validate(led)
    check("F4: archived=555 vs enumerated=2 fails",
          not ok and any("archived" in r for r in reasons))

    led = baseline()
    led["collection"]["enumerated"] = 999
    ok, reasons = validate(led)
    check("F4: enumerated=999 vs 2 documents fails",
          not ok and any("enumerated" in r for r in reasons))

    led = baseline()
    led["collection"]["enumerated"] = 1
    ok, reasons = validate(led)
    check("F4: enumerated=1 vs 2 documents fails",
          not ok and any("enumerated" in r for r in reasons))

    led = baseline()
    led["collection"]["archived"] = 1
    ok, reasons = validate(led)
    check("F4: archived=1 vs 2 archived documents fails",
          not ok and any("archived" in r for r in reasons))

    led = baseline()
    led["collection"]["missing"] = ["FAITA", "INVENTED-doc-99"]
    ok, reasons = validate(led)
    check("F4: invented missing-document ID fails",
          not ok and any("missing" in r for r in reasons))

    led = baseline()
    led["collection"]["missing"] = ["ZZZZ"]
    ok, reasons = validate(led)
    check("F4: missing entry that is not a frozen route fails",
          not ok and any("missing" in r for r in reasons))

    led = baseline()
    led["collection"]["missing"] = ["FAITA"]
    ok, reasons = validate(led)
    check("F4-control: missing a frozen route (FAITA) still passes",
          ok and not reasons)


# --- F5: route provenance ---------------------------------------------------

def test_f5_route_provenance():
    led = baseline()
    led["issuers"][0]["listings"] = [
        dict(listing("TMGH", "EGS000000001"), isin="EGS000000002")]
    ok, reasons = validate(led)
    check("F5: TMGH listing carrying ETEL's ISIN fails",
          not ok and any("ISIN" in r for r in reasons))

    led = baseline()
    led["issuers"][2]["listings"] = [
        listing("FAIT", "EGS000000003"),
        dict(listing("FAITA", None, status="blocked",
                     terminal="blocked",
                     failures=[{"kind": "B-02-missing-isin"}]),
             isin="EGS000000003")]
    ok, reasons = validate(led)
    check("F5: FAITA carrying the FAIT ISIN fails (never default)",
          not ok and any("ISIN" in r for r in reasons))

    led = baseline()
    led["issuers"][2]["documents"] = [
        doc("FAIT-doc-1", listing_code="FAITA")]
    led["collection"]["enumerated"] = 3
    led["collection"]["archived"] = 3
    ok, reasons = validate(led)
    check("F5: document under FAIT claiming blocked FAITA fails",
          not ok and any("blocked route" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", listing_code="ETEL",
            isin="EGS000000002")]
    ok, reasons = validate(led)
    check("F5: document under TMGH claiming the ETEL route fails",
          not ok and any("not a route of issuer" in r
                         for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", listing_code="ZZZZ")]
    ok, reasons = validate(led)
    check("F5: document claiming nonexistent ZZZZ route fails",
          not ok and any("not a frozen route" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", listing_code="TMGH",
            isin="EGS000000002")]
    ok, reasons = validate(led)
    check("F5: document carrying the wrong ISIN for its listing "
          "fails",
          not ok and any("ISIN" in r for r in reasons))


# --- F6: route universe / duplicates ----------------------------------------

def test_f6_route_universe_and_duplicates():
    led = baseline()
    led["issuers"].append({"issuer": "ZZZZ",
                          "listings": [listing("ZZZZ", "EGS000000009")],
                          "documents": []})
    ok, reasons = validate(led)
    check("F6: invented 32nd route fails",
          not ok and any("not in the frozen manifest" in r
                         for r in reasons))

    led = baseline()
    led["issuers"][0]["listings"] = [
        listing("TMGH", "EGS000000001"),
        listing("TMGH", "EGS000000001")]
    ok, reasons = validate(led)
    check("F6: duplicate TMGH records fail",
          not ok and any("duplicate listing route" in r
                         for r in reasons))

    led = baseline()
    led["issuers"][1]["listings"] = [
        listing("ETEL", "EGS000000002"),
        listing("TMGH", "EGS000000001")]
    ok, reasons = validate(led)
    check("F6: same route recorded under two issuers fails",
          not ok and any("duplicate listing route" in r
                         for r in reasons))

    led = baseline()
    led["issuers"].append({"issuer": "ZZZZ", "listings": [],
                          "documents": []})
    ok, reasons = validate(led)
    check("F6: issuer outside the frozen manifest fails",
          not ok and any("not in the frozen manifest" in r
                         for r in reasons))

    led = baseline()
    led["issuers"][0]["listings"] = []
    led["issuers"][1]["listings"] = [
        listing("ETEL", "EGS000000002"),
        listing("TMGH", "EGS000000001")]
    ok, reasons = validate(led)
    check("F6: route recorded under the wrong issuer fails",
          not ok and any("belongs to" in r for r in reasons))


# --- F8: corpus hash shape --------------------------------------------------

def test_f8_corpus_hash_shape():
    led = baseline()
    led["issuers"][0]["documents"] = [doc("TMGH-doc-1", sha="ab")]
    ok, reasons = validate(led)
    check("F8: archived with 2-char hash fails",
          not ok and any("body_sha256" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", sha="z" * 64)]
    ok, reasons = validate(led)
    check("F8: archived with non-hex 64-char hash fails",
          not ok and any("body_sha256" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", sha="A" * 64)]
    ok, reasons = validate(led)
    check("F8: archived with uppercase hash fails (producer shape "
          "is lowercase hex)",
          not ok and any("body_sha256" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", sha=None)]
    ok, reasons = validate(led)
    check("F8: archived with no hash fails",
          not ok and any("body_sha256" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", status="partial",
            kind="clipped-body-sha256", sha="ab")]
    led["collection"]["archived"] = 1
    ok, reasons = validate(led)
    check("F8: partial with a 2-char hash fails",
          not ok and any("body_sha256" in r for r in reasons))

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", status="not_captured", kind=None,
            sha=None, listing_code="TMGH",
            isin="EGS000000001")]
    led["collection"]["archived"] = 1
    ok, reasons = validate(led)
    check("F8-control: not_captured with no hash still passes",
          ok and not reasons)

    led = baseline()
    led["issuers"][0]["documents"] = [
        doc("TMGH-doc-1", listing_code="TMGH",
            isin="EGS000000001",
            attachments=[{"status": "link_found",
                          "path": None, "sha256": None,
                          "source_url": "https://x/y.pdf"}])]
    ok, reasons = validate(led)
    check("F8-control: link_found attachment without a hash still "
          "passes (attachment accounting is a later step)",
          ok and not reasons)


# --- Honest controls (no regression) ----------------------------------------

def test_honest_controls():
    manifest = real_manifest()
    ok, reasons = worker._validate_top30_ledger(
        real_probe_ledger(), manifest, "probe")
    check("control: committed honest probe ledger still passes",
          ok and reasons == [])

    led = copy.deepcopy(real_probe_ledger())
    led["collection"]["enumeration_closed"] = True
    led["collection"]["pagination_complete"] = True
    led["failures"] = []
    for irec in led["issuers"]:
        for lrec in irec["listings"]:
            lrec["terminal_state"] = "exhausted"
    ok, reasons = worker._validate_top30_ledger(
        led, manifest, "probe")
    check("control: #340 variant-A ledger still fails closed",
          not ok and any("listing-level failure" in r
                         for r in reasons))


# --- F2: persistent-profile transport ---------------------------------------
#
# The wiring: run_top30_enumerate passes --transport profile
# --profile <egx-profile> in live mode; the enumerator's
# ProfileFetcher loads pages through launch_persistent_context
# on that profile. Playwright is NOT installed on this VM, so
# the unit tests stub the playwright module in sys.modules and
# the end-to-end test serves a stub playwright package on
# PYTHONPATH. No live EGX is touched anywhere here.

CANNED_EMPTY_PAGE = ("<html><body><div class=\"results\">"
                     "no results found</div></body></html>")


class _StubResponse:
    def __init__(self, status=200):
        self.status = status


class _StubPage:
    def __init__(self, calls, body):
        self._calls = calls
        self._body = body

    def goto(self, url, timeout=None, wait_until=None):
        self._calls.append(("goto", url))
        return _StubResponse(200)

    def content(self):
        return self._body


class _StubContext:
    def __init__(self, calls, body):
        self._calls = calls
        self._body = body

    def new_page(self):
        return _StubPage(self._calls, self._body)

    def close(self):
        self._calls.append(("context-close",))


class _StubChromium:
    def __init__(self, calls, body):
        self._calls = calls
        self._body = body

    def launch_persistent_context(self, profile_dir, headless=None):
        self._calls.append(("launch", profile_dir, headless))
        return _StubContext(self._calls, self._body)


class _StubPlaywright:
    def __init__(self, calls, body):
        self.chromium = _StubChromium(calls, body)
        self._calls = calls

    def start(self):
        return self

    def stop(self):
        self._calls.append(("stop",))


def _install_stub_playwright(calls, body=CANNED_EMPTY_PAGE):
    """Install a fake playwright.sync_api in sys.modules; returns
    a restore function."""
    saved = {k: sys.modules.get(k) for k in
             ("playwright", "playwright.sync_api")}
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = \
        lambda: _StubPlaywright(calls, body)
    pkg = types.ModuleType("playwright")
    pkg.sync_api = sync_api
    sys.modules["playwright"] = pkg
    sys.modules["playwright.sync_api"] = sync_api

    def restore():
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return restore


def test_f2_profile_fetcher_uses_the_profile_session():
    calls = []
    restore = _install_stub_playwright(calls)
    try:
        fetcher = ENUM.ProfileFetcher("/fake/egx-profile")
        url = "https://www.egx.com.eg/ar/NewsSearch.aspx?isin=EGS000000001"
        res = fetcher(url)
        check("F2: profile fetcher returns the page body",
              res["body"] == CANNED_EMPTY_PAGE
              and res["status"] == 200 and res["fetched_at"])
        check("F2: profile fetcher launched a persistent context "
              "on the profile dir, headless",
              ("launch", "/fake/egx-profile", True) in calls)
        check("F2: profile fetcher navigated the browser to the URL",
              ("goto", url) in calls)
        fetcher.close()
        fetcher.close()
        check("F2: profile fetcher close is safe (and repeatable)",
              True)
    finally:
        restore()


def test_f2_profile_fetcher_fails_closed_without_playwright():
    saved = {k: sys.modules.get(k) for k in
             ("playwright", "playwright.sync_api")}
    for k in ("playwright", "playwright.sync_api"):
        sys.modules.pop(k, None)
    try:
        # Playwright is not installed on this VM: the import must
        # fail, and the fetcher must raise a named FetchFailure —
        # never crash, never return a synthetic empty page.
        fetcher = ENUM.ProfileFetcher("/fake/egx-profile")
        try:
            fetcher("https://www.egx.com.eg/")
            check("F2: fetch without Playwright raises FetchFailure",
                  False)
        except ENUM.FetchFailure as e:
            check("F2: fetch without Playwright raises FetchFailure",
                  "playwright" in e.error.lower())
            check("F2: fetch without Playwright names the URL",
                  e.url.startswith("https://www.egx.com.eg/"))
        try:
            fetcher("https://www.egx.com.eg/")
            check("F2: a failed launch stays failed (no retry loop)",
                  False)
        except ENUM.FetchFailure:
            check("F2: a failed launch stays failed (no retry loop)",
                  True)
        fetcher.close()
        check("F2: close after a failed launch does not raise", True)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def _write_stub_playwright_package(stub_dir):
    """A fake `playwright` package on disk: the enumerator
    subprocess (run under the venv python) imports it via
    PYTHONPATH and serves the canned empty page for every URL."""
    pkg = stub_dir / "playwright"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "sync_api.py").write_text(
        "CANNED = %r\n"
        "class _Resp:\n"
        "    status = 200\n"
        "class _Page:\n"
        "    def goto(self, url, timeout=None, wait_until=None):\n"
        "        return _Resp()\n"
        "    def content(self):\n"
        "        return CANNED\n"
        "class _Ctx:\n"
        "    def new_page(self):\n"
        "        return _Page()\n"
        "    def close(self):\n"
        "        pass\n"
        "class _Chromium:\n"
        "    def launch_persistent_context(self, profile_dir,\n"
        "                                headless=None):\n"
        "        return _Ctx()\n"
        "class _PW:\n"
        "    def __init__(self):\n"
        "        self.chromium = _Chromium()\n"
        "    def start(self):\n"
        "        return self\n"
        "    def stop(self):\n"
        "        pass\n"
        "def sync_playwright():\n"
        "    return _PW()\n" % CANNED_EMPTY_PAGE,
        encoding="utf-8")


def test_f2_live_mode_runs_through_the_profile():
    profile_dir = worker.ROOT / "egx-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    stub_dir = _TMP / "stub-playwright"
    _write_stub_playwright_package(stub_dir)
    old_path = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = str(stub_dir)
    COMMANDS_SEEN.clear()
    before = ENUMERATOR_INVOKED["n"]
    try:
        pub, done = run_execute({
            "id": "test-346-live-profile",
            "job": "top30-enumerate",
            "added": worker.now()})
    finally:
        if old_path is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = old_path
        shutil.rmtree(profile_dir, ignore_errors=True)
    enum_cmds = [c for c in COMMANDS_SEEN if "top30_enumerate.py" in c]
    check("F2: live mode invokes the enumerator once",
          ENUMERATOR_INVOKED["n"] == before + 1 and len(enum_cmds) == 1)
    check("F2: live mode passes --transport profile to the "
          "enumerator",
          any("--transport" in c and "profile" in c
              for c in enum_cmds))
    check("F2: live mode passes the persistent profile dir",
          any(str(profile_dir) in c for c in enum_cmds))
    check("F2: live mode through the profile completes ok",
          pub.get("manifest", {}).get("tools", {}).get(
              "top30-enumerate") == "ok")
    wd = worker.OUT / "test-346-live-profile" / "top30"
    ledger = json.loads(
        (wd / "top30_expected_docs.json").read_text(encoding="utf-8"))
    check("F2: live ledger records transport=profile",
          ledger.get("transport") == "profile")
    check("F2: live ledger mode is live, honestly open (FAITA "
          "blocked, canned empty pages)",
          ledger["mode"] == "live"
          and ledger["collection"]["enumeration_closed"] is False
          and len(ledger["issuers"]) == 30)
    faita = [l for i in ledger["issuers"] for l in i["listings"]
             if l["code"] == "FAITA"][0]
    check("F2: live ledger still carries FAITA as the named "
          "blocked route",
          faita["enumeration_status"] == "blocked" and any(
              f.get("kind") == "B-02-missing-isin"
              for f in faita["failures"]))
    validation = json.loads(
        (wd / "top30-validation.json").read_text(encoding="utf-8"))
    check("F2: validation record carries transport=profile",
          validation.get("transport") == "profile"
          and validation["valid"] is True)
    check("F2: live profile run marked done after publish",
          done.get("archive_sha") == "fake-archive-sha-346")


def main():
    worker.sh = fake_sh
    worker.publish = stub_publish
    worker._mark_done = stub_mark_done
    setup_release()
    test_honest_baseline_passes()
    test_f7_malformed_manifest_never_raises()
    test_malformed_battery_never_raises()
    test_f9_leading_space_parses_and_dispatches()
    test_f9_leading_space_job_runs_end_to_end()
    test_f9_leading_space_bad_job_still_named()
    test_f4_summary_reconciliation()
    test_f5_route_provenance()
    test_f6_route_universe_and_duplicates()
    test_f8_corpus_hash_shape()
    test_honest_controls()
    test_f2_profile_fetcher_uses_the_profile_session()
    test_f2_profile_fetcher_fails_closed_without_playwright()
    test_f2_live_mode_runs_through_the_profile()
    print(f"\n{PASSED} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
