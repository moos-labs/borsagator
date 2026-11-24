#!/usr/bin/env python3
"""Controls for the private EGX challenge-body store (issue #589).

Run directly:  python3 scripts/test_challenge_store.py
Stdlib only, no network: every body below is a SIMULATED challenge
page built in this file — clearly labelled, never a live EGX
capture. The store is exercised against temp directories only.

Required controls (issue #589 spec):
- size cap: a body over 64 KiB is stored truncated to the cap
  with the truncation marker appended, and the record says so;
- inert .txt enforcement: captures are .txt files (0600 in a
  0700 dir) whose bytes are clean UTF-8 text even when the body
  arrived as binary junk with NULs;
- bounded retention: only the most recent 200 captures survive
  a prune; unrelated files are untouched;
- metadata-only public record: the capture record and the
  enumerator's public sub-records carry digests/counts/state
  and NO body content and NO stored filename;
- disabled by default: no configured store dir -> state
  "disabled" and nothing written anywhere;
- a store dir inside the repo checkout is refused;
- hooks: probe_live_access and enumerate_listing hand challenge
  bodies to the store and keep non-challenge traffic untouched.
"""
import hashlib
import json
import os
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import challenge_store as S
import top30_enumerate as E

ENV = S.STORE_ENV
SENTINEL = "SENTINEL-CHALLENGE-BODY-589"


def challenge_page(extra=""):
    """A SIMULATED TSPD-style challenge shell (not a live
    capture): tspd marker, human-check text, no result links."""
    return ("<html><head><title>EGX</title></head><body>"
            "<script src=\"/tspd.js\"></script>"
            "<p>Please verify you are human</p>"
            "<p>%s</p>%s</body></html>" % (SENTINEL, extra))


def _set_env(value):
    old = os.environ.get(ENV)
    if value is None:
        os.environ.pop(ENV, None)
    else:
        os.environ[ENV] = value
    return old


def _restore_env(old):
    if old is None:
        os.environ.pop(ENV, None)
    else:
        os.environ[ENV] = old


def case_cap_truncation():
    store = tempfile.mkdtemp(prefix="challenge-store-")
    body = challenge_page("x" * (200 * 1024))
    meta = S.capture_challenge_body("https://example.invalid/p",
                                    200, body, store_dir=store)
    if meta["state"] != "stored" or not meta["truncated"]:
        return False, "state=%s truncated=%s" % (meta["state"],
                                                 meta["truncated"])
    path = os.path.join(store, meta["stored_name"])
    data = open(path, "rb").read()
    marker = S.TRUNCATION_MARKER.encode("utf-8")
    ok = (data.endswith(marker)
          and len(data) - len(marker) <= S.MAX_BODY_BYTES
          and meta["stored_bytes"] == len(data)
          and meta["stored_sha256"]
          == hashlib.sha256(data).hexdigest()
          and meta["body_bytes"] == len(body.encode("utf-8"))
          and meta["body_sha256"]
          == hashlib.sha256(body.encode("utf-8")).hexdigest())
    return ok, "stored_bytes=%d body_bytes=%d" % (len(data),
                                                  meta["body_bytes"])


def case_under_cap_verbatim():
    store = tempfile.mkdtemp(prefix="challenge-store-")
    body = challenge_page()
    meta = S.capture_challenge_body("https://example.invalid/p",
                                    403, body, store_dir=store)
    if meta["state"] != "stored" or meta["truncated"]:
        return False, "state=%s truncated=%s" % (meta["state"],
                                                 meta["truncated"])
    text = open(os.path.join(store, meta["stored_name"]),
                encoding="utf-8").read()
    return text == body, "verbatim=%s" % (text == body)


def case_inert_txt():
    store = tempfile.mkdtemp(prefix="challenge-store-")
    raw = (b"<script>alert(1)</script>\x00\xff\xfe binary "
           b"junk \x00 tspd")
    meta = S.capture_challenge_body("https://example.invalid/p",
                                    200, raw, store_dir=store)
    if meta["state"] != "stored":
        return False, "state=%s detail=%s" % (meta["state"],
                                              meta["detail"])
    path = os.path.join(store, meta["stored_name"])
    data = open(path, "rb").read()
    try:
        data.decode("utf-8")
        clean_utf8 = True
    except UnicodeDecodeError:
        clean_utf8 = False
    ok = (meta["stored_name"].endswith(".txt")
          and clean_utf8
          and b"\x00" not in data
          and stat.S_IMODE(os.stat(path).st_mode) == 0o600
          and stat.S_IMODE(os.stat(store).st_mode) == 0o700)
    return ok, "name=%s utf8=%s" % (meta["stored_name"],
                                    clean_utf8)


def case_retention_pruning():
    store = tempfile.mkdtemp(prefix="challenge-store-")
    for i in range(S.RETENTION):
        name = "20200101T000000Z-fake%012d.txt" % i
        with open(os.path.join(store, name), "w") as f:
            f.write("old simulated capture %d" % i)
    keep = os.path.join(store, "notes.md")
    with open(keep, "w") as f:
        f.write("not a capture; pruning must not touch this")
    names = []
    for i in range(3):
        meta = S.capture_challenge_body(
            "https://example.invalid/p", 200,
            challenge_page("fresh %d" % i), store_dir=store)
        if meta["state"] != "stored":
            return False, "capture %d state=%s" % (i,
                                                   meta["state"])
        names.append(meta["stored_name"])
    txts = sorted(n for n in os.listdir(store)
                  if n.endswith(".txt"))
    ok = (len(txts) == S.RETENTION
          and all(n in txts for n in names)
          and os.path.exists(keep))
    return ok, "txts=%d new_present=%s" % (
        len(txts), all(n in txts for n in names))


def case_metadata_only():
    store = tempfile.mkdtemp(prefix="challenge-store-")
    body = challenge_page()
    meta = S.capture_challenge_body("https://example.invalid/p",
                                    200, body, store_dir=store)
    blob = json.dumps(meta)
    old = _set_env(store)
    try:
        sub = E._private_capture("https://example.invalid/p", 200,
                                 body)
    finally:
        _restore_env(old)
    sub_blob = json.dumps(sub)
    ok = (SENTINEL not in blob
          and SENTINEL not in sub_blob
          and "stored_name" not in sub
          and sub["state"] == "stored"
          and sub["stored_sha256"] == meta["stored_sha256"]
          and meta["body_sha256"]
          == hashlib.sha256(body.encode("utf-8")).hexdigest())
    return ok, "sub=%s" % (sub,)


def case_disabled_default():
    old = _set_env(None)
    try:
        meta = S.capture_challenge_body(
            "https://example.invalid/p", 200, challenge_page())
    finally:
        _restore_env(old)
    ok = (meta["state"] == "disabled"
          and meta["stored_name"] is None
          and meta["stored_sha256"] is None
          and meta["body_sha256"] is not None)
    return ok, "state=%s" % meta["state"]


def case_repo_refusal():
    inside = os.path.join(HERE, "challenge-store-must-not-exist")
    meta = S.capture_challenge_body("https://example.invalid/p",
                                    200, challenge_page(),
                                    store_dir=inside)
    ok = (meta["state"] == "failed"
          and not os.path.exists(inside))
    return ok, "state=%s detail=%s" % (meta["state"],
                                       meta["detail"])


def _fake_fetcher(body, status=200):
    def fetch(url):
        return {"status": status, "body": body,
                "fetched_at": "2026-11-20T00:00:00Z"}
    return fetch


def case_probe_hook_stores():
    store = tempfile.mkdtemp(prefix="challenge-store-")
    old = _set_env(store)
    try:
        rec = E.probe_live_access(
            fetcher=_fake_fetcher(challenge_page()))
        plain = E.probe_live_access(fetcher=_fake_fetcher(
            "<html><body><div>no results found</div>"
            "</body></html>"))
    finally:
        _restore_env(old)
    pc = rec.get("private_capture") or {}
    files = [n for n in os.listdir(store) if n.endswith(".txt")]
    ok = (rec["challenge"] is True
          and pc.get("state") == "stored"
          and len(files) == 1
          and SENTINEL not in json.dumps(rec)
          and plain.get("private_capture") is None)
    return ok, "pc=%s files=%d" % (pc, len(files))


def case_probe_hook_disabled():
    old = _set_env(None)
    try:
        rec = E.probe_live_access(
            fetcher=_fake_fetcher(challenge_page()))
    finally:
        _restore_env(old)
    pc = rec.get("private_capture") or {}
    return pc.get("state") == "disabled", "pc=%s" % (pc,)


def case_enumerate_hook():
    store = tempfile.mkdtemp(prefix="challenge-store-")
    old = _set_env(store)
    try:
        listing = {"code": "POUL", "isin": "EGS02051C018",
                   "issuer": "Cairo Poultry"}
        rec = E.enumerate_listing(
            listing, _fake_fetcher(challenge_page()))
    finally:
        _restore_env(old)
    fails = [f for f in rec["failures"]
             if f["kind"] == "source_challenge"]
    if len(fails) != 1:
        return False, "failures=%s" % (rec["failures"],)
    pc = fails[0].get("private_capture") or {}
    ok = (pc.get("state") == "stored"
          and SENTINEL not in json.dumps(rec))
    return ok, "pc=%s" % (pc,)


CASES = [
    ("cap-truncation", case_cap_truncation),
    ("under-cap-verbatim", case_under_cap_verbatim),
    ("inert-txt", case_inert_txt),
    ("retention-pruning", case_retention_pruning),
    ("metadata-only", case_metadata_only),
    ("disabled-default", case_disabled_default),
    ("repo-refusal", case_repo_refusal),
    ("probe-hook-stores", case_probe_hook_stores),
    ("probe-hook-disabled", case_probe_hook_disabled),
    ("enumerate-hook", case_enumerate_hook),
]


def run_all(verbose=True):
    """Run every case; return (n_pass, n_fail, [failed names])."""
    n_pass = n_fail = 0
    failed = []
    for name, fn in CASES:
        try:
            ok, detail = fn()
        except Exception as e:  # a crashing case is a failed case
            ok, detail = False, "raised %r" % (e,)
        if ok:
            n_pass += 1
        else:
            n_fail += 1
            failed.append(name)
        if verbose:
            print("  %s challenge-store: %s %s"
                  % ("PASS" if ok else "FAIL", name, detail))
    return n_pass, n_fail, failed


def main():
    n_pass, n_fail, failed = run_all()
    print("CHALLENGE-STORE pass=%d fail=%d" % (n_pass, n_fail))
    if failed:
        print("FAILURES: %s" % ", ".join(failed))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
