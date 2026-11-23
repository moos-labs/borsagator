#!/usr/bin/env python3
"""Tests for issue #500: scripts/check_relay_envelope.py, the
ledger-publish relay's pre-merge envelope validator.

Against real local git repos (no GitHub, no network):

  - a well-formed envelope on a main base passes, and still
    passes after main gains an UNRELATED (non-ledger) commit —
    base-tip equality would over-reject this; the validator
    must not;
  - the merge-candidate RECHECK refuses the same envelope once
    main carries a NEWER heartbeat (superseded), and still
    passes after an unrelated advance;
  - an envelope built on a commit outside main's history is
    refused (declared base not an ancestor);
  - an envelope changing a path outside ledger/** relative to
    its declared base is refused;
  - an envelope whose heartbeat is older than its base's is
    refused (regressive);
  - a merge-shaped (two-parent) staged commit is refused.

Run: python3 scripts/test_ledger_relay_500.py (exit 0 = pass).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(_HERE))
import check_relay_envelope as validator  # noqa: E402

PASSED = 0

GIT_ENV = dict(os.environ,
               GIT_AUTHOR_NAME="gator-test",
               GIT_AUTHOR_EMAIL="test@borsagator.local",
               GIT_COMMITTER_NAME="gator-test",
               GIT_COMMITTER_EMAIL="test@borsagator.local")


def check(name, cond):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}")
        raise SystemExit(1)


def git(*args, cwd=None, check_rc=True):
    r = subprocess.run(["git"] + list(args), cwd=cwd, env=GIT_ENV,
                       capture_output=True, text=True, timeout=120)
    if check_rc and r.returncode != 0:
        raise AssertionError(f"git {args}: {r.stderr}")
    return r


def write_hb(repo, at, run_id="run-1"):
    p = Path(repo) / "ledger" / "guard-heartbeat.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(
        {"last_run_utc": at, "run_id": run_id, "status": "ok",
         "workflow": "ledger-guard", "note": "test"}, indent=2) + "\n")


def make_repo(base):
    """Bare remote + clone whose main carries a seed heartbeat."""
    remote = base / "remote.git"
    git("init", "--bare", "-b", "main", str(remote))
    repo = base / "repo"
    git("clone", str(remote), str(repo))
    git("-C", str(repo), "config", "user.email",
        "test@borsagator.local")
    git("-C", str(repo), "config", "user.name", "gator-test")
    write_hb(repo, "2026-11-22T08:00:00Z", run_id=None)
    (Path(repo) / "ledger" / "ledger.json").write_text('{"v": 0}\n')
    (Path(repo) / "README.md").write_text("seed\n")
    git("-C", str(repo), "add", ".")
    git("-C", str(repo), "commit", "-m", "seed")
    git("-C", str(repo), "push", "origin", "HEAD:main")
    return remote, repo


def stage_envelope(repo, at, run_id="run-1", ledger_v=1,
                   extra_path=None):
    """Commit an envelope on top of current HEAD; returns its sha
    (HEAD is left on the envelope commit)."""
    write_hb(repo, at, run_id=run_id)
    (Path(repo) / "ledger" / "ledger.json").write_text(
        json.dumps({"v": ledger_v}) + "\n")
    if extra_path:
        p = Path(repo) / extra_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("outside\n")
    git("-C", str(repo), "add", ".")
    git("-C", str(repo), "commit", "-m", f"envelope {run_id}")
    return git("-C", str(repo), "rev-parse", "HEAD").stdout.strip()


def advance_main(repo, at=None, run_id=None, unrelated=False):
    """Commit directly on main (from a clean main checkout)."""
    git("-C", str(repo), "checkout", "-q", "main")
    git("-C", str(repo), "reset", "-q", "--hard", "origin/main")
    if unrelated:
        (Path(repo) / "README.md").write_text(
            (Path(repo) / "README.md").read_text() + "more\n")
    else:
        write_hb(repo, at, run_id=run_id)
        (Path(repo) / "ledger" / "ledger.json").write_text(
            '{"v": 99}\n')
    git("-C", str(repo), "add", ".")
    git("-C", str(repo), "commit", "-m", "advance main")
    git("-C", str(repo), "push", "origin", "HEAD:main")
    git("-C", str(repo), "fetch", "-q", "origin", "main")


def verdict(repo, stage):
    return validator.validate(str(repo), stage, "origin/main")


def test_valid_envelope_and_unrelated_advance():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z")
        git("-C", str(repo), "push", "origin",
            f"HEAD:refs/heads/publish/ledger-run-1")
        v = verdict(repo, stage)
        check("valid: well-formed envelope passes", v["ok"])
        check("valid: declared base is the seed main",
              v["base_sha"] is not None and len(v["base_sha"]) == 40)
        advance_main(repo, unrelated=True)
        v = verdict(repo, stage)
        check("valid: unrelated main advance still passes "
              "(no base-tip over-rejection)", v["ok"])


def test_recheck_superseded_and_unrelated():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z")
        advance_main(repo, unrelated=True)
        check("recheck: unrelated advance passes",
              verdict(repo, stage)["ok"])
        advance_main(repo, at="2026-11-22T10:00:00Z", run_id="run-2")
        v = verdict(repo, stage)
        check("recheck: newer heartbeat on main refuses",
              not v["ok"] and "not strictly newer than main"
              in v["reason"])


def test_foreign_base_refused():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        # A side line that is not in main's history.
        git("-C", str(repo), "checkout", "-q", "--orphan", "side")
        git("-C", str(repo), "rm", "-rf", "-q", ".")
        write_hb(repo, "2026-11-22T07:00:00Z", run_id="side")
        (Path(repo) / "ledger" / "ledger.json").write_text(
            '{"v": 7}\n')
        git("-C", str(repo), "add", ".")
        git("-C", str(repo), "commit", "-m", "side root")
        side_root = git("-C", str(repo), "rev-parse",
                        "HEAD").stdout.strip()
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z",
                               run_id="side-2")
        v = validator.validate(str(repo), stage, "origin/main")
        check("foreign: envelope on a non-main base is refused",
              not v["ok"] and "not an ancestor" in v["reason"])
        check("foreign: declared base is the side root",
              v.get("base_sha") == side_root)


def test_out_of_scope_path_refused():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z",
                               extra_path="scripts/evil.py")
        v = verdict(repo, stage)
        check("scope: change outside ledger/** vs declared base "
              "is refused",
              not v["ok"] and "outside ledger" in v["reason"])


def test_regressive_heartbeat_refused():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T07:00:00Z")
        v = verdict(repo, stage)
        check("regressive: staged heartbeat older than its "
              "base's is refused",
              not v["ok"] and "not strictly newer than its base"
              in v["reason"])


def test_staged_heartbeat_equal_to_base_refused():
    # Staged heartbeat timestamp equal to its declared base's
    # timestamp must be refused (equal-to-base is not strictly newer).
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T08:00:00Z")
        v = verdict(repo, stage)
        check("equal-to-base: staged heartbeat equal to its base's "
              "is refused",
              not v["ok"] and "not strictly newer than its base"
              in v["reason"])


def test_staged_heartbeat_equal_to_main_refused():
    # Staged heartbeat timestamp equal to main's current heartbeat
    # timestamp must be refused: stage built on an older base while
    # main advanced to the same timestamp (not strictly newer than
    # pre-merge main).
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z")
        advance_main(repo, at="2026-11-22T09:00:00Z", run_id="run-2")
        v = verdict(repo, stage)
        check("equal-to-main: staged heartbeat equal to main's "
              "current heartbeat is refused",
              not v["ok"] and "not strictly newer than main"
              in v["reason"])


def test_two_parent_commit_refused():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        git("-C", str(repo), "checkout", "-q", "-b", "stagebr")
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z")
        git("-C", str(repo), "checkout", "-q", "main")
        git("-C", str(repo), "reset", "-q", "--hard", "origin/main")
        git("-C", str(repo), "merge", "-q", "--no-ff", stage,
            "-m", "merge-shaped")
        merged = git("-C", str(repo), "rev-parse",
                     "HEAD").stdout.strip()
        v = verdict(repo, merged)
        check("shape: two-parent staged commit is refused",
              not v["ok"] and "exactly one parent" in v["reason"])


def test_rename_into_ledger_refused():
    # PR #515 review: with rename detection, `git diff
    # --name-only` lists only the destination — renaming a file
    # from OUTSIDE ledger/ into it would hide the out-of-scope
    # deletion. --no-renames exposes both sides.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        write_hb(repo, "2026-11-22T09:00:00Z")
        git("-C", str(repo), "mv", "README.md",
            "ledger/README.md")
        git("-C", str(repo), "add", ".")
        git("-C", str(repo), "commit", "-m", "rename in")
        stage = git("-C", str(repo), "rev-parse",
                    "HEAD").stdout.strip()
        v = verdict(repo, stage)
        check("rename: file renamed INTO ledger/** from outside "
              "is refused (both sides checked)",
              not v["ok"] and "outside ledger" in v["reason"]
              and "README.md" in v["reason"])


def test_nonascii_ledger_path_passes():
    # PR #515 review: git's default path quoting would put a
    # quote before a non-ASCII ledger path and fail the prefix
    # check; -z parsing sees the real path.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        write_hb(repo, "2026-11-22T09:00:00Z")
        p = Path(repo) / "ledger" / "بيانات.json"
        p.write_text('{"v": 5}\n', encoding="utf-8")
        git("-C", str(repo), "add", ".")
        git("-C", str(repo), "commit", "-m", "nonascii envelope")
        stage = git("-C", str(repo), "rev-parse",
                    "HEAD").stdout.strip()
        v = verdict(repo, stage)
        check("paths: non-ASCII path under ledger/** passes "
              "the scope check", v["ok"])


def test_staged_heartbeat_without_timestamp_refused():
    # PR #515 review (092 timestamp fail-closed): a staged
    # heartbeat with no last_run_utc used to skip both ordering
    # checks and be approved.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        p = Path(repo) / "ledger" / "guard-heartbeat.json"
        p.write_text(json.dumps(
            {"run_id": "run-1", "status": "ok",
             "workflow": "ledger-guard"}) + "\n")
        (Path(repo) / "ledger" / "ledger.json").write_text(
            '{"v": 3}\n')
        git("-C", str(repo), "add", ".")
        git("-C", str(repo), "commit", "-m", "no timestamp")
        stage = git("-C", str(repo), "rev-parse",
                    "HEAD").stdout.strip()
        v = verdict(repo, stage)
        check("timestamp: staged heartbeat without last_run_utc "
              "is refused, not silently approved",
              not v["ok"] and "no readable heartbeat timestamp"
              in v["reason"])


def test_staged_heartbeat_deleted_refused():
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        git("-C", str(repo), "rm", "-q",
            "ledger/guard-heartbeat.json")
        (Path(repo) / "ledger" / "ledger.json").write_text(
            '{"v": 4}\n')
        git("-C", str(repo), "add", ".")
        git("-C", str(repo), "commit", "-m", "heartbeat deleted")
        stage = git("-C", str(repo), "rev-parse",
                    "HEAD").stdout.strip()
        v = verdict(repo, stage)
        check("timestamp: envelope deleting the heartbeat is "
              "refused", not v["ok"]
              and "no readable heartbeat timestamp"
              in v["reason"])


def test_malformed_main_timestamp_refused():
    # A baseline heartbeat that exists but cannot be ordered
    # must refuse, not be treated as absent (the freshness
    # check would silently drop).
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z")
        git("-C", str(repo), "checkout", "-q", "main")
        git("-C", str(repo), "reset", "-q", "--hard",
            "origin/main")
        p = Path(repo) / "ledger" / "guard-heartbeat.json"
        p.write_text(json.dumps(
            {"last_run_utc": "not-a-time", "run_id": "x",
             "status": "ok"}) + "\n")
        git("-C", str(repo), "add", ".")
        git("-C", str(repo), "commit", "-m", "malformed main hb")
        git("-C", str(repo), "push", "origin", "HEAD:main")
        git("-C", str(repo), "fetch", "-q", "origin", "main")
        v = verdict(repo, stage)
        check("baseline: malformed heartbeat timestamp on main "
              "refuses validation", not v["ok"]
              and "malformed" in v["reason"])


def test_missing_blob_object_fails_closed():
    # INS-REVIEW-093 counterexample: a tree entry whose blob is
    # missing from the object DB is NOT positively absent. The
    # old cat-file probe exited non-zero for it and the baseline
    # heartbeat was read as absent, so a stale envelope could
    # validate ok:true against a baseline never read. Existence
    # comes from the tree (ls-tree); a listed entry with a
    # missing blob is a lookup error and validation fails closed.
    with tempfile.TemporaryDirectory() as td:
        remote, repo = make_repo(Path(td))
        stage = stage_envelope(repo, "2026-11-22T09:00:00Z")
        base = git("-C", str(repo), "rev-parse",
                   f"{stage}^").stdout.strip()
        blob = git("-C", str(repo), "rev-parse",
                   f"{base}:ledger/guard-heartbeat.json"
                   ).stdout.strip()
        obj = Path(repo) / ".git" / "objects" / blob[:2] / blob[2:]
        check("093: baseline heartbeat blob starts as a loose "
              "object", obj.exists())
        obj.unlink()
        check("093: missing blob object is not positive absence",
              validator.file_exists(str(repo), base,
                                    "ledger/guard-heartbeat.json")
              is not False)
        v = verdict(repo, stage)
        check("093: validation fails closed when the baseline "
              "heartbeat blob is missing",
              not v["ok"] and "cannot be read" in v["reason"])


def test_cli_setup_error_is_exit_2_json():
    # PR #515 review: when git itself cannot run, the CLI
    # prints a JSON verdict and returns the setup-error status
    # 2 — not a traceback the relay misreads as a refusal.
    import contextlib
    import io
    orig_git = validator.git
    orig_argv = sys.argv

    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    validator.git = boom
    sys.argv = ["check_relay_envelope.py", "--stage", "abc"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = validator.main()
    finally:
        validator.git = orig_git
        sys.argv = orig_argv
    verdict_doc = json.loads(buf.getvalue())
    check("cli: git timeout yields exit 2", rc == 2)
    check("cli: git timeout yields a JSON setup_error verdict",
          verdict_doc.get("ok") is False
          and "TimeoutExpired" in verdict_doc.get("setup_error",
                                                  ""))


def main():
    test_valid_envelope_and_unrelated_advance()
    test_recheck_superseded_and_unrelated()
    test_foreign_base_refused()
    test_out_of_scope_path_refused()
    test_regressive_heartbeat_refused()
    test_staged_heartbeat_equal_to_base_refused()
    test_staged_heartbeat_equal_to_main_refused()
    test_two_parent_commit_refused()
    test_rename_into_ledger_refused()
    test_nonascii_ledger_path_passes()
    test_staged_heartbeat_without_timestamp_refused()
    test_staged_heartbeat_deleted_refused()
    test_malformed_main_timestamp_refused()
    test_missing_blob_object_fails_closed()
    test_cli_setup_error_is_exit_2_json()
    print(f"\n{PASSED} checks passed")


if __name__ == "__main__":
    main()
