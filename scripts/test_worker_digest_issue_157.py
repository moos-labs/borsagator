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
import json
import os
import shutil
import subprocess
import sys
import tempfile

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
        self.label_create_fails = False
        # #223: extra rows a listing returns that the store does not
        # hold (a phantom / refuted listing). {label: [{"number": n}]}
        self.list_override = {}

    def _next_number(self):
        return len(self.issues) + 1

    def run(self, args):
        self.calls.append(list(args))
        if args[:2] == ["issue", "list"]:
            label = args[args.index("--label") + 1]
            state = args[args.index("--state") + 1]
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
                    return Proc(0, json.dumps(
                        {"number": n,
                         "labels": [{"name": lb} for lb in i["labels"]]}))
            return Proc(1, "", "HTTP 404: Not Found")
        if args[:2] == ["label", "create"]:
            if self.label_create_fails:
                return Proc(1, "", "already exists")
            self.labels.add(args[2])
            return Proc(0, "")
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
            if fail == "after_record":
                self.issues.append(rec)
                return Proc(1, "",
                            "Post https://api.github.com: context "
                            "deadline exceeded (simulated)")
            if fail == "clean":
                return Proc(1, "", "HTTP 500 (simulated)")
            self.issues.append(rec)
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
    old = wdi.run_gh
    wdi.run_gh = fake.run
    try:
        fn(fake)
    finally:
        wdi.run_gh = old


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
                  "still filed, no label-less issue",
                  rc == 1 and len(fake.issues) == 1 and not nolabel
                  and fake.issues[0]["title"] == TITLE + " market=EGX",
                  f"rc={rc} issues={fake.issues}")
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

    # --- T11: the identity label is created before the issue, and a
    # failing label create does not block filing.
    try:
        tmp, base, head, dirs = make_repo(1)
        def t11(fake):
            fake.label_create_fails = True
            rc = wdi.file_issues(base, head, tmp)
            check("T11 label-create failure is tolerated, issue "
                  "still filed with its identity label",
                  rc == 0 and len(fake.issues) == 1 and
                  fake.issues[0]["labels"][1] ==
                  wdi.identity_label(dirs[0]),
                  f"rc={rc} issues={fake.issues}")
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

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
