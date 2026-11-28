#!/usr/bin/env python3
"""Tests for gdelt-fetch job type."""
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
def check(name, cond):
    global PASSED
    assert cond, name
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
    # 6
    o_sh = worker.sh
    def bad_fetch(cmd, *a, **k):
        if " fetch origin" in cmd:
            return _Res(1, "")
        return o_sh(cmd, *a, **k)
    worker.sh = bad_fetch
    called = []
    try:
        res, seen = _run_capture({"id": "i-look", "job": FIXJOB}, worker.OUT / "t959i-look", lambda c: called.append(c) or _Res())
    finally:
        worker.sh = o_sh
    check("a failed archive check is a named outcome and nothing runs", res == {"gdelt-fetch": "archive-check-failed"} and not called)
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
    pending = worker._done_or_pending(j3)
    check("once storage recovers the retry removes intent and marker without a fetch",
          not ip.exists() and not worker._gdelt_cleanup_marker(j3).exists() and pending is False)
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
        def __init__(self, data): self._data = data
        def read(self): return self._data
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
                      extra_state=None, mode="fixtures"):
    """Create worker-runs/DATE/HMS__slug__jobid in the local checkout.
    published=True commits and pushes it to the remote archive branch;
    published=False leaves it as local residue (a failed publish)."""
    _ensure_remote()
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
        (d / "gdelt" / "gdelt_fetch.json").write_text(json.dumps({"mode": mode}))
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
        for status, jid in (("budget-exhausted", "q-budget"), ("timeout", "q-timeout"), ("ok", "q-ok"), ("exit-1", "q-exit"),
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
        def __init__(self, d): self._d = d
        def read(self): return self._d
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
    check("nonzero exit status", res == {"gdelt-fetch": "exit-3"})
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
    cfg = {"config.json": {"aliases_sha256": "abc", "start": "20240501000000", "end": "20240501999999", "out": "/old/place/gdelt-out"},
           "macro_config.json": {"themes_sha256": "def", "start": "20240501000000", "end": "20240501999999", "out": "/old/place/gdelt-out"}}
    co_old = '{"file": "f1", "company": "OLD"}\n'
    ma_old = '{"file": "f1", "theme": "OLDMACRO"}\n'
    _make_archive_run("2026-11-27", "100000", "x", jid, "f1\n", matches=co_old, macro=ma_old, config=cfg)
    job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999 --mode fixtures"}
    def runner(cmd):
        out = Path(_tok(cmd, "--out"))
        with open(out / "matches.jsonl", "a") as f:
            f.write('{"file": "f2", "company": "NEW"}\n')
        with open(out / "macro_matches.jsonl", "a") as f:
            f.write('{"file": "f2", "theme": "NEWMACRO"}\n')
        return _Res()
    wd = worker.OUT / "t959-matches"
    res, seen = _run_capture(job, wd, runner)
    pub = (wd / "gdelt" / "matches.jsonl").read_text()
    pubm = (wd / "gdelt" / "macro_matches.jsonl").read_text()
    check("published company matches include the predecessor's for done files", pub == co_old + '{"file": "f2", "company": "NEW"}\n')
    check("published macro matches include the predecessor's for done files", pubm == ma_old + '{"file": "f2", "theme": "NEWMACRO"}\n')
    out_abs = os.path.abspath(str(wd / "gdelt-out"))
    c1 = json.loads((wd / "gdelt-state" / "config.json").read_text())
    c2 = json.loads((wd / "gdelt-state" / "macro_config.json").read_text())
    check("restored config re-pointed at this out dir", c1["out"] == out_abs and c2["out"] == out_abs)
    check("restored config keeps its hash and window", c1["aliases_sha256"] == "abc" and c1["end"] == "20240501999999" and c2["themes_sha256"] == "def")
    check("matches restored with the state, summary counts them", json.loads((wd / "gdelt" / "gdelt-state-summary.json").read_text())["matches"] == 2)
    # no predecessor: no matches appear from nowhere
    wd2 = worker.OUT / "t959-matches-fresh"
    res, seen = _run_capture({"id": "matches-none", "job": job["job"]}, wd2, lambda c: _Res())
    check("fresh run restores no matches", not (wd2 / "gdelt-out" / "matches.jsonl").exists())

def test_restore_brings_back_absent_state():
    _fixtures_env()
    jid = "absent-1"
    ab = "20240501001500.gkg.csv.zip\n20240501003000.gkg.csv.zip\n"
    _make_archive_run("2026-11-27", "100000", "x", jid, "f1\n", extra_state={"absent.txt": ab})
    job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501999999 --mode fixtures"}
    res, seen = _run_capture(job, worker.OUT / "t959-absent", lambda c: _Res())
    got = worker.OUT / "t959-absent" / "gdelt-state" / "absent.txt"
    check("absent.txt restored with the predecessor's state", got.exists() and got.read_text() == ab)
    check("done.txt still restored", seen["state_text"] == "f1\n")
    # a predecessor without absent.txt restores none (no file appears from nowhere)
    _make_archive_run("2026-11-27", "110000", "x", "absent-2", "f1\n")
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

def _progress_run(jid, files_done, status="budget-exhausted", absent=None, transient=None, pubs=None):
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
    worker._mark_done = lambda job, sha, extra=None: None
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
    def pick(arch, src, mode, strict=False):
        calls.append(src)
        if len(calls) == 1:
            return None
        raise RuntimeError("git failed")
    worker._gdelt_pick_published = pick
    try:
        res, seen = _run_capture({"id": "j-own", "job": fix + " --resume-from j-pred"}, worker.OUT / "t959j-pred", lambda c: _Res())
    finally:
        worker._gdelt_pick_published = o_pick
    check("a failing predecessor lookup is an unknown resume state: nothing runs", res == {"gdelt-fetch": "archive-check-failed"} and "cmd" not in seen)
    # 3: empty or invalid live master lists
    for body, label in ((b"", "empty"), (b"\n  \n", "blank"), (b"<html>oops</html>", "html"), (b"\xff\xfe", "undecodable")):
        try:
            worker._validate_master_listing(body); ok = False
        except Exception:
            ok = True
        check("master listing %s is rejected" % label, ok)
    good = b"123 abc http://data.gdeltproject.org/gdeltv2/20240501000000.gkg.csv.zip\n"
    check("a valid listing passes", worker._validate_master_listing(good) == 1)
    class _Resp:
        def __init__(self, b): self.b = b
        def read(self): return self.b
        def __enter__(self): return self
        def __exit__(self, *a): return False
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
                          (1, "state config mismatch\n", "exit-1")):
        res, seen = _run_capture({"id": "j-ck%d" % len(want), "job": fix}, worker.OUT / ("t959j-ck%d" % len(want)), lambda c, rc=rc, out=out: _Res(rc, out))
        check("filter rc %d / %r -> %s" % (rc, out[:30], want), res == {"gdelt-fetch": want})
    check("checkpoint-io-incomplete is incomplete (archived, never queue-done); checkpoint-io-failed publishes nothing",
          "checkpoint-io-incomplete" in worker.GDELT_INCOMPLETE and "checkpoint-io-failed" in worker.GDELT_NO_PUBLISH
          and "checkpoint-io-failed" not in worker.GDELT_INCOMPLETE and "exit-1" not in worker.GDELT_INCOMPLETE)
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
    worker._gdelt_retry_cleanup(jid)
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
    class _Resp:
        def __init__(self, b): self.b = b
        def read(self): return self.b
        def __enter__(self): return self
        def __exit__(self, *a): return False
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
    o_md = worker._mark_done
    worker._mark_done = lambda job, sha, extra=None: done.append(sha)
    try:
        r = _progress_run(j, 4, status="checkpoint-io-incomplete")
    finally:
        worker._mark_done = o_md
    rec = worker._gdelt_progress_read(j)
    check("checkpoint-io-incomplete: not marked done, claim released for retry, progress total kept",
          not done and r == "incomplete" and rec["total"] == 4)

def main():
    test_parse_ok()
    test_parse_rejects()
    test_959i_restore_tail_and_records()
    test_959i_swap_order_and_rollback()
    test_959i_dirs_lookup_predecessor()
    test_959i_deferred_and_stall_and_intent()
    test_959j_durability_and_failures()
    test_959j_more_asks()
    test_restore_checks_recorded_mode()
    test_restore_is_staged_and_atomic()
    test_new_claim_checks_the_published_snapshot()
    test_parse_rejects_non_ascii_digits()
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
