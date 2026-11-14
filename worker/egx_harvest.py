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
from datetime import date, timedelta

PROFILE = os.environ.get("GATOR_ROOT", "/opt/gator") + "/egx-profile"
RESULTS = "results"
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
    "AMOC": ("الإسكندرية للزيوت المعدنية", "EGS3E2B1C018"),
    "EKHO": ("القابضة المصرية الكويتية", "EGS69082C013"),
}


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
    debug = {"ticker": code, "stages": []}

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
        page.wait_for_timeout(15000)
        debug["stages"].append({"param_search": page_state(page)})
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
                log("details failed", lk["href"], str(e)[:150])
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
    with open(os.path.join(RESULTS, "debug.json"), "w") as f:
        json.dump(debug, f, indent=1, ensure_ascii=False)
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
