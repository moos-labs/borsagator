#!/usr/bin/env python3
"""Private store for EGX challenge-page bodies (issue #589).

The closed #372 work put structured public metadata in
``probe_live_access`` (status, body_chars, full-body SHA-256,
marker enums, capture state) and kept the body itself out of the
public archive: the archive is anonymously readable and publish
copies run directories wholesale, so a challenge body may never
land there. This module is the separately approved private
capture (Muhammad, 2026-11-20): when a harvest/enumeration
attempt is served a bot-defence challenge shell, the body is
kept as local diagnostic evidence in a PRIVATE store, and only
metadata joins the public record.

Rules (issue #589 spec):
- The store lives OUTSIDE the public archive tree and outside
  the repo checkout; a configured path inside the checkout is
  refused (state "failed"), never silently written.
- Each body is stored as an inert UTF-8 ``.txt`` file: the body
  is decoded to text (undecodable bytes and NULs become U+FFFD)
  and written as plain text — never binary, never executable,
  directory mode 0700, file mode 0600.
- Max 64 KiB of body per capture; a longer body is truncated to
  the cap and a truncation marker line is appended, so a stored
  file is at most the cap plus the marker.
- Bounded retention: the most recent 200 captures are kept;
  older captures are pruned on each new capture.
- The public side stays metadata-only: the returned record
  carries URL, timestamp, status, the FULL body's SHA-256 and
  byte count, plus the stored bytes' own SHA-256, stored byte
  count, truncation flag and capture state. Callers copy only
  those fields into public records — never body content, never
  the stored filename.
- Configuration is the ``BORSAGATOR_CHALLENGE_STORE_DIR``
  environment variable (the repo's env-config pattern, cf.
  ``GATOR_ROOT`` in worker/egx_harvest.py). Unset means capture
  is DISABLED: state "disabled", nothing written anywhere.
- Capture never raises: any failure is a named state in the
  returned record ("failed" with a detail), never a lost probe
  or enumeration result.

Stdlib only.
"""
import hashlib
import os
import time

STORE_ENV = "BORSAGATOR_CHALLENGE_STORE_DIR"
MAX_BODY_BYTES = 64 * 1024
RETENTION = 200
TRUNCATION_MARKER = (
    "\n\n[TRUNCATED: body exceeded %d bytes; "
    "stored prefix only]\n" % MAX_BODY_BYTES)

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)


def store_dir_from_env(env=None):
    """The configured store directory, or None when capture is
    disabled (variable unset or blank)."""
    env = os.environ if env is None else env
    raw = env.get(STORE_ENV)
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip()


def _full_bytes(body):
    """The body's bytes as received, for the full-body digest:
    str bodies encode as UTF-8; bytes pass through unchanged;
    anything else is stringified first. Never raises."""
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8", errors="replace")
    return str(body).encode("utf-8", errors="replace")


def _stored_text(body):
    """The inert stored text: the body decoded as UTF-8 with
    undecodable bytes replaced, NUL characters replaced (a NUL
    is what makes tools treat a file as binary), truncated to
    MAX_BODY_BYTES of UTF-8 with the truncation marker appended
    when the encoded text exceeds the cap. Returns
    (text, truncated)."""
    if isinstance(body, bytes):
        text = body.decode("utf-8", errors="replace")
    elif isinstance(body, str):
        text = body
    else:
        text = str(body)
    text = text.replace("\x00", "�")
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_BODY_BYTES:
        return text, False
    clipped = encoded[:MAX_BODY_BYTES].decode("utf-8",
                                              errors="ignore")
    return clipped + TRUNCATION_MARKER, True


def _inside_repo(path):
    """True when the resolved path is the repo checkout or
    anywhere under it — a store there would ride the publish
    paths, so it is refused."""
    resolved = os.path.realpath(path)
    repo = os.path.realpath(_REPO)
    return resolved == repo or resolved.startswith(repo + os.sep)


def _prune(store_dir):
    """Keep the most recent RETENTION captures. Filenames sort
    by capture time (UTC stamp first), so name order is age
    order. Best effort: a prune failure never fails a capture."""
    try:
        names = sorted(n for n in os.listdir(store_dir)
                       if n.endswith(".txt"))
    except OSError:
        return
    for name in names[:max(0, len(names) - RETENTION)]:
        try:
            os.unlink(os.path.join(store_dir, name))
        except OSError:
            pass


def capture_challenge_body(url, status, body, store_dir=None,
                           at=None):
    """Store one challenge body privately and return its
    METADATA record (never any body content):

    {"state": "stored" | "disabled" | "failed",
     "url", "at", "status",
     "body_sha256": sha256 of the FULL body as received,
     "body_bytes": full body byte count,
     "stored_sha256": sha256 of the stored file bytes or None,
     "stored_bytes": stored file byte count or None,
     "truncated": bool,
     "stored_name": stored filename or None (LOCAL use only —
     callers must not copy it into public records),
     "detail": failure detail or None}

    ``store_dir`` defaults to the BORSAGATOR_CHALLENGE_STORE_DIR
    environment variable; None there means disabled. ``at`` is
    an ISO-8601 UTC stamp (defaults to now). Never raises.
    """
    at = at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    full = _full_bytes(body)
    rec = {"state": "failed", "url": url, "at": at,
           "status": status,
           "body_sha256": hashlib.sha256(full).hexdigest(),
           "body_bytes": len(full),
           "stored_sha256": None, "stored_bytes": None,
           "truncated": False, "stored_name": None,
           "detail": None}
    if store_dir is None:
        store_dir = store_dir_from_env()
    if store_dir is None:
        rec["state"] = "disabled"
        rec["detail"] = ("%s is not set; private capture "
                         "disabled" % STORE_ENV)
        return rec
    try:
        if _inside_repo(store_dir):
            rec["detail"] = ("store dir %s is inside the repo "
                             "checkout; refused" % store_dir)
            return rec
        text, truncated = _stored_text(body)
        data = text.encode("utf-8", errors="replace")
        stamp = time.strftime("%Y%m%dT%H%M%SZ",
                              time.gmtime())
        name = "%s-%s.txt" % (stamp, rec["body_sha256"][:12])
        os.makedirs(store_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(store_dir, 0o700)
        except OSError:
            pass
        path = os.path.join(store_dir, name)
        fd = os.open(path,
                     os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                     0o600)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        rec["state"] = "stored"
        rec["stored_sha256"] = hashlib.sha256(data).hexdigest()
        rec["stored_bytes"] = len(data)
        rec["truncated"] = truncated
        rec["stored_name"] = name
        _prune(store_dir)
    except Exception as e:  # noqa: BLE001 — capture must not raise
        rec["state"] = "failed"
        rec["detail"] = "%s: %s" % (type(e).__name__, e)
    return rec
