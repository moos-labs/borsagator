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

Issue #128: a failed publish used to leave only a ⚠️ section in the
digest — and digest issues are auto-closed records, so the warning
could vanish from attention while the committed ledger stayed stale.
fail() now also files a durable signal: a dedicated issue labelled
`ledger-failure` (never a digest issue — its title never contains
"Borsagator digest" and it never carries the `digest` label, so
neither the digest watch nor board_sync's digest skip can close or
ignore it). One open signal issue per failure kind: a repeat failure
comments on the existing one instead of filing a duplicate. A later
successful publish closes the publish-failure signal again with a
recovery comment (guard-dead signals are NOT closed here — a current
ledger says nothing about guard liveness; the watchdog in
scripts/ledger_guard_watch.py owns those). All signal calls are
best-effort and never raise: no token (local run) or an API failure
is logged and the digest warning remains the only record.

Issue #128 also: the guard writes a timestamped heartbeat
(ledger/guard-heartbeat.json, see ledger-guard.yml) and the watchdog
notices a dead guard within 2h (90-minute staleness threshold on a
30-minute cadence).

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
(see the follow-up note below) — never by rebasing onto it. The
concurrent publishers are the hourly ledger guard, other sweep runs,
and human commits — NOT board-sync: scripts/board_sync.py makes
GitHub API calls only and never pushes (issue #126 side correction;
an older comment wrongly named board-sync as a pusher).

Issue #126 (panel round 11, follow-up to #119): the #119
token-expiry theory is refuted — the ledger push uses the
checkout's persisted workflow token, never the app token, and the
same job's archive push succeeded minutes before the ledger push
failed. The failure is a race: between a run's checkout and its
ledger push, main gains another ledger commit, the push is rejected
as non-fast-forward, and the rebase conflicts on the same
ledger.json / ledger.md lines. Two changes: (a) the retry below is
now bounded at PUBLISH_MAX_ATTEMPTS attempts with jittered backoff
instead of a single retry — a second overlapping publisher can land
between the first retry's fetch and its push; (b) both workflows
now share a GitHub `concurrency:` group
(`borsagator-ledger-publish`, `cancel-in-progress: false`) so
ledger publishers serialize instead of racing, and the guard cron
is staggered off `:23`. A git-lock action is NOT the fix — the
stale-lock failure mode above is why lock refs stay rejected.

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
recomputes the ledger from a fresh archive pin, and retries —
issue #126 raised the bound from one retry to PUBLISH_MAX_ATTEMPTS
attempts with jittered backoff (see above).
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

Issue #443: main's branch protection requires the `close-gate`
status check, which a commit pushed directly by the worker never
carries — every direct publish was declined by the protected-branch
hook, and the ledger went stale from 2026-11-20. The publisher
therefore grew a staging mode (--publish-branch publish/ledger-<id>):
the same compute / validate / retry cycle, but the commit is pushed
to a per-run staging branch instead of main, and the ledger-publish
relay (.github/workflows/ledger-publish-relay.yml) turns the branch
into a PR, executes the real close-gate on the candidate SHA via
workflow_dispatch, merges it, and only then is the publish landed.
A staged publish is PENDING, not published: the digest section says
so, and the #128 failure signal is NOT cleared here — clearing it
is the relay's job, after a verified merge. The reset + recompute
retry is unchanged, with one staging-only shortcut: a push rejected
because an earlier attempt of this same run already staged the
identical ledger outputs reconciles as staged (idempotent), and a
staging branch that already exists with DIFFERENT ledger content
fails immediately (branch collision) instead of burning retries —
the run id was reused, and no recompute can fix that. With
--guard-heartbeat the staged commit also carries a fresh
ledger/guard-heartbeat.json (status ok, run id from LEDGER_RUN_ID
/ GITHUB_RUN_ID): one guard run produces ONE envelope commit with
the validated outputs plus its heartbeat, or the heartbeat alone
when the outputs are unchanged. A failed run stages nothing here —
the caller (worker / ledger-guard.yml) stages a failed-status
heartbeat-only envelope instead, so invalid ledger data is never
staged. The direct-push mode remains for the sweep path
(orchestrate.yml), unchanged.
"""
import argparse, json, os, random, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request, urllib.parse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_DIR = os.path.join(ROOT, "ledger")
LEDGER_PY = os.path.join(ROOT, "scripts", "ledger.py")
FILES = ("ledger.json", "ledger.md", "weights.json",
         "benchmark.json", "benchmark.md")
FAMILIES = ("price-forecast", "technicals", "sentiment", "agent",
            "fundamentals")
# Issue #79: the fixed benchmark entrant registry (mirrors
# scripts/ledger.py). Class B entrants are "class-b-<slug>".
BENCH_ENTRANTS = ("family-price-forecast", "family-technicals",
                  "family-sentiment", "family-agent",
                  "family-fundamentals", "kronos-alone",
                  "raw-llm-cohere", "buy-and-hold")
ORG = "moos-labs"
REPO = "borsagator"
API_REF = ("https://api.github.com/repos/moos-labs/borsagator/"
           "git/ref/heads/archive")

# Issue #126: bounded recompute-and-retry. At most this many publish
# attempts in total (first try + retries). The ledger is fully
# derived from the archive, so discarding the local commit, resetting
# to the new main and recomputing from a fresh pin is always safe —
# but the bound keeps a pathological contention storm from looping
# forever. Two attempts (the #119 follow-up) proved too few: a second
# overlapping publisher can land between the first retry's fetch and
# its push, and the loser then had no attempt left.
PUBLISH_MAX_ATTEMPTS = 3
# Jittered backoff between retries (seconds): the delay grows with
# the attempt number so two losers of the same race do not retry in
# lockstep and collide again. Kept as module constants so tests can
# zero them (no sleeping in the harness).
RETRY_DELAY_BASE_S = 2.0
RETRY_DELAY_JITTER_S = 4.0


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


def validate_ledger(doc, committed=None):
    """Raise RuntimeError on any degraded ledger document.
    ledger.py itself never exits non-zero — it catches everything
    and still writes zeroed outputs on a fetch failure, so this
    validation is the failure detector. Rejection is on the specific
    failure signal (a gap prefix) or on a sharp regression versus
    the committed ledger — never on plain count monotonicity
    (issue #116). `committed` is the ledger.json currently on main
    (None on a first publish); the regression check is skipped
    without one.
    Issue #132: the gate used to check exactly five conditions and
    never inspected forecasts_detail[].status (scoring exceptions
    produce "error" rows) nor compared counts.matured against the
    committed ledger — so a total CSV-fetch failure, which wipes
    every matured forecast back to zero and resets all weights to
    neutral, published as long as sweeps > 0 and no rejecting gap
    prefix existed."""
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
        # Issue #132: no price series could be built at all (the
        # archive held candidate CSVs but none could be read) —
        # the ledger below carries no realized data whatsoever.
        # Note the `price-CSV fetch failed` prefix is deliberately
        # NOT rejected here: a single failed CSV among many
        # candidates still publishes.
        if g.startswith("no price series could be built"):
            raise RuntimeError(f"degraded run: {g}")
    if (doc.get("counts") or {}).get("sweeps", 0) == 0:
        raise RuntimeError("degraded run: zero sweeps read from the "
                           "archive tree")
    # Issue #132: a scoring exception leaves a forecasts_detail row
    # with status "error" — a ledger that could not score a
    # forecast must not publish as if it had.
    errors = [r for r in doc.get("forecasts_detail") or []
              if r.get("status") == "error"]
    if errors:
        shown = "; ".join(
            f"{r.get('ticker')} as of {r.get('as_of')} "
            f"({r.get('horizon')}) from {r.get('sweep')}: "
            f"{str(r.get('error'))[:120]}" for r in errors[:3])
        raise RuntimeError(
            f"degraded run: {len(errors)} forecast row(s) failed to "
            f"score (status 'error'): {shown}")
    # Issue #132: sharp matured regression versus the committed
    # ledger. Matured counts can legitimately dip a little (a guard
    # change invalidating a few rows), so — per issue #116, which
    # ruled out absolute count-monotonicity rejection — only a
    # collapse of more than half the committed matured set rejects.
    # The total-failure mode is 9 → 0; a 9 → 8 dip still publishes.
    if committed is not None:
        old_matured = (committed.get("counts") or {}).get("matured")
        new_matured = (doc.get("counts") or {}).get("matured", 0)
        if (isinstance(old_matured, int) and old_matured > 0
                and new_matured < old_matured / 2):
            raise RuntimeError(
                f"degraded run: matured forecasts collapsed "
                f"{old_matured} → {new_matured} versus the committed "
                "ledger — a sharp regression, not a dip (see gaps)")
    return doc


def validate_benchmark(doc, committed=None):
    """Raise RuntimeError on any degraded benchmark document (issue
    #79 F12). `committed` is the benchmark.json currently on main
    (None on a first publish). Checks: parseable JSON with the
    benchmark-ledger tool marker; no malformed-file gap (ledger.py
    records one when a frozen entrant file could not be validated);
    no row with status 'error'; every row entrant in the registry
    (or a class-b-<slug> entrant); per-(entrant, horizon) matured
    counts NEVER decrease vs the committed benchmark (monotone, same
    spirit as the #132 matured-regression guard — a decrease rejects
    the run). The 'ensemble' reference row in by_entrant is exempt
    from the monotone check: it mirrors the ensemble ledger, whose
    own regression rule is the #132 collapse check, and its skill
    count can dip when a row is newly gap-flagged."""
    if doc is None:
        raise RuntimeError("degraded run: benchmark.json is not "
                           "parseable JSON")
    if doc.get("tool") != "benchmark-ledger":
        raise RuntimeError("degraded run: benchmark.json is not a "
                           "benchmark-ledger document")
    for g in doc.get("gaps") or []:
        if g.startswith("benchmark file malformed"):
            raise RuntimeError(f"degraded run: {g}")
    errors = [r for r in doc.get("rows") or []
              if r.get("status") == "error"]
    if errors:
        shown = "; ".join(
            f"{r.get('entrant')} {r.get('ticker')} as of "
            f"{r.get('as_of')} ({r.get('horizon')}) from "
            f"{r.get('sweep')}: {str(r.get('error'))[:120]}"
            for r in errors[:3])
        raise RuntimeError(
            f"degraded run: {len(errors)} benchmark row(s) failed to "
            f"score (status 'error'): {shown}")
    for r in doc.get("rows") or []:
        ent = r.get("entrant")
        if ent and ent not in BENCH_ENTRANTS \
                and not ent.startswith("class-b-"):
            raise RuntimeError(
                f"degraded run: benchmark row entrant {ent!r} not in "
                f"the registry (issue #79)")
    if committed is not None:
        old_by = committed.get("by_entrant") or {}
        for ent, horizons in (doc.get("by_entrant") or {}).items():
            if ent == "ensemble":
                continue
            for h, a in (horizons or {}).items():
                old_n = ((old_by.get(ent) or {}).get(h) or {}).get("n")
                new_n = (a or {}).get("n", 0)
                if (isinstance(old_n, int) and isinstance(new_n, int)
                        and new_n < old_n):
                    raise RuntimeError(
                        f"degraded run: benchmark matured count "
                        f"regressed for {ent}/{h} ({old_n} → {new_n}) "
                        f"versus the committed benchmark — a decrease "
                        f"rejects the run (issue #79)")
    return doc


def run_ledger(out_dir, committed=None):
    """Run scripts/ledger.py into out_dir and validate its output.
    Returns the parsed ledger.json; raises RuntimeError on any
    degraded run. `committed` is the ledger currently on main, for
    the issue-#132 regression checks in validate_ledger."""
    r = subprocess.run([sys.executable, LEDGER_PY, out_dir],
                       capture_output=True, text=True, timeout=1200)
    p = os.path.join(out_dir, "ledger.json")
    if not os.path.exists(p):
        raise RuntimeError("ledger.py wrote no ledger.json "
                           f"(stdout tail: {r.stdout.strip()[-200:]})")
    doc = _read_json(p)
    if doc is None:
        raise RuntimeError("ledger.json is not parseable JSON")
    validate_ledger(doc, committed)
    # Issue #79: the benchmark table rides the same run — validate
    # it the same way (missing / unparseable / degraded rejects).
    bp = os.path.join(out_dir, "benchmark.json")
    if not os.path.exists(bp):
        raise RuntimeError("ledger.py wrote no benchmark.json")
    bench = _read_json(bp)
    validate_benchmark(
        bench, _read_json(os.path.join(LEDGER_DIR, "benchmark.json")))
    return doc


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


def section_published(old, new, old_w, new_w, bench=None):
    sha = str(new["source"]["tree_sha"])[:8]
    commit = str(new["source"].get("commit_sha") or "")[:8]
    delta = ""
    if old and old["counts"]["matured"] != new["counts"]["matured"]:
        delta = (f" (matured {old['counts']['matured']} → "
                 f"{new['counts']['matured']})")
    bench_line = ""
    if bench is not None:
        bc = (bench.get("counts") or {})
        bench_line = (f" Benchmark: {bc.get('entrant_rows', 0)} entrant "
                      f"rows, {bc.get('matured', 0)} matured "
                      f"({bc.get('sweeps_with_freeze', 0)} sweeps with a "
                      f"freeze).")
    return ("## 📒 Calibration ledger\n\n"
            f"Ledger rerun after this sweep (archive tree `{sha}`, "
            f"commit `{commit}`): "
            f"{_counts_line(new)}{delta}."
            f"{_weights_sentence(old_w, new_w)}{bench_line} "
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


def section_staged(new, branch):
    """Issue #443: the staging-mode digest section. Staged is
    PENDING, not published — the words must not claim the ledger
    is on main before the relay's verified merge."""
    sha = str(new["source"]["tree_sha"])[:8]
    commit = str(new["source"].get("commit_sha") or "")[:8]
    return ("## 📒 Calibration ledger\n\n"
            f"Ledger rerun (archive tree `{sha}`, commit `{commit}`): "
            f"{_counts_line(new)}. The update is staged on branch "
            f"`{branch}` for PR-based publication to `main` — it is "
            "PENDING the ledger-publish relay merge and is not on "
            "main yet; the new weights take effect once the relay "
            "lands it.")


def guard_heartbeat_doc():
    """The guard heartbeat document for a staged envelope (issue
    #443; the file itself is issue #128's). Written into the staged
    commit when --guard-heartbeat is passed, so one guard run
    produces one envelope: validated ledger outputs + this
    heartbeat, or the heartbeat alone when the outputs are
    unchanged. Status is "ok" by construction — this is only
    written on the success path, just before the commit; a failed
    run's failed-status heartbeat is staged by the caller instead.
    The run id comes from LEDGER_RUN_ID (the worker passes its job
    id; ledger-guard.yml passes its run id) and falls back to
    GITHUB_RUN_ID. It is a string on this path (the Actions
    heartbeat step used to write an int; the watchdog reads only
    last_run_utc + status, and the worker compares run ids as
    strings)."""
    run_id = os.environ.get("LEDGER_RUN_ID") or \
        os.environ.get("GITHUB_RUN_ID") or None
    return {
        "last_run_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "status": "ok",
        "workflow": "ledger-guard",
        "note": ("Written by every completed ledger-guard run; the "
                 "watchdog (ledger-guard-watchdog.yml) pages when "
                 "this is older than 90 minutes."),
    }


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


def git_publish(new_doc, branch=None):
    """Commit ledger/ and push it — to main, or (issue #443
    staging mode) to the per-run branch `branch`. Returns True on
    success (in staging mode: staged, which is PENDING, not
    published). Issue #119: a timeout / interrupt anywhere in this
    path must never strand the checkout mid-rebase — the wrapper
    aborts any in-progress rebase (e.g. one left by a killed
    earlier run) and returns False. NOTE: this function performs
    NO rebase itself any more (see _git_publish): a rejected push
    is retried by publish(), which resets to origin/main and
    recomputes. Issue #127: a failure's cause is recorded in
    LAST_GIT_* (see _record_git_failure) so publish() can name it
    in the digest instead of asserting a push failure."""
    global LAST_GIT_STAGE, LAST_GIT_DETAIL, LAST_GIT_ERROR
    try:
        return _git_publish(new_doc, branch)
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
    if stage == "push-staging":
        return "git push of ledger/ to the staging branch failed: " \
            + detail
    if stage == "branch-collision":
        return ("ledger publish failed: the staging branch already "
                "exists with different ledger content (the run id "
                "was reused): " + detail)
    if stage:
        return f"ledger publish failed at git {stage}: {detail}"
    return cause or "ledger publish failed"


def _remote_branch_sha(branch):
    """HEAD sha of refs/heads/<branch> on origin, or None when the
    branch does not exist (or cannot be read). Issue #443: the
    staging-mode push uses this to tell a fresh branch apart from
    an earlier attempt's envelope."""
    r = git("ls-remote", "origin", f"refs/heads/{branch}")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.split()[0]


def _staged_tree_matches(branch):
    """True when origin's staging branch already carries exactly
    this checkout's HEAD ledger outputs (issue #443 idempotency:
    an earlier attempt of this same run staged the identical
    envelope and then died before reporting — reconcile as
    staged, never duplicate, never treat as a failure). The
    guard heartbeat is deliberately NOT compared: it is
    rewritten with a fresh timestamp on every attempt, so it can
    never match — the envelope's identity is the ledger outputs
    (FILES). A file missing on both sides counts as matching;
    missing on exactly one side does not."""
    r = git("fetch", "origin",
            f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    if r.returncode != 0:
        return False
    for name in FILES:
        a = git("rev-parse", f"HEAD:ledger/{name}")
        b = git("rev-parse",
                f"refs/remotes/origin/{branch}:ledger/{name}")
        if (a.returncode == 0) != (b.returncode == 0):
            return False
        if a.returncode == 0 and \
                a.stdout.strip() != b.stdout.strip():
            return False
    return True


def _git_publish(new_doc, branch=None):
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
    if branch is None:
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
    # Issue #443 staging mode: the push CREATES the per-run
    # branch — it never updates one. A fresh branch accepts the
    # push outright (main moving underneath cannot reject it; the
    # relay merges the branch, divergence is the merge's
    # business). If the branch already exists, this run's envelope
    # is either already there (identical ledger outputs: reconcile
    # as staged) or the run id was reused with different content
    # (a collision no recompute can fix — publish() fails it
    # immediately, no retry). The existence check comes FIRST: a
    # checkout still holding an earlier staged commit could
    # otherwise fast-forward different outputs onto the existing
    # branch and skip collision detection entirely (review
    # finding on #491).
    if _remote_branch_sha(branch) is not None:
        if _staged_tree_matches(branch):
            log(f"staging branch {branch} already carries these "
                "exact ledger outputs — an earlier attempt staged "
                "them; treating as staged (idempotent)")
            return True
        _record_git_failure(
            "branch-collision",
            f"git push origin HEAD:refs/heads/{branch}",
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="",
                stderr="the staging branch already exists with "
                       "different ledger content (run id reused)"))
        return False
    r = git("push", "origin", f"HEAD:refs/heads/{branch}")
    if r.returncode == 0:
        return True
    # The push was rejected: either the branch appeared between
    # the check and the push (a creation race — reconcile by
    # content, exactly as above), or the push itself failed
    # (auth, network) and publish()'s retry owns it.
    if _staged_tree_matches(branch):
        log(f"staging branch {branch} already carries these exact "
            "ledger outputs — an earlier attempt staged them; "
            "treating as staged (idempotent)")
        return True
    if _remote_branch_sha(branch) is not None:
        _record_git_failure(
            "branch-collision",
            f"git push origin HEAD:refs/heads/{branch}", r)
        return False
    _record_git_failure(
        "push-staging",
        f"git push origin HEAD:refs/heads/{branch}", r)
    log("leaving the retry to publish() "
        "(reset to origin/main + recompute, never rebase)")
    return False


def fail(reason, digest_path, fail_hard, signal_ctx=None):
    log(f"FAILED: {reason}")
    append_digest(digest_path, section_failed(reason))
    # Issue #128: the digest warning alone can vanish when the digest
    # issue is auto-closed — file the durable signal too.
    file_failure_signal(reason, signal_ctx)
    return 1 if fail_hard else 0


def skip(reason, digest_path, target):
    """Issue #118: the sweep is absent from the live archive tree —
    refuse to publish a stale-as-current ledger. Visible in the
    digest, never a run failure (the sweep path never passes
    --fail-hard, and a skipped ledger must not fail the sweep)."""
    log(f"SKIPPED: {reason}")
    append_digest(digest_path, section_skipped(target))
    return 0


# ---------------------------------------------------------------------------
# Issue #128 — durable failure signal (shared with the watchdog in
# scripts/ledger_guard_watch.py, which imports these helpers).
#
# The signal is a dedicated issue labelled `ledger-failure`. It is
# never a digest issue: its title never contains "Borsagator digest"
# and it never carries the `digest` label, so the digest watch (which
# closes digest issues after reporting) and board_sync.is_digest
# (which skips digest issues entirely) can neither close it nor
# ignore it. Dedup is by label + title prefix, one open issue per
# failure kind: a repeat failure comments on the open issue instead
# of filing a duplicate, and a verified recovery closes it again.
# Every function here is best-effort and never raises — the signal
# must never break a sweep or a guard run.
# ---------------------------------------------------------------------------
SIGNAL_LABEL = "ledger-failure"
SIGNAL_LABEL_COLOR = "B60205"
SIGNAL_LABEL_DESC = ("Ledger publish failed — durable signal, not "
                     "auto-closed (issue #128)")
PUBLISH_TITLE_PREFIX = "⚠️ Ledger publish failed"


def _gh_token():
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _api_base():
    # GITHUB_API_URL is the standard override (gh CLI / Actions use
    # it too); the harness points it at a local stub server.
    return os.environ.get("GITHUB_API_URL",
                          "https://api.github.com").rstrip("/")


def gh_api(method, path, body=None, token=None):
    """One GitHub REST call. Returns (status, parsed_json_or_None).
    HTTP errors come back as their status (never raised); transport
    errors raise and are caught by the callers."""
    token = token or _gh_token()
    headers = {"User-Agent": "borsagator-ledger-publish",
               "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(_api_base() + path, method=method,
                                 data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw.decode())
                              if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw.decode()) if raw else None
        except Exception:
            parsed = None
        return e.code, parsed


def ensure_signal_label(token):
    """Create the `ledger-failure` label if it does not exist yet.
    Returns True when the label exists afterwards (or the check
    could not tell — the issue create below is the real test)."""
    status, _ = gh_api("GET", f"/repos/{ORG}/{REPO}/labels/"
                              f"{SIGNAL_LABEL}", token=token)
    if status == 200:
        return True
    if status != 404:
        log(f"signal label check failed (HTTP {status}) — proceeding")
        return True
    status, _ = gh_api("POST", f"/repos/{ORG}/{REPO}/labels",
                       {"name": SIGNAL_LABEL, "color": SIGNAL_LABEL_COLOR,
                        "description": SIGNAL_LABEL_DESC}, token=token)
    if status in (200, 201):
        log(f"signal label '{SIGNAL_LABEL}' created")
        return True
    log(f"signal label creation failed (HTTP {status}) — proceeding")
    return True


def find_open_signal_issues(token, title_prefix):
    """Open issues carrying the signal label whose title starts with
    title_prefix (one failure kind per prefix). Returns a list of
    issue dicts (number, title), most recently updated first, or []
    when the search fails — callers treat [] as 'none found'."""
    q = urllib.parse.quote(f"repo:{ORG}/{REPO} label:{SIGNAL_LABEL} "
                           f"state:open", safe="")
    status, data = gh_api("GET", f"/search/issues?q={q}&per_page=20",
                          token=token)
    if status != 200 or not isinstance(data, dict):
        log(f"signal issue search failed (HTTP {status}) — assuming none")
        return []
    return [it for it in data.get("items", [])
            if (it.get("title") or "").startswith(title_prefix)]


def _comment_issue(token, number, body):
    status, _ = gh_api(
        "POST", f"/repos/{ORG}/{REPO}/issues/{number}/comments",
        {"body": body}, token=token)
    return status in (200, 201)


def _create_issue(token, title, body):
    status, data = gh_api("POST", f"/repos/{ORG}/{REPO}/issues",
                          {"title": title, "body": body,
                           "labels": [SIGNAL_LABEL]}, token=token)
    if status in (200, 201) and isinstance(data, dict):
        return data.get("number")
    log(f"signal issue creation failed (HTTP {status})")
    return None


def _close_issue(token, number, comment=None):
    if comment:
        _comment_issue(token, number, comment)
    status, _ = gh_api("PATCH", f"/repos/{ORG}/{REPO}/issues/{number}",
                       {"state": "closed", "state_reason": "completed"},
                       token=token)
    return status == 200


def _signal_context(sweep_target=None):
    """Run/sweep facts for a signal body, from the Actions env (or
    empty strings on a local run — the body then says 'local run')."""
    run_id = os.environ.get("GITHUB_RUN_ID") or ""
    server = os.environ.get("GITHUB_SERVER_URL",
                            "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", f"{ORG}/{REPO}")
    run_url = (f"{server}/{repo}/actions/runs/{run_id}"
               if run_id else "")
    return {"run_id": run_id, "run_url": run_url,
            "sweep_target": sweep_target or "",
            "seen_utc": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC")}


def _run_line(ctx):
    return ctx.get("run_url") or (f"run {ctx['run_id']}"
                                  if ctx.get("run_id") else "local run")


def publish_failure_title_body(reason, ctx=None):
    ctx = ctx or {}
    reason = " ".join(str(reason).split())[:220]
    sweep = ctx.get("sweep_target") or "— (guard path: no single sweep)"
    body = (f"⚠️ The calibration ledger publish failed, and the "
            f"committed ledger on `main` was NOT updated — treat the "
            f"published weights as stale until a later publish "
            f"succeeds.\n\n"
            f"**Cause:** {reason}\n"
            f"**Run:** {_run_line(ctx)}\n"
            f"**Sweep:** `{sweep}`\n"
            f"**First seen:** {ctx.get('seen_utc', '')}\n\n"
            "This issue is the durable signal for #128. It is NOT a "
            "digest issue: the digest watch only closes digest issues, "
            "and board-sync only skips digest issues — this one stays "
            "open until the ledger is publishing again. A later "
            "successful publish closes it automatically with a "
            "recovery comment.\n\n"
            # WSJF 6.0 is the board's auto-promote threshold: a stale
            # ledger feeds wrong weights into the next sweep, so this
            # is live-correctness work, not backlog.
            "WSJF: 6.0")
    return PUBLISH_TITLE_PREFIX + " — " + reason[:80], body


def _recurrence_comment(reason, ctx=None):
    ctx = ctx or {}
    return (f"⚠️ Ledger publish failed again "
            f"({ctx.get('seen_utc', '')}).\n\n"
            f"**Cause:** {' '.join(str(reason).split())[:220]}\n"
            f"**Run:** {_run_line(ctx)}\n\n"
            "The committed ledger on `main` is still not updated.")


def _recovery_comment(ctx=None):
    ctx = ctx or {}
    counts = ctx.get("counts") or ""
    return (f"✅ Ledger published successfully{counts}. The committed "
            f"ledger on `main` is current again — closing this "
            f"failure signal.")


def file_failure_signal(reason, ctx=None):
    """File (or comment on) the durable publish-failure signal.
    Returns True when a signal issue was created or commented on.
    Best-effort: no token or any API failure is logged, never raised
    — the digest warning remains the only record then."""
    token = _gh_token()
    if not token:
        log("no GH_TOKEN — durable ledger-failure signal not filed "
            "(local run?)")
        return False
    try:
        ensure_signal_label(token)
        existing = find_open_signal_issues(token, PUBLISH_TITLE_PREFIX)
        if existing:
            number = existing[0]["number"]
            if _comment_issue(token, number,
                              _recurrence_comment(reason, ctx)):
                log(f"durable signal: recurrence noted on open issue "
                    f"#{number}")
                return True
            return False
        title, body = publish_failure_title_body(reason, ctx)
        number = _create_issue(token, title, body)
        if number:
            log(f"durable signal: ledger-failure issue #{number} filed")
            return True
        return False
    except Exception as e:
        log(f"durable signal: filing failed ({e}) — digest warning only")
        return False


def clear_failure_signal(ctx=None):
    """Close any open publish-failure signal issue after a verified
    successful publish. Guard-dead issues are NOT touched — a current
    ledger says nothing about guard liveness; the watchdog owns
    those. Best-effort, never raises. Returns True when at least one
    issue was closed."""
    token = _gh_token()
    if not token:
        return False
    try:
        existing = find_open_signal_issues(token, PUBLISH_TITLE_PREFIX)
        closed_any = False
        for it in existing:
            if _close_issue(token, it["number"],
                            _recovery_comment(ctx)):
                log(f"durable signal: closed ledger-failure issue "
                    f"#{it['number']} (ledger current again)")
                closed_any = True
        return closed_any
    except Exception as e:
        log(f"durable signal: clearing failed ({e})")
        return False


def publish(commit, digest_path, fail_hard, sweep_target=None,
            fail_push=False, publish_branch=None,
            guard_heartbeat=False):
    # Issue #443: publish_branch selects staging mode — the commit
    # is pushed to that per-run branch (PENDING the relay merge),
    # never directly to main, and the #128 failure signal is not
    # cleared from here (the relay clears/comments it after a
    # verified merge). guard_heartbeat adds the run's heartbeat to
    # the staged commit (see guard_heartbeat_doc).
    # Issue #119: verify the checkout is clean BEFORE any `git add`
    # — and fail fast, before the expensive ledger rerun, when a
    # previous killed run left it mid-rebase or dirty.
    # Issue #128: the signal context travels with every fail() below
    # so the durable signal names the run and the sweep.
    ctx = _signal_context(sweep_target)
    clean, why = ensure_clean_checkout()
    if not clean:
        return fail("checkout not clean at publish start: " + why,
                    digest_path, fail_hard, ctx)
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
    # Issue #119 follow-up, extended by issue #126: the compute →
    # compare → commit/push cycle runs up to PUBLISH_MAX_ATTEMPTS
    # times. A push rejected on an attempt means main moved after
    # this checkout (usually a concurrent ledger publish — the
    # logged stderr is the cause, issue #127); a rebase onto it
    # conflicts on the ledger lines, so instead the local commit is
    # discarded, the checkout is reset to origin/main, and the next
    # attempt recomputes the ledger from a fresh archive pin —
    # never re-copying an earlier attempt's outputs, which may
    # predate the other run's tree.
    for attempt in range(1, PUBLISH_MAX_ATTEMPTS + 1):
        old = committed_ledger()
        old_w = _read_json(os.path.join(LEDGER_DIR, "weights.json"))
        # Issue #116: NO tree-sha skip here. The rerun below always
        # revalidates (run_ledger rejects on a per-file fetch failure),
        # and the byte-identical check further down is the only skip —
        # so an incomplete ledger can neither be published nor locked in.
        # Issue #394: the attempt tempdir is owned by this
        # `with` — it is removed on every exit path
        # (success, fail, retry, exception, interrupt),
        # never leaked onto the worker disk.
        with tempfile.TemporaryDirectory(prefix="ledger-run-") as tmp:
            try:
                # Issue #132: pass the committed ledger in so
                # validate_ledger can reject a sharp matured regression
                # (and error rows) instead of publishing a wiped ledger.
                new = run_ledger(tmp, old)
            except Exception as e:
                return fail(str(e), digest_path, fail_hard, ctx)
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
                                digest_path, fail_hard, ctx)
                if not os.path.exists(oldp) or \
                        open(newp, "rb").read() != open(oldp, "rb").read():
                    changed.append(name)
            # Issue #443: the guard envelope. The heartbeat is
            # written into ledger/ BEFORE the change decision, on
            # every attempt (a retry's reset --hard wipes it, so it
            # is rewritten here, inside the loop): with it, a run
            # whose outputs are unchanged still produces the
            # heartbeat-only envelope commit. Its freshness (a new
            # timestamp every run) is what makes the envelope
            # differ from main's committed heartbeat.
            hb_changed = False
            if guard_heartbeat:
                os.makedirs(LEDGER_DIR, exist_ok=True)
                hb_path = os.path.join(LEDGER_DIR,
                                       "guard-heartbeat.json")
                hb_bytes = (json.dumps(guard_heartbeat_doc(),
                                       indent=2) + "\n").encode()
                old_hb = None
                if os.path.exists(hb_path):
                    with open(hb_path, "rb") as f:
                        old_hb = f.read()
                if old_hb != hb_bytes:
                    with open(hb_path, "wb") as f:
                        f.write(hb_bytes)
                    hb_changed = True
            if not changed and not hb_changed:
                log("rerun produced byte-identical outputs — nothing to publish")
                append_digest(digest_path, section_unchanged(new))
                # Issue #128: the ledger is verified current — a recovery
                # closes any open publish-failure signal. Issue #443:
                # in staging mode the signal lifecycle belongs to the
                # relay (it comments the recovery evidence after a
                # verified merge) — never clear it from here.
                if publish_branch is None:
                    ctx["counts"] = (f" ({new['counts']['forecasts']} forecasts, "
                                     f"{new['counts']['matured']} matured)")
                    clear_failure_signal(ctx)
                return 0
            os.makedirs(LEDGER_DIR, exist_ok=True)
            for name in changed:
                shutil.copyfile(os.path.join(tmp, name),
                                os.path.join(LEDGER_DIR, name))
            new_w = _read_json(os.path.join(tmp, "weights.json"))
            # Issue #79: the benchmark table rides the same publish —
            # its counts line travels in the digest section (counts
            # only, no claims).
            new_bench = _read_json(os.path.join(tmp, "benchmark.json"))
            log(f"changed: {', '.join(changed)} — {new['counts']}")
            if not commit:
                append_digest(digest_path,
                              section_published(old, new, old_w, new_w,
                                                new_bench))
                return 0
            # Direct mode keeps the historical one-argument call
            # shape: the #394 regression harness stubs git_publish
            # with a one-argument replacement.
            if publish_branch is not None:
                published = git_publish(new, publish_branch)
            else:
                published = git_publish(new)
            if published:
                if publish_branch is not None:
                    # Issue #443: staged is PENDING, not published.
                    # No digest "published" claim, no signal clear —
                    # the relay owns completion (verified merge,
                    # then the recovery evidence comment).
                    log(f"staged on {publish_branch} — PENDING the "
                        "ledger-publish relay merge; the ledger is "
                        "not on main yet")
                    append_digest(digest_path,
                                  section_staged(new, publish_branch))
                    return 0
                append_digest(digest_path,
                              section_published(old, new, old_w, new_w,
                                                new_bench))
                # Issue #128: verified publish — close any open
                # publish-failure signal with a recovery comment.
                ctx["counts"] = (f" ({new['counts']['forecasts']} forecasts, "
                                 f"{new['counts']['matured']} matured)")
                clear_failure_signal(ctx)
                return 0
            # The publish failed — its cause is in LAST_GIT_* (issue
            # #127: never assert "push failed" when the failure was at
            # add/commit, and never drop git's own stderr). Capture the
            # stage/detail now: the fetch/reset below must not
            # overwrite them.
            stage, detail = LAST_GIT_STAGE, LAST_GIT_DETAIL
            cause = LAST_GIT_ERROR or "ledger publish failed (no cause recorded)"
            # Issue #443: a staging branch collision (the run id
            # was reused with different ledger content) cannot be
            # fixed by recomputing — the recomputed commit would
            # collide with the same branch again. Fail it now
            # instead of burning the remaining attempts.
            if publish_branch is not None and \
                    stage == "branch-collision":
                return fail(_publish_fail_reason(stage, detail, cause),
                            digest_path, fail_hard or fail_push, ctx)
            # Retry, by reset + recompute — never by rebase (see the
            # #119 follow-up note at the top of this file). Issue #126:
            # bounded at PUBLISH_MAX_ATTEMPTS attempts with a jittered
            # backoff between them, so a second overlapping publisher
            # landing mid-retry does not exhaust the attempts.
            if attempt < PUBLISH_MAX_ATTEMPTS:
                log("ledger publish failed — " + cause +
                    " — resetting to origin/main and recomputing from a "
                    f"fresh archive pin (attempt {attempt + 1} of "
                    f"{PUBLISH_MAX_ATTEMPTS})")
                try:
                    r = git("fetch", "origin", "main")
                    if r.returncode != 0:
                        return fail(_publish_fail_reason(stage, detail, cause) +
                                    " (and the origin/main fetch for the "
                                    "retry failed: " + _git_err(r) + ")",
                                    digest_path, fail_hard or fail_push, ctx)
                    r = git("reset", "--hard", "origin/main")
                    if r.returncode != 0:
                        return fail(_publish_fail_reason(stage, detail, cause) +
                                    " (and the reset to origin/main for "
                                    "the retry failed: " + _git_err(r) + ")",
                                    digest_path, fail_hard or fail_push, ctx)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    log("interrupted during the push-retry reset — "
                        "cleaning up")
                    abort_rebase()
                    return fail(_publish_fail_reason(stage, detail, cause) +
                                " (interrupted during the retry reset)",
                                digest_path, fail_hard or fail_push, ctx)
                delay = (RETRY_DELAY_BASE_S * attempt +
                         random.uniform(0, RETRY_DELAY_JITTER_S))
                log(f"waiting {delay:.1f}s before attempt "
                    f"{attempt + 1} (jittered backoff)")
                try:
                    time.sleep(delay)
                except KeyboardInterrupt:
                    log("interrupted during the retry backoff — cleaning up")
                    abort_rebase()
                    return fail(_publish_fail_reason(stage, detail, cause) +
                                " (interrupted during the retry backoff)",
                                digest_path, fail_hard or fail_push, ctx)
                continue
            return fail(_publish_fail_reason(stage, detail, cause),
                        digest_path, fail_hard or fail_push, ctx)


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
    ap.add_argument("--publish-branch", default=None,
                    help="stage the commit on this branch instead of "
                         "pushing it to main (issue #443: the "
                         "ledger-publish relay turns the branch into "
                         "a PR, executes the required close-gate on "
                         "the candidate commit and merges it). The "
                         "publish is PENDING until the relay merges — "
                         "the failure signal is not cleared here")
    ap.add_argument("--guard-heartbeat", action="store_true",
                    help="include a fresh ledger/guard-heartbeat.json "
                         "(status ok) in the commit — the guard "
                         "paths' run-bound envelope (issue #443); the "
                         "run id comes from LEDGER_RUN_ID / "
                         "GITHUB_RUN_ID")
    a = ap.parse_args()
    sweep_target = (a.sweep_target or
                    os.environ.get("LEDGER_SWEEP_TARGET") or None)
    if sweep_target:
        sweep_target = sweep_target.strip() or None
    try:
        return publish(a.commit, a.digest, a.fail_hard, sweep_target,
                       a.fail_push, a.publish_branch,
                       a.guard_heartbeat)
    except KeyboardInterrupt:
        # Issue #119: an interrupt used to propagate out uncaught
        # (and, mid-rebase, strand the checkout). git_publish
        # already aborts any rebase on its way out; this is the
        # backstop for an interrupt anywhere else in the run.
        log("interrupted — aborting any in-progress rebase")
        abort_rebase()
        return fail("publisher interrupted", a.digest, a.fail_hard,
                    _signal_context(sweep_target))
    except Exception as e:  # the publisher must never crash a sweep
        return fail(f"unexpected publisher error: {e}",
                    a.digest, a.fail_hard, _signal_context(sweep_target))


if __name__ == "__main__":
    sys.exit(main())
