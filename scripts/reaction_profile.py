#!/usr/bin/env python3
"""Per-stock reaction profiles (issue #32).

For one ticker, walk the sweep archive and measure how the stock
actually reacted to its own past events: every archived disclosure /
news item becomes an event; the verified price series (egx-data for
EGX tickers) gives the close-to-close reaction at +1/+3/+5 sessions,
with dividend windows (from the ensembles' corporate-action blocks)
annotated and adjusted for. Aggregates by event type answer the
question the daily recommendation needs: "when THIS stock reports
earnings / declares a dividend / changes management, what does it
usually do next?"

House rules, same as the ledger: stdlib only, deterministic, never
raises — a broken input degrades the profile, never the pipeline.

Outputs: profiles/<TICKER>.json + profiles/<TICKER>.md
Usage: python3 scripts/reaction_profile.py POUL.CA
"""
import csv
import io
import json
import re
import statistics
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

REPO = "moos-labs/borsagator"
BRANCH = "archive"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
HELPER = ["python3", "workspace/custom-connectors/custom.github/bin/"
          "github_api.py"]


def warn(msg):
    print(f"WARN {msg}", file=sys.stderr)


def fetch_text(url, timeout=60):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        warn(f"fetch failed {url}: {e}")
        return None


def fetch_tree():
    try:
        out = subprocess.run(
            HELPER + ["get",
                      f"/repos/{REPO}/git/trees/{BRANCH}?recursive=1"],
            capture_output=True, text=True, timeout=120, cwd="/home/hatch")
        return [t["path"] for t in json.loads(out.stdout)["tree"]]
    except Exception as e:
        warn(f"tree fetch failed: {e}")
        return []


def parse_date(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %Z",
                "%d/%m/%Y", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)),
                            int(m.group(3))).date()
        except Exception:
            return None
    return None


def parse_price_csv(text):
    """(date, close) rows ascending; column names vary by source."""
    rows = []
    try:
        rdr = csv.DictReader(io.StringIO(text))
        fields = {f.lower(): f for f in (rdr.fieldnames or [])}
        dcol = next((fields[k] for k in fields
                     if k in ("date", "datetime", "time")), None)
        ccol = next((fields[k] for k in fields
                     if k in ("close", "closing", "adj close")), None)
        if not dcol or not ccol:
            return rows
        for row in rdr:
            d = parse_date(row.get(dcol, ""))
            try:
                c = float(row.get(ccol, ""))
            except Exception:
                continue
            if d and c > 0:
                rows.append((d, c))
    except Exception as e:
        warn(f"price csv parse failed: {e}")
    rows.sort()
    return rows


# Event taxonomy — mirrors the ensemble's risk-overlay types
# (item 5) so profiles and overlays speak the same language.
TAXONOMY = [
    ("earnings", ["نتائج أعمال", "صافي الربح", "القوائم المالية",
                  "earnings", "net profit", "financial results",
                  "quarterly", "annual results"]),
    ("dividend", ["كوبون", "توزيع", "dividend", "coupon", "payout"]),
    ("capital", ["زيادة رأس المال", "تجزئة", "اكتتاب", "capital increase",
                 "stock split", "rights issue", "merger", "اندماج"]),
    ("management", ["مجلس إدارة", "رئيس مجلس", "عضو منتدب", "استقالة",
                    "board", "chairman", "resignation", "appoint"]),
    ("legal", ["محكمة", "قضية", "غرامة", "رقابة مالية", "court",
               "lawsuit", "fine", "fraud", "تحقيق"]),
    ("governance", ["جمعية عامة", "عمومية", "general assembly",
                    "shareholders meeting", "agm", "egm"]),
]


def classify(title):
    t = (title or "").lower()
    for kind, keys in TAXONOMY:
        if any(k.lower() in t for k in keys):
            return kind
    return "other"


def norm_title(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", "", (t or "").lower())
                  ).strip()


def main():
    ticker = (sys.argv[1] if len(sys.argv) > 1 else "POUL.CA").upper()
    code = ticker.split(".")[0].lower()
    paths = fetch_tree()
    if not paths:
        print("reaction_profile: no archive tree — nothing to do")
        return 0

    # --- price series: newest egxpy csv for the ticker -------------
    csvs = sorted(p for p in paths
                  if p.startswith("sweeps/")
                  and p.endswith(f"egxpy_{code}.csv"))
    series = []
    if csvs:
        txt = fetch_text(RAW + csvs[-1])
        if txt:
            series = parse_price_csv(txt)
    if not series:
        print(f"reaction_profile: no price series for {ticker}")
        return 0
    dates = [d for d, _ in series]
    closes = {d: c for d, c in series}

    def idx_on_or_before(d):
        lo = None
        for i, sd in enumerate(dates):
            if sd <= d:
                lo = i
            else:
                break
        return lo

    # --- corporate actions from archived ensembles ------------------
    actions = []
    for p in sorted(x for x in paths
                    if x.startswith("sweeps/")
                    and x.endswith("ensemble.json")):
        txt = fetch_text(RAW + p)
        if not txt:
            continue
        try:
            ens = json.loads(txt)
        except Exception:
            continue
        if (ens.get("ticker") or ticker) != ticker:
            continue
        for a in ens.get("corporate_actions") or []:
            ex = parse_date(a.get("ex_date"))
            if ex and a.get("dps"):
                actions.append({"ex_date": ex, "dps": float(a["dps"])})

    # --- events from archived news/disclosure outputs ---------------
    seen, events = set(), []
    feed_files = sorted(
        p for p in paths
        if ("news-disclosure" in p or "egx-harvest" in p)
        and (p.endswith("disclosures.json") or p.endswith("news.json")))
    for p in feed_files:
        txt = fetch_text(RAW + p)
        if not txt:
            continue
        try:
            doc = json.loads(txt)
        except Exception:
            continue
        # Feed files from other tickers' sweeps live in the same
        # archive (NVDA's EDGAR items polluted the first POUL run) —
        # only ever measure THIS ticker's events.
        if (doc.get("ticker") or ticker) != ticker:
            continue
        items = doc.get("items", [])
        for it in items:
            d = parse_date(it.get("date"))
            title = it.get("title") or ""
            if not d or not title:
                continue
            key = (d.isoformat(), norm_title(title)[:60])
            if key in seen:
                continue
            seen.add(key)
            events.append({"date": d, "title": title[:160],
                           "type": classify(title),
                           "kind": it.get("kind", "")})
    events.sort(key=lambda e: e["date"])
    # One underlying event is republished by many outlets with
    # different headlines (the 19 Oct AGM dividend story appeared
    # six times) — counting each copy would let coverage volume,
    # not market reaction, dominate the medians. Cluster by
    # (date, type): one event, longest title kept, copies counted.
    clustered = {}
    for e in events:
        k = (e["date"], e["type"])
        if k in clustered:
            clustered[k]["coverage"] += 1
            if len(e["title"]) > len(clustered[k]["title"]):
                clustered[k]["title"] = e["title"]
        else:
            clustered[k] = {**e, "coverage": 1}
    events = sorted(clustered.values(), key=lambda e: e["date"])

    # --- measure reactions -------------------------------------------
    def reaction(ev):
        i = idx_on_or_before(ev["date"])
        if i is None:
            return None
        base = closes[dates[i]]
        out = {"base_date": dates[i].isoformat(), "base": base}
        crossed = [a for a in actions
                   if dates[i] < a["ex_date"] <=
                   (dates[i + 5] if i + 5 < len(dates) else dates[-1])]
        out["dividend_window"] = bool(crossed)
        for h in (1, 3, 5):
            j = i + h
            if j >= len(dates):
                out[f"r{h}"] = None
                out[f"r{h}_adj"] = None
                continue
            r = (closes[dates[j]] / base - 1) * 100
            out[f"r{h}"] = round(r, 2)
            adj = r
            for a in crossed:
                if dates[j] >= a["ex_date"]:
                    adj += a["dps"] / base * 100
            out[f"r{h}_adj"] = round(adj, 2)
        return out

    measured = []
    for ev in events:
        r = reaction(ev)
        if r is None:
            continue
        measured.append({**ev, "date": ev["date"].isoformat(), **r})

    # --- aggregates by type -------------------------------------------
    def med(vals):
        vals = [v for v in vals if v is not None]
        return round(statistics.median(vals), 2) if vals else None

    by_type = {}
    for kind in sorted({e["type"] for e in measured}):
        sub = [e for e in measured if e["type"] == kind]
        full = [e for e in sub if e["r5"] is not None]
        by_type[kind] = {
            "events": len(sub),
            "median_r1": med([e["r1"] for e in sub]),
            "median_r3": med([e["r3"] for e in sub]),
            "median_r5": med([e["r5"] for e in sub]),
            "median_r5_adj": med([e["r5_adj"] for e in full]),
            "big_move_share_r5": (
                round(sum(1 for e in full if abs(e["r5"]) >= 2)
                      / len(full), 2) if full else None),
        }

    # --- slice 2 (issue #32): top move days + shock follow-through --
    rets = []
    for i in range(1, len(series)):
        r = (series[i][1] / series[i - 1][1] - 1) * 100
        rets.append((series[i][0], r, i))
    # |move| beyond the EGX ±20% daily limit is a data artifact
    # (reference-price resets like the Sep 2026 merger seam), not a
    # tradable move — excluded from discovery and labelled.
    tradable = [x for x in rets if abs(x[1]) <= 21]
    artifacts = [x for x in rets if abs(x[1]) > 21]
    ev_by_date = {}
    for e in measured:
        ev_by_date.setdefault(e["date"], []).append(e["type"])
    top_moves = []
    for d, r, i in sorted(tradable, key=lambda x: -abs(x[1]))[:15]:
        fwd = {}
        for h in (1, 3, 5):
            j = i + h
            fwd[f"r{h}"] = (round((series[j][1] / series[i][1] - 1)
                                  * 100, 2) if j < len(series)
                            else None)
        near = [t for dd, ts in ev_by_date.items()
                if abs((parse_date(dd) - d).days) <= 1 for t in ts]
        top_moves.append({"date": d.isoformat(), "move": round(r, 2),
                          "close": series[i][1], **fwd,
                          "event_types_near": sorted(set(near))})
    shocks_up = [x for x in tradable if x[1] >= 5]
    shocks_dn = [x for x in tradable if x[1] <= -5]

    def follow_through(shocks):
        nxt, n3 = [], []
        for d, r, i in shocks:
            if i + 1 < len(series):
                nxt.append((series[i + 1][1] / series[i][1] - 1) * 100)
            if i + 3 < len(series):
                n3.append((series[i + 3][1] / series[i][1] - 1) * 100)
        return {"days": len(shocks),
                "median_next1": med(nxt), "median_next3": med(n3),
                "revert_share_next1": (
                    round(sum(1 for v in nxt if v < 0) / len(nxt), 2)
                    if nxt else None)}

    # --- slice 3 (issue #32): contemporaneous drivers via GDELT ---
    # The archive's own events only cover recent weeks, so the top
    # move days (2021-2026) get their drivers from a GDELT DOC sweep
    # fetched once from runner IPs (the API rate-limits this
    # sandbox's egress) and committed as profiles/gdelt_<TICKER>.json.
    gdelt_doc = {}
    try:
        gdelt_doc = json.loads(fetch_text(
            f"https://raw.githubusercontent.com/{REPO}/main/"
            f"profiles/gdelt_{ticker}.json"))
    except Exception:
        gdelt_doc = {}
    for m in top_moves:
        g = gdelt_doc.get(m["date"]) or {}
        arts = []
        for lang in ("ar", "en"):
            arts += (g.get(lang) or {}).get("articles", [])
        m["gdelt"] = {
            "articles": len(arts),
            "driver_types": sorted({classify(a.get("title", ""))
                                    for a in arts} - {"other"}),
            "headlines": [{"date": (a.get("seendate") or "")[:8],
                           "title": a.get("title", ""),
                           "domain": a.get("domain", "")}
                          for a in arts[:3]]}

    # --- slice 4 (issue #32): reaction fit with shrinkage + a
    # walk-forward sign check. Per-type medians are shrunk toward
    # the global median with a pseudo-count k=5, so a type with two
    # events cannot shout over the stock's whole history. The
    # walk-forward fits on the first half of the events and scores
    # sign predictions on the second half — indicative at this n.
    K = 5
    all_r5 = [e["r5"] for e in measured if e["r5"] is not None]
    global_r5 = med(all_r5)
    fitted = {}
    for kind in sorted({e["type"] for e in measured}):
        vals = [e["r5"] for e in measured
                if e["type"] == kind and e["r5"] is not None]
        if vals and global_r5 is not None:
            raw = med(vals)
            fitted[kind] = {
                "n": len(vals), "raw_median_r5": raw,
                "shrunk_r5": round((len(vals) * raw + K * global_r5)
                                   / (len(vals) + K), 2)}
    evs = sorted((e for e in measured if e["r5"] is not None),
                 key=lambda e: e["date"])
    wf = {"train": 0, "test": 0, "hits": None, "baseline_hits": None}
    if len(evs) >= 8 and global_r5 is not None:
        half = len(evs) // 2
        train, test = evs[:half], evs[half:]
        tg = med([e["r5"] for e in train])
        tmed = {}
        for kind in {e["type"] for e in train}:
            vals = [e["r5"] for e in train if e["type"] == kind]
            tmed[kind] = (len(vals) * med(vals) + K * tg) / (len(vals) + K)
        hits = base = n = 0
        for e in test:
            if abs(e["r5"]) < 0.75:
                continue
            pred = tmed.get(e["type"], tg)
            n += 1
            hits += (pred > 0) == (e["r5"] > 0)
            base += (tg > 0) == (e["r5"] > 0)
        wf = {"train": len(train), "test": n, "hits": hits,
              "baseline_hits": base}

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    profile = {"ticker": ticker, "built_at": stamp,
               "series": {"sessions": len(series),
                          "from": dates[0].isoformat(),
                          "to": dates[-1].isoformat()},
               "events_measured": len(measured),
               "by_type": by_type, "events": measured,
               "top_moves": top_moves,
               "reaction_fit": {"global_median_r5": global_r5,
                                "shrinkage_k": K, "by_type": fitted},
               "walk_forward": wf,
               "shock_followthrough": {
                   "up_5pct": follow_through(shocks_up),
                   "down_5pct": follow_through(shocks_dn)},
               "series_artifacts_excluded": len(artifacts)}
    import os
    os.makedirs("profiles", exist_ok=True)
    with open(f"profiles/{ticker}.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=1, ensure_ascii=False)
    lines = [f"# Reaction profile — {ticker}", "",
             f"Sessions: {len(series)} ({dates[0]} → {dates[-1]}). "
             f"Events measured: {len(measured)}.", "",
             "| Type | Events | Median +1 | Median +3 | Median +5 | "
             "Median +5 (div-adj) | |Move|≥2% share |",
             "|---|---|---|---|---|---|---|"]
    for kind, a in by_type.items():
        lines.append(
            f"| {kind} | {a['events']} | {a['median_r1']} | "
            f"{a['median_r3']} | {a['median_r5']} | "
            f"{a['median_r5_adj']} | {a['big_move_share_r5']} |")
    lines += ["", "## Events", "",
              "| Date | Type | Title | +1 | +3 | +5 | Notes |",
              "|---|---|---|---|---|---|---|"]
    for e in measured:
        note = "dividend window" if e["dividend_window"] else ""
        lines.append(
            f"| {e['date']} | {e['type']} | {e['title'][:60]} | "
            f"{e['r1']} | {e['r3']} | {e['r5']} | {note} |")
    lines += ["", "## Top move days (|move| ≤ 21%; beyond the EGX "
              "limit = data artifact, excluded)", "",
              "| Date | Move % | Close | +1 | +3 | +5 | Events near |",
              "|---|---|---|---|---|---|---|"]
    for m in top_moves:
        lines.append(
            f"| {m['date']} | {m['move']} | {m['close']} | {m['r1']} | "
            f"{m['r3']} | {m['r5']} | "
            f"{', '.join(m['event_types_near'])} |")
    lines += ["", "### What the contemporaneous press said (GDELT)", ""]
    for m in top_moves:
        g = m.get("gdelt") or {}
        if g.get("articles"):
            heads = "; ".join(
                f"{h['title'][:60]} ({h['domain']})"
                for h in g["headlines"])
            lines.append(
                f"- **{m['date']}** ({m['move']:+}%): drivers "
                f"{', '.join(g['driver_types']) or 'unclassified'} — "
                f"{heads}")
        else:
            lines.append(
                f"- **{m['date']}** ({m['move']:+}%): no contemporaneous "
                f"coverage found in GDELT")
    fit = profile["reaction_fit"]
    lines += ["", "## Reaction fit (median +5 shrunk toward the "
              f"global median {fit['global_median_r5']}%, k="
              f"{fit['shrinkage_k']})", "",
              "| Type | n | Raw median +5 | Shrunk +5 |",
              "|---|---|---|---|"]
    for kind, fv in fit["by_type"].items():
        lines.append(f"| {kind} | {fv['n']} | {fv['raw_median_r5']} | "
                     f"{fv['shrunk_r5']} |")
    wfv = profile["walk_forward"]
    if wfv["hits"] is not None and wfv["test"]:
        lines += ["",
                  f"Walk-forward: fit on {wfv['train']} events, sign "
                  f"hits {wfv['hits']}/{wfv['test']} on the later half "
                  f"(baseline always-global: {wfv['baseline_hits']}/"
                  f"{wfv['test']}) — indicative only at this sample size."]
    sf = profile["shock_followthrough"]
    lines += ["", "## Shock follow-through (|move| ≥ 5%)", "",
              f"Up days: {sf['up_5pct']['days']} — median next day "
              f"{sf['up_5pct']['median_next1']}%, next 3 "
              f"{sf['up_5pct']['median_next3']}%, revert share "
              f"{sf['up_5pct']['revert_share_next1']}",
              f"Down days: {sf['down_5pct']['days']} — median next day "
              f"{sf['down_5pct']['median_next1']}%, next 3 "
              f"{sf['down_5pct']['median_next3']}%, revert share "
              f"{sf['down_5pct']['revert_share_next1']}"]
    with open(f"profiles/{ticker}.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"reaction_profile: {ticker} events={len(measured)} "
          f"types={list(by_type)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never raise into a pipeline
        print(f"reaction_profile: failed soft: {e}", file=sys.stderr)
        sys.exit(0)
