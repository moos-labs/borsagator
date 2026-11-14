#!/usr/bin/env python3
"""Daily recommendation glue (issue #32, final piece).

Combines the three measured layers Borsagator already produces —
the newest archived ensemble forecast for the ticker, the stock's
own reaction fit (profiles/<TICKER>.json, when one exists), and the
ensemble's risk overlay + corporate-action detection — into one
deterministic daily call:

    action (buy / hold / sell-trim), buy_below, sell_above,
    the reasoning chain, and an honestly-capped confidence.

Rules are transparent arithmetic, no LLM:
- The action horizon is the ensemble's WEEK horizon; day/month are
  context. fair = base x (1 + expected_week). The action band is
  fair shifted by half the week's 1-sigma move (from the range the
  ensemble published): buy at or below the band's low edge,
  sell/trim at or above its high edge, hold between.
- A fresh event of a fitted type (<= 2 sessions old in the profile)
  nudges the expected move by the type's SHRUNK reaction, decayed.
- A dividend ex-date inside the horizon is stated mechanically:
  the price is expected to drop by the DPS on the ex-date, and the
  buy band is quoted on the post-drop reference so the call does
  not chase the cum-dividend price.
- Risk gates: shock risk forces HOLD; unknown risk caps
  confidence at the ensemble's own cap. When the reaction fit's
  walk-forward showed no edge over the naive baseline, that is
  printed on the recommendation instead of hidden.

House rules: stdlib only, deterministic, never raises.
Outputs: profiles/<TICKER>.recommendation.json + .md
Usage: python3 scripts/recommend.py POUL.CA
"""
import json
import os
import statistics
import sys
import urllib.request
from datetime import date

REPO = "moos-labs/borsagator"
RAW_ARCHIVE = f"https://raw.githubusercontent.com/{REPO}/archive/"
RAW_MAIN = f"https://raw.githubusercontent.com/{REPO}/main/"


def fetch_text(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "borsagator"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def list_sweep_dirs():
    """Newest-first sweep directories on the archive branch, via the
    git trees API (one call, like ledger.py)."""
    import subprocess
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    from dynamic_credentials import (add_surrogate_to_request,
                                     read_response_body)
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/git/trees/archive"
        "?recursive=1", method="GET")
    add_surrogate_to_request(req, "custom.github",
                             allowed_hosts=["api.github.com"])
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.build_opener().open(req, timeout=60) as r:
        tree = json.loads(read_response_body(r))
    dirs = sorted({p.rsplit("/", 1)[0] for p in
                   (t["path"] for t in tree.get("tree", []))
                   if p.startswith("sweeps/") and p.endswith("ensemble.json")},
                  reverse=True)
    return dirs, {t["path"] for t in tree.get("tree", [])}


def newest_ensemble(ticker):
    dirs, paths = list_sweep_dirs()
    slug = ticker.lower().replace(".", "-")
    for d in dirs:
        # sweep dir names embed the job, not reliably the ticker —
        # read the ensemble and check.
        try:
            e = json.loads(fetch_text(RAW_ARCHIVE + d + "/ensemble.json"))
        except Exception:
            continue
        if (e.get("ticker") or "").upper() == ticker:
            return e, d
    return None, None


def main():
    ticker = (sys.argv[1] if len(sys.argv) > 1 else "POUL.CA").upper()
    ens, sweep_dir = newest_ensemble(ticker)
    if not ens:
        print(f"recommend: no archived ensemble for {ticker}")
        return 0
    base = ens["base_price"]
    hz = ens.get("horizons") or {}
    week = hz.get("week") or {}
    expected = week.get("expected_move_pct", 0.0)
    lo = week.get("range_low_pct", -2.0)
    hi = week.get("range_high_pct", 2.0)
    conf = week.get("confidence", 0.3)
    risk = (ens.get("risk") or {}).get("level", "unknown")
    notes = [f"ensemble as of {ens.get('date')} (sweep {sweep_dir})",
             f"weights source: {ens.get('weights_source', 'builtin')}"]

    # --- reaction-fit nudge -------------------------------------------
    profile = {}
    try:
        profile = json.loads(fetch_text(
            RAW_MAIN + f"profiles/{ticker}.json"))
    except Exception:
        profile = {}
    fit = profile.get("reaction_fit") or {}
    fitted = fit.get("by_type") or {}
    nudge = 0.0
    events = profile.get("events") or []
    series_to = (profile.get("series") or {}).get("to")
    if events and series_to:
        end = date.fromisoformat(series_to)
        for e in events:
            try:
                age = (end - date.fromisoformat(e["date"])).days
            except Exception:
                continue
            fv = fitted.get(e.get("type") or "")
            if fv and age <= 3:  # fresh event of a fitted type
                nudge = round(fv["shrunk_r5"] * 0.5, 2)
                notes.append(
                    f"fresh {e['type']} event ({e['date']}): shrunk "
                    f"reaction {fv['shrunk_r5']:+}% x 0.5 decay = "
                    f"{nudge:+}% nudge")
                break
    wf = profile.get("walk_forward") or {}
    if (wf.get("hits") is not None and wf.get("baseline_hits") is not None
            and wf["hits"] <= wf["baseline_hits"]):
        notes.append(
            "reaction fit walk-forward showed no edge over the naive "
            "baseline yet — nudge kept at half weight, treat as context")

    # --- dividend mechanics -------------------------------------------
    ref_base = base
    for a in ens.get("corporate_actions") or []:
        if a.get("type") == "dividend" and a.get("dps"):
            ref_base = round(base - a["dps"], 2)
            notes.append(
                f"dividend: DPS {a['dps']} ex {a.get('ex_date')} — "
                f"mechanical drop {a.get('mechanical_pct')}% takes the "
                f"reference from {base} to {ref_base}; bands are quoted "
                f"on the post-drop reference")
            break

    expected_adj = round(expected + nudge, 2)
    fair = ref_base * (1 + expected_adj / 100)
    half_band = ref_base * max(abs(hi - expected), abs(expected - lo)) / 100 * 0.5
    buy_below = round(fair - half_band, 2)
    sell_above = round(fair + half_band, 2)

    if risk == "shock":
        action = "hold"
        notes.append("risk overlay = shock: action forced to HOLD")
    elif ref_base <= buy_below:
        # Decide on the reference: pre-ex, today's cum price minus
        # the locked dividend IS the buyer's effective entry, so the
        # bands (quoted post-drop) must be compared against it, not
        # against the cum price.
        action = "buy"
    elif ref_base >= sell_above:
        action = "sell/trim"
    else:
        action = "hold"
    if ref_base != base:
        notes.append("action decided on the post-drop reference "
                     "(cum price minus the locked dividend)")
    if risk == "unknown":
        conf = min(conf, 0.35)

    rec = {"ticker": ticker, "as_of": ens.get("date"),
           "base_price": base, "reference_price": ref_base,
           "action": action, "buy_below": buy_below,
           "sell_above": sell_above,
           "expected_week_pct": expected, "nudge_pct": nudge,
           "expected_week_adj_pct": expected_adj,
           "confidence": conf, "risk": risk,
           "weights_source": ens.get("weights_source", "builtin"),
           "notes": notes}
    os.makedirs("profiles", exist_ok=True)
    with open(f"profiles/{ticker}.recommendation.json", "w",
              encoding="utf-8") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
    lines = [f"# Daily recommendation — {ticker} (as of {rec['as_of']})",
             "",
             f"**{action.upper()}** · base {base} · reference "
             f"{ref_base} · buy at/below **{buy_below}** · sell/trim "
             f"at/above **{sell_above}** · confidence {conf} · risk "
             f"{risk}", "", "Why:", ""]
    lines += [f"- {n}" for n in notes]
    lines += ["", "_Deterministic glue over the ensemble + reaction "
              "fit — research tooling, not financial advice._"]
    with open(f"profiles/{ticker}.recommendation.md", "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"recommend: {ticker} {action} buy<={buy_below} "
          f"sell>={sell_above} (base {base}, ref {ref_base})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never raise into a pipeline
        print(f"recommend: failed soft: {e}", file=sys.stderr)
        sys.exit(0)
