#!/usr/bin/env python3
"""Deterministic report renderer (issue #69).

Renders one Report Model (``borsagator-report-model/2``, issue #68;
v1 models still render — see ``scripts/report_model.py``) into one
self-contained HTML file with the model embedded as a JSON data
island, plus an MD twin. Stdlib only, no network, no LLM.

Usage:
    python3 scripts/render.py <report-model.json>
        [--profile <profiles/TICKER.json>]
        [--delta <delta.json>] [--narrative <narrative.json>]
        [--sweep-dir <archived sweep dir>] [--out-dir <dir>]
        [--i18n <render_i18n.json>]

Exit 0 on a rendered report (including degraded models). Non-zero
only on the fail-loudly cases (scoping §6): unknown schema,
envelope contradiction, missing required envelope field, profile
mismatch, prose-audit failure, narrative/report mismatch on the
fallback path, i18n parity failure, non-finite number. A derived
number (the disagreement spread) passes the prose-audit only as an
explicitly traced claim — approved formula + source-field bindings,
verified by recomputation (§2i, issue #261).
"""
import argparse
import csv
import html
import json
import math
import os
import re
import sys

try:
    import report_model
except ImportError:  # imported from a checkout without scripts/ on path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import report_model

# The Report Model contract (versions, field sets, no-bump
# schema-diff check) lives in scripts/report_model.py — the single
# pinned authority. This module never re-states a version marker.
SCHEMA = report_model.SCHEMA
MODEL_VERSION = report_model.MODEL_VERSION
METRICS_SCHEMA = "untyped-flat"

# --- #77 framing v2, §6 forbidden claims (renderer prose-audit) --------
FORBIDDEN_EN = [
    "guaranteed", "will rise", "will fall", "sure profit", "risk-free",
    "buy now", "should buy", "should sell", "best stock", "can't lose",
    "proven", "verified", "beats the market", "outperform", "reliable",
    "calibrated", "sec-approved", "registered", "endorsed", "opportunity",
    "set-up", "consider buying", "consider selling",
]
FORBIDDEN_AR = [
    "مضمون", "سيرتفع", "سينخفض", "ربح مؤكد", "بدون مخاطرة",
    "اشترِ الآن", "يجب أن تشتري", "يجب أن تبيع", "أفضل سهم",
    "مثبت", "موثّق", "يتفوق على السوق", "مربح", "موثوق", "معايَر",
]
# Second-person / imperative markers (audit only; the framing line and
# the disclaimers are verbatim canonical text and are exempted).
IMPERATIVE_EN = ["you should", "you must", "you need to"]
IMPERATIVE_AR = ["يجب عليك", "عليك أن"]

# Secret-pattern metric keys: dropped from the per-tool display (R-F11).
SECRET_KEY_RES = [
    re.compile(p, re.IGNORECASE)
    for p in (r"KEY", r"TOKEN", r"SECRET", r"PASSWORD", r"AUTH",
              r"CREDENTIAL", r"PRIVATE", r"SESSION", r"COOKIE")
]

# Strings that are verbatim canonical legal text: exempt from the audit.
AUDIT_EXEMPT = []

# --- §2f formatting table ----------------------------------------------
def fmt_pct(v):
    return "%+.2f%%" % v

def fmt_score(v):
    return "%+.2f" % v

def fmt_conf(v):
    return "%.2f" % v

def fmt_price(v):
    return "%.2f" % v

def fmt_sigma(v):
    return "%.4f" % v

def fmt_weight(v):
    return "×%.3f" % v

def fmt_int(v):
    return "%d" % v


def esc(s):
    return html.escape(str(s), quote=True)


class RenderError(Exception):
    """Fail-loudly render refusal: no files are written."""


# --- model loading / validation (§3) ------------------------------------
def load_model_bytes(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        model = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RenderError("model_unreadable: %s: %s" % (path, exc))
    if not isinstance(model, dict):
        raise RenderError("model_unreadable: top level is not an object")
    return raw, model


def validate_model(model):
    """Refusal rule (§3): schema + envelope. Raises RenderError.

    The version check is the shared contract
    (``scripts/report_model.py``): exactly (1, /1) or (2, /2),
    mixed markers and unknown versions refused, and a field the
    declared version does not define refused by the schema-diff
    check — the same verdict the validator and the delta adapter
    give. A v1 model renders with its events section saying "not
    recorded"; it is never relabelled as v2 and never shown an
    empty events set."""
    problems = report_model.validate_model(model)
    if problems:
        # The shared gate phrases the tuple refusal with the prefix
        # already: strip it per problem so the refusal carries the
        # prefix once, not twice.
        stripped = [p[len("model_schema_unsupported: "):]
                    if p.startswith("model_schema_unsupported: ") else p
                    for p in problems]
        raise RenderError(
            "model_schema_unsupported: " + "; ".join(stripped))
    if model.get("metrics_schema") != METRICS_SCHEMA:
        raise RenderError(
            "model_schema_unsupported: metrics_schema %r, expected %r"
            % (model.get("metrics_schema"), METRICS_SCHEMA))
    for field in ("job", "job_shape", "sweep_dir", "finished",
                  "ensemble_shape", "partial", "ensemble_absent"):
        if field not in model or model.get(field) is None:
            raise RenderError("model_envelope_missing: %s" % field)
    ens = model.get("ensemble")
    if ens is not None and not model.get("ensemble_absent"):
        if ens.get("ticker") != model.get("ticker"):
            raise RenderError(
                "model_envelope_contradiction: ticker %r != ensemble.ticker %r"
                % (model.get("ticker"), ens.get("ticker")))
    rec = model.get("recommendation")
    if rec is not None and rec.get("ticker") != model.get("ticker"):
        raise RenderError(
            "model_envelope_contradiction: ticker %r != recommendation.ticker %r"
            % (model.get("ticker"), rec.get("ticker")))
    if model.get("market") not in ("EGX", "US", None):
        raise RenderError(
            "model_envelope_contradiction: market %r" % (model.get("market"),))
    prov = model.get("provenance") or {}
    if prov.get("merged_by") not in ("actions", "worker", None):
        raise RenderError(
            "model_envelope_contradiction: merged_by %r" % (prov.get("merged_by"),))
    degraded = model.get("degraded")
    if degraded is not None and degraded.get("reason") not in (
            "keyless", "partial-fleet", "no-base-price", "merge-failed"):
        raise RenderError(
            "model_envelope_contradiction: degraded.reason %r"
            % (degraded.get("reason"),))
    # Non-finite numbers anywhere in a displayed field (R-F12).
    def _walk(obj, path=""):
        if isinstance(obj, float) and not math.isfinite(obj):
            raise RenderError("model_non_finite_number: %s" % path)
        if isinstance(obj, dict):
            for key, val in obj.items():
                _walk(val, path + "/" + str(key))
        elif isinstance(obj, list):
            for i, val in enumerate(obj):
                _walk(val, "%s[%d]" % (path, i))
    _walk(model)


def model_numbers(model):
    """Every numeric leaf in the model, for the prose-audit registry.
    Numbers embedded in string leaves (news titles, report text) count
    too: they still have a model source."""
    out = []
    def _walk(obj):
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            out.append(float(obj))
        elif isinstance(obj, str):
            for m in re.finditer(r"[-+]?\d[\d,]*\.?\d*\s*%", obj):
                try:
                    out.append(float(m.group(0).replace("%", "").replace(",", "").strip()))
                except ValueError:
                    pass
            for m in re.finditer(r"(?<![\w.])[-+]?\d+\.\d+(?!\d)", obj):
                try:
                    out.append(float(m.group(0)))
                except ValueError:
                    pass
        elif isinstance(obj, dict):
            for val in obj.values():
                _walk(val)
        elif isinstance(obj, list):
            for val in obj:
                _walk(val)
    _walk(model)
    return out


def model_dates(model):
    out = set()
    def _walk(obj):
        if isinstance(obj, str):
            for m in re.finditer(r"\d{4}-\d{2}-\d{2}", obj):
                out.add(m.group(0))
        elif isinstance(obj, dict):
            for val in obj.values():
                _walk(val)
        elif isinstance(obj, list):
            for val in obj:
                _walk(val)
    _walk(model)
    return out


# --- i18n (§2h) ----------------------------------------------------------
def load_i18n(path):
    with open(path, encoding="utf-8") as fh:
        table = json.load(fh)
    if not isinstance(table, dict):
        raise RenderError("i18n_unreadable: top level is not an object")
    missing = [k for k, v in table.items()
               if not isinstance(v, dict) or "en" not in v or "ar" not in v]
    if missing:
        raise RenderError("i18n_parity: keys missing en or ar: %s" % missing)
    return table


# --- i18n templates + display maps (§2h, issue #268) --------------------
# Two mechanisms, one table (render_i18n.json, EN/AR parity fail-closed):
#
# 1. Static chrome: <... data-i18n="key">EN</...> — setLang swaps the
#    whole element from window.I18N (the pre-existing mechanism).
# 2. Templated chrome: <... data-i18n-tpl="key" data-tpl-<name>="<raw>"
#    data-tpl-display="<name>:<kind>,...">EN</...> — setLang rebuilds
#    the line from the AR template, substituting args; args named in
#    data-tpl-display are looked up as display.<kind>.<value> first.
#    Templates are used where a line must stay ONE text node in EN
#    (a harness case asserts an exact label+value substring, e.g. the
#    disagreement headline, the news line, "merged by worker") or
#    where AR word order differs. The EN text rendered now is built
#    from the EN template, so the EN view is unchanged.
# 3. Display maps: model-carried display strings (enums, flag
#    prefixes, band basis, confidence basis) render as
#    <span data-i18n="display.<kind>.<value>">EN</span>. An unmapped
#    value renders verbatim EN and is logged (display_unmapped) so a
#    new enum value never refuses a live sweep.
def tpl_attrs(key, args, display_map=None):
    parts = ['data-i18n-tpl="%s"' % esc(key)]
    for name in sorted(args):
        parts.append('data-tpl-%s="%s"' % (esc(name), esc(str(args[name]))))
    if display_map:
        parts.append('data-tpl-display="%s"' % esc(",".join(
            "%s:%s" % kv for kv in sorted(display_map.items()))))
    return " ".join(parts)


def tpl_text(i18n, key, args):
    """EN text of a templated chrome line (args escaped)."""
    text = i18n[key]["en"]
    for name, val in args.items():
        text = text.replace("{%s}" % name, esc(str(val)))
    return text


def display_span(i18n, kind, value, log):
    if value is None:
        return ""
    key = "display.%s.%s" % (kind, value)
    if key in i18n:
        return '<span data-i18n="%s">%s</span>' % (esc(key), esc(value))
    log.append("display_unmapped: %s %r" % (kind, value))
    return esc(value)


# Known compiler flag patterns (compile_model.py): each maps to an
# i18n template/static key. Anything else renders verbatim EN and is
# logged, so a new compiler flag never refuses a live sweep.
_FLAG_RES = [
    (re.compile(r"^witnesses-stale: common_date (\S+) vs base_date (\S+)$"),
     "flag.witnesses-stale", ("common", "base"), None),
    (re.compile(r"^tree-sha-unavailable: archive SHA given by flag, no git "
                r"checkout to derive the tree SHA$"),
     "flag.tree-sha-unavailable", (), None),
    (re.compile(r"^archive-sha-unavailable: sweep dir is not a git checkout "
                r"and no --archive-sha was given$"),
     "flag.archive-sha-unavailable", (), None),
    (re.compile(r"^recommendation-unavailable: no profiles/(\S+)\.recommendation\.json$"),
     "flag.recommendation-unavailable", ("ticker",), None),
    (re.compile(r"^recommendation-stale: profile as_of (\S+) base (\S+) != "
                r"sweep (\S+) base (\S+)$"),
     "flag.recommendation-stale", ("asof", "base1", "date", "base2"), None),
    (re.compile(r"^base-from-undated-row$"),
     "flag.base-from-undated-row", (), None),
    (re.compile(r"^undated-actions: (\d+)$"),
     "flag.undated-actions", ("n",), None),
    (re.compile(r"^ledger-unreadable: (.+)$"),
     "flag.ledger-unreadable", ("path",), None),
    (re.compile(r"^weights-sha-differs-from-main$"),
     "flag.weights-sha-differs", (), None),
    (re.compile(r"^summary-missing: (\S+) \((\S+)\)$"),
     "flag.summary-missing", ("tool", "status"), {"status": "toolstatus"}),
    (re.compile(r"^sharia-table-missing: (\S+)$"),
     "flag.sharia-table-missing", ("std",), None),
    (re.compile(r"^sharia-insufficient-data: (\S+)$"),
     "flag.sharia-insufficient-data", ("std",), None),
    (re.compile(r"^disclosure-events-unavailable: (\S+): (.+)$"),
     "flag.disclosure-events-unavailable", ("file", "reason"), None),
    (re.compile(r"^disclosure-events-stale: (.+)$"),
     "flag.disclosure-events-stale", ("reason",), None),
]

# Risk-flag patterns (ensemble.py): "{type} event: {title}" plus the
# fixed abnormal-move / price-confirms / disclosures lines. The title
# itself is quoted news text and stays verbatim.
_RISK_FLAG_RES = [
    (re.compile(r"^(\w+) event: (.*)$", re.S),
     "riskflag.event", ("type", "title"), {"type": "event-type"}),
    (re.compile(r"^abnormal move: last session ([\d.]+)σ$"),
     "riskflag.abnormal-last", ("z",), None),
    (re.compile(r"^abnormal move: ([\d.]+)σ in the last 3 sessions$"),
     "riskflag.abnormal-3", ("z",), None),
    (re.compile(r"^price confirms: last session ([\d.]+)σ$"),
     "riskflag.price-confirms", ("z",), None),
    (re.compile(r"^(\d+) disclosure\(s\) in the last 3 days$"),
     "riskflag.disclosures", ("n",), None),
]


def _flag_element(i18n, text, patterns, log, what):
    """One <p class="flag"> element for a model flag: localized when
    its pattern is known, verbatim EN + log line when it is not."""
    for rx, key, names, display_map in patterns:
        m = rx.match(text)
        if not m:
            continue
        args = dict(zip(names, m.groups()))
        if not names:
            return ('<p class="flag" data-i18n="%s">%s</p>'
                    % (esc(key), esc(i18n[key]["en"])))
        return ('<p class="flag" %s>%s</p>'
                % (tpl_attrs(key, args, display_map),
                   tpl_text(i18n, key, args)))
    log.append("display_unmapped: %s flag %r" % (what, text))
    return '<p class="flag">%s</p>' % esc(text)


def render_flag(i18n, flag, log):
    return _flag_element(i18n, flag, _FLAG_RES, log, "model")


def render_risk_flag(i18n, flag, log):
    return _flag_element(i18n, flag, _RISK_FLAG_RES, log, "risk")


# --- prose-audit (§2i) ----------------------------------------------------
def _phrase_re(phrase):
    # Word-boundary aware: a phrase next to a letter, digit or hyphen is
    # part of another word ("buy-decision" must not trip "buy").
    return re.compile(r"(?<![\w\-])" + re.escape(phrase) + r"(?![\w\-])",
                      re.IGNORECASE if phrase.isascii() else 0)


_FORBIDDEN_RES = [_phrase_re(p) for p in FORBIDDEN_EN + FORBIDDEN_AR]
_IMPERATIVE_RES = [_phrase_re(p) for p in IMPERATIVE_EN + IMPERATIVE_AR]


# --- derived claims (§2i, issue #261) --------------------------------------
# A derived number is one the renderer computes from model fields, so it
# appears in no model leaf (the disagreement spread: max-min of the
# family scores). It passes the prose-audit ONLY as an explicitly traced
# derived claim: an approved formula + source-field bindings, verified by
# recomputation against the raw model values. A derived value that does
# not recompute within the audit tolerance, or whose named sources are
# not the actual argmax/argmin, is refused exactly like an unsourced
# number. There is no blanket exemption for headline numbers and the
# tolerance is NOT widened (AUDIT_TOLERANCE is the pre-existing 0.011).
AUDIT_TOLERANCE = 0.011

APPROVED_DERIVATIONS = {
    "disagreement-spread": {
        "formula": "max(family_scores) - min(family_scores)",
        "sources": ("family_scores.<hi-family>",
                    "family_scores.<lo-family>"),
    },
}


def verify_derived_claim(claim, model):
    """Recompute one derived claim from the raw model and check its
    source-field bindings. Returns the claim's displayed value.
    Raises RenderError on any mismatch (unapproved formula, wrong
    argmax/argmin binding, stale bound values, recompute drift)."""
    if not isinstance(claim, dict):
        raise RenderError("derived_claim_invalid: claim is not an object")
    spec = APPROVED_DERIVATIONS.get(claim.get("name"))
    if spec is None:
        raise RenderError("derived_claim_unapproved: %r"
                          % (claim.get("name"),))
    if claim.get("formula") != spec["formula"]:
        raise RenderError(
            "derived_claim_unapproved_formula: %r != approved %r"
            % (claim.get("formula"), spec["formula"]))
    scores = {k: v for k, v in (model.get("family_scores") or {}).items()
              if v is not None}
    hi_family = claim.get("hi_family")
    lo_family = claim.get("lo_family")
    if hi_family not in scores or lo_family not in scores:
        raise RenderError(
            "derived_claim_binding_missing: %r / %r not in family_scores"
            % (hi_family, lo_family))
    hi = max(scores.items(), key=lambda kv: kv[1])
    lo = min(scores.items(), key=lambda kv: kv[1])
    if hi[0] != hi_family or lo[0] != lo_family:
        raise RenderError(
            "derived_claim_binding_mismatch: headline names %s / %s but "
            "family_scores argmax/argmin are %s / %s"
            % (hi_family, lo_family, hi[0], lo[0]))
    if (abs(float(claim.get("hi_value", float("nan"))) - hi[1])
            > AUDIT_TOLERANCE
            or abs(float(claim.get("lo_value", float("nan"))) - lo[1])
            > AUDIT_TOLERANCE):
        raise RenderError(
            "derived_claim_binding_mismatch: headline bound values %r / %r "
            "do not match family_scores %r / %r"
            % (claim.get("hi_value"), claim.get("lo_value"),
               hi[1], lo[1]))
    recomputed = hi[1] - lo[1]
    displayed = claim.get("displayed_spread")
    if displayed is None or abs(float(displayed) - recomputed) > AUDIT_TOLERANCE:
        raise RenderError(
            "derived_claim_recompute_mismatch: spread %r does not recompute "
            "from %s %r - %s %r = %r (formula: %s)"
            % (displayed, hi_family, hi[1], lo_family, lo[1],
               recomputed, claim.get("formula")))
    return float(displayed)


def audit_narrative(text, allowed_numbers, allowed_dates, label,
                    derived_claims=None, model=None):
    """Number trace + forbidden words + imperatives. Raises RenderError.

    ``derived_claims`` is a list of explicitly traced derived claims
    (see verify_derived_claim): each is verified by recomputation
    against ``model`` first, and only its verified displayed value may
    then satisfy the number trace — a literal that matches no model
    number and no verified derived value is still refused.
    """
    if not text:
        return
    checked = text
    for exempt in AUDIT_EXEMPT:
        checked = checked.replace(exempt, " ")
    # 1. Forbidden words / imperatives (word-boundary aware).
    for rx in _FORBIDDEN_RES + _IMPERATIVE_RES:
        m = rx.search(checked)
        if m:
            raise RenderError(
                "prose_audit_failed: %s: forbidden wording %r in %r"
                % (label, m.group(0), text[:160]))
    # 1b. Derived claims: verify each by recomputation against the raw
    # model before any literal may rely on it.
    derived_values = []
    for claim in (derived_claims or []):
        if model is None:
            raise RenderError(
                "derived_claim_no_model: %s passed without a model to "
                "verify against" % label)
        derived_values.append(verify_derived_claim(claim, model))
    # 2. Every number must trace to the model (within formatting rounding),
    # or to a verified derived claim's displayed value (matched tightly:
    # the literal is the claim's own formatted value, so 0.001 suffices —
    # the 0.011 audit tolerance applies to the claim's recomputation,
    # not to the literal match).
    # The lookahead allows sentence-final punctuation: "8.20." must still
    # be audited as 8.20, not skipped because a period follows it.
    for m in re.finditer(r"[-+]?\d[\d,]*\.?\d*\s*%", checked):
        val = float(m.group(0).replace("%", "").replace(",", "").strip())
        if not any(abs(val - n) <= 0.011 for n in allowed_numbers) \
                and not any(abs(val - d) <= 0.001 for d in derived_values):
            raise RenderError(
                "prose_audit_failed: %s: number %r has no model source in %r"
                % (label, m.group(0), text[:160]))
    for m in re.finditer(r"(?<![\w.])[-+]?\d+\.\d+(?!\d)", checked):
        val = float(m.group(0))
        if not any(abs(val - n) <= 0.011 for n in allowed_numbers) \
                and not any(abs(val - d) <= 0.001 for d in derived_values):
            raise RenderError(
                "prose_audit_failed: %s: number %r has no model source in %r"
                % (label, m.group(0), text[:160]))
    for m in re.finditer(r"(?<![\w.])\d{4}-\d{2}-\d{2}(?![\w.])", checked):
        if m.group(0) not in allowed_dates:
            raise RenderError(
                "prose_audit_failed: %s: date %r has no model source in %r"
                % (label, m.group(0), text[:160]))


# --- minimal Markdown-subset converter (D-4) ------------------------------
def md_to_html(md_text):
    """Pinned subset: headings, tables, lists, bold/italic, inline code,
    links. Anything outside the subset falls back to escaped <pre>."""
    lines = md_text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            out.append("<h%d>%s</h%d>" % (len(m.group(1)) + 1,
                                          _md_inline(m.group(2)),
                                          len(m.group(1)) + 1))
            i += 1
            continue
        if re.match(r"^\s*\|.*\|\s*$", line) and i + 1 < len(lines) and \
                re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
            rows = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if len(rows) < 2:
                out.append("<pre>%s</pre>" % esc(line))
                continue
            head = rows[0]
            body = [r for r in rows[1:] if not all(set(c) <= set(":- ") for c in r)]
            buf = ["<table><thead><tr>%s</tr></thead><tbody>"
                   % "".join("<th>%s</th>" % _md_inline(c) for c in head)]
            for r in body:
                buf.append("<tr>%s</tr>"
                           % "".join("<td>%s</td>" % _md_inline(c) for c in r))
            buf.append("</tbody></table>")
            out.append("".join(buf))
            continue
        if re.match(r"^\s*[-*]\s+\S", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+\S", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append("<ul>%s</ul>"
                       % "".join("<li>%s</li>" % _md_inline(c) for c in items))
            continue
        if re.match(r"^\s*\d+[.)]\s+\S", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s+\S", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]))
                i += 1
            out.append("<ol>%s</ol>"
                       % "".join("<li>%s</li>" % _md_inline(c) for c in items))
            continue
        # Plain paragraph; a line carrying raw HTML falls back to <pre>.
        if "<" in line and re.search(r"<[a-zA-Z/!]", line):
            out.append("<pre>%s</pre>" % esc(line))
            i += 1
            continue
        out.append("<p>%s</p>" % _md_inline(line))
        i += 1
    return "\n".join(out)


def _md_inline(text):
    text = esc(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


# --- sweep-dir fallback reads (I-5) ---------------------------------------
def read_tool_report(sweep_dir, tool):
    path = os.path.join(sweep_dir, "collected", tool, "report.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def read_price_tail(sweep_dir, allowed_sources=None):
    """Last 30 close-bearing rows per price source (IR-3 fallback).
    Only files the model names in ``price_series_last`` are read — a
    sweep dir also holds reference-workload CSVs (e.g. AAPL) that must
    never be plotted as the ticker's series."""
    tails = {}
    collected = os.path.join(sweep_dir, "collected")
    if not os.path.isdir(collected):
        return tails
    for tool in sorted(os.listdir(collected)):
        tool_dir = os.path.join(collected, tool)
        if not os.path.isdir(tool_dir):
            continue
        for fname in sorted(os.listdir(tool_dir)):
            rel = "%s/%s" % (tool, fname)
            if allowed_sources is not None and rel not in allowed_sources:
                continue
            if not fname.endswith(".csv"):
                continue
            path = os.path.join(tool_dir, fname)
            try:
                with open(path, newline="", encoding="utf-8", errors="replace") as fh:
                    rows = list(csv.DictReader(fh))
            except Exception:
                continue
            if not rows:
                continue
            keys = [k.lower() if k else "" for k in (rows[0].keys() or [])]
            if "date" not in keys or "close" not in keys:
                continue
            date_k = [k for k in rows[0].keys() if k and k.lower() == "date"][0]
            close_k = [k for k in rows[0].keys() if k and k.lower() == "close"][0]
            series = []
            prev_date = None
            bad_order = False
            for row in rows:
                try:
                    close = float(str(row[close_k]).replace(",", ""))
                except (TypeError, ValueError):
                    continue
                # Issue #258: float() accepts NaN/Infinity — a
                # non-finite close is not a price, skip the row.
                if not math.isfinite(close):
                    continue
                date = str(row[date_k])[:10]
                if not date:
                    continue
                # Issue #258: no date-order validation let a
                # misordered file plot backwards. Dates must be
                # strictly increasing; a violation drops the whole
                # series rather than a silently wrong chart.
                if prev_date is not None and date <= prev_date:
                    bad_order = True
                    break
                prev_date = date
                series.append((date, close))
            if series and not bad_order:
                tails["%s/%s" % (tool, fname)] = series[-30:]
    return tails


def read_kronos_forecast(sweep_dir):
    path = os.path.join(sweep_dir, "collected", "kronos", "forecast.csv")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:
        return None
    out = []
    for row in rows:
        keys = {k.lower(): k for k in row.keys() if k}
        if "date" not in keys or "close" not in keys:
            return None
        try:
            out.append((str(row[keys["date"]])[:10],
                        float(str(row[keys["close"]]).replace(",", ""))))
        except (TypeError, ValueError):
            continue
    return out or None


# --- view building (§2d) ---------------------------------------------------
REFERENCE_WORKLOADS = {"backtrader", "pybroker", "edgartools", "finvizfinance"}

def band_levels(model):
    """D2 bands: model.levels, or the §2i fallback from horizons.week."""
    levels = model.get("levels")
    if levels and levels.get("support") is not None and levels.get("resistance") is not None:
        return float(levels["support"]), float(levels["resistance"]), levels.get("basis", ""), False
    week = (model.get("horizons") or {}).get("week")
    price = model.get("price") or {}
    base = price.get("base_price")
    if week and base is not None and week.get("range_low_pct") is not None \
            and week.get("range_high_pct") is not None:
        support = base * (1 + float(week["range_low_pct"]) / 100.0)
        resistance = base * (1 + float(week["range_high_pct"]) / 100.0)
        return support, resistance, "week horizon range_low_pct / range_high_pct", True
    return None, None, "", False


def disagreement_headline(model):
    """Headline + its explicitly traced derived claim (#261).

    Returns (headline, claim, tpl_args) or (None, None, None) when
    fewer than two families scored. The spread is a derived number:
    the claim binds it to its approved formula and source fields (the
    argmax/argmin families and their raw scores) so the prose-audit
    can verify it by recomputation instead of by registry membership.
    tpl_args carries the same values for the i18n template
    (headline.disagree): the EN headline is built from the EN
    template so the EN view is byte-identical to before.
    """
    scores = {k: v for k, v in (model.get("family_scores") or {}).items()
              if v is not None}
    if len(scores) < 2:
        return None, None, None
    hi = max(scores.items(), key=lambda kv: kv[1])
    lo = min(scores.items(), key=lambda kv: kv[1])
    spread = hi[1] - lo[1]
    headline = ("Families disagree: %s %s vs %s %s (spread %s)"
                % (hi[0], fmt_score(hi[1]), lo[0], fmt_score(lo[1]),
                   fmt_score(spread)))
    claim = {
        "name": "disagreement-spread",
        "formula": APPROVED_DERIVATIONS["disagreement-spread"]["formula"],
        "hi_family": hi[0],
        "hi_value": hi[1],
        "lo_family": lo[0],
        "lo_value": lo[1],
        "spread": spread,
        "displayed_spread": float(fmt_score(spread)),
    }
    tpl_args = {"hi": hi[0], "hi_val": fmt_score(hi[1]),
                "lo": lo[0], "lo_val": fmt_score(lo[1]),
                "spread": fmt_score(spread)}
    return headline, claim, tpl_args


def drop_secrets(summary):
    """R-F11: drop secret-pattern metric keys from the display copy.
    Recurses into nested dicts (e.g. a tool's ``metrics`` block)."""
    if isinstance(summary, list):
        return [drop_secrets(v)[0] for v in summary], []
    if not isinstance(summary, dict):
        return summary, []
    dropped = []
    kept = {}
    for key, val in summary.items():
        if any(rx.search(str(key)) for rx in SECRET_KEY_RES):
            dropped.append(str(key))
            continue
        if isinstance(val, dict):
            val, sub = drop_secrets(val)
            dropped.extend(sub)
        kept[key] = val
    return kept, dropped


def build_view(model, profile, delta, narrative, sweep_dir, i18n):
    """One shared view feeding HTML + MD. Returns (sections, numbers,
    dates, log, slot_html, slot_md, quoted, derived_claims)."""
    t = model.get("ticker")
    ens = model.get("ensemble") or {}
    price = model.get("price") or {}
    numbers = list(model_numbers(model))
    dates = model_dates(model)
    derived_claims = []  # explicitly traced derived claims (#261)
    if delta:
        numbers += model_numbers(delta)
        dates |= model_dates(delta)
    if profile:
        numbers += model_numbers(profile)
    sections = []  # (anchor, title_key, html_body, md_body)
    quoted = []  # (html form, md form) of verbatim tool reports: quoted
    # data, not narrative — excluded from the prose-audit (§2i).
    log = []

    def fmt_num_list(vals):
        for v in vals:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                numbers.append(float(v))

    # §0 header + short disclaimer (always present).
    no_forecast = bool(model.get("partial") or model.get("ensemble_absent"))
    no_forecast_key = "forecast.partial" if model.get("partial") else "forecast.noensemble"
    header_md = [
        "# Borsagator report — %s (%s)" % (t, model.get("date")),
        "",
        "Job: %s · shape: %s · market: %s" % (
            model.get("job"), model.get("job_shape"),
            model.get("market") or "no market filter"),
        "Model: %s · sweep: %s · archive commit: %s" % (
            model.get("schema"), model.get("sweep_dir"),
            model.get("archive_commit") or "not recorded"),
    ]
    sections.append(("header", "sec.header", "", "\n".join(header_md)))

    # §1 D2 bands.
    support, resistance, basis, computed = band_levels(model)
    rec = model.get("recommendation")
    bands_md = ["## Technical Support / Resistance Levels"]
    bands_html = []
    if no_forecast:
        # §2j: forecast sections are omitted with the placeholder in
        # their place — never zero-filled, never a stale line.
        bands_html.append('<p data-i18n="%s">%s</p>' % (
            no_forecast_key, esc(i18n[no_forecast_key]["en"])))
        bands_md.append(i18n[no_forecast_key]["en"])
    else:
        if support is None:
            bands_html.append('<p data-i18n="bands.none">No levels available for this sweep.</p>')
            bands_md.append("No levels available for this sweep.")
        else:
            bands_html.append(
                '<p><span data-i18n="bands.support">Technical Support Level at</span> '
                '<span class="num">%s</span></p>' % fmt_price(support))
            bands_html.append(
                '<p><span data-i18n="bands.resistance">Technical Resistance Level at</span> '
                '<span class="num">%s</span></p>' % fmt_price(resistance))
            # The basis is a model-carried display string: the two
            # known values map through display.levels-basis; anything
            # else renders verbatim (display_span logs it).
            bands_html.append('<p class="dim">%s</p>' % (
                display_span(i18n, "levels-basis", basis, log)
                if basis else ""))
            if computed:
                bands_html.append('<p class="dim" data-i18n="bands.computed">'
                                   'Computed by the renderer from the week horizon range.</p>')
                bands_md.append("_Computed by the renderer from the week horizon range._")
            bands_md.append("Technical Support Level at %s" % fmt_price(support))
            bands_md.append("Technical Resistance Level at %s" % fmt_price(resistance))
            bands_md.append("Basis: %s" % basis)
            base = price.get("base_price")
            if base is not None and not (support < base < resistance):
                bands_html.append('<p class="dim" data-i18n="bands.note.oneside">Both levels sit on one side of the current price — the range does not straddle the base.</p>')
                bands_md.append("Both levels sit on one side of the current price — the range does not straddle the base.")
        bands_html.append(
            '<p class="framing" data-i18n="framing">This is a description of a computed '
            'model output, not a recommendation to buy, sell, or hold any security. '
            'You must make your own investment decisions.</p>')
        bands_md.append(
            "> This is a description of a computed model output, not a recommendation "
            "to buy, sell, or hold any security. You must make your own investment decisions.")
        if rec is None:
            bands_html.append('<p data-i18n="rec.none">Recommendation not available for this sweep.</p>')
            bands_md.append("Recommendation not available for this sweep.")
        else:
            bands_html.append('<p><span data-i18n="rec.base">Base price:</span> <span class="num">%s</span> · <span data-i18n="rec.ref">Reference price:</span> <span class="num">%s</span></p>' % (
                fmt_price(rec.get("base_price")),
                fmt_price(rec.get("reference_price"))))
            bands_md.append("Base price: %s · Reference price: %s" % (
                fmt_price(rec.get("base_price")), fmt_price(rec.get("reference_price"))))
            for note in rec.get("notes") or []:
                audit_narrative(note, numbers, dates, "recommendation.notes")
                bands_html.append('<p>%s</p>' % esc(note))
                bands_md.append("- %s" % note)
    sections.append(("bands", "sec.bands", "\n".join(bands_html), "\n".join(bands_md)))

    # §2 family scores + applied weights + disagreement headline.
    fscores = model.get("family_scores") or {}
    fam_html, fam_md = [], ["## Family scores"]
    headline, headline_claim, headline_args = disagreement_headline(model)
    if headline:
        derived_claims.append(headline_claim)
        audit_narrative(headline, numbers, dates, "disagreement-headline",
                        derived_claims=derived_claims, model=model)
        log.append("derived-claim disagreement-spread: %s %r - %s %r = %r "
                   "(displayed %s; formula: %s)"
                   % (headline_claim["hi_family"],
                      headline_claim["hi_value"],
                      headline_claim["lo_family"],
                      headline_claim["lo_value"],
                      headline_claim["spread"],
                      fmt_score(headline_claim["spread"]),
                      headline_claim["formula"]))
        # One text node in EN (a harness case asserts the exact EN
        # headline); the AR form comes from the headline.disagree
        # template, with the family names display-mapped.
        fam_html.append('<p class="headline" %s>%s</p>' % (
            tpl_attrs("headline.disagree", headline_args,
                      {"hi": "family", "lo": "family"}),
            esc(headline)))
        fam_md.append(headline)
    fam_html.append('<table><thead><tr><th data-i18n="th.family">Family</th><th data-i18n="th.score">Score</th></tr></thead><tbody>')
    for fam in ("price-forecast", "technicals", "sentiment", "fundamentals", "agent"):
        val = fscores.get(fam)
        if val is not None:
            cell = fmt_score(val)
        else:
            cell = '<span data-i18n="fam.nodata">no data</span>'
        fam_html.append("<tr><td>%s</td><td class=\"num\">%s</td></tr>" % (
            display_span(i18n, "family", fam, log), cell))
        fam_md.append("- %s: %s" % (fam, fmt_score(val) if val is not None else "no data"))
    fam_html.append("</tbody></table>")
    weights = model.get("weights") or {}
    applied = weights.get("applied_weights")
    shape = model.get("ensemble_shape") or {}
    if applied and shape.get("has_applied_weights"):
        factors = applied.get("factors") or {}
        fam_html.append('<p><span data-i18n="weights.applied.label">Applied weights (ledger):</span> %s</p>' % ", ".join(
            "%s %s" % (display_span(i18n, "family", k, log), fmt_weight(v))
            for k, v in sorted(factors.items())))
        fam_md.append("Applied weights (ledger): %s" % ", ".join(
            "%s %s" % (k, fmt_weight(v)) for k, v in sorted(factors.items())))
        # The basis is a model-carried display string (two known
        # values); anything else renders verbatim (display_span logs).
        basis = weights.get("confidence_basis") or ""
        fam_html.append('<p><span data-i18n="weights.confidence.label">Confidence basis:</span> %s</p>' % (
            display_span(i18n, "confidence-basis", basis, log) if basis else ""))
        fam_md.append("Confidence basis: %s" % (weights.get("confidence_basis") or ""))
    else:
        fam_html.append('<p data-i18n="weights.none">Weights not recorded for this sweep (pre-#93/#94 run).</p>')
        fam_md.append("Weights not recorded for this sweep (pre-#93/#94 run).")
    if no_forecast:
        fam_html = ['<p data-i18n="%s">%s</p>' % (
            no_forecast_key, esc(i18n[no_forecast_key]["en"]))]
        fam_md = ["## Family scores", i18n[no_forecast_key]["en"]]
    sections.append(("families", "sec.families", "\n".join(fam_html), "\n".join(fam_md)))

    # §3 delta (optional input I-3).
    d_html, d_md = [], ["## What changed"]
    if delta is None:
        d_html.append('<p data-i18n="delta.none">First sweep of this ticker + job shape — nothing to compare against yet.</p>')
        d_md.append("First sweep of this ticker + job shape — nothing to compare against yet.")
    elif delta.get("pair_invalid"):
        reason = str(delta.get("pair_invalid"))
        d_html.append('<p %s>%s</p>' % (
            tpl_attrs("delta.unavailable", {"reason": reason}),
            tpl_text(i18n, "delta.unavailable", {"reason": reason})))
        d_md.append("Delta unavailable — %s" % reason)
    elif delta.get("first_sweep"):
        d_html.append('<p data-i18n="delta.none">First sweep of this ticker + job shape — nothing to compare against yet.</p>')
        d_md.append("First sweep of this ticker + job shape — nothing to compare against yet.")
    else:
        prev = os.path.basename(str(delta.get("previous_sweep") or ""))
        cur = os.path.basename(str(delta.get("current_sweep") or ""))
        d_html.append('<p %s>%s</p>' % (
            tpl_attrs("delta.prevcur", {"prev": prev, "cur": cur}),
            tpl_text(i18n, "delta.prevcur", {"prev": prev, "cur": cur})))
        d_md.append("Previous: %s · Current: %s" % (prev, cur))
        exd = delta.get("ex_date") or {}
        if exd.get("ex_date"):
            d_html.append('<p %s>%s</p>' % (
                tpl_attrs("delta.exdate", {"date": exd["ex_date"],
                                          "pct": fmt_pct(exd.get("mechanical_pct"))}),
                tpl_text(i18n, "delta.exdate", {"date": exd["ex_date"],
                                                "pct": fmt_pct(exd.get("mechanical_pct"))})))
            d_md.append("Ex-date %s in window: mechanical %s" % (
                exd["ex_date"], fmt_pct(exd.get("mechanical_pct"))))
        pd = (delta.get("sections") or {}).get("price") or {}
        pdel = pd.get("delta") or {}
        if pdel:
            d_html.append('<p %s>%s</p>' % (
                tpl_attrs("delta.basemove", {
                    "base": fmt_pct(pdel.get("base_pct")),
                    "mech": fmt_pct(pdel.get("mechanical_pct")),
                    "res": fmt_pct(pdel.get("residual_pct"))}),
                tpl_text(i18n, "delta.basemove", {
                    "base": fmt_pct(pdel.get("base_pct")),
                    "mech": fmt_pct(pdel.get("mechanical_pct")),
                    "res": fmt_pct(pdel.get("residual_pct"))})))
            d_md.append("Base move: %s (mechanical %s, residual %s)" % (
                fmt_pct(pdel.get("base_pct")), fmt_pct(pdel.get("mechanical_pct")),
                fmt_pct(pdel.get("residual_pct"))))
        for name in ("price", "horizons", "family_scores", "risk", "tools",
                     "calibration", "corporate_actions", "news", "weights"):
            note = ((delta.get("sections") or {}).get(name) or {}).get("note")
            if note:
                audit_narrative(note, numbers, dates, "delta.sections.%s" % name)
                d_html.append("<p>%s</p>" % esc(note))
                d_md.append("- %s" % note)
        for line in delta.get("notes") or []:
            audit_narrative(line, numbers, dates, "delta.notes")
            d_html.append("<p>%s</p>" % esc(line))
            d_md.append("- %s" % line)
    sections.append(("delta", "sec.delta", "\n".join(d_html), "\n".join(d_md)))

    # §4 horizons + price. The horizons table is a forecast section
    # (§2j placeholder when there is no forecast); the price block and
    # the price-series table are data and still render.
    h_html, h_md = [], ["## Horizons + price"]
    horizons = model.get("horizons") or {}
    if no_forecast:
        h_html.append('<p data-i18n="%s">%s</p>' % (
            no_forecast_key, esc(i18n[no_forecast_key]["en"])))
        h_md.append(i18n[no_forecast_key]["en"])
    elif not horizons:
        h_html.append('<p data-i18n="horizons.none">No horizon scored a family — no forecast.</p>')
        h_md.append("No horizon scored a family — no forecast.")
    else:
        h_html.append('<table><thead><tr><th data-i18n="th.horizon">Horizon</th><th data-i18n="th.direction">Direction</th>'
                      '<th data-i18n="th.expected">Expected</th><th data-i18n="th.range">Range</th><th data-i18n="th.confidence">Confidence</th></tr></thead><tbody>')
        for name in ("day", "week", "month"):
            hz = horizons.get(name)
            if not hz:
                h_html.append("<tr><td>%s</td><td colspan=\"4\" data-i18n=\"fam.horizon.notscored\">not scored</td></tr>" % display_span(i18n, "horizon", name, log))
                h_md.append("- %s: not scored" % name)
                continue
            h_html.append("<tr><td>%s</td><td>%s</td><td class=\"num\">%s</td>"
                          "<td class=\"num\">%s … %s</td><td class=\"num\">%s</td></tr>" % (
                              display_span(i18n, "horizon", name, log),
                              display_span(i18n, "direction", hz.get("direction"), log),
                              fmt_pct(hz.get("expected_move_pct")),
                              fmt_pct(hz.get("range_low_pct")),
                              fmt_pct(hz.get("range_high_pct")),
                              fmt_conf(hz.get("confidence"))))
            h_md.append("- %s: %s %s (range %s … %s, confidence %s)" % (
                name, hz.get("direction"), fmt_pct(hz.get("expected_move_pct")),
                fmt_pct(hz.get("range_low_pct")), fmt_pct(hz.get("range_high_pct")),
                fmt_conf(hz.get("confidence"))))
        h_html.append("</tbody></table>")
    if price:
        base_date = price.get("base_date") or "base date not established"
        h_html.append('<p %s>%s</p>' % (
            tpl_attrs("price.base", {
                "price": fmt_price(price.get("base_price")),
                "source": price.get("base_source"),
                "date": base_date}, {"date": "sentinel"}),
            tpl_text(i18n, "price.base", {
                "price": fmt_price(price.get("base_price")),
                "source": price.get("base_source"),
                "date": base_date})))
        h_md.append("Base price: %s (%s, %s)" % (
            fmt_price(price.get("base_price")), price.get("base_source"),
            price.get("base_date") or "base date not established"))
        cc = price.get("price_crosscheck") or {}
        if cc:
            h_html.append('<p %s>%s</p>' % (
                tpl_attrs("price.crosscheck", {
                    "status": cc.get("status"),
                    "common": cc.get("common_date"),
                    "base": cc.get("base_date")}, {"status": "crosscheck"}),
                tpl_text(i18n, "price.crosscheck", {
                    "status": cc.get("status"),
                    "common": cc.get("common_date"),
                    "base": cc.get("base_date")})))
            h_md.append("Price cross-check: %s (common date %s, base date %s)" % (
                cc.get("status"), cc.get("common_date"), cc.get("base_date")))
            if cc.get("common_date") and price.get("base_date") and \
                    str(cc["common_date"]) < str(price["base_date"]):
                h_html.append('<p class="flag" %s>%s</p>' % (
                    tpl_attrs("price.stale-note", {
                        "common": cc.get("common_date"),
                        "base": price.get("base_date")}),
                    tpl_text(i18n, "price.stale-note", {
                        "common": cc.get("common_date"),
                        "base": price.get("base_date")})))
                h_md.append("Witnesses stale: common date %s trails base date %s." % (
                    cc["common_date"], price["base_date"]))
    psl = model.get("price_series_last") or []
    if psl:
        h_html.append('<table><thead><tr><th data-i18n="th.source">Source</th><th data-i18n="th.lastdate">Last date</th>'
                      '<th data-i18n="th.lastclose">Last close</th><th data-i18n="th.volume">Volume</th></tr></thead><tbody>')
        for row in psl:
            close = row.get("last_close")
            if close is not None:
                cell = fmt_price(close)
            else:
                cell = '<span data-i18n="price.noclose">last close-bearing row has no close — see note</span>'
            stale = '<span data-i18n="price.stale"> (stale)</span>' if row.get("stale") else ""
            h_html.append("<tr><td>%s</td><td>%s</td><td class=\"num\">%s</td><td>%s%s</td></tr>" % (
                esc(row.get("source")), esc(row.get("last_date")), cell,
                esc(str(row.get("last_volume"))), stale))
            h_md.append("- %s: %s on %s%s" % (
                row.get("source"), cell if close is not None else "last close-bearing row has no close — see note",
                row.get("last_date"), " (stale)" if row.get("stale") else ""))
        h_html.append("</tbody></table>")
    sections.append(("horizons", "sec.horizons", "\n".join(h_html), "\n".join(h_md)))

    # §5 reaction profile.
    r_html, r_md = [], ["## Reaction profile"]
    rp = model.get("reaction_profile") or {}
    if not rp.get("present"):
        r_html.append('<p data-i18n="profile.none">No reaction profile for this ticker — no nudge applied.</p>')
        r_md.append("No reaction profile for this ticker — no nudge applied.")
    else:
        wf = rp.get("walk_forward") or {}
        fit = rp.get("fit") or {}
        r_html.append('<p %s>%s</p>' % (
            tpl_attrs("reaction.built", {
                "built": rp.get("built_at"), "train": wf.get("train"),
                "test": wf.get("test"), "hits": wf.get("hits"),
                "base": wf.get("baseline_hits")}),
            tpl_text(i18n, "reaction.built", {
                "built": rp.get("built_at"), "train": wf.get("train"),
                "test": wf.get("test"), "hits": wf.get("hits"),
                "base": wf.get("baseline_hits")})))
        r_md.append("Built at %s · walk-forward train %s / test %s · hits %s · baseline hits %s" % (
            rp.get("built_at"), wf.get("train"), wf.get("test"),
            wf.get("hits"), wf.get("baseline_hits")))
        if profile:
            by_type = profile.get("by_type") or {}
            if by_type:
                r_html.append('<table><thead><tr><th data-i18n="th.eventtype">Event type</th><th data-i18n="th.median5d">Median +5d (div-adj)</th><th data-i18n="th.n">n</th></tr></thead><tbody>')
                for etype, vals in sorted(by_type.items()):
                    med = (vals or {}).get("median_r5_adj")
                    cell = fmt_pct(med) if med is not None else "—"
                    r_html.append("<tr><td>%s</td><td class=\"num\">%s</td><td>%s</td></tr>" % (
                        display_span(i18n, "event-type", etype, log), cell, (vals or {}).get("n")))
                    r_md.append("- %s: median +5d %s (n=%s)" % (etype, cell, (vals or {}).get("n")))
                r_html.append("</tbody></table>")
            events = profile.get("events") or []
            if events:
                r_html.append('<p %s>%s</p>' % (
                    tpl_attrs("reaction.events", {"n": len(events)}),
                    tpl_text(i18n, "reaction.events", {"n": len(events)})))
                r_md.append("Events: %s recorded." % len(events))
    sections.append(("reaction", "sec.reaction", "\n".join(r_html), "\n".join(r_md)))

    # §6 per-tool sections + §7 tool run table.
    tools = model.get("tools") or []
    t_html, t_md = [], ["## Per-tool sections"]
    for tool in tools:
        name = tool.get("tool")
        summary, dropped = drop_secrets(tool.get("summary"))
        if dropped:
            log.append("secret_fields_dropped_from_display: %s: %s" % (name, dropped))
        t_html.append("<h3>%s</h3>" % esc(name))
        t_md.append("### %s" % name)
        if name in REFERENCE_WORKLOADS:
            t_html.append('<p class="dim" %s>%s</p>' % (
                tpl_attrs("tools.refworkload", {"ticker": t}),
                tpl_text(i18n, "tools.refworkload", {"ticker": t})))
            t_md.append("_Reference workload — not %s data._" % t)
        status = tool.get("status")
        t_html.append('<p %s>%s</p>' % (
            tpl_attrs("tools.status", {"status": status,
                                      "code": tool.get("exit_code")},
                      {"status": "toolstatus"}),
            tpl_text(i18n, "tools.status", {"status": status,
                                            "code": tool.get("exit_code")})))
        t_md.append("Status: %s · exit code: %s" % (status, tool.get("exit_code")))
        if summary:
            if isinstance(summary, dict):
                metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else summary
                rows = []
                for k in sorted(metrics.keys()):
                    v = metrics[k]
                    if isinstance(v, bool) or v is None:
                        cell = str(v)
                    elif isinstance(v, (int, float)):
                        cell = fmt_price(v) if abs(v) < 100000 and isinstance(v, float) else str(v)
                    else:
                        cell = esc(str(v))[:200]
                    rows.append("<tr><td>%s</td><td>%s</td></tr>" % (esc(k), cell))
                if rows:
                    t_html.append("<table><tbody>%s</tbody></table>" % "".join(rows))
                t_md.append("Summary keys: %s" % ", ".join(sorted(metrics.keys())[:20]))
            else:
                t_html.append("<p>%s</p>" % esc(str(summary))[:1000])
                t_md.append(str(summary)[:1000])
        else:
            t_html.append('<p data-i18n="tool.nosummary">No summary — tool produced no summary.</p>')
            t_md.append("No summary — tool produced no summary.")
        report_md = None
        if tool.get("report_md_present"):
            if sweep_dir:
                report_md = read_tool_report(sweep_dir, name)
                if report_md is None:
                    raise RenderError(
                        "report_md_mismatch: %s marked present but no file in --sweep-dir" % name)
            else:
                report_md = None
        if report_md:
            report_html = md_to_html(report_md)
            quoted.append((report_html, report_md))
            t_html.append(report_html)
            t_md.append(report_md)
        else:
            t_html.append('<p data-i18n="tool.noreport">No report for this tool.</p>')
            t_md.append("No report for this tool.")
    # §7 run table.
    t_html.append('<h3 data-i18n="tools.runtable">Tool run table</h3>')
    t_md.append("### Tool run table")
    t_html.append('<table><thead><tr><th data-i18n="th.tool">Tool</th><th data-i18n="th.category">Category</th><th data-i18n="th.status">Status</th>'
                  '<th data-i18n="th.exit">Exit</th><th data-i18n="th.run">Run</th></tr></thead><tbody>')
    for tool in tools:
        if tool.get("run_url"):
            run = '<a href="%s" data-i18n="tools.run.link">run</a>' % esc(tool["run_url"])
        elif tool.get("worker_run"):
            run = '<span %s>%s</span>' % (
                tpl_attrs("tools.run.worker", {"id": tool["worker_run"]}),
                tpl_text(i18n, "tools.run.worker", {"id": tool["worker_run"]}))
        else:
            run = '<span data-i18n="tools.run.bare">worker run</span>'
        t_html.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(tool.get("tool")),
            display_span(i18n, "category", tool.get("category"), log),
            display_span(i18n, "toolstatus", tool.get("status"), log),
            tool.get("exit_code"), run))
        t_md.append("- %s (%s): %s, exit %s" % (
            tool.get("tool"), tool.get("category"), tool.get("status"), tool.get("exit_code")))
    for name in model.get("tools_absent") or []:
        t_html.append("<tr><td>%s</td><td></td><td>%s</td><td></td><td></td></tr>" % (
            esc(name), display_span(i18n, "toolstatus", "absent", log)))
        t_md.append("- %s: absent" % name)
    for name in model.get("tools_failed") or []:
        t_html.append("<tr><td>%s</td><td></td><td>%s</td><td></td><td></td></tr>" % (
            esc(name), display_span(i18n, "toolstatus", "failed", log)))
        t_md.append("- %s: failed" % name)
    t_html.append("</tbody></table>")
    sections.append(("tools", "sec.tools", "\n".join(t_html), "\n".join(t_md)))

    # §8 news + disclosures.
    news = model.get("news") or {}
    n_html, n_md = [], ["## News + disclosures"]
    # One text node in EN (a harness case asserts the exact EN line);
    # the AR form comes from the news.line template.
    n_html.append('<p %s>%s</p>' % (
        tpl_attrs("news.line", {
            "news": news.get("news_count"),
            "disc": news.get("disclosure_count"),
            "scheme": news.get("identity_scheme") or ""}),
        tpl_text(i18n, "news.line", {
            "news": news.get("news_count"),
            "disc": news.get("disclosure_count"),
            "scheme": news.get("identity_scheme") or ""})))
    n_md.append("News: %s · disclosures: %s · identity scheme: %s" % (
        news.get("news_count"), news.get("disclosure_count"), news.get("identity_scheme")))
    for item in (news.get("news_items") or [])[:22]:
        title = item.get("title") or ""
        body = '<a href="%s">%s</a>' % (esc(item["identity_key"]), esc(title)) \
            if item.get("key_type") == "resolved_url" and item.get("identity_key") \
            else esc(title)
        n_html.append('<p lang="ar" dir="rtl">%s</p>' % body if _looks_arabic(title)
                      else "<p>%s</p>" % body)
        n_md.append("- %s" % title)
    for item in (news.get("disclosure_items") or [])[:11]:
        title = item.get("title") or ""
        body = '<a href="%s">%s</a>' % (esc(item["identity_key"]), esc(title)) \
            if item.get("key_type") == "resolved_url" and item.get("identity_key") \
            else esc(title)
        n_html.append('<p lang="ar" dir="rtl">%s</p>' % body if _looks_arabic(title)
                      else "<p>%s</p>" % body)
        n_md.append("- %s" % title)
    sections.append(("news", "sec.news", "\n".join(n_html), "\n".join(n_md)))

    # §8b disclosure events (#280, v2 only). A v1 model carries no
    # block: the section says events were NOT RECORDED by that
    # contract — never an empty events set. A v2 block renders its
    # events verbatim (summaries are deterministic extractor
    # templates over structured facts, like news titles); the
    # verification wording avoids the prose-audit's forbidden
    # "verified" ("confirmed" / "not confirmed" instead).
    ev_block = model.get("disclosure_events")
    e_html, e_md = [], ["## Disclosure events"]
    if ev_block is None:
        e_html.append('<p data-i18n="events.not-recorded">%s</p>'
                      % esc(i18n["events.not-recorded"]["en"]))
        e_md.append(i18n["events.not-recorded"]["en"])
    else:
        counts = ev_block.get("counts") or {}
        e_html.append('<p %s>%s</p>' % (
            tpl_attrs("events.line", {
                "events": counts.get("events"),
                "confirmed": counts.get("verified"),
                "candidates": counts.get("candidates"),
                "status": ev_block.get("status") or ""},
                {"status": "events-status"}),
            tpl_text(i18n, "events.line", {
                "events": counts.get("events"),
                "confirmed": counts.get("verified"),
                "candidates": counts.get("candidates"),
                "status": ev_block.get("status") or ""})))
        e_md.append("Disclosure events: %s (%s confirmed, %s "
                    "candidates) · status: %s"
                    % (counts.get("events"), counts.get("verified"),
                       counts.get("candidates"),
                       ev_block.get("status")))
        if ev_block.get("reason"):
            e_html.append('<p %s>%s</p>' % (
                tpl_attrs("events.reason", {
                    "reason": ev_block.get("reason")}),
                tpl_text(i18n, "events.reason", {
                    "reason": ev_block.get("reason")})))
            e_md.append("Reason: %s" % ev_block.get("reason"))
        if ev_block.get("status") == "valid" \
                and not (ev_block.get("events") or []):
            e_html.append('<p data-i18n="events.empty">%s</p>'
                          % esc(i18n["events.empty"]["en"]))
            e_md.append(i18n["events.empty"]["en"])
        for event in (ev_block.get("events") or [])[:22]:
            etype = event.get("event_type") or ""
            type_span = display_span(i18n, "event-type", etype, log)
            announced = (event.get("announced") or {}).get("value")
            verified = event.get("verification_status") == "verified"
            status_key = "events.confirmed" if verified \
                else "events.not-confirmed"
            status_en = i18n[status_key]["en"]
            status_span = ('<span data-i18n="%s">%s</span>'
                           % (esc(status_key), esc(status_en)))
            doc_id = event.get("source_document_id") or ""
            url = event.get("source_url") or ""
            rev = (event.get("document_revision_id") or "")
            meta_en = "Announced %s · %s · Source: %s · %s" % (
                announced or "?", status_en, doc_id,
                rev.replace("clipped-body-sha256:", "doc-sha256:")[:28])
            summary_en = event.get("summary_en") or ""
            summary_ar = event.get("summary_ar") or ""
            head = "%s %s" % (type_span, esc(summary_en)) \
                if summary_en else "%s %s" % (type_span, esc(doc_id))
            e_html.append("<p>%s</p>" % head)
            if summary_ar:
                e_html.append('<p lang="ar" dir="rtl">%s</p>'
                              % esc(summary_ar))
            if url:
                source_text = tpl_text(i18n, "events.source", {
                    "doc": doc_id}).replace(
                        esc(doc_id),
                        '<a href="%s">%s</a>' % (esc(url), esc(doc_id)))
                meta_html = ('<span %s>%s</span> · %s · <span %s>%s</span> · %s'
                             % (tpl_attrs("events.announced", {
                                 "date": announced or "?"}),
                                tpl_text(i18n, "events.announced", {
                                    "date": announced or "?"}),
                                status_span,
                                tpl_attrs("events.source", {
                                    "doc": doc_id}),
                                source_text,
                                esc(rev.replace(
                                    "clipped-body-sha256:",
                                    "doc-sha256:")[:28])))
            else:
                meta_html = esc(meta_en)
            e_html.append("<p>%s</p>" % meta_html)
            e_md.append("- [%s] %s" % (etype, summary_en or doc_id))
            if summary_ar:
                e_md.append("  - %s" % summary_ar)
            e_md.append("  - %s" % meta_en)
            reasons = event.get("candidate_reasons") or []
            if reasons:
                # Label toggles EN/AR; the reasons are extractor
                # data and render verbatim, like news titles.
                e_html.append('<p><span data-i18n="events.candidate-label">%s</span> — %s</p>'
                              % (esc(i18n["events.candidate-label"]["en"]),
                                 esc("; ".join(reasons))))
                e_md.append("  - candidate: %s" % "; ".join(reasons))
    sections.append(("events", "sec.events", "\n".join(e_html),
                     "\n".join(e_md)))

    # §9 sentiment + fundamentals.
    s_html, s_md = [], ["## Sentiment + fundamentals"]
    by_tool = {t.get("tool"): t for t in tools}
    nd = by_tool.get("news-disclosure")
    if nd and isinstance(nd.get("summary"), dict):
        m = nd["summary"].get("metrics") or {}
        for key in ("finbert_negative", "finbert_positive", "multilingual_positive",
                    "multilingual_negative", "translated_positive", "translated_negative"):
            if key in m and m[key] is not None:
                s_html.append("<p>%s: <span class=\"num\">%s</span></p>" % (esc(key), fmt_conf(m[key])))
                s_md.append("- %s: %s" % (key, fmt_conf(m[key])))
    for fam in ("finbert", "finbert-tone", "financial-roberta"):
        ft = by_tool.get(fam)
        if ft and isinstance(ft.get("summary"), dict):
            label = ft["summary"].get("label")
            if label:
                val_html = display_span(i18n, "sentiment-label", label, log)
            else:
                val_html = esc(str(ft["summary"].get("model") or ""))
            s_html.append("<p>%s: %s</p>" % (esc(fam), val_html))
            s_md.append("- %s: %s" % (fam, ft["summary"].get("label") or ft["summary"].get("model") or ""))
    ftool = by_tool.get("financetoolkit")
    if ftool and isinstance(ftool.get("summary"), dict):
        company = ftool["summary"].get("company") or ""
        s_html.append('<p %s>%s</p>' % (
            tpl_attrs("sentiment.company", {"company": company}),
            tpl_text(i18n, "sentiment.company", {"company": company})))
        s_md.append("Company: %s" % (ftool["summary"].get("company") or ""))
        s_html.append('<p data-i18n="fund.ratios">Valuation ratios are not carried in the model — no corrected-valuation callout in this report.</p>')
        s_md.append("Valuation ratios are not carried in the model — no corrected-valuation callout in this report.")
    sections.append(("sentiment", "sec.sentiment", "\n".join(s_html), "\n".join(s_md)))

    # §10 risks.
    risk = model.get("risk") or {}
    r_html, r_md = [], ["## Risks"]
    level = risk.get("level")
    if level == "unknown":
        r_html.append('<p data-i18n="risk.unknown">Risk level unknown — the news tool was missing or failed; not “no risk”.</p>')
        r_md.append("Risk level unknown — the news tool was missing or failed; not “no risk”.")
    else:
        cap = risk.get("conf_cap")
        cap_text = fmt_conf(cap) if cap is not None else "not recorded"
        r_html.append('<p %s>%s</p>' % (
            tpl_attrs("risk.level", {"level": level, "cap": cap_text},
                      {"level": "risk", "cap": "sentinel"}),
            tpl_text(i18n, "risk.level", {"level": level, "cap": cap_text})))
        r_md.append("Risk level: %s · confidence cap: %s" % (
            level, fmt_conf(cap) if cap is not None else "not recorded"))
    for flag in risk.get("flags") or []:
        r_html.append(render_risk_flag(i18n, flag, log))
        r_md.append("- %s" % flag)
    for ev in risk.get("events") or []:
        title = ev.get("title") if isinstance(ev, dict) else str(ev)
        r_html.append("<p>%s</p>" % esc(title))
        r_md.append("- %s (truncated title — see the archived news file for full text)" % title)
    for ca in model.get("corporate_actions") or []:
        r_html.append('<p %s>%s</p>' % (
            tpl_attrs("risk.corporate", {
                "type": ca.get("type") or ca.get("action") or "",
                "ex": ca.get("ex_date"),
                "dps": ca.get("dps") or ca.get("coupon") or ""},
                {"type": "corporate"}),
            tpl_text(i18n, "risk.corporate", {
                "type": ca.get("type") or ca.get("action") or "",
                "ex": ca.get("ex_date"),
                "dps": ca.get("dps") or ca.get("coupon") or ""})))
        r_md.append("- Corporate action: %s · ex-date: %s · DPS: %s" % (
            ca.get("type") or ca.get("action") or "", ca.get("ex_date"),
            ca.get("dps") or ca.get("coupon") or ""))
    kxr = model.get("kronos_ex_rescale")
    if kxr is None:
        r_html.append('<p data-i18n="rescale.none">Kronos ex-date rescale state not recorded.</p>')
        r_md.append("Kronos ex-date rescale state not recorded.")
    elif isinstance(kxr, dict) and kxr.get("applied"):
        r_html.append('<p %s>%s</p>' % (
            tpl_attrs("risk.rescale.applied", {"factor": kxr.get("factor")}),
            tpl_text(i18n, "risk.rescale.applied", {"factor": kxr.get("factor")})))
        r_md.append("Rescale applied: factor %s" % kxr.get("factor"))
    else:
        r_html.append('<p %s>%s</p>' % (
            tpl_attrs("risk.rescale.attempted", {"reason": (kxr or {}).get("reason")}),
            tpl_text(i18n, "risk.rescale.attempted", {"reason": (kxr or {}).get("reason")})))
        r_md.append("Rescale attempted, did not apply — %s" % (kxr or {}).get("reason"))
    sections.append(("risks", "sec.risks", "\n".join(r_html), "\n".join(r_md)))

    # §11 price chart + Kronos cone (IR-3 fallback I-5; else table).
    # Only the base source's tail is plotted: the other price sources
    # are the same stale series, and plotting every CSV would mix in
    # reference-workload rows. The caption carries no numbers (plotted
    # points are data, not narrative — §5).
    c_html, c_md = [], ["## Price chart"]
    psl_sources = {r.get("source") for r in psl if r.get("source")}
    tails = read_price_tail(sweep_dir, psl_sources) if sweep_dir else {}
    forecast = read_kronos_forecast(sweep_dir) if sweep_dir else None
    base_src = (model.get("price") or {}).get("base_source")
    chart_tails = {base_src: tails[base_src]} if base_src in tails else {}
    # Issue #258: history source, usable-point count and forecast
    # presence are separate facts. A forecast-only SVG used to
    # carry the same "price tail + forecast cone" caption and the
    # same chart flag as a real price chart, hiding absent history
    # from any check on the chart flag alone.
    history_points = sum(len(rows) for rows in chart_tails.values())
    if chart_tails or forecast:
        c_html.append(_svg_chart(chart_tails, forecast, price, i18n))
        if chart_tails:
            c_md.append("Chart: %s price tail (%d points) + Kronos "
                        "forecast cone (see HTML)."
                        % (base_src, history_points))
        else:
            c_md.append("Chart: Kronos forecast cone only — no usable "
                        "price history (see HTML).")
        for row in psl:
            close = row.get("last_close")
            cell = fmt_price(close) if close is not None else "no close"
            c_md.append("- %s: last %s on %s" % (row.get("source"), cell, row.get("last_date")))
        if forecast:
            c_md.append("- Kronos forecast: %s points, last %s at %s" % (
                len(forecast), fmt_price(forecast[-1][1]), forecast[-1][0]))
    else:
        c_html.append('<p data-i18n="chart.table">Chart data unavailable — price-series table instead.</p>')
        c_md.append("Chart data unavailable — price-series table instead.")
        for row in psl:
            close = row.get("last_close")
            cell = fmt_price(close) if close is not None else "no close"
            c_md.append("- %s: %s on %s" % (row.get("source"), cell, row.get("last_date")))
    sections.append(("chart", "sec.chart", "\n".join(c_html), "\n".join(c_md)))

    # §12 LLM provenance.
    l_html, l_md = [], ["## LLM provenance"]
    llm = model.get("llm") or {}
    status = llm.get("llm_status")
    if status == "not-recorded" or not llm:
        l_html.append('<p data-i18n="llm.none">Model not recorded (pre-#74 run).</p>')
        l_md.append("Model not recorded (pre-#74 run).")
    else:
        for call in llm.get("calls") or []:
            l_html.append('<p %s>%s</p>' % (
                tpl_attrs("llm.call", {
                    "tool": call.get("tool"),
                    "role": call.get("role"),
                    "model": call.get("model") or "not recorded",
                    "tin": call.get("tokens_in") or "not recorded",
                    "tout": call.get("tokens_out") or "not recorded",
                    "usd": call.get("usd") or "not recorded"},
                    {"role": "llm-role", "model": "sentinel",
                     "tin": "sentinel", "tout": "sentinel",
                     "usd": "sentinel"}),
                tpl_text(i18n, "llm.call", {
                    "tool": call.get("tool"),
                    "role": call.get("role"),
                    "model": call.get("model") or "not recorded",
                    "tin": call.get("tokens_in") or "not recorded",
                    "tout": call.get("tokens_out") or "not recorded",
                    "usd": call.get("usd") or "not recorded"})))
            l_md.append("- %s · %s · model: %s" % (
                call.get("tool"), call.get("role"), call.get("model") or "not recorded"))
    sections.append(("llm", "sec.llm", "\n".join(l_html), "\n".join(l_md)))

    # §13 weights provenance / ledger pin.
    lp = model.get("ledger_pin") or {}
    counts = lp.get("counts") or {}
    w_html, w_md = [], ["## Ledger pin"]
    w_html.append('<p %s>%s</p>' % (
        tpl_attrs("ledger.counts", {
            "s": counts.get("sweeps"), "f": counts.get("forecasts"),
            "m": counts.get("matured"), "p": counts.get("pending"),
            "i": counts.get("invalid")}),
        tpl_text(i18n, "ledger.counts", {
            "s": counts.get("sweeps"), "f": counts.get("forecasts"),
            "m": counts.get("matured"), "p": counts.get("pending"),
            "i": counts.get("invalid")})))
    w_md.append("Ledger counts — sweeps: %s · forecasts: %s · matured: %s · pending: %s · invalid: %s" % (
        counts.get("sweeps"), counts.get("forecasts"), counts.get("matured"),
        counts.get("pending"), counts.get("invalid")))
    matured = counts.get("matured")
    w_html.append('<p %s>%s</p>' % (
        tpl_attrs("ledger.accuracy", {"n": matured}),
        tpl_text(i18n, "ledger.accuracy", {"n": matured})))
    w_md.append("No accuracy figure is published until n ≥ 30 matured forecasts (n = %s)." % matured)
    if lp.get("weights_sha_matches_ensemble") is False:
        w_html.append('<p class="flag" data-i18n="ledger.weights-changed">Weights changed since this sweep — the forecast stands on the pinned weights.</p>')
        w_md.append("Weights changed since this sweep — the forecast stands on the pinned weights.")
    sections.append(("ledger", "sec.ledger", "\n".join(w_html), "\n".join(w_md)))

    # §14 data-quality flags.
    f_html, f_md = [], ["## Data-quality flags"]
    flags = model.get("flags") or []
    if not flags:
        f_html.append('<p data-i18n="flags.none">No data-quality flags raised.</p>')
        f_md.append("No data-quality flags raised.")
    for flag in flags:
        f_html.append(render_flag(i18n, flag, log))
        f_md.append("- %s" % flag)
    for mm in model.get("ticker_mismatch") or []:
        f_html.append('<p class="flag" %s>%s</p>' % (
            tpl_attrs("flags.ticker-mismatch", {"value": mm}),
            tpl_text(i18n, "flags.ticker-mismatch", {"value": mm})))
        f_md.append("- Ticker mismatch: %s" % mm)
    for cf in model.get("coercion_failed") or []:
        f_html.append('<p class="flag" %s>%s</p>' % (
            tpl_attrs("flags.coercion-failed", {"value": cf}),
            tpl_text(i18n, "flags.coercion-failed", {"value": cf})))
        f_md.append("- Coercion failed: %s" % cf)
    degraded = model.get("degraded")
    if degraded:
        f_html.append('<p class="flag" %s>%s</p>' % (
            tpl_attrs("flags.degraded", {"value": str(degraded)}),
            tpl_text(i18n, "flags.degraded", {"value": str(degraded)})))
        f_md.append("Degraded: %s" % degraded)
    sections.append(("flags", "sec.flags", "\n".join(f_html), "\n".join(f_md)))

    # §15 provenance + disclaimer footer.
    prov = model.get("provenance") or {}
    p_html, p_md = [], ["## Provenance"]
    merged_by = prov.get("merged_by") or ""
    p_html.append('<p %s>%s</p>' % (
        tpl_attrs("prov.line", {
            "merged": merged_by,
            "compiler": prov.get("compiler") or "",
            "schema": model.get("schema")}, {"merged": "merged-by"}),
        tpl_text(i18n, "prov.line", {
            "merged": merged_by,
            "compiler": prov.get("compiler") or "",
            "schema": model.get("schema")})))
    p_md.append("Provenance: merged by %s · compiler: %s · model: %s" % (
        prov.get("merged_by") or "", prov.get("compiler") or "", model.get("schema")))
    p_html.append('<p><span data-i18n="prov.viewer">Viewer:</span> <span class="watermark">&lt;unassigned&gt;</span></p>')
    p_md.append("Viewer: <unassigned>")
    sections.append(("provenance", "sec.provenance", "\n".join(p_html), "\n".join(p_md)))

    # Narrative slots (I-4): audited, rendered, never auto-filled.
    slot_html, slot_md = [], []
    if narrative:
        slots = narrative.get("slots") or []
        known = {"summary", "risks_note", "sentiment_note"}
        for slot in slots:
            sid = slot.get("id")
            if sid not in known:
                log.append("narrative_slot_ignored: unknown id %r" % sid)
                continue
            text = slot.get("text") or ""
            max_chars = slot.get("max_chars") or 2000
            if len(text) > max_chars:
                text = text[:max_chars] + " [truncated]"
                log.append("narrative_slot_truncated: %s" % sid)
            audit_narrative(text, numbers, dates, "narrative.%s" % sid)
            slot_html.append('<p class="slot">%s</p>' % esc(text))
            slot_md.append(text)
    return sections, numbers, dates, log, slot_html, slot_md, quoted, derived_claims


def _looks_arabic(text):
    return any("\u0600" <= ch <= "\u06ff" for ch in text)


def _svg_chart(tails, forecast, price, i18n):
    """Inline SVG line chart: price tails (solid) + Kronos forecast (dashed)."""
    points = []
    for src, rows in tails.items():
        points += [(d, c) for d, c in rows]
    if forecast:
        points += list(forecast)
    if not points:
        return '<p data-i18n="chart.unavailable">Chart data unavailable.</p>'
    closes = [c for _, c in points]
    lo, hi = min(closes), max(closes)
    if hi - lo < 1e-9:
        hi = lo + 1.0
    width, height = 720, 260
    pad = 8
    n = len(points)
    def xy(i, val):
        x = pad + (width - 2 * pad) * (i / max(n - 1, 1))
        y = pad + (height - 2 * pad) * (1 - (val - lo) / (hi - lo))
        return x, y
    lines = []
    # One polyline per tail series, then the forecast as a dashed line.
    idx = 0
    for src, rows in sorted(tails.items()):
        pts = " ".join("%.1f,%.1f" % xy(idx + j, c) for j, (_, c) in enumerate(rows))
        lines.append('<polyline points="%s" fill="none" stroke="#2563eb" stroke-width="1.5"/>' % pts)
        idx += len(rows)
    if forecast:
        pts = " ".join("%.1f,%.1f" % xy(idx + j, c) for j, (_, c) in enumerate(forecast))
        lines.append('<polyline points="%s" fill="none" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="5 4"/>' % pts)
    return ('<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="%s" data-i18n-aria="%s">%s</svg>'
            '<p class="dim" data-i18n="chart.legend">Solid: recorded closes; dashed: Kronos forecast.</p>'
            % (width, height,
               esc(i18n["chart.aria.forecast"]["en"] if not tails else i18n["chart.aria"]["en"]),
               "chart.aria.forecast" if not tails else "chart.aria",
               "".join(lines)))


# --- emitters ---------------------------------------------------------------
CSS = """
body{font-family:'IBM Plex Sans','IBM Plex Sans Arabic',system-ui,-apple-system,'Segoe UI',Tahoma,sans-serif;max-width:860px;margin:0 auto;padding:16px;color:#111;line-height:1.55}
h1{font-size:1.5em}h2{font-size:1.2em;border-top:1px solid #ddd;padding-top:12px}h3{font-size:1.05em}
table{border-collapse:collapse;margin:8px 0}th,td{border:1px solid #ccc;padding:4px 8px;text-align:left}
.num{font-variant-numeric:tabular-nums}.dim{color:#555}.flag{color:#8a1f1f}.headline{font-weight:600}
.framing{border:1px solid #888;padding:8px}.disclaimer{border:1px solid #888;padding:8px;margin:12px 0}
.watermark{opacity:.55}.banner{background:#fff3cd;border:1px solid #d9a400;padding:8px}
button{font:inherit;padding:4px 10px;margin:4px 4px 4px 0}
pre{white-space:pre-wrap;word-break:break-word;background:#f6f6f6;padding:8px}
code{font-family:ui-monospace,Menlo,monospace}
"""

TOGGLE_JS = """
var LANG='en';
function fmtTpl(tpl,args,display,t){return tpl.replace(/\\{(\\w+)\\}/g,function(m,name){var v=args[name];if(v===undefined){return m;}var kind=display[name];if(kind){var k='display.'+kind+'.'+v;if(t[k]!==undefined){return t[k];}}return v;});}
function tplArgs(el){var args={},display={};Array.prototype.slice.call(el.attributes).forEach(function(a){if(a.name.indexOf('data-tpl-')===0&&a.name!=='data-tpl-display'){args[a.name.slice(9)]=a.value;}});var spec=el.getAttribute('data-tpl-display');if(spec){spec.split(',').forEach(function(pair){var kv=pair.split(':');if(kv.length===2){display[kv[0]]=kv[1];}});}return {args:args,display:display};}
document.getElementById('langEn').addEventListener('click',function(){setLang('en')});
document.getElementById('langAr').addEventListener('click',function(){setLang('ar')});
function setLang(l){LANG=l;var t=window.I18N[l];document.documentElement.lang=l;document.documentElement.dir=(l==='ar'?'rtl':'ltr');document.querySelectorAll('[data-i18n]').forEach(function(el){var k=el.getAttribute('data-i18n');if(t[k]!==undefined){el.textContent=t[k];}});document.querySelectorAll('[data-i18n-tpl]').forEach(function(el){var k=el.getAttribute('data-i18n-tpl');if(t[k]===undefined){return;}var d=tplArgs(el);el.textContent=fmtTpl(t[k],d.args,d.display,t);});document.querySelectorAll('[data-i18n-aria]').forEach(function(el){var k=el.getAttribute('data-i18n-aria');if(t[k]!==undefined){el.setAttribute('aria-label',t[k]);}});}
document.getElementById('copyJson').addEventListener('click',function(){var s=document.getElementById('report-model').textContent;if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(s).then(function(){document.getElementById('copyMsg').textContent=window.I18N[LANG]['ui.copied'];},function(){document.getElementById('copyMsg').textContent=window.I18N[LANG]['ui.copy.failed'];});}else{document.getElementById('copyMsg').textContent=window.I18N[LANG]['ui.copy.unavailable'];}});
"""


def render_html(model, raw_model, sections, slot_html, i18n, log):
    t = model.get("ticker")
    # The data island is the model file's exact bytes; every "<" is
    # escaped at embed time only (§2e). Issue #258: escaping only the
    # exact lowercase "</script>" left mixed-case ("</ScRiPt>") and
    # whitespace ("</script >", "</ script>") closers able to
    # terminate the island. "\u003c" is a valid JSON escape, so the
    # island still parses to the identical model.
    island = raw_model.decode("utf-8").replace("<", "\\u003c")
    i18n_json = json.dumps({"en": {k: v["en"] for k, v in i18n.items()},
                            "ar": {k: v["ar"] for k, v in i18n.items()}},
                           ensure_ascii=False, sort_keys=True)
    title_args = {"ticker": t, "date": model.get("date")}
    job_args = {"job": model.get("job"), "shape": model.get("job_shape"),
                "market": model.get("market") or "no market filter"}
    model_args = {"schema": model.get("schema"),
                  "sweep": model.get("sweep_dir"),
                  "commit": model.get("archive_commit") or "not recorded"}
    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en" dir="ltr">')
    parts.append("<head><meta charset=\"utf-8\">")
    parts.append('<title %s>%s</title>' % (
        tpl_attrs("ui.title", title_args),
        tpl_text(i18n, "ui.title", title_args)))
    parts.append('<link rel="icon" href="data:,">')
    parts.append("<style>%s</style></head>" % CSS)
    parts.append("<body>")
    parts.append('<p><button id="langEn" type="button">English</button>'
                 '<button id="langAr" type="button">العربية</button>'
                 '<button id="copyJson" type="button" data-i18n="ui.copy">Copy model JSON</button>'
                 '<span id="copyMsg"></span></p>')
    if model.get("partial") or model.get("ensemble_absent"):
        parts.append('<p class="banner" data-i18n="banner.partial">Partial sweep — forecast sections are not available for this sweep.</p>')
    degraded = model.get("degraded")
    if degraded:
        parts.append('<p class="banner" %s>%s</p>' % (
            tpl_attrs("flags.degraded", {"value": str(degraded)}),
            tpl_text(i18n, "flags.degraded", {"value": str(degraded)})))
    parts.append('<div class="disclaimer"><p data-i18n="disclaimer.short">%s</p></div>'
                 % esc(i18n["disclaimer.short"]["en"]))
    parts.append('<h1 %s>%s</h1>' % (
        tpl_attrs("ui.title", title_args),
        tpl_text(i18n, "ui.title", title_args)))
    parts.append('<p %s>%s</p>' % (
        tpl_attrs("header.job", job_args, {"market": "sentinel"}),
        tpl_text(i18n, "header.job", job_args)))
    parts.append('<p %s>%s</p>' % (
        tpl_attrs("header.model", model_args, {"commit": "sentinel"}),
        tpl_text(i18n, "header.model", model_args)))
    for anchor, key, body, _md in sections[1:]:
        title = i18n.get(key, {}).get("en", key)
        parts.append('<section id="%s"><h2 data-i18n="%s">%s</h2>%s</section>'
                     % (esc(anchor), esc(key), esc(title), body))
    if slot_html:
        parts.append('<section id="narrative"><h2 data-i18n="sec.narrative">Narrative</h2>%s</section>'
                     % "\n".join(slot_html))
    parts.append('<div class="disclaimer"><p data-i18n="disclaimer.short">%s</p>'
                 '<p data-i18n="disclaimer.long">%s</p></div>' % (
                     esc(i18n["disclaimer.short"]["en"]),
                     esc(i18n["disclaimer.long"]["en"])))
    parts.append('<p class="dim" data-i18n="ui.footer">Deterministic glue over the ensemble + reaction fit — '
                 'research tooling, not financial advice.</p>')
    parts.append('<script type="application/json" id="report-model">%s</script>' % island)
    parts.append("<script>window.I18N=%s;%s</script>" % (i18n_json, TOGGLE_JS))
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def render_md(model, sections, slot_md, i18n):
    lines = []
    lines.append("# Borsagator report — %s (%s)" % (model.get("ticker"), model.get("date")))
    lines.append("")
    lines.append(i18n["disclaimer.short"]["en"])
    lines.append("")
    lines.append("Job: %s · shape: %s · market: %s" % (
        model.get("job"), model.get("job_shape"),
        model.get("market") or "no market filter"))
    lines.append("Model: %s · sweep: %s · archive commit: %s" % (
        model.get("schema"), model.get("sweep_dir"),
        model.get("archive_commit") or "not recorded"))
    lines.append("")
    for _anchor, key, _html, md in sections[1:]:
        title = i18n.get(key, {}).get("en", key)
        lines.append("## %s" % title)
        lines.append("")
        lines.append(md)
        lines.append("")
    if slot_md:
        lines.append("## Narrative")
        lines.append("")
        lines.extend(slot_md)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(i18n["disclaimer.short"]["en"])
    lines.append("")
    lines.append(i18n["disclaimer.long"]["en"])
    lines.append("")
    lines.append("### Arabic disclaimer")
    lines.append("")
    lines.append(i18n["disclaimer.short"]["ar"])
    lines.append("")
    lines.append(i18n["disclaimer.long"]["ar"])
    lines.append("")
    lines.append("_Deterministic glue over the ensemble + reaction fit — research tooling, not financial advice._")
    lines.append("")
    lines.append("Viewer: <unassigned>")
    return "\n".join(lines)


# --- main -------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic report renderer (issue #69).")
    ap.add_argument("model", help="report-model.json")
    ap.add_argument("--profile", default=None, help="profiles/<TICKER>.json")
    ap.add_argument("--delta", default=None, help="delta JSON (issue #70)")
    ap.add_argument("--narrative", default=None, help="narrative slots JSON")
    ap.add_argument("--sweep-dir", default=None,
                    help="archived sweep dir (fallback I-5: report.md contents, chart CSVs)")
    ap.add_argument("--out-dir", default=None, help="output directory (default: model dir)")
    ap.add_argument("--i18n", default=None,
                    help="render_i18n.json (default: scripts/render_i18n.json)")
    args = ap.parse_args(argv)

    try:
        i18n_path = args.i18n or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "render_i18n.json")
        i18n = load_i18n(i18n_path)
        raw_model, model = load_model_bytes(args.model)
        validate_model(model)

        profile = None
        rp = model.get("reaction_profile") or {}
        if rp.get("present"):
            if not args.profile:
                raise RenderError(
                    "profile_mismatch: reaction_profile.present is true but no --profile given")
            with open(args.profile, encoding="utf-8") as fh:
                profile = json.load(fh)
            if profile.get("built_at") != rp.get("built_at"):
                raise RenderError(
                    "profile_mismatch: profile built_at %r != model %r"
                    % (profile.get("built_at"), rp.get("built_at")))
        elif args.profile:
            with open(args.profile, encoding="utf-8") as fh:
                profile = json.load(fh)

        delta = None
        if args.delta:
            try:
                with open(args.delta, encoding="utf-8") as fh:
                    delta = json.load(fh)
                if not isinstance(delta, dict):
                    raise ValueError("top level is not an object")
                if delta.get("ticker") and delta.get("ticker") != model.get("ticker"):
                    raise ValueError("ticker mismatch")
            except Exception as exc:
                print("delta_unavailable: %s" % exc, file=sys.stderr)
                delta = {"pair_invalid": "delta file unusable: %s" % exc}

        narrative = None
        if args.narrative:
            try:
                with open(args.narrative, encoding="utf-8") as fh:
                    narrative = json.load(fh)
            except Exception as exc:
                raise RenderError("narrative_unreadable: %s" % exc)

        # Canonical legal text is exempt from the prose-audit (it is the
        # framing itself, not narrative). The verbatim confidence_basis
        # string is likewise the model's own wording (§2i).
        global AUDIT_EXEMPT
        AUDIT_EXEMPT = [i18n["disclaimer.short"]["en"], i18n["disclaimer.short"]["ar"],
                        i18n["disclaimer.long"]["en"], i18n["disclaimer.long"]["ar"],
                        i18n["framing"]["en"], i18n["framing"]["ar"]]
        cb = (model.get("weights") or {}).get("confidence_basis")
        if cb:
            AUDIT_EXEMPT.append(cb)

        sections, numbers, dates, log, slot_html, slot_md, quoted, \
            derived_claims = build_view(
                model, profile, delta, narrative, args.sweep_dir, i18n)

        out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.model))
        os.makedirs(out_dir, exist_ok=True)
        html_text = render_html(model, raw_model, sections, slot_html, i18n, log)
        md_text = render_md(model, sections, slot_md, i18n)
        # The audit covers the renderer's own generated lines too (§2i).
        # Data islands, inline scripts and the SVG chart carry computed
        # coordinates, not narrative — they are stripped before the audit,
        # as are verbatim quoted tool reports (data, not narrative).
        visible = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
        visible = re.sub(r"<style.*?</style>", " ", visible, flags=re.S)
        visible = re.sub(r"<svg.*?</svg>", " ", visible, flags=re.S)
        visible = re.sub(r"<[^>]+>", " ", visible)
        visible = html.unescape(visible)
        for q_html, _q_md in quoted:
            visible = visible.replace(
                html.unescape(re.sub(r"<[^>]+>", " ", q_html)), " ")
        # The whole-document audit re-verifies the derived claims too
        # (#261): the spread appears in the rendered twins, so it must
        # pass here as a traced derivation, not by registry coincidence.
        audit_narrative(visible, numbers, dates, "rendered-html",
                        derived_claims=derived_claims, model=model)
        md_audited = md_text
        for _q_html, q_md in quoted:
            md_audited = md_audited.replace(q_md, " ")
        audit_narrative(md_audited, numbers, dates, "rendered-md",
                        derived_claims=derived_claims, model=model)
        with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as fh:
            fh.write(html_text)
        with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
            fh.write(md_text)
        for line in log:
            print("render: %s" % line, file=sys.stderr)
        print("render: %s -> %s/report.html + report.md"
              % (args.model, out_dir))
        return 0
    except RenderError as exc:
        print("render refused: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("render failed: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
