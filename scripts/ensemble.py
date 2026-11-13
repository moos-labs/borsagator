#!/usr/bin/env python3
"""Borsagator ensemble synthesizer (v2).

Runs inside the Borsagator workflow right after orchestrate.py. Reads
digest/digest.json + the harvested per-tool results in collected/ and
produces ONE forecast per horizon (day / week / month).

Design (v2 — root fixes over v1):
- Tools vote by FAMILY (registry family+role), never per tool.
- Sentiment inputs are LIVE per-ticker headlines: the FinBERT trio
  fetches the day's coverage itself (fetch_headlines.py in each
  sentiment repo) — no stored samples anywhere in the chain.
- Ranges are anchored in the stock's OWN realized volatility
  (sigma = max of 60-session and 10-session daily-return stdev, from
  the price history the fleet already collects), not in the forecast
  model's self-reported bands — so intervals widen by themselves on
  shock days, because the shock is inside the recent returns.
- The price family's score is the Kronos move measured in units of
  that volatility (z-score), not an arbitrary multiplier — a +5% path
  means something different on a calm stock than on a crashing one.
- The news layer never votes direction; it is a risk overlay that
  caps confidence, discounts the price weight and stretches ranges.
- Confidence is PROVISIONAL (uncalibrated) until the scoring ledger
  (phase 2) has measured this ensemble's own history.

Deterministic, stdlib only, no LLM. Never raises.
"""
import csv, glob, json, math, os, re, sys
from datetime import datetime, timezone, date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIGEST = os.path.join(os.getcwd(), "digest", "digest.json")
COLLECTED = os.path.join(os.getcwd(), "collected")
REGISTRY = os.path.join(ROOT, "registry", "tools.json")
OUT_JSON = os.path.join(os.getcwd(), "digest", "ensemble.json")
OUT_MD = os.path.join(os.getcwd(), "digest", "digest.md")

HORIZONS = {"day": 1, "week": 5, "month": 21}
W = {
    "price-forecast": {"day": .45, "week": .40, "month": .30},
    "technicals":     {"day": .30, "week": .20, "month": .10},
    "sentiment":      {"day": .15, "week": .15, "month": .05},
    "agent":          {"day": .10, "week": .20, "month": .30},
    "fundamentals":   {"day": .00, "week": .00, "month": .25},
}
RISK_MULT = {"none": 1.0, "elevated": 1.2, "shock": 1.5, "unknown": 1.3}
SHOCK_WORDS = [
    "resign", "oust", "ceo", "earnings", "guidance", "investigat", "fraud",
    "halt", "merger", "acquisition", "dividend", "profit warning",
    "bankrupt", "lawsuit", "استقال", "إقال", "نتائج", "أرباح", "توزيع",
    "اندماج", "تحقيق", "إيقاف", "مجلس الإدارة", "جمعية عامة",
]
# Event taxonomy for the risk overlay (v2.1): a shock is an EVENT of a
# severe type, or a price move the event stream cannot explain — not a
# bag of keywords. Severity: high = shock-capable on its own; medium =
# elevated, or shock when the price confirms it.
EVENT_TYPES = [
    ("earnings", "high",
     ["earnings", "profit", "loss", "revenue", "results", "quarterly",
      "أرباح", "خسائر", "نتائج", "إيرادات", "صافي الربح", "نتائج الأعمال"]),
    ("management", "high",
     ["resign", "oust", "appoint", "ceo", "chief executive",
      "استقال", "إقال", "تعيين", "رئيس تنفيذي", "عضو منتدب"]),
    ("legal", "high",
     ["investigat", "lawsuit", "fine", "fraud", "bankrupt", "halt",
      "تحقيق", "غرامة", "احتيال", "قضية", "إفلاس", "إيقاف التداول"]),
    ("capital", "high",
     ["merger", "acquisition", "capital increase", "share split",
      "اندماج", "استحواذ", "زيادة رأس المال", "تجزئة"]),
    ("dividend", "medium",
     ["dividend", "distribution", "coupon", "توزيع", "كوبون"]),
    ("governance", "medium",
     ["board of directors", "general assembly", "agm", "egm",
      "مجلس الإدارة", "جمعية عامة", "جمعية عمومية"]),
]
RATING_MAP = {"strong buy": 1.0, "buy": .75, "overweight": .5, "hold": 0.0,
              "underweight": -.5, "sell": -.75, "strong sell": -1.0}


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def find_key(obj, needles, depth=0):
    if depth > 4 or not isinstance(obj, dict):
        return None
    for k, v in obj.items():
        if any(n in k.lower() for n in needles):
            n = fnum(v)
            if n is not None:
                return n
    for v in obj.values():
        if isinstance(v, dict):
            r = find_key(v, needles, depth + 1)
            if r is not None:
                return r
    return None


def realized_sigma(ticker, base=None):
    """Daily-return stdev from collected price CSVs.
    Returns (sigma, source, density): sigma = max(sigma_60, sigma_10);
    density = trading sessions per calendar day in that series — Kronos
    emits calendar-day bars, so horizon maths must convert.
    Series choice is ANCHORED on the verified base close when known:
    among candidates whose last close sits within 25% of base, take the
    longest (a stray foreign series must not set the volatility); with
    no anchor available, fall back to the longest candidate."""
    code = re.sub(r"[^a-z0-9]", "", ticker.split(".")[0].lower())
    best = None
    anchored = None
    _reg = load_json(REGISTRY) or {}
    _cats = {t.get("id"): t.get("category") for t in _reg.get("tools", [])}
    for path in glob.glob(os.path.join(COLLECTED, "*", "*.csv")):
        name = os.path.basename(path).lower()
        # Same exclusion as price_series: validation/backtest tools run
        # reference workloads — their CSVs never enter the sigma pool.
        if _cats.get(os.path.basename(os.path.dirname(path))) in (
                "validation", "backtest"):
            continue
        if not any(s in name for s in ("ohlc", "indicators", code)):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        if len(rows) < 30:
            continue
        col = next((c for c in rows[0] if c and c.strip().lower() in
                    ("close", "adj close", "adjclose")), None)
        if not col:
            continue
        closes = [fnum(r.get(col)) for r in rows]
        dates = []
        dcol = next((c for c in rows[0] if c and ("date" in c.strip().lower()
                     or c.strip().lower() in ("datetime", "index"))), None)
        if dcol:
            for r in rows:
                s = str(r.get(dcol) or "")[:10]
                try:
                    dates.append(datetime.strptime(s, "%Y-%m-%d"))
                except Exception:
                    dates.append(None)
        pairs = [(c, d) for c, d in zip(closes, dates or [None] * len(closes))
                 if c and c > 0]
        closes = [c for c, _ in pairs]
        if len(closes) < 30:
            continue
        cand = (closes, [d for _, d in pairs],
                os.path.basename(os.path.dirname(path)) + "/" + name)
        if best is None or len(closes) > len(best[0]):
            best = cand
        if base and abs(closes[-1] - base) / base <= 0.25:
            if anchored is None or len(closes) > len(anchored[0]):
                anchored = cand
    if anchored is not None:
        best = anchored
    if not best:
        return 0.02, "default (no history found)", 5 / 7
    closes, dates, src = best
    density = 5 / 7
    ds = [d for d in dates if d]
    if len(ds) >= 30 and (ds[-1] - ds[0]).days > 0:
        density = min(1.0, max(0.4, (len(ds) - 1) / (ds[-1] - ds[0]).days))

    def sd(vals):
        rets = [math.log(vals[i] / vals[i - 1]) for i in range(1, len(vals))]
        if len(rets) < 5:
            return 0.0
        mu = sum(rets) / len(rets)
        return math.sqrt(sum((r - mu) ** 2 for r in rets) / len(rets))

    s60 = sd(closes[-61:])
    s10 = sd(closes[-11:])
    return max(s60, s10), f"{src} (σ60={s60:.4f}, σ10={s10:.4f})", density


def price_series(ticker):
    """Collected price series for the ticker as {source: {date: close}}
    (date '' when the CSV has no usable date column). Validation and
    backtest tools are excluded by registry category: they run
    REFERENCE workloads (their CSVs are not this ticker's series —
    vectorbt's poul_ohlc.csv ends at 3.13, quantstats' at 2.83, while
    every price-bearing tool agrees on ~10.2)."""
    code = re.sub(r"[^a-z0-9]", "", ticker.split(".")[0].lower())
    registry = load_json(REGISTRY) or {}
    cats = {t.get("id"): t.get("category")
            for t in registry.get("tools", [])}
    series = {}
    for path in glob.glob(os.path.join(COLLECTED, "*", "*.csv")):
        tool = os.path.basename(os.path.dirname(path))
        if cats.get(tool) in ("backtest", "stats"):
            continue
        name = os.path.basename(path).lower()
        if not any(s in name for s in ("ohlc", "indicators", code)):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        if len(rows) < 5:
            continue
        col = next((c for c in rows[0] if c and c.strip().lower() in
                    ("close", "adj close", "adjclose")), None)
        if not col:
            continue
        dcol = next((c for c in rows[0] if c and ("date" in c.strip().lower()
                     or c.strip().lower() in ("datetime", "index"))), None)
        out = {}
        for r in rows:
            c = fnum(r.get(col))
            if not c:
                continue
            d = ""
            if dcol:
                s = str(r.get(dcol) or "")[:10]
                try:
                    datetime.strptime(s, "%Y-%m-%d")
                    d = s
                except Exception:
                    d = ""
            out[d or f"row{len(out)}"] = c
        if out:
            src = os.path.basename(os.path.dirname(path)) + "/" + name
            series[src] = out
    return series


def price_crosscheck(ticker, base, base_src, series):
    """Two-source verification of the price the forecast stands on
    (audit item: Yahoo was the single artery, with corrupted segments).
    Witnesses: the base from the digest metrics + the last close of
    every collected price series, aligned on the latest date at least
    two dated series share. A spread above 2% means the sources
    disagree: the ensemble then stands on the EGX-native series
    (egx-data) when present, else the median witness, and the digest
    says so out loud."""
    witnesses = {}
    if base:
        witnesses[f"metrics:{base_src}"] = base
    dated = {s: m for s, m in series.items()
             if any(len(k) == 10 and k[4] == "-" for k in m)}
    common = None
    if len(dated) >= 2:
        sets = [set(m.keys()) for m in dated.values()]
        inter = set.intersection(*sets) if sets else set()
        real = sorted(d for d in inter if len(d) == 10 and d[4] == "-")
        common = real[-1] if real else None
    for src, m in series.items():
        if common and common in m:
            witnesses[src] = m[common]
        else:
            witnesses[src] = m[sorted(m.keys())[-1]]
    # Deduplicate by TOOL: a tool's own collected series supersedes its
    # digest metric — the same underlying data must not vote twice
    # (Ins review, issue #49).
    series_tools = {src.split("/")[0] for src in witnesses if "/" in src}
    witnesses = {k: v for k, v in witnesses.items()
                 if not (k.startswith("metrics:")
                         and k.split(":", 1)[1] in series_tools)}
    vals = sorted(witnesses.values())
    if len(vals) < 2:
        return {"status": "single-source", "witnesses": witnesses,
                "spread_pct": None, "common_date": common,
                "base_used": base, "base_source_used": base_src}
    # Cluster the witnesses (2% chaining): the largest cluster is the
    # consensus. A lone outlier series must not veto four agreeing
    # sources — and the base standing OUTSIDE the consensus is exactly
    # the failure this check exists to catch.
    ordered = sorted(witnesses.items(), key=lambda kv: kv[1])
    clusters = [[ordered[0]]]
    for item in ordered[1:]:
        if item[1] <= clusters[-1][-1][1] * 1.02:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    consensus = max(clusters, key=len)
    cons = dict(consensus)
    outliers = {s: v for s, v in witnesses.items() if s not in cons}
    cvals = sorted(cons.values())
    spread = (cvals[-1] - cvals[0]) / cvals[len(cvals) // 2] \
        if cvals[len(cvals) // 2] else 0.0
    base_key = f"metrics:{base_src}"
    base_in_cons = (base_key in cons
                    or any(s.split("/")[0] == base_src for s in cons))
    if base_in_cons and len(consensus) >= 2:
        return {"status": "agree", "witnesses": witnesses,
                "outliers": outliers,
                "spread_pct": round(spread * 100, 2), "common_date": common,
                "base_used": base, "base_source_used": base_src}
    egx = next((s for s in cons if s.startswith("egx-data/")), None)
    if egx:
        chosen, chosen_src = cons[egx], egx
    else:
        chosen = cvals[len(cvals) // 2]
        chosen_src = "consensus median"
    gap = abs(base - chosen) / chosen if chosen else 0.0
    return {"status": "disagree", "witnesses": witnesses,
            "outliers": outliers,
            "spread_pct": round(gap * 100, 2), "common_date": common,
            "base_used": chosen, "base_source_used": chosen_src}


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4,
           "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8,
           "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11,
           "ديسمبر": 12, "january": 1, "february": 2, "march": 3,
           "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
           "september": 9, "october": 10, "november": 11, "december": 12}
_DIV_WORDS = ("كوبون", "توزيع", "dividend", "coupon")


def _norm_digits(s):
    return str(s).translate(_AR_DIGITS)


def _find_dates(text, default_year):
    """All (date, context_window) pairs in a text: numeric d/m/Y,
    '15 نوفمبر 2026', '15 November 2026', 'November 15, 2026'."""
    t = _norm_digits(text)
    found = []
    for m in re.finditer(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", t):
        try:
            found.append((date(int(m.group(3)), int(m.group(2)),
                               int(m.group(1))),
                          t[max(0, m.start() - 40):m.start()]))
        except ValueError:
            pass
    low = t.lower()
    for name, mon in _MONTHS.items():
        for m in re.finditer(r"(\d{1,2})\s+" + re.escape(name) +
                             r"(?:\s+(\d{4}))?", low):
            try:
                found.append((date(int(m.group(2) or default_year), mon,
                                   int(m.group(1))),
                              low[max(0, m.start() - 40):m.start()]))
            except ValueError:
                pass
        for m in re.finditer(re.escape(name) +
                             r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", low):
            try:
                found.append((date(int(m.group(2)), mon, int(m.group(1))),
                              low[max(0, m.start() - 40):m.start()]))
            except ValueError:
                pass
    return found


def detect_corporate_actions(items, base, default_year):
    """Dividend announcements in the collected items. Conservative by
    design: an amount is only trusted next to dividend wording, an
    ex-date only next to entitlement/ex wording (a payout date is NOT
    an ex-date). A miss records nothing — scoring-time re-detection on
    the archived items remains possible; a false positive would poison
    the ledger, so precision beats recall here."""
    actions = []
    for it in items:
        text = (str(it.get("title") or "") + " "
                + str(it.get("body") or "")[:1500])
        low = _norm_digits(text).lower()
        if not any(w in low for w in _DIV_WORDS):
            continue
        dps = None
        for pat in (r"بواقع\s*(\d+(?:\.\d+)?)",
                    r"(\d+(?:\.\d+)?)\s*(?:جنيه|جنيها|egp)\s*(?:للسهم|/share|per share)?",
                    r"(?:dividend|coupon)\s*(?:of\s*)?(?:egp\s*)?(\d+(?:\.\d+)?)"):
            m = re.search(pat, low)
            if m:
                dps = float(m.group(1))
                break
        if dps is None or base <= 0 or not (0 < dps < base):
            continue
        ex_date, basis = None, None
        item_year = None
        try:
            item_year = int(str(it.get("date") or "")[:4]) or None
        except Exception:
            item_year = None
        dates = _find_dates(text, item_year or default_year)
        for d, ctx in dates:
            if any(w in ctx for w in ("نهاية الحق", "استحقاق", "entitlement")):
                ex_date, basis = d + timedelta(days=1), "entitlement+1"
                break
            if "ex-" in ctx or "ex date" in ctx or "خارج" in ctx:
                ex_date, basis = d, "ex-date"
                break
        if ex_date is None and dates:
            # Item-level fallback: disclosure titles put «نهاية الحق»
            # far from the date — if the item speaks of entitlement and
            # never of payout, its lone date is the entitlement end.
            has_ent = any(w in low for w in ("نهاية الحق", "استحقاق", "entitlement"))
            has_pay = any(w in low for w in ("صرف", "payment", "يوزع يوم"))
            if has_ent and not has_pay:
                ex_date = dates[0][0] + timedelta(days=1)
                basis = "entitlement+1"
        key = (dps, ex_date.isoformat() if ex_date else None)
        if any((a["dps"], a["ex_date"]) == (key[0], key[1]) for a in actions):
            continue
        # A dated detection supersedes an undated one for the same DPS.
        if ex_date is not None:
            actions = [a for a in actions
                       if not (a["dps"] == dps and a["ex_date"] is None)]
        elif any(a["dps"] == dps and a["ex_date"] is not None for a in actions):
            continue
        actions.append({
            "type": "dividend", "dps": dps,
            "ex_date": ex_date.isoformat() if ex_date else None,
            "date_basis": basis,
            "mechanical_pct": round(-dps / base * 100, 2),
            "title": str(it.get("title") or "")[:90]})
    return actions


def main():
    digest = load_json(DIGEST)
    if not digest:
        print("ensemble: no digest.json — skipping")
        return
    ticker = (digest.get("ticker") or "").upper()
    results = {r["tool"]: r for r in digest.get("results", [])
               if isinstance(r, dict) and r.get("tool")}

    def metrics(tool):
        r = results.get(tool) or {}
        return ((r.get("summary") or {}).get("metrics")) or {}

    def ok(tool):
        return (results.get(tool) or {}).get("status") == "ok"

    # ---------- base price ----------
    base, base_src = None, ""
    for tool in ("pandas-ta", "talib"):
        m = metrics(tool)
        if ok(tool) and fnum(m.get("close")) and (m.get("ticker", ticker) == ticker):
            base, base_src = fnum(m["close"]), tool
            break
    if base is None:
        for tool in results:
            if not ok(tool):
                continue
            for k, v in metrics(tool).items():
                if k.endswith("_last_close") and ticker.replace(".", "_") in k.upper().replace(".", "_"):
                    base, base_src = fnum(v), tool
                    break
            if base:
                break
    if not base:
        print("ensemble: no base price found — skipping")
        return

    # ---------- two-source price verification ----------
    check = price_crosscheck(ticker, base, base_src, price_series(ticker))
    if check["status"] == "disagree":
        print(f"ensemble: PRICE SOURCES DISAGREE (spread "
              f"{check['spread_pct']}%): {check['witnesses']} — "
              f"standing on {check['base_source_used']}")
        base, base_src = check["base_used"], check["base_source_used"]

    sigma, sigma_src, density = realized_sigma(ticker, base)

    # ---------- Kronos path ----------
    kronos_path = []
    kcsv = os.path.join(COLLECTED, "kronos", "forecast.csv")
    if os.path.exists(kcsv):
        try:
            with open(kcsv, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    c, h, l = fnum(row.get("close")), fnum(row.get("high")), fnum(row.get("low"))
                    if c:
                        kronos_path.append((c, h or c, l or c))
        except Exception:
            kronos_path = []
    if not kronos_path and ok("kronos"):
        last = fnum(metrics("kronos").get("forecast.csv_last_close"))
        if last:
            kronos_path = [(last, last, last)] * 10

    def kronos_at(bar):
        if not kronos_path:
            return None
        i = min(bar, len(kronos_path)) - 1
        c, h, l = kronos_path[i]
        return {"close": c, "move": c / base - 1.0,
                "band": max((h - l) / 2.0 / base, 0.004),
                "short": len(kronos_path) < bar}

    # ---------- technicals (pandas-ta voter) ----------
    tech = None
    if ok("pandas-ta"):
        m = metrics("pandas-ta")
        rsi, hist, adx = fnum(m.get("rsi_14")), fnum(m.get("macd_hist")), fnum(m.get("adx_14"))
        close, ema20 = fnum(m.get("close")), fnum(m.get("ema_20"))
        stoch = fnum(m.get("stoch_k"))
        if rsi is not None:
            s = 0.0
            s += .45 if rsi < 30 else .15 if rsi < 45 else 0 if rsi <= 55 else -.15 if rsi <= 70 else -.45
            if adx and adx > 40:
                s *= .55
            if hist is not None:
                s += .30 if hist > 0 else -.30
            if close and ema20:
                s += .15 if close > ema20 else -.15
            if stoch is not None:
                s += -.10 if stoch > 80 else .10 if stoch < 20 else 0
            tech = max(-1.0, min(1.0, s))

    # ---------- sentiment (live-headline trio + news FinBERT) ----------
    subs = []
    for tool in ("finbert", "finbert-tone", "financial-roberta"):
        if not ok(tool):
            continue
        d = load_json(os.path.join(COLLECTED, tool, "sentiment.json"))
        mp = (d or {}).get("mean_probabilities") or {}
        pos, neg = fnum(mp.get("positive")), fnum(mp.get("negative"))
        if pos is None and d:
            pos, neg = find_key(d, ["positive"]), find_key(d, ["negative"])
        if pos is not None and neg is not None:
            subs.append(pos - neg)
    nd = metrics("news-disclosure")
    # The news tool contributes ONE sentiment slot: the average of its
    # own legs (FinBERT on English titles, FinBERT on translated
    # Arabic, the multilingual model on Arabic) — three legs from one
    # tool must not outvote the rest of the family.
    news_legs = []
    if ok("news-disclosure"):
        for pos_k, neg_k in (("finbert_positive", "finbert_negative"),
                             ("translated_positive", "translated_negative"),
                             ("multilingual_positive", "multilingual_negative")):
            if fnum(nd.get(pos_k)) is not None:
                news_legs.append(fnum(nd[pos_k]) - fnum(nd.get(neg_k) or 0))
    if news_legs:
        subs.append(sum(news_legs) / len(news_legs))
    sentiment = (sum(subs) / len(subs)) if subs else None

    # ---------- agents ----------
    avotes = []
    if ok("tradingagents"):
        rating = str(metrics("tradingagents").get("final_rating") or "").strip().lower()
        if rating in RATING_MAP:
            avotes.append(RATING_MAP[rating])
    if ok("finrobot"):
        verdict = str(metrics("finrobot").get("verdict") or "").lower()
        if "bullish" in verdict or "buy" in verdict:
            avotes.append(.6)
        elif "bearish" in verdict or "sell" in verdict:
            avotes.append(-.6)
        elif "neutral" in verdict or "hold" in verdict:
            avotes.append(0.0)
    agent = (sum(avotes) / len(avotes)) if avotes else None

    # ---------- fundamentals (month only, ticker-checked) ----------
    fund = None
    if ok("financetoolkit"):
        comp = str(metrics("financetoolkit").get("company") or "")
        code = ticker.split(".")[0]
        if code in comp or ticker in comp or not comp:
            pe, ref = None, None

            def scan_pe(obj, ref_ctx=None, depth=0):
                """Find a P/E leaf: keys like pe_consolidated_npat_x or
                price_to_earnings, values numeric or {'value': n}.
                Sections named VALUATION_AT_<price> set the ref price."""
                nonlocal pe, ref
                if pe is not None or depth > 6:
                    return
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        m = re.search(r"valuation_at_([\d.]+)", k.lower())
                        r2 = float(m.group(1)) if m else ref_ctx
                        kl = k.lower()
                        if re.search(r"(^|_)pe(_|$)", kl) or "price_to_earnings" in kl \
                                or "price_earnings" in kl:
                            val = fnum(v) if not isinstance(v, dict) else fnum(v.get("value"))
                            if val:
                                pe, ref = val, r2
                                return
                        scan_pe(v, r2, depth + 1)
                        if pe is not None:
                            return
                elif isinstance(obj, list):
                    for v in obj:
                        scan_pe(v, ref_ctx, depth + 1)
                        if pe is not None:
                            return

            def scan_quality(obj):
                """Fallback: latest-period ROE + net margin from blocks
                like {'FY2025': {'roe_pct': {'value': 39.4}, ...}}."""
                best = {}

                def walk(o, section=""):
                    if isinstance(o, dict):
                        for k, v in o.items():
                            kl = k.lower()
                            if kl in ("roe_pct",) or "net_margin" in kl:
                                val = fnum(v) if not isinstance(v, dict) else fnum(v.get("value"))
                                if val is not None:
                                    yr = max([int(y) for y in re.findall(r"(20\d\d)", section)] or [0])
                                    cur = best.get(kl if kl == "roe_pct" else "net_margin")
                                    if cur is None or yr >= cur[0]:
                                        best[kl if kl == "roe_pct" else "net_margin"] = (yr, val)
                            walk(v, k)
                walk(obj)
                roe = best.get("roe_pct", (0, None))[1]
                nm = best.get("net_margin", (0, None))[1]
                if roe is None and nm is None:
                    return None
                s = 0.0
                if roe is not None:
                    s += .30 if roe >= 25 else .15 if roe >= 15 else 0 if roe >= 5 else -.25
                if nm is not None:
                    s += .10 if nm >= 15 else 0 if nm >= 5 else -.10
                return max(-.5, min(.5, s))

            quality = None
            for path in glob.glob(os.path.join(COLLECTED, "financetoolkit", "*.json")):
                d = load_json(path)
                if not d:
                    continue
                scan_pe(d)
                if pe:
                    break
                if quality is None:
                    quality = scan_quality(d)
            if pe and pe > 0:
                if ref:
                    pe = pe * base / ref  # rescale the file's reference price to today's base
                fund = .4 if pe < 8 else .15 if pe < 15 else -.1 if pe < 25 else -.35
            elif quality is not None:
                fund = quality

    # ---------- news risk overlay ----------
    # "none" is a MEASURED state (the news tool ran and found nothing
    # alarming). If the tool is missing or failed, the risk is UNKNOWN —
    # never silently "none": cap confidence and widen ranges instead
    # (sweep #20 printed uncapped 0.54 confidence with no overlay at all
    # after the news tool errored).
    risk = {"level": "none", "conf_cap": .60, "price_mult": 1.0, "flags": []}
    if not ok("news-disclosure"):
        risk.update(level="unknown", conf_cap=.35, price_mult=.8,
                    flags=["news overlay unavailable — risk unassessed, "
                           "confidence capped"])
    else:
        news = load_json(os.path.join(COLLECTED, "news-disclosure", "news.json")) or {}
        disc = load_json(os.path.join(COLLECTED, "news-disclosure", "disclosures.json")) or {}
        items = (disc.get("items") or []) + (news.get("items") or [])
        now = datetime.now(timezone.utc)
        fresh_disc = 0
        events = []  # (severity, type, title)
        for it in items:
            title = str(it.get("title") or "")
            dt = None
            for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(str(it.get("date") or ""), fmt).replace(tzinfo=timezone.utc)
                    break
                except Exception:
                    continue
            age = (now - dt).days if dt else 99
            if it.get("kind") == "disclosure" and age <= 3:
                fresh_disc += 1
            window = 3 if it.get("kind") == "disclosure" else 2
            if age <= window:
                # Classify on the article BODY when the runner fetched
                # it — a headline can be clickbait or boilerplate while
                # the text carries the actual event.
                text = title + " " + str(it.get("body") or "")[:600]
                low = text.lower()
                for etype, sev, words in EVENT_TYPES:
                    if any(w in low for w in words):
                        events.append((sev, etype, title[:90]))
                        break
        # Abnormal-move confirmation from the verified price series:
        # a severe event the price ignores is weaker than one it
        # confirms, and a >=2.5-sigma session is a shock on its own.
        z_last = z_max3 = 0.0
        try:
            series = price_series(ticker)
            pick = next((s for s in series if s.startswith("egx-data/")), None)
            if pick is None and series:
                pick = max(series, key=lambda s: len(series[s]))
            if pick:
                m = series[pick]
                closes = [m[d] for d in sorted(m)
                          if len(d) == 10 and d[4] == "-"]
                closes = [c for c in closes if c and c > 0]
                if len(closes) >= 4 and sigma > 0:
                    rets = [math.log(closes[i] / closes[i - 1])
                            for i in range(1, len(closes))]
                    z_last = abs(rets[-1]) / sigma
                    z_max3 = max(abs(r) for r in rets[-3:]) / sigma
        except Exception:
            pass
        high = [e for e in events if e[0] == "high"]
        med = [e for e in events if e[0] == "medium"]
        risk["events"] = [{"type": t, "severity": s, "title": ti}
                          for s, t, ti in events[:6]]
        risk["move_z"] = {"last": round(z_last, 2),
                          "max3": round(z_max3, 2)}
        if high or z_last >= 2.5 or (med and z_max3 >= 1.5):
            risk.update(level="shock", conf_cap=.30, price_mult=.5)
            risk["flags"] = [f"{t} event: {ti}" for _, t, ti in high[:3]]
            if not risk["flags"]:
                risk["flags"] = [f"abnormal move: last session "
                                 f"{z_last:.1f}σ"]
            if high and z_last >= 1.5:
                risk["flags"].append(f"price confirms: last session "
                                     f"{z_last:.1f}σ")
        elif med or z_max3 >= 1.5 or fresh_disc or len(items) >= 10:
            risk.update(level="elevated", conf_cap=.45, price_mult=.8)
            risk["flags"] = [f"{t} event: {ti}" for _, t, ti in med[:2]]
            if fresh_disc:
                risk["flags"].append(f"{fresh_disc} disclosure(s) in the last 3 days")
            if z_max3 >= 1.5:
                risk["flags"].append(f"abnormal move: {z_max3:.1f}σ in the last 3 sessions")

    # ---------- corporate actions (dividend awareness) ----------
    # A forecast that spans an ex-date contains a MECHANICAL move (the
    # price drops by ~the dividend on the ex-date) that is not a market
    # signal. Detect announced dividends in the collected items, record
    # the decomposition, and mark every horizon that spans the ex-date
    # — the calibration ledger will score those forecasts on a
    # dividend-adjusted basis instead of counting the drop as error.
    actions = []
    try:
        _news = load_json(os.path.join(COLLECTED, "news-disclosure", "news.json")) or {}
        _disc = load_json(os.path.join(COLLECTED, "news-disclosure", "disclosures.json")) or {}
        _items = (_disc.get("items") or []) + (_news.get("items") or [])
        as_of = None
        try:
            as_of = date.fromisoformat(str(digest.get("date") or "")[:10])
        except Exception:
            as_of = datetime.now(timezone.utc).date()
        actions = detect_corporate_actions(_items, base, as_of.year)
    except Exception:
        actions = []

    # ---------- combine per horizon ----------
    fam_fixed = {"technicals": tech, "sentiment": sentiment,
                 "agent": agent, "fundamentals": fund}
    out = {"tool": "forecast-ensemble", "version": 2, "ticker": ticker,
           "base_price": base, "base_source": base_src,
           "price_crosscheck": check, "corporate_actions": actions,
           "sigma_daily": round(sigma, 4), "sigma_source": sigma_src,
           "sessions_per_calendar_day": round(density, 3),
           "date": digest.get("date"), "risk": risk,
           "family_scores": {}, "horizons": {},
           "confidence_basis": "provisional (uncalibrated — no scoring history yet)"}
    fam_display = dict(fam_fixed)
    for hname, bar in HORIZONS.items():
        ka = kronos_at(bar)
        # Kronos bars are CALENDAR days; sigma is per TRADING session.
        # A horizon of `bar` calendar days contains ~bar*density sessions,
        # and it is the sessions that carry the volatility.
        h_eff = max(1, round(bar * density))
        vol_h = sigma * math.sqrt(h_eff)        # 1-sigma move over the horizon
        price_score = None
        if ka:
            price_score = max(-1.0, min(1.0, ka["move"] / (2.0 * vol_h))) if vol_h > 0 else 0.0
        fam_display["price-forecast"] = price_score
        scores, weights = {}, {}
        for fam, s in list(fam_fixed.items()) + [("price-forecast", price_score)]:
            if s is None or W[fam][hname] == 0:
                continue
            w = W[fam][hname] * (risk["price_mult"] if fam == "price-forecast" else 1.0)
            scores[fam], weights[fam] = s, w
        if not scores:
            continue
        wsum = sum(weights.values())
        net = sum(scores[f] * weights[f] for f in scores) / wsum
        var = sum(weights[f] * (scores[f] - net) ** 2 for f in scores) / wsum
        disagree = math.sqrt(var)
        kmove = ka["move"] if ka else 0.0
        expected = .6 * kmove + .4 * net * (1.28 * vol_h)
        half = max(1.28 * vol_h, ka["band"] if ka else 0.0) \
            * RISK_MULT[risk["level"]] * (1 + .5 * disagree)
        agree = max(0.0, 1.0 - disagree)
        conf = min(risk["conf_cap"], .20 + .45 * agree + .10 * (len(scores) / 5))
        out["horizons"][hname] = {
            "direction": "up" if expected > .0075 else "down" if expected < -.0075 else "flat",
            "expected_move_pct": round(expected * 100, 2),
            "range_low_pct": round((expected - half) * 100, 2),
            "range_high_pct": round((expected + half) * 100, 2),
            "confidence": round(conf, 2),
            "net_score": round(net, 3),
            "families": {f: round(scores[f], 3) for f in scores},
            "horizon_short": bool(ka and ka["short"]),
            "trading_sessions": h_eff,
        }
        # Mark horizons spanning an ex-date: the mechanical dividend
        # drop inside them is decomposed, not forecast skill/error.
        for a in actions:
            if a.get("ex_date"):
                try:
                    ex = date.fromisoformat(a["ex_date"])
                except Exception:
                    continue
                if as_of < ex <= as_of + timedelta(days=bar):
                    out["horizons"][hname]["corporate_action"] = {
                        "type": a["type"], "dps": a["dps"],
                        "ex_date": a["ex_date"],
                        "mechanical_pct": a["mechanical_pct"]}
    out["family_scores"] = {k: (round(v, 3) if v is not None else None)
                            for k, v in fam_display.items()}

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    lines = ["", "---", "", "## 🎯 Ensemble forecast (synthesizer v2)", "",
             f"Base price {base} ({base_src}). Daily volatility σ {sigma:.2%} ({sigma_src}). "
             f"Kronos bars are calendar days — horizons are scaled to trading sessions "
             f"(density {density:.2f}/day). "
             f"News risk: **{risk['level']}**"
             + ((" — " + "; ".join(risk["flags"])) if risk["flags"] else "") + ".",
             "Ranges are anchored in realized volatility. Confidence is provisional "
             "(uncalibrated) until the scoring ledger has history.", ""]
    if check["status"] == "disagree":
        wit = ", ".join(f"{s} {v:g}" for s, v in check["witnesses"].items())
        lines += [f"⚠️ **Price sources disagree** (spread {check['spread_pct']}%: "
                  f"{wit}) — this forecast stands on {check['base_source_used']} "
                  f"= {check['base_used']:g}.", ""]
    for a in actions:
        if a.get("ex_date"):
            lines += [f"💰 **Corporate action:** dividend {a['dps']:g}/share, "
                      f"ex-date {a['ex_date']} — a mechanical "
                      f"≈ {a['mechanical_pct']:+.2f}% move is expected on the "
                      f"ex-date (not a market signal). Horizons spanning it "
                      f"are marked; the calibration ledger will score them "
                      f"dividend-adjusted.", ""]
    lines += [
             "| Horizon | Direction | Expected | Range | Confidence |",
             "|---|---|---|---|---|"]
    for hname in ("day", "week", "month"):
        h = out["horizons"].get(hname)
        if not h:
            continue
        arrow = {"up": "⬆ up", "down": "⬇ down", "flat": "➡ flat"}[h["direction"]]
        note = " (fleet horizon)" if h["horizon_short"] else ""
        if h.get("trading_sessions") and h["trading_sessions"] != HORIZONS[hname]:
            note += f" (≈{h['trading_sessions']} sessions)"
        if h.get("corporate_action"):
            note += (f" (incl. {h['corporate_action']['mechanical_pct']:+.1f}% "
                     f"mechanical ex-dividend)")
        lines.append(f"| {hname}{note} | {arrow} | {h['expected_move_pct']:+.2f}% | "
                     f"{h['range_low_pct']:+.2f}% … {h['range_high_pct']:+.2f}% | {h['confidence']:.2f} |")
    lines += ["", "Family scores (−1…+1): " + ", ".join(
        f"{k} {v:+.2f}" if v is not None else f"{k} —" for k, v in fam_display.items()) + ".",
        "Verdicts are combined by family, weighted by horizon; disagreement widens "
        "the range instead of being averaged away."]
    with open(OUT_MD, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("ensemble v2: written for", ticker, "| sigma", round(sigma, 4),
          "| horizons:", list(out["horizons"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ensemble failed (non-fatal):", e)
        # Never fail SILENTLY: leave a sentinel next to the digest and a
        # visible warning in it, so a missing ensemble is noticed.
        try:
            ddir = os.path.dirname(OUT_JSON)
            os.makedirs(ddir, exist_ok=True)
            with open(os.path.join(ddir, "ensemble_error.txt"), "w") as f:
                f.write(f"ensemble failed: {type(e).__name__}: {e}\n")
            if os.path.exists(OUT_MD):
                with open(OUT_MD, "a") as f:
                    f.write("\n## ⚠️ Ensemble failed — see ensemble_error.txt; "
                            "this digest has NO ensemble forecast.\n")
        except Exception:
            pass
    sys.exit(0)
