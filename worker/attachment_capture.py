#!/usr/bin/env python3
"""Disclosure attachment capture (issue #279) — capture-only.

At harvest time, follow each disclosure's attachment link where the
source offers one and store the PDF under the archive with a stable
pointer from the event (file path + content hash). Capture failures
are recorded explicitly — never silently omitted.

Statuses (``attachment.status`` on a harvested item):
- ``captured``      — at least one PDF stored under
  ``attachments/<NewsID>/<file>.pdf`` (path is relative to the
  directory holding ``disclosures.json``); each file carries its
  sha256, byte size and source URL.
- ``no_attachment`` — the source offered no attachment: no PDF link
  on the detail page and no attachment marker in the body.
- ``fetch_failed``  — an attachment was offered but could not be
  stored (no PDF link found although the body mentions one, a
  download error, a non-PDF response, or an over-size file). The
  ``reason`` names the failure; ``failures`` lists per-URL errors.
- ``not_recorded``  — the item predates capture (old harvests): the
  extractor synthesises this status so a missing pointer is an
  explicit state, never an absent key.

This module is stdlib-only and Playwright-free so it is unit-testable
without a browser: the harvester passes in a ``fetch(url)`` callable
that returns ``(bytes, content_type)`` (in production, the
Playwright request context of the trusted EGX session).

What this module does NOT do (out of #279 by the recorded scope
decision): extract fields from inside PDFs. The stored PDF is the
true source document for the fields the pilot already extracts from
harvested item text; ``scripts/disclosure_events.py verify``
re-reads the stored PDF and checks those fields reproduce — a
verification property of the capture, not new extraction.
"""
import hashlib
import os
import re
from urllib.parse import urljoin, urlparse

ATTACHMENT_DIR = "attachments"
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MiB per file
MAX_ATTACHMENTS_PER_ITEM = 3

_PDF_RE = re.compile(r"\.pdf($|[?#&])", re.IGNORECASE)
_ATTACH_WORDS = ("مرفق", "attachment", "attach")
_OFFER_WORDS = ("مرفق", "attachment")


def attachment_offered(body, title=""):
    """True when the harvested text says an attachment exists.

    EGX detail bodies end with e.g. ``مرفق الإعلان (214 KB)`` when a
    PDF is attached. A mention is an offer even when no link was
    found on the page — that case is ``fetch_failed``, not
    ``no_attachment``.
    """
    hay = ((body or "") + "\n" + (title or "")).lower()
    return any(w.lower() in hay for w in _OFFER_WORDS)


def _is_pdf_href(href):
    """True for a link that points at a PDF document.

    Accepts ``.pdf`` at the end of the path or before a query
    string, fragment or further parameter (``f=x.pdf&v=2`` counts:
    the download step still verifies the ``%PDF`` magic, so a
    permissive discovery rule cannot store a non-PDF). A bare
    ``?download=...`` link with no ``.pdf`` anywhere is not one:
    the harvester cannot know it is a PDF without fetching it, and
    fetching arbitrary links off a disclosure page is out of scope.
    """
    if not href:
        return False
    return bool(_PDF_RE.search(href))


def find_attachment_links(links, base_url):
    """PDF attachment URLs from a detail page's anchors.

    ``links`` is a list of ``{"href": ..., "text": ...}`` (as
    collected by the harvester's ``collect_attachment_links``).
    Returns deduplicated absolute URLs, attachment-word links
    first, capped at ``MAX_ATTACHMENTS_PER_ITEM``. Relative hrefs
    resolve against ``base_url`` (the detail-page URL).
    """
    seen = []
    text_by_url = {}
    for link in links or []:
        href = (link or {}).get("href") or ""
        if not _is_pdf_href(href):
            continue
        abs_url = urljoin(base_url or "", href)
        if abs_url not in text_by_url:
            text_by_url[abs_url] = (link or {}).get("text") or ""
            seen.append(abs_url)
    preferred = [u for u in seen
                 if any(w in text_by_url[u].lower()
                        for w in _ATTACH_WORDS)]
    ordered = preferred + [u for u in seen if u not in preferred]
    return ordered[:MAX_ATTACHMENTS_PER_ITEM]


def safe_filename(url, news_id, index=0):
    """Filesystem-safe PDF filename for a captured attachment."""
    base = os.path.basename(urlparse(url).path or "")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or ""
    if not base.lower().endswith(".pdf"):
        base = (base + ".pdf") if base else ""
    if not base:
        base = "%s.pdf" % news_id
    elif index:
        stem = base[:-4]
        base = "%s-%d.pdf" % (stem, index)
    if base == ".pdf":
        base = "%s.pdf" % news_id
    return base


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def capture_attachments(news_id, urls, offered, fetch, results_dir,
                        now_iso=None):
    """Download attachment PDFs into the archive; return the record.

    ``fetch(url)`` returns ``(bytes, content_type)`` or raises.
    Files land under ``<results_dir>/attachments/<news_id>/`` and
    the record's ``path`` values are relative to ``results_dir``
    (the directory holding ``disclosures.json``), so the same
    pointer resolves in the run dir, the on-box cache
    (``ROOT/harvest/attachments/``) and any copy of the harvest.
    A failure in any one file never raises: it is recorded.
    """
    import time
    record = {"status": None, "files": [], "failures": [],
              "reason": None,
              "captured_at": now_iso or time.strftime(
                  "%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    urls = list(urls or [])
    if not urls:
        if offered:
            record["status"] = "fetch_failed"
            record["reason"] = (
                "attachment mentioned in the disclosure body but no "
                "PDF link found on the detail page")
        else:
            record["status"] = "no_attachment"
            record["reason"] = (
                "no attachment offered: no PDF link on the detail "
                "page and no attachment marker in the body")
        return record
    target_dir = os.path.join(results_dir, ATTACHMENT_DIR,
                              str(news_id))
    for index, url in enumerate(urls):
        try:
            data, content_type = fetch(url)
        except Exception as e:  # noqa: BLE001 - recorded, not raised
            record["failures"].append(
                {"url": url, "error": "%s: %s" % (
                    type(e).__name__, str(e)[:200])})
            continue
        if not isinstance(data, (bytes, bytearray)):
            record["failures"].append(
                {"url": url, "error": "fetch returned non-bytes"})
            continue
        if len(data) > MAX_ATTACHMENT_BYTES:
            record["failures"].append(
                {"url": url, "error": "file too large: %d bytes > %d"
                 % (len(data), MAX_ATTACHMENT_BYTES)})
            continue
        if not bytes(data).startswith(b"%PDF"):
            record["failures"].append(
                {"url": url,
                 "error": "downloaded content is not a PDF "
                          "(missing %PDF magic)"})
            continue
        name = safe_filename(url, news_id, index)
        try:
            os.makedirs(target_dir, exist_ok=True)
            disk_path = os.path.join(target_dir, name)
            with open(disk_path, "wb") as f:
                f.write(data)
        except Exception as e:  # noqa: BLE001 - recorded, not raised
            record["failures"].append(
                {"url": url, "error": "%s: %s" % (
                    type(e).__name__, str(e)[:200])})
            continue
        record["files"].append({
            "url": url,
            "path": "%s/%s/%s" % (ATTACHMENT_DIR, news_id, name),
            "sha256": _sha256(bytes(data)),
            "bytes": len(data),
            "content_type": content_type or "",
        })
    if record["files"]:
        record["status"] = "captured"
        if record["failures"]:
            record["reason"] = (
                "%d of %d attachment(s) failed; see failures"
                % (len(record["failures"]), len(urls)))
    else:
        record["status"] = "fetch_failed"
        record["reason"] = "; ".join(
            "%s: %s" % (f.get("url", ""), f.get("error", ""))
            for f in record["failures"])[:500] or "download failed"
    return record


def legacy_attachment_record():
    """Explicit pointer state for items harvested before #279."""
    return {"status": "not_recorded", "files": [], "failures": [],
            "reason": "harvest predates attachment capture (#279)",
            "captured_at": None}
