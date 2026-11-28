#!/usr/bin/env python3
"""Tests for gdelt-fetch job type."""
import inspect
import json
import os
import shlex
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _test_tmp
_TMP = _test_tmp.mkdtemp(prefix="gator-gdelt-test-")
os.environ["GATOR_ROOT"] = str(_TMP)

_HERE = Path(os.path.abspath(__file__)).parent
_REPO = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO / "scripts"))

import worker
# Minimal release checkout: scripts + evaluation CSVs
_code = worker.CODE
(_code / "scripts").mkdir(parents=True, exist_ok=True)
(_code / "evaluation").mkdir(parents=True, exist_ok=True)
import shutil as _sh
_sh.copyfile(_REPO / "scripts" / "gdelt_gkg_filter.py", _code / "scripts" / "gdelt_gkg_filter.py")
for f in ("gdelt_alias_table.csv","gdelt_macro_themes.csv"):
    _sh.copyfile(_REPO / "evaluation" / f, _code / "evaluation" / f)

(_code / "registry").mkdir(parents=True, exist_ok=True)
_sh.copyfile(_REPO / "registry" / "tools.json", _code / "registry" / "tools.json")

PASSED = 0
def check(name, cond, detail=""):
    global PASSED
    assert cond, "%s %s" % (name, detail)
    PASSED += 1
    print("pass: %s" % name)

def test_parse_ok():
    plan = worker.parse_gdelt_fetch_job(
        "gdelt-fetch --start 20240501000000 --end 20240531235959")
    check("parse: full live job", plan is not None and plan["start"]=="20240501000000"
          and plan["end"]=="20240531235959" and plan["mode"]=="live"
          and plan["workers"]==6 and plan["budget_seconds"]==0)

def test_parse_fixtures():
    plan = worker.parse_gdelt_fetch_job(
        "gdelt-fetch --start 20240501000000 --end 20240531235959 --mode fixtures")
    check("parse: fixtures mode", plan is not None and plan["mode"]=="fixtures")

def test_parse_rejects_non_ascii_digits():
    arabic = "\u0662\u0660\u0662\u0664\u0660\u0665\u0660\u0661\u0660\u0660\u0660\u0660\u0660\u0660"
    check("parse: 14 non-ASCII digits are digits for str.isdigit (premise)", arabic.isdigit() and len(arabic) == 14)
    check("parse: non-ASCII --start rejected", worker.parse_gdelt_fetch_job("gdelt-fetch --start %s --end 20240531235959" % arabic) is None)
    check("parse: non-ASCII --end rejected", worker.parse_gdelt_fetch_job("gdelt-fetch --start 20240501000000 --end %s" % arabic) is None)
    check("parse: ASCII still accepted", worker.parse_gdelt_fetch_job("gdelt-fetch --start 20240501000000 --end 20240531235959") is not None)

def test_filter_launch_env_is_denylist_filtered():
    _fixtures_env()
    job = {"id": "env-1", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    orig = worker.sh_group
    seen = {}
    def fake(cmd, cwd=None, env=None, timeout=3600):
        seen["env"] = env
        return _Res(0, "chunk done\n")
    # The archive lookup runs before the filter: create the local bare
    # remote (and its checkout) FIRST, so this test passes when run alone
    # instead of trying to clone the sentinel host and stopping with
    # archive-check-failed before `fake` is called.
    _ensure_remote()
    prev_url = os.environ.get("GATOR_BUS_URL")
    os.environ["GATOR_BUS_URL"] = "https://example.invalid/bus"
    worker.sh_group = fake
    try:
        wd = worker.OUT / "t959-env"; wd.mkdir(parents=True, exist_ok=True)
        worker.run_gdelt_fetch(job, wd)
    finally:
        worker.sh_group = orig
        if prev_url is None:
            os.environ.pop("GATOR_BUS_URL", None)
        else:
            os.environ["GATOR_BUS_URL"] = prev_url
    e = seen.get("env")
    check("filter launch passes an explicit env", isinstance(e, dict) and "PATH" in e)
    check("filter launch env carries no denied key", e is not None and not (set(e) & worker.ENV_DENY_FOR_TOOLS))
    check("GATOR_BUS_URL is among the denied keys (premise)", "GATOR_BUS_URL" in worker.ENV_DENY_FOR_TOOLS)

def _wprog(jid, until):
    pth = worker._gdelt_progress_path(jid)
    pth.parent.mkdir(parents=True, exist_ok=True)
    pth.write_text(json.dumps({"total": 1, "stalls": 0, "deferred_until": until}, allow_nan=True))

def test_deferred_unparseable_deadline():
    jid = "defer-bad"
    for bad in ("soon", [1], {"a": 1}, None, "", float("nan")):
        _wprog(jid, bad)
        check("deferred_until=%r does not raise and means not deferred" % (bad,), worker._gdelt_deferred(jid) is False)
    _wprog(jid, time.time() + 1000)
    check("a valid future deadline still defers", worker._gdelt_deferred(jid) is True)

def _rel(d):
    return "worker-runs/%s/%s" % (d.parent.name, d.name)

def _local_state(wd, text, binding=None):
    st = wd / "gdelt-state"
    st.mkdir(parents=True, exist_ok=True)
    (st / "done.txt").write_text(text)
    if binding is not None:
        (st / worker.GDELT_BINDING).write_text(json.dumps({"run": binding}))

def test_restore_checks_recorded_mode():
    _fixtures_env()
    live = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode live"
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    _make_archive_run("2026-11-27", "100000", "x", "mode-pred", "FIXTURE-STATE\n", mode="fixtures")
    called = []
    res, seen = _run_capture({"id": "mode-succ", "job": live + " --resume-from mode-pred"}, worker.OUT / "t959-mode1",
                             lambda c: called.append(c) or _Res())
    check("live job with a fixtures predecessor: named outcome, nothing restored, no filter run",
          res == {"gdelt-fetch": "resume-mode-mismatch"} and not called and not (worker.OUT / "t959-mode1" / "gdelt-state" / "done.txt").exists())
    check("mismatch is written to the run log", "resume-mode-mismatch" in (worker.OUT / "t959-mode1" / "gdelt" / "gdelt-fetch.log").read_text())
    res, seen = _run_capture({"id": "mode-succ2", "job": fix + " --resume-from mode-pred"}, worker.OUT / "t959-mode2", lambda c: _Res())
    check("same-mode predecessor still restores", seen["state_text"] == "FIXTURE-STATE\n")
    _make_archive_run("2026-11-27", "100000", "x", "legacy-pred", "LEGACY\n", mode=None)
    res, seen = _run_capture({"id": "legacy-succ", "job": fix + " --resume-from legacy-pred"}, worker.OUT / "t959-mode3", lambda c: _Res())
    check("a predecessor with no recorded mode is rejected for --resume-from", res == {"gdelt-fetch": "resume-mode-mismatch"})
    _make_archive_run("2026-11-27", "100000", "x", "legacy-own", "LEGACY-OWN\n", mode=None)
    res, seen = _run_capture({"id": "legacy-own", "job": fix}, worker.OUT / "t959-mode4", lambda c: _Res())
    check("the job's own legacy run (same plan) still resumes", seen["state_text"] == "LEGACY-OWN\n")
    _make_archive_run("2026-11-27", "100000", "x", "own-cross", "X\n", mode="live")
    res, seen = _run_capture({"id": "own-cross", "job": fix}, worker.OUT / "t959-mode5", lambda c: _Res())
    check("a same-id run recorded in another mode is rejected too", res == {"gdelt-fetch": "resume-mode-mismatch"})

def test_restore_is_staged_and_atomic():
    _fixtures_env()
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    d = _make_archive_run("2026-11-27", "100000", "x", "stage-1", "PUB\n", matches='{"ok": 1}\nnot json\n')
    wd = worker.OUT / "t959-stage"
    _local_state(wd, "LOCAL\n", binding="worker-runs/older/run")
    (wd / "gdelt-out").mkdir(parents=True, exist_ok=True)
    (wd / "gdelt-out" / "matches.jsonl").write_text('{"local": 1}\n')
    res, seen = _run_capture({"id": "stage-1", "job": fix}, wd, lambda c: _Res())
    check("a restore that fails validation stops the run (unknown resume state) and leaves the previous done.txt",
          res == {"gdelt-fetch": "archive-check-failed"} and "cmd" not in seen
          and (wd / "gdelt-state" / "done.txt").read_text() == "LOCAL\n")
    check("and the previous matches", (wd / "gdelt-out" / "matches.jsonl").read_text() == '{"local": 1}\n')
    check("and no partial restore files or scratch directories", not [p for p in wd.iterdir() if p.name.startswith(".gdelt-restore")]
          and not (wd / "gdelt-state" / "config.json").exists())
    d2 = _make_archive_run("2026-11-28", "100000", "x", "stage-2", "PUB2\n", matches='{"ok": 1}\n', macro='{"m": 1}\n')
    wd2 = worker.OUT / "t959-stage2"
    res, seen = _run_capture({"id": "stage-2", "job": fix}, wd2, lambda c: _Res())
    check("a valid restore commits state, matches and the binding together",
          seen["state_text"] == "PUB2\n" and (wd2 / "gdelt-out" / "matches.jsonl").read_text() == '{"ok": 1}\n'
          and (wd2 / "gdelt-out" / "macro_matches.jsonl").exists()
          and json.loads((wd2 / "gdelt-state" / worker.GDELT_BINDING).read_text())["run"] == _rel(d2))

def test_new_claim_checks_the_published_snapshot():
    _fixtures_env()
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    a = _make_archive_run("2026-11-26", "100000", "x", "snap-1", "SNAP-A\n")
    b = _make_archive_run("2026-11-27", "100000", "x", "snap-1", "SNAP-B\n")
    job = {"id": "snap-1", "job": fix}
    wd = worker.OUT / "t959-snap1"; _local_state(wd, "LOCAL\n", binding=_rel(b))
    res, seen = _run_capture(job, wd, lambda c: _Res())
    check("local checkpoint bound to the latest published run keeps the fast path", seen["state_text"] == "LOCAL\n")
    wd = worker.OUT / "t959-snap2"; _local_state(wd, "LOCAL\n", binding=_rel(a))
    res, seen = _run_capture(job, wd, lambda c: _Res())
    check("another worker advanced the job: the latest snapshot is restored over the stale local one", seen["state_text"] == "SNAP-B\n")
    wd = worker.OUT / "t959-snap3"; _local_state(wd, "LOCAL\n")
    res, seen = _run_capture(job, wd, lambda c: _Res())
    check("an unbound local checkpoint is replaced by the latest published snapshot", seen["state_text"] == "SNAP-B\n")
    wd = worker.OUT / "t959-snap4"; _local_state(wd, "LOCAL\n")
    res, seen = _run_capture({"id": "never-published", "job": fix}, wd, lambda c: _Res())
    check("nothing published: the local checkpoint stays", seen["state_text"] == "LOCAL\n")

def _mk(jid, matches=None, mode="fixtures", **kw):
    return _make_archive_run("2026-11-27", "100000", "x", jid, kw.pop("done", "PUB\n"), matches=matches, mode=mode, **kw)

W999 = ("20240501000000", "20240501999999")
FIXJOB = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"

def test_959i_restore_tail_and_records():
    _fixtures_env()
    # 1: interrupted tail on the published checkpoint is repaired on the staged copy
    _mk("i-tail", matches='{"ok": 1}\n{"partial": "no newline')
    wd = worker.OUT / "t959i-tail"
    res, seen = _run_capture({"id": "i-tail", "job": FIXJOB}, wd, lambda c: _Res())
    check("an interrupted JSONL tail no longer rejects the snapshot", seen["state_text"] == "PUB\n")
    check("the partial record is cut, complete rows kept", (wd / "gdelt-out" / "matches.jsonl").read_text() == '{"ok": 1}\n')
    f = Path(tempfile.mkdtemp()) / "m.jsonl"
    f.write_bytes(b'{"a": 1}\n{"a": "\xd8')
    cut = worker._truncate_tail_bytes(f)
    check("a tail cut inside a UTF-8 character is removed byte-safely", f.read_bytes() == b'{"a": 1}\n' and cut == 8)
    _mk("i-bad", matches='{"ok": 1}\nnot json\n{"ok": 2}\n')
    wd = worker.OUT / "t959i-bad"; _local_state(wd, "LOCAL\n")
    res, seen = _run_capture({"id": "i-bad", "job": FIXJOB}, wd, lambda c: _Res())
    check("a complete malformed record rejects the snapshot and the run stops (unknown resume state, no filter launch)",
          res == {"gdelt-fetch": "archive-check-failed"} and "cmd" not in seen
          and (wd / "gdelt-state" / "done.txt").read_text() == "LOCAL\n")
    # 2: U+2028 inside a valid record
    _mk("i-u2028", matches='{"t": "a\u2028b"}\n{"t": "c"}\n')
    wd = worker.OUT / "t959i-u2028"
    res, seen = _run_capture({"id": "i-u2028", "job": FIXJOB}, wd, lambda c: _Res())
    check("a valid record containing U+2028 is not split and the snapshot restores", seen["state_text"] == "PUB\n")

def test_959i_swap_order_and_rollback():
    _fixtures_env()
    _mk("i-swap", matches='{"ok": 1}\n')
    arch = worker.ROOT / "archive-push"
    # 3: output installed before state; failure on the state install rolls back
    wd = worker.OUT / "t959i-swap"; _local_state(wd, "LOCAL\n", binding="worker-runs/older/run")
    (wd / "gdelt-out").mkdir(parents=True, exist_ok=True); (wd / "gdelt-out" / "matches.jsonl").write_text('{"local": 1}\n')
    real, order = os.rename, []
    def spy(src, dst, *a, **k):
        order.append((Path(src).name, Path(dst).name)); return real(src, dst, *a, **k)
    os.rename = spy
    try:
        worker._gdelt_restore_remote(arch, "i-swap", wd / "gdelt-state", wd / "gdelt-out", mode="fixtures")
    finally:
        os.rename = real
    installs = [t for t in order if t[1] in ("gdelt-out", "gdelt-state")]
    check("the new output is installed before the new state", [t[1] for t in installs][-2:] == ["gdelt-out", "gdelt-state"])
    wd = worker.OUT / "t959i-swap2"; _local_state(wd, "LOCAL\n", binding="worker-runs/older/run")
    (wd / "gdelt-out").mkdir(parents=True, exist_ok=True); (wd / "gdelt-out" / "matches.jsonl").write_text('{"local": 1}\n')
    def fail_state(src, dst, *a, **k):
        if Path(src).name == "state" and Path(dst).name == "gdelt-state":
            raise OSError("boom")
        return real(src, dst, *a, **k)
    os.rename = fail_state
    try:
        try:
            worker._gdelt_restore_remote(arch, "i-swap", wd / "gdelt-state", wd / "gdelt-out", mode="fixtures")
            raised = False
        except OSError:
            raised = True
    finally:
        os.rename = real
    check("a failure installing the state rolls back to the previous state AND output",
          raised and (wd / "gdelt-state" / "done.txt").read_text() == "LOCAL\n"
          and (wd / "gdelt-out" / "matches.jsonl").read_text() == '{"local": 1}\n'
          and not [p for p in wd.iterdir() if p.name.startswith(".gdelt-restore")])
    # 4: rollback itself fails: backups are preserved and the run stops
    wd = worker.OUT / "t959i-swap3"; _local_state(wd, "LOCAL\n", binding="worker-runs/older/run")
    (wd / "gdelt-out").mkdir(parents=True, exist_ok=True); (wd / "gdelt-out" / "matches.jsonl").write_text('{"local": 1}\n')
    def fail_both(src, dst, *a, **k):
        if (Path(src).name == "state" and Path(dst).name == "gdelt-state") or Path(src).name == "prev-out":
            raise OSError("boom")
        return real(src, dst, *a, **k)
    os.rename = fail_both
    called = []
    try:
        res, seen = _run_capture({"id": "i-swap", "job": FIXJOB}, wd, lambda c: called.append(c) or _Res())
    finally:
        os.rename = real
    left = [p for p in wd.iterdir() if p.name.startswith(".gdelt-restore")]
    check("rollback failure: named outcome, filter not run", res == {"gdelt-fetch": "restore-rollback-failed"} and not called)
    check("rollback failure: the staging dir with the previous output is preserved",
          len(left) == 1 and (left[0] / "prev-out" / "matches.jsonl").read_text() == '{"local": 1}\n')

def test_959i_dirs_lookup_predecessor():
    _fixtures_env()
    # 5
    base = Path(tempfile.mkdtemp()); synced = []
    o = worker._fsync_dir; worker._fsync_dir = lambda p: synced.append(str(p))
    try:
        worker._makedirs_durable(base / "a" / "b" / "state")
    finally:
        worker._fsync_dir = o
    exp = [str(base / "a" / "b" / "state"), str(base / "a" / "b"), str(base / "a")]
    check("worker-created directories and their parents are fsynced", all(e in synced for e in exp + [str(base)]))
    # 6: the archive checkout must exist BEFORE the failure is injected, so the
    # runner reaches the lookup and calls bad_fetch (no GATOR_BUS_URL needed)
    _ensure_remote()
    o_sh = worker.sh
    bad_calls = []
    def bad_fetch(cmd, *a, **k):
        if " fetch origin" in cmd:
            bad_calls.append(cmd)
            return _Res(1, "")
        return o_sh(cmd, *a, **k)
    worker.sh = bad_fetch
    called = []
    try:
        res, seen = _run_capture({"id": "i-look", "job": FIXJOB}, worker.OUT / "t959i-look", lambda c: called.append(c) or _Res())
    finally:
        worker.sh = o_sh
    check("a failed archive check is a named outcome and nothing runs", res == {"gdelt-fetch": "archive-check-failed"} and not called)
    check("the injected fetch failure was actually exercised", bad_calls)
    o_pub, o_md, o_run = worker.publish, worker._mark_done, worker.run_gdelt_fetch
    pubs = []
    worker.publish = lambda job, wd, m: pubs.append(1) or "sha"
    worker._mark_done = lambda job, sha, extra=None: None
    worker.run_gdelt_fetch = lambda job, wd: {"gdelt-fetch": "archive-check-failed"}
    try:
        r = worker._execute({"id": "i-look2", "job": FIXJOB})
    finally:
        worker.publish, worker._mark_done, worker.run_gdelt_fetch = o_pub, o_md, o_run
    check("archive-check-failed publishes nothing and releases the claim", not pubs and r == "incomplete")
    # 7
    called = []
    res, seen = _run_capture({"id": "i-pred", "job": FIXJOB + " --resume-from no-such-pred"}, worker.OUT / "t959i-pred", lambda c: called.append(c) or _Res())
    check("a missing explicit predecessor is a named outcome, no fresh backfill",
          res == {"gdelt-fetch": "resume-predecessor-missing"} and not called)
    ran = []
    res, seen = _run_capture({"id": "i-pred2", "job": FIXJOB}, worker.OUT / "t959i-pred2", lambda c: ran.append(c) or _Res())
    check("without --resume-from a fresh start runs the filter and is ok", res == {"gdelt-fetch": "ok"} and len(ran) == 1)

def test_959i_deferred_and_stall_and_intent():
    jid = "i-def"
    pth = worker._gdelt_progress_path(jid); pth.parent.mkdir(parents=True, exist_ok=True)
    for raw in ('{"total": 1, "stalls": 0, "deferred_until": 1' + "0" * 400 + '}', '{"total": 1, "stalls": 0, "deferred_until": Infinity}',
                '{"total": 1, "stalls": 0, "deferred_until": -Infinity}', '{"total": 1, "stalls": 0, "deferred_until": NaN}'):
        pth.write_text(raw)
        try:
            v = worker._gdelt_deferred(jid)
            ok = v is False
        except Exception:
            ok = False
        check("deferred_until %s does not raise or defer" % raw[-24:], ok)
    pth.write_text(json.dumps({"total": 1, "stalls": 0, "deferred_until": time.time() + 1000}))
    check("a finite future deadline still defers", worker._gdelt_deferred(jid) is True)
    # 10: first-time transient failures are progress, repeats are not
    j2 = "i-stall"; worker._gdelt_progress_clear(j2)
    _progress_run(j2, 0, transient=3)
    for t, name in ((6, "new transient files"), (9, "more new transient files")):
        worker._intent_path(j2).unlink(missing_ok=True)
        _progress_run(j2, 0, transient=t)
        check("%s count as advancement" % name, worker._gdelt_progress_read(j2)["stalls"] == 0)
    for i in range(worker.GDELT_STALL_LIMIT):
        worker._intent_path(j2).unlink(missing_ok=True)
        _progress_run(j2, 0, transient=9)
    check("repeat failures of the same files stall and defer", worker._gdelt_deferred(j2))
    # 9: intent cleanup retried without rerunning the fetch
    j3 = "i-intent"; ip = worker._intent_path(j3); ip.parent.mkdir(parents=True, exist_ok=True); ip.write_text("x")
    # 959o F6: the claim this host holds carries an attempt id, which the cleanup marker records
    _cl3 = worker.BUS / "queue" / "claims" / (j3 + ".json"); _cl3.parent.mkdir(parents=True, exist_ok=True)
    _cl3.write_text(json.dumps({"worker": "h", "attempt": "att-i3"}))
    real_unlink = Path.unlink
    def failing(self, *a, **k):
        if self == ip:
            raise OSError("ro")
        return real_unlink(self, *a, **k)
    Path.unlink = failing
    try:
        released = worker._gdelt_release_intent(j3, "sha9")
        marker = worker._gdelt_cleanup_marker(j3).exists()
    finally:
        Path.unlink = real_unlink
    check("failed intent cleanup is reported and recorded with the verified publication", released is False and marker and ip.exists())
    rc_calls = []
    o_rc = worker._release_claim
    worker._release_claim = lambda jid, only_own=False, expect_attempt=False: rc_calls.append((jid, only_own, expect_attempt)) or True
    try:
        pending = worker._done_or_pending(j3)
    finally:
        worker._release_claim = o_rc
    check("once storage recovers the retry removes intent and marker without rerunning the fetch",
          not ip.exists() and not worker._gdelt_cleanup_marker(j3).exists() and pending is False)
    check("the replayed cleanup then releases only this host's claim, bound to its attempt id", rc_calls == [(j3, True, "att-i3")], str(rc_calls))
    # 959o F6: a marker WITHOUT a nonempty-string attempt id releases no claim, whatever the claim holds
    for _nm, _att in (("missing", "__absent__"), ("null", None), ("empty", ""), ("non-string", 7)):
        jb = "i-intent-noatt-%s" % _nm; ipb = worker._intent_path(jb); ipb.parent.mkdir(parents=True, exist_ok=True)
        ipb.write_text(json.dumps({"job": "A", "started": "t1"}))
        mk = {"intent": ipb.read_text()}
        if _att != "__absent__":
            mk["claim_attempt"] = _att
        mpb = worker._gdelt_cleanup_marker(jb); mpb.parent.mkdir(parents=True, exist_ok=True); mpb.write_text(json.dumps(mk))
        calls = []
        worker._release_claim = lambda jid, only_own=False, expect_attempt=False: calls.append((jid, expect_attempt)) or True
        try:
            worker._done_or_pending(jb)
        finally:
            worker._release_claim = o_rc
        check("959o F6: intent-cleanup replay with %s claim_attempt releases NO claim and drops the marker" % _nm,
              calls == [] and not mpb.exists(), str(calls))
    # execute-level: a failed cleanup does not release the claim
    # No pre-written intent: _execute creates it, the unlink of THAT intent fails.
    j4 = "i-intent2"; ip4 = worker._intent_path(j4)
    ip4.unlink(missing_ok=True); worker._gdelt_cleanup_marker(j4).unlink(missing_ok=True)
    attempts, pubs4 = [], []
    def failing4(self, *a, **k):
        if self == ip4:
            attempts.append(1)
            raise OSError("ro")
        return real_unlink(self, *a, **k)
    Path.unlink = failing4
    try:
        r = _progress_run(j4, 5, pubs=pubs4)
    finally:
        Path.unlink = real_unlink
    check("the run was published and the intent cleanup was attempted before the return value is judged",
          pubs4 == [j4] and len(attempts) >= 1 and ip4.exists())
    check("an incomplete published run with a stuck intent does not report itself resumable", r is None)
    ip4.unlink(missing_ok=True); worker._gdelt_cleanup_marker(j4).unlink(missing_ok=True)

def test_parse_rejects():
    for bad in ["", "gdelt-fetch", "gdelt-fetch --start 20240501000000",
                "gdelt-fetch --end 20240531235959",
                "gdelt-fetch --start 20240501000000 --end 20240501000000 --foo bar",
                "gdelt-fetch --start 202405010000 --end 20240531235959",
                "gdelt-fetch --start 20240531235959 --end 20240501000000"]:
        check("parse: rejects %r" % bad, worker.parse_gdelt_fetch_job(bad) is None)
    check("parse: non-string", worker.parse_gdelt_fetch_job(None) is None)

import contextlib as _ctx

@_ctx.contextmanager
def _no_bus_url_no_clone():
    """959o F2: run_gdelt_fetch clones ROOT/archive-push from GATOR_BUS_URL when
    that checkout is absent. Clear the URL for the run and fail the test if any
    `git clone` is attempted, so it can never clone a developer's real archive."""
    prev, o_sh, cmds = os.environ.pop("GATOR_BUS_URL", None), worker.sh, []
    def spy(cmd, *a, **k):
        cmds.append(cmd)
        return o_sh(cmd, *a, **k)
    worker.sh = spy
    try:
        yield cmds
    finally:
        worker.sh = o_sh
        if prev is not None:
            os.environ["GATOR_BUS_URL"] = prev
    check("959o F2: no git clone was attempted (GATOR_BUS_URL cleared)", not any("git clone" in c for c in cmds), str(cmds))

def test_fixtures_run():
    # build fixture master lists — real 3-field format '<size> <md5> <url>'
    # with a timestamp OUTSIDE the job's start/end range, so list_files
    # legitimately selects 0 files with NO network fetch (plumbing-only check).
    fx = Path(tempfile.mkdtemp())
    (fx / "masterfilelist.txt").write_text(
        "12345 d41d8cd98f00b204e9800998ecf8427e "
        "https://data.gdeltproject.org/gdeltv2/20240601000000.gkg.csv.zip\n")
    (fx / "masterfilelist-translation.txt").write_text("")
    os.environ["GDELT_FIXTURE_MASTER_DIR"] = str(fx)
    job = {"id": "test-gdelt-1", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    wd = worker.OUT / "test-gdelt-run"
    wd.mkdir(parents=True, exist_ok=True)
    with _no_bus_url_no_clone():
        res = worker.run_gdelt_fetch(job, wd)
    check("run: returns ok", res == {"gdelt-fetch": "ok"})
    # manifest fields sidecar
    gf = wd / "gdelt" / "gdelt_fetch.json"
    check("run: sidecar exists", gf.exists())
    data = json.loads(gf.read_text())
    check("run: sidecar mode fixtures", data.get("mode") == "fixtures")
    check("run: sidecar files_done 0", data.get("files_done") == 0)
    check("run: sidecar matches 0", data.get("matches") == 0)

def test_bad_job():
    job = {"id": "test-gdelt-bad", "job": "gdelt-fetch --garbage"}
    wd = worker.OUT / "test-gdelt-bad"
    wd.mkdir(parents=True, exist_ok=True)
    res = worker.run_gdelt_fetch(job, wd)
    check("bad job: returns bad-job", res == {"gdelt-fetch": "bad-job"})

def test_live_argv_no_duplicate():
    # No-network proof that the live-mode argv builds the filter command
    # with the script path exactly once and --master/--master-translation
    # exactly once each. sh is monkeypatched (the filter never runs), and
    # urlopen is monkeypatched to serve the two master lists from memory.
    orig_sh, orig_urlopen = worker.sh_group, worker.urlopen
    captured = {}
    class _FakeResult:
        returncode = 0
        stdout = ""
        stderr = ""
    def fake_sh(cmd, cwd=None, env=None, timeout=3600):
        captured["cmd"] = cmd
        return _FakeResult()
    class _FakeResp:
        def __init__(self, data):
            import io; self._f = io.BytesIO(data)
        def read(self, n=-1): return self._f.read(n)
        def __enter__(self): return self
        def __exit__(self, *a): return False
    master_bytes = (b"100 d41d8cd98f00b204e9800998ecf8427e "
                    b"https://data.gdeltproject.org/gdeltv2/20240501000000.gkg.csv.zip\n"
                    b"200 d41d8cd98f00b204e9800998ecf8427e "
                    b"https://data.gdeltproject.org/gdeltv2/20240502000000.gkg.csv.zip\n")
    worker.sh_group = fake_sh
    worker.urlopen = lambda req, timeout=300: _FakeResp(master_bytes)
    try:
        job = {"id": "test-gdelt-live-argv",
               "job": "gdelt-fetch --start 20240501000000 --end 20240531235959"}
        wd = worker.OUT / "test-gdelt-live-argv"
        wd.mkdir(parents=True, exist_ok=True)
        with _no_bus_url_no_clone():
            res = worker.run_gdelt_fetch(job, wd)
        check("live argv: returns ok", res == {"gdelt-fetch": "ok"})
        cmd_str = captured.get("cmd", "")
        tokens = shlex.split(cmd_str)
        script_name = str(worker.CODE / "scripts" / "gdelt_gkg_filter.py")
        check("live argv: script path exactly once", tokens.count(script_name) == 1)
        check("live argv: --master exactly once", tokens.count("--master") == 1)
        check("live argv: --master-translation exactly once",
              tokens.count("--master-translation") == 1)
    finally:
        worker.sh_group = orig_sh
        worker.urlopen = orig_urlopen

# ---- INS-FIX-959 additions --------------------------------------------
import subprocess as _sp

class _Res:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err

def _tok(cmd, flag):
    t = shlex.split(cmd)
    return t[t.index(flag) + 1]

_REMOTE = {}
def _git(*a, cwd=None):
    r = _sp.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a],
                cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, (a, r.stderr)
    return r.stdout

def _ensure_remote():
    """ROOT/archive-push is a clone of a bare remote whose branch is 'archive'."""
    if _REMOTE:
        return
    base = Path(tempfile.mkdtemp(prefix="gdelt-remote-"))
    bare, seed = base / "bare.git", base / "seed"
    _git("init", "--bare", "-b", "archive", str(bare))
    _git("init", "-b", "archive", str(seed))
    (seed / "README").write_text("archive\n")
    _git("add", "-A", cwd=seed); _git("commit", "-m", "seed", cwd=seed)
    _git("push", str(bare), "archive:archive", cwd=seed)
    arch = worker.ROOT / "archive-push"
    if arch.exists():
        _sh.rmtree(arch)
    _git("clone", "--branch", "archive", str(bare), str(arch))
    _REMOTE.update(bare=bare, arch=arch)

def _make_archive_run(date, hms, slug_tail, jobid, done_lines, with_state=True,
                      published=True, matches=None, macro=None, config=None,
                      extra_state=None, mode="fixtures", window=None):
    """Create worker-runs/DATE/HMS__slug__jobid in the local checkout.
    published=True commits and pushes it to the remote archive branch;
    published=False leaves it as local residue (a failed publish)."""
    _ensure_remote()
    if window is None:
        # 959n F8: restore refuses a checkpoint that does not establish the
        # job window; default to the FIXJOB window (a legacy run with no
        # sidecar gets it through a bound config instead).
        window = ("20240501000000", "20240501000000")
        c0 = (config or {}).get("config.json") or {}
        if "start" in c0 and "end" in c0:
            window = (c0["start"], c0["end"])   # the checkpoint's own bounds
        if mode is None and config is None:
            config = {"config.json": {"start": window[0], "end": window[1]}}
    d = worker.ROOT / "archive-push" / "worker-runs" / date / ("%s__%s__%s" % (hms, slug_tail, jobid))
    (d / "gdelt").mkdir(parents=True, exist_ok=True)
    if with_state:
        (d / "gdelt-state").mkdir(parents=True, exist_ok=True)
        (d / "gdelt-state" / "done.txt").write_text(done_lines)
        if config is not None:
            for k, v in config.items():
                (d / "gdelt-state" / k).write_text(json.dumps(v))
        for k, v in (extra_state or {}).items():
            (d / "gdelt-state" / k).write_text(v)
    if matches is not None:
        (d / "gdelt" / "matches.jsonl").write_text(matches)
    if macro is not None:
        (d / "gdelt" / "macro_matches.jsonl").write_text(macro)
    (d / "gdelt" / "keep").write_text("x")
    if mode is not None:   # the sidecar every real run writes; None = a legacy run without it
        side = {"mode": mode}
        if window is not None:
            side["start"], side["end"] = window
        (d / "gdelt" / "gdelt_fetch.json").write_text(json.dumps(side))
    if published:
        arch = worker.ROOT / "archive-push"
        _git("add", "-A", str(d), cwd=arch)
        _git("commit", "-m", "run " + d.name, cwd=arch)
        _git("push", "origin", "HEAD:archive", cwd=arch)
    return d

def _run_capture(job, wd, runner):
    """Run run_gdelt_fetch with sh_group replaced by `runner(cmd)`."""
    orig = worker.sh_group
    seen = {}
    def fake(cmd, cwd=None, env=None, timeout=3600):
        seen["cmd"] = cmd
        seen["state_done"] = (Path(_tok(cmd, "--state")) / "done.txt")
        seen["state_text"] = seen["state_done"].read_text() if seen["state_done"].exists() else None
        return runner(cmd)
    worker.sh_group = fake
    try:
        wd.mkdir(parents=True, exist_ok=True)
        res = worker.run_gdelt_fetch(job, wd)
    finally:
        worker.sh_group = orig
    return res, seen

FX = None
def _fixtures_env():
    fx = Path(tempfile.mkdtemp())
    (fx / "masterfilelist.txt").write_text("")
    (fx / "masterfilelist-translation.txt").write_text("")
    os.environ["GDELT_FIXTURE_MASTER_DIR"] = str(fx)

def test_parse_resume_key():
    base = "gdelt-fetch --start 20240501000000 --end 20240531235959 "
    p = worker.parse_gdelt_fetch_job(base + "--resume-from job-12_ab.3")
    check("parse: resume-from accepted", p is not None and p["resume_from"] == "job-12_ab.3")
    check("parse: resume-from default None", worker.parse_gdelt_fetch_job(base)["resume_from"] is None)
    for bad in ("--resume-from", "--resume-from ../x", "--resume-from a/b", "--resume-from -x",
                "--resume-from a;b", "--resume-from " + "a" * 129):
        check("parse: rejects %r" % bad, worker.parse_gdelt_fetch_job(base + bad) is None)

def test_restore_from_dated_dirs():
    _fixtures_env()
    jid = "restore-own-1"
    # slug ends in the last job argument, as publish() builds it
    _make_archive_run("2026-11-26", "100000", "gdelt-fetch-start-20240501000000-end-20240531235959", jid, "OLD\n")
    _make_archive_run("2026-11-27", "090000", "gdelt-fetch-start-20240501000000-end-20240531235959", jid, "NEW\n")
    _make_archive_run("2026-11-27", "090000", "x", "restore-other", "OTHER\n")
    _make_archive_run("2026-11-28", "090000", "x", jid, "", with_state=False)  # newest run without state is skipped
    job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    res, seen = _run_capture(job, worker.OUT / "t959-restore", lambda c: _Res())
    check("restore: dated dirs found, latest run with state used", seen["state_text"] == "NEW\n")
    check("restore: other job id not restored", "OTHER" not in (seen["state_text"] or ""))
    # a name that merely ends with the id text is not a match
    _make_archive_run("2026-11-29", "090000", "x", "zz" + jid, "SUFFIX\n")
    res, seen = _run_capture(job, worker.OUT / "t959-restore2", lambda c: _Res())
    check("restore: only the exact __<jobid> suffix matches", seen["state_text"] == "NEW\n")

def test_resume_key_predecessor_and_requeue():
    _fixtures_env()
    _make_archive_run("2026-11-26", "100000", "x", "pred-A", "PRED-OLD\n")
    _make_archive_run("2026-11-27", "100000", "x", "pred-A", "PRED-NEW\n")
    _make_archive_run("2026-11-28", "100000", "x", "succ-B", "OWN\n")
    job = {"id": "succ-B", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures --resume-from pred-A"}
    res, seen = _run_capture(job, worker.OUT / "t959-pred", lambda c: _Res())
    check("same-id retry restores its OWN published run over the predecessor", seen["state_text"] == "OWN\n")
    jobc = {"id": "succ-C", "job": job["job"]}
    res, seen = _run_capture(jobc, worker.OUT / "t959-predc", lambda c: _Res())
    check("no own published run: falls back to the predecessor's latest run", seen["state_text"] == "PRED-NEW\n")
    job2 = {"id": "succ-B", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    res, seen = _run_capture(job2, worker.OUT / "t959-requeue", lambda c: _Res())
    check("same-id re-queue resumes from its own published partial run", seen["state_text"] == "OWN\n")
    # no prior state anywhere: starts fresh
    job3 = {"id": "never-ran", "job": job2["job"]}
    res, seen = _run_capture(job3, worker.OUT / "t959-fresh", lambda c: _Res())
    check("no predecessor: fresh state", seen["state_text"] is None)

def test_budget_run_not_queue_done_and_complete_is_done():
    done_calls, pub_calls, rets = [], [], {}
    o_pub, o_md, o_run = worker.publish, worker._mark_done, worker.run_gdelt_fetch
    worker.publish = lambda job, wd, m: pub_calls.append(job["id"]) or "sha123"
    worker._mark_done = lambda job, sha, extra=None: done_calls.append(job["id"])
    try:
        for status, jid in (("budget-exhausted", "q-budget"), ("timeout", "q-timeout"), ("ok", "q-ok"), ("refused", "q-exit"),
                            ("unfinished", "q-unf"), ("master-download-failed", "q-mdf")):
            worker.run_gdelt_fetch = lambda job, wd, st=status: {"gdelt-fetch": st}
            job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
            rets[jid] = worker._execute(job)
        check("budget-limited run archived", "q-budget" in pub_calls and "q-timeout" in pub_calls)
        check("budget-limited run NOT marked queue-done", "q-budget" not in done_calls)
        check("timed-out run NOT marked queue-done", "q-timeout" not in done_calls)
        check("incomplete statuses signal execute() to release the claim",
              all(rets[j] == "incomplete" for j in ("q-budget", "q-timeout", "q-unf", "q-mdf")))
        check("finished and failed-exit runs do not signal a release", rets["q-ok"] is None and rets["q-exit"] is None)
        check("unfinished run NOT marked queue-done", "q-unf" not in done_calls)
        check("master-download-failed (transient) NOT marked queue-done", "q-mdf" not in done_calls)
        check("completed fetch is marked done", "q-ok" in done_calls)
        check("failed-exit run keeps the old done-after-publish behaviour", "q-exit" in done_calls)
        check("incomplete run releases its intent so a same-id re-queue is admitted",
              not worker._intent_path("q-budget").exists() and not worker._intent_path("q-timeout").exists())
        check("no intent leaked for a pending-free job", not worker._done_or_pending("q-budget"))
    finally:
        worker.publish, worker._mark_done, worker.run_gdelt_fetch = o_pub, o_md, o_run

def test_budget_status_from_filter_output():
    _fixtures_env()
    job = {"id": "bud-1", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures --budget-seconds 5"}
    res, _ = _run_capture(job, worker.OUT / "t959-bud", lambda c: _Res(0, "x\nbudget exhausted; rerun to resume\n"))
    check("budget exhausted output gives status budget-exhausted", res == {"gdelt-fetch": "budget-exhausted"})
    data = json.loads((worker.OUT / "t959-bud" / "gdelt" / "gdelt_fetch.json").read_text())
    check("sidecar carries the status", data["status"] == "budget-exhausted")

def test_master_lists_excluded_from_publish_copy():
    class _FR:
        def __init__(self, d):
            import io; self._f = io.BytesIO(d)
        def read(self, n=-1): return self._f.read(n)
        def __enter__(self): return self
        def __exit__(self, *a): return False
    o_url = worker.urlopen
    worker.urlopen = lambda req, timeout=300: _FR(b"1 d41d8cd98f00b204e9800998ecf8427e https://data.gdeltproject.org/gdeltv2/20240501000000.gkg.csv.zip\n")
    try:
        job = {"id": "master-1", "job": "gdelt-fetch --start 20240501000000 --end 20240531235959"}
        wd = worker.OUT / "t959-master"
        res, seen = _run_capture(job, wd, lambda c: _Res())
        mpath = Path(_tok(seen["cmd"], "--master"))
        check("master list not under workdir", not any("masterfilelist" in str(p) for p in wd.rglob("*")))
        check("master list path is outside workdir", wd not in mpath.parents)
        check("master temp dir removed after a successful run", not mpath.exists() and not mpath.parent.exists())
        def boom(req, timeout=300):
            raise OSError("down")
        worker.urlopen = boom
        wd2 = worker.OUT / "t959-master-fail"
        wd2.mkdir(parents=True, exist_ok=True)
        before = set(Path(tempfile.gettempdir()).glob("gdelt-master-*"))
        res = worker.run_gdelt_fetch({"id": "master-2", "job": job["job"]}, wd2)
        check("download failure status", res == {"gdelt-fetch": "master-download-failed"})
        check("no master list under workdir on the failure path", not any("masterfilelist" in str(p) for p in wd2.rglob("*")))
        check("no leaked master temp dir on the failure path",
              set(Path(tempfile.gettempdir()).glob("gdelt-master-*")) <= before)
    finally:
        worker.urlopen = o_url

def test_timeout_archives_partial_output():
    _fixtures_env()
    job = {"id": "to-1", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    def runner(cmd):
        out = Path(_tok(cmd, "--out"))
        (out / "matches.jsonl").write_text('{"a": 1}\n{"a": 2}\n')
        (Path(_tok(cmd, "--state")) / "done.txt").write_text("f1\nf2\nf3\n")
        raise _sp.TimeoutExpired(cmd, 7200, output=b"partial-out", stderr="partial-err")
    wd = worker.OUT / "t959-timeout"
    res, _ = _run_capture(job, wd, runner)
    check("timeout: named status", res == {"gdelt-fetch": "timeout"})
    check("timeout: partial matches copied", (wd / "gdelt" / "matches.jsonl").read_text() == '{"a": 1}\n{"a": 2}\n')
    data = json.loads((wd / "gdelt" / "gdelt_fetch.json").read_text())
    check("timeout: sidecar written with counts and status",
          data["status"] == "timeout" and data["files_done"] == 3 and data["matches"] == 2)
    check("timeout: state summary written", (wd / "gdelt" / "gdelt-state-summary.json").exists())
    log = (wd / "gdelt" / "gdelt-fetch.log").read_text()
    check("timeout: log names the status and carries the output tail", "status=timeout" in log and "partial-out" in log and "partial-err" in log)
    check("timeout: group-kill helper is the one used", "sh_group" in worker.run_gdelt_fetch.__globals__
          and "sh_group(" in Path(worker.__file__).read_text().split("def _run_gdelt_fetch", 1)[1].split("(d) Copy", 1)[0])

def test_nonzero_exit_log_tail_bounded():
    _fixtures_env()
    job = {"id": "tail-1", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    big = "A" * 6000 + "TAILMARK"
    res, _ = _run_capture(job, worker.OUT / "t959-tail", lambda c: _Res(3, big, "ERRMARK"))
    check("nonzero exit status is the retryable unexpected-exit", res == {"gdelt-fetch": "unexpected-exit-3"})
    log = (worker.OUT / "t959-tail" / "gdelt" / "gdelt-fetch.log").read_text()
    tail = log.split("--- filter output tail (max 4000 chars) ---\n", 1)[1].rstrip("\n")
    check("log tail contains the end of stdout+stderr", tail.endswith("ERRMARK") and "TAILMARK" in tail)
    check("log tail is bounded to 4000 chars", len(tail) == 4000)
    ok_wd = worker.OUT / "t959-tail-ok"
    res, _ = _run_capture(job, ok_wd, lambda c: _Res(0, big, ""))
    check("successful run has no output tail in the log", "filter output tail" not in (ok_wd / "gdelt" / "gdelt-fetch.log").read_text())

def test_restore_ignores_unpublished_local_residue():
    _fixtures_env()
    jid = "resid-1"
    _make_archive_run("2026-11-26", "100000", "x", jid, "PUBLISHED\n")
    _make_archive_run("2026-11-27", "100000", "x", jid, "RESIDUE\n", published=False)
    job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    res, seen = _run_capture(job, worker.OUT / "t959-resid", lambda c: _Res())
    check("restore ignores unpublished local residue (newer, local only)", seen["state_text"] == "PUBLISHED\n")
    # a locally committed but never pushed run is residue too
    arch = worker.ROOT / "archive-push"
    d = _make_archive_run("2026-11-28", "100000", "x", jid, "COMMITTED-NOT-PUSHED\n", published=False)
    _git("add", "-A", str(d), cwd=arch); _git("commit", "-m", "local only", cwd=arch)
    res, seen = _run_capture(job, worker.OUT / "t959-resid2", lambda c: _Res())
    check("restore ignores a local commit that was never pushed", seen["state_text"] == "PUBLISHED\n")
    # a job whose only run is residue starts fresh
    _make_archive_run("2026-11-28", "110000", "x", "resid-only", "R\n", published=False)
    res, seen = _run_capture({"id": "resid-only", "job": job["job"]}, worker.OUT / "t959-resid3", lambda c: _Res())
    check("only-residue job starts fresh", seen["state_text"] is None)

def test_restore_brings_back_predecessor_matches():
    _fixtures_env()
    jid = "matches-1"
    # 959m F4: real config hashes (what the filter computes), f1 done in BOTH channels,
    # and the REAL filter is run against the restored checkpoint.
    import hashlib
    ash = hashlib.sha256((worker.CODE / "evaluation" / "gdelt_alias_table.csv").read_bytes()).hexdigest()
    tsh = hashlib.sha256((worker.CODE / "evaluation" / "gdelt_macro_themes.csv").read_bytes()).hexdigest()
    cfg = {"config.json": {"aliases_sha256": ash, "start": "20240501000000", "end": "20240501999999", "out": "/old/place/gdelt-out"},
           "macro_config.json": {"themes_sha256": tsh, "start": "20240501000000", "end": "20240501999999", "out": "/old/place/gdelt-out"}}
    co_old = '{"file": "f1", "company": "OLD"}\n'
    ma_old = '{"file": "f1", "theme": "OLDMACRO"}\n'
    _make_archive_run("2026-11-27", "100000", "x", jid, "f1\n", matches=co_old, macro=ma_old, config=cfg, extra_state={"macro_done.txt": "f1\n"},
                      window=("20240501000000", "20240501999999"))
    job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999 --mode fixtures"}
    real_sh = worker.sh_group
    real_out = {}
    def runner(cmd):
        out = Path(_tok(cmd, "--out"))
        # the real filter first: it validates the restored config hashes and reconciles orphan rows
        # 959n F4: the production launch env (sh_group refuses GATOR_BUS_URL).
        real_out["bus_url_in_parent_env"] = "GATOR_BUS_URL" in os.environ
        r = real_sh(cmd, cwd=str(worker.CODE), timeout=90,
                    env={k: v for k, v in os.environ.items()
                         if k not in worker.ENV_DENY_FOR_TOOLS})
        real_out["rc"] = r.returncode
        real_out["co"] = (out / "matches.jsonl").read_text() if (out / "matches.jsonl").exists() else None
        real_out["ma"] = (out / "macro_matches.jsonl").read_text() if (out / "macro_matches.jsonl").exists() else None
        with open(out / "matches.jsonl", "a") as f:
            f.write('{"file": "f2", "company": "NEW"}\n')
        with open(out / "macro_matches.jsonl", "a") as f:
            f.write('{"file": "f2", "theme": "NEWMACRO"}\n')
        return _Res()
    wd = worker.OUT / "t959-matches"
    res, seen = _run_capture(job, wd, runner)
    check("959n F4 (carried nit): the parent env had no GATOR_BUS_URL when the launch env was built",
          real_out.get("bus_url_in_parent_env") is False, str(real_out))
    check("959m F4: the real filter accepted the restored checkpoint and kept both old rows", real_out.get("rc") == 0
          and real_out.get("co") == co_old and real_out.get("ma") == ma_old, str(real_out))
    pub = (wd / "gdelt" / "matches.jsonl").read_text()
    pubm = (wd / "gdelt" / "macro_matches.jsonl").read_text()
    check("published company matches include the predecessor's for done files", pub == co_old + '{"file": "f2", "company": "NEW"}\n')
    check("published macro matches include the predecessor's for done files", pubm == ma_old + '{"file": "f2", "theme": "NEWMACRO"}\n')
    out_abs = os.path.abspath(str(wd / "gdelt-out"))
    c1 = json.loads((wd / "gdelt-state" / "config.json").read_text())
    c2 = json.loads((wd / "gdelt-state" / "macro_config.json").read_text())
    check("restored config re-pointed at this out dir", c1["out"] == out_abs and c2["out"] == out_abs)
    check("restored config keeps its hash and window", c1["aliases_sha256"] == ash and c1["end"] == "20240501999999" and c2["themes_sha256"] == tsh)
    check("matches restored with the state, summary counts them", json.loads((wd / "gdelt" / "gdelt-state-summary.json").read_text())["matches"] == 2)
    # no predecessor: no matches appear from nowhere
    wd2 = worker.OUT / "t959-matches-fresh"
    res, seen = _run_capture({"id": "matches-none", "job": job["job"]}, wd2, lambda c: _Res())
    check("fresh run restores no matches", not (wd2 / "gdelt-out" / "matches.jsonl").exists())

def test_restore_brings_back_absent_state():
    _fixtures_env()
    jid = "absent-1"
    ab = "20240501001500.gkg.csv.zip\n20240501003000.gkg.csv.zip\n"
    _make_archive_run("2026-11-27", "100000", "x", jid, "f1\n", extra_state={"absent.txt": ab}, window=W999)
    job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999 --mode fixtures"}
    res, seen = _run_capture(job, worker.OUT / "t959-absent", lambda c: _Res())
    got = worker.OUT / "t959-absent" / "gdelt-state" / "absent.txt"
    check("absent.txt restored with the predecessor's state", got.exists() and got.read_text() == ab)
    check("done.txt still restored", seen["state_text"] == "f1\n")
    # a predecessor without absent.txt restores none (no file appears from nowhere)
    _make_archive_run("2026-11-27", "110000", "x", "absent-2", "f1\n", window=W999)
    res, seen = _run_capture({"id": "absent-2", "job": job["job"]}, worker.OUT / "t959-absent2", lambda c: _Res())
    check("no absent.txt invented when the predecessor had none",
          not (worker.OUT / "t959-absent2" / "gdelt-state" / "absent.txt").exists())

def test_master_download_failed_publishes_restored_matches():
    _fixtures_env()
    jid = "mdf-1"
    cfg = {"config.json": {"aliases_sha256": "abc", "start": "20240501000000", "end": "20240501999999", "out": "/old/out"}}
    _make_archive_run("2026-11-27", "100000", "x", jid, "f1\n", matches='{"file": "f1", "company": "OLD"}\n',
                      macro='{"file": "f1", "theme": "OLDMACRO"}\n', config=cfg, mode="live")
    def boom(req, timeout=300):
        raise OSError("network down")
    o_url = worker.urlopen
    worker.urlopen = boom
    try:
        job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999"}
        wd = worker.OUT / "t959-mdf"
        wd.mkdir(parents=True, exist_ok=True)
        res = worker.run_gdelt_fetch(job, wd)
    finally:
        worker.urlopen = o_url
    check("master download failure keeps its failure status", res == {"gdelt-fetch": "master-download-failed"})
    check("master-download-failed is incomplete (not queue-done)", "master-download-failed" in worker.GDELT_INCOMPLETE)
    check("restored company matches published on the failure path",
          (wd / "gdelt" / "matches.jsonl").read_text() == '{"file": "f1", "company": "OLD"}\n')
    check("restored macro matches published on the failure path",
          (wd / "gdelt" / "macro_matches.jsonl").read_text() == '{"file": "f1", "theme": "OLDMACRO"}\n')

def test_unfinished_status_from_filter_output():
    _fixtures_env()
    job = {"id": "unf-1", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    res, _ = _run_capture(job, worker.OUT / "t959-unf", lambda c: _Res(0, "skip a.zip: URLError: x\ngkg-filter-status unfinished=2 absent=0\n"))
    check("unfinished files give status unfinished", res == {"gdelt-fetch": "unfinished"})
    job2 = {"id": "unf-2", "job": job["job"]}
    res, _ = _run_capture(job2, worker.OUT / "t959-abs", lambda c: _Res(0, "absent b.zip: HTTP Error 404\ngkg-filter-status unfinished=0 absent=3\n"))
    check("absent (404) files alone stay ok", res == {"gdelt-fetch": "ok"})
    res, _ = _run_capture({"id": "unf-4", "job": job["job"]}, worker.OUT / "t959-two", lambda c: _Res(0, "gkg-filter-status unfinished=0 absent=0\nx\ngkg-filter-status unfinished=4 absent=1\n"))
    check("the LAST status line is the one used", res == {"gdelt-fetch": "unfinished"})
    res, _ = _run_capture({"id": "unf-3", "job": job["job"]}, worker.OUT / "t959-old", lambda c: _Res(0, "chunk done\n"))
    check("older filter without a status line stays ok", res == {"gdelt-fetch": "ok"})
    log = (worker.OUT / "t959-unf" / "gdelt" / "gdelt-fetch.log").read_text()
    check("unfinished run keeps the skip diagnostics in the log", "skip a.zip: URLError" in log)

def test_execute_releases_bus_claim_for_incomplete_run():
    """execute() level: an incomplete run stops the refresh thread and the
    bus claim is gone from origin/queue; a finished run keeps its claim."""
    base = Path(tempfile.mkdtemp(prefix="gdelt-bus-"))
    bare, seed = base / "bare.git", base / "seed"
    _git("init", "--bare", "-b", "queue", str(bare))
    _git("init", "-b", "queue", str(seed))
    (seed / "queue" / "claims").mkdir(parents=True)
    for jid in ("inc-1", "fin-1"):
        (seed / "queue" / "claims" / (jid + ".json")).write_text('{"worker": "w"}')
    _git("add", "-A", cwd=seed); _git("commit", "-m", "seed", cwd=seed)
    _git("push", str(bare), "queue:queue", cwd=seed)
    bus = base / "bus"
    _git("clone", "--branch", "queue", str(bare), str(bus))
    _git("config", "user.name", "t", cwd=bus); _git("config", "user.email", "t@example.invalid", cwd=bus)
    o_bus, o_exec, o_sec = worker.BUS, worker._execute, worker.CLAIM_REFRESH_SECONDS
    import threading
    worker.BUS = bus
    worker.CLAIM_REFRESH_SECONDS = 3600
    seen = {}
    def _refresh_threads():
        return [t for t in threading.enumerate() if getattr(t, "_target", None) is not None
                and t._target.__name__ == "refresh" and t.is_alive()]
    def fake_exec(job):
        seen.setdefault("running", {})[job["id"]] = list(_refresh_threads())
        seen["refresh_threads_running"] = sum(1 for t in threading.enumerate() if t.daemon and t.is_alive())
        return "incomplete" if job["id"] == "inc-1" else None
    worker._execute = fake_exec
    try:
        worker.execute({"id": "inc-1", "job": "gdelt-fetch"})
        # checked immediately after the incomplete execution returns, before the finished one starts
        inc_threads = seen["running"]["inc-1"]
        inc_stopped = bool(inc_threads) and all(not t.is_alive() for t in inc_threads)
        worker.execute({"id": "fin-1", "job": "gdelt-fetch"})
    finally:
        worker.BUS, worker._execute, worker.CLAIM_REFRESH_SECONDS = o_bus, o_exec, o_sec
    ls = _git("ls-tree", "-r", "--name-only", "queue", cwd=bare)
    check("incomplete run's bus claim removed from origin/queue", "queue/claims/inc-1.json" not in ls)
    check("finished run keeps the existing completion path (claim untouched here)", "queue/claims/fin-1.json" in ls)
    check("incomplete run's own refresh thread was captured and stopped right after it returned", inc_stopped)
    check("the refresh thread was running while the job executed", seen["refresh_threads_running"] >= 1)

def test_timeout_with_truncated_utf8_record():
    _fixtures_env()
    job = {"id": "to-utf8", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    def runner(cmd):
        out = Path(_tok(cmd, "--out"))
        (out / "matches.jsonl").write_bytes(b'{"a": 1}\n{"a": "\xd8')   # cut inside a 2-byte character
        (out / "macro_matches.jsonl").write_bytes(b'{"m": "\xe2\x82')   # cut inside a 3-byte character
        raise _sp.TimeoutExpired(cmd, 7200, output=b"", stderr="")
    wd = worker.OUT / "t959-utf8"
    res, _ = _run_capture(job, wd, runner)
    check("truncated multibyte record does not stop the timeout status", res == {"gdelt-fetch": "timeout"})
    data = json.loads((wd / "gdelt" / "gdelt_fetch.json").read_text())
    check("line counts are byte-based (2 company lines, 1 macro line)", data["matches"] == 2 and data["macro_matches"] == 1)

def _progress_run(jid, files_done, status="budget-exhausted", absent=None, transient=None, pubs=None, mark_done=None):
    """One incomplete run through _execute with the fetch and publish stubbed."""
    o_pub, o_md, o_run = worker.publish, worker._mark_done, worker.run_gdelt_fetch
    def fake_run(job, wd):
        g = Path(wd) / "gdelt"; g.mkdir(parents=True, exist_ok=True)
        side = {"files_done": files_done, "macro_files_done": 0}
        if absent is not None:
            side["absent_files"] = absent
        if transient is not None:
            side["transient_files"] = transient
        (g / "gdelt_fetch.json").write_text(json.dumps(side))
        return {"gdelt-fetch": status}
    worker.publish = lambda job, wd, m: (pubs.append(jid) if pubs is not None else None) or "sha"
    # A caller-owned spy stays ACTIVE during the run (a wrong _mark_done call
    # must be visible to it); the default stays a no-op.
    worker._mark_done = mark_done if mark_done is not None else (lambda job, sha, extra=None: None)
    worker.run_gdelt_fetch = fake_run
    try:
        job = {"id": jid, "job": "gdelt-fetch --start 20200101000000 --end 20200131235959 --mode fixtures"}
        return worker._execute(job)
    finally:
        worker.publish, worker._mark_done, worker.run_gdelt_fetch = o_pub, o_md, o_run

def test_stuck_incomplete_job_yields_the_lane():
    jid = "stuck-1"
    worker._gdelt_progress_clear(jid)
    _progress_run(jid, 5)                      # first run: 5 files, progress
    check("first incomplete run with progress is not deferred", not worker._gdelt_deferred(jid))
    for i in range(worker.GDELT_STALL_LIMIT - 1):
        worker._intent_path(jid).unlink(missing_ok=True)
        _progress_run(jid, 5)
        check("stall %d below the limit: not yet deferred" % (i + 1), not worker._gdelt_deferred(jid))
    worker._intent_path(jid).unlink(missing_ok=True)
    _progress_run(jid, 5)
    check("after GDELT_STALL_LIMIT stalls the job is deferred", worker._gdelt_deferred(jid))
    rec = worker._gdelt_progress_read(jid)
    check("deferral lasts GDELT_DEFER_SECONDS",
          abs(rec["deferred_until"] - (time.time() + worker.GDELT_DEFER_SECONDS)) < 60)
    check("deferral expires", not worker._gdelt_deferred(jid, now_ts=time.time() + worker.GDELT_DEFER_SECONDS + 5))
    check("a later job is not deferred", not worker._gdelt_deferred("other-job"))
    src = Path(worker.__file__).read_text()
    m = src[src.index("def main():"):]
    check("main() skips a deferred job after the supersede handling and before claiming",
          m.index("_superseded_slot(") < m.index("if _gdelt_deferred(job_id):") < m.index("if not claimed(job_id):"))
    check("supersede handling for guard/watchdog slots is still present",
          '"ledger-guard"' in m and "_mark_superseded(" in m)
    worker._gdelt_progress_clear(jid)

def test_progressing_incomplete_job_resumes_and_is_not_demoted():
    jid = "prog-1"
    worker._gdelt_progress_clear(jid)
    total = 0
    for n in range(8):                          # 8 budget-limited runs, +71 files each
        worker._intent_path(jid).unlink(missing_ok=True)
        total += 71
        r = _progress_run(jid, total)
        check("progressing run %d signals a resume release" % (n + 1), r == "incomplete")
        check("progressing run %d is not deferred" % (n + 1), not worker._gdelt_deferred(jid))
    check("stalls stay at zero while progressing", worker._gdelt_progress_read(jid)["stalls"] == 0)
    # a stall run then a progress run resets the counter
    for _ in range(worker.GDELT_STALL_LIMIT - 1):
        worker._intent_path(jid).unlink(missing_ok=True); _progress_run(jid, total)
    worker._intent_path(jid).unlink(missing_ok=True); _progress_run(jid, total + 71)
    check("a run that advances resets the stalls", worker._gdelt_progress_read(jid)["stalls"] == 0 and not worker._gdelt_deferred(jid))
    # restore flow unchanged: own id first (covered by the restore tests); a completed job clears its record
    worker._intent_path(jid).unlink(missing_ok=True)
    _progress_run(jid, total + 142, status="ok")
    check("a completed run clears the progress record", worker._gdelt_progress_read(jid) is None)

def test_progress_total_never_decreases():
    jid = "mono-1"
    worker._gdelt_progress_clear(jid)
    worker._gdelt_note_incomplete(jid, 100)
    check("first 100-file run recorded as progress", worker._gdelt_progress_read(jid) == {"total": 100, "stalls": 0, "deferred_until": 0})
    r = worker._gdelt_note_incomplete(jid, 0)          # e.g. a failure path reporting 0
    check("a lower total does not lower the stored total", r["total"] == 100)
    check("a lower total counts as a stall", r["stalls"] == 1)
    r = worker._gdelt_note_incomplete(jid, 100)        # repeat of the same 100
    check("a repeated 100-file total after the 0 run is a stall, not progress", r["stalls"] == 2 and r["total"] == 100)
    r = worker._gdelt_note_incomplete(jid, 100)
    check("repeated stalls reach the limit and defer", r["stalls"] == 3 and r["deferred_until"] > time.time())
    worker._gdelt_progress_clear(jid)
    worker._gdelt_note_incomplete(jid, 100)
    worker._gdelt_note_incomplete(jid, 100)
    r = worker._gdelt_note_incomplete(jid, 120)
    check("a genuinely higher total (120) resets stalls to 0 and raises the total", r["stalls"] == 0 and r["total"] == 120)
    worker._gdelt_progress_clear(jid)

def test_download_failure_reports_restored_progress():
    _fixtures_env()
    jid = "mdf-prog"
    done = "".join("f%d\n" % i for i in range(100))
    mdone = "".join("m%d\n" % i for i in range(7))
    d = _make_archive_run("2026-11-27", "100000", "x", jid, done,
                          matches='{"c": 1}\n{"c": 2}\n', macro='{"m": 1}\n',
                          config={"config.json": {"aliases_sha256": "a", "start": "20240501000000", "end": "20240501999999", "out": "/o"}}, mode="live")
    (d / "gdelt-state" / "macro_done.txt").write_text(mdone)
    _git("add", "-A", str(d), cwd=worker.ROOT / "archive-push"); _git("commit", "-m", "macro done", cwd=worker.ROOT / "archive-push")
    _git("push", "origin", "HEAD:archive", cwd=worker.ROOT / "archive-push")
    def boom(req, timeout=300):
        raise OSError("down")
    o_url = worker.urlopen; worker.urlopen = boom
    try:
        wd = worker.OUT / "t959-mdfprog"; wd.mkdir(parents=True, exist_ok=True)
        res = worker.run_gdelt_fetch({"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999"}, wd)
    finally:
        worker.urlopen = o_url
    data = json.loads((wd / "gdelt" / "gdelt_fetch.json").read_text())
    check("download failure keeps its status", res == {"gdelt-fetch": "master-download-failed"})
    check("download failure reports the restored files_done and macro_files_done, not 0",
          data["files_done"] == 100 and data["macro_files_done"] == 7)
    check("download failure reports the restored match counts", data["matches"] == 2 and data["macro_matches"] == 1)
    # end to end: a 100-file run, then this failure, then the same 100-file run is a stall, not progress
    j2 = "mono-e2e"
    worker._gdelt_progress_clear(j2)
    _progress_run(j2, 107)
    worker._intent_path(j2).unlink(missing_ok=True)
    _progress_run(j2, data["files_done"] + data["macro_files_done"], status="master-download-failed")
    worker._intent_path(j2).unlink(missing_ok=True)
    _progress_run(j2, 107)
    check("after a failure run reporting restored progress, the unchanged run is stall 2", worker._gdelt_progress_read(j2)["stalls"] == 2)
    worker._gdelt_progress_clear(j2)

def test_absent_counts_as_progress():
    jid = "abs-prog"
    worker._gdelt_progress_clear(jid)
    _progress_run(jid, 10, absent=0)
    # budget-limited all-404 runs: done and macro_done unchanged, absent grows
    for n in range(worker.GDELT_STALL_LIMIT + 1):
        worker._intent_path(jid).unlink(missing_ok=True)
        _progress_run(jid, 10, absent=40 * (n + 1))
        check("all-404 run %d (absent grows) is progress, not a stall" % (n + 1),
              worker._gdelt_progress_read(jid)["stalls"] == 0 and not worker._gdelt_deferred(jid))
    top = worker._gdelt_progress_read(jid)["total"]
    check("stored total counts done + macro_done + absent", top == 10 + 40 * (worker.GDELT_STALL_LIMIT + 1))
    # a run with no new done, macro_done or absent is still a stall
    worker._intent_path(jid).unlink(missing_ok=True)
    _progress_run(jid, 10, absent=40 * (worker.GDELT_STALL_LIMIT + 1))
    check("a run with nothing new is a stall", worker._gdelt_progress_read(jid)["stalls"] == 1)
    # older sidecar without absent_files still works (counts as 0)
    worker._intent_path(jid).unlink(missing_ok=True)
    _progress_run(jid, 10)
    check("sidecar without absent_files reads as 0 and never lowers the stored total",
          worker._gdelt_progress_read(jid)["total"] == top and worker._gdelt_progress_read(jid)["stalls"] == 2)
    for _ in range(worker.GDELT_STALL_LIMIT):
        worker._intent_path(jid).unlink(missing_ok=True)
        _progress_run(jid, 10, absent=top - 10)
    check("repeated no-new runs defer after the stall limit", worker._gdelt_deferred(jid))
    worker._gdelt_progress_clear(jid)

def test_sidecar_reports_absent_both_paths():
    _fixtures_env()
    jid = "abs-side"
    done = "".join("f%d\n" % i for i in range(5))
    d = _make_archive_run("2026-11-27", "110000", "x", jid, done,
                          matches='{"c": 1}\n', macro='{"m": 1}\n',
                          config={"config.json": {"aliases_sha256": "a", "start": "20240501000000", "end": "20240501999999", "out": "/o"}},
                          extra_state={"absent.txt": "a1\na2\n\na3\n"}, mode="live")
    def boom(req, timeout=300):
        raise OSError("down")
    o_url = worker.urlopen; worker.urlopen = boom
    try:
        wd = worker.OUT / "t959-abs-mdf"; wd.mkdir(parents=True, exist_ok=True)
        res = worker.run_gdelt_fetch({"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999"}, wd)
    finally:
        worker.urlopen = o_url
    data = json.loads((wd / "gdelt" / "gdelt_fetch.json").read_text())
    check("master-download-failed path reports the restored absent count (blank lines ignored)",
          res == {"gdelt-fetch": "master-download-failed"} and data["absent_files"] == 3)
    # normal path: filter stub persists absent identities in the state dir
    job = {"id": "abs-norm", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    def runner(cmd):
        st = Path(_tok(cmd, "--state"))
        st.mkdir(parents=True, exist_ok=True)
        (st / "absent.txt").write_text("n1\nn2\n")
        class P:
            returncode = 0; stdout = "gkg-filter-status unfinished=0 absent=2\n"; stderr = ""
        return P()
    wd2 = worker.OUT / "t959-abs-norm"
    res2, _ = _run_capture(job, wd2, runner)
    data2 = json.loads((wd2 / "gdelt" / "gdelt_fetch.json").read_text())
    check("normal path sidecar reports absent_files", data2.get("absent_files") == 2)

class _Resp:
    """Streaming fake HTTP response; records every read size."""
    reads = []
    def __init__(self, b):
        import io as _io
        self.f = _io.BytesIO(b)
    def read(self, n=-1):
        _Resp.reads.append(n)
        return self.f.read(n)
    def __enter__(self): return self
    def __exit__(self, *a): return False

def test_959j_durability_and_failures():
    import contextlib
    _fixtures_env()
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    # 1: every restored file and the binding are fsynced BEFORE the first swap rename,
    # and the parent directories are fsynced after the last one.
    _mk("j-sync", matches='{"ok": 1}\n', macro='{"m": 1}\n')
    wd = worker.OUT / "t959j-sync"
    events = []
    o_tree, o_dir, o_ren, o_fs = worker._fsync_tree, worker._fsync_dir, os.rename, os.fsync
    def tree(root):
        names = sorted(p.name for p in Path(root).rglob("*") if p.is_file())
        events.append(("tree", names))
        return o_tree(root)
    def ren(a, b, *x, **k):
        events.append(("rename", str(b)))
        return o_ren(a, b, *x, **k)
    worker._fsync_tree = tree
    worker._fsync_dir = lambda d: (events.append(("dir", str(d))), o_dir(d))[1]
    os.rename = ren
    try:
        res, seen = _run_capture({"id": "j-sync", "job": fix}, wd, lambda c: _Res())
    finally:
        worker._fsync_tree, worker._fsync_dir, os.rename = o_tree, o_dir, o_ren
    kinds = [e[0] for e in events]
    t = kinds.index("tree"); first_ren = kinds.index("rename")
    check("restored match files and the binding are fsynced before the swap",
          t < first_ren and {"matches.jsonl", "macro_matches.jsonl", worker.GDELT_BINDING, "done.txt"} <= set(events[t][1]))
    last_ren = len(kinds) - 1 - kinds[::-1].index("rename")
    after = {e[1] for e in events[last_ren + 1:] if e[0] == "dir"}
    check("the parent directories of both swapped directories are fsynced after the renames", str(wd) in after)
    # the helper really syncs every file and directory
    d = Path(tempfile.mkdtemp()); (d / "a").mkdir(); (d / "a" / "f").write_text("x"); (d / "g").write_text("y")
    n = []
    os.fsync = lambda fd: (n.append(fd), o_fs(fd))[1]
    try:
        o_tree(d)
    finally:
        os.fsync = o_fs
    check("_fsync_tree syncs 2 files and 2 directories (a, root)", len(n) == 4)
    # 2: a failing explicit --resume-from lookup after the own-ID lookup bound picked stops the run
    calls = []
    o_pick = worker._gdelt_pick_published
    def pick(arch, src, mode, strict=False, window=None):
        # 959n F5: production passes window=(start, end); without the kwarg
        # the stub raised TypeError first and the check passed vacuously.
        calls.append((src, window))
        if len(calls) == 1:
            return None
        raise RuntimeError("git failed")
    worker._gdelt_pick_published = pick
    try:
        res, seen = _run_capture({"id": "j-own", "job": fix + " --resume-from j-pred"}, worker.OUT / "t959j-pred", lambda c: _Res())
    finally:
        worker._gdelt_pick_published = o_pick
    check("959n F5: the own-ID lookup returned None, then the predecessor lookup was reached with the job window",
          calls == [("j-own", ("20240501000000", "20240501000000")), ("j-pred", ("20240501000000", "20240501000000"))], str(calls))
    check("a failing predecessor lookup is an unknown resume state: nothing runs", res == {"gdelt-fetch": "archive-check-failed"} and "cmd" not in seen)
    # 3: empty or invalid live master lists
    for body, label in ((b"", "empty"), (b"\n  \n", "blank"), (b"<html>oops</html>", "html"), (b"\xff\xfe", "undecodable")):
        tf = Path(tempfile.mkdtemp()) / "m.txt"; tf.write_bytes(body)
        try:
            worker._validate_master_file(tf); ok = False
        except Exception:
            ok = True
        check("master listing %s is rejected" % label, ok)
    good = b"123 abc http://data.gdeltproject.org/gdeltv2/20240501000000.gkg.csv.zip\n"
    tf = Path(tempfile.mkdtemp()) / "m.txt"; tf.write_bytes(good)
    check("a valid listing passes", worker._validate_master_file(tf) == 1)
    livejob = "gdelt-fetch --start 20240501000000 --end 20240501000000"
    o_open = worker.urlopen
    for body, want, nran in ((b"", "master-download-failed", 0), (good, "ok", 1)):
        ran = []
        worker.urlopen = lambda req, timeout=0, _b=body: _Resp(_b)
        try:
            res, seen = _run_capture({"id": "j-live%d" % nran, "job": livejob}, worker.OUT / ("t959j-live%d" % nran), lambda c: ran.append(c) or _Res())
        finally:
            worker.urlopen = o_open
        check("live master body %r -> %s, filter launched %d time(s)" % (body[:6], want, nran), res == {"gdelt-fetch": want} and len(ran) == nran)
    # 4: checkpoint I/O failures are distinct from refusals
    for rc, out, want in ((75, "gkg-filter-checkpoint-error safe=1 OSError\n", "checkpoint-io-incomplete"),
                          (75, "gkg-filter-checkpoint-error safe=0 OSError\n", "checkpoint-io-failed"),
                          (1, "state config mismatch\ngkg-filter-refusal\n", "refused"),
                          (1, "Traceback (most recent call last):\nboom\n", "unexpected-exit-1"),
                          (137, "", "unexpected-exit-137"),
                          (-9, "", "unexpected-exit--9"),
                          (2, "usage: error\n", "unexpected-exit-2")):
        res, seen = _run_capture({"id": "j-ck%d-%s" % (rc, want), "job": fix}, worker.OUT / ("t959j-ck%d-%s" % (rc, want)), lambda c, rc=rc, out=out: _Res(rc, out))
        check("filter rc %d / %r -> %s" % (rc, out[:30], want), res == {"gdelt-fetch": want})
    check("checkpoint-io-incomplete is incomplete (archived, never queue-done); checkpoint-io-failed publishes nothing",
          "checkpoint-io-incomplete" in worker.GDELT_INCOMPLETE and "checkpoint-io-failed" in worker.GDELT_NO_PUBLISH
          and "checkpoint-io-failed" not in worker.GDELT_INCOMPLETE and "refused" not in worker.GDELT_INCOMPLETE)
    # 5: cleanup replay is bound to the intent it may remove
    jid = "j-bind"; ip = worker._intent_path(jid); ip.parent.mkdir(parents=True, exist_ok=True)
    ip.write_text('{"job": "A", "started": "t1"}')
    real_unlink = Path.unlink
    def failing(self, *a, **k):
        if self == ip:
            raise OSError("ro")
        return real_unlink(self, *a, **k)
    Path.unlink = failing
    try:
        worker._gdelt_release_intent(jid, "shaA")
    finally:
        Path.unlink = real_unlink
    mk = worker._gdelt_cleanup_marker(jid)
    check("the marker records the intent identity", json.loads(mk.read_text()).get("intent") == worker._gdelt_intent_identity(jid) is not None)
    ip.write_text('{"job": "A", "started": "t2"}')   # attempt B admitted after A's intent deletion was lost
    worker._gdelt_retry_cleanup(jid)
    check("a stale marker leaves B's intent intact and is dropped", ip.exists() and not mk.exists())
    ip.unlink(); ip.write_text('{"job": "A", "started": "t1"}')
    Path.unlink = failing
    try:
        worker._gdelt_release_intent(jid, "shaA")
    finally:
        Path.unlink = real_unlink
    o_rc = worker._release_claim
    worker._release_claim = lambda j, only_own=False, expect_attempt=False: True     # claim release has its own tests
    try:
        worker._gdelt_retry_cleanup(jid)
    finally:
        worker._release_claim = o_rc
    check("a matching marker retries A's cleanup", not ip.exists() and not mk.exists())
    # 6: repeated no-publish failures stall and defer, total never lowered, nothing published
    j6 = "j-nopub"; worker._gdelt_progress_clear(j6)
    pubs = []
    _progress_run(j6, 5, pubs=pubs); worker._intent_path(j6).unlink(missing_ok=True)
    o_pub, o_run = worker.publish, worker.run_gdelt_fetch
    worker.publish = lambda job, wd, m: pubs.append(1) or "sha"
    worker.run_gdelt_fetch = lambda job, wd: {"gdelt-fetch": "archive-check-failed"}
    rets = []
    try:
        for i in range(worker.GDELT_STALL_LIMIT):
            rets.append(worker._execute({"id": j6, "job": fix}))
            if i == 0:
                first_deferred = worker._gdelt_deferred(j6)
    finally:
        worker.publish, worker.run_gdelt_fetch = o_pub, o_run
    rec = worker._gdelt_progress_read(j6)
    check("no-publish failures publish nothing and release the claim", pubs == [pubs[0]] and rets == ["incomplete"] * worker.GDELT_STALL_LIMIT)
    check("first no-publish retry stays eligible; the stored total stays 5", first_deferred is False and rec["total"] == 5)
    check("repeated no-publish failures defer the job", worker._gdelt_deferred(j6) is True)

def test_959j_more_asks():
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    # (b) a VALID listing with no files in the requested window still succeeds
    other = b"123 abc http://data.gdeltproject.org/gdeltv2/20990101000000.gkg.csv.zip\n"
    ran = []
    o_open = worker.urlopen
    worker.urlopen = lambda req, timeout=0: _Resp(other)
    try:
        res, seen = _run_capture({"id": "j-win", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000"}, worker.OUT / "t959j-win", lambda c: ran.append(c) or _Res(0, "gkg-filter-status unfinished=0 absent=0\n"))
    finally:
        worker.urlopen = o_open
    check("a valid listing with no files in the window still succeeds (filter launched)", res == {"gdelt-fetch": "ok"} and len(ran) == 1)
    # (c) a retryable checkpoint failure is never marked done and keeps progress
    j = "j-ckprog"; worker._gdelt_progress_clear(j)
    done = []
    r = _progress_run(j, 4, status="checkpoint-io-incomplete", mark_done=lambda job, sha, extra=None: done.append(sha))
    rec = worker._gdelt_progress_read(j)
    check("checkpoint-io-incomplete: not marked done, claim released for retry, progress total kept",
          not done and r == "incomplete" and rec["total"] == 4)

def test_959k():
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    # F5: a post-swap sync failure moves the NEW state aside and restores the previous pair
    _fixtures_env()
    _mk("k-sw", matches='{"ok": 1}\n')
    wd = worker.OUT / "t959k-sw"; _local_state(wd, "LOCAL\n", binding="worker-runs/older/run")
    (wd / "gdelt-out").mkdir(parents=True, exist_ok=True)
    (wd / "gdelt-out" / "matches.jsonl").write_text('{"local": 1}\n')
    o_ren, o_dir = os.rename, worker._fsync_dir
    box = {"n": 0, "raised": False}
    def ren(a, b, *x, **k):
        box["n"] += 1
        return o_ren(a, b, *x, **k)
    def fdir(d):
        if box["n"] >= 4 and not box["raised"]:
            box["raised"] = True
            raise OSError("sync failed after the swap")
        return o_dir(d)
    os.rename, worker._fsync_dir = ren, fdir
    try:
        res, seen = _run_capture({"id": "k-sw", "job": fix}, wd, lambda c: _Res())
    finally:
        os.rename, worker._fsync_dir = o_ren, o_dir
    check("sync failure after the state install: rollback confirmed, previous pair back, run stops as unknown resume state",
          box["raised"] and res == {"gdelt-fetch": "archive-check-failed"} and "cmd" not in seen
          and (wd / "gdelt-state" / "done.txt").read_text() == "LOCAL\n"
          and (wd / "gdelt-out" / "matches.jsonl").read_text() == '{"local": 1}\n'
          and not (wd / "gdelt-state" / worker.GDELT_BINDING).read_text().count("k-sw"))
    # F5: rollback itself fails -> local reuse invalidated (no binding, no done markers)
    _mk("k-sw2", matches='{"ok": 1}\n')
    wd = worker.OUT / "t959k-sw2"; _local_state(wd, "LOCAL\n", binding="worker-runs/older/run")
    box = {"n": 0, "raised": False}
    def ren2(a, b, *x, **k):
        box["n"] += 1
        if Path(a).name == "prev-state":
            raise OSError("rollback rename failed")
        return o_ren(a, b, *x, **k)
    os.rename, worker._fsync_dir = ren2, fdir
    try:
        res, seen = _run_capture({"id": "k-sw2", "job": fix}, wd, lambda c: _Res())
    finally:
        os.rename, worker._fsync_dir = o_ren, o_dir
    st = wd / "gdelt-state"
    check("an unconfirmed rollback reports restore-rollback-failed and invalidates local reuse",
          res == {"gdelt-fetch": "restore-rollback-failed"} and "cmd" not in seen
          and not (st / worker.GDELT_BINDING).exists() and not (st / "done.txt").exists())
    # F6: an unreadable intent identity is a mismatch: marker dropped, intent kept
    jid = "k-unread"; ip = worker._intent_path(jid); ip.parent.mkdir(parents=True, exist_ok=True)
    ip.write_text('{"job": "A", "started": "t1"}')
    mk = worker._gdelt_cleanup_marker(jid); mk.parent.mkdir(parents=True, exist_ok=True)
    mk.write_text(json.dumps({"archive_sha": "x", "intent": "deadbeef"}))
    o_id = worker._gdelt_intent_identity
    worker._gdelt_intent_identity = lambda j: None   # present but unreadable
    try:
        worker._gdelt_retry_cleanup(jid)
    finally:
        worker._gdelt_intent_identity = o_id
    check("unreadable intent identity: intent kept, only the marker dropped", ip.exists() and not mk.exists())
    ip.unlink()
    mk.write_text(json.dumps({"archive_sha": "x", "intent": "deadbeef"}))
    o_rc = worker._release_claim
    worker._release_claim = lambda j, only_own=False, expect_attempt=False: True
    try:
        worker._gdelt_retry_cleanup(jid)
    finally:
        worker._release_claim = o_rc
    check("an absent intent still clears the marker", not mk.exists() and not ip.exists())
    # F7: checkpoint-io-failed quarantines the unsafe local pair before the retry is admitted
    def run_with(status, jid):
        def fake_run(job, wd):
            for d, f in (("gdelt-state", "done.txt"), ("gdelt-out", "matches.jsonl")):
                (Path(wd) / d).mkdir(parents=True, exist_ok=True); (Path(wd) / d / f).write_text("x\n")
            return {"gdelt-fetch": status}
        pubs = []
        o_pub, o_run = worker.publish, worker.run_gdelt_fetch
        worker.publish = lambda job, wd, m: pubs.append(1) or "sha"
        worker.run_gdelt_fetch = fake_run
        try:
            r = worker._execute({"id": jid, "job": fix})
        finally:
            worker.publish, worker.run_gdelt_fetch = o_pub, o_run
        return r, pubs
    worker._gdelt_progress_clear("k-ckf")
    r, pubs = run_with("checkpoint-io-failed", "k-ckf")
    q = list((worker.JOB_STATE / "gdelt-quarantine").glob("k-ckf-*"))
    wdirs = [p for p in worker.OUT.rglob("gdelt-state") if p.is_dir() and (p / "done.txt").exists() and (p.parent.name.startswith("k-ckf") or "k-ckf" in str(p))]
    check("checkpoint-io-failed: nothing published, retry admitted, unsafe pair quarantined",
          r == "incomplete" and not pubs and len(q) == 1 and (q[0] / "gdelt-state" / "done.txt").exists()
          and (q[0] / "gdelt-out" / "matches.jsonl").exists() and not wdirs)
    worker._gdelt_progress_clear("k-cki")
    r, pubs = run_with("checkpoint-io-incomplete", "k-cki")
    qi = list((worker.JOB_STATE / "gdelt-quarantine").glob("k-cki-*"))
    check("checkpoint-io-incomplete keeps the safe local checkpoint (no quarantine) and publishes", r == "incomplete" and pubs and not qi)
    # F7: when the pair cannot be set aside, the retry is NOT admitted (intent stays)
    worker._gdelt_progress_clear("k-ckn")
    o_ren = os.rename
    def ren3(a, b, *x, **k):
        if "gdelt-quarantine" in str(b):
            raise OSError("cannot move")
        return o_ren(a, b, *x, **k)
    os.rename = ren3
    try:
        r, pubs = run_with("checkpoint-io-failed", "k-ckn")
    finally:
        os.rename = o_ren
    check("unconfirmed quarantine: no retry admitted, intent kept, nothing published",
          r is None and not pubs and worker._intent_path("k-ckn").exists())
    worker._intent_path("k-ckn").unlink(missing_ok=True)
    # N2: the master download is streamed in bounded reads and a rejected listing leaves nothing behind
    _fixtures_env()
    livejob = "gdelt-fetch --start 20240501000000 --end 20240501000000"
    good = b"123 abc http://data.gdeltproject.org/gdeltv2/20240501000000.gkg.csv.zip\n" * 3
    _Resp.reads.clear()
    o_open = worker.urlopen
    worker.urlopen = lambda req, timeout=0: _Resp(good)
    ran = []
    try:
        res, seen = _run_capture({"id": "k-stream", "job": livejob}, worker.OUT / "t959k-stream", lambda c: ran.append(c) or _Res())
    finally:
        worker.urlopen = o_open
    check("streamed download: bounded reads only, filter launched, ok", res == {"gdelt-fetch": "ok"} and _Resp.reads and all(n > 0 for n in _Resp.reads))
    worker.urlopen = lambda req, timeout=0: _Resp(b"<html>not a listing</html>")
    ran = []
    try:
        res, seen = _run_capture({"id": "k-stream2", "job": livejob}, worker.OUT / "t959k-stream2", lambda c: ran.append(c) or _Res())
    finally:
        worker.urlopen = o_open
    check("an invalid streamed listing is master-download-failed and the filter never runs", res == {"gdelt-fetch": "master-download-failed"} and not ran)

def test_959l():
    # M2: a body that only resembles a listing is rejected; a valid master whose
    # entries are all outside any window still passes
    def vf(body):
        tf = Path(tempfile.mkdtemp()) / "m.txt"; tf.write_bytes(body)
        try:
            return worker._validate_master_file(tf)
        except ValueError:
            return None
    gk = b"123 abc http://data.gdeltproject.org/gdeltv2/20150218230000.gkg.csv.zip\n"
    check("M2: placeholder line with 3 fields but no GKG archive is rejected", vf(b"123 placeholder /maintenance\n") is None)
    check("M2: export/mentions-only master is rejected",
          vf(b"1 a http://x/gdeltv2/20150218230000.export.CSV.zip\n") is None)
    check("M2: non-14-digit GKG name is rejected", vf(b"1 a http://x/gdeltv2/2015.gkg.csv.zip\n") is None)
    check("M2: a recognisable GKG entry passes (window is not consulted)", vf(gk) == 1)
    check("M2: translation-style GKG entry passes",
          vf(b"1 a http://data.gdeltproject.org/gdeltv2/20150218230000.translation.gkg.csv.zip\n") == 1)
    # M3: makedirs failure is a named no-publish, retryable outcome (no escape)
    _fixtures_env()
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    o_mk = worker._makedirs_durable
    def boom(path): raise OSError("no space")
    worker._makedirs_durable = boom
    try:
        res = worker.run_gdelt_fetch({"id": "l-mk", "job": fix}, worker.OUT / "t959l-mk")
    finally:
        worker._makedirs_durable = o_mk
    check("M3: makedirs OSError returns setup-io-failed, not an exception",
          res == {"gdelt-fetch": "setup-io-failed"} and "setup-io-failed" in worker.GDELT_NO_PUBLISH)
    o_pmk = Path.mkdir
    def pmk(self, *a, **k):
        if self.name == "gdelt" and "t959l-rd" in str(self):
            raise OSError("no inodes")
        return o_pmk(self, *a, **k)
    Path.mkdir = pmk
    try:
        res = worker.run_gdelt_fetch({"id": "l-rd", "job": fix}, worker.OUT / "t959l-rd")
    finally:
        Path.mkdir = o_pmk
    check("M3: run-dir creation failure is the same named outcome", res == {"gdelt-fetch": "setup-io-failed"})
    pubs = []
    o_pub, o_run = worker.publish, worker.run_gdelt_fetch
    worker.publish = lambda job, wd, m: pubs.append(1) or "sha"
    worker.run_gdelt_fetch = lambda job, wd: {"gdelt-fetch": "setup-io-failed"}
    try:
        r = worker._execute({"id": "l-mk2", "job": fix})
    finally:
        worker.publish, worker.run_gdelt_fetch = o_pub, o_run
    check("M3: through execute(): nothing published, intent released, retry admitted",
          r == "incomplete" and not pubs and not worker._intent_path("l-mk2").exists())
    # M4: a missing checkpoint output removes the earlier run_dir copy (master failure path)
    _ensure_remote()
    wd = worker.OUT / "t959l-stale"; (wd / "gdelt").mkdir(parents=True, exist_ok=True)
    (wd / "gdelt" / "matches.jsonl").write_text('{"stale": 1}\n')
    (wd / "gdelt" / "macro_matches.jsonl").write_text('{"stale": 1}\n')
    o_url = worker.urlopen
    def fail_url(*a, **k): raise OSError("net down")
    worker.urlopen = fail_url
    live = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode live"
    try:
        res = worker.run_gdelt_fetch({"id": "l-stale", "job": live}, wd)
    finally:
        worker.urlopen = o_url
    check("M4: master failure outcome", res == {"gdelt-fetch": "master-download-failed"}, str(res))
    check("M4: stale matches copies are removed when the checkpoint has no source",
          not (wd / "gdelt" / "matches.jsonl").exists() and not (wd / "gdelt" / "macro_matches.jsonl").exists())
    wd = worker.OUT / "t959l-stale2"; (wd / "gdelt").mkdir(parents=True, exist_ok=True)
    (wd / "gdelt" / "matches.jsonl").write_text('{"stale": 1}\n')
    _mk("l-stale2")
    res, seen = _run_capture({"id": "l-stale2", "job": fix}, wd, lambda c: _Res())
    check("M4: main copy loop also drops a stale copy", not (wd / "gdelt" / "matches.jsonl").exists() or
          (wd / "gdelt" / "matches.jsonl").read_text() != '{"stale": 1}\n')
    # M5: bounded retention of gdelt-quarantine
    q = worker.JOB_STATE / "gdelt-quarantine"
    if q.exists():
        _sh.rmtree(q)
    q.mkdir(parents=True)
    now = time.time()
    for k in range(worker.GDELT_QUARANTINE_KEEP_MAX + 3):
        d = q / ("job-%d" % k); (d / "gdelt-state").mkdir(parents=True)
        os.utime(d, (now - k * 60, now - k * 60))
    old = q / "job-old"; old.mkdir()
    os.utime(old, (now - (worker.GDELT_QUARANTINE_KEEP_DAYS + 1) * 86400,) * 2)
    worker.prune_gdelt_quarantine()
    left = sorted(p.name for p in q.iterdir())
    check("M5: only the newest KEEP_MAX survive and the over-age one is gone",
          len(left) == worker.GDELT_QUARANTINE_KEEP_MAX and "job-old" not in left and "job-0" in left and "job-12" not in left, str(left))
    # 959o N2: fewer directories than KEEP_MAX: only the expired one is pruned, the recent one stays
    _sh.rmtree(q); q.mkdir(parents=True)
    exp, rec = q / "job-expired", q / "job-recent"
    for _d in (exp, rec):
        (_d / "gdelt-state").mkdir(parents=True)
    os.utime(exp, (now - (worker.GDELT_QUARANTINE_KEEP_DAYS + 1) * 86400,) * 2)
    os.utime(rec, (now - 60, now - 60))
    worker.prune_gdelt_quarantine()
    left = sorted(p.name for p in q.iterdir())
    check("959o N2: below KEEP_MAX only the expired directory is removed", 2 < worker.GDELT_QUARANTINE_KEEP_MAX and left == ["job-recent"], str(left))
    # m3: a failed fetch is not a confirmation
    calls = []
    o_gb, o_push = worker.git_bus, worker.push_bus
    def gb_fail(cmd, timeout=120):
        calls.append(cmd)
        if cmd.startswith("fetch"):
            return _Res(1, "")
        return _Res(0, "")          # a stale/empty ls-tree would fake success
    worker.git_bus, worker.push_bus = gb_fail, lambda *a, **k: True
    try:
        ok = worker._release_claim("l-claim")
    finally:
        worker.git_bus, worker.push_bus = o_gb, o_push
    check("m3: failed fetch means NOT confirmed (ls-tree never trusted)", ok is False and not any(c.startswith("ls-tree") for c in calls), str(calls))
    # m5: claim released after the deferred intent cleanup; own claims only
    def run_cleanup(owner, fetch_ok=True, push_ok=True, marker_attempt="att-1"):
        j = "l-cl"; ip = worker._intent_path(j); ip.parent.mkdir(parents=True, exist_ok=True); ip.write_text("x")
        ident = worker._gdelt_intent_identity(j)
        mk = worker._gdelt_cleanup_marker(j); mk.parent.mkdir(parents=True, exist_ok=True)
        _m = {"archive_sha": "s", "intent": ident}
        if marker_attempt is not None:
            _m["claim_attempt"] = marker_attempt     # 959o F6: a marker with an identity
        mk.write_text(json.dumps(_m))
        st = {"claim": True, "pushed": []}
        def gb(cmd, timeout=120):
            if cmd.startswith("fetch"):
                return _Res(0 if fetch_ok else 1, "")
            if cmd.startswith("ls-tree"):
                return _Res(0, "queue/claims/l-cl.json\n" if st["claim"] else "")
            if cmd.startswith("show"):
                return _Res(0, json.dumps({"worker": owner} if marker_attempt is None else {"worker": owner, "attempt": "att-1"}))
            return _Res(0, "")
        def push(msg, *a, **k):
            st["pushed"].append(msg)
            if push_ok:
                st["claim"] = False
            return push_ok
        o_gb, o_push, o_id = worker.git_bus, worker.push_bus, os.uname
        worker.git_bus, worker.push_bus = gb, push
        try:
            worker._gdelt_retry_cleanup(j)
        finally:
            worker.git_bus, worker.push_bus = o_gb, o_push
        return st, mk, ip
    me = os.uname().nodename
    st, mk, ip = run_cleanup(me)
    check("m5: own claim released after the replayed intent is removed; marker cleared",
          not ip.exists() and st["pushed"] and not mk.exists(), str(st))
    st, mk, ip = run_cleanup("another-host")
    check("m5: a claim placed by another worker is never deleted (nothing pushed)",
          not ip.exists() and not st["pushed"] and not mk.exists(), str(st))
    st, mk, ip = run_cleanup(me, push_ok=False)
    check("m5: failed release keeps a claim_pending marker for the next cycle",
          not ip.exists() and mk.exists() and json.loads(mk.read_text()) == {"claim_pending": True, "claim_attempt": "att-1"}, str(st))
    # 959o F6 repro through the real _release_claim: a legacy marker without an attempt id and a
    # same-host legacy claim without one (None == None) must NOT be unlinked or pushed.
    st, mk, ip = run_cleanup(me, marker_attempt=None)
    check("959o F6: marker without attempt + same-host legacy claim without attempt: nothing pushed, claim kept, marker dropped",
          not ip.exists() and not st["pushed"] and st["claim"] is True and not mk.exists(), str(st))
    # next cycle: succeeds, marker cleared
    mk.parent.mkdir(parents=True, exist_ok=True)
    mk.write_text(json.dumps({"claim_pending": True, "claim_attempt": "att-1"}))   # the pending marker of the failed release
    st2 = {"claim": True}
    def gb2(cmd, timeout=120):
        if cmd.startswith("ls-tree"):
            return _Res(0, "queue/claims/l-cl.json\n" if st2["claim"] else "")
        if cmd.startswith("show"):
            return _Res(0, json.dumps({"worker": me, "attempt": "att-1"}))   # 959o F3: same nonempty attempt as the marker
        return _Res(0, "")
    def push2(msg, *a, **k):
        st2["claim"] = False; return True
    o_gb, o_push = worker.git_bus, worker.push_bus
    worker.git_bus, worker.push_bus = gb2, push2
    try:
        worker._gdelt_retry_cleanup("l-cl")
    finally:
        worker.git_bus, worker.push_bus = o_gb, o_push
    check("m5: the pending marker is cleared once the release is confirmed", not mk.exists())
    check("959o F3: the replay removed the remote claim AND cleared the marker (identity-less refusal is the separate 959n F14 case)",
          st2["claim"] is False and not mk.exists(), str(st2))


def test_959m_claim_attempt_identity_f11():
    """F11: a replayed cleanup removes only the claim of the attempt that
    recorded the marker, never a later attempt's claim on the same host."""
    me = os.uname().nodename
    def run(marker, remote):
        j = "m-f11"; ip = worker._intent_path(j); ip.parent.mkdir(parents=True, exist_ok=True); ip.write_text("x")
        mk = worker._gdelt_cleanup_marker(j); mk.parent.mkdir(parents=True, exist_ok=True)
        m = dict(marker)
        if m.pop("_ident", False):
            m["intent"] = worker._gdelt_intent_identity(j)
        mk.write_text(json.dumps(m))
        st = {"claim": True, "pushed": []}
        def gb(cmd, timeout=120):
            if cmd.startswith("fetch"):
                return _Res(0, "")
            if cmd.startswith("ls-tree"):
                return _Res(0, "queue/claims/m-f11.json\n" if st["claim"] else "")
            if cmd.startswith("show"):
                return _Res(0, json.dumps(remote))
            return _Res(0, "")
        def push(msg, *a, **k):
            st["pushed"].append(msg); st["claim"] = False; return True
        o_gb, o_push = worker.git_bus, worker.push_bus
        worker.git_bus, worker.push_bus = gb, push
        try:
            worker._gdelt_retry_cleanup(j)
        finally:
            worker.git_bus, worker.push_bus = o_gb, o_push
        return st, mk
    st, mk = run({"_ident": True, "claim_attempt": "A"}, {"worker": me, "attempt": "B"})
    check("959m F11: marker from attempt A + a newer same-host claim (attempt B): nothing pushed, marker dropped",
          not st["pushed"] and not mk.exists(), str(st))
    st, mk = run({"_ident": True, "claim_attempt": "A"}, {"worker": me, "attempt": "A"})
    check("959m F11: the claim of the recording attempt is still released", len(st["pushed"]) == 1 and not mk.exists(), str(st))
    st, mk = run({"claim_pending": True, "claim_attempt": "A"}, {"worker": me, "attempt": "B"})
    check("959m F11: claim_pending marker for A leaves B's claim in place", not st["pushed"] and not mk.exists(), str(st))
    st, mk = run({"claim_pending": True, "claim_attempt": "A"}, {"worker": me, "attempt": "A"})
    check("959m F11: claim_pending marker releases its own attempt's claim", len(st["pushed"]) == 1 and not mk.exists(), str(st))
    st, mk = run({"claim_pending": True}, {"worker": me, "attempt": "B"})
    check("959m F11: legacy claim_pending marker (no identity) never releases a claim", not st["pushed"] and not mk.exists(), str(st))


def test_959m_f7_f8_f5():
    """F7 scheme-less entry rejected, valid out-of-window entry passes; F8
    OUT parent is synced and a failing sync is the retryable setup outcome;
    F5 the publish strip removes only restore stages."""
    def vf(body):
        tf = Path(tempfile.mkdtemp()) / "m.txt"; tf.write_bytes(body)
        try:
            return worker._validate_master_file(tf)
        except ValueError:
            return None
    check("959m F7: scheme-less path entry is not usable coverage",
          vf(b"123 abc /20990101000000.gkg.csv.zip\n") is None)
    check("959m F7: wrong host is not usable coverage",
          vf(b"123 abc https://evil.example/20990101000000.gkg.csv.zip\n") is None)
    check("959m F7: valid https entry outside any window still establishes the listing",
          vf(b"123 abc https://data.gdeltproject.org/gdeltv2/20150218230000.gkg.csv.zip\n") == 1)
    check("959m F7: one valid entry among invalid ones counts",
          vf(b"1 a /x/20150218230000.gkg.csv.zip\n123 abc http://data.gdeltproject.org/gdeltv2/20150218230000.gkg.csv.zip\n") == 2)
    _fixtures_env()
    fix = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    o = worker._fsync_dir
    seen = []
    wd = worker.OUT / "t959m-f8"
    def spy(path):
        seen.append(str(path))
        if str(path) == str(wd.parent) and spy.fail:
            raise OSError("sync")
        return o(path)
    spy.fail = True
    worker._fsync_dir = spy
    try:
        res = worker.run_gdelt_fetch({"id": "m-f8", "job": fix}, wd)
    finally:
        worker._fsync_dir = o
    check("959m F8: a failing sync of OUT is the retryable no-publish setup outcome and OUT was synced",
          res == {"gdelt-fetch": "setup-io-failed"} and str(wd.parent) in seen, str((res, seen[-3:])))
    d = Path(tempfile.mkdtemp())
    (d / ".gdelt-restore-abc" / "prev-out").mkdir(parents=True)
    (d / ".gdelt-restore-abc" / "prev-out" / "m.jsonl").write_text("x")
    (d / "gdelt").mkdir(); (d / "gdelt" / "keep.txt").write_text("k")
    check("959n F6: the strip is the helper publish() calls", worker._strip_restore_stages(d) == 0
          and "_strip_restore_stages(dest)" in inspect.getsource(worker.publish))
    check("959m F5: the strip removes the restore stage and keeps everything else",
          not (d / ".gdelt-restore-abc").exists() and (d / "gdelt" / "keep.txt").exists())


def test_959m_f6_f9_f10_f12():
    _fixtures_env()
    # F6: the output directory's parent is synced after the output install and BEFORE the state install
    _mk("m-f6", matches='{"ok": 1}\n')
    arch = worker.ROOT / "archive-push"
    wd = worker.OUT / "t959m-f6"; _local_state(wd, "LOCAL\n", binding="worker-runs/older/run")
    (wd / "gdelt-out").mkdir(parents=True, exist_ok=True); (wd / "gdelt-out" / "matches.jsonl").write_text('{"local": 1}\n')
    real_r, real_s, ev = os.rename, worker._fsync_dir, []
    def spy_r(src, dst, *a, **k):
        ev.append(("rename", Path(dst).name)); return real_r(src, dst, *a, **k)
    def spy_s(path):
        ev.append(("sync", str(path))); return real_s(path)
    os.rename, worker._fsync_dir = spy_r, spy_s
    try:
        worker._gdelt_restore_remote(arch, "m-f6", wd / "gdelt-state", wd / "gdelt-out", mode="fixtures")
    finally:
        os.rename, worker._fsync_dir = real_r, real_s
    i_out = max(i for i, e in enumerate(ev) if e == ("rename", "gdelt-out"))
    i_st = max(i for i, e in enumerate(ev) if e == ("rename", "gdelt-state"))
    check("959m F6: a directory sync of the workdir sits between the output install and the state install",
          i_out < i_st and any(e == ("sync", str(wd)) for e in ev[i_out + 1:i_st]), str(ev[i_out:i_st + 1]))
    # F9: a predecessor with another window is never restored nor published under the current plan
    live = "gdelt-fetch --start 20240601000000 --end 20240630235959 --mode fixtures"
    _make_archive_run("2026-11-27", "100000", "x", "m-f9-may", "MAY\n", matches='{"file": "f1", "company": "MAY"}\n',
                      window=("20240501000000", "20240531235959"))
    called = []
    res, seen = _run_capture({"id": "m-f9-june", "job": live + " --resume-from m-f9-may"}, worker.OUT / "t959m-f9",
                             lambda c: called.append(c) or _Res())
    wd9 = worker.OUT / "t959m-f9"
    check("959m F9: May predecessor + June plan is rejected, filter never runs, no May matches or state installed",
          res == {"gdelt-fetch": "resume-mode-mismatch"} and not called
          and not (wd9 / "gdelt-out" / "matches.jsonl").exists() and not (wd9 / "gdelt-state" / "done.txt").exists()
          and not (wd9 / "gdelt" / "gdelt_fetch.json").exists(), str(res))
    _make_archive_run("2026-11-27", "110000", "x", "m-f9-ok", "JUNE\n", window=("20240601000000", "20240630235959"))
    res, seen = _run_capture({"id": "m-f9-ok2", "job": live + " --resume-from m-f9-ok"}, worker.OUT / "t959m-f9b", lambda c: _Res())
    check("959m F9: a predecessor with the same window still restores", seen["state_text"] == "JUNE\n")
    # F10: an unsafe exit is classified before any checkpoint file is read
    for safe, want in (("safe=0", "checkpoint-io-failed"), ("safe=1", "checkpoint-io-failed")):
        def runner(c, safe=safe):
            sd = Path(_tok(c, "--state"))
            (sd / "absent.txt").unlink(missing_ok=True)
            (sd / "absent.txt").mkdir()          # unreadable as a file: read_text raises
            return _Res(75, "gkg-filter-checkpoint-error " + safe)
        try:
            res, seen = _run_capture({"id": "m-f10-" + safe, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999 --mode fixtures"},
                                     worker.OUT / ("t959m-f10-" + safe), runner)
            got = res
        except Exception as e:
            got = "raised %s" % type(e).__name__
        check("959m F10: rc 75 %s with an unreadable absent.txt returns %s instead of raising" % (safe, want),
              got == {"gdelt-fetch": want}, str(got))
    # F12: a failed publish of an incomplete gdelt-fetch run does not leave the job gated
    jid = "m-f12"
    o_pub, o_md, o_run, o_rpf = worker.publish, worker._mark_done, worker.run_gdelt_fetch, worker._record_publish_failure
    def fake_run(job, wd):
        g = Path(wd) / "gdelt"; g.mkdir(parents=True, exist_ok=True)
        (g / "gdelt_fetch.json").write_text(json.dumps({"files_done": 1, "macro_files_done": 0}))
        return {"gdelt-fetch": "budget-exhausted"}
    failed = []
    worker.publish = lambda job, wd, m: None
    worker._mark_done = lambda job, sha, extra=None: failed.append("done")
    worker.run_gdelt_fetch = fake_run
    worker._record_publish_failure = lambda job: failed.append("recorded")
    try:
        out = worker._execute({"id": jid, "job": "gdelt-fetch --start 20200101000000 --end 20200131235959 --mode fixtures"})
    finally:
        worker.publish, worker._mark_done, worker.run_gdelt_fetch, worker._record_publish_failure = o_pub, o_md, o_run, o_rpf
    check("959m F12: failed publish of a budget-limited run records the failure, releases the intent, reports incomplete (claim release), never marks done",
          out == "incomplete" and failed == ["recorded"] and not worker._intent_path(jid).exists(), str((out, failed)))


def test_959n_worker_findings():
    _fixtures_env()
    base = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    # F7: a negative budget is refused at parse time; 0 stays unlimited.
    check("959n F7: --budget-seconds -1 is refused", worker.parse_gdelt_fetch_job(base + " --budget-seconds -1") is None)
    p0 = worker.parse_gdelt_fetch_job(base + " --budget-seconds 0")
    p5 = worker.parse_gdelt_fetch_job(base + " --budget-seconds 5")
    check("959n F7: 0 stays unlimited and a positive value passes",
          p0 is not None and p0["budget_seconds"] == 0 and p5 is not None and p5["budget_seconds"] == 5)
    # F9: restore memory does not scale with the checkpoint (streamed tar and
    # line-by-line validation). 8 MB of matches; the old code peaked at ~3x.
    import tracemalloc
    line = json.dumps({"file": "f1", "company": "X" * 200}) + "\n"
    big = line * (8 * 1024 * 1024 // len(line))
    d9 = _make_archive_run("2026-11-27", "100400", "x", "n-f9", "f1\n", matches=big,
                           window=("20240501000000", "20240501000000"))
    arch = worker.ROOT / "archive-push"
    picked = worker._gdelt_pick_published(arch, "n-f9", "fixtures")
    w9 = worker.OUT / "t959n-f9"; w9.mkdir(parents=True, exist_ok=True)
    tracemalloc.start()
    worker._gdelt_restore_remote(arch, "n-f9", w9 / "st", w9 / "out", mode="fixtures", picked=picked,
                                 window=("20240501000000", "20240501000000"))
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    check("959n F9: peak Python memory of an 8 MB checkpoint restore stays under half the file (4 MB)", peak < len(big) // 2, str(peak))
    check("959n F9: the matches were installed intact and no scratch tar is left",
          (w9 / "out" / "matches.jsonl").read_bytes() == big.encode() and not list(w9.rglob("archive.tar")))
    # F10: mkdtemp failing is a named no-publish outcome, not an escaping OSError.
    import tempfile as _tf
    o_mk = _tf.mkdtemp
    def bad_mk(*a, **k):
        raise OSError("no space")
    _tf.mkdtemp = bad_mk
    try:
        res = worker.run_gdelt_fetch({"id": "n-f10", "job": base}, worker.OUT / "t959n-f10")
    except OSError:
        res = "ESCAPED"
    finally:
        _tf.mkdtemp = o_mk
    check("959n F10: mkdtemp OSError returns setup-io-failed", res == {"gdelt-fetch": "setup-io-failed"}, str(res))
    # F8: restored config window must match the job window before install.
    def side_only(d, side):
        (d / "gdelt" / "gdelt_fetch.json").write_text(json.dumps(side))
        arch = worker.ROOT / "archive-push"
        _git("add", "-A", str(d), cwd=arch); _git("commit", "-m", "side " + d.name, cwd=arch)
        _git("push", "origin", "HEAD:archive", cwd=arch)
    badcfg = {"config.json": {"aliases_sha256": "a", "start": "20230101000000", "end": "20230101000000", "out": "/o"}}
    _make_archive_run("2026-11-27", "100000", "x", "n-f8a", "OLDWINDOW\n", config=badcfg,
                      window=("20240501000000", "20240501000000"))   # sidecar matches; only the config differs
    res, seen = _run_capture({"id": "n-f8a", "job": base}, worker.OUT / "t959n-f8a", lambda c: _Res())
    check("959n F8: a restored config for another window is refused, nothing installed, filter not run",
          res == {"gdelt-fetch": "resume-mode-mismatch"} and "cmd" not in seen
          and not (worker.OUT / "t959n-f8a" / "gdelt-state" / "done.txt").exists(), str((res, seen.get("state_text"))))
    d = _make_archive_run("2026-11-27", "100100", "x", "n-f8b", "LEGACY\n")
    side_only(d, {"mode": "fixtures"})
    res, seen = _run_capture({"id": "n-f8b", "job": base}, worker.OUT / "t959n-f8b", lambda c: _Res())
    check("959n F8: a bound-less sidecar with a bound-less checkpoint is refused",
          res == {"gdelt-fetch": "resume-mode-mismatch"} and "cmd" not in seen, str(res))
    okcfg = {"config.json": {"aliases_sha256": "a", "start": "20240501000000", "end": "20240501000000", "out": "/o"}}
    d = _make_archive_run("2026-11-27", "100200", "x", "n-f8c", "LEGACY-OK\n", config=okcfg)
    side_only(d, {"mode": "fixtures"})
    res, seen = _run_capture({"id": "n-f8c", "job": base}, worker.OUT / "t959n-f8c", lambda c: _Res())
    check("959n F8: a bound-less sidecar is accepted when the checkpoint config establishes the window",
          seen.get("state_text") == "LEGACY-OK\n", str((res, seen.get("state_text"))))
    # F11 / F12: the master-download-failure handler and the status order.
    import shutil as _shu
    _make_archive_run("2026-11-27", "100300", "x", "n-f11", "f1\n", matches='{"file": "f1"}\n', mode="live",
                      window=("20240501000000", "20240501000000"))
    o_url, o_cp = worker.urlopen, worker.shutil.copy2
    def boom(req, timeout=300):
        raise OSError("down")
    def cp_fail(*a, **k):
        raise OSError("copy failed")
    worker.urlopen = boom; worker.shutil.copy2 = cp_fail
    try:
        wd = worker.OUT / "t959n-f11"; wd.mkdir(parents=True, exist_ok=True)
        try:
            res = worker.run_gdelt_fetch({"id": "n-f11", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000"}, wd)
        except OSError:
            res = "ESCAPED"
    finally:
        worker.urlopen, worker.shutil.copy2 = o_url, o_cp
    check("959n F11: a checkpoint copy failure in the download-failure handler is checkpoint-io-failed",
          res == {"gdelt-fetch": "checkpoint-io-failed"}, str(res))
    def runner(cmd):
        out = Path(_tok(cmd, "--out"))
        (out / "matches.jsonl").write_text('{"a": 1}\n')
        raise _sp.TimeoutExpired(cmd, 7200, output=b"", stderr="")
    worker.shutil.copy2 = cp_fail
    try:
        res, _ = _run_capture({"id": "n-f12", "job": base}, worker.OUT / "t959n-f12", runner)
    finally:
        worker.shutil.copy2 = o_cp
    check("959n F12: a timeout plus a copy failure is checkpoint-io-failed (no publish), not timeout",
          res == {"gdelt-fetch": "checkpoint-io-failed"}, str(res))
    # F13: the pending release is persisted BEFORE the claim delete, kept when unconfirmed.
    def exec_incomplete(rel_result):
        jid = "n-f13"
        mk = worker._gdelt_cleanup_marker(jid); mk.parent.mkdir(parents=True, exist_ok=True); mk.unlink(missing_ok=True)
        before = []
        o_ex, o_rel, o_att = worker._execute, worker._release_claim, worker._local_claim_attempt
        worker._execute = lambda job: "incomplete"
        def rel(job_id, *a, **k):
            before.append(json.loads(mk.read_text()) if mk.exists() else None)
            return rel_result
        worker._release_claim = rel
        worker._local_claim_attempt = lambda j: "ATT-1"
        try:
            worker.execute({"id": jid, "job": base})
        finally:
            worker._execute, worker._release_claim, worker._local_claim_attempt = o_ex, o_rel, o_att
        return before, mk
    before, mk = exec_incomplete(False)
    check("959n F13: pending marker with the attempt exists before the delete and stays when unconfirmed",
          before == [{"claim_pending": True, "claim_attempt": "ATT-1"}] and mk.exists(), str((before, mk.exists())))
    mk.unlink(missing_ok=True)
    before, mk = exec_incomplete(True)
    check("959n F13: a confirmed release clears the marker",
          before == [{"claim_pending": True, "claim_attempt": "ATT-1"}] and not mk.exists())
    # F14: a missing/null/non-string/empty claim_attempt is identity-less.
    me = os.uname().nodename
    for label, marker in (("missing", {"claim_pending": True}), ("null", {"claim_pending": True, "claim_attempt": None}),
                          ("empty", {"claim_pending": True, "claim_attempt": ""}), ("non-string", {"claim_pending": True, "claim_attempt": 7})):
        j = "n-f14"; mk = worker._gdelt_cleanup_marker(j); mk.parent.mkdir(parents=True, exist_ok=True)
        mk.write_text(json.dumps(marker)); pushed = []
        def gb(cmd, timeout=120):
            if cmd.startswith("ls-tree"):
                return _Res(0, "queue/claims/n-f14.json\n")
            if cmd.startswith("show"):
                return _Res(0, json.dumps({"worker": me}))   # a claim with no attempt either
            return _Res(0, "")
        o_gb, o_push = worker.git_bus, worker.push_bus
        worker.git_bus, worker.push_bus = gb, (lambda m, *a, **k: pushed.append(m) or True)
        try:
            worker._gdelt_retry_cleanup(j)
        finally:
            worker.git_bus, worker.push_bus = o_gb, o_push
        check("959n F14: %s claim_attempt drops the marker without releasing" % label, not pushed and not mk.exists(), str(pushed))
    # F15: a failed publish of an incomplete run records the stall.
    noted = []
    o_pub, o_run, o_note = worker.publish, worker.run_gdelt_fetch, worker._gdelt_note_incomplete
    def fake_run(job, wd):
        g = Path(wd) / "gdelt"; g.mkdir(parents=True, exist_ok=True)
        (g / "gdelt_fetch.json").write_text(json.dumps({"files_done": 4, "macro_files_done": 1, "absent_files": 2, "transient_files": 3}))
        return {"gdelt-fetch": "timeout"}
    worker.publish = lambda job, wd, m: None
    worker.run_gdelt_fetch = fake_run
    worker._gdelt_note_incomplete = lambda jid, total, now_ts=None: noted.append((jid, total))
    try:
        worker._execute({"id": "n-f15", "job": base})
    finally:
        worker.publish, worker.run_gdelt_fetch, worker._gdelt_note_incomplete = o_pub, o_run, o_note
    check("959n F15: the failed-publish incomplete path records the stall with the summed total",
          noted == [("n-f15", 10)], str(noted))



def test_959o_worker_findings():
    _fixtures_env()
    base = "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"
    # U1: the LAST complete anchored checkpoint-error record on STDOUT decides, for both guards.
    SAFE1, SAFE0 = "gkg-filter-checkpoint-error safe=1 setup OSError\n", "gkg-filter-checkpoint-error safe=0 sync OSError\n"
    cases = (("safe=1 then a later safe=0 record", SAFE1 + "x\n" + SAFE0, "", "checkpoint-io-failed", False),
             ("safe=0 then a later safe=1 record", SAFE0 + SAFE1, "", "checkpoint-io-incomplete", True),
             ("safe=1 only on stderr", "", SAFE1, "checkpoint-io-failed", False),
             ("safe=1 not at the line start", "note: gkg-filter-checkpoint-error safe=1\n", "", "checkpoint-io-failed", False),
             ("no record at all", "something else\n", "", "checkpoint-io-failed", False),
             ("safe=1 truncated (no newline) after an earlier safe=0", SAFE0 + "gkg-filter-checkpoint-error safe=1", "", "checkpoint-io-failed", False),
             ("safe=1 record", SAFE1, "", "checkpoint-io-incomplete", True))
    for i, (label, out, err, want, copied) in enumerate(cases):
        wd = worker.OUT / ("t959o-u1-%d" % i)
        def runner(cmd, out=out, err=err):
            (Path(_tok(cmd, "--out")) / "matches.jsonl").write_text('{"a": 1}\n')
            return _Res(75, out, err)
        res, _ = _run_capture({"id": "o-u1-%d" % i, "job": base}, wd, runner)
        check("959o U1: %s -> %s" % (label, want), res == {"gdelt-fetch": want}, str(res))
        check("959o U1: %s -> checkpoint %s (the second guard agrees)" % (label, "copied" if copied else "not copied"),
              (wd / "gdelt" / "matches.jsonl").exists() == copied)
    # F4: a marked refusal still copies its (consistent) checkpoint; an unexpected exit does not.
    for rc, out, copied, lab in ((1, "refusal msg\ngkg-filter-refusal\n", True, "marked refusal"), (137, "", False, "SIGKILL")):
        wd = worker.OUT / ("t959o-f4c-%d" % rc)
        def runner(cmd, rc=rc, out=out):
            (Path(_tok(cmd, "--out")) / "matches.jsonl").write_text('{"a": 1}\n')
            return _Res(rc, out)
        _run_capture({"id": "o-f4c-%d" % rc, "job": base}, wd, runner)
        check("959o F4: %s -> checkpoint %s" % (lab, "copied" if copied else "not copied"), (wd / "gdelt" / "matches.jsonl").exists() == copied)
    # F4: a SIGKILL-style exit is retryable: no publish, not done, quarantined, claim released.
    pubs, dones, quar = [], [], []
    o_pub, o_md, o_run, o_q = worker.publish, worker._mark_done, worker.run_gdelt_fetch, worker._gdelt_quarantine_checkpoint
    worker.publish = lambda job, wd, m: pubs.append(job["id"]) or "sha"
    worker._mark_done = lambda job, sha, extra=None: dones.append(job["id"])
    worker._gdelt_quarantine_checkpoint = lambda jid, wd: quar.append(jid) or True
    rets = {}
    try:
        for st, jid in (("unexpected-exit-137", "o-f4-137"), ("unexpected-exit--9", "o-f4-sig"), ("unexpected-exit-1", "o-f4-1"),
                        ("refused", "o-f4-ref"), ("resume-predecessor-missing", "o-f7-pred"), ("resume-mode-mismatch", "o-f7-mode")):
            worker.run_gdelt_fetch = lambda job, wd, st=st: {"gdelt-fetch": st}
            rets[jid] = worker._execute({"id": jid, "job": base})
    finally:
        worker.publish, worker._mark_done, worker.run_gdelt_fetch, worker._gdelt_quarantine_checkpoint = o_pub, o_md, o_run, o_q
    for jid in ("o-f4-137", "o-f4-sig", "o-f4-1"):
        check("959o F4: %s is never published and never marked done" % jid, jid not in pubs and jid not in dones)
        check("959o F4: %s checkpoint is quarantined and the claim is released for retry" % jid, jid in quar and rets[jid] == "incomplete", str((quar, rets[jid])))
    check("959o F4: a marked refusal keeps the terminal behaviour (published, marked done)", "o-f4-ref" in pubs and "o-f4-ref" in dones)
    for jid in ("o-f7-pred", "o-f7-mode"):
        check("959o F7: %s neither publishes nor marks done" % jid, jid not in pubs and jid not in dones)
        check("959o F7: %s is retryable (claim released, stall noted)" % jid, rets[jid] == "incomplete", str(rets[jid]))
    check("959o F7: both statuses are in the no-publish set", all(x in worker.GDELT_NO_PUBLISH for x in ("resume-predecessor-missing", "resume-mode-mismatch")))
    # F5: ENOSPC on the log or sidecar write after the intent exists is the no-publish retry outcome.
    for target in ("gdelt-fetch.log", "gdelt_fetch.json"):
        real_wt = Path.write_text
        def wt(self, *a, **k):
            if self.name == target:
                raise OSError(28, "No space left on device")
            return real_wt(self, *a, **k)
        Path.write_text = wt
        try:
            res, _ = _run_capture({"id": "o-f5-" + target[:8], "job": base}, worker.OUT / ("t959o-f5-" + target[:8]), lambda c: _Res())
        finally:
            Path.write_text = real_wt
        check("959o F5: ENOSPC writing %s is checkpoint-io-failed (no publish), not an escaped OSError" % target,
              res == {"gdelt-fetch": "checkpoint-io-failed"}, str(res))
    # F8: a publication TimeoutExpired for an incomplete run takes the unconfirmed-publication path.
    noted, failed, released = [], [], []
    o_pub, o_run, o_note, o_rf, o_ri = worker.publish, worker.run_gdelt_fetch, worker._gdelt_note_incomplete, worker._record_publish_failure, worker._gdelt_release_intent
    def fake_run(job, wd):
        g = Path(wd) / "gdelt"; g.mkdir(parents=True, exist_ok=True)
        (g / "gdelt_fetch.json").write_text(json.dumps({"files_done": 2, "macro_files_done": 0, "absent_files": 0, "transient_files": 0}))
        return {"gdelt-fetch": "timeout"}
    def boom(job, wd, m):
        raise _sp.TimeoutExpired("git push", 600)
    worker.publish, worker.run_gdelt_fetch = boom, fake_run
    worker._gdelt_note_incomplete = lambda jid, total, now_ts=None: noted.append((jid, total))
    worker._record_publish_failure = lambda job: failed.append(job["id"])
    worker._gdelt_release_intent = lambda jid, *a, **k: released.append(jid) or True
    try:
        ret = worker._execute({"id": "o-f8", "job": base})
    finally:
        worker.publish, worker.run_gdelt_fetch, worker._gdelt_note_incomplete = o_pub, o_run, o_note
        worker._record_publish_failure, worker._gdelt_release_intent = o_rf, o_ri
    check("959o F8: publish TimeoutExpired on an incomplete run: failure recorded, stall noted, intent released, claim released",
          failed == ["o-f8"] and noted == [("o-f8", 2)] and released == ["o-f8"] and ret == "incomplete", str((failed, noted, released, ret)))


def main():
    test_parse_ok()
    test_parse_rejects()
    test_959i_restore_tail_and_records()
    test_959i_swap_order_and_rollback()
    test_959i_dirs_lookup_predecessor()
    test_959i_deferred_and_stall_and_intent()
    test_959j_durability_and_failures()
    test_959j_more_asks()
    test_959k()
    test_959l()
    test_restore_checks_recorded_mode()
    test_restore_is_staged_and_atomic()
    test_new_claim_checks_the_published_snapshot()
    test_parse_rejects_non_ascii_digits()
    test_959m_claim_attempt_identity_f11()
    test_959m_f7_f8_f5()
    test_959m_f6_f9_f10_f12()
    test_959n_worker_findings()
    test_959o_worker_findings()
    test_filter_launch_env_is_denylist_filtered()
    test_deferred_unparseable_deadline()
    test_parse_fixtures()
    test_bad_job()
    test_fixtures_run()
    test_live_argv_no_duplicate()
    test_parse_resume_key()
    test_restore_from_dated_dirs()
    test_resume_key_predecessor_and_requeue()
    test_budget_run_not_queue_done_and_complete_is_done()
    test_budget_status_from_filter_output()
    test_master_lists_excluded_from_publish_copy()
    test_timeout_archives_partial_output()
    test_nonzero_exit_log_tail_bounded()
    test_restore_ignores_unpublished_local_residue()
    test_restore_brings_back_predecessor_matches()
    test_restore_brings_back_absent_state()
    test_master_download_failed_publishes_restored_matches()
    test_unfinished_status_from_filter_output()
    test_execute_releases_bus_claim_for_incomplete_run()
    test_timeout_with_truncated_utf8_record()
    test_stuck_incomplete_job_yields_the_lane()
    test_progressing_incomplete_job_resumes_and_is_not_demoted()
    test_progress_total_never_decreases()
    test_download_failure_reports_restored_progress()
    test_absent_counts_as_progress()
    test_sidecar_reports_absent_both_paths()
    print("\n%d passed" % PASSED)
    return 0

if __name__ == "__main__":
    sys.exit(main())
