#!/usr/bin/env python3
"""Attachment capture for the EGX disclosure harvest (issue #279).

Capture-only: at harvest time, follow each disclosure's attachment
link where the source offers one and store the PDF under the archive
with a stable pointer from the event (file path + content hash).
Record capture failures explicitly — never silently omit.

What this module does NOT do (out of #279, separate follow-up if
wanted): extract fields from inside the PDFs (revenue, board details,
record date). The acceptance property "re-reading the stored PDF
reproduces the extracted event fields" is a verification property of
the capture: the stored bytes must be the true source document for
the fields the pilot already extracts from the harvested item text
(scripts/disclosure_events.py works off title/body/row_text), so the
module offers verify_attachment() (re-read + sha256 match) and
fields_present_in_pdf() (the extracted field strings are present in
the stored bytes). It never parses a PDF.

Layout (worker/egx_harvest.py writes results/disclosures.json; the
worker archives the whole results/ tree into worker-runs/ and copies
disclosures.json to the stable harvest/<CODE>.json pointer — see
worker/worker.py publish(), which also copies results/attachments/
next to that pointer):
    results/attachments/<NewsID>.pdf          (first attachment)
    results/attachments/<NewsID>_2.pdf        (second, and so on)
    item["attachments"] = [pointer, ...]      (one record per link,
                                               never an empty list)

Pointer record:
    {"status": "captured" | "no_attachment" | "fetch_failed"
               | "not_pdf" | "too_large" | "link_scan_failed",
     "path": "attachments/<NewsID>.pdf" | None,
     "sha256": "<hex>" | None,
     "size_bytes": <int> | None,
     "source_url": "<absolute url>" | None,
     "reason": "<human-readable>" | None}

Link finding is defensive: the EGX detail page was never fetched
live from this VM (egx.com.eg sits behind TSPD bot defense and the
fetch failed), so the rules are grounded only in what the harvested
bodies prove — attachment lines in the harvested text carry a size
suffix, e.g. " تقرير ممارسة النشاط المجمعة (64 KB)". A link counts
as an attachment when its href ends in .pdf, or when its anchor text
ends with such a size suffix and the href is not a detail/search
page. Anything else is not followed.

Stdlib only. No network in this module: fetching is injected as a
callable so the harvester can pass its Playwright session (same
TSPD-trusted browser context) and tests can pass a fake.
"""
import hashlib
import os
import re
from urllib.parse import urljoin, urlparse

ATTACHMENT_DIR = "attachments"
MAX_ATTACHMENTS_PER_ITEM = 5
MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MiB guard: a PDF bigger than
# this is not a disclosure attachment, it is a bad fetch.

# Anchor text of an EGX attachment line ends with a size in
# parentheses — "تقرير ممارسة النشاط المجمعة (64 KB)", "بيان من
# البنك باللغة الإنجليزية (440 KB)" — as harvested in real bodies
# (COMI 297291/297289/297292, harvest 2026-11-18).
_SIZE_SUFFIX = re.compile(r"\(\s*[\d,]+(?:\.\d+)?\s*[KM]B\s*\)\s*$",
                          re.IGNORECASE)
_PDF_PATH = re.compile(r"\.pdf(?:[?#]|$)", re.IGNORECASE)
# EGX navigation pages are never attachments, whatever their text.
_DETAIL_PAGE = re.compile(r"NewsDetails\.aspx|NewsSearch\.aspx",
                          re.IGNORECASE)


def _record(status, source_url=None, reason=None, path=None,
            sha256=None, size_bytes=None):
    return {"status": status, "path": path, "sha256": sha256,
            "size_bytes": size_bytes, "source_url": source_url,
            "reason": reason}


def _is_pdf_href(href):
    return bool(href) and bool(_PDF_PATH.search(
        urlparse(href).path or ""))


def _is_usable_href(href):
    """A followable http(s) URL — no javascript:, mailto:, fragments."""
    if not href:
        return False
    low = href.strip().lower()
    if low.startswith(("javascript:", "mailto:", "#")):
        return False
    return urlparse(href).scheme in ("http", "https", "") \
        and not _DETAIL_PAGE.search(href)


def find_attachment_links(anchors, base_url):
    """Detail-page anchors -> ordered, de-duplicated absolute PDF URLs.

    anchors: [{"href": ..., "text": ...}] as collected from the live
    detail page. base_url: the detail page URL (resolves relatives).
    Strong rule: href path ends in .pdf. Weaker rule: anchor text ends
    with a size suffix "(64 KB)" and the href is a followable,
    non-detail URL. Detail/search pages, javascript:/mailto: links and
    fragments are never followed.
    """
    seen, out = set(), []
    for a in anchors or []:
        href = (a or {}).get("href") or ""
        text = (a or {}).get("text") or ""
        if not _is_usable_href(href):
            continue
        if not (_is_pdf_href(href)
                or _SIZE_SUFFIX.search(text.strip())):
            continue
        abs_url = urljoin(base_url or "", href)
        if not urlparse(abs_url).scheme.startswith("http"):
            continue
        if abs_url in seen:
            continue
        seen.add(abs_url)
        out.append(abs_url)
    return out


def store_pdf(data, dest_dir, news_id, index=0):
    """Validate + store fetched bytes. Returns the pointer record.

    Not a fetcher: callers pass bytes they already downloaded.
    A record with status "captured" is the only outcome that writes
    a file; every other outcome leaves nothing on disk.
    """
    if not data or not data.startswith(b"%PDF-"):
        return _record("not_pdf", reason="fetched bytes are not a PDF "
                       "(no %PDF- header)")
    if len(data) > MAX_PDF_BYTES:
        return _record("too_large",
                       reason="PDF is %d bytes, over the %d-byte cap"
                       % (len(data), MAX_PDF_BYTES))
    filename = ("%s.pdf" % news_id) if index == 0 \
        else ("%s_%d.pdf" % (news_id, index + 1))
    os.makedirs(dest_dir, exist_ok=True)
    with open(os.path.join(dest_dir, filename), "wb") as f:
        f.write(data)
    return _record("captured", path="%s/%s" % (ATTACHMENT_DIR, filename),
                   sha256=hashlib.sha256(data).hexdigest(),
                   size_bytes=len(data))


def capture_one(fetch, url, dest_dir, news_id, index=0):
    """Fetch one attachment URL and store it. fetch(url) -> (status,
    data: bytes); it may raise on transport failure. Returns the
    pointer record; a fetch failure is a record, never an exception.
    """
    try:
        status, data = fetch(url)
    except Exception as exc:  # transport failure, timeout, TSPD wall
        return _record("fetch_failed", source_url=url,
                       reason="fetch raised: %s" % str(exc)[:200])
    if status != 200:
        return _record("fetch_failed", source_url=url,
                       reason="HTTP %s" % status)
    rec = store_pdf(data, dest_dir, news_id, index)
    rec["source_url"] = url
    return rec


def capture_item_attachments(news_id, anchors, base_url, fetch,
                             results_dir):
    """The per-item capture step egx_harvest.py calls for each
    disclosure. anchors: [{"href","text"}] from the detail page, or
    None when the link scan itself failed. Returns the item's
    "attachments" list — never empty: a disclosure with no attachment
    link gets one explicit no_attachment record, and a failed link
    scan gets one explicit link_scan_failed record.
    """
    if anchors is None:
        return [_record("link_scan_failed",
                        reason="attachment link scan failed on the "
                        "detail page")]
    urls = find_attachment_links(anchors, base_url)
    if not urls:
        return [_record("no_attachment",
                        reason="no attachment link on the detail page")]
    dest = os.path.join(results_dir, ATTACHMENT_DIR)
    return [capture_one(fetch, url, dest, news_id, i)
            for i, url in enumerate(urls[:MAX_ATTACHMENTS_PER_ITEM])]


def verify_attachment(record, stored_bytes):
    """Re-read check (the #279 acceptance property): the stored file's
    bytes must hash to the pointer's sha256 and still be a PDF.
    stored_bytes is None when the file is missing. Returns
    (ok: bool, reason: str)."""
    if not isinstance(record, dict) \
            or record.get("status") != "captured":
        return False, "record is not a captured attachment"
    if stored_bytes is None:
        return False, "stored file missing"
    if not stored_bytes.startswith(b"%PDF-"):
        return False, "stored bytes are not a PDF"
    if hashlib.sha256(stored_bytes).hexdigest() \
            != record.get("sha256"):
        return False, "sha256 mismatch: stored bytes are not the " \
                      "captured bytes"
    return True, "ok"


def fields_present_in_pdf(pdf_bytes, fields):
    """Which of the given extracted-field strings are NOT present in
    the stored PDF bytes. Returns the missing list (empty = the PDF
    reproduces every field). The check is byte-substring on the raw
    stored bytes: it is a fixture/verification aid, not a PDF parser
    — real PDFs may compress or re-encode text, so a miss here means
    "cannot confirm from raw bytes", never "the field is absent".
    """
    if pdf_bytes is None:
        return list(fields)
    return [f for f in fields if f.encode("utf-8") not in pdf_bytes]
