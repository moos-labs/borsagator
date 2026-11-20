#!/usr/bin/env python3
"""Paired A/B single-URL EGX diagnostic harness (issue #283).

Why this exists: the live top-30 enumeration failed twice with
``Page.goto: net::ERR_CONNECTION_RESET`` on every listing, while a
diagnostic harvest (``w5-harvest-poul-diag-001``, archive ``3bb74d0f``)
did NOT reset — the EGX homepage loaded (200) but NewsSearch landed
on ``EGX_Error.aspx`` and ``/ar/`` warmup returned 403. The two tools
launch Chromium differently, and time and configuration are confounded
across all runs so far:

- enumerator (``scripts/top30_enumerate.py`` L310-311): persistent
  profile, ``headless=True``, NO overrides.
- harvester (``worker/egx_harvest.py`` L227-237): SAME persistent
  profile, headful under Xvfb (``headless=not bool(DISPLAY)``),
  viewport 1366x768, ``timezone_id="Africa/Cairo"``,
  ``--disable-blink-features=AutomationControlled``, Chrome/124
  Windows UA, ``locale="ar-EG"``.

This harness runs BOTH launch configurations against ONE fixed URL,
sequentially, with a clean context close between legs (default
A-B-A: the repeated A leg guards against a short transient). Only the
launch configuration differs between legs; URL, profile, navigation
timeout and settle wait are identical.

What it discriminates (read the verdict, not the exit code):
- A responds + B resets  -> configuration-dependent handling.
- both reset             -> shared current access problem.
- both respond            -> the reset was not reproduced at that
                             moment (transient, or already gone).
- anything else           -> inconclusive; read the per-leg records.

Exit code: 0 when the record was written — even when both legs
reset, because the record IS the deliverable (an honest failure
record is a successful probe run, like run_top30_enumerate's
honest-failure ledger). Non-zero only when no record could be
written (bad arguments, missing profile, no playwright).

Run on the worker via the ``diag-egx-ab`` job (worker/worker.py
run_diag_egx_ab); the URL is fixed — the job takes no arguments.
``--dry-run`` serves SIMULATED pages from a local stub server and
runs both legs against them: it exercises the leg runner without
EGX contact. The stub pages are clearly labelled fixtures, never
presented as live captures.

Usage:
  python3 scripts/diag_egx_ab.py --profile /opt/gator/egx-profile \
      --out-dir diag-egx-ab
  python3 scripts/diag_egx_ab.py --dry-run --out-dir /tmp/diag-dry
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timezone

# The one fixed URL both legs fetch, byte-identical. POUL NewsSearch
# window 19/08/2026-19/11/2026 (ISIN EGS02051C018, sec_id 20) — the
# same query the live enumeration uses for POUL.
DIAG_URL = ("https://www.egx.com.eg/ar/NewsSearch.aspx?com=&word="
            "&from=19/08/2026&to=19/11/2026&isin=EGS02051C018"
            "&sec_id=20")
NAV_TIMEOUT_MS = 90000
SETTLE_MS = 5000

# --- Launch configurations: copied VERBATIM from the two tools ------
# Leg A — harvester launch (worker/egx_harvest.py L227-237). The
# headless flag follows the harvester's own rule verbatim:
# headful iff DISPLAY is set (the worker wraps the run in xvfb-run,
# so leg A is headful there).
LEG_A_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36")
LEG_A_VIEWPORT = {"width": 1366, "height": 768}
LEG_A_TIMEZONE = "Africa/Cairo"
LEG_A_ARGS = ["--disable-blink-features=AutomationControlled"]
LEG_A_LOCALE = "ar-EG"
# Leg B — enumerator launch (scripts/top30_enumerate.py L310-311):
# launch_persistent_context(profile_dir, headless=True), no overrides.
# There is deliberately nothing else here.

_TSPD_RE = re.compile(r"tspd|bot detection|are you human|captcha",
                      re.IGNORECASE)
_RESET_RES = (re.compile(r"ERR_CONNECTION_RESET"),
              re.compile(r"Connection reset", re.IGNORECASE))


# --- classification (pure; unit-tested without network) --------------
def classify_page(status, final_url, html, text):
    """Classify one fetched page.

    Order matters: the EGX error page is checked FIRST — the
    observed one is only 511 chars, so a size-based empty check
    must never swallow it, and it carries no result links, so a
    results check must never claim it.
    Returns one of: egx-error | forbidden | challenge | results |
    no-response | empty | unknown.
    """
    url = final_url or ""
    body = html or ""
    if "EGX_Error.aspx" in url or "aspxerrorpath=" in url \
            or "EGX_Error.aspx" in body or "aspxerrorpath=" in body:
        return "egx-error"
    if status == 403:
        return "forbidden"
    if _TSPD_RE.search(body):
        return "challenge"
    if "NewsDetails.aspx" in body:
        return "results"
    if status is None:
        return "no-response"
    if len((text or "").strip()) < 50 or len(body) < 200:
        return "empty"
    return "unknown"


def classify_nav_error(exc_text):
    """Classify a page.goto exception: reset | timeout | other."""
    s = exc_text or ""
    if any(r.search(s) for r in _RESET_RES):
        return "reset"
    if "timeout" in s.lower() or "Timeout" in s:
        return "timeout"
    return "navigation-error"


def derive_verdict(legs):
    """Interpret the legs. Uses the FIRST A leg and the FIRST B leg;
    when the repeated A legs disagree, the verdict is inconclusive —
    a transient moved under the probe, so no config claim is safe.
    Returns (verdict, note)."""
    by_leg = {}
    for leg in legs or []:
        by_leg.setdefault(leg.get("leg"), []).append(
            leg.get("classification"))
    a = by_leg.get("A", [])
    b = by_leg.get("B", [])
    if not a or not b:
        return "inconclusive", "missing leg: ran %s" % sorted(by_leg)
    if len(set(a)) > 1:
        return ("inconclusive",
                "repeated A legs disagree: %s (transient moved)" % a)
    if a[0] == "results" and b[0] == "reset":
        return ("config-dependent",
                "A (harvester launch) responds, B (enumerator launch) "
                "resets on the same URL")
    if a[0] == "reset" and b[0] == "reset":
        return ("shared-access-problem",
                "both launch configs reset on the same URL")
    if a[0] == "results" and b[0] == "results":
        return ("not-reproduced",
                "both launch configs respond; the reset did not "
                "reproduce at this moment")
    return ("inconclusive",
            "A=%s B=%s: neither the config-dependent nor the "
            "shared-problem pattern" % (a[0], b[0]))


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def egress_ip(timeout=10):
    """Best-effort egress identity; None when unobtainable. Never
    raises — the probe must not fail because an IP lookup failed."""
    try:
        req = urllib.request.Request("https://api.ipify.org",
                                     headers={"User-Agent": "diag-egx-ab"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ip = r.read(64).decode("utf-8", "replace").strip()
            return ip or None
    except Exception:
        return None


def clear_stale_locks(profile_dir):
    """Shared hygiene (NOT part of either launch config): the
    harvester clears stale Chromium singleton locks before launching
    when no process is using the profile (worker/egx_harvest.py
    L216-226). Without it a stale lock from a killed run would
    masquerade as a config effect in whichever leg ran first."""
    try:
        alive = subprocess.run(["pgrep", "-f", profile_dir],
                               capture_output=True).returncode == 0
        if not alive:
            for lock in ("SingletonLock", "SingletonCookie",
                         "SingletonSocket"):
                p = os.path.join(profile_dir, lock)
                if os.path.lexists(p):
                    os.unlink(p)
    except Exception:
        pass


def launch_context(pw, leg, profile_dir):
    """Launch one leg's persistent context. The two branches below
    are verbatim copies of the two tools' launch calls — do not
    'improve' them; the whole point is that only the config differs.
    """
    if leg == "A":
        # Harvester (worker/egx_harvest.py L227-237).
        return pw.chromium.launch_persistent_context(
            profile_dir, headless=not bool(os.environ.get("DISPLAY")),
            viewport=dict(LEG_A_VIEWPORT),
            timezone_id=LEG_A_TIMEZONE,
            args=list(LEG_A_ARGS),
            user_agent=LEG_A_USER_AGENT,
            locale=LEG_A_LOCALE)
    # Leg B — enumerator (scripts/top30_enumerate.py L310-311).
    return pw.chromium.launch_persistent_context(
        profile_dir, headless=True)


def run_leg(pw, leg, profile_dir, url, nav_timeout_ms=NAV_TIMEOUT_MS,
            settle_ms=SETTLE_MS):
    """Run one leg: launch, navigate, settle, classify, clean close.
    Never raises: a failed leg is a recorded leg."""
    rec = {"leg": leg, "config": "harvester" if leg == "A"
           else "enumerator", "url": url,
           "started": utcnow(), "nav_error": None,
           "nav_error_kind": None, "status": None,
           "final_url": None, "body_chars": 0,
           "body_sample": "", "classification": None,
           "egress_ip": None}
    ctx = None
    try:
        clear_stale_locks(profile_dir)
        ctx = launch_context(pw, leg, profile_dir)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            resp = page.goto(url, wait_until="domcontentloaded",
                             timeout=nav_timeout_ms)
            rec["status"] = resp.status if resp is not None else None
        except Exception as e:  # noqa: BLE001 — the error IS the data
            rec["nav_error"] = "%s: %s" % (type(e).__name__, e)
            rec["nav_error_kind"] = classify_nav_error(str(e))
            rec["classification"] = rec["nav_error_kind"]
            rec["finished"] = utcnow()
            rec["egress_ip"] = egress_ip()
            return rec
        page.wait_for_timeout(settle_ms)
        rec["final_url"] = page.url
        try:
            html = page.content()
        except Exception:
            html = ""
        try:
            text = page.evaluate(
                "() => document.body ? document.body.innerText : ''")
        except Exception:
            text = ""
        rec["body_chars"] = len(text or "")
        rec["body_sample"] = (text or "")[:500]
        rec["classification"] = classify_page(rec["status"],
                                              rec["final_url"], html,
                                              text)
    except Exception as e:  # noqa: BLE001 — launch failure is a leg
        rec["nav_error"] = "%s: %s" % (type(e).__name__, e)
        rec["nav_error_kind"] = classify_nav_error(str(e))
        rec["classification"] = rec["nav_error_kind"]
    finally:
        try:
            if ctx is not None:
                ctx.close()
        except Exception:
            pass
    rec["finished"] = utcnow()
    rec["egress_ip"] = egress_ip()
    return rec


# --- dry-run stub server (SIMULATED pages, clearly labelled) --------
def fixture_results_page():
    """SIMULATED NewsSearch results page (not a live EGX capture)."""
    return ("<html><head><title>EGX News Search</title></head><body>"
            "<form id='NewsSearch'><select id='com'>"
            "<option>POUL</option></select></form>"
            "<table><tr><td><a href='/ar/NewsDetails.aspx?NewsID=1'>"
            "Board meeting results</a></td></tr>"
            "<tr><td><a href='/ar/NewsDetails.aspx?NewsID=2'>"
            "Dividend announcement</a></td></tr></table>"
            "<p>19/11/2026</p></body></html>")


def fixture_error_page():
    """SIMULATED EGX_Error page, exactly 511 chars like the observed
    harvest diagnostic body (w5-harvest-poul-diag-001)."""
    core = ("<html><head><title>EGX Error</title></head><body>"
            "<h1>Error</h1><p>An error occurred while processing "
            "your request: aspxerrorpath=/ar/NewsSearch.aspx</p>")
    pad = " " * (511 - len(core) - len("</body></html>"))
    return core + pad + "</body></html>"


def fixture_forbidden_page():
    return ("<html><head><title>403 Forbidden</title></head><body>"
            "<h1>403 Forbidden</h1><p>Access denied.</p></body></html>")


def fixture_challenge_page():
    return ("<html><head><title>EGX</title></head><body>"
            "<script src='/tspd.js'></script>"
            "<p>Please verify you are human</p></body></html>")


def fixture_empty_page():
    return "<html><head><title></title></head><body></body></html>"


def start_stub_server():
    """Serve the fixtures on 127.0.0.1; returns (server, base_url).
    NewsSearch path -> results; EGX_Error.aspx -> the 511-char
    error page; anything else -> 404."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path.endswith("/NewsSearch.aspx"):
                body, code = fixture_results_page(), 200
            elif "EGX_Error.aspx" in path:
                body, code = fixture_error_page(), 200
            elif path.endswith("/forbidden"):
                body, code = fixture_forbidden_page(), 403
            else:
                body, code = fixture_empty_page(), 404
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type",
                             "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def _stop_stub_server(srv):
    """Stop a stub server and free its port. shutdown() alone only
    stops the serve loop — the listening socket stays open until
    server_close(), so both are needed for a full cleanup."""
    try:
        srv.shutdown()
    finally:
        srv.server_close()


def run_probe(profile_dir, url, legs=("A", "B", "A"),
              nav_timeout_ms=NAV_TIMEOUT_MS, settle_ms=SETTLE_MS):
    """Run the legs sequentially under one playwright session and
    return the record dict (legs + verdict)."""
    from playwright.sync_api import sync_playwright
    record = {"tool": "scripts/diag_egx_ab.py", "issue": 283,
              "url": url, "legs": legs, "profile": profile_dir,
              "nav_timeout_ms": nav_timeout_ms,
              "settle_ms": settle_ms,
              "started": utcnow(), "legs_records": []}
    with sync_playwright() as pw:
        for leg in legs:
            record["legs_records"].append(
                run_leg(pw, leg, profile_dir, url,
                        nav_timeout_ms, settle_ms))
    verdict, note = derive_verdict(record["legs_records"])
    record["verdict"] = verdict
    record["verdict_note"] = note
    record["finished"] = utcnow()
    return record


def write_outputs(record, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "diag-egx-ab.json"), "w",
              encoding="utf-8") as f:
        json.dump(record, f, indent=1, ensure_ascii=False)
    lines = ["diag-egx-ab (issue #283) url=%s" % record["url"],
             "started=%s finished=%s" % (record["started"],
                                         record["finished"])]
    for leg in record["legs_records"]:
        lines.append(
            "leg %s (%s): status=%s final_url=%s body_chars=%d "
            "classification=%s nav_error=%s" % (
                leg["leg"], leg["config"], leg["status"],
                leg["final_url"], leg["body_chars"],
                leg["classification"], leg["nav_error"] or "-"))
    lines.append("verdict: %s — %s" % (record["verdict"],
                                       record["verdict_note"]))
    with open(os.path.join(out_dir, "diag-egx-ab.log"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=None,
                    help="persistent Chromium profile dir (required "
                         "unless --dry-run)")
    ap.add_argument("--url", default=DIAG_URL,
                    help="URL both legs fetch (default: the fixed "
                         "POUL NewsSearch URL)")
    ap.add_argument("--out-dir", default="diag-egx-ab",
                    help="output dir for diag-egx-ab.json + .log")
    ap.add_argument("--legs", default="A,B,A",
                    help="comma-separated leg sequence (default A,B,A)")
    ap.add_argument("--dry-run", action="store_true",
                    help="serve SIMULATED pages locally and run both "
                         "legs against them (no EGX contact)")
    ap.add_argument("--nav-timeout-ms", type=int,
                    default=NAV_TIMEOUT_MS)
    ap.add_argument("--settle-ms", type=int, default=SETTLE_MS)
    args = ap.parse_args(argv)
    legs = [t.strip().upper() for t in args.legs.split(",") if t.strip()]
    if not legs or any(t not in ("A", "B") for t in legs):
        print("bad --legs: %r (use A/B only)" % args.legs,
              file=sys.stderr)
        return 2
    url = args.url
    profile_dir = args.profile
    srv = None
    # Issue #394: a dry-run without --profile gets an auto-created
    # profile dir; it is removed on every exit path below, including
    # a failure during dry-run setup itself (e.g. BrokenPipeError
    # from the stub print) — so the try/finally starts BEFORE the
    # setup, not after it. A user-supplied --profile is never
    # removed. The stub server is likewise shut down on every path.
    created_profile_dir = False
    try:
        if args.dry_run:
            srv, base = start_stub_server()
            url = base + "/ar/NewsSearch.aspx?com=&word=&from=19/08/2026" \
                "&to=19/11/2026&isin=EGS02051C018&sec_id=20"
            if not profile_dir:
                profile_dir = tempfile.mkdtemp(
                    prefix="diag-egx-ab-prof-")
                created_profile_dir = True
            print("dry-run: stub at %s (SIMULATED pages)" % base)
        if not profile_dir:
            print("--profile is required (unless --dry-run)",
                  file=sys.stderr)
            return 2
        try:
            import playwright  # noqa: F401 — import check before launching
        except ImportError:
            print("playwright is not installed; run in the egx-harvest "
                  "venv (worker) or install playwright", file=sys.stderr)
            return 2
        try:
            record = run_probe(profile_dir, url, legs,
                               args.nav_timeout_ms, args.settle_ms)
        finally:
            if srv is not None:
                _stop_stub_server(srv)
                srv = None
        for line in write_outputs(record, args.out_dir):
            print(line)
        return 0
    finally:
        if srv is not None:
            _stop_stub_server(srv)
        if created_profile_dir:
            shutil.rmtree(profile_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
