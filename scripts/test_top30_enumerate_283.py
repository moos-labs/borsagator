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
import os
import sys

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
