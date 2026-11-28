#!/usr/bin/env python3
"""Tests for gdelt-fetch job type."""
import json
import os
import shlex
import sys
import tempfile
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

def _make_archive_run(date, hms, slug_tail, jobid, done_lines, with_state=True):
    d = worker.ROOT / "archive-push" / "worker-runs" / date / ("%s__%s__%s" % (hms, slug_tail, jobid))
    (d / "gdelt").mkdir(parents=True, exist_ok=True)
    if with_state:
        (d / "gdelt-state").mkdir(parents=True, exist_ok=True)
        (d / "gdelt-state" / "done.txt").write_text(done_lines)
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
    check("resume key: restores the predecessor's latest run, not its own", seen["state_text"] == "PRED-NEW\n")
    job2 = {"id": "succ-B", "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
    res, seen = _run_capture(job2, worker.OUT / "t959-requeue", lambda c: _Res())
    check("same-id re-queue resumes from its own published partial run", seen["state_text"] == "OWN\n")
    # no prior state anywhere: starts fresh
    job3 = {"id": "never-ran", "job": job2["job"]}
    res, seen = _run_capture(job3, worker.OUT / "t959-fresh", lambda c: _Res())
    check("no predecessor: fresh state", seen["state_text"] is None)

def test_budget_run_not_queue_done_and_complete_is_done():
    done_calls, pub_calls = [], []
    o_pub, o_md, o_run = worker.publish, worker._mark_done, worker.run_gdelt_fetch
    worker.publish = lambda job, wd, m: pub_calls.append(job["id"]) or "sha123"
    worker._mark_done = lambda job, sha, extra=None: done_calls.append(job["id"])
    try:
        for status, jid in (("budget-exhausted", "q-budget"), ("timeout", "q-timeout"), ("ok", "q-ok"), ("exit-1", "q-exit")):
            worker.run_gdelt_fetch = lambda job, wd, st=status: {"gdelt-fetch": st}
            job = {"id": jid, "job": "gdelt-fetch --start 20240501000000 --end 20240501000000 --mode fixtures"}
            worker._execute(job)
        check("budget-limited run archived", "q-budget" in pub_calls and "q-timeout" in pub_calls)
        check("budget-limited run NOT marked queue-done", "q-budget" not in done_calls)
        check("timed-out run NOT marked queue-done", "q-timeout" not in done_calls)
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

def main():
    test_parse_ok()
    test_parse_rejects()
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
    print("\n%d passed" % PASSED)
    return 0

if __name__ == "__main__":
    sys.exit(main())
