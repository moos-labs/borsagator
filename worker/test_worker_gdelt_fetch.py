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
                      published=True, matches=None, macro=None, config=None):
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
    if matches is not None:
        (d / "gdelt" / "matches.jsonl").write_text(matches)
    if macro is not None:
        (d / "gdelt" / "macro_matches.jsonl").write_text(macro)
    (d / "gdelt" / "keep").write_text("x")
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

def test_master_download_failed_publishes_restored_matches():
    _fixtures_env()
    jid = "mdf-1"
    cfg = {"config.json": {"aliases_sha256": "abc", "start": "20240501000000", "end": "20240501999999", "out": "/old/out"}}
    _make_archive_run("2026-11-27", "100000", "x", jid, "f1\n", matches='{"file": "f1", "company": "OLD"}\n',
                      macro='{"file": "f1", "theme": "OLDMACRO"}\n', config=cfg)
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
    def fake_exec(job):
        seen["refresh_threads_running"] = sum(1 for t in threading.enumerate() if t.daemon and t.is_alive())
        return "incomplete" if job["id"] == "inc-1" else None
    worker._execute = fake_exec
    try:
        worker.execute({"id": "inc-1", "job": "gdelt-fetch"})
        worker.execute({"id": "fin-1", "job": "gdelt-fetch"})
    finally:
        worker.BUS, worker._execute, worker.CLAIM_REFRESH_SECONDS = o_bus, o_exec, o_sec
    ls = _git("ls-tree", "-r", "--name-only", "queue", cwd=bare)
    check("incomplete run's bus claim removed from origin/queue", "queue/claims/inc-1.json" not in ls)
    check("finished run keeps the existing completion path (claim untouched here)", "queue/claims/fin-1.json" in ls)
    alive = [t for t in threading.enumerate() if getattr(t, "_target", None) is not None and t._target.__name__ == "refresh" and t.is_alive()]
    check("claim-refresh thread stopped by execute()", not alive)
    check("the refresh thread was running while the job executed", seen["refresh_threads_running"] >= 1)

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
    test_restore_ignores_unpublished_local_residue()
    test_restore_brings_back_predecessor_matches()
    test_master_download_failed_publishes_restored_matches()
    test_unfinished_status_from_filter_output()
    test_execute_releases_bus_claim_for_incomplete_run()
    print("\n%d passed" % PASSED)
    return 0

if __name__ == "__main__":
    sys.exit(main())
