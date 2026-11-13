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
from datetime import datetime, timezone

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
RISK_MULT = {"none": 1.0, "elevated": 1.2, "shock": 1.5}
SHOCK_WORDS = [
    "resign", "oust", "ceo", "earnings", "guidance", "investigat", "fraud",
    "halt", "merger", "acquisition", "dividend", "profit warning",
    "bankrupt", "lawsuit", "استقال", "إقال", "نتائج", "أرباح", "توزيع",
    "اندماج", "تحقيق", "إيقاف", "مجلس الإدارة", "جمعية عامة",
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


def realized_sigma(ticker):
    """Daily-return stdev from collected price CSVs.
    Returns (sigma, source) with sigma = max(sigma_60, sigma_10)."""
    code = ticker.split(".")[0].lower()
    best = None
    for path in glob.glob(os.path.join(COLLECTED, "*", "*.csv")):
        name = os.path.basename(path).lower()
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
        closes = [c for c in closes if c]
        if len(closes) < 30:
            continue
        if best is None or len(closes) > len(best[0]):
            best = (closes, os.path.basename(os.path.dirname(path)) + "/" + name)
    if not best:
        return 0.02, "default (no history found)"
    closes, src = best

    def sd(vals):
        rets = [math.log(vals[i] / vals[i - 1]) for i in range(1, len(vals))]
        if len(rets) < 5:
            return 0.0
        mu = sum(rets) / len(rets)
        return math.sqrt(sum((r - mu) ** 2 for r in rets) / len(rets))

    s60 = sd(closes[-61:])
    s10 = sd(closes[-11:])
    return max(s60, s10), f"{src} (σ60={s60:.4f}, σ10={s10:.4f})"


def main():
    digest = load_json(DIGEST)
    if not digest:
        print("ensemble: no digest.json — skipping")
        return
    ticker = (digest.get("ticker") or "").upper()
    results = {r["tool"]: r for r in digest.get("results", [])}

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

    sigma, sigma_src = realized_sigma(ticker)

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
    if ok("news-disclosure") and fnum(nd.get("finbert_positive")) is not None:
        subs.append(fnum(nd["finbert_positive"]) - fnum(nd.get("finbert_negative") or 0))
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
            pe = None
            for path in glob.glob(os.path.join(COLLECTED, "financetoolkit", "*.json")):
                d = load_json(path)
                if d:
                    pe = find_key(d, ["price_earnings", "pe_ratio", "p_e"])
                    if pe:
                        break
            if pe is None:
                for path in glob.glob(os.path.join(COLLECTED, "financetoolkit", "*.csv")):
                    try:
                        with open(path, newline="", encoding="utf-8") as f:
                            for row in csv.DictReader(f):
                                for k, v in row.items():
                                    if k and any(n in k.lower() for n in
                                                 ("price_earnings", "pe_ratio", "p_e")):
                                        pe = fnum(v)
                                        if pe:
                                            break
                                if pe:
                                    break
                    except Exception:
                        continue
                    if pe:
                        break
            if pe:
                fund = .4 if pe < 8 else .15 if pe < 15 else -.1 if pe < 25 else -.35

    # ---------- news risk overlay ----------
    risk = {"level": "none", "conf_cap": .60, "price_mult": 1.0, "flags": []}
    if ok("news-disclosure"):
        news = load_json(os.path.join(COLLECTED, "news-disclosure", "news.json")) or {}
        disc = load_json(os.path.join(COLLECTED, "news-disclosure", "disclosures.json")) or {}
        items = (disc.get("items") or []) + (news.get("items") or [])
        now = datetime.now(timezone.utc)
        fresh_disc, shock = 0, []
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
            if age <= 2 and any(w in title.lower() for w in SHOCK_WORDS):
                shock.append(title[:90])
        if shock:
            risk.update(level="shock", conf_cap=.30, price_mult=.5)
            risk["flags"] = ["shock headline(s): " + s for s in shock[:3]]
        elif fresh_disc or len(items) >= 10:
            risk.update(level="elevated", conf_cap=.45, price_mult=.8)
            if fresh_disc:
                risk["flags"].append(f"{fresh_disc} disclosure(s) in the last 3 days")

    # ---------- combine per horizon ----------
    fam_fixed = {"technicals": tech, "sentiment": sentiment,
                 "agent": agent, "fundamentals": fund}
    out = {"tool": "forecast-ensemble", "version": 2, "ticker": ticker,
           "base_price": base, "base_source": base_src,
           "sigma_daily": round(sigma, 4), "sigma_source": sigma_src,
           "date": digest.get("date"), "risk": risk,
           "family_scores": {}, "horizons": {},
           "confidence_basis": "provisional (uncalibrated — no scoring history yet)"}
    fam_display = dict(fam_fixed)
    for hname, bar in HORIZONS.items():
        ka = kronos_at(bar)
        vol_h = sigma * math.sqrt(bar)          # 1-sigma move over the horizon
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
        }
    out["family_scores"] = {k: (round(v, 3) if v is not None else None)
                            for k, v in fam_display.items()}

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    lines = ["", "---", "", "## 🎯 Ensemble forecast (synthesizer v2)", "",
             f"Base price {base} ({base_src}). Daily volatility σ {sigma:.2%} ({sigma_src}). "
             f"News risk: **{risk['level']}**"
             + ((" — " + "; ".join(risk["flags"])) if risk["flags"] else "") + ".",
             "Ranges are anchored in realized volatility. Confidence is provisional "
             "(uncalibrated) until the scoring ledger has history.", "",
             "| Horizon | Direction | Expected | Range | Confidence |",
             "|---|---|---|---|---|"]
    for hname in ("day", "week", "month"):
        h = out["horizons"].get(hname)
        if not h:
            continue
        arrow = {"up": "⬆ up", "down": "⬇ down", "flat": "➡ flat"}[h["direction"]]
        note = " (fleet horizon)" if h["horizon_short"] else ""
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
    sys.exit(0)
