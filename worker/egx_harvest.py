#!/usr/bin/env python3
"""EGX disclosure harvester (issue #47) — runs on the worker.

egx.com.eg sits behind F5 TSPD bot defense: plain HTTP and fresh
headless sessions get challenge shells; a real, PERSISTENT browser
profile passes. The worker keeps one profile (egx-profile/) and
reuses it for every harvest, so the TSPD trust the profile earns is
kept between runs.

Job: harvest the official disclosure texts («إفصاح الشركات», section
20) for one EGX company from the exchange's own search + details
pages, and write them as feed-style items (id, date, title, url,
body) to results/disclosures.json — the stage-B consumer is
news-disclosure's fetch_feed, which today only gets Mubasher titles
for these same items because Mubasher's pages are JS shells.

Search strategy: try the parameterized search URL first (ISIN is a
form field); if it yields no result rows, drive the company dropdown
by its Arabic name instead. Details pages are server-rendered HTML;
the body is the page's main text block.
"""
import json
import os
import re
import sys
import time
from datetime import date, timedelta

PROFILE = os.environ.get("GATOR_ROOT", "/opt/gator") + "/egx-profile"
RESULTS = "results"
BASE = "https://www.egx.com.eg"
# code -> (Arabic name as listed on EGX, ISIN)
EGX_COMPANIES = {
    "POUL": ("القاهرة للدواجن", "EGS02051C018"),
    "COMI": ("البنك التجاري الدولي", "EGS60121C018"),
    "ETEL": ("المصرية للاتصالات", "EGS48031C016"),
    "HRHO": ("المجموعة المالية هيرمس", "EGS69101C011"),
    "TMGH": ("طلعت مصطفى", "EGS691S1C011"),
    "SWDY": ("السويدي اليكتريك", "EGS3G0Z1C014"),
    "ESRS": ("عز ستيل", "EGS3C251C013"),
    "ABUK": ("أبو قير للأسمدة", "EGS38161C013"),
    "AMOC": ("الإسكندرية للزيوت المعدنية", "EGS3E2B1C018"),
    "EKHO": ("القابضة المصرية الكويتية", "EGS69082C013"),
}


def log(*a):
    print("[egx-harvest]", *a, flush=True)


def extract_main_text(page):
    """Largest readable text block on a NewsDetails page."""
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


def main():
    code = (sys.argv[1] if len(sys.argv) > 1 else "").upper().split(".")[0]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    if code not in EGX_COMPANIES:
        print(f"egx_harvest: no EGX listing known for {code}", file=sys.stderr)
        return 2
    ar_name, isin = EGX_COMPANIES[code]
    os.makedirs(RESULTS, exist_ok=True)
    to_d = date.today()
    from_d = to_d - timedelta(days=days)
    fmt = "%d/%m/%Y"

    from playwright.sync_api import sync_playwright
    items = []
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            PROFILE, headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            locale="ar-EG")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        url = (f"{BASE}/ar/NewsSearch.aspx?com=&word="
               f"&from={from_d.strftime(fmt)}&to={to_d.strftime(fmt)}"
               f"&isin={isin}&sec_id=20")
        log("search:", url)
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(12000)  # TSPD resolves + grid renders
        links = collect_result_links(page)
        if not links:
            log("parameterized search empty — driving the form")
            try:
                page.select_option("select", label=ar_name, timeout=15000)
            except Exception as e:
                log("dropdown select failed:", e)
            page.wait_for_timeout(8000)
            links = collect_result_links(page)
        log("result links:", len(links))
        seen = set()
        for lk in links:
            m = re.search(r"NewsID=(\d+)", lk["href"])
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            dpage = ctx.new_page()
            try:
                dpage.goto(lk["href"], wait_until="domcontentloaded",
                           timeout=90000)
                dpage.wait_for_timeout(6000)
                body = extract_main_text(dpage)
            except Exception as e:
                log("details failed", lk["href"], e)
                body = ""
            finally:
                dpage.close()
            items.append({
                "id": m.group(1), "kind": "disclosure", "source": "egx.com.eg",
                "title": lk["text"][:200], "url": lk["href"],
                "row_text": lk["row"][:300], "body": body[:8000],
                "body_chars": len(body)})
            log("item", m.group(1), "body_chars", len(body))
            time.sleep(1)
        ctx.close()
    out = {"ticker": f"{code}.CA", "company_ar": ar_name, "isin": isin,
           "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "count": len(items), "items": items}
    with open(os.path.join(RESULTS, "disclosures.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"egx_harvest: {code} items={len(items)} "
          f"bodies={sum(1 for i in items if i['body_chars'] >= 200)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
