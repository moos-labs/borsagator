#!/usr/bin/env python3
"""Verification for issue #268 (full renderer-facing Arabic).

Renders a Report Model with scripts/render.py, simulates the EN->AR
toggle (a faithful port of setLang in render.py — same rules as
harness_issue69.ar_visible_text), and checks, per chrome site, that
the Arabic view carries the Arabic string while the English view and
the MD twin are unchanged.

Usage:
    test_render_i18n_268.py --model <report-model.json>
        --profile <profiles/TICKER.json> --sweep-dir <archived sweep>
        --out-dir <dir> [--baseline-html <old report.html>]
        [--expect-md <golden report.md>] [--mutations]

    --mutations additionally renders mutated copies of the model that
    exercise the branches the golden sweep does not hit (degraded,
    partial, every flag/risk-flag pattern, every enum value, LLM
    roles, provisional confidence basis, rescale states) and checks
    each renders, AR-simulates, and logs no display_unmapped line —
    except the two deliberate unknown-value cases, which must render
    verbatim EN with the log line (fail-open, never a refusal).

Exit 0 only when every check passes. Stdlib only.
"""
import argparse
import html as html_mod
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                       (" — " + str(detail)[:200]) if detail and not ok else ""))


def run_render(model, out_dir, profile, extra=None):
    cmd = [sys.executable, os.path.join(REPO, "scripts", "render.py"),
           model, "--profile", profile, "--out-dir", out_dir]
    if extra:
        cmd += extra
    return subprocess.run(cmd, capture_output=True, text=True)


def visible_text(html_text):
    txt = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<svg.*?</svg>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    return html_mod.unescape(txt)


def _fmt_tpl(tpl, args, display, table):
    def _sub(m):
        name = m.group(1)
        if name not in args:
            return m.group(0)
        v = args[name]
        kind = display.get(name)
        if kind:
            key = "display.%s.%s" % (kind, v)
            if key in table:
                return table[key]
        return v
    return re.sub(r"\{(\w+)\}", _sub, tpl)


def ar_visible_text(html_text):
    """Port of setLang('ar') (render.py TOGGLE_JS), mirroring
    harness_issue69.ar_visible_text."""
    m = re.search(r"window\.I18N=(\{.*?\});", html_text, re.S)
    table = json.loads(m.group(1)) if m else {}
    ar = table.get("ar", {})

    def _sub(mm):
        tag, pre, key, post = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
        if key in ar:
            return '<%s%sdata-i18n="%s"%s>%s</%s>' % (
                tag, pre, key, post, ar[key], tag)
        return mm.group(0)

    def _sub_tpl(mm):
        tag, pre, key, post = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
        if key not in ar:
            return mm.group(0)
        opening = pre + post
        args = {}
        for name, val in re.findall(r"data-tpl-([a-z0-9_]+)=\"([^\"]*)\"",
                                    opening):
            if name == "display":
                continue
            args[name] = html_mod.unescape(val)
        display = {}
        spec = re.search(r"data-tpl-display=\"([^\"]*)\"", opening)
        if spec:
            for pair in spec.group(1).split(","):
                kv = pair.split(":")
                if len(kv) == 2:
                    display[kv[0]] = kv[1]
        return '<%s%sdata-i18n-tpl="%s"%s>%s</%s>' % (
            tag, pre, key, post,
            _fmt_tpl(ar[key], args, display, ar), tag)

    body = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
    out = re.sub(r"<(\w+)([^>]*?)data-i18n=\"([^\"]+)\"([^>]*)>(.*?)</\1>",
                 _sub, body, flags=re.S)
    out = re.sub(r"<(\w+)([^>]*?)data-i18n-tpl=\"([^\"]+)\"([^>]*)>(.*?)</\1>",
                 _sub_tpl, out, flags=re.S)
    return visible_text(out)


def numbers_in(text):
    # Same extraction as harness_issue69.numbers_in (percentages +
    # decimals only — bare integers such as years are not numbers
    # here, so a template that spells out a count in words cannot
    # break parity by dropping a digit).
    out = []
    for m in re.finditer(r"[-+]?\d[\d,]*\.?\d*\s*%", text):
        out.append(float(m.group(0).replace("%", "").replace(",", "").strip()))
    for m in re.finditer(r"(?<![\w.])[-+]?\d+\.\d+(?![\w.])", text):
        out.append(float(m.group(0)))
    return sorted(out)


# (site, EN marker, AR marker) — the per-site verification table for
# the golden sweep. Markers are distinctive substrings of the EN and
# AR visible text.
SITES = [
    ("title", "Borsagator report — POUL.CA (2026-11-19)",
     "تقرير بورساجاتور — POUL.CA (2026-11-19)"),
    ("header.job", "Job: sweep-lite", "المهمة: sweep-lite"),
    ("header.model", "archive commit:", "بصمة الأرشيف:"),
    ("ui.copy", "Copy model JSON", "نسخ نموذج JSON"),
    ("disclaimer.short", "Borsagator is not an investment adviser",
     "بورساجاتور ليست مستشارًا استثماريًا"),
    ("sec.bands", "Technical Support / Resistance Levels",
     "مستويات الدعم / المقاومة الفنية"),
    ("bands.support", "Technical Support Level at", "مستوى الدعم الفني عند"),
    ("bands.resistance", "Technical Resistance Level at",
     "مستوى المقاومة الفنية عند"),
    ("bands.basis", "week horizon range_low_pct",
     "نطاق أفق الأسبوع range_low_pct"),
    ("framing", "not a recommendation to buy, sell, or hold",
     "وليس توصية بشراء أو بيع أو الاحتفاظ"),
    ("rec.base", "Base price:", "السعر الأساسي:"),
    ("headline", "Families disagree: price-forecast +0.40 vs sentiment -0.02 (spread +0.42)",
     "تختلف العائلات: توقع السعر +0.40 مقابل المشاعر -0.02 (الفرق +0.42)"),
    ("th.family/score", "Family", "العائلة"),
    ("family.names", "price-forecast", "توقع السعر"),
    ("fam.nodata", "no data", "لا توجد بيانات"),
    ("weights.applied", "Applied weights (ledger):", "الأوزان المطبّقة (السجل):"),
    ("weights.confidence", "Confidence basis:", "أساس الثقة:"),
    ("confidence-basis", "calibrated (ledger skill factors applied)",
     "مُعايَر (طُبِّقَت عوامل مهارة السجل)"),
    ("delta.none", "First sweep of this ticker", "أول مسح لهذا السهم"),
    ("sec.horizons", "Horizons + price", "الآفاق + السعر"),
    ("th.horizon", "Horizon", "الأفق"),
    ("horizon.names", "day", "يوم"),
    ("direction", "up", "صاعد"),
    ("price.base", "Base price: 7.70", "السعر الأساسي: 7.70"),
    ("price.crosscheck", "Price cross-check: agree", "التحقق المتقاطع للسعر: متفق"),
    ("price.stale-note", "Witnesses stale:", "الشواهد متقادمة:"),
    ("th.source", "Source", "المصدر"),
    ("price.stale", "(stale)", "(قديم)"),
    ("reaction.built", "Built at 2026-11-14T23:44:23Z", "بُني في 2026-11-14T23:44:23Z"),
    ("th.eventtype", "Event type", "نوع الحدث"),
    ("event-type", "dividend", "توزيعات"),
    ("reaction.events", "Events: 22 recorded.", "الأحداث: 22 مسجلة."),
    ("tools.status", "Status: ok", "الحالة: ناجح"),
    ("tools.runtable", "Tool run table", "جدول تشغيل الأدوات"),
    ("th.category", "Category", "الفئة"),
    ("category", "technicals", "فني"),
    ("tools.run.worker", "worker run worker-runs/", "تشغيل العامل worker-runs/"),
    ("news.line", "News: 32", "الأخبار: 32"),
    ("sentiment.company", "Company:", "الشركة:"),
    ("risk.level", "Risk level: shock", "مستوى الخطر: صدمة"),
    ("riskflag.event", "earnings event:", "حدث أرباح:"),
    ("risk.corporate", "Corporate action: dividend", "إجراء مؤسسي: توزيع نقدي"),
    ("chart.legend", "Solid: recorded closes", "متصل: إغلاقات مسجلة"),
    ("sec.llm", "LLM provenance", "مصدر النماذج اللغوية"),
    ("llm.none", "Model not recorded (pre-#74 run).",
     "النموذج غير مسجل (تشغيل قبل #74)."),
    ("ledger.counts", "Ledger counts — sweeps: 48", "أعداد السجل — المسوح: 48"),
    ("ledger.accuracy", "No accuracy figure is published",
     "لا يُنشر أي رقم دقة"),
    ("flag.witnesses-stale", "witnesses-stale:", "شواهد متقادمة:"),
    ("flag.tree-sha", "tree-sha-unavailable:", "تعذّر اشتقاق بصمة الشجرة:"),
    ("flag.recommendation-stale", "recommendation-stale:", "توصية قديمة:"),
    ("flag.sharia", "sharia-insufficient-data: AAOIFI",
     "بيانات شرعية غير كافية: AAOIFI"),
    ("prov.line", "Provenance: merged by worker",
     "المصدر والتتبع: دُمج بواسطة العامل"),
    ("prov.viewer", "Viewer:", "المشاهد:"),
    ("ui.footer", "Deterministic glue", "ربط حتمي"),
]

# English words that may never survive into the AR view as chrome.
# (Quoted tool reports / news titles / identifiers are excluded by
# the classifier before this list is consulted.)
CHROME_WATCH = {
    "families", "disagree", "spread", "risk", "level", "news",
    "disclosures", "identity", "scheme", "status", "exit", "code",
    "price", "chart", "solid", "recorded", "closes", "dashed",
    "forecast", "technical", "support", "resistance", "base",
    "reference", "applied", "weights", "confidence", "basis",
    "previous", "current", "built", "walk-forward", "train", "test",
    "hits", "baseline", "events", "ledger", "counts", "sweeps",
    "matured", "pending", "invalid", "provenance", "merged",
    "viewer", "deterministic", "glue", "research", "tooling",
    "financial", "advice", "copy", "model", "json", "english",
    "horizon", "direction", "expected", "range", "source", "last",
    "date", "close", "volume", "tool", "category", "run", "worker",
    "table", "family", "score", "not", "scored", "data", "company",
    "corporate", "action", "rescale", "witnesses", "stale",
    "trails", "sharia", "insufficient", "table", "missing",
    "recommendation", "unavailable", "tree", "sha", "archive",
    "given", "checkout", "derive", "flags", "quality",
}


def classify_ar_leftovers(ar_html, model, sweep_dir):
    """Every Latin-bearing DOM node of the AR view, classified:
    quoted tool report / news title / identifier-or-number / CHROME.
    Returns (leftover_words, node_count, latin_node_count)."""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.nodes = []
            self.skip = 0
        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip += 1
        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self.skip -= 1
        def handle_data(self, data):
            if self.skip:
                return
            t = data.strip()
            if t:
                self.nodes.append(t)

    p = P()
    p.feed(ar_html)
    latin_nodes = [n for n in p.nodes if re.search(r"[A-Za-z]", n)]
    # Allowed Latin: quoted tool reports + news/disclosure titles.
    # Markdown markers are stripped first: the renderer's md->html
    # converter splits a quoted line at **bold** / `code`, so a DOM
    # node is often a fragment of the quoted line, not the whole.
    allowed = []
    if sweep_dir:
        coll = os.path.join(sweep_dir, "collected")
        if os.path.isdir(coll):
            for tool in sorted(os.listdir(coll)):
                path = os.path.join(coll, tool, "report.md")
                if os.path.isfile(path):
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        allowed.append(re.sub(r"\s+", " ", fh.read()))
    news = model.get("news") or {}
    for key in ("news_items", "disclosure_items"):
        for item in news.get(key) or []:
            if item.get("title"):
                allowed.append(re.sub(r"\s+", " ", item["title"]))
    # Disclosure-events string values are model data too (the v2
    # block's event fields render verbatim as evidence): a DOM node
    # that equals one of them verbatim is data, not chrome. Without
    # this, extractor wording such as "decision details in
    # attachment, not harvested" (candidate_reasons) is misflagged as
    # chrome English (#280).
    # Tool-summary string values are model data too (company names,
    # source descriptions, method labels): a DOM node that equals
    # one of them verbatim is data, not chrome.
    def _str_leaves(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from _str_leaves(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from _str_leaves(v)
    for tool in model.get("tools") or []:
        for leaf in _str_leaves(tool.get("summary")):
            if len(leaf) >= 2:
                allowed.append(re.sub(r"\s+", " ", leaf))
    for leaf in _str_leaves(model.get("disclosure_events")):
        if len(leaf) >= 2:
            allowed.append(re.sub(r"\s+", " ", leaf))
    allowed_norm = [re.sub(r"\s+", " ", re.sub(r"[*`#]", "", a))
                    for a in allowed]

    def is_quoted(node):
        n = re.sub(r"\s+", " ", node)
        return any(n in a or a in n for a in allowed_norm)

    # Identifier-ish tokens: must contain a digit, underscore, dot,
    # slash, pipe, plus or hyphen (paths, tickers, codes, model
    # names, dates, numbers, units) — a plain lowercase word is NOT
    # an identifier and must be explained as quoted text instead.
    ident_re = re.compile(r"^(?=.*[\d_./|+\-])[\w./|+\-]+$")
    data_tokens = {
        # Fixed data tokens kept verbatim by design (not chrome):
        # the "English" language button (language names stay),
        # "None" (a profile repr artifact in the n column), tool /
        # model identifiers, metric keys rendered verbatim in the
        # per-tool tables, and the flag-template code-words
        # (as_of/base/sweep/common_date/base_date are field names
        # inside the flag strings, kept as identifiers).
        "english", "none", "as_of", "base", "sweep",
        "common_date", "base_date",
        "agent", "fundamentals", "price-forecast", "sentiment",
        "technicals", "finbert_negative", "finbert_neutral",
        "finbert_positive", "multilingual_negative",
        "multilingual_neutral", "multilingual_positive",
        "translated_negative", "translated_neutral",
        "translated_positive", "resolved_url|title-date-hash",
        "borsagator-report-model/1", "POUL.CA", "EGX",
        "ProsusAI/finbert", "yiyanghkust/finbert-tone",
        "soleimanian/financial-roberta-large-sentiment",
        "egx-data/egxpy_poul.csv", "sweep-lite",
        "sweep-lite POUL.CA market=EGX",
    }
    # Metric keys from the model's tool summaries are data, not
    # chrome: they render verbatim in the per-tool tables.
    for tool in model.get("tools") or []:
        summary = tool.get("summary")
        if isinstance(summary, dict):
            metrics = summary.get("metrics")
            if isinstance(metrics, dict):
                data_tokens.update(str(k).lower() for k in metrics)
            data_tokens.update(str(k).lower() for k in summary
                               if k in ("label", "model", "company"))
    leftover = {}
    for node in latin_nodes:
        if is_quoted(node):
            continue
        for tok in re.findall(r"[A-Za-z][\w./|+\-]*", node):
            if tok in data_tokens or ident_re.match(tok):
                continue
            # tokens inside an identifier-ish span (paths etc.)
            if "/" in tok or "_" in tok or tok.isupper():
                continue
            leftover[tok.lower()] = leftover.get(tok.lower(), 0) + 1
    return leftover, len(p.nodes), len(latin_nodes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--sweep-dir", default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--baseline-html", default=None)
    ap.add_argument("--expect-md", default=None)
    ap.add_argument("--mutations", action="store_true")
    args = ap.parse_args(argv)

    model = json.load(open(args.model, encoding="utf-8"))
    profile = args.profile or os.path.join(
        REPO, "profiles", "%s.json" % model.get("ticker"))
    proc = run_render(args.model, args.out_dir, profile,
                      ["--sweep-dir", args.sweep_dir] if args.sweep_dir else [])
    check("render exits 0", proc.returncode == 0, proc.stderr[:300])
    if proc.returncode != 0:
        return 1
    check("no display_unmapped on golden render",
          "display_unmapped" not in proc.stderr, proc.stderr[:300])
    html_path = os.path.join(args.out_dir, "report.html")
    md_path = os.path.join(args.out_dir, "report.md")
    h = open(html_path, encoding="utf-8").read()
    m = open(md_path, encoding="utf-8").read()

    # Data island: 0 raw "<", parses to the identical model.
    im = re.search(
        r'<script type="application/json" id="report-model">(.*?)</script>',
        h, re.S)
    check("data island present", im is not None)
    island = json.loads(im.group(1)) if im else {}
    check("island: 0 raw '<'", im and "<" not in im.group(1))
    check("island == committed model", island == model)

    # MD twin unchanged (EN-only by the #268 decision).
    if args.expect_md:
        check("MD twin unchanged",
              m == open(args.expect_md, encoding="utf-8").read())

    # EN view unchanged vs the pre-#268 render.
    en_vis = visible_text(h)
    if args.baseline_html:
        base_vis = visible_text(
            open(args.baseline_html, encoding="utf-8").read())
        check("EN visible text unchanged",
              re.sub(r"\s+", " ", en_vis) == re.sub(r"\s+", " ", base_vis))

    # i18n parity: every data-i18n / data-i18n-tpl / data-i18n-aria
    # key has EN+AR in the embedded table.
    tm = re.search(r"window\.I18N=(\{.*?\});", h, re.S)
    table = json.loads(tm.group(1)) if tm else {}
    for attr in ("data-i18n", "data-i18n-tpl", "data-i18n-aria"):
        keys = set(re.findall(r'%s="([^"]+)"' % attr, h))
        missing = [k for k in keys
                   if k not in table.get("en", {}) or k not in table.get("ar", {})]
        check("every %s key has EN+AR" % attr, missing == [], str(missing))

    # AR simulation + numeric parity.
    ar_vis = ar_visible_text(h)
    en_nums = numbers_in(en_vis)
    ar_nums = numbers_in(ar_vis)
    check("EN/AR numeric parity", len(en_nums) == len(ar_nums)
          and all(abs(a - b) <= 0.005 for a, b in zip(en_nums, ar_nums)),
          "en=%d ar=%d" % (len(en_nums), len(ar_nums)))
    check("AR sets lang/dir rtl",
          'document.documentElement.lang' in h and "dir=" in h)

    # Per-site table.
    for site, en_marker, ar_marker in SITES:
        check("site %s: EN present" % site, en_marker in en_vis)
        check("site %s: AR present" % site, ar_marker in ar_vis)

    # Remaining Latin in the AR view, classified.
    # Rebuild the AR HTML (not just visible text) for node parsing:
    # reuse the simulation on the HTML string itself.
    sim_html = _simulate_html(h)
    leftover, total_nodes, latin_nodes = classify_ar_leftovers(
        sim_html, model, args.sweep_dir)
    watch_hits = {w: c for w, c in leftover.items() if w in CHROME_WATCH}
    check("AR view: no chrome English left", not watch_hits,
          str(sorted(watch_hits.items())[:12]))
    if leftover:
        print("info: AR leftover Latin words (non-chrome): %s"
              % sorted(leftover.items())[:20])
    print("info: AR view nodes: %d total, %d Latin-bearing"
          % (total_nodes, latin_nodes))

    if args.mutations:
        return 0 if _mutations(args, model, profile) else 1
    failed = [c for c in CHECKS if not c[1]]
    print("268-verify: %d checks, %d failed" % (len(CHECKS), len(failed)))
    return 1 if failed else 0


def _simulate_html(html_text):
    """ar_visible_text but returning HTML (for node parsing)."""
    m = re.search(r"window\.I18N=(\{.*?\});", html_text, re.S)
    table = json.loads(m.group(1)) if m else {}
    ar = table.get("ar", {})

    def _sub(mm):
        tag, pre, key, post = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
        if key in ar:
            return '<%s%sdata-i18n="%s"%s>%s</%s>' % (
                tag, pre, key, post, ar[key], tag)
        return mm.group(0)

    def _sub_tpl(mm):
        tag, pre, key, post = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
        if key not in ar:
            return mm.group(0)
        opening = pre + post
        args = {}
        for name, val in re.findall(r"data-tpl-([a-z0-9_]+)=\"([^\"]*)\"",
                                    opening):
            if name == "display":
                continue
            args[name] = html_mod.unescape(val)
        display = {}
        spec = re.search(r"data-tpl-display=\"([^\"]*)\"", opening)
        if spec:
            for pair in spec.group(1).split(","):
                kv = pair.split(":")
                if len(kv) == 2:
                    display[kv[0]] = kv[1]
        return '<%s%sdata-i18n-tpl="%s"%s>%s</%s>' % (
            tag, pre, key, post,
            _fmt_tpl(ar[key], args, display, ar), tag)

    body = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
    out = re.sub(r"<(\w+)([^>]*?)data-i18n=\"([^\"]+)\"([^>]*)>(.*?)</\1>",
                 _sub, body, flags=re.S)
    out = re.sub(r"<(\w+)([^>]*?)data-i18n-tpl=\"([^\"]+)\"([^>]*)>(.*?)</\1>",
                 _sub_tpl, out, flags=re.S)
    return out


MUTATIONS = [
    ("degraded-keyless",
     lambda m: m.update(degraded={"reason": "keyless"}),
     ["متدهور:", "keyless"], []),
    ("partial",
     lambda m: m.update(partial=True),
     ["مسح جزئي"], []),
    ("ensemble-absent",
     lambda m: m.update(ensemble_absent=True),
     ["غير متاح — لا يوجد تجميع"], []),
    ("risk-elevated-nocap",
     lambda m: m["risk"].update(level="elevated", conf_cap=None),
     ["مستوى الخطر: مرتفع", "غير مسجّل"], []),
    ("risk-unknown",
     lambda m: m["risk"].update(level="unknown"),
     ["مستوى الخطر غير معروف"], []),
    ("direction-down-flat",
     lambda m: (m["horizons"]["day"].update(direction="down"),
                m["horizons"]["week"].update(direction="flat"),
                m["horizons"].pop("month")),
     ["هابط", "مستقر", "غير مُقيَّم"], []),
    ("crosscheck-disagree",
     lambda m: m["price"]["price_crosscheck"].update(status="disagree"),
     ["مختلف"], []),
    ("all-flag-patterns",
     lambda m: m.update(flags=[
         "witnesses-stale: common_date 2026-11-16 vs base_date 2026-11-18",
         "tree-sha-unavailable: archive SHA given by flag, no git checkout to derive the tree SHA",
         "archive-sha-unavailable: sweep dir is not a git checkout and no --archive-sha was given",
         "recommendation-unavailable: no profiles/POUL.CA.recommendation.json",
         "recommendation-stale: profile as_of 2026-11-13 base 10.15 != sweep 2026-11-19 base 7.7",
         "base-from-undated-row",
         "undated-actions: 2",
         "ledger-unreadable: ledger/ledger.json",
         "weights-sha-differs-from-main",
         "summary-missing: kronos (failed)",
         "sharia-table-missing: DJIM",
         "sharia-insufficient-data: AAOIFI",
     ]),
     ["شواهد متقادمة:", "تعذّر اشتقاق بصمة الشجرة:",
      "بصمة الأرشيف غير متاحة:", "التوصية غير متاحة:",
      "توصية قديمة:", "الأساس من صف بلا تاريخ",
      "إجراءات بلا تاريخ: 2", "السجل غير مقروء:",
      "بصمة الأوزان تختلف عن الرئيسية", "الملخص مفقود:",
      "جدول شرعي مفقود: DJIM", "بيانات شرعية غير كافية: AAOIFI"], []),
    ("all-riskflag-patterns",
     lambda m: m["risk"].update(flags=[
         "earnings event: some title here",
         "abnormal move: last session 3.2σ",
         "abnormal move: 3.2σ in the last 3 sessions",
         "price confirms: last session 1.8σ",
         "2 disclosure(s) in the last 3 days",
     ]),
     ["حدث أرباح:", "حركة غير طبيعية: الجلسة الأخيرة 3.2σ",
      "حركة غير طبيعية: 3.2σ في آخر 3 جلسات",
      "السعر يؤكد: الجلسة الأخيرة 1.8σ",
      "2 من الإفصاحات في آخر 3 أيام"], []),
    ("tool-statuses",
     lambda m: (m["tools"][0].update(status="failed"),
                m["tools"][1].update(status="error"),
                m["tools"][2].update(category="agent"),
                m.update(tools_absent=["gone-tool"],
                         tools_failed=["broke-tool"])),
     ["فشل", "خطأ", "وكيل", "غائب"], []),
    ("provisional-basis",
     lambda m: (m["weights"].update(
         confidence_basis="provisional (uncalibrated — no scoring history yet)"),
         m["levels"].update(
             basis="week horizon range_low_pct / range_high_pct")),
     ["مؤقت (غير مُعايَر", "نطاق أفق الأسبوع range_low_pct"], []),
    ("llm-roles-sentinels",
     lambda m: m["llm"].update(llm_status="recorded", calls=[
         {"tool": "news-disclosure", "role": "llm", "model": None,
          "tokens_in": None, "tokens_out": None, "usd": None},
         {"tool": "news-disclosure", "role": "translation", "model": None,
          "tokens_in": None, "tokens_out": None, "usd": None}]),
     ["نموذج لغوي", "ترجمة", "غير مسجّل",
      "النموذج: غير مسجّل", "الرموز الداخلة/الخارجة:"], []),
    ("merged-by-actions",
     lambda m: m["provenance"].update(merged_by="actions"),
     ["GitHub Actions"], []),
    ("rescale-applied",
     lambda m: m.update(kronos_ex_rescale={"applied": True, "factor": 0.8}),
     ["طُبّقت إعادة القياس: المعامل 0.8"], []),
    ("rescale-attempted",
     lambda m: m.update(kronos_ex_rescale={
         "applied": False, "reason": "no ex-date in window"}),
     ["حاولت إعادة القياس ولم تُطبَّق"], []),
    ("sentiment-label",
     lambda m: [t["summary"].update(label="positive")
                for t in m["tools"] if t["tool"] == "finbert"],
     ["إيجابي"], []),
    ("unknown-flag-fail-open",
     lambda m: m.update(flags=["bogus-flag: xyz"]),
     ["bogus-flag: xyz"],
     ["display_unmapped: model flag 'bogus-flag: xyz'"]),
    ("unknown-direction-fail-open",
     lambda m: m["horizons"]["day"].update(direction="sideways"),
     ["sideways"],
     ["display_unmapped: direction 'sideways'"]),
]


def _mutations(args, model, profile):
    import copy
    import tempfile
    ok = True
    for name, mutate, ar_markers, expect_logs in MUTATIONS:
        m = copy.deepcopy(model)
        mutate(m)
        with tempfile.TemporaryDirectory(prefix="268-mut-") as td:
            mp = os.path.join(td, "model.json")
            with open(mp, "w", encoding="utf-8") as fh:
                json.dump(m, fh)
            out = os.path.join(td, "out")
            proc = run_render(mp, out, profile,
                              ["--sweep-dir", args.sweep_dir]
                              if args.sweep_dir else [])
            passed = proc.returncode == 0
            if not passed:
                check("mutation %s renders" % name, False,
                      proc.stderr[:200])
                ok = False
                continue
            for want in expect_logs:
                if want not in proc.stderr:
                    check("mutation %s logs %r" % (name, want), False,
                          proc.stderr[:200])
                    ok = False
            if not expect_logs and "display_unmapped" in proc.stderr:
                check("mutation %s: no display_unmapped" % name, False,
                      proc.stderr[:300])
                ok = False
            h = open(os.path.join(out, "report.html"),
                     encoding="utf-8").read()
            ar_vis = ar_visible_text(h)
            for marker in ar_markers:
                if marker not in ar_vis:
                    check("mutation %s: AR %r" % (name, marker), False)
                    ok = False
            check("mutation %s" % name, passed)
    failed = [c for c in CHECKS if not c[1]]
    print("268-verify: %d checks, %d failed" % (len(CHECKS), len(failed)))
    return not failed


if __name__ == "__main__":
    sys.exit(main())
