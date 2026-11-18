#!/usr/bin/env python3
"""Proof harness for issue #157 (panel round 12, F13):
worker-digest-issue dedup was fuzzy/open-only and creation was not
atomic:

(a) the workflow deduped on `gh issue list --state open --search
    "$title"` — fuzzy, index-lagged, open-only — so a closed digest
    issue never matched and the sweep was re-filed;
(b) on `before=0000` (force/first push) the helper lists EVERY
    historical merge-manifest, so a replay re-filed every past sweep;
(c) two concurrent workflow runs could both observe "no issue" and
    both create one — check and create were separate operations;
(d) the `|| gh issue create` blind retry double-created on a
    post-creation transient error, and the retry dropped the
    `borsagator` label, so the duplicate escaped label-based
    digest-watch handling;
(e) the title is not a per-sweep identity at all — it is
    `# 🐊 Borsagator digest — {job}` and repeats for every sweep of
    a job — so an open issue for one sweep false-skipped every
    later sweep of the same job, losing their digests.

The fix makes the sweep DIR the identity: a unique
`digest-<sha256(sweep_dir)[:16]>` label is created with the issue
(beside the `borsagator` label), a sweep is skipped whenever ANY
issue — open or closed — already carries its label, creation is
serialized by the workflow's concurrency group, and there is no
blind retry (one create; a failed create re-checks the label once
to tell a lost response from a real failure, and a real failure
fails the step loudly).

Issue #223 (amendment 2026-11-18): the #220 burst test showed a
first attempt staying green, creating its identity label and filing
NO issue — the helper trusted a bare `gh issue list --label` result
in the skip branch and the lost-create recheck, and an unverified
rc==0 create could exit green with nothing filed. The helper now
fetch-confirms every listed issue before trusting it (CONFIRMED /
REFUTED / INDETERMINATE — see the helper docstring) and reconciles
every sweep once after the filing pass, so a create that reported
success without landing fails loudly instead of exiting 0. This
harness was amended for that behaviour: the fake `gh` answers
`issue view` from the in-memory store (a fetch of an unknown number
fails 404, i.e. INDETERMINATE), T6's list count grows by the
reconciliation pass, and T13/T14 pin the new contract (a listing
that names an unresolvable issue fails red with no create; a listed
issue that no longer carries the label is filed in the same run).

Issue #229 (amendment 2026-11-19): reconciliation checked
EXISTENCE, not uniqueness, so two racing runs could both file
and both exit 0, and the skip check had the same existence-only
shape. The helper now CLAIMS a sweep before filing it: `gh label
create <identity label>` is the server-side compare-and-swap
(exactly one concurrent creator wins — an ASSUMPTION from the
documented 201/422 create-a-label contract and `gh label
create`'s --force semantics, to be verified live under #219,
not something this harness proves; the confirming entity GET
is advisory only — it can BLOCK a run but never prove absence,
and no lag-free read is assumed of it either), a claim loser
never creates —
it waits a bounded budget for the winner's issue, skips on a
fetch-confirmed exactly-one, adopts a released orphan, and fails
red on a permanent orphan — and reconciliation requires EXACTLY
ONE fetch-confirmed issue; duplicates are detect-and-red (the
run fails naming the pair and its manual repair — close each
extra AND remove its identity label, because --state all still
sees a closed issue's labels), and the claim is NEVER
auto-released: a nonzero create response plus an empty listing
does not prove no issue landed (#230 lag). This harness was
amended for that behaviour: T11 became the orphaned-claim red
test (a failed label create is now load-bearing, never
swallowed), the fake `gh` answers label GET / label delete, and
T20-T27 pin the claim, the loser paths, duplicate detection,
lost-response claim retention and REAL two-process races
against a file-backed fake `gh` (atomic O_EXCL label claim).

The `gh` CLI is faked in-process (in-memory issue store, no
network, no real repo touched) by monkeypatching the module's
`run_gh`. Listing tests use throwaway git repos, as in
harness_issue67 case 16.

The harness discriminates: on unmodified main it fails at import
(`identity_label`, `file_issues` and `run_gh` do not exist there);
with the fix, every test passes.

Usage: python3 scripts/test_worker_digest_issue_157.py
Exit 0 only when every test passes.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import worker_digest_issue as wdi

RESULTS = []
JOB = "sweep-lite POUL.CA"
TITLE = "# 🐊 Borsagator digest — sweep-lite POUL.CA"
ZERO = "0" * 40


class Proc:
    """Minimal stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeGh:
    """In-memory `gh` for the commands the filing path uses.

    `fail_create` controls the create outcome: None (succeed),
    "after_record" (record the issue, then report failure — a
    post-creation transient error), or "clean" (fail, record
    nothing). `fail_titles` restricts the failure to those titles;
    other titles succeed. `label_create_fails` makes every label
    create fail (the "already exists" path — filing must not care).
    """

    def __init__(self):
        self.issues = []
        self.labels = set()
        self.calls = []
        self.fail_create = None
        self.fail_titles = None
        # #229: a failed label create is load-bearing (the claim).
        # label_create_fails models "the label already exists"
        # (another run holds the claim): create rc1 AND the entity
        # GET answers 200. label_create_fails_until fails only the
        # first N creates (a released orphan, adopted on retry).
        # label_api_down fails the GET itself (indeterminate).
        self.label_create_fails = False
        self.label_create_fails_until = 0
        self.label_api_down = False
        self.label_api_garbage = False
        self.label_creates_seen = 0
        self.deleted_labels = []
        # #229: race knobs. appear_after_lists injects a rival
        # issue carrying the queried label after N list calls (a
        # concurrent winner filing mid-wait); race_on_create /
        # race_after_create land a rival issue just before / after
        # ours inside the create call.
        self.appear_after_lists = None
        self.lists_seen = 0
        self._appeared = False
        self.race_on_create = False
        self.race_after_create = False
        # #223: extra rows a listing returns that the store does not
        # hold (a phantom / refuted listing). {label: [{"number": n}]}
        self.list_override = {}
        # #230: after a create records an issue, the next
        # `lag_after_create` listings return nothing (index lag).
        # `hide_after_view` hides every listing after the first
        # successful fetch (a skipped sweep that goes missing).
        self.lag_after_create = 0
        self.lag_remaining = 0
        self.hide_after_view = False
        # one-shot read fault armed by a create: "list_rc",
        # "list_garbage" (next listing) or "view_fail" (next fetch)
        self.fault_after_create = None
        self.armed_fault = None
        self.sleeps = []

    def _next_number(self):
        return len(self.issues) + 1

    def _inject_rival(self, label):
        if not self._appeared:
            self._appeared = True
            self.issues.append({"number": self._next_number(),
                                "title": TITLE,
                                "labels": ["borsagator", label],
                                "state": "open"})

    def run(self, args):
        self.calls.append(list(args))
        if args[0] == "api":
            # #229: entity GET for the claim — direct, never the
            # lagged listing index.
            name = args[1].rsplit("/", 1)[-1]
            if self.label_api_down:
                return Proc(1, "", "HTTP 502 (simulated)")
            if self.label_api_garbage:
                return Proc(0, "not json")
            if (name in self.labels or self.label_create_fails or
                    self.label_creates_seen <=
                    self.label_create_fails_until):
                return Proc(0, json.dumps({"name": name}))
            return Proc(1, "", "HTTP 404: Not Found")
        if args[:2] == ["issue", "list"]:
            self.lists_seen += 1
            label = args[args.index("--label") + 1]
            if (self.appear_after_lists is not None and
                    self.lists_seen > self.appear_after_lists):
                self._inject_rival(label)
            state = args[args.index("--state") + 1]
            if self.armed_fault in ("list_rc", "list_garbage"):
                fault, self.armed_fault = self.armed_fault, None
                if fault == "list_rc":
                    return Proc(1, "", "HTTP 502 (simulated)")
                return Proc(0, "not json")
            if self.lag_remaining != 0:
                self.lag_remaining -= 1
                return Proc(0, "[]")
            rows = [{"number": i["number"]} for i in self.issues
                    if label in i["labels"] and
                    (state == "all" or i["state"] == state)]
            # #223: a listing may name numbers the store does not
            # hold (phantom / refuted). They ride the rows so the
            # helper's fetch-confirmation sees them.
            for r in self.list_override.get(label, []):
                if r not in rows:
                    rows.append(dict(r))
            return Proc(0, json.dumps(rows))
        if args[:2] == ["issue", "view"]:
            # #223: fetch-confirmation for one listed number. A
            # stored issue answers with its labels; anything else
            # is a failed fetch (INDETERMINATE), never "absent".
            try:
                n = int(args[2])
            except (ValueError, IndexError):
                raise AssertionError(f"fake gh: bad view args {args!r}")
            for i in self.issues:
                if i["number"] == n:
                    if self.armed_fault == "view_fail":
                        self.armed_fault = None
                        return Proc(1, "", "HTTP 502 (simulated)")
                    if self.hide_after_view:
                        self.lag_remaining = 1000
                    return Proc(0, json.dumps(
                        {"number": n,
                         "labels": [{"name": lb} for lb in i["labels"]]}))
            return Proc(1, "", "HTTP 404: Not Found")
        if args[:2] == ["label", "create"]:
            # #229: the compare-and-swap — a name that exists
            # (created here, held by a racer, or within the
            # fails_until window) fails, exactly like GitHub's
            # uniqueness constraint.
            self.label_creates_seen += 1
            if (self.label_create_fails or args[2] in self.labels or
                    self.label_creates_seen <=
                    self.label_create_fails_until):
                return Proc(1, "", "already exists")
            self.labels.add(args[2])
            return Proc(0, "")
        if args[:2] == ["label", "delete"]:
            # #229: claim release.
            name = args[-1]
            self.deleted_labels.append(name)
            self.labels.discard(name)
            if self.label_create_fails:
                self.label_create_fails = False
            if self.label_creates_seen <= self.label_create_fails_until:
                self.label_create_fails_until = self.label_creates_seen
            return Proc(0, "")
        if args[:2] == ["issue", "close"]:
            # #229: the helper must NEVER close issues — any close
            # call is a bug; fail the test loudly.
            raise AssertionError(f"fake gh: unexpected close {args!r}")
        if args[:2] == ["issue", "create"]:
            title = args[args.index("--title") + 1]
            body = args[args.index("--body-file") + 1]
            labels = [args[i + 1] for i, a in enumerate(args)
                      if a == "--label"]
            if not os.path.isfile(body):
                return Proc(1, "", f"body file not found: {body}")
            fail = None
            if self.fail_create and (
                    self.fail_titles is None or
                    title in self.fail_titles):
                fail = self.fail_create
            rec = {"number": self._next_number(), "title": title,
                   "labels": labels, "state": "open"}
            if self.race_on_create:
                # #229: a rival's filing lands just BEFORE ours —
                # independent of whether OUR response is lost.
                self.issues.append({
                    "number": self._next_number(), "title": title,
                    "labels": list(labels), "state": "open"})
                rec["number"] = self._next_number()
            if fail == "after_record":
                self.issues.append(rec)
                # #229: a lost response can coincide with a lagged
                # listing — arm the lag too.
                self.lag_remaining = self.lag_after_create
                return Proc(1, "",
                            "Post https://api.github.com: context "
                            "deadline exceeded (simulated)")
            if fail == "clean":
                return Proc(1, "", "HTTP 500 (simulated)")
            if fail == "phantom_success":
                # #230: reports success, files nothing.
                return Proc(0, "created (simulated, not stored)")
            self.issues.append(rec)
            if self.race_after_create:
                # #229: a rival's filing lands just AFTER ours.
                self.issues.append({
                    "number": self._next_number(), "title": title,
                    "labels": list(labels), "state": "open"})
            self.lag_remaining = self.lag_after_create
            self.armed_fault = self.fault_after_create
            return Proc(
                0, f"https://github.com/moos-labs/borsagator/issues/"
                   f"{rec['number']}")
        raise AssertionError(f"fake gh: unexpected call {args!r}")

    def issues_with_title(self, title):
        return [i for i in self.issues if i["title"] == title]


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name +
          ("" if cond else f": {detail}"))


def git(*args, cwd):
    subprocess.run(["git", "-C", str(cwd)] + list(args), check=True,
                   capture_output=True, text=True)


def make_repo(n_sweeps, digest_titles=None):
    """Throwaway git repo: base commit + one commit adding N merged
    sweep dirs (merge-manifest.json + digest.md each). Returns
    (tmpdir, base_sha, head_sha, [sweep_dirs])."""
    tmp = tempfile.mkdtemp(prefix="wdi157-")
    git("init", "-q", cwd=tmp)
    git("config", "user.email", "t@t", cwd=tmp)
    git("config", "user.name", "t", cwd=tmp)
    with open(os.path.join(tmp, "README"), "w") as f:
        f.write("base\n")
    git("add", ".", cwd=tmp)
    git("commit", "-qm", "base", "--no-gpg-sign", cwd=tmp)
    base = subprocess.run(["git", "-C", tmp, "rev-parse", "HEAD"],
                          capture_output=True, text=True,
                          check=True).stdout.strip()
    dirs = []
    for i in range(n_sweeps):
        day = f"2026-11-{15 + i:02d}"
        sd = (f"sweeps/{day}/080000__sweep-lite-poul-ca__"
              f"runsched-{day}")
        dirs.append(sd)
        path = os.path.join(tmp, sd)
        os.makedirs(path)
        with open(os.path.join(path, "merge-manifest.json"), "w") as f:
            f.write("{}")
        title = (digest_titles[i] if digest_titles else TITLE)
        with open(os.path.join(path, "digest.md"), "w") as f:
            f.write(f"{title}\n\n"
                    "<!-- borsagator-digest-status: complete -->\n\n"
                    f"Started {day} 08:00 UTC · finished 08:15 UTC · "
                    "5 tools\n")
    git("add", ".", cwd=tmp)
    git("commit", "-qm", "merged sweeps", "--no-gpg-sign", cwd=tmp)
    head = subprocess.run(["git", "-C", tmp, "rev-parse", "HEAD"],
                          capture_output=True, text=True,
                          check=True).stdout.strip()
    return tmp, base, head, dirs


def with_fake(fn):
    """Run fn(fake) with wdi.run_gh patched; restore afterwards."""
    fake = FakeGh()
    old, old_sleep = wdi.run_gh, wdi._sleep
    wdi.run_gh = fake.run
    wdi._sleep = fake.sleeps.append  # never really sleep (#230)
    try:
        fn(fake)
    finally:
        wdi.run_gh, wdi._sleep = old, old_sleep


def run_quiet(call):
    """(call(), captured stderr) - to assert diagnostics (#230)."""
    err = io.StringIO()
    with redirect_stderr(err):
        result = call()
    return result, err.getvalue()


# #229, T26: an executable fake `gh` with a file-backed store.
# The label claim is a REAL atomic compare-and-swap across
# processes (O_CREAT|O_EXCL); issues and the listing lag live in
# a locked JSON store. No network, no real repo touched. The
# O_EXCL MODELS the assumed server-side atomicity of `gh label
# create` (see claim_sweep's docstring); it does not prove
# GitHub's concurrent-create behaviour. WDI_BARRIER (unique per
# repetition, 30 s timeout, absent for single-process runs) is a
# deterministic rendezvous so both competitors reach the claim.
FAKE_GH_EXECUTABLE = '''#!/usr/bin/env python3
import fcntl
import json
import os
import sys
import time

store = os.environ["WDI_STORE"]
os.makedirs(os.path.join(store, "labels"), exist_ok=True)
lockpath = os.path.join(store, "lock")
issues_p = os.path.join(store, "issues.json")
lag_p = os.path.join(store, "lag")


def load():
    try:
        with open(issues_p) as f:
            return json.load(f)
    except OSError:
        return []


def save(x):
    with open(issues_p, "w") as f:
        json.dump(x, f)


args = sys.argv[1:]
if args[:2] == ["label", "create"]:
    name = args[2]
    barrier = os.environ.get("WDI_BARRIER")
    if barrier:
        # Deterministic rendezvous: BOTH competing processes must
        # reach the claim attempt before either proceeds (T26/T27).
        # Unique per repetition via the barrier path. Absent for
        # single-process runs (e.g. the T27b recovery), so those
        # never wait. A timeout fails loudly instead of hanging.
        open(barrier + "." + str(os.getpid()), "w").close()
        deadline = time.time() + 30
        prefix = os.path.basename(barrier) + "."
        while len([q for q in os.listdir(store)
                   if q.startswith(prefix)]) < 2:
            if time.time() > deadline:
                print("WDI_BARRIER timeout waiting for the second "
                      "claimant", file=sys.stderr)
                sys.exit(3)
            time.sleep(0.01)
    try:
        fd = os.open(os.path.join(store, "labels", name),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        print("already exists", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
if args[:2] == ["label", "delete"]:
    name = args[-1]
    try:
        os.unlink(os.path.join(store, "labels", name))
    except OSError:
        pass
    sys.exit(0)
if args[0] == "api":
    name = args[1].rsplit("/", 1)[-1]
    if os.path.exists(os.path.join(store, "labels", name)):
        print(json.dumps({"name": name}))
        sys.exit(0)
    print("HTTP 404: Not Found", file=sys.stderr)
    sys.exit(1)
if args[:2] == ["issue", "list"]:
    label = args[args.index("--label") + 1]
    with open(lockpath, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            lag = int(open(lag_p).read())
        except OSError:
            lag = 0
        if lag > 0:
            with open(lag_p, "w") as f:
                f.write(str(lag - 1))
            rows = []
        else:
            rows = [{"number": i["number"]} for i in load()
                    if label in i["labels"]]
    print(json.dumps(rows))
    sys.exit(0)
if args[:2] == ["issue", "view"]:
    n = int(args[2])
    with open(lockpath, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        for i in load():
            if i["number"] == n:
                print(json.dumps(
                    {"number": n,
                     "labels": [{"name": lb} for lb in i["labels"]]}))
                sys.exit(0)
    print("HTTP 404: Not Found", file=sys.stderr)
    sys.exit(1)
if args[:2] == ["issue", "create"]:
    title = args[args.index("--title") + 1]
    labels = [args[k + 1] for k, a in enumerate(args)
              if a == "--label"]
    time.sleep(float(os.environ.get("WDI_CREATE_DELAY", "0.3")))
    with open(lockpath, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        issues = load()
        n = len(issues) + 1
        issues.append({"number": n, "title": title,
                       "labels": labels, "state": "open"})
        save(issues)
        with open(lag_p, "w") as f:
            f.write(os.environ.get("WDI_LAG", "2"))
    if os.environ.get("WDI_FAIL_CREATE") == "after_record":
        # #229 T27: the issue LANDED but the response is lost.
        print("Post https://api.github.com: context deadline "
              "exceeded (simulated)", file=sys.stderr)
        sys.exit(1)
    print("https://github.com/moos-labs/borsagator/issues/%d" % n)
    sys.exit(0)
if args[:2] == ["issue", "close"]:
    n = int(args[2])
    with open(lockpath, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        issues = load()
        for i in issues:
            if i["number"] == n:
                i["state"] = "closed"
        save(issues)
    sys.exit(0)
sys.exit(2)
'''


def main():
    # --- T1: the identity label is deterministic, distinct, short.
    try:
        a = "sweeps/2026-11-15/080000__sweep-lite-poul-ca__runsched-2026-11-15"
        b = "sweeps/2026-11-16/080000__sweep-lite-poul-ca__runsched-2026-11-16"
        la, la2, lb = (wdi.identity_label(a), wdi.identity_label(a),
                       wdi.identity_label(b))
        check("T1 identity label: deterministic, distinct per sweep "
              "dir, <= 50 chars",
              la == la2 and la != lb and len(la) <= 50 and
              la.startswith("digest-") and len(lb) <= 50,
              f"{la!r} vs {lb!r}")
        # A raw `digest:<sweep-dir>` would NOT fit the label limit —
        # the hash is why the label is a hash, not the raw dir.
        check("T1b raw digest:<sweep-dir> would exceed the 50-char "
              "label limit",
              len("digest:" + a) > 50, f"len={len('digest:' + a)}")
    except Exception as e:
        check("T1 identity label", False, f"{type(e).__name__}: {e}")

    # --- T2: a new sweep files exactly one issue, both labels on it.
    tmp = base = head = None
    try:
        tmp, base, head, dirs = make_repo(1)
        def t2(fake):
            rc = wdi.file_issues(base, head, tmp)
            check("T2 new sweep: one issue, both labels, exit 0",
                  rc == 0 and len(fake.issues) == 1 and
                  fake.issues[0]["labels"] == ["borsagator",
                                                wdi.identity_label(dirs[0])],
                  f"rc={rc} issues={fake.issues}")
        with_fake(t2)
    except Exception as e:
        check("T2 new sweep files one labelled issue", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T3: a CLOSED issue with the identity label blocks a re-file.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t3(fake):
            fake.issues.append({"number": 1, "title": TITLE,
                                "labels": ["borsagator",
                                           wdi.identity_label(dirs[0])],
                                "state": "closed"})
            rc = wdi.file_issues(base, head, tmp)
            check("T3 closed issue with the identity label: zero "
                  "creates, exit 0",
                  rc == 0 and len(fake.issues) == 1,
                  f"rc={rc} issues={len(fake.issues)}")
        with_fake(t3)
    except Exception as e:
        check("T3 closed issue blocks re-file", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T4: force-push replay (before=0000) files zero duplicates.
    try:
        tmp, base, head, dirs = make_repo(3)
        def t4(fake):
            for i, sd in enumerate(dirs):
                fake.issues.append({
                    "number": i + 1, "title": TITLE,
                    "labels": ["borsagator", wdi.identity_label(sd)],
                    "state": "closed" if i % 2 else "open"})
            rc = wdi.file_issues(ZERO, head, tmp)
            check("T4 force-push replay over already-filed sweeps: "
                  "zero creates, exit 0",
                  rc == 0 and len(fake.issues) == 3,
                  f"rc={rc} issues={len(fake.issues)}")
        with_fake(t4)
    except Exception as e:
        check("T4 force-push replay files zero", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T5: a sequential re-run files zero (idempotency holds).
    try:
        tmp, base, head, dirs = make_repo(2)
        def t5(fake):
            rc1 = wdi.file_issues(base, head, tmp)
            rc2 = wdi.file_issues(base, head, tmp)
            check("T5 second run over the same push: zero new "
                  "issues, exit 0",
                  rc1 == 0 and rc2 == 0 and len(fake.issues) == 2,
                  f"rc1={rc1} rc2={rc2} issues={len(fake.issues)}")
        with_fake(t5)
    except Exception as e:
        check("T5 re-run files zero", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T6: create fails AFTER the issue landed: re-check finds it,
    # no second create, exit 0 (the old blind retry double-created).
    # #223: the filing pass now fetches to confirm (1 view) and the
    # post-run reconciliation lists + fetches once more, so the
    # call counts are 3 lists / 2 views, not 2 lists / 0 views.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t6(fake):
            fake.fail_create = "after_record"
            rc = wdi.file_issues(base, head, tmp)
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            lists = [c for c in fake.calls
                     if c[:2] == ["issue", "list"]]
            views = [c for c in fake.calls
                     if c[:2] == ["issue", "view"]]
            check("T6 lost create response: one issue, one create "
                  "attempt, label re-checked after the failure, "
                  "exit 0",
                  rc == 0 and len(fake.issues) == 1 and
                  len(creates) == 1 and len(lists) == 3 and
                  len(views) == 2 and
                  fake.issues[0]["labels"] == ["borsagator",
                                                wdi.identity_label(dirs[0])],
                  f"rc={rc} issues={len(fake.issues)} "
                  f"creates={len(creates)} lists={len(lists)} "
                  f"views={len(views)}")
        with_fake(t6)
    except Exception as e:
        check("T6 lost create response is recognised", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T7: a genuine create failure fails loudly, files the other
    # sweeps, and creates no label-less issue.
    try:
        tmp, base, head, dirs = make_repo(
            2, digest_titles=[TITLE, TITLE + " market=EGX"])
        def t7(fake):
            fake.fail_create = "clean"
            fake.fail_titles = {TITLE}
            rc = wdi.file_issues(base, head, tmp)
            nolabel = [i for i in fake.issues
                       if "borsagator" not in i["labels"]]
            check("T7 genuine create failure: exit 1, other sweep "
                  "still filed, no label-less issue, claim retained "
                  "(no label delete)",
                  rc == 1 and len(fake.issues) == 1 and not nolabel
                  and fake.issues[0]["title"] == TITLE + " market=EGX"
                  and fake.deleted_labels == [],
                  f"rc={rc} issues={fake.issues} "
                  f"deleted={fake.deleted_labels}")
        with_fake(t7)
    except Exception as e:
        check("T7 genuine failure fails loudly", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T8: same title, different sweep dirs — both are filed.
    # (The old title dedup false-skipped the second sweep.)
    try:
        tmp, base, head, dirs = make_repo(2)
        def t8(fake):
            rc = wdi.file_issues(base, head, tmp)
            labels = {i["labels"][1] for i in fake.issues}
            check("T8 same title, two sweep dirs: two issues, two "
                  "distinct identity labels",
                  rc == 0 and len(fake.issues) == 2 and
                  labels == {wdi.identity_label(d) for d in dirs},
                  f"rc={rc} issues={fake.issues}")
        with_fake(t8)
    except Exception as e:
        check("T8 same title files both sweeps", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T9: the workflow no longer searches, retries blindly, or
    # files without serialization; it invokes --file.
    try:
        wf = (os.path.join(ROOT, ".github", "workflows",
                           "worker-digest-issue.yml"))
        text = open(wf, encoding="utf-8").read()
        check("T9 workflow: concurrency group serializes runs, no "
              "cancel-in-progress",
              "group: worker-digest-issue" in text and
              "cancel-in-progress: false" in text,
              "concurrency group missing")
        check("T9b workflow: no fuzzy --search dedup, no blind "
              "retry, invokes --file",
              "--search" not in text and
              "|| gh issue create" not in text and
              "--file" in text,
              "old dedup/retry text still present")
    except Exception as e:
        check("T9 workflow text", False, f"{type(e).__name__}: {e}")

    # --- T10: listing behaviour is unchanged (added manifests only;
    # before=0000 lists every manifest).
    try:
        tmp, base, head, dirs = make_repo(1)
        found = wdi.added_merge_manifests(base, head, tmp)
        check("T10 listing: added merged sweep listed",
              found == dirs, f"found={found}")
        all_found = wdi.added_merge_manifests(ZERO, head, tmp)
        check("T10b listing: before=0000 lists every manifest",
              all_found == dirs, f"found={all_found}")
        # A raw worker-run dir (no merge-manifest.json) is not listed.
        raw = os.path.join(tmp, "sweeps", "2026-11-15",
                           "080000__harvest-egx-poul__w5-harvest-001")
        os.makedirs(raw, exist_ok=True)
        with open(os.path.join(raw, "manifest.json"), "w") as f:
            f.write("{}")
        git("add", ".", cwd=tmp)
        git("commit", "-qm", "raw run", "--no-gpg-sign", cwd=tmp)
        head2 = subprocess.run(["git", "-C", tmp, "rev-parse", "HEAD"],
                               capture_output=True, text=True,
                               check=True).stdout.strip()
        found2 = wdi.added_merge_manifests(head, head2, tmp)
        check("T10c listing: raw worker-run dir without a merge "
              "manifest is not listed",
              found2 == [], f"found={found2}")
    except Exception as e:
        check("T10 listing unchanged", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T11 (#229): the identity label create is the CLAIM and
    # its failure is load-bearing. A label that exists while no
    # issue ever materializes is an orphaned claim: the run waits
    # the bounded budget, NEVER files, and fails red. (Before #229
    # the failure was swallowed and the run filed anyway — the
    # double-file hole.)
    try:
        tmp, base, head, dirs = make_repo(1)
        def t11(fake):
            fake.label_create_fails = True
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T11 orphaned claim: held label, no issue ever "
                  "materializes: red, no create, bounded waits",
                  rc == 1 and not creates and not fake.issues and
                  fake.sleeps == [2, 4, 8, 16] and
                  fake.label_creates_seen == 5 and
                  "orphaned claim" in err,
                  f"rc={rc} creates={len(creates)} "
                  f"issues={len(fake.issues)} sleeps={fake.sleeps} "
                  f"claims={fake.label_creates_seen}")
        with_fake(t11)
        def t11b(fake):
            rc = wdi.file_issues(base, head, tmp)
            label_calls = [c for c in fake.calls
                           if c[:2] == ["label", "create"]]
            create_calls = [c for c in fake.calls
                            if c[:2] == ["issue", "create"]]
            check("T11b identity label is created before the issue "
                  "create",
                  rc == 0 and len(label_calls) == 1 and
                  len(create_calls) == 1 and
                  label_calls[0][2] == wdi.identity_label(dirs[0]),
                  f"calls={fake.calls}")
        with_fake(t11b)
    except Exception as e:
        check("T11 label handling", False, f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T12: a merged sweep without digest.md files nothing.
    try:
        tmp, base, head, dirs = make_repo(1)
        os.remove(os.path.join(tmp, dirs[0], "digest.md"))
        def t12(fake):
            rc = wdi.file_issues(base, head, tmp)
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T12 missing digest.md: no create attempted, "
                  "exit 1",
                  rc == 1 and not creates and not fake.issues,
                  f"rc={rc} creates={creates}")
        with_fake(t12)
    except Exception as e:
        check("T12 missing digest.md files nothing", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T13 (#223): a listing that names an unresolvable issue
    # fails red with NO create — the incident shape. The old code
    # silently skipped (exit 0, no issue); the patched helper treats
    # the failed fetch as INDETERMINATE and fails the step loudly.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t13(fake):
            lab = wdi.identity_label(dirs[0])
            fake.list_override[lab] = [{"number": 424242}]
            rc = wdi.file_issues(base, head, tmp)
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T13 phantom listing: unresolvable issue fails "
                  "red, no create",
                  rc == 1 and not creates and not fake.issues,
                  f"rc={rc} creates={len(creates)} "
                  f"issues={len(fake.issues)}")
        with_fake(t13)
    except Exception as e:
        check("T13 phantom listing fails red", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T14 (#223): a listed issue that no longer carries the
    # identity label is REFUTED — the sweep is filed in the same
    # run instead of silently skipped.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t14(fake):
            lab = wdi.identity_label(dirs[0])
            fake.issues.append({"number": 1, "title": TITLE,
                                "labels": ["borsagator"],
                                "state": "open"})
            fake.list_override[lab] = [{"number": 1}]
            rc = wdi.file_issues(base, head, tmp)
            check("T14 refuted listing: issue without the identity "
                  "label is filed in the same run",
                  rc == 0 and len(fake.issues) == 2 and
                  fake.issues[1]["labels"] == ["borsagator", lab],
                  f"rc={rc} issues={fake.issues}")
        with_fake(t14)
    except Exception as e:
        check("T14 refuted listing files in-run", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T15-T17 (#230): the post-create reconciliation retries a
    # lagging listing with a bounded backoff. Sleeps are recorded by
    # the fake, never real. `want` is (rc, sleeps, issues, creates,
    # lists, views); stderr is checked too, so an internal exception
    # (e.g. an index error on the last round) can never pass as the
    # expected red run.
    def lag_case(name, lag, mode, sweeps, want):
        tmp = None
        try:
            tmp, base, head, dirs = make_repo(sweeps)
            def run(fake):
                fake.lag_after_create = lag
                fake.fail_create = mode
                rc, err = run_quiet(
                    lambda: wdi.file_issues(base, head, tmp))
                def n(verb):
                    return len([c for c in fake.calls
                                if c[:2] == ["issue", verb]])
                got = (rc, fake.sleeps, len(fake.issues), n("create"),
                       n("list"), n("view"))
                red = want[0] == 1
                check(name,
                      got == want and
                      ("refusing to exit green" in err) == red and
                      err.count("waiting") == len(fake.sleeps)
                      and "could not complete" not in err and
                      "Traceback" not in err and "Error" not in err,
                      f"got={got} want={want} stderr={err!r}")
            with_fake(run)
        except Exception as e:
            check(name, False, f"{type(e).__name__}: {e}")
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    lag_case("T15 lagging listing, found in round 3: green, one "
             "create, waits 2+4, no duplicate",
             2, None, 1, (0, [2, 4], 1, 1, 4, 1))
    lag_case("T15b lag fits the budget exactly (found in the last "
             "round 5): green",
             4, None, 1, (0, [2, 4, 8, 16], 1, 1, 6, 1))
    lag_case("T15c two just-created sweeps share ONE wait budget: "
             "green, waits 2 only",
             2, None, 2, (0, [2], 2, 2, 6, 2))
    lag_case("T16 filing genuinely absent (create reported success, "
             "stored nothing): red after exactly 5 rounds",
             0, "phantom_success", 1, (1, [2, 4, 8, 16], 0, 1, 6, 0))
    lag_case("T16b two absent sweeps: red, still only 30 s of waits",
             0, "phantom_success", 2, (1, [2, 4, 8, 16], 0, 2, 12, 0))
    lag_case("T17 budget exhausted (listing never catches up in 5 "
             "rounds): red, one create, no duplicate",
             5, None, 1, (1, [2, 4, 8, 16], 1, 1, 6, 0))

    # --- T18 (#230): only a sweep created in this run is retried.
    # Each case is one check with no waiting.
    tmp = None
    try:
        tmp, base, head, dirs = make_repo(1)
        lab = wdi.identity_label(dirs[0])
        def t18(fake):
            fake.issues.append({"number": 1, "title": TITLE,
                                "labels": ["borsagator", lab],
                                "state": "open"})
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            check("T18 skipped sweep: green, no waiting",
                  rc == 0 and fake.sleeps == [] and err == "",
                  f"rc={rc} sleeps={fake.sleeps} stderr={err!r}")
        with_fake(t18)
        def t18b(fake):
            fake.list_override[lab] = [{"number": 424242}]
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            check("T18b indeterminate fetch: red, no waiting",
                  rc == 1 and fake.sleeps == [],
                  f"rc={rc} sleeps={fake.sleeps}")
        with_fake(t18b)
        def t18c(fake):
            fake.hide_after_view = True
            fake.issues.append({"number": 1, "title": TITLE,
                                "labels": ["borsagator", lab],
                                "state": "open"})
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            lists = [c for c in fake.calls if c[:2] == ["issue", "list"]]
            check("T18c skipped sweep missing at reconciliation: red "
                  "at once, no waiting, no create",
                  rc == 1 and fake.sleeps == [] and len(lists) == 2
                  and "refusing to exit green" in err
                  and not [c for c in fake.calls
                           if c[:2] == ["issue", "create"]],
                  f"rc={rc} sleeps={fake.sleeps} lists={len(lists)}")
        with_fake(t18c)
    except Exception as e:
        check("T18 no retry outside a created sweep", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T19 (#230): a verification ERROR on a just-created sweep
    # is final at once. The fault is one-shot, so a wrongful retry
    # would succeed on the next read and turn the run green.
    def fault_case(name, fault, views_want):
        tmp = None
        try:
            tmp, base, head, dirs = make_repo(1)
            def run(fake):
                fake.fault_after_create = fault
                rc, err = run_quiet(
                    lambda: wdi.file_issues(base, head, tmp))
                n = lambda verb: len([c for c in fake.calls
                                      if c[:2] == ["issue", verb]])
                got = (rc, fake.sleeps, len(fake.issues), n("create"),
                       n("list"), n("view"))
                check(name,
                      got == (1, [], 1, 1, 2, views_want) and
                      "could not complete" in err and
                      "refusing to exit green" in err and
                      "waiting" not in err and "Traceback" not in err,
                      f"got={got} stderr={err!r}")
            with_fake(run)
        except Exception as e:
            check(name, False, f"{type(e).__name__}: {e}")
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    fault_case("T19 list failure after create: one attempt, red, "
               "no wait", "list_rc", 0)
    fault_case("T19b malformed listing after create: one attempt, "
               "red, no wait", "list_garbage", 0)
    fault_case("T19c failed fetch after create: one attempt, red, "
               "no wait", "view_fail", 1)

    # --- T20 (#229): the claim is a compare-and-swap — exactly
    # one of two claims on the same sweep wins; the loser is held
    # and confirmed by an entity GET; a failed GET is
    # indeterminate, never "absent".
    try:
        sd = "sweeps/2026-11-15/080000__sweep-lite-poul-ca__runsched-2026-11-15"
        def t20(fake):
            first = wdi.claim_sweep(sd)
            second = wdi.claim_sweep(sd)
            apis = [c for c in fake.calls if c[0] == "api"]
            check("T20 claim CAS: first claimed, second held, "
                  "confirmed by one entity GET",
                  first == "claimed" and second == "held" and
                  len(apis) == 1 and not fake.issues,
                  f"first={first} second={second} apis={len(apis)}")
        with_fake(t20)
        def t20b(fake):
            fake.label_api_down = True
            fake.labels.add(wdi.identity_label(sd))
            try:
                wdi.claim_sweep(sd)
                outcome = "no raise"
            except wdi.VerificationIndeterminate:
                outcome = "indeterminate"
            check("T20b failed claim GET is indeterminate, never "
                  "absent",
                  outcome == "indeterminate" and not fake.issues,
                  outcome)
        with_fake(t20b)
        def t20c(fake):
            fake.label_api_garbage = True
            fake.labels.add(wdi.identity_label(sd))
            try:
                wdi.claim_sweep(sd)
                outcome = "no raise"
            except wdi.VerificationIndeterminate:
                outcome = "indeterminate"
            check("T20c malformed claim GET payload is "
                  "indeterminate, never absent",
                  outcome == "indeterminate" and not fake.issues,
                  outcome)
        with_fake(t20c)
    except Exception as e:
        check("T20 claim CAS", False, f"{type(e).__name__}: {e}")

    # --- T21 (#229): migration / manual repair of an orphaned
    # claim — the run goes red and NEVER deletes the label; only
    # after the OPERATOR deletes it (reconciled: no create landed,
    # no active holder) does a re-run claim and file, exactly once.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t21(fake):
            fake.label_create_fails = True
            rc1 = wdi.file_issues(base, head, tmp)
            helper_deletes = list(fake.deleted_labels)
            # Operator reconciliation: establish no create landed,
            # then delete the label — the ONLY delete in this test.
            fake.run(["label", "delete", "--yes",
                      wdi.identity_label(dirs[0])])
            rc2 = wdi.file_issues(base, head, tmp)
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T21 orphaned claim: red without deleting; files "
                  "only after operator label delete, exit 0, one "
                  "issue",
                  rc1 == 1 and helper_deletes == [] and
                  fake.deleted_labels == [wdi.identity_label(dirs[0])]
                  and rc2 == 0 and len(fake.issues) == 1 and
                  len(creates) == 1,
                  f"rc1={rc1} rc2={rc2} "
                  f"helper_deletes={helper_deletes} "
                  f"issues={len(fake.issues)}")
        with_fake(t21)
    except Exception as e:
        check("T21 orphan repair is manual-only", False,
              f"{type(e).__name__}: {e}")

    # --- T22 (#229): a claim loser whose sibling files mid-wait
    # skips green on the fetch-confirmed issue and NEVER creates.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t22(fake):
            fake.label_create_fails = True
            fake.appear_after_lists = 1
            rc = wdi.file_issues(base, head, tmp)
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T22 loser skips on the winner's issue: green, "
                  "zero creates, bounded wait",
                  rc == 0 and not creates and
                  len(fake.issues) == 1 and fake.sleeps == [2],
                  f"rc={rc} creates={len(creates)} "
                  f"issues={len(fake.issues)} sleeps={fake.sleeps}")
        with_fake(t22)
    except Exception as e:
        check("T22 loser skips on sibling issue", False,
              f"{type(e).__name__}: {e}")

    # --- T23 (#229): a duplicate pair raced into existence by a
    # non-claiming actor is detect-and-red — NOTHING is closed or
    # edited (a close alone leaves the identity label visible to
    # --state all), both issues stay open, and the error names
    # the pair, the survivor and the label-removal repair.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t23(fake):
            fake.race_on_create = True
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            keep = fake.issues[0]["number"]
            extra = fake.issues[1]["number"]
            check("T23 duplicate: red, no close/edit, pair + "
                  "keep-lowest + label removal named",
                  rc == 1 and len(fake.issues) == 2 and
                  all(i["state"] == "open" for i in fake.issues) and
                  "duplicate digest issues" in err and
                  f"Keeping #{keep}" in err and
                  f"close it AND remove label" in err and
                  str(extra) in err,
                  f"rc={rc} states={[i['state'] for i in fake.issues]} "
                  f"stderr={err!r}")
        with_fake(t23)
    except Exception as e:
        check("T23 duplicate detect-and-red", False,
              f"{type(e).__name__}: {e}")

    # --- T23b (#229): same when the rival's issue lands AFTER
    # ours (we hold the lower number): still red, still untouched.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t23b(fake):
            fake.race_after_create = True
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            own = fake.issues[0]["number"]
            other = fake.issues[1]["number"]
            check("T23b duplicate (rival higher): red, no close, "
                  "the extra is named",
                  rc == 1 and
                  all(i["state"] == "open" for i in fake.issues) and
                  f"Keeping #{own}" in err and str(other) in err,
                  f"rc={rc} stderr={err!r}")
        with_fake(t23b)
    except Exception as e:
        check("T23b duplicate rival-higher red", False,
              f"{type(e).__name__}: {e}")

    # --- T23c (#229): a duplicate that is CLOSED but still
    # carries the identity label still counts — the check lists
    # --state all, so the pair is red and the repair guidance's
    # label removal is what matters, not the close.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t23c(fake):
            lab = wdi.identity_label(dirs[0])
            fake.labels.add(lab)
            fake.issues.append({"number": 1, "title": TITLE,
                                "labels": ["borsagator", lab],
                                "state": "open"})
            fake.issues.append({"number": 2, "title": TITLE,
                                "labels": ["borsagator", lab],
                                "state": "closed"})
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            check("T23c closed-but-still-labeled duplicate: red, "
                  "untouched, label removal named, detected in the "
                  "skip branch (not deferred to reconciliation)",
                  rc == 1 and
                  fake.issues[0]["state"] == "open" and
                  fake.issues[1]["state"] == "closed" and
                  "[1, 2]" in err and "Keeping #1" in err and
                  "remove label" in err and "--state all" in err and
                  "could not complete" not in err,
                  f"rc={rc} stderr={err!r}")
        with_fake(t23c)
    except Exception as e:
        check("T23c closed-labeled duplicate red", False,
              f"{type(e).__name__}: {e}")

    # --- T23d (#229): a duplicate discovered by the lost-response
    # RE-CHECK (create landed but reported failure; the recheck
    # finds two confirmed issues) is red with the duplicate
    # message — the failed sweep is excluded from reconciliation,
    # so this raise is the ONLY detection on that path.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t23d(fake):
            fake.race_on_create = True
            fake.fail_create = "after_record"
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            check("T23d duplicate at lost-response recheck: red, "
                  "duplicate named at the recheck (not deferred to "
                  "reconciliation), claim retained",
                  rc == 1 and len(fake.issues) == 2 and
                  "duplicate digest issues" in err and
                  "Keeping #1" in err and
                  "could not complete" not in err and
                  fake.deleted_labels == [],
                  f"rc={rc} issues={len(fake.issues)} "
                  f"deleted={fake.deleted_labels} stderr={err!r}")
        with_fake(t23d)
    except Exception as e:
        check("T23d duplicate at recheck red", False,
              f"{type(e).__name__}: {e}")

    # --- T24 (#229): a pre-existing duplicated pair is detected
    # by ANY run touching the sweep — red, no create, no close of
    # other actors' issues.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t24(fake):
            lab = wdi.identity_label(dirs[0])
            fake.labels.add(lab)
            fake.issues.append({"number": 1, "title": TITLE,
                                "labels": ["borsagator", lab],
                                "state": "closed"})
            fake.issues.append({"number": 2, "title": TITLE,
                                "labels": ["borsagator", lab],
                                "state": "open"})
            rc, err = run_quiet(
                lambda: wdi.file_issues(base, head, tmp))
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T24 pre-existing pair: red, no create, no "
                  "close, both numbers named",
                  rc == 1 and not creates and
                  "[1, 2]" in err and "Keeping #1" in err and
                  fake.issues[0]["state"] == "closed" and
                  fake.issues[1]["state"] == "open" and
                  "could not complete" not in err,
                  f"rc={rc} creates={len(creates)} stderr={err!r}")
        with_fake(t24)
    except Exception as e:
        check("T24 pre-existing pair detected red", False,
              f"{type(e).__name__}: {e}")

    # --- T25 (#229): the loser exits 0 ONLY with a fetch-confirmed
    # exactly-one issue — a held claim whose listing shows a
    # phantom fails red (no skip on an unverifiable listing).
    try:
        tmp, base, head, dirs = make_repo(1)
        def t25(fake):
            fake.label_create_fails = True
            lab = wdi.identity_label(dirs[0])
            fake.list_override[lab] = [{"number": 424242}]
            rc = wdi.file_issues(base, head, tmp)
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T25 held claim + phantom listing: red, no "
                  "create, no wait",
                  rc == 1 and not creates and not fake.issues and
                  fake.sleeps == [],
                  f"rc={rc} creates={len(creates)} "
                  f"sleeps={fake.sleeps}")
        with_fake(t25)
    except Exception as e:
        check("T25 held claim phantom listing red", False,
              f"{type(e).__name__}: {e}")

    # --- T25b (#229): the fault model that forbids auto-release:
    # create LANDS but reports failure AND the listing lags past
    # the re-check. The run must go red with the claim RETAINED
    # (no label delete); once the lag clears, a re-run skips on
    # the fetch-confirmed issue — and no second issue ever appears.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t25b(fake):
            fake.fail_create = "after_record"
            fake.lag_after_create = 3
            rc1 = wdi.file_issues(base, head, tmp)
            # lag consumed by the failed re-check (1); 2 remain.
            rc2 = wdi.file_issues(base, head, tmp)
            creates = [c for c in fake.calls
                       if c[:2] == ["issue", "create"]]
            check("T25b lost response + lagged listing: red, claim "
                  "retained, re-run skips green, still one issue",
                  rc1 == 1 and fake.deleted_labels == [] and
                  rc2 == 0 and len(fake.issues) == 1 and
                  len(creates) == 1 and fake.sleeps == [2, 4],
                  f"rc1={rc1} rc2={rc2} "
                  f"deleted={fake.deleted_labels} "
                  f"issues={len(fake.issues)} "
                  f"creates={len(creates)} sleeps={fake.sleeps}")
        with_fake(t25b)
    except Exception as e:
        check("T25b lost response retains claim", False,
              f"{type(e).__name__}: {e}")

    # --- T26 (#229): two REAL concurrent helper processes race the
    # same push against a file-backed fake `gh` whose label create
    # is an atomic O_EXCL — the actual claim mechanism, no mocked
    # serialization. A barrier inside the fake (WDI_BARRIER)
    # guarantees both processes reach the competing claim attempt;
    # the 0.3 s create delay only exercises the loser's wait.
    # Exactly one issue is filed and both runs exit 0, on every
    # repetition.
    tmp = None
    try:
        tmp, base, head, dirs = make_repo(1)
        fakebin = os.path.join(tmp, "bin")
        os.makedirs(fakebin)
        gh_path = os.path.join(fakebin, "gh")
        with open(gh_path, "w") as f:
            f.write(FAKE_GH_EXECUTABLE)
        os.chmod(gh_path, 0o755)
        script = os.path.join(SCRIPTS, "worker_digest_issue.py")
        ok_all, detail = True, ""
        for it in range(3):
            store = os.path.join(tmp, f"store-{it}")
            os.makedirs(store)
            env = dict(os.environ)
            env["PATH"] = fakebin + os.pathsep + env.get("PATH", "")
            env["WDI_STORE"] = store
            env["WDI_LAG"] = "0"
            env["WDI_CREATE_DELAY"] = "0.3"
            env["WDI_BARRIER"] = os.path.join(store, "barrier")
            cmd = [sys.executable, script, "--before", base,
                   "--after", head, "--repo-dir", tmp, "--file"]
            procs = [subprocess.Popen(
                cmd, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True) for _ in range(2)]
            outs = [p.communicate(timeout=180) for p in procs]
            rcs = [p.returncode for p in procs]
            with open(os.path.join(store, "issues.json")) as f:
                issues = json.load(f)
            filings = sum("filing digest issue" in (o[0] or "")
                          for o in outs)
            if not (rcs == [0, 0] and len(issues) == 1 and
                    filings == 1):
                ok_all = False
                detail = (f"iter={it} rcs={rcs} "
                          f"issues={len(issues)} filings={filings}")
                break
        check("T26 real two-process race: exactly one issue, both "
              "runs green, 3 repetitions",
              ok_all, detail)
    except Exception as e:
        check("T26 real two-process race", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    # --- T27 (#229): two REAL processes, and the WINNER's create
    # lands but reports failure while the listing stays hidden
    # past every budget. No process may file a second issue, the
    # claim must survive on disk, and only clearing the listing
    # lag — with the claim RETAINED — turns a re-run green, with
    # still exactly one issue and no second create. (The
    # operator-delete repair after a create that did NOT land is
    # T21's job.) Delays
    # are zeroed in a COPY of the script so the suite stays fast;
    # every other byte is the shipped helper.
    tmp = None
    try:
        tmp, base, head, dirs = make_repo(1)
        fakebin = os.path.join(tmp, "bin")
        os.makedirs(fakebin)
        gh_path = os.path.join(fakebin, "gh")
        with open(gh_path, "w") as f:
            f.write(FAKE_GH_EXECUTABLE)
        os.chmod(gh_path, 0o755)
        src = open(os.path.join(SCRIPTS, "worker_digest_issue.py"),
                   encoding="utf-8").read()
        zeroed = src.replace("RECONCILE_RETRY_DELAYS = (2, 4, 8, 16)",
                             "RECONCILE_RETRY_DELAYS = (0, 0, 0, 0)")
        assert zeroed != src
        script = os.path.join(tmp, "worker_digest_issue_zeroed.py")
        with open(script, "w") as f:
            f.write(zeroed)
        store = os.path.join(tmp, "store-27")
        os.makedirs(store)
        env = dict(os.environ)
        env["PATH"] = fakebin + os.pathsep + env.get("PATH", "")
        env["WDI_STORE"] = store
        env["WDI_LAG"] = "1000"
        env["WDI_CREATE_DELAY"] = "0.1"
        env["WDI_FAIL_CREATE"] = "after_record"
        env["WDI_BARRIER"] = os.path.join(store, "barrier")
        cmd = [sys.executable, script, "--before", base,
               "--after", head, "--repo-dir", tmp, "--file"]
        procs = [subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True) for _ in range(2)]
        outs = [p.communicate(timeout=180) for p in procs]
        rcs = sorted(p.returncode for p in procs)
        with open(os.path.join(store, "issues.json")) as f:
            issues = json.load(f)
        label = wdi.identity_label(dirs[0])
        claim_file = os.path.join(store, "labels", label)
        check("T27 lost response + hidden listing, real race: both "
              "red, claim retained, exactly one issue",
              rcs == [1, 1] and len(issues) == 1 and
              os.path.isfile(claim_file),
              f"rcs={rcs} issues={len(issues)} "
              f"claim_retained={os.path.isfile(claim_file)}")
        # Manual reconciliation here finds the landed issue in
        # authoritative history, so the claim is RETAINED — on
        # real GitHub deleting a label strips it FROM the issue,
        # so unlinking it in the fake (which would leave the
        # issue's labels intact) would fake a recovery real
        # operators cannot get. Only the listing lag clears; the
        # re-run must skip on the fetch-confirmed exactly-one
        # without a second create. Single process: no barrier.
        with open(os.path.join(store, "lag"), "w") as f:
            f.write("0")
        env["WDI_LAG"] = "0"
        env.pop("WDI_BARRIER", None)
        p3 = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
        p3out, p3err = p3.communicate(timeout=180)
        with open(os.path.join(store, "issues.json")) as f:
            issues = json.load(f)
        check("T27b lag cleared, claim retained: re-run green, "
              "still exactly one issue, no second create, claim "
              "kept",
              p3.returncode == 0 and len(issues) == 1 and
              os.path.isfile(claim_file) and
              "filing digest issue" not in (p3out or ""),
              f"rc={p3.returncode} issues={len(issues)} "
              f"claim_kept={os.path.isfile(claim_file)} "
              f"refiled={'filing digest issue' in (p3out or '')}")
    except Exception as e:
        check("T27 real lost-response race", False,
              f"{type(e).__name__}: {e}")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
