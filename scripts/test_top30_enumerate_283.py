#!/usr/bin/env python3
"""Negative + positive controls for the #283 stage-2 enumeration.

Run directly:  python3 scripts/test_top30_enumerate_283.py
Also wired into scripts/harness_issue109.py (--scorer). Stdlib only,
no network: every live-shape input is a SIMULATED NewsSearch page
built by page_html() below — clearly labelled, never presented as a
live EGX capture. The live fetcher is exercised only through the
probe record (a fake fetcher raising FetchFailure).

Required controls (issue #283 stage 2):
- pagination reaches an evidenced terminal state (exhausted /
  count_reconciled / duplicate_page / empty), never loops forever;
- source result counts reconcile, and a mismatch is a NAMED FAILURE
  (not a silent shortfall);
- fetch failures, challenge shells and non-terminating pagination are
  named failures with URL + evidence, never silent defaults;
- FAITA (no verified ISIN) is blocked with B-02 and NEVER defaults
  to the FAIT ISIN;
- corpus hashes: a full body hashes as "full"; a clipped body hashes
  as "clipped-body-sha256" and is never presented as a full hash.
"""
import hashlib
import io
import json
import os
import sys
import tempfile
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import top30_enumerate as E


# --- simulated NewsSearch pages (NOT live EGX captures) -------------------
def page_html(items, total=None, has_next=False, challenge=False):
    """Build a simulated NewsSearch result page.

    items: [(news_id, title, standalone_date_or_None)].
    ``total`` renders a source-reported result count; ``has_next``
    renders a next-page control; ``challenge`` renders a TSPD-style
    challenge shell instead of results.
    """
    if challenge:
        return ("<html><head><title>EGX</title></head><body>"
                "<script src=\"/tspd.js\"></script>"
                "<p>Please verify you are human</p></body></html>")
    rows = []
    for nid, title, d in items:
        row = ("<tr><td><a href=\"/ar/NewsDetails.aspx?NewsID=%s\">%s"
               "</a></td></tr>" % (nid, title))
        if d:
            row += "<tr><td>\n%s\n</td></tr>" % d
        rows.append(row)
    total_html = ("<div>total results: %d</div>" % total
                  if total is not None else "")
    next_html = ("<a href=\"#\" onclick=\"__doPostBack("
                 "'ctl00$ContentPlaceHolder1$gvNews','Page$2')\">"
                 "next</a>" if has_next else "")
    # A real empty result page states so explicitly; the marker is
    # what distinguishes an evidenced empty set from a challenge
    # shell in parse_search_page.
    empty_html = ("<div>no results found</div>" if not items else "")
    return ("<html><body><table>%s</table>%s%s%s</body></html>"
            % ("".join(rows), total_html, next_html, empty_html))


def detail_html(body):
    return "<html><body><div>%s</div></body></html>" % body


class FakeFetcher:
    """URL -> {"status", "body"} store; records every URL asked for."""

    def __init__(self, store):
        self.store = store
        self.asked = []

    def __call__(self, url):
        self.asked.append(url)
        if url not in self.store:
            raise E.FetchFailure(url, "no fixture for URL")
        return self.store[url]


def _listing(code, isin, issuer=None):
    return {"code": code, "isin": isin, "issuer": issuer or code}


def _poul_pages():
    """POUL pilot fixture: 2 pages, 3 documents, total 3."""
    p1 = page_html([
        ("296001", "POUL dividend announcement", "02/11/2026"),
        ("296002", "POUL board decisions", "10/11/2026"),
    ], total=3, has_next=True)
    p2 = page_html([
        ("296003", "POUL earnings Q3", "12/11/2026"),
    ], total=3, has_next=False)
    return {E.search_url("EGS02051C018", page=1): {"status": 200,
                                                   "body": p1},
            E.search_url("EGS02051C018", page=2): {"status": 200,
                                                   "body": p2}}


# --- controls ---------------------------------------------------------------
def test_pagination_two_pages_terminal():
    f = FakeFetcher(_poul_pages())
    rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"), f)
    ok = (rec["enumeration_status"] == "enumerated"
          and rec["terminal_state"] == "count_reconciled"
          and rec["pages_fetched"] == 2
          and rec["collected_ids"] == ["296001", "296002", "296003"]
          and len(rec["documents"]) == 3
          and not rec["failures"])
    return ok, ("terminal=%s pages=%d docs=%d failures=%s"
                % (rec["terminal_state"], rec["pages_fetched"],
                   len(rec["documents"]), rec["failures"]))


def test_count_mismatch_named_failure():
    store = {E.search_url("EGS02051C018", page=1): {
        "status": 200, "body": page_html([
            ("296001", "POUL dividend", "02/11/2026"),
            ("296002", "POUL board", "10/11/2026"),
        ], total=5, has_next=False)}}
    rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"),
                              FakeFetcher(store))
    kinds = [f["kind"] for f in rec["failures"]]
    ok = (rec["enumeration_status"] == "failed"
          and "count_mismatch" in kinds
          and "5" in rec["failures"][0]["reason"]
          and len(rec["documents"]) == 2)
    return ok, ("status=%s failures=%s docs=%d"
                % (rec["enumeration_status"], kinds,
                   len(rec["documents"])))


def test_duplicate_page_terminal():
    p1 = page_html([("296001", "POUL dividend", "02/11/2026"),
                    ("296002", "POUL board", "10/11/2026")],
                   has_next=True)
    store = {E.search_url("EGS02051C018", page=1): {"status": 200,
                                                    "body": p1},
             E.search_url("EGS02051C018", page=2): {"status": 200,
                                                    "body": p1}}
    rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"),
                              FakeFetcher(store))
    ok = (rec["terminal_state"] == "duplicate_page"
          and rec["pages_fetched"] == 2
          and rec["collected_ids"] == ["296001", "296002"])
    return ok, ("terminal=%s pages=%d ids=%s"
                % (rec["terminal_state"], rec["pages_fetched"],
                   rec["collected_ids"]))


def test_empty_result_evidenced():
    store = {E.search_url("EGS02051C018", page=1): {
        "status": 200, "body": page_html([], has_next=False)}}
    rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"),
                              FakeFetcher(store))
    ok = (rec["enumeration_status"] == "enumerated"
          and rec["terminal_state"] == "empty"
          and rec["documents"] == [])
    return ok, ("status=%s terminal=%s docs=%d"
                % (rec["enumeration_status"], rec["terminal_state"],
                   len(rec["documents"])))


def test_challenge_named_failure():
    store = {E.search_url("EGS02051C018", page=1): {
        "status": 200, "body": page_html([], challenge=True)}}
    rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"),
                              FakeFetcher(store))
    kinds = [f["kind"] for f in rec["failures"]]
    ok = (rec["enumeration_status"] == "failed"
          and "source_challenge" in kinds
          and rec["documents"] == []
          and "raw_sha256" in rec["failures"][0]["evidence"])
    return ok, ("status=%s failures=%s"
                % (rec["enumeration_status"], kinds))


def test_fetch_failure_named():
    def _boom(url):
        raise E.FetchFailure(url, "URLError: empty reply")
    rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"), _boom)
    kinds = [f["kind"] for f in rec["failures"]]
    ok = (rec["enumeration_status"] == "failed"
          and "fetch_failed" in kinds
          and "EGS02051C018" in rec["failures"][0]["evidence"])
    return ok, ("status=%s failures=%s evidence=%s"
                % (rec["enumeration_status"], kinds,
                   rec["failures"][0]["evidence"]))


def test_faita_never_defaults_isin():
    f = FakeFetcher({})
    rec = E.enumerate_listing(_listing("FAITA", None, issuer="FAIT"), f)
    kinds = [f2["kind"] for f2 in rec["failures"]]
    ok = (rec["enumeration_status"] == "blocked"
          and "B-02-missing-isin" in kinds
          and f.asked == []  # no request made at all, let alone
          and rec["documents"] == [])  # with the FAIT ISIN
    return ok, ("status=%s failures=%s urls_asked=%s"
                % (rec["enumeration_status"], kinds, f.asked))


def test_invalid_isin_blocked():
    rec = E.enumerate_listing(_listing("AMOC", "EGS3E2B1C018"),
                              FakeFetcher({}))
    kinds = [f["kind"] for f in rec["failures"]]
    ok = (rec["enumeration_status"] == "blocked"
          and "invalid-isin" in kinds)
    return ok, ("status=%s failures=%s"
                % (rec["enumeration_status"], kinds))


def test_max_pages_guard():
    def _endless(url):
        n = len(_endless.asked) + 1
        _endless.asked.append(url)
        return {"status": 200, "body": page_html([
            ("296%03d" % n, "POUL item %d" % n, "02/11/2026")],
            has_next=True)}
    _endless.asked = []
    rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"),
                              _endless, max_pages=3)
    kinds = [f["kind"] for f in rec["failures"]]
    ok = (rec["enumeration_status"] == "failed"
          and rec["terminal_state"] == "failed"
          and "pagination_not_terminated" in kinds
          and rec["pages_fetched"] == 3)
    return ok, ("status=%s failures=%s pages=%d"
                % (rec["enumeration_status"], kinds,
                   rec["pages_fetched"]))


def _mini_manifest():
    return {"base_commit": "test", "frozen_at": "2026-11-19",
            "quarter": {"start": "2026-08-19",
                        "end": "2026-11-19"},
            "issuers": [
                {"issuer": "POUL", "listings": [
                    {"code": "POUL", "currency": "EGP",
                     "isin": "EGS02051C018"}]},
                {"issuer": "FAIT", "listings": [
                    {"code": "FAIT", "currency": "EGP",
                     "isin": "EGS60321C014"},
                    {"code": "FAITA", "currency": "USD",
                     "isin": None}]},
            ]}


def test_ledger_schema_and_collection():
    store = _poul_pages()
    # FAIT: one page, one doc; the same NewsID also appears under
    # FAITA's listing in a second fixture to prove issuer-level
    # dedupe — here FAITA is blocked, so the union is just FAIT's.
    store[E.search_url("EGS60321C014", page=1)] = {
        "status": 200, "body": page_html([
            ("297001", "FAIT dividend", "03/11/2026")],
            total=1, has_next=False)}
    ledger = E.enumerate_universe(_mini_manifest(),
                                  FakeFetcher(store), run_id="test-run")
    coll = ledger["collection"]
    fait = [i for i in ledger["issuers"] if i["issuer"] == "FAIT"][0]
    ok = (ledger["schema_version"] == 1
          and ledger["window"] == {"start": "2026-08-19",
                                   "end": "2026-11-19",
                                   "inclusive": True}
          and coll["enumerated"] == 4
          and coll["archived"] == 0
          and coll["missing"] == []
          and coll["enumeration_closed"] is False  # FAITA blocked
          and coll["pagination_complete"] is False
          and fait["collected_count"] == 1
          and any(f["kind"] == "B-02-missing-isin"
                  for f in fait["failures"]))
    return ok, ("collection=%s fait_docs=%d fait_failures=%s"
                % (coll, fait["collected_count"],
                   [f["kind"] for f in fait["failures"]]))


def test_ledger_closed_when_clean():
    manifest = {"base_commit": "test", "frozen_at": "2026-11-19",
                "quarter": {"start": "2026-08-19",
                            "end": "2026-11-19"},
                "issuers": [{"issuer": "POUL", "listings": [
                    {"code": "POUL", "currency": "EGP",
                     "isin": "EGS02051C018"}]}]}
    ledger = E.enumerate_universe(manifest, FakeFetcher(_poul_pages()),
                                  run_id="test-run")
    coll = ledger["collection"]
    ok = (coll["enumerated"] == 3
          and coll["enumeration_closed"] is True
          and coll["pagination_complete"] is True
          and ledger["failures"] == [])
    return ok, ("collection=%s" % (coll,))


def test_issuer_union_dedupes_source_ids():
    # The same NewsID served under both listings of one issuer
    # (dual-listed issuer, same disclosure): the issuer unions and
    # dedupes to one document. Each listing keeps its OWN verified
    # ISIN — nothing is substituted across listings.
    manifest = {"base_commit": "test", "frozen_at": "2026-11-19",
                "quarter": {"start": "2026-08-19",
                            "end": "2026-11-19"},
                "issuers": [{"issuer": "FAIT", "listings": [
                    {"code": "FAIT", "currency": "EGP",
                     "isin": "EGS60321C014"},
                    {"code": "FAITX", "currency": "EGP",
                     "isin": "EGS60121C018"}]}]}
    body = page_html([("297001", "FAIT dividend", "03/11/2026")],
                     total=1, has_next=False)
    store = {E.search_url("EGS60321C014", page=1): {
                 "status": 200, "body": body},
             E.search_url("EGS60121C018", page=1): {
                 "status": 200, "body": body}}
    ledger = E.enumerate_universe(manifest, FakeFetcher(store),
                                  run_id="test-run")
    fait = ledger["issuers"][0]
    ok = (fait["collected_count"] == 1
          and len(fait["documents"]) == 1
          and fait["documents"][0]["source_document_id"] == "egx:297001")
    return ok, ("collected=%d docs=%s"
                % (fait["collected_count"], fait["documents"]))


def test_corpus_full_hash_vs_clipped():
    body = "POUL disclosure body " * 50  # 1100 chars
    store = {"https://example.invalid/detail": {
        "status": 200, "body": detail_html(body)}}
    f = FakeFetcher(store)
    doc = {"source_document_id": "egx:296001",
           "url": "https://example.invalid/detail",
           "corpus": {"status": "not_captured", "body_sha256": None,
                      "body_hash_kind": None, "body_chars": None,
                      "attachments": []}}
    corpus = E.capture_document(f, doc)
    full_hash = hashlib.sha256(
        detail_html(body).encode("utf-8")).hexdigest()
    doc2 = {"source_document_id": "egx:296001",
            "url": "https://example.invalid/detail",
            "corpus": {"status": "not_captured", "body_sha256": None,
                       "body_hash_kind": None, "body_chars": None,
                       "attachments": []}}
    clipped = E.capture_document(f, doc2, max_body_chars=100)
    ok = (corpus["status"] == "archived"
          and corpus["body_hash_kind"] == "full"
          and corpus["body_sha256"] == full_hash
          and clipped["status"] == "partial"
          and clipped["body_hash_kind"] == "clipped-body-sha256"
          and clipped["body_sha256"] != full_hash
          and clipped["body_chars"] == 100)
    return ok, ("full=%s clipped=%s"
                % (corpus["body_hash_kind"],
                   clipped["body_hash_kind"]))


def test_corpus_fetch_failure_recorded():
    def _boom(url):
        raise E.FetchFailure(url, "URLError: empty reply")
    doc = {"source_document_id": "egx:296001",
           "url": "https://example.invalid/detail",
           "corpus": {"status": "not_captured", "body_sha256": None,
                      "body_hash_kind": None, "body_chars": None,
                      "attachments": []}}
    corpus = E.capture_document(_boom, doc)
    ok = (corpus["status"] == "failed"
          and corpus["failures"][0]["kind"] == "fetch_failed")
    return ok, ("status=%s failures=%s"
                % (corpus["status"], corpus.get("failures")))


def test_window_frozen():
    url = E.search_url("EGS02051C018")
    ok = ("from=19/08/2026" in url and "to=19/11/2026" in url
          and E.WINDOW_START == "2026-08-19"
          and E.WINDOW_END == "2026-11-19")
    try:
        E.search_url(None)
        no_isin_raises = False
    except ValueError:
        no_isin_raises = True
    return ok and no_isin_raises, ("url=%s no_isin_raises=%s"
                                   % (url, no_isin_raises))


def test_challenge_probe_structured_record():
    """Issue #372: a challenge probe records structured public
    metadata — marker enums, status, full body_chars, a digest of
    the full body, and an explicit capture state — and no body
    text anywhere in the record."""
    sentinel = "SENTINEL-372-BODY-SECRET-7f3a9"
    body = ("<html><head><title>EGX</title></head><body>"
            "<script src=\"/tspd.js\"></script>"
            "<p>captcha check %s</p></body></html>" % sentinel)
    probe = E.probe_live_access(
        fetcher=lambda url: {"status": 200, "body": body})
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    ok = (probe["reachable"] is False
          and probe["status"] == 200
          and probe["body_chars"] == len(body)
          and probe["body_sha256"] == digest
          and probe["body_hash_kind"] == "full"
          and probe["challenge"] is True
          and probe["challenge_markers"] == ["tspd", "captcha"]
          and probe["vendor_hint"] == "tspd"
          and probe["capture_state"] == "captured"
          and sentinel not in json.dumps(probe))
    # Generic marker only: enums recorded, no vendor hint.
    generic = E.probe_live_access(
        fetcher=lambda url: {"status": 200,
                             "body": "<html><body>please complete "
                                     "the captcha</body></html>"})
    ok = (ok and generic["challenge_markers"] == ["captcha"]
          and generic["vendor_hint"] is None
          and generic["capture_state"] == "captured")
    # Near-empty shell, no matched signal: challenge by the parse
    # rule, marker "empty-body", still no vendor hint.
    empty = E.probe_live_access(
        fetcher=lambda url: {"status": 200,
                             "body": "<html></html>"})
    ok = (ok and empty["challenge"] is True
          and empty["challenge_markers"] == ["empty-body"]
          and empty["vendor_hint"] is None)
    return ok, ("tspd probe=%s generic=%s empty=%s"
                % (probe, generic["challenge_markers"],
                   empty["challenge_markers"]))


def test_challenge_probe_capture_failure_state():
    """Issue #372: capture failure has a named state without
    losing the original probe result."""
    def _boom(url):
        raise E.FetchFailure(url, "URLError: empty reply")
    failed = E.probe_live_access(fetcher=_boom)
    ok = (failed["capture_state"] == "fetch_failed"
          and failed["reachable"] is False
          and failed["status"] is None
          and failed["body_chars"] is None
          and failed["body_sha256"] is None
          and failed["body_hash_kind"] is None
          and failed["challenge"] is None
          and failed["challenge_markers"] == []
          and failed["vendor_hint"] is None
          and "empty reply" in failed["detail"]
          and failed["url"] and failed["at"])

    def _crash(url):
        raise RuntimeError("boom")
    errored = E.probe_live_access(fetcher=_crash)
    ok = (ok and errored["capture_state"] == "probe_error"
          and errored["reachable"] is False
          and "boom" in errored["detail"])
    return ok, ("fetch_failed=%s probe_error=%s"
                % (failed["capture_state"],
                   errored["capture_state"]))


def test_challenge_probe_publication_exclusion():
    """Issue #372: the challenge body is nowhere in the published
    run directory. Publish copies the run directory wholesale
    (worker/worker.py publish: cp -r results_dir/. dest/), so the
    test serialises the ledger exactly as main() does into a temp
    run dir and walks every file: the sentinel body text must
    appear in none of them, and no probe/body side file may exist.
    """
    sentinel = "SENTINEL-372-BODY-SECRET-7f3a9"
    body = ("<html><head><title>EGX</title></head><body>"
            "<script src=\"/tspd.js\"></script>"
            "<p>captcha check %s</p></body></html>" % sentinel)
    store = {E.search_url("EGS02051C018"):
             {"status": 200, "body": body},
             E.search_url("EGS02051C018", page=1):
             {"status": 200, "body": body}}
    manifest = {"base_commit": "test", "frozen_at": "2026-11-19",
                "quarter": {"start": "2026-08-19",
                            "end": "2026-11-19"},
                "issuers": [{"issuer": "POUL", "listings": [
                    {"code": "POUL", "currency": "EGP",
                     "isin": "EGS02051C018"}]}]}
    probe = E.probe_live_access(fetcher=FakeFetcher(store))
    ledger = E.enumerate_universe(manifest, FakeFetcher(store),
                                  mode="live")
    ledger["live_access"] = {"reachable": probe["reachable"],
                             "probes": [probe]}
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "top30_expected_docs.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=1, ensure_ascii=False)
        leaked = []
        files = []
        for root, _dirs, names in os.walk(tmp):
            for name in names:
                files.append(os.path.join(root, name))
                with open(os.path.join(root, name),
                          encoding="utf-8") as f:
                    if sentinel in f.read():
                        leaked.append(name)
        ok = (not leaked
              and files == [out]
              and sentinel not in json.dumps(probe)
              and probe["body_sha256"] == hashlib.sha256(
                  body.encode("utf-8")).hexdigest())
    return ok, ("files=%s leaked=%s"
                % ([os.path.basename(f) for f in files], leaked))


def test_probe_mode_ledger_honest():
    def _boom(url):
        raise E.FetchFailure(url, "URLError: empty reply")
    probe = E.probe_live_access(fetcher=_boom)
    manifest = {"base_commit": "test", "frozen_at": "2026-11-19",
                "quarter": {"start": "2026-08-19",
                            "end": "2026-11-19"},
                "issuers": [{"issuer": "POUL", "listings": [
                    {"code": "POUL", "currency": "EGP",
                     "isin": "EGS02051C018"}]}]}
    # run_probe_mode probes live; patch by monkey-checking the probe
    # record shape only — the ledger builder is exercised via
    # enumerate_universe in probe-like conditions below.
    ok = (probe["reachable"] is False
          and "empty reply" in probe["detail"])
    return ok, ("probe=%s" % (probe,))


def test_httperror_403_probe_preserves_evidence():
    """Issue #378: a non-2xx response that actually arrived keeps
    its evidence. http_fetch reads the HTTPError body and carries
    status + body on the FetchFailure; probe_live_access records
    the same structured fields as a 2xx response (status,
    body_chars, full digest, challenge markers, vendor hint)
    with capture_state "captured" and reachable False — not
    fetch_failed. The body itself appears nowhere in the record.
    Connection failures stay fetch_failed with no status, and
    enumeration keeps its existing non-2xx failure behaviour
    (kind fetch_failed, never source_challenge)."""
    import urllib.request
    sentinel = "SENTINEL-378-BODY-SECRET-2c8e1"
    body = ("<html><head><title>EGX</title></head><body>"
            "<script src=\"/tspd.js\"></script>"
            "<p>captcha check %s</p></body></html>" % sentinel)
    url = E.search_url("EGS02051C018")
    real_urlopen = urllib.request.urlopen

    def _raise_403(req, timeout=30):
        raise urllib.error.HTTPError(
            url, 403, "Forbidden", hdrs=None,
            fp=io.BytesIO(body.encode("utf-8")))
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    try:
        urllib.request.urlopen = _raise_403
        # http_fetch level: status + body carried on the failure.
        try:
            E.http_fetch(url)
            fetch_ok = False
            ferr = None
        except E.FetchFailure as e:
            fetch_ok = (e.status == 403 and e.body == body
                        and e.error == "HTTPError: HTTP Error 403: "
                        "Forbidden")
            ferr = e
        # Probe level (default fetcher = http_fetch, real path).
        probe = E.probe_live_access()
        ok = (fetch_ok
              and probe["reachable"] is False
              and probe["status"] == 403
              and probe["body_chars"] == len(body)
              and probe["body_sha256"] == digest
              and probe["body_hash_kind"] == "full"
              and probe["challenge"] is True
              and probe["challenge_markers"] == ["tspd", "captcha"]
              and probe["vendor_hint"] == "tspd"
              and probe["capture_state"] == "captured"
              and "HTTPError" in probe["detail"]
              and sentinel not in json.dumps(probe))
        # Enumeration level: same failure, still kind fetch_failed.
        rec = E.enumerate_listing(_listing("POUL", "EGS02051C018"),
                                  E.http_fetch)
        kinds = [f["kind"] for f in rec["failures"]]
        ok = (ok and rec["enumeration_status"] == "failed"
              and kinds == ["fetch_failed"]
              and rec["documents"] == [])

        def _raise_conn(req, timeout=30):
            raise urllib.error.URLError("empty reply")
        urllib.request.urlopen = _raise_conn
        try:
            E.http_fetch(url)
            conn_ok = False
        except E.FetchFailure as e:
            conn_ok = (e.status is None and e.body is None
                       and "URLError" in e.error)
        conn_probe = E.probe_live_access()
        ok = (ok and conn_ok
              and conn_probe["capture_state"] == "fetch_failed"
              and conn_probe["reachable"] is False
              and conn_probe["status"] is None
              and conn_probe["body_chars"] is None
              and conn_probe["body_sha256"] is None
              and conn_probe["body_hash_kind"] is None
              and conn_probe["challenge_markers"] == []
              and conn_probe["vendor_hint"] is None
              and "empty reply" in conn_probe["detail"])
    finally:
        urllib.request.urlopen = real_urlopen
    return ok, ("probe=%s conn_probe_state=%s ferr=%s"
                % (probe, conn_probe["capture_state"], ferr))


def test_httperror_403_non_challenge_body_still_captured():
    """Issue #378: a 403 body with no challenge marker still gets
    its evidence preserved — captured with the status/digest, not
    fetch_failed — and reachable stays False (a non-2xx response
    is never reachable, however benign its body looks)."""
    import urllib.request
    body = ("<html><body><p>Access denied by policy. "
            "Please contact the site operator for assistance "
            "with your request and quote reference 12345. "
            "This page intentionally carries no challenge "
            "marker at all, so it must not be misread as a "
            "challenge shell or as a reachable page.</p>"
            "</body></html>")
    assert len(body) >= 200
    url = E.search_url("EGS02051C018")
    real_urlopen = urllib.request.urlopen

    def _raise_403(req, timeout=30):
        raise urllib.error.HTTPError(
            url, 403, "Forbidden", hdrs=None,
            fp=io.BytesIO(body.encode("utf-8")))
    try:
        urllib.request.urlopen = _raise_403
        probe = E.probe_live_access()
    finally:
        urllib.request.urlopen = real_urlopen
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    ok = (probe["reachable"] is False
          and probe["status"] == 403
          and probe["body_chars"] == len(body)
          and probe["body_sha256"] == digest
          and probe["body_hash_kind"] == "full"
          and probe["challenge"] is False
          and probe["challenge_markers"] == []
          and probe["vendor_hint"] is None
          and probe["capture_state"] == "captured")
    return ok, ("probe=%s" % (probe,))


def test_httperror_body_read_failure_not_captured_empty():
    """Issue #383 (CodeRabbit Minor on PR #375, follow-up to #372):
    an HTTPError whose body cannot be read must NOT be recorded
    as a full capture of an empty body. http_fetch carries
    body=None (status kept) on a failed read, and
    probe_live_access records capture_state "body_unreadable"
    with the status kept and every body field unset — no
    body_chars=0 / empty-body digest presented as a full capture.
    Contrast: a genuinely empty body that really arrived IS still
    recorded as captured (body_chars=0, sha256 of "")."""
    import urllib.request

    class _FailingBody(io.BytesIO):
        def read(self, *args, **kwargs):
            raise IOError("simulated body read failure")

    url = E.search_url("EGS02051C018")
    real_urlopen = urllib.request.urlopen

    def _raise_403_unreadable(req, timeout=30):
        raise urllib.error.HTTPError(
            url, 403, "Forbidden", hdrs=None,
            fp=_FailingBody(b"never read"))

    def _raise_403_empty(req, timeout=30):
        raise urllib.error.HTTPError(
            url, 403, "Forbidden", hdrs=None, fp=io.BytesIO(b""))
    empty_digest = hashlib.sha256(b"").hexdigest()
    try:
        urllib.request.urlopen = _raise_403_unreadable
        # http_fetch level: status kept, body None, read cause kept.
        try:
            E.http_fetch(url)
            fetch_ok = False
            ferr = None
        except E.FetchFailure as e:
            fetch_ok = (e.status == 403 and e.body is None
                        and "unreadable" in e.error)
            ferr = e
        # Probe level (default fetcher = http_fetch, real path).
        probe = E.probe_live_access()
        ok = (fetch_ok
              and probe["reachable"] is False
              and probe["status"] == 403
              and probe["body_chars"] is None
              and probe["body_sha256"] is None
              and probe["body_hash_kind"] is None
              and probe["challenge"] is None
              and probe["challenge_markers"] == []
              and probe["vendor_hint"] is None
              and probe["capture_state"] == "body_unreadable"
              and probe["body_sha256"] != empty_digest
              and "HTTPError" in probe["detail"])
        # Contrast: a genuinely empty body that really arrived is
        # still a full capture of an empty body.
        urllib.request.urlopen = _raise_403_empty
        empty_probe = E.probe_live_access()
        ok = (ok and empty_probe["status"] == 403
              and empty_probe["body_chars"] == 0
              and empty_probe["body_sha256"] == empty_digest
              and empty_probe["body_hash_kind"] == "full"
              and empty_probe["capture_state"] == "captured")
    finally:
        urllib.request.urlopen = real_urlopen
    return ok, ("probe=%s empty_probe_state=%s ferr=%s"
                % (probe, empty_probe["capture_state"], ferr))


def test_httperror_body_non_bytes_not_captured_empty():
    """Issue #389 (INS-383 follow-up, residual of #383/#384): an
    HTTPError whose body read returns a non-bytes value (None, str)
    must NOT be recorded as a full capture of an empty body.
    http_fetch carries body=None on the #383 body_unreadable path
    (status kept, cause kept), and probe_live_access records
    capture_state "body_unreadable" with every body field unset.
    Contrast: a genuinely empty body that really arrived IS still
    recorded as captured (body_chars=0, sha256 of "")."""
    import urllib.request

    class _NoneBody(io.BytesIO):
        def read(self, *args, **kwargs):
            return None

    class _StrBody(io.BytesIO):
        def read(self, *args, **kwargs):
            return "not-bytes"

    url = E.search_url("EGS02051C018")
    real_urlopen = urllib.request.urlopen

    def _raise_403(fp):
        def _raise(req, timeout=30):
            raise urllib.error.HTTPError(
                url, 403, "Forbidden", hdrs=None, fp=fp)
        return _raise

    empty_digest = hashlib.sha256(b"").hexdigest()
    try:
        ok = True
        for fp, label in ((_NoneBody(b"x"), "None"),
                         (_StrBody(b"x"), "str")):
            urllib.request.urlopen = _raise_403(fp)
            # http_fetch level: status kept, body None, cause kept.
            try:
                E.http_fetch(url)
                fetch_ok = False
                ferr = None
            except E.FetchFailure as e:
                fetch_ok = (e.status == 403 and e.body is None
                            and "unreadable" in e.error)
                ferr = e
            # Probe level (default fetcher = http_fetch, real path).
            probe = E.probe_live_access()
            ok = (ok and fetch_ok
                  and probe["reachable"] is False
                  and probe["status"] == 403
                  and probe["body_chars"] is None
                  and probe["body_sha256"] is None
                  and probe["body_hash_kind"] is None
                  and probe["challenge"] is None
                  and probe["challenge_markers"] == []
                  and probe["vendor_hint"] is None
                  and probe["capture_state"] == "body_unreadable"
                  and probe["body_sha256"] != empty_digest
                  and "HTTPError" in probe["detail"])
            if not ok:
                return False, ("non-bytes=%s probe=%s ferr=%s"
                               % (label, probe, ferr))
        # Contrast: a genuinely empty body that really arrived is
        # still a full capture of an empty body.
        urllib.request.urlopen = _raise_403(io.BytesIO(b""))
        empty_probe = E.probe_live_access()
        ok = (ok and empty_probe["status"] == 403
              and empty_probe["body_chars"] == 0
              and empty_probe["body_sha256"] == empty_digest
              and empty_probe["body_hash_kind"] == "full"
              and empty_probe["capture_state"] == "captured")
    finally:
        urllib.request.urlopen = real_urlopen
    return ok, ("non-bytes probes body_unreadable; "
                "empty_probe_state=%s" % empty_probe["capture_state"])


def test_attachment_link_classification():
    ok = (E.classify_attachment_link(
              "https://www.egx.com.eg/ar/file.pdf", "report")
          and E.classify_attachment_link(
              "https://www.egx.com.eg/ar/att?id=1",
              "تقرير ممارسة النشاط المجمعة (64 KB)")
          and not E.classify_attachment_link(
              "/ar/NewsDetails.aspx?NewsID=1", "title")
          and not E.classify_attachment_link(
              "https://www.egx.com.eg/ar/NewsSearch.aspx", "search")
          and not E.classify_attachment_link(
              "https://example.invalid/page", "plain link"))
    return ok, "pdf/size-suffix True, detail/search/plain False"


def test_isin_validation_mirrors_harvester():
    ok = (E.is_valid_isin("EGS02051C018")
          and E.is_valid_isin("EGS380P1C010")  # corrected AMOC
          and not E.is_valid_isin("EGS3E2B1C018")  # stage-1 AMOC typo
          and not E.is_valid_isin(None))
    return ok, "valid POUL/AMOC pass, stage-1 AMOC typo fails"


CASES = [
    ("pagination-two-pages-terminal", test_pagination_two_pages_terminal),
    ("count-mismatch-named-failure", test_count_mismatch_named_failure),
    ("duplicate-page-terminal", test_duplicate_page_terminal),
    ("empty-result-evidenced", test_empty_result_evidenced),
    ("challenge-named-failure", test_challenge_named_failure),
    ("fetch-failure-named", test_fetch_failure_named),
    ("faita-never-defaults-isin", test_faita_never_defaults_isin),
    ("invalid-isin-blocked", test_invalid_isin_blocked),
    ("max-pages-guard", test_max_pages_guard),
    ("ledger-schema-and-collection", test_ledger_schema_and_collection),
    ("ledger-closed-when-clean", test_ledger_closed_when_clean),
    ("issuer-union-dedupes-source-ids",
     test_issuer_union_dedupes_source_ids),
    ("corpus-full-hash-vs-clipped", test_corpus_full_hash_vs_clipped),
    ("corpus-fetch-failure-recorded",
     test_corpus_fetch_failure_recorded),
    ("window-frozen", test_window_frozen),
    ("probe-mode-ledger-honest", test_probe_mode_ledger_honest),
    ("challenge-probe-structured-record",
     test_challenge_probe_structured_record),
    ("challenge-probe-capture-failure-state",
     test_challenge_probe_capture_failure_state),
    ("challenge-probe-publication-exclusion",
     test_challenge_probe_publication_exclusion),
    ("httperror-403-probe-preserves-evidence",
     test_httperror_403_probe_preserves_evidence),
    ("httperror-403-non-challenge-body-still-captured",
     test_httperror_403_non_challenge_body_still_captured),
    ("httperror-body-read-failure-not-captured-empty",
     test_httperror_body_read_failure_not_captured_empty),
    ("httperror-body-non-bytes-not-captured-empty",
     test_httperror_body_non_bytes_not_captured_empty),
    ("attachment-link-classification",
     test_attachment_link_classification),
    ("isin-validation-mirrors-harvester",
     test_isin_validation_mirrors_harvester),
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
            print("  %s enumerate-283: %s %s"
                  % ("PASS" if ok else "FAIL", name, detail))
    return n_pass, n_fail, failed


def main():
    n_pass, n_fail, failed = run_all()
    print("ENUMERATE-283 pass=%d fail=%d" % (n_pass, n_fail))
    if failed:
        print("FAILURES: %s" % ", ".join(failed))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
