#!/usr/bin/env python3
"""EGX disclosure harvester (issue #47) — runs on the worker.

egx.com.eg sits behind F5 TSPD bot defense: plain HTTP and fresh
headless sessions get challenge shells; a real, PERSISTENT browser
profile passes. The worker keeps one profile (egx-profile/) and
reuses it for every harvest, so the TSPD trust the profile earns is
kept between runs.

v2 diagnostics: every run writes results/debug.json describing what
the browser actually saw (title, body sample, TSPD markers, form
inventory) so a zero-item harvest is explainable from the bus alone.
"""
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta

PROFILE = os.environ.get("GATOR_ROOT", "/opt/gator") + "/egx-profile"
RESULTS = "results"
# Issue #279: attachment capture lives in the sibling module; the
# script dir is on sys.path whether run as a script or loaded by a
# test harness via importlib (which does not add it).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attachment_capture import capture_item_attachments  # noqa: E402
BASE = "https://www.egx.com.eg"
EGX_COMPANIES = {
    "POUL": ("القاهرة للدواجن", "EGS02051C018"),
    "COMI": ("البنك التجاري الدولي", "EGS60121C018"),
    "ETEL": ("المصرية للاتصالات", "EGS48031C016"),
    "HRHO": ("المجموعة المالية هيرمس", "EGS69101C011"),
    "TMGH": ("طلعت مصطفى", "EGS691S1C011"),
    "SWDY": ("السويدي اليكتريك", "EGS3G0Z1C014"),
    "ESRS": ("عز ستيل", "EGS3C251C013"),
    "ABUK": ("أبو قير للأسمدة", "EGS38161C013"),
    "AMOC": ("الإسكندرية للزيوت المعدنية", "EGS380P1C010"),
    "EKHO": ("القابضة المصرية الكويتية", "EGS69082C013"),
}


def is_valid_isin(isin):
    """ISO 6166 check-digit validation for one ISIN.

    An ISIN is 2 country letters + 9 alphanumerics + 1 check digit.
    Letters convert A=10 .. Z=35, then the digit string must satisfy
    the Luhn mod-10 check (every second digit from the right,
    check digit included, is doubled, values >9 reduced by 9).
    Returns False for malformed strings as well as bad check digits.
    """
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


def validate_egx_companies_isins(companies=None):
    """Fail loudly on any mistyped ISIN in the EGX_COMPANIES table.

    Returns the list of bad (code, isin) pairs (empty when the table
    is clean). Raises ValueError naming every bad entry, so a typo
    can never flow silently into a harvest query — it must be fixed
    at the source instead. Issue #304: the AMOC entry carried
    EGS3E2B1C018, which fails this check and is not a real ISIN.
    """
    table = EGX_COMPANIES if companies is None else companies
    bad = [(code, isin) for code, (_ar, isin) in table.items()
           if not is_valid_isin(isin)]
    if bad:
        raise ValueError(
            "invalid ISIN(s) in EGX_COMPANIES (ISO 6166 check digit): "
            + ", ".join(f"{code}={isin}" for code, isin in bad))
    return bad


def log(*a):
    print("[egx-harvest]", *a, flush=True)


def page_state(page):
    return page.evaluate("""() => {
      const body = document.body ? document.body.innerText : '';
      const selects = [...document.querySelectorAll('select')].map(s => ({
        id: s.id, name: s.name, options: s.options.length,
        sample: [...s.options].slice(0, 3).map(o => o.text)}));
      return {
        title: document.title,
        url: location.href,
        body_chars: body.length,
        body_sample: body.slice(0, 1200),
        tspd: /tspd|bot detection|are you human|captcha/i.test(
          document.documentElement.innerHTML),
        selects: selects,
        inputs: [...document.querySelectorAll('input')].slice(0, 12)
          .map(i => ({id: i.id, name: i.name, type: i.type})),
        detail_links: document.querySelectorAll(
          'a[href*="NewsDetails.aspx"]').length,
      };
    }""")


def extract_main_text(page):
    return page.evaluate("""() => {
      const bad = /^(script|style|nav|header|footer)$/i;
      let best = '', bestLen = 0;
      document.querySelectorAll('div, td, article, section').forEach(el => {
        if (bad.test(el.tagName)) return;
        const t = (el.innerText || '').trim();
        if (t.length > bestLen && t.length < 20000) {
          const links = el.querySelectorAll('a').length;
          if (t.length > 300 && links < 40) { best = t; bestLen = t.length; }
        }
      });
      return best || (document.body ? document.body.innerText : '');
    }""")


def collect_result_links(page):
    return page.evaluate("""() => {
      const out = [];
      document.querySelectorAll('a[href*="NewsDetails.aspx"]').forEach(a => {
        const row = a.closest('tr') || a.parentElement;
        out.push({href: a.href,
                  text: (a.innerText || '').trim(),
                  row: row ? (row.innerText || '').trim() : ''});
      });
      return out;
    }""")


def collect_attachment_links(page):
    """All anchors on the detail page, for issue #279 attachment
    capture. Returns [{"href", "text"}]; the capture module decides
    which are attachment links (never the page's own navigation)."""
    return page.evaluate("""() => {
      return [...document.querySelectorAll('a[href]')].map(a => ({
        href: a.href, text: (a.innerText || '').trim()}));
    }""")


def iso_date(body, row_text=""):
    """Publish date of one harvested EGX disclosure (issue #274).

    The date is the dd/mm/yyyy that stands alone on its own line
    under the title — the same rule as scripts/disclosure_events.py
    _announced (basis "standalone-date-line") and the downstream
    news-disclosure-runner _harvest_publish_date. Never the first
    date in the body, never a date inside a period range: for
    earnings the title line itself carries the reporting period
    ("... عن الفترة: من 01/01/2026 إلى 30/09/2026"), so a
    first-date-wins rule stamps the period start as the publish
    date (COMI 297291/297289 were stamped 2026-01-01 while the
    real publish date sits on its own line just below, 10/11/2026).

    First valid standalone line wins; an invalid standalone line
    is skipped. No fallback to first-date-wins: an item with no
    standalone date line is dateless (""), never silently stamped
    with a period start. The search-row text is scanned the same
    way (standalone lines only) — it is the same title, so it
    cannot rescue a dateless item with a period date either.
    Returns "YYYY-MM-DD" or "".
    """
    for hay in (body or "", row_text or ""):
        for m in re.finditer(r"(?m)^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$",
                             hay):
            try:
                dt = datetime(int(m.group(3)), int(m.group(2)),
                              int(m.group(1)))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue  # invalid standalone line: keep looking
    return ""


def main():
    code = (sys.argv[1] if len(sys.argv) > 1 else "").upper().split(".")[0]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    if code not in EGX_COMPANIES:
        print(f"egx_harvest: no EGX listing known for {code}", file=sys.stderr)
        return 2
    ar_name, isin = EGX_COMPANIES[code]
    # Issue #304: a mistyped ISIN must fail here, loudly, before it
    # flows into a harvest query — never launch the browser on a
    # value that cannot be a real ISIN.
    if not is_valid_isin(isin):
        raise ValueError(
            f"invalid ISIN for {code}: {isin} "
            "(fails ISO 6166 check digit)")
    os.makedirs(RESULTS, exist_ok=True)
    to_d = date.today()
    from_d = to_d - timedelta(days=days)
    fmt = "%d/%m/%Y"
    import shutil
    debug = {"ticker": code, "stages": [],
             "xvfb": shutil.which("Xvfb") or shutil.which("xvfb-run")}

    from playwright.sync_api import sync_playwright
    items = []
    # INS-R3-04: a previous run killed mid-flight can orphan a
    # Chromium that holds the persistent profile's lock, failing
    # every later launch. If no process is using this profile,
    # clear the stale singleton locks before launching.
    try:
        import subprocess
        alive = subprocess.run(["pgrep", "-f", "egx-profile"],
                               capture_output=True).returncode == 0
        if not alive:
            for lock in ("SingletonLock", "SingletonCookie",
                         "SingletonSocket"):
                p = os.path.join(PROFILE, lock)
                if os.path.lexists(p):
                    os.unlink(p)
    except Exception:
        pass
    with sync_playwright() as pw:
        headful = bool(os.environ.get("DISPLAY"))
        ctx = pw.chromium.launch_persistent_context(
            PROFILE, headless=not headful,
            viewport={"width": 1366, "height": 768},
            timezone_id="Africa/Cairo",
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            locale="ar-EG")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        netlog = []
        page.on("requestfailed", lambda r: netlog.append(
            {"url": r.url[:120],
             "error": (r.failure or "")[:200]}))
        page.on("response", lambda r: netlog.append(
            {"url": r.url[:120], "status": r.status})
            if r.status >= 400 else None)
        # Reachability probes: which variant of the site answers?
        for probe in ("https://www.egx.com.eg/ar/",
                      "https://www.egx.com.eg/",
                      "http://www.egx.com.eg/ar/",
                      "https://egx.com.eg/ar/"):
            try:
                resp = page.goto(probe, wait_until="domcontentloaded",
                                 timeout=45000)
                debug["stages"].append(
                    {"probe": probe,
                     "status": resp.status if resp else None,
                     "state": page_state(page)})
                if page_state(page)["body_chars"] > 200:
                    break
            except Exception as e:
                debug["stages"].append(
                    {"probe": probe, "error": str(e)[:250]})
            page.wait_for_timeout(3000)
        debug["netlog"] = netlog[:30]
        # Warm-up: land on the site root first, like a human would.
        try:
            page.goto(BASE + "/ar/", wait_until="domcontentloaded",
                      timeout=90000)
            page.wait_for_timeout(10000)
            debug["stages"].append({"warmup": page_state(page)})
        except Exception as e:
            debug["stages"].append({"warmup_error": str(e)[:200]})
        url = (f"{BASE}/ar/NewsSearch.aspx?com=&word="
               f"&from={from_d.strftime(fmt)}&to={to_d.strftime(fmt)}"
               f"&isin={isin}&sec_id=20")
        log("search:", url)
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        # TSPD serves a 200 with an EMPTY body while its challenge JS
        # runs; wait until real content appears (up to ~90 s).
        waited = 0
        while waited < 90000:
            page.wait_for_timeout(5000)
            waited += 5000
            if page_state(page)["body_chars"] > 200:
                break
        debug["stages"].append({"param_search": page_state(page),
                                "tspd_wait_ms": waited})
        links = collect_result_links(page)
        if not links:
            log("parameterized search empty — driving the form")
            st = debug["stages"][-1]["param_search"]
            for sel in st.get("selects", []):
                if sel["options"] > 20:  # the company dropdown
                    try:
                        page.select_option(f"#{sel['id']}", label=ar_name,
                                           timeout=15000)
                        page.wait_for_timeout(10000)
                        debug["stages"].append(
                            {"after_select": page_state(page)})
                        links = collect_result_links(page)
                        break
                    except Exception as e:
                        log("select failed:", str(e)[:200])
        log("result links:", len(links))
        debug["links"] = len(links)

        # iso_date is module-level (issue #274): the publish date
        # is the standalone dd/mm/yyyy line, never first-date-wins.

        def write_out():
            out = {"ticker": f"{code}.CA", "company_ar": ar_name,
                   "isin": isin,
                   "harvested_at": time.strftime(
                       "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "count": len(items), "items": items}
            with open(os.path.join(RESULTS, "disclosures.json"),
                      "w") as f:
                json.dump(out, f, indent=1, ensure_ascii=False)

        seen = set()
        deadline = time.time() + 1500  # INS-R3-04: bounded loop
        for lk in links:
            if len(items) >= 25 or time.time() > deadline:
                log("harvest cap/deadline reached at", len(items))
                break
            m = re.search(r"NewsID=(\d+)", lk["href"])
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            dpage = ctx.new_page()
            try:
                try:
                    dpage.goto(lk["href"], wait_until="domcontentloaded",
                               timeout=90000)
                    dpage.wait_for_timeout(6000)
                    body = extract_main_text(dpage)
                except Exception as e:
                    log("details failed", lk["href"], str(e)[:150])
                    body = ""
                # Issue #279: attachment capture. Each step fails
                # independently and is recorded on the item — a
                # failed capture never loses the harvested body and
                # never fails the harvest.
                try:
                    anchors = collect_attachment_links(dpage)
                except Exception as e:
                    log("attachment links failed", lk["href"],
                        str(e)[:150])
                    anchors = None

                def _fetch(url, _page=dpage):
                    # Same browser session as the detail page, so the
                    # TSPD-trusted profile's cookies ride along.
                    resp = _page.request.get(url, timeout=60000)
                    return resp.status, resp.body()

                try:
                    attachments = capture_item_attachments(
                        m.group(1), anchors, lk["href"], _fetch, RESULTS)
                except Exception as e:
                    log("attachment capture failed", lk["href"],
                        str(e)[:150])
                    attachments = [{"status": "link_scan_failed",
                                    "path": None, "sha256": None,
                                    "size_bytes": None, "source_url": None,
                                    "reason": "capture raised: %s"
                                    % str(e)[:200]}]
            finally:
                dpage.close()
            items.append({
                "id": m.group(1), "kind": "disclosure", "source": "egx.com.eg",
                "date": iso_date(body, lk["row"]),
                "title": lk["text"][:200], "url": lk["href"],
                "row_text": lk["row"][:300], "body": body[:8000],
                "body_chars": len(body),
                "attachments": attachments})
            write_out()  # incremental: a timeout keeps what exists
            log("item", m.group(1), "body_chars", len(body),
                "attachments",
                ",".join(a["status"] for a in attachments))
            time.sleep(1)
        ctx.close()
    with open(os.path.join(RESULTS, "debug.json"), "w") as f:
        json.dump(debug, f, indent=1, ensure_ascii=False)
    out = {"ticker": f"{code}.CA", "company_ar": ar_name, "isin": isin,
           "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "count": len(items), "items": items}
    with open(os.path.join(RESULTS, "disclosures.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"egx_harvest: {code} items={len(items)} "
          f"bodies={sum(1 for i in items if i['body_chars'] >= 200)}")
    if not items:
        # A zero-item harvest is a FAILURE (wall changed, layout
        # changed, profile trust lost) — never a silent success:
        # callers must not cache it or report the job ok. (Panel
        # round 3, Gemini finding 3.)
        print("egx_harvest: zero items — treating as failure",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
