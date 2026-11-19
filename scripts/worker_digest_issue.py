#!/usr/bin/env python3
"""Split-merge digest-issue helper (#67 §4d, route 1).

The worker archives a merged sweep; this script (run by the
worker-digest-issue workflow on `archive`-branch pushes) lists the
merged sweep dirs added by a push, so the workflow can open one
digest issue per merged sweep with the workflow token — the same
credential and the same #113/#120 title/status handling as the
Actions issue step in orchestrate.yml. The worker PAT is never
widened to issues:write (a Muhammad decision, not decided here).

A sweep dir qualifies ONLY when it carries merge-manifest.json —
an archive push for a raw worker-run must never open an issue.

Idempotency (#157): the sweep DIR is the identity, not the title —
titles are `# 🐊 Borsagator digest — {job}` and repeat for every
sweep of a job, so title matching both re-files closed sweeps and
false-skips live ones. Each sweep gets a unique identity label
``digest-<sha256(sweep_dir)[:16]>`` (a hash, because a raw
``digest:<sweep-dir>`` label would exceed GitHub's 50-character
label limit). The issue is created with BOTH the `borsagator`
label (what the digest watch discovers) and its identity label,
and a sweep is skipped whenever ANY issue — open or closed —
already carries its identity label. The label filter is an exact
API filter, not the lagged fuzzy search the old workflow used.
Runs of THIS workflow are serialized by the workflow's
`concurrency` group, but the group covers no other actor — the
orchestrate.yml issue step, a manual filing, or a rerun outside
the group race freely. Issue #229: a sweep is therefore CLAIMED
before it is filed, via `gh label create <identity label>`.
Safety rests on exactly two pillars, stated as the assumptions
they are: (a) SERVER-SIDE LABEL-NAME UNIQUENESS — the REST
"create a label" endpoint documents 201 Created / 422 Validation
failed, and `gh label create` documents that updating an
existing label requires --force, so a plain create is treated as
failing when the name exists; exactly one concurrent creator
wins. This is an API-contract assumption, to be verified against
live GitHub under #219, not something these tests can prove.
(b) NO AUTOMATIC RELEASE: a claim, once held, is never deleted
by this script. A nonzero issue-create response plus an empty
listing does NOT prove no issue landed (#230's lag), so the
claim survives every ambiguous outcome; only a human, after
reconciling (did a create land? is a holder still active?), may
`gh label delete` and re-run. The confirming entity GET
(`gh api repos/:owner/:repo/labels/<label>`) is advisory only:
it can only ever BLOCK a run (a stale or wrong answer produces a
red run or a bounded wait, never a duplicate), so no lag-free
read guarantee is needed or claimed. A claim loser waits a
bounded budget for the winner's issue — PER HELD SWEEP, not a
shared per-run budget like #230's reconciliation (see
RECONCILE_RETRY_DELAYS for the sleep-only worst case) —
re-claiming each round, and skips only on a fetch-confirmed
exactly-one.
Reconciliation requires EXACTLY ONE fetch-confirmed issue per
sweep — the old existence check let two racing runs both file
and both exit 0 — and duplicates are DETECT-AND-RED: the run
fails naming the pair and the repair (keep the lowest number;
for each extra, close it AND remove its identity label — the
label check lists --state all, and a closed issue still carries
its labels, so a close alone leaves the pair visible). This
helper never closes or edits issues: filing is its mandate. The
claim closes the double-file hole only among runs of THIS code;
a non-adopter (old workflow run, manual `gh issue create`)
never claims, and its in-window duplicate can slip a lagged
listing — caught red by the next run touching that sweep.
MIGRATION: identity labels predate this protocol. A past
successful filing (label + issue) is safe — the run skips on
the confirmed issue. A past ORPHANED label (created by old code,
issue never landed) now blocks filing with a red orphaned-claim
run until a human reconciles and deletes it; an empty listing
alone never justifies the deletion. There is no blind retry:
the issue is created once; if the create call fails, the
identity label is re-checked once (a create that landed
server-side but reported failure is then recognised as filed),
and a genuine failure fails the step loudly with the claim
retained for manual reconciliation.

Issue #223: twice in the #220 burst test a first attempt stayed
green, created its identity label and filed NO issue, and the
identical re-run then filed correctly. Green-exit paths
consistent with that evidence: the skip branch and the lost-
create recheck (both trust a bare `gh issue list --label`
result), and a create that reported success without landing.
Which one fired is UNPROVEN (scheduled-run logs are unavailable)
and this script does not assume one. What changes is the trust:
a bare listing can no longer suppress a filing on its own. Every
listed issue number is fetched (verify_listed_issues) and sorted
three ways: CONFIRMED (fetched, payload schema-valid, returned
number exactly the requested positive int, identity label
present) justifies a skip; REFUTED (successfully fetched and
schema-valid, but the issue no longer carries the label) is
treated as absent with a loud stderr note, so the sweep is
filed; and INDETERMINATE (ANY failed fetch - network, DNS, auth
or repository-concealment failures are indistinguishable from a
missing issue in gh's output - plus timeout, malformed payload
or number mismatch) raises and fails the step loudly. An unknown
is never turned into "absent", so no transient error can file a
duplicate; the cost is that a listing naming an unresolvable or
nonexistent issue produces a red run rather than self-healing,
which is the fail-loud alternative #223 sanctions. After the
filing pass, every sweep in the event range is reconciled once
against a confirmed issue, so a create that reported success
without landing fails loudly instead of exiting 0. #230: a check
right after a create can miss the new issue (suspected index lag,
not proven), so a just-created sweep is re-checked with a bounded
backoff (see reconcile_sweeps); creates and errors are never
retried. In --file
mode an unexpected helper exception now exits 1 for the same
reason. Guarantees are as observed by this run at verification
time; cross-writer atomicity holds only among actors that claim
(#229), never against a non-adopter. Deployment prerequisites
(per official GitHub docs, not verified live here): the filing
token needs the "Issues" repository permission (write) — the
documented requirement for both "Create a label" and "Create an
issue"; the workflow's existing `issues: write` satisfies this
on paper.

Usage (listing, unchanged — exit 0 always):
    worker_digest_issue.py --before <sha> --after <sha>
        --repo-dir <archive-branch checkout>
Stdout is one line per newly added merged sweep:
    <sweep_dir>\t<title>
Exit 0 always (a listing failure prints nothing, never fails the
workflow step that consumes it — the workflow treats an empty
listing as "nothing to file").

Usage (filing — what the workflow runs):
    worker_digest_issue.py --before <sha> --after <sha>
        --repo-dir <archive-branch checkout> --file
Files (or skips) one digest issue per listed sweep and exits 0
only when every sweep was filed or already had its issue; exits
1 when any sweep failed, after still filing the others.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Green, matching the repo's other automation labels.
IDENTITY_LABEL_COLOR = "0E8A16"
IDENTITY_LABEL_PREFIX = "digest-"

# #230: waits between post-create reconciliation rounds: 1 +
# len(delays) = 5 rounds and at most 2+4+8+16 = 30 s of sleep per
# run, shared by all sweeps (network calls are extra). #229: the
# same VALUES bound the claim wait, but with different sharing
# semantics: the claim wait is PER HELD SWEEP inside file_issue
# (up to 30 s of sleep for EACH sweep whose claim is held by
# another run while this run waits), not one shared budget per
# run. Worst-case SLEEP per run is therefore 30 s x held sweeps +
# 30 s of shared reconciliation. These figures count sleep only:
# every gh call adds up to its 120 s timeout on top, so "~19
# fully-held sweeps risk the workflow's 10-minute timeout" is an
# illustrative sleep-budget estimate, not a wall-clock bound
# (typical pushes add a handful of sweeps, and a sweep whose
# issue is confirmed early costs one round, never the full
# budget).
RECONCILE_RETRY_DELAYS = (2, 4, 8, 16)


def digest_title_status(text, fallback_job=""):
    """(title, status) from a digest.md text, mirroring the
    orchestrate.yml issue step: title is the first line (headerless
    digests fall back to the job); a running/failed marker appends
    the FAILED flag to the title."""
    lines = (text or "").splitlines()
    title = lines[0].strip() if lines and lines[0].strip() else ""
    if not title:
        job = fallback_job or "unknown job"
        title = f"# 🐊 Borsagator digest — {job}"
    m = re.search(r"borsagator-digest-status: (\w+)", text or "")
    status = m.group(1) if m else None
    if status in ("running", "failed"):
        title = title + " — ⚠️ FAILED"
    return title, status


def identity_label(sweep_dir):
    """The durable per-sweep identity label for a sweep dir.

    ``digest-<first 16 hex of sha256(sweep_dir)>`` — deterministic,
    distinct per sweep dir (the dir embeds date, finished time and
    job id), 23 chars, well inside GitHub's 50-character label
    limit. The raw ``digest:<sweep-dir>`` form the issue suggests
    does not fit: a real dir is ~60–85 chars on its own."""
    digest = hashlib.sha256(sweep_dir.encode("utf-8")).hexdigest()
    return IDENTITY_LABEL_PREFIX + digest[:16]


def added_merge_manifests(before, after, repo_dir):
    """Sweep dirs whose merge-manifest.json was ADDED between
    `before` and `after` (git diff --name-only). A zero `before`
    (first push / rewritten history) lists every merge-manifest at
    `after` instead. Returns sorted sweep-dir paths, archive
    relative (sweeps/<date>/<dir>)."""
    repo_dir = Path(repo_dir)
    if not before or before.startswith("0000"):
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "ls-tree", "-r", "--name-only",
             after],
            capture_output=True, text=True, timeout=120)
        names = proc.stdout.splitlines() if proc.returncode == 0 \
            else []
    else:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "diff", "--name-only",
             "--diff-filter=A", before, after],
            capture_output=True, text=True, timeout=120)
        names = proc.stdout.splitlines() if proc.returncode == 0 \
            else []
    dirs = set()
    for name in names:
        parts = name.split("/")
        if len(parts) >= 3 and parts[0] == "sweeps" and \
                parts[-1] == "merge-manifest.json":
            dirs.add("/".join(parts[:-1]))
    return sorted(dirs)


def run_gh(args):
    """One `gh` call (module-level so tests can monkeypatch it).
    Returns the CompletedProcess; raises only on spawn/timeout."""
    return subprocess.run(["gh"] + list(args), capture_output=True,
                          text=True, timeout=120)


def issue_numbers_with_label(label):
    """Issue numbers carrying `label`, ANY state (open or closed).

    An exact label filter — not the search index — so a closed
    digest issue is found and a replay files no duplicate. Raises
    on an API failure: a failed check must never be read as "no
    issue exists", or the next step would file a duplicate."""
    proc = run_gh(["issue", "list", "--label", label, "--state",
                   "all", "--json", "number"])
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh issue list --label {label} failed: "
            f"{(proc.stderr or proc.stdout or '').strip()[:200]}")
    try:
        # #223: no `or "[]"` fallback - a successful call with EMPTY
        # output is malformed, not a verified empty array, and must
        # fail loudly below.
        rows = json.loads(proc.stdout)
        if not isinstance(rows, list):
            raise ValueError("payload is not a JSON array")
        numbers = []
        for row in rows:
            # #223: no coercion - a bool (True == 1) or string row
            # must fail loudly, not silently become a number.
            n = row.get("number") if isinstance(row, dict) else None
            if not isinstance(n, int) or isinstance(n, bool) \
                    or n <= 0:
                raise ValueError(f"unexpected issue number: {n!r}")
            numbers.append(n)
        return numbers
    except (ValueError, TypeError) as e:
        raise RuntimeError(
            f"gh issue list --label {label} returned unparsable "
            f"output: {e}") from e


class VerificationIndeterminate(RuntimeError):
    """A listed issue could be neither confirmed nor ruled out.

    Raised instead of guessing: an indeterminate verification must
    fail the step loudly, never become a silent skip (the #223
    class) and never become a fresh filing (a duplicate)."""


def _fetch_issue_labels(number):
    """The label names on issue #number, fetched and validated.

    ANY nonzero `gh issue view` exit is indeterminate: gh's
    not-found wording also covers DNS failures ("Could not
    resolve host") and repository/auth concealment, so a failed
    fetch cannot be read as "the issue does not exist" from here.
    A successful fetch must return a schema-valid payload whose
    number is exactly the requested positive int."""
    proc = run_gh(["issue", "view", str(number),
                   "--json", "number,labels"])
    if proc.returncode != 0:
        raise VerificationIndeterminate(
            f"gh issue view {number} failed: "
            f"{(proc.stderr or proc.stdout or '').strip()[:200]}")
    try:
        data = json.loads(proc.stdout or "")
    except ValueError as e:
        raise VerificationIndeterminate(
            f"gh issue view {number} returned unparsable JSON: {e}"
            ) from e
    n = data.get("number") if isinstance(data, dict) else None
    labels = data.get("labels") if isinstance(data, dict) else None
    if not isinstance(n, int) or isinstance(n, bool) \
            or n != number or not isinstance(labels, list):
        raise VerificationIndeterminate(
            f"gh issue view {number} returned a payload that does "
            f"not match the request or the expected schema")
    names = set()
    for row in labels:
        if not isinstance(row, dict) or \
                not isinstance(row.get("name"), str):
            raise VerificationIndeterminate(
                f"gh issue view {number} returned a label entry "
                f"without a string name")
        names.add(row["name"])
    return names


def verify_listed_issues(label):
    """Confirmed issue numbers for `label`, from a DISTRUSTED
    listing (#223).

    Every number from issue_numbers_with_label is fetched. A
    number is CONFIRMED - and may justify a skip - only when the
    fetch succeeds, the payload is schema-valid, its number is
    exactly the requested one, and the issue still carries
    `label`. A number that fetches cleanly but no longer carries
    `label` is REFUTED and logged loudly; refuted listings never
    suppress a filing. Anything else - a failed fetch of any
    kind, malformed or mismatched payload - raises
    VerificationIndeterminate and fails the step loudly instead
    of choosing between a silent skip and a duplicate. The LIST
    call itself still raises via issue_numbers_with_label: a
    failed check is never read as "no issue exists"."""
    confirmed = []
    for number in issue_numbers_with_label(label):
        names = _fetch_issue_labels(number)
        if label in names:
            confirmed.append(number)
        else:
            print(f"worker_digest_issue: label check listed issue "
                  f"#{number} for {label} but the fetched issue "
                  f"does not carry it - listing refuted, not "
                  f"skipping", file=sys.stderr)
    return confirmed


def fetch_label_exists(label):
    """True when the identity LABEL entity exists (#229).

    Advisory ONLY: this GET can block a run, never unblock one —
    a 200 means "claim held, do not file", and ANY failure is
    indeterminate (#223): gh's not-found wording is
    indistinguishable from DNS/auth failures, so an unknown answer
    is never read as "no label", and a schema-mismatched payload
    fails loudly instead of guessing. Safety does not depend on
    this read being fresh or correct: a stale 200 costs a bounded
    wait or a red run, never a duplicate. Uniqueness itself comes
    from the label CREATE, not from this GET."""
    proc = run_gh(["api", f"repos/:owner/:repo/labels/{label}"])
    if proc.returncode != 0:
        raise VerificationIndeterminate(
            f"gh api labels/{label} failed: "
            f"{(proc.stderr or proc.stdout or '').strip()[:200]}")
    try:
        data = json.loads(proc.stdout or "")
    except ValueError as e:
        raise VerificationIndeterminate(
            f"gh api labels/{label} returned unparsable JSON: {e}"
            ) from e
    if not isinstance(data, dict) or data.get("name") != label:
        raise VerificationIndeterminate(
            f"gh api labels/{label} returned a payload that does "
            f"not match the request")
    return True


def claim_sweep(sweep_dir):
    """Claim the sweep for THIS run via its identity label (#229).

    Label creation is the server-side compare-and-swap: GitHub
    enforces label-name uniqueness (REST "create a label": 201 /
    422; `gh label create` updates an existing name only with
    --force), so exactly one concurrent run's create succeeds.
    ATOMICITY UNDER SIMULTANEOUS CREATES is a deployment
    ASSUMPTION from that contract, not an independently proven
    guarantee — verify with two forced-concurrent runs under
    #219's live proof before relying on it fleet-wide. Returns
    "claimed" when this run created the label, "held" when it
    already exists — the claim then belongs to another run
    (past, in-flight or orphaned) and the caller decides on
    fetch-confirmed ISSUES, never on the label alone. A create
    that fails for any reason is confirmed by an entity GET:
    200 means the claim is held; anything else raises
    VerificationIndeterminate, because an unknown claim state
    must fail loudly, never become a silent skip or a duplicate."""
    label = identity_label(sweep_dir)
    desc = f"Digest issue for {sweep_dir}"[:100]
    proc = run_gh(["label", "create", label, "--color",
                   IDENTITY_LABEL_COLOR, "--description", desc])
    if proc.returncode == 0:
        return "claimed"
    if fetch_label_exists(label):
        return "held"


def duplicate_error(sweep_dir, label, confirmed):
    """The RuntimeError for >=2 fetch-confirmed issues (#229).

    Detect-and-red, never auto-repair: closing an extra alone
    does NOT restore uniqueness, because the label check lists
    --state all and a closed issue still carries its labels —
    the repair must also REMOVE the identity label from every
    extra. Keep-lowest is the deterministic tie-break any two
    operators agree on."""
    keep = min(confirmed)
    extras = [n for n in sorted(confirmed) if n != keep]
    return RuntimeError(
        f"{sweep_dir}: duplicate digest issues {sorted(confirmed)} "
        f"carry {label}. Keeping #{keep} (lowest); for each of "
        f"{extras}: close it AND remove label {label} from it "
        f"(a closed issue still carries its labels, so closing "
        f"alone leaves the duplicate visible to --state all), "
        f"then re-run")


def _sleep(seconds):
    """time.sleep, module-level so tests can monkeypatch it."""
    time.sleep(seconds)


def reconcile_sweeps(sweeps, created):
    """Sweep dirs without EXACTLY ONE confirmed issue (#230, #229).

    Rounds run over all pending sweeps, then one shared wait, so
    the sleep total does not grow with the sweep count. Only a
    sweep in `created` (filed by this run) is re-checked after an
    EMPTY result: a check right after a create can miss it
    (suspected index lag, not proven). A raised error (failed
    list, indeterminate fetch, malformed payload, a duplicate)
    is final at once for every sweep, never waited on. The round
    count is fixed, so a genuinely absent filing is returned for
    the caller to fail red. No create is retried, so no duplicate
    can be filed. #229: EXISTENCE is not enough — two racing runs
    could both file and both see >=1 confirmed issue, exiting 0
    over a duplicated sweep. >=2 confirmed issues are
    detect-and-red (duplicate_error), never silently passed and
    never auto-repaired."""
    rounds = len(RECONCILE_RETRY_DELAYS) + 1
    unverified = []
    pending = list(sweeps)
    for rnd in range(1, rounds + 1):
        retry = []
        for sweep_dir in pending:
            label = identity_label(sweep_dir)
            try:
                confirmed = verify_listed_issues(label)
                if len(confirmed) >= 2:
                    raise duplicate_error(sweep_dir, label,
                                          confirmed)
                ok = bool(confirmed)
            except Exception as e:  # noqa: BLE001 - final, no retry
                print(f"worker_digest_issue: reconciliation for "
                      f"{sweep_dir} could not complete: {e}",
                      file=sys.stderr)
                unverified.append(sweep_dir)
                continue
            if ok:
                if rnd != 1 and sweep_dir in created:
                    print(f"worker_digest_issue: {sweep_dir} "
                          f"confirmed on retry in reconciliation "
                          f"round {rnd}/{rounds}", file=sys.stderr)
                continue
            if sweep_dir in created and rnd != rounds:
                retry.append(sweep_dir)
            else:
                unverified.append(sweep_dir)
        pending = retry
        if not pending:
            break
        delay = RECONCILE_RETRY_DELAYS[rnd - 1]
        print(f"worker_digest_issue: {len(pending)} just-created "
              f"sweep(s) not listed yet (round {rnd}/{rounds}); "
              f"waiting {delay}s", file=sys.stderr)
        _sleep(delay)
    return unverified


def file_issue(sweep_dir, title, repo_dir):
    """File (or skip) the digest issue for one merged sweep.

    Returns "created" or "exists". Raises on a genuine failure —
    the caller records it and files the remaining sweeps first.
    A missing digest.md is a failure, never a body-less issue.
    "exists" requires a CONFIRMED issue (#223): a bare label-list
    hit that a fetch cannot corroborate never suppresses filing,
    and an indeterminate fetch fails loudly instead of guessing.
    #229: only the CLAIM WINNER may create — a run that does not
    hold the claim waits a bounded budget for the winner's issue,
    re-claiming each round, then skips on a fetch-confirmed
    exactly-one or raises on an orphaned claim. NOTE: this wait
    is PER HELD SWEEP (up to 30 s OF SLEEP each; gh call time is
    extra), unlike the shared #230 reconciliation budget — see
    the RECONCILE_RETRY_DELAYS comment for the sleep-only worst
    case against the workflow timeout.
    >=2 confirmed issues are detect-and-red (duplicate_error),
    here and in reconciliation. The claim is NEVER released by
    this script: a failed create with an empty listing may be a
    lost response under #230 lag, so the claim is retained for
    a human to reconcile. Behaviour change to state plainly: a
    re-run after a genuinely failed create no longer retries
    automatically — it blocks on the retained claim until the
    operator reconciles and deletes the label."""
    label = identity_label(sweep_dir)
    rounds = len(RECONCILE_RETRY_DELAYS) + 1
    status = None
    confirmed = []
    for rnd in range(1, rounds + 1):
        status = claim_sweep(sweep_dir)
        confirmed = verify_listed_issues(label)
        if confirmed or status == "claimed":
            break
        # Claim held, zero confirmed issues: the winner may still
        # be creating (its create follows its claim by seconds).
        # Wait, then re-claim; the loop never deletes anything.
        if rnd != rounds:
            delay = RECONCILE_RETRY_DELAYS[rnd - 1]
            print(f"worker_digest_issue: {sweep_dir} is claimed by "
                  f"another run, no issue yet (round {rnd}/{rounds}"
                  f"); waiting {delay}s", file=sys.stderr)
            _sleep(delay)
    if len(confirmed) >= 2:
        raise duplicate_error(sweep_dir, label, confirmed)
    if len(confirmed) == 1:
        print(f"issue already exists for {sweep_dir} - skipping "
              f"(confirmed by fetch)")
        return "exists"
    if status != "claimed":
        raise RuntimeError(
            f"{sweep_dir}: identity label {label} exists but after "
            f"{rounds} rounds no fetch-confirmed issue carries it - "
            f"an orphaned claim (a holder died between claiming and "
            f"filing) or a delayed/partial create still in flight; "
            f"refusing to file a possible duplicate. Do NOT delete "
            f"the label on the empty listing alone: reconcile first "
            f"(did a create land? is a holder still active?), then "
            f"delete label {label} and re-run")
    body = Path(repo_dir) / sweep_dir / "digest.md"
    if not body.is_file():
        raise FileNotFoundError(
            f"{sweep_dir}: digest.md missing, refusing to file a "
            f"body-less issue")
    print(f"filing digest issue for {sweep_dir}")
    proc = run_gh(["issue", "create", "--title", title,
                   "--body-file", str(body),
                   "--label", "borsagator", "--label", label])
    if proc.returncode == 0:
        return "created"
    # No blind retry (#157): the create may have landed server-side
    # while the CLI reported failure. Re-check the identity label
    # once — if the issue is there now, it was filed; only a real
    # absence is a failure, and it fails loudly. The claim is
    # RETAINED either way (#229): the empty re-check may be #230
    # lag over a landed create, and releasing would let a second
    # adopter file a duplicate.
    confirmed = verify_listed_issues(label)
    if len(confirmed) >= 2:
        raise duplicate_error(sweep_dir, label, confirmed)
    if len(confirmed) == 1:
        print(f"issue for {sweep_dir} exists after a failed create "
              f"- treating as filed (create response was lost; "
              f"confirmed by fetch)")
        return "exists"
    raise RuntimeError(
        f"gh issue create for {sweep_dir} failed and no "
        f"fetch-confirmed issue carries {label}: "
        f"{(proc.stderr or proc.stdout or '').strip()[:200]} - "
        f"claim RETAINED (the empty re-check may be listing lag "
        f"over a landed create). Reconcile: if the issue exists, "
        f"nothing to do; only after establishing that NO create "
        f"landed and no holder is active, delete label {label} "
        f"and re-run")


def file_issues(before, after, repo_dir):
    """File (or skip) one digest issue per newly merged sweep.

    Returns 0 when every sweep was filed or already had its issue,
    1 when any sweep failed — after still filing the others, so
    one bad sweep never blocks the rest of the push. After the
    filing pass every sweep is reconciled once against a
    fetch-confirmed issue (#223): a create that reported success
    without landing, an indeterminate verification, or any
    remaining silent-skip path is aggregated into the failures
    instead of exiting 0. Sweeps created in THIS run are re-checked
    (#230, reconcile_sweeps): an empty result is retried in up to 5
    rounds with one shared wait between rounds (2, 4, 8, 16 s, at
    most 30 s of sleep per run, whatever the sweep count) before it
    fails red. Skipped sweeps and any raised error get one check.
    Each round costs one list plus one fetch per listed issue per
    pending sweep. #229: reconciliation requires EXACTLY ONE
    fetch-confirmed issue — a duplicated sweep fails red naming
    the pair and its manual repair."""
    sweeps = added_merge_manifests(before, after, repo_dir)
    failures = []
    created = set()
    for sweep_dir in sweeps:
        md = Path(repo_dir) / sweep_dir / "digest.md"
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            text = ""
        title, _status = digest_title_status(text)
        try:
            if file_issue(sweep_dir, title, repo_dir) == "created":
                created.add(sweep_dir)
        except Exception as e:  # noqa: BLE001 - one sweep must not
            # block the rest; the failure is reported at the end.
            failures.append((sweep_dir, e))
            print(f"worker_digest_issue: FAILED {sweep_dir}: {e}",
                  file=sys.stderr)
    # Post-run reconciliation (#223): every sweep that did not
    # already fail must now have a fetch-confirmed issue carrying
    # its identity label. Each check is isolated so one bad sweep
    # never stops the others from being verified.
    failed_dirs = {d for d, _ in failures}
    to_check = [d for d in sweeps if d not in failed_dirs]
    for sweep_dir in reconcile_sweeps(to_check, created):
        e = RuntimeError(
            f"{sweep_dir}: no fetch-confirmed issue carries "
            f"{identity_label(sweep_dir)} after the filing pass - "
            f"refusing to exit green")
        failures.append((sweep_dir, e))
        print(f"worker_digest_issue: FAILED {sweep_dir}: {e}",
              file=sys.stderr)
    if failures:
        print(f"worker_digest_issue: {len(failures)} sweep(s) failed "
              f"to file; re-run the workflow to retry (a re-run's "
              f"fetch-confirmed label check skips sweeps whose "
              f"issue genuinely exists at that time)",
              file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="List merged sweeps added by an archive push.")
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--file", action="store_true",
                    help="file (or skip) one digest issue per listed "
                    "sweep instead of just listing them")
    args = ap.parse_args(argv)
    if args.file:
        try:
            return file_issues(args.before, args.after, args.repo_dir)
        except Exception as e:  # noqa: BLE001 - #223: an unexpected
            # failure must fail the step loudly in --file mode; a green
            # exit here would hide that nothing was verified or filed.
            # This intentionally changes --file mode only: plain
            # listing mode below still never fails the workflow.
            print(f"worker_digest_issue: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return 1
    try:
        for sweep_dir in added_merge_manifests(args.before, args.after,
                                               args.repo_dir):
            md = Path(args.repo_dir) / sweep_dir / "digest.md"
            try:
                text = md.read_text(encoding="utf-8")
            except OSError:
                text = ""
            title, _status = digest_title_status(text)
            print(f"{sweep_dir}\t{title}")
    except Exception as e:  # noqa: BLE001 - never fail the workflow
        print(f"worker_digest_issue: {type(e).__name__}: {e}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
