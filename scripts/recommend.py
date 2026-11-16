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
- A fresh event of a fitted type (within 5 calendar days before the
  ensemble's as-of date, newest wins) nudges the expected move by
  the type's SHRUNK reaction, decayed.
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
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

REPO = "moos-labs/borsagator"
RAW_MAIN = f"https://raw.githubusercontent.com/{REPO}/main/"
API_REF = (f"https://api.github.com/repos/{REPO}/git/ref/heads/"
           f"archive")
# Issue #121: the tree is fetched at the pinned commit sha, never at
# the live branch — the tree URLs are built in fetch_tree() once the
# commit is resolved. Bodies are fetched via blob_url() at the same
# commit, so a branch advance mid-run cannot mix bodies from tree Y
# into a recommendation that records tree X.
# NOTE: the old module-level RAW_ARCHIVE (live-branch URL) is gone
# by design. RAW_MAIN stays: profiles/<TICKER>.json is a main-branch
# input (the latest committed reaction fit), not an archive body,
# and the output records no main tree — pinning it would freeze a
# stale profile, not fix the archive race this issue covers.
# Connector helper, anchored to the checkout (not a machine path,
# not cwd-dependent — INS-R6-04 pattern). Only used if the
# anonymous API fetch fails or truncates.
HELPER = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "custom-connectors", "custom.github", "bin", "github_api.py"))


def fetch_text(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "borsagator"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# Issue #121: the archive commit sha resolved at run start — the pin
# for the whole run. Set by fetch_tree() once it resolves it;
# blob_url() refuses to fetch before it is set (fail closed, never
# silently fall back to the live branch).
PINNED_COMMIT = None


def blob_url(rel):
    """raw.githubusercontent URL for a path at the pinned commit."""
    if not PINNED_COMMIT:
        raise RuntimeError("archive commit not resolved before body "
                           "fetch (issue #121 pin missing)")
    return (f"https://raw.githubusercontent.com/{REPO}/{PINNED_COMMIT}/"
            + urllib.parse.quote(rel))


def resolve_archive_commit():
    """Resolve the archive branch to its HEAD commit sha via the
    GitHub API; fall back to the connector helper (authenticated)
    if the anonymous rate limit bites. The commit sha is the pin
    for the run (issue #121, same as #117)."""
    try:
        data = json.loads(fetch_text(API_REF))
        sha = (data.get("object") or {}).get("sha")
        if sha and (data.get("object") or {}).get("type") == "commit":
            return sha
        print(f"recommend: archive ref has no commit sha "
              f"({str(data)[:120]}); trying API helper",
              file=sys.stderr)
    except Exception as e:
        print(f"recommend: archive ref fetch failed ({e}); "
              "trying API helper", file=sys.stderr)
    out = subprocess.run(
        [sys.executable, HELPER, "get",
         f"/repos/{REPO}/git/ref/heads/archive"],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(
            f"archive ref fetch failed: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    sha = (data.get("object") or {}).get("sha")
    if not sha or (data.get("object") or {}).get("type") != "commit":
        raise RuntimeError("archive ref fetch returned no commit sha")
    return sha


def fetch_tree():
    """Archive tree via the public API first; the connector helper
    (authenticated) only if the anonymous fetch fails or the API
    truncates the recursive tree (INS-R6-01, INS-R6-05). Re-applies
    the #59 fix that #60's rewrite dropped: no /opt/muse import,
    runnable off the VM.

    Issue #121: the branch is resolved to its HEAD commit sha FIRST
    and the tree is fetched at that commit sha, so the tree and
    every body fetched from it belong to one immutable commit."""
    global PINNED_COMMIT
    try:
        PINNED_COMMIT = resolve_archive_commit()
    except Exception as e:
        print(f"recommend: archive commit resolution failed ({e}); "
              "failing closed, no recommendation written",
              file=sys.stderr)
        return []
    tree_url = (f"https://api.github.com/repos/{REPO}/git/trees/"
                f"{PINNED_COMMIT}?recursive=1")
    try:
        txt = fetch_text(tree_url)
        if txt:
            data = json.loads(txt)
            if not data.get("truncated"):
                return [t["path"] for t in data.get("tree", [])]
            print("recommend: anonymous tree truncated; "
                  "trying API helper", file=sys.stderr)
    except Exception as e:
        print(f"recommend: anonymous tree fetch failed ({e}); "
              "trying API helper", file=sys.stderr)
    try:
        out = subprocess.run(
            [sys.executable, HELPER, "get",
             f"/repos/{REPO}/git/trees/{PINNED_COMMIT}?recursive=1"],
            capture_output=True, text=True, timeout=120)
        # INS-R7-04: a hard helper failure (nonzero exit, empty
        # stdout) must not degrade to a JSON error mislabeled as
        # missing data — same check ledger.py already has.
        if out.returncode != 0:
            raise RuntimeError(
                f"helper tree fetch failed: {out.stderr[:200]}")
        data = json.loads(out.stdout)
        if data.get("truncated"):
            # INS-R7-03: auth does not raise GitHub's truncation cap,
            # so the helper truncates identically — recover by
            # fetching the sweeps subtree (the only part these
            # scripts read) instead of consuming a known-incomplete
            # tree.
            return fetch_tree_sweeps_subtree(PINNED_COMMIT)
        return [t["path"] for t in data.get("tree", [])]
    except Exception as e:
        print(f"recommend: tree fetch failed: {e}", file=sys.stderr)
        return []


def fetch_tree_sweeps_subtree(commit_sha):
    """Fallback when the recursive tree truncates: fetch the
    recursive tree rooted at sweeps/ only, at the pinned commit
    (issue #121 — the subtree must come from the same commit as
    the tree it replaces). Every path these scripts read lives
    under sweeps/, and the subtree is far under the truncation
    cap. If even that truncates, fail closed — never consume a
    known-incomplete tree (INS-R7-03)."""
    tree_url = (f"https://api.github.com/repos/{REPO}/git/trees/"
                f"{commit_sha}:sweeps?recursive=1")
    try:
        txt = fetch_text(tree_url)
        if txt:
            data = json.loads(txt)
            if not data.get("truncated"):
                return ["sweeps/" + t["path"]
                        for t in data.get("tree", [])]
    except Exception as e:
        print(f"recommend: sweeps-subtree fetch failed ({e})",
              file=sys.stderr)
    print("recommend: tree truncated and sweeps-subtree unavailable "
          "— failing closed, no recommendation written",
          file=sys.stderr)
    return []


def list_sweep_dirs():
    """Newest-first sweep directories on the archive branch, via the
    git trees API (one call, like ledger.py)."""
    paths = fetch_tree()
    dirs = sorted({p.rsplit("/", 1)[0] for p in paths
                   if p.startswith("sweeps/") and p.endswith("ensemble.json")},
                  reverse=True)
    return dirs, set(paths)


def newest_ensemble(ticker):
    dirs, paths = list_sweep_dirs()
    if PINNED_COMMIT is None:
        # fetch_tree() failed to resolve the pin — fail closed,
        # never read bodies from the live branch (issue #121).
        print("recommend: archive commit not resolved — failing "
              "closed, no recommendation written", file=sys.stderr)
        return None, None
    slug = ticker.lower().replace(".", "-")
    for d in dirs:
        # sweep dir names embed the job, not reliably the ticker —
        # read the ensemble and check.
        try:
            # Issue #121: body at the pinned commit, never the live
            # branch.
            e = json.loads(fetch_text(blob_url(d + "/ensemble.json")))
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
             f"archive pinned to commit {PINNED_COMMIT} — ensemble "
             f"body fetched at that commit (issue #121)",
             f"weights source: {ens.get('weights_source', 'builtin')}"]

    # --- reaction-fit nudge -------------------------------------------
    # Freshness is anchored on the ENSEMBLE's as-of date, not the
    # profile's own series end: an event counts only if it happened
    # within 5 calendar days before the ensemble (about 3 trading
    # sessions) — never in the future, never from a stale profile.
    # The NEWEST eligible event wins (INS-R5-03).
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
    asof = None
    try:
        asof = date.fromisoformat((ens.get("date") or "")[:10])
    except Exception:
        asof = None
    if events and asof:
        for e in sorted(events, key=lambda x: x.get("date", ""),
                        reverse=True):
            # INS-R7-01: never nudge on an unclassified event, whatever
            # the committed profile contains — the build side excludes
            # "other" from fitted types, but a stale pre-fix profile
            # carried forward after a soft-fail would re-open it.
            if (e.get("type") or "") == "other":
                continue
            try:
                age = (asof - date.fromisoformat(e["date"][:10])).days
            except Exception:
                continue
            fv = fitted.get(e.get("type") or "")
            # INS-R6-02: old-format profiles predate the R5-05 key
            # rename (shrunk_r5, not shrunk_r5_adj) — a bare key
            # access would kill the whole recommendation.
            shrunk = (fv or {}).get("shrunk_r5_adj")
            if shrunk is not None and 0 <= age <= 5:
                nudge = round(shrunk * 0.5, 2)
                notes.append(
                    f"fresh {e['type']} event ({e['date']}, {age}d "
                    f"before the ensemble): shrunk reaction "
                    f"{shrunk:+}% x 0.5 decay = "
                    f"{nudge:+}% nudge")
                break
    wf = profile.get("walk_forward") or {}
    if (wf.get("hits") is not None and wf.get("baseline_hits") is not None
            and wf["hits"] <= wf["baseline_hits"]):
        notes.append(
            "reaction fit walk-forward showed no edge over the naive "
            "baseline yet — nudge kept at half weight, treat as context")

    # --- dividend mechanics -------------------------------------------
    # A dividend subtracts from the reference ONLY when its ex-date
    # falls inside this recommendation's week horizon (as-of < ex <=
    # as-of + 7 calendar days, the week horizon's calendar span).
    # A past, undated, or far-future dividend is already in the
    # price or out of scope and must NOT be subtracted again
    # (INS-R5-02). The nearest eligible ex-date wins; others are
    # noted, not summed.
    ref_base = base
    divs = []
    for a in ens.get("corporate_actions") or []:
        if a.get("type") != "dividend" or not a.get("dps"):
            continue
        ex = None
        try:
            ex = date.fromisoformat((a.get("ex_date") or "")[:10])
        except Exception:
            ex = None
        divs.append((ex, a))
    eligible = [(ex, a) for ex, a in divs if ex and asof
                and asof < ex <= (asof + timedelta(days=7))]
    if eligible:
        ex, a = sorted(eligible, key=lambda t: t[0])[0]
        ref_base = round(base - a["dps"], 2)
        notes.append(
            f"dividend: DPS {a['dps']} ex {a.get('ex_date')} — "
            f"mechanical drop {a.get('mechanical_pct')}% takes the "
            f"reference from {base} to {ref_base}; bands are quoted "
            f"on the post-drop reference")
        if len(eligible) > 1:
            notes.append(f"{len(eligible) - 1} further dividend(s) "
                         f"inside the horizon noted, not summed")
    elif divs:
        notes.append(
            "dividend action(s) present but no ex-date falls inside "
            "this week horizon — reference left at the base price")

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
           "archive_commit": PINNED_COMMIT,
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
          f"sell>={sell_above} (base {base}, ref {ref_base}, "
          f"archive {PINNED_COMMIT[:8]})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never raise into a pipeline
        print(f"recommend: failed soft: {e}", file=sys.stderr)
        sys.exit(0)
