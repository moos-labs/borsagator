#!/usr/bin/env python3
"""Publish the calibration ledger after a sweep is archived (issue #64).

Runs scripts/ledger.py against the archive branch, validates the run,
and — only when the outputs actually changed — commits ledger/ back to
main, closing the calibration feedback loop with no human step.

A failed or degraded run publishes NOTHING (a degraded ledger.json
with zeroed counts is worse than a stale one). On the sweep path the
failure surfaces as a ⚠️ section in the digest — the issue's hard
requirement: never fail silently. With --fail-hard the failure exits
non-zero instead (the scheduled guard's surface is the failed Actions
run itself). With --fail-push only a failed git push exits non-zero
on the sweep path — a push failure that survives the reset +
recompute retry must fail the step (issue #119 follow-up); other
failures still warn-only unless --fail-hard is also passed.

Issue #127: _git_publish used to swallow git's stderr on every
failure path — `git add` failing logged nothing at all, `git
commit` failing logged only "nothing staged?", and a rejected push
logged a canned "almost always a concurrent ledger publish"
assertion without the push output — so the digest warning named
the wrong cause (any add/commit failure was reported as a push
failure). Every failure path now logs git's actual stderr, and
publish() carries that cause into the digest warning (and into
the retry-path fetch/reset failures). No behaviour change: still
no rebase, still reset + recompute, still a plain fast-forward
push, and a push failure keeps the established "git push of
ledger/ to main failed" digest wording with the push stderr
appended.

Issue #117: ledger.py pins every archive read to the commit sha it
resolves at run start, so the ledger is a self-consistent snapshot
of that commit whatever the branch does mid-run. The publisher
additionally compares the pinned commit against the live archive
HEAD before publishing (the interim check from the #117 triage):
on a mismatch it logs the advance and still publishes the pinned
snapshot — the snapshot is consistent, and the next guard tick
refreshes it for the new tree. Refusing to publish on a benign
advance would fail the guard run for no integrity gain.

Issue #118: the sweep-path ledger step is gated on the archive push
in orchestrate.yml, and the publisher additionally refuses to
publish when the live archive tree does not contain this sweep's
directory (--sweep-target / LEDGER_SWEEP_TARGET): a failed archive
must never produce a ledger that omits the sweep while the digest
claims it is current. On such a refusal the publisher writes a ⚠️
section to the digest and skips the publish — it never fails the
sweep. The guard path passes no target, so it is unaffected.

Issue #119: a timeout or interrupt DURING the rebase used to
propagate out of git_publish with no abort — the checkout was left
MID-REBASE and every later publish failed until manual cleanup.
The rebase is now wrapped so a timeout / interrupt / non-zero exit
all abort it (and the abort itself is checked), publish() verifies
the checkout is clean before any `git add`, and a stale rebase left
by a killed earlier run is aborted at publish start. Dirt confined
to ledger/ (the publisher's own leftovers from a run killed between
copy and commit) is reset to HEAD — the ledger is recomputed from
the archive on every run, so discarding it is safe; dirt anywhere
else is refused loudly instead of publishing into it. No repo-side
serialization was added: the guard and the sweep publisher run on
different runners, so a /tmp lockfile cannot serialize them, and a
lock ref would add a new stale-lock failure mode (a killed run
strands the lock — the exact class this issue eliminates). Concurrent
publishers are serialized through the push itself: only one wins,
and the loser resets to the new main and retries from a fresh pin
(see the follow-up note below) — never by rebasing onto it.

Issue #119 follow-up (live proof run 43889942381): the push-retry
itself was the failure. A rebase can NEVER replay a ledger commit
onto a newer ledger commit — both rewrite the same ledger.json /
ledger.md lines (tree_sha, counts, per-ticker rows), so the rebase
conflicts every time. Reproduced locally: a bb645b6 checkout's
ledger commit rebased onto origin/main at 2d33c27 conflicts on
ledger/ledger.json and ledger/ledger.md. (The same run also refuted
the expired-app-token theory: the ledger push uses the checkout's
persisted GITHUB_TOKEN — actions/checkout's default — never the app
token minted in step 5, which the gator step alone consumes; the
archive push seconds earlier succeeded with that same credential.)
So on a rejected push _git_publish no longer rebases at all:
publish() discards the local commit, resets to origin/main,
recomputes the ledger from a fresh archive pin, and retries once.
Recomputing (not re-copying the first attempt's outputs) matters:
the other run's publish may come from a newer archive tree, and
re-copying the older outputs would regress the ledger. The retry
is still a plain fast-forward push — no force push anywhere. A
push failure that survives the retry fails the step on the sweep
path (--fail-push): run 43889942381's step 11 exited 0 while
publishing nothing, and only the digest warning disclosed it.

Modes:
  sweep path (orchestrate.yml):  ledger_publish.py --digest digest/digest.md --commit --fail-push
  guard path (ledger-guard.yml): ledger_publish.py --commit --fail-hard
  local/dry:                     ledger_publish.py [--digest PATH]

Idempotency: when a rerun produces byte-identical outputs, nothing
is committed. The ledger is revalidated on EVERY run — the old
tree-sha skip trusted the committed ledger blindly for the live
archive tree, which locked in any incomplete ledger published before
issue #116 (a missing sweep was never re-added until the tree moved
again). Revalidation costs one ledger run per guard tick and keeps
that lock-in impossible.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_DIR = os.path.join(ROOT, "ledger")
LEDGER_PY = os.path.join(ROOT, "scripts", "ledger.py")
FILES = ("ledger.json", "ledger.md", "weights.json")
FAMILIES = ("price-forecast", "technicals", "sentiment", "agent",
            "fundamentals")
API_REF = ("https://api.github.com/repos/moos-labs/borsagator/"
           "git/ref/heads/archive")


def log(msg):
    print(f"[ledger-publish] {msg}", flush=True)


def live_archive_commit_sha():
    """HEAD commit sha of the archive branch right now (issue #117
    interim check: compare the ledger's pinned commit against live
    before publishing). Returns None when the API cannot be reached
    — the check is advisory; the pinned ledger is self-consistent
    either way, so an unreachable check never blocks a publish."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {"User-Agent": "borsagator-ledger-publish",
               "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(API_REF, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return (data.get("object") or {}).get("sha")
    except Exception as e:
        log(f"live archive HEAD check failed ({e}) — skipping comparison")
        return None


def live_archive_contains(target):
    """True when this sweep's directory is present on the live archive
    branch (its manifest.json is reachable), False when it is absent,
    None when the check itself could not be performed (issue #118
    belt-and-braces: the workflow gates the sweep-path ledger step
    on the archive push, but if the branch moved on between the push
    and this run, never publish a ledger that omits the sweep while
    claiming to be current). An unreachable check never blocks a
    publish — the pinned snapshot is self-consistent either way,
    mirroring live_archive_commit_sha."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {"User-Agent": "borsagator-ledger-publish",
               "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = ("https://api.github.com/repos/moos-labs/borsagator/contents/"
           f"{target}/manifest.json?ref=archive")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        log(f"archive-contains check failed (HTTP {e.code}) — proceeding")
        return None
    except Exception as e:
        log(f"archive-contains check failed ({e}) — proceeding")
        return None


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def committed_ledger():
    return _read_json(os.path.join(LEDGER_DIR, "ledger.json"))


def validate_ledger(doc):
    """Raise RuntimeError on any degraded ledger document.
    ledger.py itself never exits non-zero — it catches everything
    and still writes zeroed outputs on a fetch failure, so this
    validation is the failure detector. Rejection is on the specific
    failure signal (a gap prefix), never on count monotonicity
    (issue #116)."""
    if not (doc.get("source") or {}).get("tree_sha"):
        raise RuntimeError("degraded run: no archive tree sha "
                           "(the archive fetch failed — see gaps)")
    # Issue #117: a ledger without the pinned commit sha was not
    # computed from a pinned snapshot — reject it.
    if not (doc.get("source") or {}).get("commit_sha"):
        raise RuntimeError("degraded run: no archive commit sha "
                           "(the archive pin was not resolved — see gaps)")
    for g in doc.get("gaps") or []:
        if g.startswith("archive tree could not be fetched"):
            raise RuntimeError(f"degraded run: {g}")
        if g.startswith("per-file fetch failed"):
            raise RuntimeError(f"degraded run: {g}")
    if (doc.get("counts") or {}).get("sweeps", 0) == 0:
        raise RuntimeError("degraded run: zero sweeps read from the "
                           "archive tree")
    return doc


def run_ledger(out_dir):
    """Run scripts/ledger.py into out_dir and validate its output.
    Returns the parsed ledger.json; raises RuntimeError on any
    degraded run."""
    r = subprocess.run([sys.executable, LEDGER_PY, out_dir],
                       capture_output=True, text=True, timeout=1200)
    p = os.path.join(out_dir, "ledger.json")
    if not os.path.exists(p):
        raise RuntimeError("ledger.py wrote no ledger.json "
                           f"(stdout tail: {r.stdout.strip()[-200:]})")
    doc = _read_json(p)
    if doc is None:
        raise RuntimeError("ledger.json is not parseable JSON")
    return validate_ledger(doc)


def _counts_line(doc):
    c = doc["counts"]
    return (f"**{c['forecasts']} forecasts · {c['matured']} matured · "
            f"{c['pending']} pending · {c['invalid']} invalid**")


def _weights_sentence(old_w, new_w):
    if not new_w:
        return ""
    changed, factors = [], (new_w.get("factors") or {})
    old_factors = (old_w or {}).get("factors") or {}
    for fam in FAMILIES:
        nf = (factors.get(fam) or {}).get("factor")
        of = (old_factors.get(fam) or {}).get("factor")
        if nf is not None and of is not None and nf != of:
            changed.append(f"{fam} ×{nf}")
    if changed:
        return " Weights updated: " + ", ".join(changed) + "."
    return " Weights unchanged."


def section_published(old, new, old_w, new_w):
    sha = str(new["source"]["tree_sha"])[:8]
    commit = str(new["source"].get("commit_sha") or "")[:8]
    delta = ""
    if old and old["counts"]["matured"] != new["counts"]["matured"]:
        delta = (f" (matured {old['counts']['matured']} → "
                 f"{new['counts']['matured']})")
    return ("## 📒 Calibration ledger\n\n"
            f"Ledger rerun after this sweep (archive tree `{sha}`, "
            f"commit `{commit}`): "
            f"{_counts_line(new)}{delta}."
            f"{_weights_sentence(old_w, new_w)} "
            "Published to `ledger/` on main; the new weights take "
            "effect from the next sweep.")


def section_unchanged(doc):
    sha = str(doc["source"]["tree_sha"])[:8]
    return ("## 📒 Calibration ledger\n\n"
            f"Ledger already current for archive tree `{sha}`: "
            f"{_counts_line(doc)}. Nothing to publish.")


def section_skipped(target):
    return ("## ⚠️ Calibration ledger\n\n"
            f"⚠️ This sweep (`{target}`) is not in the archive tree on "
            "branch `archive`, so the ledger rerun was skipped — the "
            "committed ledger on main was NOT updated and does not "
            "include this sweep. Treat the published weights as stale "
            "until the next successful rerun.")


def section_failed(reason):
    reason = " ".join(str(reason).split())[:220]
    return ("## ⚠️ Calibration ledger\n\n"
            f"⚠️ The ledger rerun failed ({reason}). The committed "
            "ledger on main was NOT updated — treat the published "
            "weights as stale until the next successful rerun.")


def append_digest(digest_path, section):
    if not digest_path:
        return
    if not os.path.exists(digest_path):
        log(f"digest {digest_path} not found — section not appended")
        return
    with open(digest_path, "a", encoding="utf-8") as f:
        f.write("\n" + section + "\n")
    log(f"digest section appended to {digest_path}")


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args],
                          capture_output=True, text=True, timeout=120)


def _git_dir():
    """Absolute path of this checkout's git dir, or None when git
    cannot tell us (a broken checkout — the callers treat that as
    'no rebase known', never as a reason to publish blind)."""
    r = git("rev-parse", "--git-dir")
    if r.returncode != 0:
        return None
    d = r.stdout.strip()
    return d if os.path.isabs(d) else os.path.join(ROOT, d)


def rebase_in_progress():
    """True when a rebase is mid-flight in this checkout (issue #119:
    a timed-out / interrupted rebase used to strand the checkout
    here, and every later publish failed until manual cleanup)."""
    gd = _git_dir()
    if gd is None:
        return False
    return (os.path.isdir(os.path.join(gd, "rebase-merge")) or
            os.path.isdir(os.path.join(gd, "rebase-apply")))


def abort_rebase():
    """Best-effort `rebase --abort`, only when a rebase is actually
    in progress. Returns True when no rebase remains afterwards.
    The abort's own result is checked and logged — the old code
    fired it and never looked."""
    if not rebase_in_progress():
        return True
    log("aborting in-progress rebase")
    try:
        r = git("rebase", "--abort")
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as e:
        log(f"rebase --abort did not finish ({type(e).__name__}) — "
            "checkout may still be mid-rebase")
        return not rebase_in_progress()
    if r.returncode != 0:
        log(f"rebase --abort failed (rc {r.returncode}): "
            f"{r.stderr.strip()[-200:]}")
    ok = not rebase_in_progress()
    log("rebase aborted — checkout clean" if ok else
        "rebase --abort finished but a rebase is still in progress")
    return ok


def ensure_clean_checkout():
    """Pre-flight check for publish() (issue #119): the checkout
    must have no rebase in progress and no modification to any
    tracked file before `git add` runs. A stale mid-rebase state
    (left by a killed earlier run) is aborted here. Dirt confined
    to ledger/ is the publisher's own leftover from a run killed
    between copying the new outputs and committing them — it is
    reset to HEAD, which is safe because the ledger is recomputed
    from the archive on every run. Dirt anywhere else is refused
    loudly instead of publishing into it. Untracked files
    (digest/, archive_stage/, runner outputs) are expected in the
    sweep checkout and are ignored. Returns (True, '') or
    (False, reason)."""
    if rebase_in_progress():
        log("stale rebase in progress at publish start — aborting it")
        if not abort_rebase():
            return False, ("a rebase is in progress and "
                           "`rebase --abort` did not clear it")
    try:
        r = git("status", "--porcelain")
    except subprocess.TimeoutExpired:
        return False, "git status timed out — refusing to publish blind"
    if r.returncode != 0:
        return False, (f"git status failed (rc {r.returncode}) — "
                       "refusing to publish blind")
    dirty = [line for line in r.stdout.splitlines()
             if line and not line.startswith("??")]
    if not dirty:
        return True, ""
    paths = [line[3:] for line in dirty]
    if all(p == "ledger" or p.startswith("ledger/") for p in paths):
        log("resetting the publisher's own leftover ledger/ changes "
            "to HEAD (a previous run was killed before committing)")
        if git("reset", "-q", "--", "ledger/").returncode != 0 or \
                git("checkout", "-q", "--", "ledger/").returncode != 0:
            return False, ("ledger/ is dirty and the reset to HEAD "
                           "failed — refusing to publish")
        return True, ""
    return False, ("tracked files modified in the working tree: " +
                   ", ".join(paths[:5]))


def git_publish(new_doc):
    """Commit ledger/ and push to main. Returns True on success.
    Issue #119: a timeout / interrupt anywhere in this path must
    never strand the checkout mid-rebase — the wrapper aborts any
    in-progress rebase (e.g. one left by a killed earlier run) and
    returns False. NOTE: this function performs NO rebase itself
    any more (see _git_publish): a rejected push is retried by
    publish(), which resets to origin/main and recomputes.
    Issue #127: a failure's cause is recorded in LAST_GIT_* (see
    _record_git_failure) so publish() can name it in the digest
    instead of asserting a push failure."""
    global LAST_GIT_STAGE, LAST_GIT_DETAIL, LAST_GIT_ERROR
    try:
        return _git_publish(new_doc)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as e:
        LAST_GIT_STAGE = "interrupted"
        LAST_GIT_DETAIL = f"{type(e).__name__} during git publish"
        LAST_GIT_ERROR = ("git publish interrupted/timed out: " +
                          LAST_GIT_DETAIL)
        log("git publish interrupted/timed out — cleaning up")
        abort_rebase()
        return False


# Issue #127: the last _git_publish failure's cause, for publish()
# to carry into the digest warning. _git_publish used to swallow
# git's stderr on every failure path (add: no log at all; commit:
# only "nothing staged?"; push: a canned "almost always a
# concurrent publish" assertion), so a failed publish named the
# wrong cause. Each path now records its stage, the one-line
# stderr summary, and the full log line — cleared at the start of
# every _git_publish call so a later success never carries a
# stale cause.
LAST_GIT_STAGE = ""
LAST_GIT_DETAIL = ""
LAST_GIT_ERROR = ""


def _git_err(r):
    """One-line stderr summary for a failed git call: the last 200
    chars of stderr (stdout when stderr is empty), whitespace
    collapsed. The tail holds the cause for push rejections
    ('error: failed to push some refs ...') and for add/commit
    failures alike."""
    err = (r.stderr or "").strip() or (r.stdout or "").strip()
    if not err:
        return "(no output)"
    return " ".join(err.split())[-200:]


def _record_git_failure(stage, label, r):
    """Record + log one failed git call inside _git_publish."""
    global LAST_GIT_STAGE, LAST_GIT_DETAIL, LAST_GIT_ERROR
    LAST_GIT_STAGE = stage
    LAST_GIT_DETAIL = _git_err(r)
    LAST_GIT_ERROR = (f"{label} failed (rc {r.returncode}): "
                      f"{LAST_GIT_DETAIL}")
    log(LAST_GIT_ERROR)


def _publish_fail_reason(stage, detail, cause):
    """Digest fail reason naming the real cause (issue #127). A
    push failure keeps the established 'git push of ledger/ to
    main failed' wording (test_119 test 10 asserts it) with the
    push stderr appended; any other stage names its stage instead
    of asserting a push failure."""
    if stage == "push":
        return "git push of ledger/ to main failed: " + detail
    if stage:
        return f"ledger publish failed at git {stage}: {detail}"
    return cause or "ledger publish failed"


def _git_publish(new_doc):
    global LAST_GIT_STAGE, LAST_GIT_DETAIL, LAST_GIT_ERROR
    LAST_GIT_STAGE = ""
    LAST_GIT_DETAIL = ""
    LAST_GIT_ERROR = ""
    git("config", "user.name", "borsagator-ledger")
    git("config", "user.email", "moos@sherbeeny.com")
    r = git("add", "ledger/")
    if r.returncode != 0:
        _record_git_failure("add", "git add ledger/", r)
        return False
    c = new_doc["counts"]
    msg = (f"Ledger: tree {str(new_doc['source']['tree_sha'])[:8]} — "
           f"{c['forecasts']} forecasts, {c['matured']} matured, "
           f"{c['pending']} pending, {c['invalid']} invalid (#64)")
    r = git("commit", "-m", msg)
    if r.returncode != 0:
        _record_git_failure("commit", "git commit", r)
        return False
    r = git("push", "origin", "HEAD:main")
    if r.returncode == 0:
        return True
    # Push rejected — the actual stderr logged above IS the cause
    # (a concurrent ledger publish is the common case, but only
    # the push output says so — issue #127). Do NOT rebase here:
    # the other commit rewrote the same ledger.json / ledger.md
    # lines, so a rebase conflicts every time (proven live in run
    # 43889942381 and reproduced locally against 2d33c27).
    # publish() handles the retry: it discards this commit, resets
    # to origin/main, recomputes the ledger from a fresh archive
    # pin, and pushes that.
    _record_git_failure("push", "git push origin HEAD:main", r)
    log("leaving the retry to publish() "
        "(reset to origin/main + recompute, never rebase)")
    return False


def fail(reason, digest_path, fail_hard):
    log(f"FAILED: {reason}")
    append_digest(digest_path, section_failed(reason))
    return 1 if fail_hard else 0


def skip(reason, digest_path, target):
    """Issue #118: the sweep is absent from the live archive tree —
    refuse to publish a stale-as-current ledger. Visible in the
    digest, never a run failure (the sweep path never passes
    --fail-hard, and a skipped ledger must not fail the sweep)."""
    log(f"SKIPPED: {reason}")
    append_digest(digest_path, section_skipped(target))
    return 0


def publish(commit, digest_path, fail_hard, sweep_target=None,
            fail_push=False):
    # Issue #119: verify the checkout is clean BEFORE any `git add`
    # — and fail fast, before the expensive ledger rerun, when a
    # previous killed run left it mid-rebase or dirty.
    clean, why = ensure_clean_checkout()
    if not clean:
        return fail("checkout not clean at publish start: " + why,
                    digest_path, fail_hard)
    # Issue #118: when the sweep path names this sweep's archive
    # directory, refuse to publish unless the live archive tree
    # contains it — otherwise the rerun below would publish a ledger
    # that omits this sweep while the digest claims it is current.
    # No target (guard path, local runs) means no check.
    if sweep_target:
        contains = live_archive_contains(sweep_target)
        if contains is False:
            return skip("archive tree does not contain this sweep "
                        f"({sweep_target})", digest_path, sweep_target)
        if contains:
            log(f"archive tree contains this sweep ({sweep_target})")
    # Issue #119 follow-up: the compute → compare → commit/push
    # cycle runs up to twice. A push rejected on attempt 1 means
    # main moved after this checkout (usually a concurrent ledger
    # publish — the logged stderr is the cause, issue #127); a
    # rebase onto it conflicts on the ledger lines, so instead the local commit is discarded, the checkout
    # is reset to origin/main, and attempt 2 recomputes the ledger
    # from a fresh archive pin — never re-copying attempt 1's
    # outputs, which may predate the other run's tree.
    for attempt in (1, 2):
        old = committed_ledger()
        old_w = _read_json(os.path.join(LEDGER_DIR, "weights.json"))
        # Issue #116: NO tree-sha skip here. The rerun below always
        # revalidates (run_ledger rejects on a per-file fetch failure),
        # and the byte-identical check further down is the only skip —
        # so an incomplete ledger can neither be published nor locked in.
        tmp = tempfile.mkdtemp(prefix="ledger-run-")
        try:
            new = run_ledger(tmp)
        except Exception as e:
            return fail(str(e), digest_path, fail_hard)
        # Issue #117 interim check: compare the pinned commit the ledger
        # was computed from against the live archive HEAD. A mismatch
        # means the branch advanced mid-run — the ledger is still a
        # self-consistent snapshot of its pinned commit, so publish it
        # and let the next guard tick refresh for the new tree.
        live = live_archive_commit_sha()
        pinned = (new.get("source") or {}).get("commit_sha")
        if live and pinned and live != pinned:
            log(f"archive advanced during the run (pinned "
                f"{str(pinned)[:8]}, live {str(live)[:8]}) — publishing "
                "the pinned snapshot; the next guard tick refreshes it")
        elif live and pinned:
            log(f"pinned commit {str(pinned)[:8]} matches live archive HEAD")
        changed = []
        for name in FILES:
            newp, oldp = os.path.join(tmp, name), os.path.join(LEDGER_DIR, name)
            if not os.path.exists(newp):
                return fail(f"ledger.py did not write {name}",
                            digest_path, fail_hard)
            if not os.path.exists(oldp) or \
                    open(newp, "rb").read() != open(oldp, "rb").read():
                changed.append(name)
        if not changed:
            log("rerun produced byte-identical outputs — nothing to publish")
            append_digest(digest_path, section_unchanged(new))
            return 0
        os.makedirs(LEDGER_DIR, exist_ok=True)
        for name in changed:
            shutil.copyfile(os.path.join(tmp, name),
                            os.path.join(LEDGER_DIR, name))
        new_w = _read_json(os.path.join(tmp, "weights.json"))
        log(f"changed: {', '.join(changed)} — {new['counts']}")
        if not commit:
            append_digest(digest_path,
                          section_published(old, new, old_w, new_w))
            return 0
        if git_publish(new):
            append_digest(digest_path,
                          section_published(old, new, old_w, new_w))
            return 0
        # The publish failed — its cause is in LAST_GIT_* (issue
        # #127: never assert "push failed" when the failure was at
        # add/commit, and never drop git's own stderr). Capture the
        # stage/detail now: the fetch/reset below must not
        # overwrite them.
        stage, detail = LAST_GIT_STAGE, LAST_GIT_DETAIL
        cause = LAST_GIT_ERROR or "ledger publish failed (no cause recorded)"
        # One retry, by reset + recompute — never by rebase (see the
        # #119 follow-up note at the top of this file).
        if attempt == 1:
            log("ledger publish failed — " + cause +
                " — resetting to origin/main and recomputing from a "
                "fresh archive pin (attempt 2)")
            try:
                r = git("fetch", "origin", "main")
                if r.returncode != 0:
                    return fail(_publish_fail_reason(stage, detail, cause) +
                                " (and the origin/main fetch for the "
                                "retry failed: " + _git_err(r) + ")",
                                digest_path, fail_hard or fail_push)
                r = git("reset", "--hard", "origin/main")
                if r.returncode != 0:
                    return fail(_publish_fail_reason(stage, detail, cause) +
                                " (and the reset to origin/main for "
                                "the retry failed: " + _git_err(r) + ")",
                                digest_path, fail_hard or fail_push)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                log("interrupted during the push-retry reset — "
                    "cleaning up")
                abort_rebase()
                return fail(_publish_fail_reason(stage, detail, cause) +
                            " (interrupted during the retry reset)",
                            digest_path, fail_hard or fail_push)
            continue
        return fail(_publish_fail_reason(stage, detail, cause),
                    digest_path, fail_hard or fail_push)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--digest", default=None,
                    help="digest markdown file to append the ledger "
                         "section (or ⚠️ failure line) to")
    ap.add_argument("--commit", action="store_true",
                    help="commit + push ledger/ to main when changed")
    ap.add_argument("--fail-hard", action="store_true",
                    help="exit non-zero on failure (guard mode)")
    ap.add_argument("--fail-push", action="store_true",
                    help="exit non-zero when the git push fails "
                         "(sweep path, issue #119 follow-up: a push "
                         "failure that survives the reset + recompute "
                         "retry must fail the step instead of warning "
                         "only in the digest; other failures still "
                         "warn-only unless --fail-hard is also passed)")
    ap.add_argument("--sweep-target", default=None,
                    help="this sweep's archive directory, e.g. "
                         "sweeps/2026-11-16/081500__sweep-lite-poul-ca__run123 "
                         "(issue #118: refuse to publish when the live "
                         "archive tree does not contain it; defaults to "
                         "LEDGER_SWEEP_TARGET)")
    a = ap.parse_args()
    sweep_target = (a.sweep_target or
                    os.environ.get("LEDGER_SWEEP_TARGET") or None)
    if sweep_target:
        sweep_target = sweep_target.strip() or None
    try:
        return publish(a.commit, a.digest, a.fail_hard, sweep_target,
                       a.fail_push)
    except KeyboardInterrupt:
        # Issue #119: an interrupt used to propagate out uncaught
        # (and, mid-rebase, strand the checkout). git_publish
        # already aborts any rebase on its way out; this is the
        # backstop for an interrupt anywhere else in the run.
        log("interrupted — aborting any in-progress rebase")
        abort_rebase()
        return fail("publisher interrupted", a.digest, a.fail_hard)
    except Exception as e:  # the publisher must never crash a sweep
        return fail(f"unexpected publisher error: {e}",
                    a.digest, a.fail_hard)


if __name__ == "__main__":
    sys.exit(main())
