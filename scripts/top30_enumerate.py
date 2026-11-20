#!/usr/bin/env python3
"""Fixed-window enumeration for the #283 top-30 evaluation (stage 2).

Enumerates the expected EGX disclosure documents for every listing in
the frozen manifest (``evaluation/top30_manifest.json``) over the
FIXED quarter 2026-08-19 -> 2026-11-19, ISIN-keyed, paginating every
NewsSearch page to an evidenced terminal state, and writes the
expected-document ledger (``evaluation/top30_expected_docs.json``).

This module does NOT rewrite the rolling harvester (``worker/``
is untouched): the harvester rolls from today, collects one DOM view
and stops at 25 items. Enumeration is a separate, offline, resumable
step with its own terminal-state evidence.

Gates (INS-283-ENUM-DESIGN, issue #283 comment 7019892536):
enumeration -> expected-document ledger; corpus -> immutable source
evidence. Gold, scorer verdicts and per-cell reports follow on the
ledger + corpus and are NOT produced here.

Live access: egx.com.eg sits behind F5 TSPD bot defence and this VM
cannot reach it (verified 2026-11-19 ~22:21-22:22 UTC: curl "Empty
reply from server", urllib RemoteDisconnected, browser fetch network
error — see docs/top30-enumeration.md). The live fetcher therefore
records the exact failure per request and the ledger records every
issuer as not_run with a named failure instead of inventing
documents. A full live run belongs on the worker, where the
TSPD-trusted browser profile lives: ``--transport profile`` fetches
through that persistent Chromium profile session (ProfileFetcher
below, issue #346 F2); the filter-semantics validation protocol
for that run is in docs/top30-enumeration.md. No profile-backed
live enumeration has been verified yet — the wiring is proven by
fixture/stub tests only, and the first live sweep is still the
proof that remains (see docs/top30-enumeration.md §7).

Stdlib only. No network in the pure functions: fetching is injected
as a callable so tests (and the fixture pilot) can pass a fake.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

WINDOW_START = "2026-08-19"
WINDOW_END = "2026-11-19"
BASE = "https://www.egx.com.eg"
ENUMERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = 1

# Pagination guard: a listing that cannot reach a terminal state in
# this many pages is a named failure, never a silent truncation.
MAX_PAGES = 200

TERMINAL_STATES = ("empty", "exhausted", "count_reconciled",
                   "duplicate_page", "failed")


def fmt_dmy(iso):
    """YYYY-MM-DD -> dd/mm/yyyy (the NewsSearch from/to format)."""
    y, m, d = iso.split("-")
    return "%s/%s/%s" % (d, m, y)


def search_url(isin, page=None):
    """NewsSearch URL for one ISIN over the frozen window.

    Same query shape as worker/egx_harvest.py:206-208 (from/to/isn,
    sec_id=20). ``page`` is appended as &page=N when given; the live
    EGX pagination control is a __doPostBack form, so a browser-based
    fetcher (worker profile) drives the form while this URL form is
    the transport the fixture/HTTP fetchers use. The terminal-state
    logic below does not depend on which transport produced a page.
    """
    if not isin:
        raise ValueError("search_url requires an ISIN (never default "
                         "to another listing's ISIN)")
    url = ("%s/ar/NewsSearch.aspx?com=&word=&from=%s&to=%s&isin=%s"
           "&sec_id=20" % (BASE, fmt_dmy(WINDOW_START),
                           fmt_dmy(WINDOW_END), isin))
    if page is not None:
        url += "&page=%d" % page
    return url


def iso_date(body, row_text=""):
    """Publish date of one EGX disclosure (mirrors
    worker/egx_harvest.py iso_date, issue #274): the dd/mm/yyyy that
    stands alone on its own line under the title. Never the first
    date in the body, never a date inside a period range. Returns
    "YYYY-MM-DD" or "".
    """
    for hay in (body or "", row_text or ""):
        for m in re.finditer(r"(?m)^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$",
                             hay):
            try:
                dt = date(int(m.group(3)), int(m.group(2)),
                          int(m.group(1)))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return ""


def is_valid_isin(isin):
    """ISO 6166 check-digit validation (mirrors
    worker/egx_harvest.py is_valid_isin)."""
    if not isinstance(isin, str):
        return False
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        return False
    digits = "".join(str(ord(ch) - 55) if ch.isalpha() else ch
                     for ch in isin)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


_CHALLENGE_MARKERS = (
    # (substring, marker enum) — the schema-ordered list of
    # bot-defence signals a page body can match. "tspd" is the only
    # allowlisted vendor SIGNATURE: matching it may add a vendor
    # hint, never a certainty. The other markers are generic — a
    # page can say "captcha" without naming a vendor — so they
    # never produce a vendor hint.
    ("tspd", "tspd"),
    ("bot detection", "bot-detection"),
    ("are you human", "human-check"),
    ("captcha", "captcha"),
)


def challenge_markers(html):
    """Matched challenge-marker enums for a page body, in schema
    order. Empty when no bot-defence marker matches — a page can
    still be a challenge shell via the near-empty-body rule in
    parse_search_page (marker "empty-body", recorded by the
    caller)."""
    raw = html if isinstance(html, str) else ""
    return [enum for pat, enum in _CHALLENGE_MARKERS
            if re.search(pat, raw, re.I)]
_NEWS_LINK = re.compile(
    r'<a[^>]+href="([^"]*NewsDetails\.aspx[^"]*)"[^>]*>'
    r'(.*?)</a>', re.I | re.S)
_TOTAL_PATTERNS = (
    re.compile(r"(\d+)\s*(?:result|نتيجة|نتائج)", re.I),
    re.compile(r"total[^0-9]{0,20}(\d+)", re.I),
    re.compile(r"عدد النتائج[^0-9]{0,20}(\d+)"),
)
_NEXT_HINT = re.compile(
    r"(__doPostBack\([^)]*Page\$\d+[^)]*\)|"
    r"page=\d+[^\"']*[^>]*>\s*(?:next|التالي|›|»)|"
    r"class=\"[^\"]*next[^\"]*\")", re.I)
_TAG = re.compile(r"<[^>]+>")
_SIZE_SUFFIX = re.compile(r"\(\s*\d+(?:\.\d+)?\s*(?:KB|MB|GB)\s*\)\s*$",
                          re.I)


def _text(html):
    return _TAG.sub("", html or "").strip()


_EMPTY_MARKER = re.compile(
    r"no results|no data|0 results|لا توجد نتائج|لا يوجد", re.I)


def parse_search_page(html, url):
    """Parse one NewsSearch result page.

    Returns a dict: items (list of {news_id, href, title, row_text,
    announced_date}), source_total (int or None — None means the
    source did not report a total on this page; never invented),
    has_next_hint (bool), is_challenge (bool), raw_sha256.

    Challenge rule: a page that carries result links is never a
    challenge shell. A link-less page is a challenge shell when it
    matches a bot-defence marker, or when it is a near-empty body
    with no explicit empty-result marker (TSPD serves a 200 with an
    EMPTY body while its challenge JS runs — worker/egx_harvest.py).
    A link-less page WITH an explicit empty marker is an evidenced
    empty result set, not a challenge.
    """
    raw = html if isinstance(html, str) else ""
    out = {"url": url,
           "raw_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
           "items": [], "source_total": None,
           "has_next_hint": False, "is_challenge": False}
    for m in _NEWS_LINK.finditer(raw):
        href = m.group(1)
        mid = re.search(r"NewsID=(\d+)", href)
        if not mid:
            continue
        title = _text(m.group(2))
        # Row text: the text around the link (same row), for the
        # standalone-date-line rule.
        start = max(0, m.start() - 600)
        row = _text(raw[start:m.end() + 200])
        out["items"].append({
            "news_id": mid.group(1),
            "href": href if href.startswith("http") else BASE + href
            if href.startswith("/") else BASE + "/" + href,
            "title": title[:200],
            "row_text": row[:300],
            "announced_date": iso_date("", row) or None,
        })
    if out["items"]:
        # Result links present: this is a real result page, never a
        # challenge shell, however short the markup is.
        pass
    elif challenge_markers(raw):
        out["is_challenge"] = True
        return out
    elif len(raw) < 200 and not _EMPTY_MARKER.search(raw):
        out["is_challenge"] = True
        return out
    for pat in _TOTAL_PATTERNS:
        m = pat.search(raw)
        if m:
            try:
                out["source_total"] = int(m.group(1))
            except ValueError:
                pass
            break
    out["has_next_hint"] = bool(_NEXT_HINT.search(raw))
    return out


def classify_attachment_link(href, text):
    """Mirror of the worker/attachment_capture.py rule (issue #279):
    a link counts as an attachment when its href ends in .pdf, or
    when its anchor text ends with a size suffix like "(64 KB)" and
    the href is not a detail/search page. Anything else is not
    followed."""
    href = href or ""
    text = (text or "").strip()
    if "NewsDetails.aspx" in href or "NewsSearch.aspx" in href:
        return False
    if href.lower().split("?")[0].endswith(".pdf"):
        return True
    return bool(_SIZE_SUFFIX.search(text))


class FetchFailure(Exception):
    """A fetch that produced no usable page. Carries the exact
    evidence (url, error, timestamp) so the ledger can name it.

    ``status`` / ``body`` are set only when a response actually
    arrived (issue #378): http_fetch catches HTTPError separately
    and carries the non-2xx status + body here, so the probe can
    preserve the evidence instead of discarding it. Connection
    failures (URLError, timeout, disconnect) leave both None —
    no response arrived, so there is no evidence to preserve.
    ``body`` is None (with ``status`` set) when a response
    arrived but its body could not be read (issue #383): that is
    NOT an empty body — a genuinely empty body that really
    arrived is carried as ``body=""``. The distinction matters:
    a failed read must never be recorded as a full capture of
    an empty body. The body is carried only in memory, never
    stored: the probe records structured fields from it, never
    the body itself."""

    def __init__(self, url, error, status=None, body=None):
        super().__init__("%s: %s" % (url, error))
        self.url = url
        self.error = str(error)
        self.at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.status = status
        self.body = body


def http_fetch(url, timeout=30):
    """Default live fetcher: plain HTTP with a browser UA. Raises
    FetchFailure with the exact error — never returns a synthetic
    empty page (an empty page would masquerade as an empty result
    set). A non-2xx response still raises (enumeration keeps its
    existing non-2xx failure behaviour), but the HTTPError body is
    read and carried on the FetchFailure (issue #378), so a probe
    can record the response's evidence instead of losing it."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            return {"status": r.status, "body": body,
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime())}
    except urllib.error.HTTPError as e:
        # A response arrived: read its body so the probe record
        # keeps the evidence (status, chars, digest, challenge
        # markers). Still raises — enumeration's non-2xx failure
        # behaviour is unchanged; only the probe preserves what
        # arrived. A body that cannot be read keeps the status
        # with body=None (issue #383) — never an empty body as if
        # one had arrived; the read error is kept in the message
        # so the cause is not lost.
        try:
            raw = e.read()
        except Exception as read_err:  # noqa: BLE001 — must not raise
            raise FetchFailure(
                url, "%s: %s (error body unreadable: %s: %s)"
                     % (type(e).__name__, e,
                        type(read_err).__name__, read_err),
                status=e.code, body=None)
        body = (raw.decode("utf-8", errors="replace")
                if isinstance(raw, (bytes, bytearray)) else "")
        raise FetchFailure(url, "%s: %s" % (type(e).__name__, e),
                           status=e.code, body=body)
    except Exception as e:  # URLError, RemoteDisconnected, timeout...
        raise FetchFailure(url, "%s: %s" % (type(e).__name__, e))


class ProfileFetcher:
    """Live fetcher through the persistent Chromium profile session
    (issue #346 F2): pages load in the TSPD-trusted browser the
    harvester uses, so EGX sees the profile's cookies/trust
    instead of a bare urllib request. Playwright is imported
    lazily on first fetch; any failure (Playwright missing,
    profile launch failed, navigation failed) raises FetchFailure
    with the exact error — never a synthetic empty page. One
    browser page is reused across URLs; call close() when done.
    Pagination still uses the URL form (&page=N) the HTTP fetcher
    uses — driving the __doPostBack form is a later step, not
    claimed here."""

    def __init__(self, profile_dir, timeout=60):
        self.profile_dir = str(profile_dir)
        self.timeout = timeout
        self._pw = None
        self._ctx = None
        self._page_obj = None
        self._launch_error = None

    def __call__(self, url):
        try:
            page = self._page(url)
            resp = page.goto(url, timeout=self.timeout * 1000,
                             wait_until="domcontentloaded")
            body = page.content()
            status = resp.status if resp is not None else 200
        except FetchFailure:
            raise
        except Exception as e:  # noqa: BLE001 — fetch must not raise
            raise FetchFailure(url, "%s: %s" % (type(e).__name__, e))
        return {"status": status, "body": body,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime())}

    def _page(self, url):
        if self._page_obj is not None:
            return self._page_obj
        if self._launch_error is not None:
            raise FetchFailure(url, self._launch_error)
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            headful = bool(os.environ.get("DISPLAY"))
            self._ctx = self._pw.chromium.launch_persistent_context(
                self.profile_dir, headless=not headful,
                viewport={"width": 1366, "height": 768},
                timezone_id="Africa/Cairo",
                args=["--disable-blink-features=AutomationControlled"],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36",
                locale="ar-EG")
            self._page_obj = self._ctx.new_page()
        except Exception as e:  # noqa: BLE001 — launch must not raise
            self._launch_error = "%s: %s" % (type(e).__name__, e)
            raise FetchFailure(url, self._launch_error)
        return self._page_obj

    def close(self):
        try:
            if self._ctx is not None:
                self._ctx.close()
        except Exception:  # noqa: BLE001 — close must not raise
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:  # noqa: BLE001 — close must not raise
            pass
        self._ctx = None
        self._pw = None
        self._page_obj = None


def enumerate_listing(listing, fetcher, max_pages=MAX_PAGES):
    """Enumerate one listing (one code/ISIN) to a terminal state.

    ``listing``: {"code", "isin", "issuer"}. ``fetcher``: callable
    url -> {"status", "body", "fetched_at"} (raises FetchFailure).
    Returns a per-listing enumeration record (see build_ledger).
    """
    code = listing["code"]
    isin = listing.get("isin")
    rec = {"code": code, "issuer": listing.get("issuer", code),
           "isin": isin, "enumeration_status": "enumerated",
           "terminal_state": None, "source_total": None,
           "pages_fetched": 0, "collected_ids": [],
           "documents": [], "failures": []}
    if not isin:
        # B-02: FAITA has no verified ISIN. Enumeration for this
        # listing is BLOCKED — never default to the FAIT ISIN.
        rec["enumeration_status"] = "blocked"
        rec["terminal_state"] = "failed"
        rec["failures"].append({
            "kind": "B-02-missing-isin",
            "reason": "no verified ISIN for listing %s; ISIN-keyed "
                      "enumeration cannot run (never default to "
                      "another listing's ISIN)" % code,
            "evidence": "evaluation/top30_manifest.json blockers B-02"})
        return rec
    if not is_valid_isin(isin):
        rec["enumeration_status"] = "blocked"
        rec["terminal_state"] = "failed"
        rec["failures"].append({
            "kind": "invalid-isin",
            "reason": "ISIN %s for %s fails ISO 6166 check-digit "
                      "validation" % (isin, code),
            "evidence": "is_valid_isin(%s)" % isin})
        return rec
    seen = {}
    page_no = 1
    while page_no <= max_pages:
        url = search_url(isin, page=page_no)
        try:
            resp = fetcher(url)
        except FetchFailure as e:
            rec["enumeration_status"] = "failed"
            rec["terminal_state"] = "failed"
            rec["failures"].append({
                "kind": "fetch_failed",
                "reason": "fetch failed: %s" % e.error,
                "evidence": "url=%s at=%s" % (e.url, e.at)})
            return rec
        parsed = parse_search_page(resp.get("body", ""), url)
        rec["pages_fetched"] += 1
        if parsed["is_challenge"]:
            rec["enumeration_status"] = "failed"
            rec["terminal_state"] = "failed"
            rec["failures"].append({
                "kind": "source_challenge",
                "reason": "page served a bot-defence/challenge shell "
                          "or near-empty body (not an empty result set)",
                "evidence": "url=%s raw_sha256=%s"
                            % (url, parsed["raw_sha256"])})
            return rec
        if parsed["source_total"] is not None:
            if rec["source_total"] is None:
                rec["source_total"] = parsed["source_total"]
            elif rec["source_total"] != parsed["source_total"]:
                rec["failures"].append({
                    "kind": "count_mismatch",
                    "reason": "source total changed across pages: "
                              "%s then %s" % (rec["source_total"],
                                              parsed["source_total"]),
                    "evidence": "url=%s" % url})
        new_ids = 0
        for item in parsed["items"]:
            nid = item["news_id"]
            if nid in seen:
                continue
            seen[nid] = item
            new_ids += 1
            rec["documents"].append({
                "source_document_id": "egx:%s" % nid,
                "url": item["href"],
                "title": item["title"],
                "announced_date": item["announced_date"],
                "announced_date_source":
                    "row" if item["announced_date"] else None,
                "listing": code,
                "isin": isin,
                "first_seen_page": page_no,
                "corpus": {"status": "not_captured",
                           "body_sha256": None,
                           "body_hash_kind": None,
                           "body_chars": None,
                           "attachments": []},
            })
        # Terminal-state evidence, in order:
        if page_no == 1 and not parsed["items"] \
                and not parsed["has_next_hint"]:
            rec["terminal_state"] = "empty"
            break
        if rec["source_total"] is not None \
                and len(seen) == rec["source_total"]:
            rec["terminal_state"] = "count_reconciled"
            break
        if new_ids == 0 and page_no > 1:
            # A page that adds nothing new: pagination is exhausted
            # (or looping); do not keep requesting.
            rec["terminal_state"] = "duplicate_page"
            break
        if not parsed["has_next_hint"] and not parsed["items"]:
            rec["terminal_state"] = "exhausted"
            break
        if not parsed["has_next_hint"]:
            # No next-page control and this page added items: the
            # source shows one page only; that IS the terminal state
            # (single-page result set).
            rec["terminal_state"] = "exhausted"
            break
        page_no += 1
    else:
        rec["enumeration_status"] = "failed"
        rec["terminal_state"] = "failed"
        rec["failures"].append({
            "kind": "pagination_not_terminated",
            "reason": "no terminal state within %d pages" % max_pages,
            "evidence": "collected %d unique ids" % len(seen)})
        return rec
    # Count reconciliation: when the source reports a total, the
    # collected unique ids must equal it, or the enumeration is a
    # named failure (not a silent shortfall).
    if rec["source_total"] is not None \
            and len(seen) != rec["source_total"]:
        rec["enumeration_status"] = "failed"
        rec["failures"].append({
            "kind": "count_mismatch",
            "reason": "collected %d unique ids but source reports "
                      "total %d" % (len(seen), rec["source_total"]),
            "evidence": "terminal_state=%s" % rec["terminal_state"]})
    rec["collected_ids"] = sorted(seen)
    return rec


def capture_document(fetcher, doc, max_body_chars=None):
    """Capture one enumerated document's corpus: full detail-page
    body + attachment pointers, with hashes.

    The full body is hashed as ``sha256`` (``body_hash_kind`` =
    "full"). A clipped body is NEVER presented as a full-document
    hash: when the fetched body had to be clipped (max_body_chars),
    the hash is labelled ``clipped-body-sha256`` and corpus status
    is "partial". Attachment failures are recorded on the document
    and never lose the body. Returns the updated corpus record.
    """
    corpus = doc["corpus"]
    try:
        resp = fetcher(doc["url"])
    except FetchFailure as e:
        corpus["status"] = "failed"
        corpus["failures"] = [{
            "kind": "fetch_failed",
            "reason": "detail fetch failed: %s" % e.error,
            "evidence": "url=%s at=%s" % (e.url, e.at)}]
        return corpus
    body = resp.get("body", "")
    full = body
    clipped = False
    if max_body_chars is not None and len(body) > max_body_chars:
        full = body[:max_body_chars]
        clipped = True
    corpus["body_chars"] = len(full)
    corpus["body_sha256"] = hashlib.sha256(
        full.encode("utf-8")).hexdigest()
    corpus["body_hash_kind"] = ("clipped-body-sha256" if clipped
                                else "full")
    corpus["status"] = "partial" if clipped else "archived"
    # Attachment pointers: classify links on the detail page; the
    # caller fetches each PDF with the same session. Here the
    # fetcher returns page HTML, so attachment discovery records
    # the links found (fetching them is the corpus runner's step).
    corpus["attachments"] = [
        {"status": "link_found", "path": None, "sha256": None,
         "size_bytes": None, "source_url": href,
         "reason": "attachment link discovered; PDF fetch is the "
                   "corpus runner's step"}
        for href, text in _iter_links(body)
        if classify_attachment_link(href, text)]
    return corpus


def _iter_links(html):
    for m in re.finditer(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>',
                         html or "", re.I | re.S):
        yield m.group(1), _text(m.group(2))


def load_manifest(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def enumerate_universe(manifest, fetcher, run_id=None, mode="live"):
    """Enumerate every listing in the frozen manifest. Returns the
    ledger dict (schema v1). Issuers with two listings (FAIT/FAITA)
    union source records: duplicate NewsIDs across the issuer's
    listings are deduplicated at the issuer level before the ledger
    is written (one cell per issuer, not per listing)."""
    run_id = run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "issue": 283,
        "manifest": {
            "path": "evaluation/top30_manifest.json",
            "base_commit": manifest.get("base_commit"),
            "frozen_at": manifest.get("frozen_at"),
            "quarter": manifest.get("quarter", {}).get("start")
                       + " -> "
                       + manifest.get("quarter", {}).get("end", ""),
        },
        "window": {"start": WINDOW_START, "end": WINDOW_END,
                   "inclusive": True},
        "enumerator": "scripts/top30_enumerate.py",
        "enumerator_version": ENUMERATOR_VERSION,
        "run_id": run_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime()),
        "mode": mode,
        "live_access": {"reachable": None, "probes": []},
        "collection": {"enumerated": 0, "archived": 0, "missing": [],
                       "enumeration_closed": False,
                       "pagination_complete": False},
        "issuers": [],
        "failures": [],
    }
    total_docs = 0
    all_closed = True
    all_paginated = True
    for issuer in manifest.get("issuers", []):
        name = issuer["issuer"]
        irec = {"issuer": name, "listings": [],
                "enumeration_status": "enumerated",
                "terminal_states": {}, "source_total": None,
                "collected_count": 0, "documents": [],
                "failures": []}
        seen_ids = set()
        for listing in issuer.get("listings", []):
            listing = dict(listing, issuer=name)
            lrec = enumerate_listing(listing, fetcher)
            irec["listings"].append(lrec)
            irec["terminal_states"][lrec["code"]] = \
                lrec["terminal_state"]
            if lrec["source_total"] is not None:
                irec["source_total"] = (irec["source_total"] or 0) \
                    + lrec["source_total"]
            for doc in lrec["documents"]:
                if doc["source_document_id"] in seen_ids:
                    continue  # FAIT/FAITA union: dedupe by source id
                seen_ids.add(doc["source_document_id"])
                irec["documents"].append(doc)
            irec["failures"].extend(
                {"listing": lrec["code"], **f} for f in lrec["failures"])
            if lrec["enumeration_status"] != "enumerated":
                irec["enumeration_status"] = lrec["enumeration_status"]
            if lrec["terminal_state"] not in (
                    "empty", "exhausted", "count_reconciled",
                    "duplicate_page"):
                # "failed" (or None) means this listing never reached
                # an evidenced terminal state: pagination incomplete.
                all_paginated = False
        irec["collected_count"] = len(irec["documents"])
        total_docs += irec["collected_count"]
        if irec["enumeration_status"] != "enumerated":
            all_closed = False
        ledger["issuers"].append(irec)
        ledger["failures"].extend(
            {"issuer": name, **f} for f in irec["failures"])
    ledger["collection"]["enumerated"] = total_docs
    ledger["collection"]["archived"] = sum(
        1 for i in ledger["issuers"] for d in i["documents"]
        if d["corpus"]["status"] == "archived")
    ledger["collection"]["enumeration_closed"] = all_closed \
        and not ledger["failures"]
    ledger["collection"]["pagination_complete"] = all_paginated
    return ledger


def _probe_record_fields(rec, url, status, body):
    """Fill the structured capture fields of a probe record from a
    body that was actually received — a 2xx body or an HTTPError
    body (issue #378). The same fields either way, so a 403
    challenge shell gets the same evidence as a 200 one. The body
    itself is never stored: only status, chars, digest, marker
    enums and vendor hint land in the record. Returns the parsed
    page, for the caller's reachable/detail decisions."""
    body = body if isinstance(body, str) else ""
    parsed = parse_search_page(body, url)
    markers = challenge_markers(body)
    if parsed["is_challenge"] and not markers:
        # Near-empty body with no explicit empty-result marker: a
        # challenge shell by the parse rule, with no matched signal
        # to name.
        markers = ["empty-body"]
    rec["status"] = status
    rec["body_chars"] = len(body)
    rec["body_sha256"] = parsed["raw_sha256"]
    rec["body_hash_kind"] = "full"
    rec["challenge"] = parsed["is_challenge"]
    rec["challenge_markers"] = markers
    # Allowlisted vendor signature only: "tspd" may hint at the
    # vendor; a generic captcha/human-check marker never does.
    rec["vendor_hint"] = "tspd" if "tspd" in markers else None
    return parsed


def probe_live_access(fetcher=None):
    """One pilot probe (POUL control, ISIN EGS02051C018) to establish
    whether this machine can reach EGX NewsSearch at all. Returns
    the probe record; never raises.

    Structured record (issue #372): HTTP status, full body_chars,
    a sha256 digest of the FULL body received (body_hash_kind
    "full" — a clipped hash is never presented as a full hash,
    mirroring the corpus rule), the matched challenge-marker
    enums, an allowlisted vendor hint (a hint, never a certainty
    from a generic marker), and an explicit capture state. The
    body itself is NEVER stored in the record: the archive is
    anonymously readable and publish copies the run directory
    wholesale, so no body text, URL, or script content may land
    here — only the enums, counts and digest above. Challenge
    captures stay outside documents[].corpus. A non-2xx response
    that actually arrived (HTTPError with a body, issue #378) is
    not a capture failure: its status, body_chars, digest, markers
    and vendor hint are recorded exactly as for a 2xx body, with
    capture_state "captured" and reachable False. If the response
    arrived but its body could not be read (issue #383), the
    status is kept but no body evidence is recorded at all —
    body_chars / body_sha256 / body_hash_kind stay None and
    capture_state is "body_unreadable": a failed read is never
    presented as a full capture of an empty body. Only a
    connection failure — no response arrived — is "fetch_failed"
    with no status. Capture failure has a named state
    ("fetch_failed" / "body_unreadable" / "probe_error") and keeps
    the original probe result (reachable False, detail with the
    error). The legacy detail string is kept for compatibility:
    run_probe_mode embeds it in failure reasons."""
    fetcher = fetcher or http_fetch
    url = search_url("EGS02051C018")
    rec = {"url": url,
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "reachable": False, "detail": None,
           "status": None, "body_chars": None,
           "body_sha256": None, "body_hash_kind": None,
           "challenge": None, "challenge_markers": [],
           "vendor_hint": None, "capture_state": "not_attempted"}
    try:
        resp = fetcher(url)
        body = resp.get("body", "")
        parsed = _probe_record_fields(rec, url, resp.get("status"),
                                      body)
        rec["capture_state"] = "captured"
        rec["reachable"] = not parsed["is_challenge"]
        rec["detail"] = ("status=%s body_chars=%d challenge=%s"
                         % (rec["status"], rec["body_chars"],
                            parsed["is_challenge"]))
    except FetchFailure as e:
        if getattr(e, "status", None) is not None:
            # A response actually arrived (non-2xx HTTPError): its
            # evidence is preserved exactly like a 2xx body
            # (issue #378) — capture_state "captured", reachable
            # stays False, and the legacy error detail is kept.
            # Only a response that arrived gets this treatment;
            # a connection failure (status None) stays fetch_failed
            # with no status below. But a response whose body
            # could not be read (body None, issue #383) is NOT a
            # capture: the status is kept, every body field stays
            # unset, and capture_state is "body_unreadable" —
            # a failed read is never recorded as a captured
            # empty body.
            if getattr(e, "body", None) is not None:
                _probe_record_fields(rec, url, e.status, e.body)
                rec["capture_state"] = "captured"
            else:
                rec["status"] = e.status
                rec["capture_state"] = "body_unreadable"
            rec["reachable"] = False
            rec["detail"] = "%s: %s" % (type(e).__name__, e.error)
        else:
            rec["capture_state"] = "fetch_failed"
            rec["detail"] = "%s: %s" % (type(e).__name__, e.error)
    except Exception as e:  # noqa: BLE001 — probe must not raise
        rec["capture_state"] = "probe_error"
        rec["detail"] = "%s: %s" % (type(e).__name__, e)
    return rec


def run_probe_mode(manifest):
    """Probe mode (default): one pilot probe, then a ledger that
    honestly records every issuer as not_run with the shared probe
    evidence. No doomed per-issuer requests, no invented documents.
    FAITA additionally carries its B-02 named failure.
    """
    probe = probe_live_access()
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "issue": 283,
        "manifest": {
            "path": "evaluation/top30_manifest.json",
            "base_commit": manifest.get("base_commit"),
            "frozen_at": manifest.get("frozen_at"),
            "quarter": manifest.get("quarter", {}).get("start")
                       + " -> "
                       + manifest.get("quarter", {}).get("end", ""),
        },
        "window": {"start": WINDOW_START, "end": WINDOW_END,
                   "inclusive": True},
        "enumerator": "scripts/top30_enumerate.py",
        "enumerator_version": ENUMERATOR_VERSION,
        "run_id": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime()),
        "mode": "probe",
        "live_access": {"reachable": probe["reachable"],
                        "probes": [probe]},
        "collection": {"enumerated": 0, "archived": 0, "missing": [],
                       "enumeration_closed": False,
                       "pagination_complete": False},
        "issuers": [],
        "failures": [],
    }
    for issuer in manifest.get("issuers", []):
        name = issuer["issuer"]
        if probe["reachable"]:
            reason = ("enumeration not attempted in probe mode; live "
                      "EGX is reachable from this machine — run "
                      "--mode live (probe: %s)" % probe["detail"])
        else:
            reason = ("live EGX NewsSearch unreachable from this "
                      "machine; enumeration not attempted (probe: "
                      "%s)" % probe["detail"])
        failures = [{
            "kind": "egx_unreachable_from_vm"
                    if not probe["reachable"] else "not_run_probe_mode",
            "reason": reason,
            "evidence": "url=%s at=%s"
                        % (probe["url"], probe["at"])}]
        listings = []
        for listing in issuer.get("listings", []):
            lrec = {"code": listing["code"],
                    "issuer": name,
                    "isin": listing.get("isin"),
                    "enumeration_status": "not_run",
                    "terminal_state": None,
                    "source_total": None,
                    "pages_fetched": 0,
                    "collected_ids": [],
                    "documents": [],
                    "failures": []}
            if not listing.get("isin"):
                # B-02: FAITA has no verified ISIN — recorded here
                # as well as in the manifest, never defaulted.
                lrec["failures"].append({
                    "kind": "B-02-missing-isin",
                    "reason": "no verified ISIN for listing %s; "
                              "ISIN-keyed enumeration cannot run "
                              "(never default to another listing's "
                              "ISIN)" % listing["code"],
                    "evidence": "evaluation/top30_manifest.json "
                                "blockers B-02"})
                failures.append({"listing": listing["code"],
                                 **lrec["failures"][-1]})
            listings.append(lrec)
        ledger["issuers"].append({
            "issuer": name, "listings": listings,
            "enumeration_status": "not_run",
            "terminal_states": {l["code"]: None for l in listings},
            "source_total": None, "collected_count": 0,
            "documents": [], "failures": failures})
        ledger["failures"].extend(
            {"issuer": name, **f} for f in failures)
    return ledger


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=os.path.join(
        REPO, "evaluation", "top30_manifest.json"))
    ap.add_argument("--out", default=os.path.join(
        REPO, "evaluation", "top30_expected_docs.json"))
    ap.add_argument("--mode", choices=("probe", "live", "fixtures"),
                    default="probe")
    ap.add_argument("--fixtures", default=None,
                    help="fixture dir (mode=fixtures): JSON files "
                         "mapping URL -> {status, body}")
    ap.add_argument("--transport", choices=("http", "profile"),
                    default="http",
                    help="live-mode fetch transport: plain HTTP "
                         "(default) or the persistent Chromium "
                         "profile session (issue #346 F2)")
    ap.add_argument("--profile", default=None,
                    help="profile dir for --transport profile "
                         "(the worker's egx-profile)")
    args = ap.parse_args(argv)
    manifest = load_manifest(args.manifest)
    if args.mode == "probe":
        ledger = run_probe_mode(manifest)
    elif args.mode == "fixtures":
        store = {}
        for fn in sorted(os.listdir(args.fixtures)):
            if fn.endswith(".json"):
                with open(os.path.join(args.fixtures, fn),
                          encoding="utf-8") as f:
                    store.update(json.load(f))

        def _fetch(url, _store=store):
            if url not in _store:
                raise FetchFailure(url, "no fixture for URL")
            return _store[url]

        ledger = enumerate_universe(manifest, _fetch,
                                    mode="fixtures")
        ledger["live_access"] = {
            "reachable": None,
            "probes": [{"url": None, "at": ledger["generated_at"],
                        "reachable": None,
                        "detail": "fixture mode: no live access "
                                  "attempted; pages are SIMULATED, "
                                  "not live EGX captures",
                        "status": None, "body_chars": None,
                        "body_sha256": None, "body_hash_kind": None,
                        "challenge": None, "challenge_markers": [],
                        "vendor_hint": None,
                        "capture_state": "not_attempted"}]}
    else:  # live: full enumeration on a machine that can reach EGX
        # Issue #346 F2: --transport profile fetches through the
        # persistent Chromium profile session (the probe rides the
        # same session, so it tests the transport the enumeration
        # will use). Plain HTTP stays the default for probe mode
        # and for machines without the profile.
        if args.transport == "profile":
            if not args.profile:
                ap.error("--transport profile needs --profile DIR")
            fetcher = ProfileFetcher(args.profile)
            try:
                probe = probe_live_access(fetcher)
                ledger = enumerate_universe(manifest, fetcher,
                                            mode="live")
            finally:
                fetcher.close()
        else:
            probe = probe_live_access()
            ledger = enumerate_universe(manifest, http_fetch,
                                        mode="live")
        ledger["live_access"] = {"reachable": probe["reachable"],
                                 "probes": [probe]}
    ledger["transport"] = {"probe": "http",
                           "fixtures": "fixtures",
                           "live": args.transport}[args.mode]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1, ensure_ascii=False)
    n_docs = ledger["collection"]["enumerated"]
    n_fail = len(ledger["failures"])
    print("top30_enumerate: mode=%s issuers=%d documents=%d "
          "failures=%d enumeration_closed=%s" % (
              args.mode, len(ledger["issuers"]), n_docs, n_fail,
              ledger["collection"]["enumeration_closed"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
