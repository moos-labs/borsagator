"""Round 70: cross-sectional IC shadow scorer (stdlib). DESCRIPTIVE only.

Design and accepted thresholds: docs/round70_ic_shadow_design_skeleton.md
(committed before this scorer). No verdict word or key. Below the gate the
scorer prints counts only and computes no statistic.

Per signal (technicals, sentiment, ensemble net_score) and horizon (day,
week): a row is clean when status is matured, dividend_gap is null, the
horizon matches, realized_move_pct and the signal are not null. One row per
(as_of, horizon, ticker): the FIRST such row in ledger order is kept (the
ledger holds re-issued forecasts for some tickers; sources do not settle
which to keep, so the earliest is used and this is flagged for review).
A wide date has >= 20 distinct tickers. Excess return = realised move minus
the date's mean over its clean tickers. IC = Spearman rank correlation of
signal vs excess return (average ranks; zero signals stay in).
"""
import argparse
import json
import math
import random

HORIZONS = ("day", "week")
SIGNALS = ("technicals", "sentiment", "net_score")
WIDE = 20
GATE_DATES = 20
B_DRAWS = 2000
SEED = 70


def signal_value(f, sig):
    if sig == "net_score":
        return f.get("net_score")
    return (f.get("families") or {}).get(sig)


def clean_rows(rows, sig, h):
    seen = set()
    out = []
    for f in rows:
        v = signal_value(f, sig)
        if (f.get("status") != "matured" or f.get("dividend_gap") is not None
                or f.get("horizon") != h or v is None
                or f.get("realized_move_pct") is None):
            continue
        key = (f["as_of"], f["ticker"])
        if key in seen:
            continue
        seen.add(key)
        out.append((f["as_of"], f["ticker"], float(v), float(f["realized_move_pct"])))
    return out


def _ranks(v):
    order = sorted(range(len(v)), key=lambda k: v[k])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def spearman(x, y):
    if len(x) < 3:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def date_ics(rows):
    """{as_of: IC} over wide dates; excess = move - date mean."""
    by = {}
    for d, t, s, m in rows:
        by.setdefault(d, []).append((s, m))
    out = {}
    for d, g in by.items():
        if len(g) < WIDE:
            continue
        mean = sum(m for _, m in g) / len(g)
        ic = spearman([s for s, _ in g], [m - mean for _, m in g])
        if ic is not None:
            out[d] = ic
    return out


def boot_ci(ics, draws=B_DRAWS, seed=SEED):
    keys = sorted(ics)
    if not keys:
        return None, None
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        vals.append(sum(ics[rng.choice(keys)] for _k in keys) / len(keys))
    vals.sort()
    return vals[int(0.025 * (len(vals) - 1))], vals[int(round(0.975 * (len(vals) - 1)))]


def icir(vals):
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    return None if sd == 0 else m / sd


def pass_leg(res):
    return all(res[h]["ci95"][0] is not None and res[h]["ci95"][0] > 0
               and res[h]["n_dates"] >= GATE_DATES for h in HORIZONS)


def score(rows):
    out = {"wide_min_tickers": WIDE, "gate_required": GATE_DATES, "signals": {}}
    for sig in SIGNALS:
        ics = {h: date_ics(clean_rows(rows, sig, h)) for h in HORIZONS}
        both = set(ics["day"]) & set(ics["week"])
        s = {"wide_dates_day": len(ics["day"]), "wide_dates_week": len(ics["week"]),
             "wide_dates_both": len(both), "gate_reached": len(both) >= GATE_DATES}
        if s["gate_reached"]:
            for h in HORIZONS:
                v = [ics[h][d] for d in sorted(ics[h])]
                lo, hi = boot_ci(ics[h])
                s[h] = {"n_dates": len(v), "mean_ic": sum(v) / len(v), "icir": icir(v),
                        "ci95": [lo, hi]}
            s["ci_lower_gt_0_both"] = pass_leg(s)
        out["signals"][sig] = s
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default="ledger/ledger.json")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = score(json.load(open(a.ledger))["forecasts_detail"])
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
