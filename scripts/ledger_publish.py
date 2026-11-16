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
run itself).

Modes:
  sweep path (orchestrate.yml):  ledger_publish.py --digest digest/digest.md --commit
  guard path (ledger-guard.yml): ledger_publish.py --commit --fail-hard
  local/dry:                     ledger_publish.py [--digest PATH]

Idempotency: when the committed ledger already records the live
archive tree, the rerun is skipped; when a rerun produces
byte-identical outputs, nothing is committed. Weights published by a
sweep take effect on the NEXT sweep's ensemble (the ensemble runs
before the archive commit) — one sweep of latency, by construction.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_DIR = os.path.join(ROOT, "ledger")
LEDGER_PY = os.path.join(ROOT, "scripts", "ledger.py")
FILES = ("ledger.json", "ledger.md", "weights.json")
API = "https://api.github.com/repos/moos-labs/borsagator"
FAMILIES = ("price-forecast", "technicals", "sentiment", "agent",
            "fundamentals")


def log(msg):
    print(f"[ledger-publish] {msg}", flush=True)


def _token():
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def api_get(path):
    headers = {"User-Agent": "borsagator-ledger-publish"}
    tok = _token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(API + path, headers=headers)
    with urllib.request.build_opener().open(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def live_archive_tree_sha():
    ref = api_get("/git/ref/heads/archive")
    commit = api_get(f"/git/commits/{ref['object']['sha']}")
    return commit["tree"]["sha"]


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def committed_ledger():
    return _read_json(os.path.join(LEDGER_DIR, "ledger.json"))


def run_ledger(out_dir):
    """Run scripts/ledger.py into out_dir and validate its output.
    Returns the parsed ledger.json; raises RuntimeError on any
    degraded run (ledger.py itself never exits non-zero — it catches
    everything and still writes zeroed outputs on a fetch failure,
    so the validation here is the failure detector)."""
    r = subprocess.run([sys.executable, LEDGER_PY, out_dir],
                       capture_output=True, text=True, timeout=1200)
    p = os.path.join(out_dir, "ledger.json")
    if not os.path.exists(p):
        raise RuntimeError("ledger.py wrote no ledger.json "
                           f"(stdout tail: {r.stdout.strip()[-200:]})")
    doc = _read_json(p)
    if doc is None:
        raise RuntimeError("ledger.json is not parseable JSON")
    if not (doc.get("source") or {}).get("tree_sha"):
        raise RuntimeError("degraded run: no archive tree sha "
                           "(the archive fetch failed — see gaps)")
    for g in doc.get("gaps") or []:
        if g.startswith("archive tree could not be fetched"):
            raise RuntimeError(f"degraded run: {g}")
    if (doc.get("counts") or {}).get("sweeps", 0) == 0:
        raise RuntimeError("degraded run: zero sweeps read from the "
                           "archive tree")
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


def section_published(old, new, old_w, new_w):
    sha = str(new["source"]["tree_sha"])[:8]
    delta = ""
    if old and old["counts"]["matured"] != new["counts"]["matured"]:
        delta = (f" (matured {old['counts']['matured']} → "
                 f"{new['counts']['matured']})")
    return ("## 📒 Calibration ledger\n\n"
            f"Ledger rerun after this sweep (archive tree `{sha}`): "
            f"{_counts_line(new)}{delta}."
            f"{_weights_sentence(old_w, new_w)} "
            "Published to `ledger/` on main; the new weights take "
            "effect from the next sweep.")


def section_unchanged(doc):
    sha = str(doc["source"]["tree_sha"])[:8]
    return ("## 📒 Calibration ledger\n\n"
            f"Ledger already current for archive tree `{sha}`: "
            f"{_counts_line(doc)}. Nothing to publish.")


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


def git_publish(new_doc):
    """Commit ledger/ and push to main. Returns True on success."""
    git("config", "user.name", "borsagator-ledger")
    git("config", "user.email", "moos@sherbeeny.com")
    if git("add", "ledger/").returncode != 0:
        return False
    c = new_doc["counts"]
    msg = (f"Ledger: tree {str(new_doc['source']['tree_sha'])[:8]} — "
           f"{c['forecasts']} forecasts, {c['matured']} matured, "
           f"{c['pending']} pending, {c['invalid']} invalid (#64)")
    if git("commit", "-m", msg).returncode != 0:
        log("git commit failed (nothing staged?)")
        return False
    if git("push", "origin", "HEAD:main").returncode == 0:
        return True
    # Someone else pushed to main in the meantime (board-sync does):
    # rebase once onto the new main and retry.
    log("push rejected — rebasing onto origin/main and retrying")
    if git("fetch", "origin", "main").returncode != 0:
        return False
    if git("rebase", "origin/main").returncode != 0:
        git("rebase", "--abort")
        return False
    return git("push", "origin", "HEAD:main").returncode == 0


def fail(reason, digest_path, fail_hard):
    log(f"FAILED: {reason}")
    append_digest(digest_path, section_failed(reason))
    return 1 if fail_hard else 0


def publish(commit, digest_path, fail_hard):
    old = committed_ledger()
    old_w = _read_json(os.path.join(LEDGER_DIR, "weights.json"))
    try:
        live_tree = live_archive_tree_sha()
    except Exception as e:
        live_tree = None
        log(f"could not read the live archive tree ({e}); running anyway")
    if old and live_tree and \
            (old.get("source") or {}).get("tree_sha") == live_tree:
        log(f"archive tree {live_tree[:8]} already published — skipping")
        append_digest(digest_path, section_unchanged(old))
        return 0
    tmp = tempfile.mkdtemp(prefix="ledger-run-")
    try:
        new = run_ledger(tmp)
    except Exception as e:
        return fail(str(e), digest_path, fail_hard)
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
    if commit and not git_publish(new):
        return fail("git push of ledger/ to main failed",
                    digest_path, fail_hard)
    append_digest(digest_path, section_published(old, new, old_w, new_w))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--digest", default=None,
                    help="digest markdown file to append the ledger "
                         "section (or ⚠️ failure line) to")
    ap.add_argument("--commit", action="store_true",
                    help="commit + push ledger/ to main when changed")
    ap.add_argument("--fail-hard", action="store_true",
                    help="exit non-zero on failure (guard mode)")
    a = ap.parse_args()
    try:
        return publish(a.commit, a.digest, a.fail_hard)
    except Exception as e:  # the publisher must never crash a sweep
        return fail(f"unexpected publisher error: {e}",
                    a.digest, a.fail_hard)


if __name__ == "__main__":
    sys.exit(main())
