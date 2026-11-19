#!/usr/bin/env python3
"""Proof harness for issue #69 (deterministic report renderer).

Harness-first, per the #69 deep scoping §8 proof plan. Runs the
renderer (``scripts/render.py``, stdlib only) over REAL Report Models
compiled from real archived sweeps with the real #68 compiler
(``scripts/compile_model.py``) — models are compiled fresh per run,
never hand-written — plus synthetic mutations for the degraded and
negative cases. Archive reads only; no Actions logs or artifacts.

Usage:
    harness_issue69.py [--archive-root PATH] [--stage PATH] [--keep-stage]
    harness_issue69.py --pristine [--archive-root PATH]

The archive root defaults to ``$BORSAGATOR_ARCHIVE_ROOT`` or the
sibling ``borsagator-69-archive`` checkout. Stage (models, mutated
copies, outputs) defaults to /tmp/borsagator-69-harness; pass
--stage to put it on real disk (the VM's /tmp is a 512M tmpfs).

Pristine control (--pristine): a naive hand-rolled HTML dump of the
model (no escaping, no audit, no i18n table, no data island) is run
through the discriminating cases — it must FAIL cases 3, 9, 10, 12,
14 and 18. If the naive control passes any of them, the case does
not test what it claims and the harness exits 1.

Readings recorded here (scoping ambiguities resolved by the build):
- Case 13, second half: R-F11 drops secret-pattern fields from the
  DISPLAY (visible HTML + MD twin). The data island stays the model
  bytes verbatim (§2e); a dirty model is the compiler's failure
  (#68 R-12), not the renderer's. The harness asserts the display
  drop + the render-log line, and separately asserts the CLEAN
  render has no key names / unlabelled 40-hex anywhere incl. island.
- Case 1 headline: the scoping's "price-forecast +0.40" assumed
  decimal rounding of 0.395; the renderer formats 0.395 as +0.39,
  so fundamentals (+0.40) is the max and the headline reads
  "fundamentals +0.40 vs sentiment -0.10 (spread +0.50)".
- Case 5(b): the real NVDA sweep (140746) is refused by the #68
  compiler (no ensemble, no marker) — unrenderable by design, no
  model exists. The ensemble-absent case is therefore synthetic.

Ported coverage (2026-11-19, Muhammad's "port it onto main"
decision): the render-69 build's extra harness cases merged in —
case 1 corporate-actions / ledger-pin / sharia-flag checks, case 3
cwd + timestamp + model-untouched checks, case 10 wrong-field
limitation, case 11 envelope/vocabulary negatives, case 12 AR
long-disclaimer + EN/AR numeric parity, case 15 no-$ check, case
21 key-reorder invariance (render-69 T2), case 22 mutation
discrimination (render-69 T8, audit + clock mutants only).
Dropped with reasons recorded in the PR: render-69's
render_error.txt marker assertions (main's renderer does not write
the marker; the worker hook / Actions step does), its
recommendation-notes refusal (main does not prose-audit
recommendation.notes), its Eastern-Arabic-digits refusal (main's
audit traces them as Western values), its final-gate mutant (no
second gate on main, §2i), its MD model-SHA check (main's MD
carries no SHA line) and its pristine P-series (main's control is
a static-string discrimination).
"""
import argparse
import datetime
import hashlib
import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

ARCHIVE_DEFAULT = os.environ.get(
    "BORSAGATOR_ARCHIVE_ROOT",
    os.path.join(os.path.dirname(REPO), "borsagator-69-archive"))
STAGE_DEFAULT = os.environ.get("BORSAGATOR_HARNESS_STAGE",
                               "/tmp/borsagator-69-harness")

SWEEPS = {
    "141124": ("sweeps/2026-11-16/141124__sweep-lite-poul-ca__"
               "run43875894633"),
    "141558": ("sweeps/2026-11-15/141558__sweep-lite-poul-ca-market-"
               "egx__run43721738392"),
    "050559": ("sweeps/2026-11-16/050559__sweep-lite-poul-ca-market-"
               "egx__run43805931446"),
    "085806": ("sweeps/2026-11-16/085806__sweep-lite-poul-ca__"
               "run43829283730"),
    "041112": ("sweeps/2026-11-16/041112__category-news-poul-ca__"
               "run43801982888"),
}

CHECKS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, cond, detail=""):
    if cond:
        CHECKS["pass"] += 1
        print("  PASS %s" % name)
    else:
        CHECKS["fail"] += 1
        FAILURES.append(name)
        print("  FAIL %s %s" % (name, detail))


def run(cmd, env=None, cwd=None):
    merged = dict(os.environ)
    if env:
        merged.update(env)
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          env=merged, cwd=cwd, timeout=300)
    return proc


def git_head(path):
    return run(["git", "-C", path, "rev-parse", "HEAD"]).stdout.strip()


def compile_model(archive_root, key, out, repo_root):
    sweep = os.path.join(archive_root, SWEEPS[key])
    proc = run([sys.executable, os.path.join(repo_root, "scripts", "compile_model.py"),
                sweep, "--repo-root", repo_root,
                "--archive-sha", git_head(archive_root),
                "--compiler-sha", git_head(repo_root),
                "--out", out])
    assert proc.returncode == 0, proc.stderr
    return out


def render(repo_root, model, out_dir, extra=None, env=None):
    cmd = [sys.executable, os.path.join(repo_root, "scripts", "render.py"),
           model, "--profile", os.path.join(repo_root, "profiles", "POUL.CA.json"),
           "--out-dir", out_dir]
    if extra:
        cmd += extra
    return run(cmd, env=env)


def visible_text(html_text):
    txt = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
    txt = re.sub(r"<style.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<svg.*?</svg>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    return html_mod.unescape(txt)


def ar_visible_text(html_text):
    """Simulate the EN->AR toggle (ported from the render-69 build,
    its case 12): replace every data-i18n element's content with the
    AR string from the embedded window.I18N table — exactly what
    setLang('ar') does via textContent — then strip to visible
    text."""
    m = re.search(r"window\.I18N=(\{.*?\});", html_text, re.S)
    table = json.loads(m.group(1)) if m else {}
    ar = table.get("ar", {})

    def _sub(mm):
        tag, pre, key, post = mm.group(1), mm.group(2), mm.group(3), mm.group(4)
        if key in ar:
            return '<%s%sdata-i18n="%s"%s>%s</%s>' % (
                tag, pre, key, post, ar[key], tag)
        return mm.group(0)

    body = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
    out = re.sub(r"<(\w+)([^>]*?)data-i18n=\"([^\"]+)\"([^>]*)>(.*?)</\1>",
                 _sub, body, flags=re.S)
    return visible_text(out)


# Canonical legal text the renderer exempts from its prose-audit (§2i):
# the #77 disclaimers + framing line, and the model's own verbatim
# confidence_basis. The harness applies the same exemptions, and also
# discounts forbidden-word hits that occur only inside verbatim
# quoted tool reports (data, not narrative).
def plain_report(report):
    lines = [l for l in report.splitlines()
             if not re.match(r"^\s*\|[\s:\-|]+\|\s*$", l)]
    txt = "\n".join(lines)
    txt = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", txt)
    txt = re.sub(r"[#>*`\|]", " ", txt)
    return txt


def _quoted_text(sweep_dir):
    quoted = ""
    if sweep_dir:
        collected = os.path.join(sweep_dir, "collected")
        if os.path.isdir(collected):
            for tool in sorted(os.listdir(collected)):
                path = os.path.join(collected, tool, "report.md")
                if os.path.isfile(path):
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        quoted += " " + plain_report(fh.read())
    return re.sub(r"\s+", " ", quoted)


def _exempted(text, model=None):
    i18n = load_json(os.path.join(REPO, "scripts", "render_i18n.json"))
    for key in ("disclaimer.short", "disclaimer.long", "framing"):
        for lang in ("en", "ar"):
            text = text.replace(re.sub(r"\s+", " ", i18n[key][lang]), " ")
    if model is not None:
        cb = (model.get("weights") or {}).get("confidence_basis")
        if cb:
            text = text.replace(cb, " ")
    return text


def audit_forbidden(html_text, sweep_dir=None, model=None):
    """Forbidden-phrase hits in the renderer's auditable text: visible
    HTML, minus canonical legal strings, minus hits explained by
    verbatim quoted tool reports."""
    vis = _exempted(re.sub(r"\s+", " ", visible_text(html_text)), model)
    quoted = _quoted_text(sweep_dir)
    hits = []
    for phrase in FORBIDDEN:
        rx = re.compile(r"(?<![\w\-])" + re.escape(phrase) + r"(?![\w\-])",
                        re.IGNORECASE if phrase.isascii() else 0)
        if len(rx.findall(vis)) > len(rx.findall(quoted)):
            hits.append(phrase)
    return hits


def audit_forbidden_md(md_text, sweep_dir=None, model=None):
    """Same scan over the MD twin (quoted reports removed verbatim)."""
    txt = _exempted(re.sub(r"\s+", " ", md_text), model)
    if sweep_dir:
        collected = os.path.join(sweep_dir, "collected")
        if os.path.isdir(collected):
            for tool in sorted(os.listdir(collected)):
                path = os.path.join(collected, tool, "report.md")
                if os.path.isfile(path):
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        txt = txt.replace(re.sub(r"\s+", " ", fh.read()), " ")
    return forbidden_hits(txt)


def section(html_text, anchor):
    m = re.search(r'<section id="%s">(.*?)</section>' % re.escape(anchor),
                  html_text, re.S)
    return m.group(1) if m else ""


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=True)


def numbers_in(text):
    out = []
    for m in re.finditer(r"[-+]?\d[\d,]*\.?\d*\s*%", text):
        out.append(float(m.group(0).replace("%", "").replace(",", "").strip()))
    for m in re.finditer(r"(?<![\w.])[-+]?\d+\.\d+(?![\w.])", text):
        out.append(float(m.group(0)))
    return out


FORBIDDEN = ["guaranteed", "will rise", "will fall", "sure profit",
             "risk-free", "buy now", "should buy", "should sell",
             "best stock", "can't lose", "proven", "verified",
             "beats the market", "outperform", "reliable", "calibrated",
             "sec-approved", "registered", "endorsed", "opportunity",
             "set-up", "مضمون", "سيرتفع", "سينخفض", "ربح مؤكد",
             "بدون مخاطرة", "اشترِ الآن", "يجب أن تشتري", "يجب أن تبيع",
             "أفضل سهم", "مثبت", "موثّق", "يتفوق على السوق", "مربح",
             "موثوق", "معايَر"]


def forbidden_hits(text):
    hits = []
    for phrase in FORBIDDEN:
        rx = re.compile(r"(?<![\w\-])" + re.escape(phrase) + r"(?![\w\-])",
                        re.IGNORECASE if phrase.isascii() else 0)
        if rx.search(text):
            hits.append(phrase)
    return hits


# --- cases ---------------------------------------------------------------

def case1_golden(ctx):
    print("case 1: golden render (141124)")
    model = compile_model(ctx["archive"], "141124",
                          os.path.join(ctx["stage"], "model-141124.json"),
                          ctx["repo"])
    sweep = os.path.join(ctx["archive"], SWEEPS["141124"])
    out = os.path.join(ctx["stage"], "out-141124")
    proc = render(ctx["repo"], model, out, ["--sweep-dir", sweep,
                                            "--delta", ctx["delta"]])
    check("1 render exit 0", proc.returncode == 0, proc.stderr[:300])
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    m = open(os.path.join(out, "report.md"), encoding="utf-8").read()
    vis = visible_text(h)
    check("1 14 sections + header (§2d §0–§15)", len(re.findall(r'<section id="', h)) == 14,
          "sections found: %d" % len(re.findall(r'<section id="', h)))
    check("1 header ticker/date", "POUL.CA" in vis and "2026-11-16" in vis)
    check("1 base 8.02", "8.02" in vis)
    check("1 day +18.71%", "+18.71%" in vis)
    check("1 week +16.73%", "+16.73%" in vis)
    check("1 risk shock", "shock" in vis)
    check("1 weights pinned n=5", "0.993" in vis and "0.742" in vis and "1.024" in vis)
    check("1 bands 7.13/11.59", "7.13" in vis and "11.59" in vis)
    check("1 kronos rescale not recorded",
          "rescale state not recorded" in vis.lower())
    check("1 witnesses-stale flag", "witnesses-stale" in vis)
    check("1 price_series_last egx-data",
          "8.02" in section(h, "horizons") and "32041362" in section(h, "horizons"))
    check("1 stale sources marked",
          section(h, "horizons").count("(stale)") >= 3)
    check("1 news 22 + disclosures 11", "News: 22" in vis and "disclosures: 11" in vis)
    check("1 headline fundamentals max",
          "Families disagree: fundamentals +0.40 vs sentiment -0.10 (spread +0.50)" in vis)
    check("1 confidence_basis verbatim",
          "calibrated (ledger skill factors applied)" in vis)
    check("1 no hardcoded provisional line",
          "Confidence is provisional" not in vis)
    check("1 md bands", "Technical Support Level at 7.13" in m)
    # Ported from the render-69 build (its case 1): corporate
    # actions, the ledger pin and the sharia flags on the golden.
    vis_n = re.sub(r"\s+", " ", vis)
    check("1 corporate actions: 3 blocks, dividend ex-date 2026-11-16",
          vis_n.count("Corporate action:") == 3
          and "ex-date: 2026-11-16" in vis_n
          and "DPS: 1.8999999998" in vis_n)
    mdoc = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    counts = (mdoc.get("ledger_pin") or {}).get("counts") or {}
    check("1 ledger pin counts printed = model's counts",
          ("sweeps: %s" % counts.get("sweeps")) in vis_n
          and ("forecasts: %s" % counts.get("forecasts")) in vis_n
          and ("matured: %s" % counts.get("matured")) in vis_n
          and ("pending: %s" % counts.get("pending")) in vis_n
          and ("invalid: %s" % counts.get("invalid")) in vis_n,
          str(counts))
    sharia_flags = re.findall(
        r"sharia-(?:insufficient-data|table-missing)", vis_n)
    check("1 sharia flags: all 8 standards, none determinate",
          len(sharia_flags) == 8
          and all(s in vis_n for s in ("AAOIFI", "DJIM", "EGX33", "FTSE",
                                       "ISLAMICLY", "MSCI_M", "SP_SHARIAH")),
          "flags=%d" % len(sharia_flags))
    return model, out, h, m


def case2_per_tool(ctx, out):
    print("case 2: per-tool tolerance (141124)")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    vis = visible_text(h)
    check("2 20 tools with no report", vis.count("No report for this tool") == 20,
          "count=%d" % vis.count("No report for this tool"))
    check("2 4 reference workloads", vis.count("Reference workload") == 4)
    check("2 kronos last actual 10.15",
          "10.15" in section(h, "tools"))
    check("2 kronos forecast last close 9.6256",
          "9.6256" in section(h, "tools"))
    md = open(os.path.join(out, "report.md"), encoding="utf-8").read()
    run_table = md.split("### Tool run table", 1)[1].split("\n## ", 1)[0]
    check("2 run table lists 29 tools",
          len([l for l in run_table.splitlines() if l.startswith("- ")]) == 29)


def case3_determinism(ctx, model):
    print("case 3: determinism")
    sweep = os.path.join(ctx["archive"], SWEEPS["141124"])
    with open(model, "rb") as fh:
        model_sha_before = hashlib.sha256(fh.read()).hexdigest()
    outs = []
    for i, env in enumerate((None,
                             {"PYTHONHASHSEED": "7", "TZ": "Pacific/Kiritimati",
                              "LC_ALL": "C"})):
        out = os.path.join(ctx["stage"], "out-det%d" % i)
        proc = render(ctx["repo"], model, out, ["--sweep-dir", sweep,
                                                "--delta", ctx["delta"]],
                      env=env)
        check("3 render %d exit 0" % i, proc.returncode == 0, proc.stderr[:200])
        outs.append(out)
    # Ported from the render-69 build (its case 3): a render from a
    # foreign cwd must exit 0 and produce identical bytes. All
    # arguments are absolutized — the point is the renderer's own
    # cwd-independence, not the caller's relative paths.
    out2 = os.path.join(ctx["stage"], "out-det2")
    proc = run([sys.executable,
                os.path.join(ctx["repo"], "scripts", "render.py"),
                os.path.abspath(model),
                "--profile", os.path.join(ctx["repo"], "profiles",
                                          "POUL.CA.json"),
                "--out-dir", os.path.abspath(out2),
                "--sweep-dir", os.path.abspath(sweep),
                "--delta", os.path.abspath(ctx["delta"])],
               cwd="/")
    check("3 render from cwd=/ exit 0", proc.returncode == 0,
          proc.stderr[:200])
    outs.append(out2)
    outs.append(os.path.join(ctx["stage"], "out-141124"))
    blobs = []
    for out in outs:
        blobs.append((open(os.path.join(out, "report.html"), "rb").read(),
                      open(os.path.join(out, "report.md"), "rb").read()))
    check("3 byte-identical html", len({b[0] for b in blobs}) == 1)
    check("3 byte-identical md", len({b[1] for b in blobs}) == 1)
    # Ported: no render-time timestamp in the output, and the model
    # file itself is untouched by rendering.
    h_det = open(os.path.join(outs[0], "report.html"),
                 encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    check("3 no render-time timestamp in output",
          (today + "T") not in h_det
          and "rendered at" not in h_det.lower())
    with open(model, "rb") as fh:
        model_sha_after = hashlib.sha256(fh.read()).hexdigest()
    check("3 model file unchanged across renders",
          model_sha_after == model_sha_before)


def case4_legacy(ctx):
    print("case 4: legacy shape (141558)")
    model = compile_model(ctx["archive"], "141558",
                          os.path.join(ctx["stage"], "model-141558.json"),
                          ctx["repo"])
    sweep = os.path.join(ctx["archive"], SWEEPS["141558"])
    out = os.path.join(ctx["stage"], "out-141558")
    proc = render(ctx["repo"], model, out, ["--sweep-dir", sweep])
    check("4 render exit 0", proc.returncode == 0, proc.stderr[:300])
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    vis = visible_text(h)
    check("4 weights not recorded",
          "Weights not recorded for this sweep (pre-#93/#94 run)" in vis)
    check("4 base date not established", "base date not established" in vis)
    check("4 base source pandas-ta", "pandas-ta" in section(h, "horizons"))
    check("4 price-forecast -0.26", "-0.26" in vis)
    check("4 rescale not recorded",
          "rescale state not recorded" in vis.lower())


def case5_partial(ctx):
    print("case 5: partial + ensemble-absent")
    model = compile_model(ctx["archive"], "041112",
                          os.path.join(ctx["stage"], "model-041112.json"),
                          ctx["repo"])
    sweep = os.path.join(ctx["archive"], SWEEPS["041112"])
    out = os.path.join(ctx["stage"], "out-041112")
    proc = render(ctx["repo"], model, out, ["--sweep-dir", sweep])
    check("5a render exit 0", proc.returncode == 0, proc.stderr[:300])
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    vis = visible_text(h)
    check("5a partial banner", "Partial sweep" in vis)
    check("5a forecast placeholder x3",
          vis.count("Not available for a partial sweep") == 3,
          "count=%d" % vis.count("Not available for a partial sweep"))
    check("5a data sections render", "News + disclosures" in vis)
    # (b) synthetic ensemble-absent model.
    base = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    base["ensemble"] = None
    base["ensemble_absent"] = True
    base["partial"] = False
    base["horizons"] = {}
    base["price"] = None
    base["levels"] = None
    base["family_scores"] = {k: None for k in base["family_scores"]}
    base["recommendation"] = None
    mut = os.path.join(ctx["stage"], "model-noensemble.json")
    write_json(mut, base)
    out2 = os.path.join(ctx["stage"], "out-noensemble")
    proc = render(ctx["repo"], mut, out2,
                  ["--sweep-dir", os.path.join(ctx["archive"], SWEEPS["141124"])])
    check("5b render exit 0", proc.returncode == 0, proc.stderr[:300])
    if proc.returncode != 0:
        return
    h2 = open(os.path.join(out2, "report.html"), encoding="utf-8").read()
    check("5b no-ensemble placeholder",
          "Not available — no ensemble for this sweep" in visible_text(h2))
    # (c) synthetic horizons={} on the golden model.
    base = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    base["horizons"] = {}
    mut2 = os.path.join(ctx["stage"], "model-nohorizons.json")
    write_json(mut2, base)
    out3 = os.path.join(ctx["stage"], "out-nohorizons")
    proc = render(ctx["repo"], mut2, out3)
    check("5c render exit 0", proc.returncode == 0, proc.stderr[:300])
    h3 = open(os.path.join(out3, "report.html"), encoding="utf-8").read()
    check("5c no-horizon wording",
          "No horizon scored a family — no forecast" in visible_text(h3))


def case6_nosummary(ctx):
    print("case 6: no-summary + failed-tool (050559)")
    model = compile_model(ctx["archive"], "050559",
                          os.path.join(ctx["stage"], "model-050559.json"),
                          ctx["repo"])
    sweep = os.path.join(ctx["archive"], SWEEPS["050559"])
    out = os.path.join(ctx["stage"], "out-050559")
    proc = render(ctx["repo"], model, out, ["--sweep-dir", sweep])
    check("6 render exit 0", proc.returncode == 0, proc.stderr[:300])
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    vis = visible_text(h)
    check("6 kronos no-summary",
          "No summary — tool produced no summary" in vis)
    check("6 price-forecast no data",
          "price-forecast" in vis and "no data" in section(h, "families"))


def case7_staleness(ctx, out):
    print("case 7: staleness flags (141124)")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    vis = visible_text(h)
    check("7 witnesses-stale next to crosscheck",
          "Witnesses stale" in section(h, "horizons"))
    check("7 recommendation-stale flag", "recommendation-stale" in vis)
    check("7 stale rows flagged",
          section(h, "horizons").count("(stale)") >= 3)


def case8_worker_shape(ctx):
    print("case 8: worker-shape synthetic")
    base = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    base["provenance"]["merged_by"] = "worker"
    base["degraded"] = {"reason": "keyless", "absent_families": ["agent"],
                        "absent_tools": ["news-disclosure"]}
    for t in base["tools"]:
        t["run_url"] = None
        t["conclusion"] = None
        t["worker_run"] = "worker-run-123"
    mut = os.path.join(ctx["stage"], "model-worker.json")
    write_json(mut, base)
    out = os.path.join(ctx["stage"], "out-worker")
    proc = render(ctx["repo"], mut, out)
    check("8 render exit 0", proc.returncode == 0, proc.stderr[:300])
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    vis = visible_text(h)
    check("8 worker provenance", "merged by worker" in vis)
    check("8 keyless banner", "Degraded:" in vis and "keyless" in vis)
    check("8 no dead github links", "github.com" not in h)
    check("8 worker-run pointer", "worker run worker-run-123" in vis)
    check("8 bands still render", "7.13" in vis and "11.59" in vis)
    check("8 headline still renders", "Families disagree:" in vis)


def case9_d2_gate(ctx, out):
    print("case 9: D2 gate (legal case)")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    m = open(os.path.join(out, "report.md"), encoding="utf-8").read()
    vis = visible_text(h)
    vis_n = re.sub(r"\s+", " ", vis)
    sweep = os.path.join(ctx["archive"], SWEEPS["141124"])
    model = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    check("9 bands present",
          re.search(r"Technical Support Level at\s+7\.13", vis_n) is not None
          and re.search(r"Technical Resistance Level at\s+11\.59", vis_n) is not None)
    check("9 no HOLD line", "HOLD" not in vis and "HOLD" not in m)
    check("9 no buy/sell lines",
          "buy at/below" not in vis.lower() and "sell/trim" not in vis.lower()
          and "buy ≤" not in vis and "sell ≥" not in vis)
    check("9 forbidden list zero hits in visible html",
          audit_forbidden(h, sweep, model) == [],
          str(audit_forbidden(h, sweep, model)))
    check("9 forbidden list zero hits in md",
          audit_forbidden_md(m, sweep, model) == [],
          str(audit_forbidden_md(m, sweep, model)))
    check("9 short disclaimer header+footer",
          vis.count("Borsagator is not an investment adviser") >= 2)
    check("9 long disclaimer in footer",
          "Borsagator sells a computed report" in vis)
    check("9 AR short disclaimer present",
          "بورساجاتور ليست مستشارًا استثماريًا" in h)
    # Tampered slot must fail the render with no files written.
    narr = {"slots": [{"id": "summary", "max_chars": 2000,
                       "text": "Day move +18.71% — buy now, guaranteed gains."}]}
    narr_path = os.path.join(ctx["stage"], "narr-bad.json")
    write_json(narr_path, narr)
    out_bad = os.path.join(ctx["stage"], "out-badslot")
    proc = render(ctx["repo"], os.path.join(ctx["stage"], "model-141124.json"),
                  out_bad, ["--narrative", narr_path])
    check("9 tampered slot refused", proc.returncode != 0, proc.stderr[:200])
    check("9 tampered slot wrote no files",
          not os.path.exists(os.path.join(out_bad, "report.html")))


def case10_prose_audit(ctx):
    print("case 10: prose-audit cases")
    model = os.path.join(ctx["stage"], "model-141124.json")
    cases = [
        ("10a +18.71% passes", "Day move +18.71%, base 8.02.", True),
        ("10a +19% fails", "Day move +19%, base 8.02.", False),
        ("10b 8.02 passes", "Base 8.02.", True),
        ("10b 8.20 fails", "Base 8.20.", False),
        ("10c buy-decision passes",
         "Figures from the 10-Nov-2026 buy-decision research.", True),
        ("10c buy now fails", "You should buy now.", False),
        # Ported from the render-69 build (its case 10i, T4): a
        # value copied from the WRONG field passes — the audit is
        # value-level only. Recorded limitation, asserted as-is.
        ("10d wrong-field copy passes (value-level audit only)",
         "Day move +16.73%.", True),
    ]
    for name, text, ok in cases:
        narr_path = os.path.join(ctx["stage"], "narr-10.json")
        write_json(narr_path, {"slots": [{"id": "summary", "max_chars": 2000,
                                          "text": text}]})
        out = os.path.join(ctx["stage"], "out-10")
        shutil.rmtree(out, ignore_errors=True)
        proc = render(ctx["repo"], model, out, ["--narrative", narr_path])
        if ok:
            check(name, proc.returncode == 0, proc.stderr[:200])
        else:
            check(name, proc.returncode != 0
                  and not os.path.exists(os.path.join(out, "report.html")),
                  proc.stderr[:200])


def case11_schema_negative(ctx):
    print("case 11: schema + envelope negatives")
    base = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    base["schema"] = "borsagator-report-model/99"
    mut = os.path.join(ctx["stage"], "model-v99.json")
    write_json(mut, base)
    out = os.path.join(ctx["stage"], "out-v99")
    proc = render(ctx["repo"], mut, out)
    check("11 refused", proc.returncode != 0, proc.stderr[:200])
    check("11 names expected vs found",
          "model_schema_unsupported" in proc.stderr
          and "borsagator-report-model/99" in proc.stderr)
    check("11 wrote no files",
          not os.path.exists(os.path.join(out, "report.html")))
    # Ported from the render-69 build (its case 11, T5): missing
    # envelope fields and out-of-vocabulary values refuse the same
    # way (non-zero exit, no files written).
    for label, mutate in (
            ("finished", lambda b: b.pop("finished")),
            ("ensemble_shape", lambda b: b.pop("ensemble_shape")),
            ("market", lambda b: b.update(market="MARS")),
            ("merged_by", lambda b: b["provenance"].update(
                merged_by="someone-else"))):
        neg = load_json(os.path.join(ctx["stage"], "model-141124.json"))
        mutate(neg)
        neg_path = os.path.join(ctx["stage"], "model-neg-%s.json" % label)
        write_json(neg_path, neg)
        out_neg = os.path.join(ctx["stage"], "out-neg-%s" % label)
        proc = render(ctx["repo"], neg_path, out_neg)
        check("11 missing/bad %s refused" % label,
              proc.returncode != 0
              and not os.path.exists(os.path.join(out_neg, "report.html")),
              proc.stderr[:200])


def case12_offline_bilingual(ctx, out):
    print("case 12: offline / self-contained + bilingual")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    check("12 no <link> to a host",
          not re.search(r'<link[^>]+href="https?://', h))
    check("12 no <script src>", "<script src" not in h)
    check("12 no <img", "<img" not in h)
    check("12 no @import", "@import" not in h)
    check("12 no url(http", "url(http" not in h)
    check("12 no favicon fetch", "favicon.ico" not in h)
    check("12 plain links allowed", "<a href=" in h)
    m = re.search(r"window\.I18N=(\{.*?\});", h, re.S)
    check("12 i18n table embedded", m is not None)
    table = json.loads(m.group(1)) if m else {}
    keys = set(re.findall(r'data-i18n="([^"]+)"', h))
    missing = [k for k in keys
               if k not in table.get("en", {}) or k not in table.get("ar", {})]
    check("12 every data-i18n key has EN+AR", missing == [], str(missing))
    check("12 AR short disclaimer verbatim",
          "بورساجاتور ليست مستشارًا استثماريًا" in table.get("ar", {}).get(
              "disclaimer.short", ""))
    # Ported from the render-69 build (its case 12): the AR long
    # disclaimer verbatim in the table, and EN/AR numeric parity —
    # the AR view (setLang simulation) must carry the same numbers
    # as the EN view, same count.
    check("12 AR long disclaimer verbatim",
          table.get("ar", {}).get("disclaimer.long", "").startswith(
              "بورساجاتور تبيع تقريرًا محسوبًا"))
    en_nums = sorted(numbers_in(visible_text(h)))
    ar_nums = sorted(numbers_in(ar_visible_text(h)))
    check("12 EN/AR numeric parity (same numbers, same count)",
          len(en_nums) == len(ar_nums)
          and all(abs(a - b) <= 0.005
                  for a, b in zip(en_nums, ar_nums)),
          "en=%d ar=%d" % (len(en_nums), len(ar_nums)))
    check("12 toggle sets lang/dir",
          'document.documentElement.lang' in h and "dir=" in h)
    # Tampered i18n table (one AR string deleted) must fail the render.
    i18n = load_json(os.path.join(ctx["repo"], "scripts", "render_i18n.json"))
    del i18n["bands.support"]["ar"]
    bad_i18n = os.path.join(ctx["stage"], "i18n-bad.json")
    write_json(bad_i18n, i18n)
    out_bad = os.path.join(ctx["stage"], "out-badi18n")
    proc = run([sys.executable,
                os.path.join(ctx["repo"], "scripts", "render.py"),
                os.path.join(ctx["stage"], "model-141124.json"),
                "--profile", os.path.join(ctx["repo"], "profiles", "POUL.CA.json"),
                "--i18n", bad_i18n, "--out-dir", out_bad])
    check("12 tampered i18n refused", proc.returncode != 0, proc.stderr[:200])


def case13_no_secret(ctx, out):
    print("case 13: no-secret scan")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    m = open(os.path.join(out, "report.md"), encoding="utf-8").read()
    for name in ("COHERE_API_KEY", "SIMFIN_API_KEY", "GH_TOKEN",
                 "BORSAGATOR_APP_PRIVATE_KEY", "GATOR_BUS_URL"):
        check("13 no %s" % name, name not in h and name not in m)
    hexes = set(re.findall(r"\b[0-9a-f]{40}\b", h + m))
    model_shas = set(re.findall(r"\b[0-9a-f]{40}\b",
                                json.dumps(load_json(
                                    os.path.join(ctx["stage"],
                                                 "model-141124.json")))))
    check("13 no unlabelled 40-hex", hexes <= model_shas,
          "unlabelled: %s" % sorted(hexes - model_shas)[:3])
    # Force a fake key into a tool summary: the display must drop it.
    base = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    base["tools"][0]["summary"]["metrics"]["FAKE_API_KEY"] = "sk-test-1234567890abcdef"
    mut = os.path.join(ctx["stage"], "model-secret.json")
    write_json(mut, base)
    out2 = os.path.join(ctx["stage"], "out-secret")
    proc = render(ctx["repo"], mut, out2)
    check("13 injected key renders", proc.returncode == 0, proc.stderr[:200])
    h2 = open(os.path.join(out2, "report.html"), encoding="utf-8").read()
    m2 = open(os.path.join(out2, "report.md"), encoding="utf-8").read()
    check("13 key name dropped from display",
          "FAKE_API_KEY" not in visible_text(h2) and "FAKE_API_KEY" not in m2)
    check("13 key value dropped from display",
          "sk-test-1234567890abcdef" not in visible_text(h2)
          and "sk-test-1234567890abcdef" not in m2)
    check("13 drop logged", "secret_fields_dropped" in proc.stderr)


def case14_data_island(ctx, out):
    print("case 14: data island")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    island = re.search(
        r'<script type="application/json" id="report-model">(.*?)</script>',
        h, re.S).group(1)
    model = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    check("14 island parses to the identical model",
          json.loads(island) == model)
    base = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    base["news"]["news_items"][0]["title"] = "</script><script>alert(1)</script>"
    mut = os.path.join(ctx["stage"], "model-script.json")
    write_json(mut, base)
    out2 = os.path.join(ctx["stage"], "out-script")
    proc = render(ctx["repo"], mut, out2)
    check("14 hostile title renders", proc.returncode == 0, proc.stderr[:200])
    h2 = open(os.path.join(out2, "report.html"), encoding="utf-8").read()
    island2 = re.search(
        r'<script type="application/json" id="report-model">(.*?)</script>',
        h2, re.S).group(1)
    check("14 island still parses to the mutated model",
          json.loads(island2) == base)
    check("14 title escaped in visible html",
          "&lt;/script&gt;" in h2
          and "<script>alert(1)</script>" not in h2)
    # Issue #258: the old island escape matched only the exact
    # lowercase "</script>". Mixed-case and whitespace closers must
    # be neutralised too — the fix escapes EVERY "<", so no literal
    # "<" can survive in the island at all.
    for variant in ("</ScRiPt><script>alert(1)</script>",
                    "</script ><script>alert(1)</script>",
                    "</ script><script>alert(1)</script>",
                    "</SCRIPT><script>alert(1)</script>"):
        base_v = load_json(os.path.join(ctx["stage"],
                                        "model-141124.json"))
        base_v["news"]["news_items"][0]["title"] = variant
        mut_v = os.path.join(ctx["stage"], "model-script-var.json")
        write_json(mut_v, base_v)
        out_v = os.path.join(ctx["stage"], "out-script-var")
        shutil.rmtree(out_v, ignore_errors=True)
        proc_v = render(ctx["repo"], mut_v, out_v)
        check("14 variant %r renders" % variant[:12],
              proc_v.returncode == 0, proc_v.stderr[:200])
        if proc_v.returncode != 0:
            continue
        h_v = open(os.path.join(out_v, "report.html"),
                   encoding="utf-8").read()
        island_v = re.search(
            r'<script type="application/json" id="report-model">(.*?)</script>',
            h_v, re.S).group(1)
        check("14 variant %r island parses to the mutated model"
              % variant[:12],
              json.loads(island_v) == base_v)
        check("14 variant %r island holds no literal '<'"
              % variant[:12],
              "<" not in island_v)
        check("14 variant %r cannot terminate the island"
              % variant[:12],
              h_v.count("<script") == 2)  # island + toggle only


def case15_private_path(ctx):
    print("case 15: private-path control")
    private = os.path.join(ctx["stage"], "private")
    proc = render(ctx["repo"], os.path.join(ctx["stage"], "model-141124.json"),
                  private)
    check("15 render exit 0", proc.returncode == 0, proc.stderr[:200])
    check("15 outputs in the private dir",
          os.path.isfile(os.path.join(private, "report.html"))
          and os.path.isfile(os.path.join(private, "report.md")))
    repo = ctx["repo"]
    stray = []
    for root, _dirs, files in os.walk(repo):
        if "report.html" in files or "report.md" in files:
            if root.endswith("out-141124") or "hidden_files" in root:
                continue
            stray.append(root)
    check("15 no file on the public path", stray == [], str(stray[:3]))
    h = open(os.path.join(private, "report.html"), encoding="utf-8").read()
    check("15 watermark unassigned", "unassigned" in h)
    check("15 no user id / requester",
          "user_id" not in h and "requester" not in h)
    # Ported from the render-69 build (its case 15): no product
    # price in the report — no $ amounts in either twin.
    m_priv = open(os.path.join(private, "report.md"),
                  encoding="utf-8").read()
    check("15 no product price ($ amounts) in outputs",
          "$" not in h and "$" not in m_priv)


def case16_delta(ctx, out):
    print("case 16: delta section")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    dsec = section(h, "delta")
    check("16a mechanical -23.69% vs residual +3.89%",
          "-23.69%" in dsec and "+3.89%" in dsec)
    check("16a delta after bands, before tools",
          h.index('id="bands"') < h.index('id="delta"') < h.index('id="tools"'))
    check("16a no imperative wording in delta",
          forbidden_hits(visible_text(dsec)) == [],
          str(forbidden_hits(visible_text(dsec))))
    # (b) Without a delta file: first-sweep note, exit 0.
    out2 = os.path.join(ctx["stage"], "out-nodelta")
    proc = render(ctx["repo"], os.path.join(ctx["stage"], "model-141124.json"),
                  out2)
    check("16b render exit 0", proc.returncode == 0, proc.stderr[:200])
    h2 = open(os.path.join(out2, "report.html"), encoding="utf-8").read()
    check("16b first-sweep note",
          "nothing to compare against yet" in section(h2, "delta"))
    # (c) pair_invalid delta: the reason renders, no diff shown.
    bad = {"ticker": "POUL.CA", "pair_invalid": "no pair: shapes differ"}
    bad_path = os.path.join(ctx["stage"], "delta-invalid.json")
    write_json(bad_path, bad)
    out3 = os.path.join(ctx["stage"], "out-baddelta")
    proc = render(ctx["repo"], os.path.join(ctx["stage"], "model-141124.json"),
                  out3, ["--delta", bad_path])
    check("16c render exit 0", proc.returncode == 0, proc.stderr[:200])
    h3 = open(os.path.join(out3, "report.html"), encoding="utf-8").read()
    check("16c invalid reason renders",
          "no pair: shapes differ" in section(h3, "delta"))


def case17_twin_parity(ctx, out):
    print("case 17: twin parity")
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    m = open(os.path.join(out, "report.md"), encoding="utf-8").read()
    vis = visible_text(h)
    md_nums = numbers_in(m)
    missing = [n for n in md_nums
               if not any(abs(n - x) <= 0.011 for x in numbers_in(vis))]
    check("17 every MD number appears in the HTML", missing == [],
          "missing: %s" % missing[:5])
    check("17 same bands in MD", "Technical Support Level at 7.13" in m)
    check("17 same footer in MD",
          "Deterministic glue over the ensemble" in m)
    check("17 MD has no imperative line",
          audit_forbidden_md(m, os.path.join(ctx["archive"], SWEEPS["141124"]),
                             load_json(os.path.join(ctx["stage"],
                                                  "model-141124.json"))) == [],
          str(audit_forbidden_md(m, os.path.join(ctx["archive"], SWEEPS["141124"]),
                                 load_json(os.path.join(ctx["stage"],
                                                      "model-141124.json")))))


def case18_escaping(ctx):
    print("case 18: HTML-escaping negative")
    mini = os.path.join(ctx["stage"], "mini-sweep")
    shutil.rmtree(mini, ignore_errors=True)
    # The renderer refuses when a present report is missing from
    # --sweep-dir (R-F6), so the mini sweep carries the real reports
    # for all 9 present tools and only kronos's is injected.
    real = os.path.join(ctx["archive"], SWEEPS["141124"], "collected")
    for tool in sorted(os.listdir(real)):
        src = os.path.join(real, tool, "report.md")
        if os.path.isfile(src):
            dest_dir = os.path.join(mini, "collected", tool)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(src, os.path.join(dest_dir, "report.md"))
    with open(os.path.join(mini, "collected", "kronos", "report.md"),
              "w", encoding="utf-8") as fh:
        fh.write("<script>alert(1)</script>\n\n# Kronos\n\nForecast ok.\n")
    base = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    base["news"]["news_items"][0]["title"] = "<b>bold</b> headline"
    mut = os.path.join(ctx["stage"], "model-esc.json")
    write_json(mut, base)
    out = os.path.join(ctx["stage"], "out-esc")
    proc = render(ctx["repo"], mut, out, ["--sweep-dir", mini])
    check("18 render exit 0", proc.returncode == 0, proc.stderr[:200])
    if proc.returncode != 0:
        return
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    check("18 script renders as text", "&lt;script&gt;alert(1)" in h)
    check("18 no executable script from the report",
          h.count("<script") == 2)  # island + toggle only
    check("18 bold renders as text", "&lt;b&gt;bold&lt;/b&gt;" in h)


def case20_price_tail(ctx):
    """Issue #258: read_price_tail rejects NaN/Infinity closes and
    out-of-order dates; a forecast-only render labels itself as
    such instead of borrowing the price-chart flag."""
    print("case 20: price-tail contract + forecast-only chart")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "render_under_test",
        os.path.join(ctx["repo"], "scripts", "render.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tail_dir = os.path.join(ctx["stage"], "tail-sweep")
    shutil.rmtree(tail_dir, ignore_errors=True)
    tool_dir = os.path.join(tail_dir, "collected", "yahooquery")
    os.makedirs(tool_dir, exist_ok=True)
    with open(os.path.join(tool_dir, "prices.csv"), "w",
              encoding="utf-8") as fh:
        fh.write("date,close\n"
                 "2026-11-10,9.50\n"
                 "2026-11-11,NaN\n"
                 "2026-11-12,Infinity\n"
                 "2026-11-13,9.70\n"
                 "2026-11-14,9.80\n")
    with open(os.path.join(tool_dir, "bad-order.csv"), "w",
              encoding="utf-8") as fh:
        fh.write("date,close\n"
                 "2026-11-12,9.60\n"
                 "2026-11-11,9.50\n")
    tails = module.read_price_tail(tail_dir)
    check("20 NaN/Infinity closes skipped, valid rows kept",
          tails.get("yahooquery/prices.csv")
          == [("2026-11-10", 9.5), ("2026-11-13", 9.7),
              ("2026-11-14", 9.8)])
    check("20 out-of-order series dropped whole",
          "yahooquery/bad-order.csv" not in tails)
    # Forecast-only end-to-end: mini sweep with real per-tool
    # reports + a real Kronos forecast, but no price CSVs at all.
    mini = os.path.join(ctx["stage"], "mini-forecast-only")
    shutil.rmtree(mini, ignore_errors=True)
    real = os.path.join(ctx["archive"], SWEEPS["141124"], "collected")
    for tool in sorted(os.listdir(real)):
        src = os.path.join(real, tool, "report.md")
        if os.path.isfile(src):
            dest_dir = os.path.join(mini, "collected", tool)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(src, os.path.join(dest_dir, "report.md"))
    shutil.copyfile(
        os.path.join(real, "kronos", "forecast.csv"),
        os.path.join(mini, "collected", "kronos", "forecast.csv"))
    # The forecast file itself is a CSV with date/close columns,
    # so the no-price-CSV check must use the model's own
    # price_series_last sources (as the renderer does) — the
    # forecast file is not a price source.
    model20 = load_json(os.path.join(ctx["stage"],
                                     "model-141124.json"))
    psl20 = {r.get("source") for r in
             model20.get("price_series_last") or []}
    check("20 forecast-only sweep carries no price CSV",
          module.read_price_tail(mini, psl20) == {})
    out = os.path.join(ctx["stage"], "out-forecast-only")
    proc = render(ctx["repo"],
                  os.path.join(ctx["stage"], "model-141124.json"),
                  out, ["--sweep-dir", mini])
    check("20 forecast-only render exit 0", proc.returncode == 0,
          proc.stderr[:200])
    if proc.returncode != 0:
        return
    h = open(os.path.join(out, "report.html"), encoding="utf-8").read()
    m = open(os.path.join(out, "report.md"), encoding="utf-8").read()
    check("20 forecast-only SVG is labelled forecast-only",
          'aria-label="Price chart (forecast only)"' in h)
    check("20 forecast-only SVG is not labelled a price chart",
          'aria-label="Price chart"' not in h)
    check("20 forecast-only MD caption says so",
          "forecast cone only" in m
          and "price tail" not in m)


def _sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _reorder_keys(obj):
    """Recursively reverse JSON object key order (render-69 T2)."""
    if isinstance(obj, dict):
        return {k: _reorder_keys(obj[k]) for k in reversed(list(obj))}
    if isinstance(obj, list):
        return [_reorder_keys(x) for x in obj]
    return obj


def case21_key_reorder(ctx):
    """Ported from the render-69 build (its case 20, T2): the
    rendered view is invariant under JSON object key order; array
    order is meaningful and must change the output."""
    print("case 21: key-reorder invariance (ported, render-69 T2)")
    sweep = os.path.join(ctx["archive"], SWEEPS["141124"])
    golden_out = os.path.join(ctx["stage"], "out-141124")
    golden_html_sha = _sha256_file(os.path.join(golden_out,
                                                "report.html"))

    def _variant(doc, label):
        path = os.path.join(ctx["stage"], "model-%s.json" % label)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1,
                      sort_keys=False)
        out = os.path.join(ctx["stage"], "out-%s" % label)
        proc = render(ctx["repo"], path, out,
                      ["--sweep-dir", sweep, "--delta", ctx["delta"]])
        return proc, out

    def _strip_scripts(text):
        return re.sub(r"<script.*?</script>", " ", text, flags=re.S)

    base_model = load_json(os.path.join(ctx["stage"],
                                        "model-141124.json"))
    proc, out = _variant(_reorder_keys(base_model), "reordered")
    check("21 key reorder renders", proc.returncode == 0,
          proc.stderr[:200])
    if proc.returncode == 0:
        h_new = open(os.path.join(out, "report.html"),
                     encoding="utf-8").read()
        h_base = open(os.path.join(golden_out, "report.html"),
                      encoding="utf-8").read()
        check("21 key reorder -> identical rendered view "
              "(data island excluded: it is the input file verbatim)",
              _strip_scripts(h_new) == _strip_scripts(h_base))
        m_new = open(os.path.join(out, "report.md"),
                     encoding="utf-8").read()
        m_base = open(os.path.join(golden_out, "report.md"),
                      encoding="utf-8").read()
        check("21 key reorder -> identical MD twin", m_new == m_base)
    doc = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    doc["tools"] = list(reversed(doc["tools"]))
    proc, out = _variant(doc, "tools-reversed")
    check("21 tools[] order reversed -> output DIFFERS "
          "(array order is meaningful)",
          proc.returncode == 0
          and _sha256_file(os.path.join(out, "report.html"))
          != golden_html_sha)
    doc = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    series = doc.get("price_series_last") or []
    if len(series) >= 2:
        series[0], series[1] = series[1], series[0]
    proc, out = _variant(doc, "series-swapped")
    check("21 price_series_last entries swapped -> output DIFFERS",
          proc.returncode == 0
          and _sha256_file(os.path.join(out, "report.html"))
          != golden_html_sha)


def _mutant_render(ctx, mut, label):
    """A copy of render.py + its i18n table with one fault injected
    (render-69 T8). Returns the mutant script path."""
    mdir = os.path.join(ctx["stage"], "mutant-%s" % label)
    os.makedirs(mdir, exist_ok=True)
    src = open(os.path.join(ctx["repo"], "scripts", "render.py"),
               encoding="utf-8").read()
    mutated = mut(src)
    assert mutated != src, "mutant %s: anchor not found" % label
    script = os.path.join(mdir, "render.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(mutated)
    shutil.copy(os.path.join(ctx["repo"], "scripts",
                             "render_i18n.json"),
                os.path.join(mdir, "render_i18n.json"))
    return script


def _run_script(script, ctx, model, out, extra=None):
    cmd = [sys.executable, script, model,
           "--profile", os.path.join(ctx["repo"], "profiles",
                                     "POUL.CA.json"),
           "--out-dir", out]
    if extra:
        cmd += extra
    return run(cmd)


def case22_mutations(ctx):
    """Ported from the render-69 build (its case 21, T8): mutation
    discrimination — each injected fault must fail exactly the
    check the design predicts. (render-69's final-gate mutant is
    NOT ported: main's renderer exempts verbatim quoted tool
    reports from the prose audit by design (§2i), so there is no
    second gate to gut.)"""
    print("case 22: mutation discrimination (ported, render-69 T8)")
    model = os.path.join(ctx["stage"], "model-141124.json")
    sweep = os.path.join(ctx["archive"], SWEEPS["141124"])

    # (a) Gut the prose audit: the 'buy now' slot now renders.
    # Control: the real renderer refuses the same input.
    def gut_audit(src):
        anchor = ("def audit_narrative(text, allowed_numbers, "
                  "allowed_dates, label):")
        assert anchor in src, "audit_narrative def not found"
        return src.replace(
            anchor,
            anchor + "\n    return  # MUTANT: audit gutted\n"
            "def _audit_narrative_dead(text, allowed_numbers, "
            "allowed_dates, label):", 1)

    script = _mutant_render(ctx, gut_audit, "gut-audit")
    narr_path = os.path.join(ctx["stage"], "narr-22.json")
    write_json(narr_path, {"slots": [{"id": "summary", "max_chars": 2000,
                                      "text": "Day move +18.71% — buy "
                                              "now, guaranteed gains."}]})
    out_m = os.path.join(ctx["stage"], "out-mutant-audit")
    proc = _run_script(script, ctx, model, out_m,
                       ["--narrative", narr_path])
    check("22 mutant (audit gutted): 'buy now' slot now RENDERS",
          proc.returncode == 0
          and os.path.isfile(os.path.join(out_m, "report.html")),
          proc.stderr[:200])
    out_c = os.path.join(ctx["stage"], "out-mutant-control")
    proc = _run_script(os.path.join(ctx["repo"], "scripts", "render.py"),
                       ctx, model, out_c, ["--narrative", narr_path])
    check("22 control: real renderer REFUSES the same slot",
          proc.returncode != 0
          and not os.path.exists(os.path.join(out_c, "report.html")))

    # (b) Inject a wall clock into the HTML tail: two renders of
    # the same model must differ — the determinism check fails as
    # predicted.
    def inject_clock(src):
        anchor = '    parts.append("</body></html>")'
        assert src.count(anchor) == 1, "render_html tail anchor not unique"
        return src.replace(
            anchor,
            '    parts.append("<!-- rendered at " + '
            '__import__("datetime").datetime.now('
            '__import__("datetime").timezone.utc).isoformat()'
            ' + " -->")\n' + anchor, 1)

    script = _mutant_render(ctx, inject_clock, "clock")
    clock_html = []
    for tag in ("a", "b"):
        out_k = os.path.join(ctx["stage"], "out-mutant-clock-%s" % tag)
        proc = _run_script(script, ctx, model, out_k,
                           ["--sweep-dir", sweep,
                            "--delta", ctx["delta"]])
        check("22 clock mutant render %s exit 0" % tag,
              proc.returncode == 0, proc.stderr[:200])
        clock_html.append(
            open(os.path.join(out_k, "report.html"),
                 encoding="utf-8").read()
            if proc.returncode == 0 else "")
    check("22 mutant (clock injected): two renders DIFFER",
          clock_html[0] != "" and clock_html[0] != clock_html[1])


def case19_pristine(ctx):
    print("case 19: pristine control (aggregate)")
    check("19 render.py exists on the fixed tree",
          os.path.isfile(os.path.join(ctx["repo"], "scripts", "render.py")))
    check("19 render_i18n.json exists",
          os.path.isfile(os.path.join(ctx["repo"], "scripts", "render_i18n.json")))


def naive_control(ctx):
    """--pristine: a hand-rolled HTML dump (no escaping, no audit, no
    i18n, no island, and it reproduces the stale HOLD line the old
    recommend.py printed) must FAIL the discriminating cases."""
    print("pristine control: naive HTML dump of the 141124 model")
    model = load_json(os.path.join(ctx["stage"], "model-141124.json"))
    slot = "Day move +19% — buy now, guaranteed gains."
    title = "</script><script>alert(1)</script>"
    naive = ("<html><body><h1>%s</h1>"
             "<p>HOLD · buy at/below 9.5 · sell/trim at/above 10.59</p>"
             "<p>base %s</p><p>%s</p><p>%s</p><p>%s</p><p>%s</p></body></html>" % (
                 model["ticker"], model["price"]["base_price"], slot, title,
                 json.dumps(model["family_scores"]),
                 "</ScRiPt><script>alert(1)</script>"))
    fails = []
    if "report-model" not in naive:
        fails.append("14 (no data island)")
    if "data-i18n" not in naive:
        fails.append("12 (no i18n table)")
    if "<script>alert(1)</script>" in naive:
        fails.append("18 (no escaping)")
    if "</ScRiPt>" in naive:
        fails.append("14-variant (mixed-case closer survives)")
    if forbidden_hits(naive):
        fails.append("9 (forbidden wording: %s)" % forbidden_hits(naive))
    if "+19%" in naive:
        fails.append("10 (unaudited number)")
    for f in fails:
        print("  naive fails %s" % f)
    print("pristine control: %d discriminating failures (need >= 4)" % len(fails))
    return len(fails) >= 4


def build_delta(ctx):
    """Real Pair A delta (085806 -> 141124) via scripts/delta.py --model."""
    prev = os.path.join(ctx["archive"], SWEEPS["085806"])
    cur = os.path.join(ctx["archive"], SWEEPS["141124"])
    out = os.path.join(ctx["stage"], "delta-085806-141124.json")
    proc = run([sys.executable, os.path.join(ctx["repo"], "scripts", "delta.py"),
                prev, cur, "--model", "--out", out])
    assert proc.returncode == 0, proc.stderr
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Proof harness for issue #69.")
    ap.add_argument("--archive-root", default=ARCHIVE_DEFAULT)
    ap.add_argument("--stage", default=STAGE_DEFAULT)
    ap.add_argument("--keep-stage", action="store_true")
    ap.add_argument("--pristine", action="store_true")
    args = ap.parse_args(argv)

    ctx = {"repo": REPO, "archive": args.archive_root, "stage": args.stage}
    if not os.path.isfile(os.path.join(REPO, "scripts", "render.py")):
        print("PRISTINE: no scripts/render.py on this tree — harness exits 1")
        return 1
    os.makedirs(args.stage, exist_ok=True)
    ctx["delta"] = build_delta(ctx)

    if args.pristine:
        ok = naive_control(ctx)
        print("pristine control: %s" % ("DISCRIMINATES" if ok else "VOID"))
        return 0 if ok else 1

    model, out, _h, _m = case1_golden(ctx)
    case2_per_tool(ctx, out)
    case3_determinism(ctx, os.path.join(ctx["stage"], "model-141124.json"))
    case4_legacy(ctx)
    case5_partial(ctx)
    case6_nosummary(ctx)
    case7_staleness(ctx, out)
    case8_worker_shape(ctx)
    case9_d2_gate(ctx, out)
    case10_prose_audit(ctx)
    case11_schema_negative(ctx)
    case12_offline_bilingual(ctx, out)
    case13_no_secret(ctx, out)
    case14_data_island(ctx, out)
    case15_private_path(ctx)
    case16_delta(ctx, out)
    case17_twin_parity(ctx, out)
    case18_escaping(ctx)
    case19_pristine(ctx)
    case20_price_tail(ctx)
    case21_key_reorder(ctx)
    case22_mutations(ctx)

    print("\nharness_issue69: %d pass, %d fail" % (CHECKS["pass"], CHECKS["fail"]))
    if FAILURES:
        print("failures: %s" % ", ".join(FAILURES))
    if not args.keep_stage:
        shutil.rmtree(args.stage, ignore_errors=True)
    return 0 if CHECKS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
