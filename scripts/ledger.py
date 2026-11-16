#!/usr/bin/env python3
"""Borsagator calibration ledger (v1).

Scores the ensemble's own archived forecasts against what the market
actually did, using ONLY the point-in-time sweep archive (branch
`archive` of moos-labs/borsagator) as its data source:

- Forecasts come from each sweep's ensemble.json.
- Actual daily closes come from the sweeps' own collected price CSVs
  (egx-data preferred among content-validated series; otherwise the
  longest content-validated series for the ticker). Later sweeps
  extend the series; a forecast is never scored on data from its own
  sweep.
- Point-in-time pin (issue #117): the archive branch is resolved to
  its HEAD commit sha at run start; the tree is fetched at that
  commit and every body via raw at that same commit. A branch advance
  mid-run therefore cannot mix bodies from a newer tree into a ledger
  that records this tree's sha; the pinned commit sha is recorded in
  ledger.json alongside the tree sha.
- Validity guard (issue #87): a forecast is scored only when its
  base_price matches the ticker's evidenced price level — closes from
  files positively tied to the ticker by symbol column or filename —
  at its as-of date. A sweep whose ensemble base was manufactured
  from another ticker's data fails this check and its forecasts are
  marked invalid, never scored.
- A horizon matures when the series holds at least `trading_sessions`
  sessions strictly after the forecast date. If the window spans a
  dividend ex-date recorded by the forecast (issue #26), the realized
  move is computed dividend-adjusted (DPS added back to post-ex
  closes) and the row is marked adjusted.

Outputs ledger.json + ledger.md. Stdlib only, deterministic, and
defensive throughout: a bad sweep, file or row is recorded as a gap,
never raised.
"""
import csv, io, json, os, re, subprocess, sys, urllib.parse, urllib.request
from datetime import date

REPO = "moos-labs/borsagator"
BRANCH = "archive"
API_REF = (f"https://api.github.com/repos/{REPO}/git/ref/heads/"
           f"{BRANCH}")
# Issue #117: the tree is fetched at the pinned commit sha, never at
# the live branch — the tree URL is built in fetch_tree() once the
# commit is resolved. Bodies are fetched via blob_url() at the same
# commit, so a branch advance mid-run cannot mix bodies from tree Y
# into a ledger that records tree X.
# The sweeps-subtree fallback URL is likewise built at the pinned
# commit inside fetch_tree_sweeps_subtree().
# NOTE: the old module-level RAW (branch URL) is gone by design.
# INS-R7-02: anchored to the checkout like the other two scripts
# (INS-R6-04 pattern) — the old $HOME path was dead weight off-VM.
HELPER = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "custom-connectors", "custom.github", "bin", "github_api.py"))

HORIZONS = ("day", "week", "month")
DEFAULT_SESSIONS = {"day": 1, "week": 5, "month": 14}
FLAT_BAND_PCT = 0.75          # |realized| below this counts as "flat"
VALID_TOL = 0.03              # 3% close-vs-base validation tolerance
# Files that are never an actual-price series for the target ticker.
BLOCKLIST = ("forecast.csv", "account_value", "port_analysis",
             "report_normal", "screener", "companies", "fred_")

WARNINGS = []
STATS = {"skipped_rows": 0}   # malformed CSV rows dropped while parsing


def warn(msg):
    WARNINGS.append(str(msg))


# Issue #64: in Actions a token is always available — using it for
# the API reads removes the anonymous rate limit, the flakiest
# failure mode of the automated rerun. Raw-file fetches stay
# anonymous (public repo); the header is scoped to api.github.com.
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def fetch_text(url, timeout=60):
    headers = {"User-Agent": "borsagator-ledger"}
    if TOKEN and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener().open(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# Issue #117: the archive commit sha resolved at run start — the pin
# for the whole run. Set by main() once fetch_tree() resolves it;
# blob_url() refuses to fetch before it is set (fail closed, never
# silently fall back to the live branch).
PINNED_COMMIT = None


def blob_url(rel):
    """raw.githubusercontent URL for a path at the pinned commit."""
    if not PINNED_COMMIT:
        raise RuntimeError("archive commit not resolved before body "
                           "fetch (issue #117 pin missing)")
    return (f"https://raw.githubusercontent.com/{REPO}/{PINNED_COMMIT}/"
            + urllib.parse.quote(rel))


def fetch_tree():
    """Archive tree pinned to one immutable commit (issue #117).

    The branch is resolved to its HEAD commit sha FIRST; the tree is
    then fetched at that commit sha and every body via raw at the
    same commit sha. A commit is immutable, so a worker archiving a
    sweep mid-run cannot mix bodies from a newer tree into a ledger
    that records this tree's sha. Returns (tree, commit_sha, via).
    Raises on failure — main() records it as a gap and the publisher
    rejects the run (issue #116)."""
    commit_sha = resolve_archive_commit()
    tree_url = (f"https://api.github.com/repos/{REPO}/git/trees/"
                f"{commit_sha}?recursive=1")
    try:
        data = json.loads(fetch_text(tree_url))
        if not data.get("truncated"):
            return data, commit_sha, "api-token" if TOKEN else "api-anonymous"
        # INS-R6-05 (extension): a truncated recursive tree must
        # never be silently consumed — fall through to the helper.
        warn("anonymous tree truncated; trying API helper")
    except Exception as e:
        warn(f"anonymous tree fetch failed ({e}); trying API helper")
    out = subprocess.run(
        [sys.executable, HELPER, "get",
         f"/repos/{REPO}/git/trees/{commit_sha}?recursive=1"],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"tree fetch failed: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    if data.get("truncated"):
        # INS-R7-03: auth does not raise GitHub's truncation cap,
        # so the helper truncates identically — recover via the
        # sweeps subtree (the only part the ledger reads) instead of
        # consuming a known-incomplete tree.
        return fetch_tree_sweeps_subtree(commit_sha)
    return data, commit_sha, "api-helper"


def resolve_archive_commit():
    """Resolve the archive branch to its HEAD commit sha via the
    GitHub API; fall back to the connector helper (authenticated)
    if the anonymous rate limit bites. The commit sha is the pin
    for the run (issue #117)."""
    try:
        data = json.loads(fetch_text(API_REF))
        sha = (data.get("object") or {}).get("sha")
        if sha and (data.get("object") or {}).get("type") == "commit":
            return sha
        warn(f"archive ref has no commit sha ({str(data)[:120]}); "
             "trying API helper")
    except Exception as e:
        warn(f"archive ref fetch failed ({e}); trying API helper")
    out = subprocess.run(
        [sys.executable, HELPER, "get",
         f"/repos/{REPO}/git/ref/heads/{BRANCH}"],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"archive ref fetch failed: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    sha = (data.get("object") or {}).get("sha")
    if not sha or (data.get("object") or {}).get("type") != "commit":
        raise RuntimeError("archive ref fetch returned no commit sha")
    return sha


def fetch_tree_sweeps_subtree(commit_sha):
    """Fallback when the recursive tree truncates: fetch the
    recursive tree rooted at sweeps/ only, at the pinned commit
    (issue #117 — the subtree must come from the same commit as
    the tree it replaces). If even that truncates, fail closed —
    a silently truncated tree would corrupt the calibration
    instrument (INS-R7-03)."""
    url = (f"https://api.github.com/repos/{REPO}/git/trees/"
           f"{commit_sha}:sweeps?recursive=1")
    try:
        data = json.loads(fetch_text(url))
        if not data.get("truncated"):
            prefixed = []
            for entry in data.get("tree", []):
                e = dict(entry)
                e["path"] = "sweeps/" + e["path"]
                prefixed.append(e)
            data["tree"] = prefixed
            return data, commit_sha, "api-sweeps-subtree"
    except Exception as e:
        warn(f"sweeps-subtree fetch failed ({e})")
    raise RuntimeError("tree truncated and sweeps-subtree unavailable "
                       "— failing closed")


def parse_date(s):
    s = (s or "").strip().strip('"')
    if not s:
        return None
    head = s[:10]
    for fmt in ("%Y-%m-%d",):
        try:
            y, m, d = int(head[:4]), int(head[5:7]), int(head[8:10])
            if head[4] == "-" and head[7] == "-":
                return date(y, m, d).isoformat()
        except Exception:
            pass
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            from datetime import datetime
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except Exception:
            continue
    return None


def parse_price_csv(text):
    """Generic dated-close extraction. Returns {iso_date: close} or
    None when the file is not a dated price series. A `symbol` column,
    when present, is returned too so callers can reject reference
    workloads for other tickers."""
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:
        return None, None
    if len(rows) < 5:
        return None, None
    header = [h.strip().lower() for h in rows[0]]
    def find(names):
        for n in names:
            if n in header:
                return header.index(n)
        return None
    di = find(["date", "datetime", "day", "index", ""])
    ci = find(["close", "closing", "last"])
    if ci is None:
        ci = find(["adjclose", "adj close"])
    si = find(["symbol", "ticker"])
    if di is None or ci is None:
        return None, None
    out, symbols = {}, set()
    for r in rows[1:]:
        if len(r) <= max(di, ci):
            STATS["skipped_rows"] += 1
            continue
        d = parse_date(r[di])
        if not d:
            STATS["skipped_rows"] += 1
            continue
        try:
            c = float(str(r[ci]).replace(",", ""))
        except Exception:
            STATS["skipped_rows"] += 1
            continue
        if c > 0:
            out[d] = c
            if si is not None and len(r) > si:
                symbols.add(r[si].strip())
        else:
            STATS["skipped_rows"] += 1
    if len(out) < 20:
        return None, None
    return out, (symbols or None)


def rel_close(a, b):
    return abs(a - b) / b if b else 1.0


def pick_series(sweep, ticker, base_price, accumulated, foreign_codes=()):
    """Choose this sweep's price series for the ticker. Returns
    (series, source_rel, evidenced_series, evidenced_rel,
    fetch_failures): the main pick plus the best positively
    ticker-evidenced series (a file whose symbol column names the
    ticker, or whose filename carries the ticker's code as a token —
    egxpy_comi.csv, NVDA.csv). Either pair may be (None, None).
    fetch_failures is [(rel, error)] for every candidate CSV whose
    body could not be fetched at all. Issue #132: a fetch failure
    used to be warn() + continue and nothing else, so a total
    raw-host failure silently left every forecast pending, matured
    0, and the ledger published with all weights reset to neutral."""
    code = ticker.split(".")[0].lower()
    candidates, evidenced, fetch_failures = [], [], []
    for rel, size in sweep["csvs"]:
        name = rel.rsplit("/", 1)[-1].lower()
        if any(b in name for b in BLOCKLIST):
            continue
        if size > 1_500_000:
            continue  # screeners/dumps, never a daily target series
        tokens = [t for t in re.split(r"[^a-z0-9]+", name) if t]
        if code not in tokens and any(t in foreign_codes for t in tokens):
            continue  # filename names another ticker: reference workload
        try:
            # Issue #117: body at the pinned commit, never the live branch.
            series, symbols = parse_price_csv(fetch_text(blob_url(rel)))
        except Exception as e:
            warn(f"{sweep['dir']}: unreadable {rel} ({e})")
            # Issue #132: record the failure for the caller — a
            # warn() alone never reached the validation gate.
            fetch_failures.append((rel, str(e)))
            continue
        if series is None:
            continue
        if symbols and ticker not in symbols:
            continue  # reference workload for another ticker
        candidates.append((rel, series))
        if (symbols and ticker in symbols) or code in tokens:
            evidenced.append((rel, series))
    # Evidenced pick: the file positively names this ticker, so it is
    # trusted for level checks without price validation (egx first,
    # else longest) — the yardstick for the issue-#87 scoring guard.
    ev_pick, ev_src = None, None
    if evidenced:
        pool_ev = sorted(evidenced, key=lambda rs: len(rs[1]), reverse=True)
        ev_src, ev_pick = pool_ev[0]
        for rel, series in evidenced:
            if "/egx-data/" in rel:
                ev_pick, ev_src = series, rel
                break
    if not candidates:
        return None, None, ev_pick, ev_src, fetch_failures

    def last_on_or_before(series, iso):
        ds = [d for d in series if d <= iso]
        return series[max(ds)] if ds else None

    validated = []
    for rel, series in candidates:
        anchor = last_on_or_before(series, sweep["date"])
        ok = False
        if base_price and anchor:
            ok = rel_close(anchor, base_price) <= VALID_TOL
        elif accumulated:
            overlap = [d for d in series if d in accumulated]
            if len(overlap) >= 5:
                diffs = sorted(rel_close(series[d], accumulated[d]) for d in overlap)
                ok = diffs[len(diffs) // 2] <= VALID_TOL
        if ok:
            validated.append((rel, series))
    pool = validated or []
    # egx-data is the exchange series for EGX tickers: among the
    # VALIDATED candidates it wins outright. It must pass the same
    # content validation as every other source — the old shortcut
    # trusted it unconditionally ("the tool only ever fetches the
    # sweep's own ticker"), and issue #87 broke that assumption:
    # egx-data ignored the sweep ticker and returned POUL data for
    # COMI and NVDA sweeps, and the unvalidated shortcut let it
    # poison those tickers' actuals series (phantom -94% NVDA rows).
    for rel, series in validated:
        if "/egx-data/" in rel:
            return series, rel, ev_pick, ev_src, fetch_failures
    if not pool:
        return None, None, ev_pick, ev_src, fetch_failures
    pool.sort(key=lambda rs: len(rs[1]), reverse=True)
    return pool[0][1], pool[0][0], ev_pick, ev_src, fetch_failures


def csv_failure_gaps(series, fetch_failures, pick_failures=()):
    """Gap strings for price-CSV failures (issue #132).
    `fetch_failures` is [(sweep_dir, rel, error)] aggregated across
    sweeps; `pick_failures` is [(sweep_dir, error)] for sweeps whose
    whole series pick raised. Every failed fetch is recorded under
    the distinct `price-CSV fetch failed` prefix — the publisher
    does NOT reject on that prefix alone, so a single failed CSV
    among many candidates still publishes. Only the last gap is a
    rejecting signal: it fires when no price series could be built
    for any ticker AND at least one fetch or pick failed, i.e. the
    archive held candidate CSVs but none could be read. With no
    failures at all an empty series is an honest data state (no
    CSVs in the tree yet), not a fetch failure, and no gap fires.
    Pure and testable — main() only aggregates its inputs."""
    gaps = [f"price-CSV fetch failed: {d}: {rel} could not be "
            f"fetched ({e})" for d, rel, e in fetch_failures]
    gaps += [f"price series pick failed: {d} ({e})"
             for d, e in pick_failures]
    if not series and (fetch_failures or pick_failures):
        gaps.append(
            f"no price series could be built: "
            f"{len(fetch_failures)} price-CSV fetch(es) and "
            f"{len(pick_failures)} series pick(s) failed and no "
            "actuals series exists for any ticker")
    return gaps


def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def realized_direction(pct):
    if abs(pct) < FLAT_BAND_PCT:
        return "flat"
    return "up" if pct > 0 else "down"


# Issue #131: same reporting-noise tolerance as ensemble.py —
# 1.89 / 1.9 / 1.8999999998 are one coupon, not three. Defence in
# depth: a duplicate arriving from any path (not only detection)
# must not be summed twice. This subsumes dedup on
# (ex_date, round(dps, 2)): values rounding to the same — or an
# adjacent — 2dp bucket differ by <= 0.01 and merge here.
def _dps_same(a, b):
    try:
        a, b = float(a), float(b)
    except Exception:
        return False
    return abs(a - b) <= max(0.02, 0.01 * max(abs(a), abs(b)))


def _dedup_actions(actions):
    """Unique (ex_date, DPS) pairs, keep first, in order."""
    out = []
    for a in actions:
        if any(o["ex_date"] == a["ex_date"]
               and _dps_same(o["dps"], a["dps"]) for o in out):
            continue
        out.append(a)
    return out


def normalize_actions(ens, horizon_block):
    """Dividend actions for one horizon: the horizon-level block
    (issue #26) wins; else the ensemble-level corporate_actions."""
    raw = []
    ha = (horizon_block or {}).get("corporate_action")
    if isinstance(ha, dict) and ha.get("ex_date"):
        raw = [ha]
    elif isinstance(ens.get("corporate_actions"), list):
        raw = [a for a in ens["corporate_actions"]
               if isinstance(a, dict) and a.get("ex_date")]
    out = []
    for a in raw:
        try:
            out.append({"dps": float(a["dps"]), "ex_date": str(a["ex_date"])[:10],
                        "mechanical_pct": a.get("mechanical_pct")})
        except Exception:
            continue
    # Issue #131: two dated detections of one coupon must count
    # once, however they reached the ledger. Keep the first.
    return _dedup_actions(out)


def score_forecast(fc, series, provenance, own_sweep):
    """Score one forecast against {date: close}. Pure and testable.
    `provenance` maps date -> set of sweep dirs that supplied the
    close; maturity points must come from at least one OTHER sweep."""
    after = sorted(d for d in series if d > fc["as_of"])
    usable = [d for d in after
              if provenance.get(d, set()) - {own_sweep}]
    row = dict(fc)
    if len(usable) < fc["sessions"]:
        row.update(status="pending", sessions_available=len(usable))
        return row
    maturity = usable[fc["sessions"] - 1]
    close = series[maturity]
    adjusted, dps_total = False, 0.0
    counted = []  # (ex_date, dps) pairs already added — issue #131
    for a in fc.get("corporate_actions") or []:
        if fc["as_of"] < a["ex_date"] <= maturity:
            # Issue #131: sum each (ex_date, DPS) pair once. A
            # duplicate dated detection of one coupon (1.89 vs 1.9
            # vs 1.8999999998) arriving from any path must not be
            # summed twice; keep the first.
            dps = float(a["dps"])
            if any(ex == a["ex_date"] and _dps_same(d, dps)
                   for ex, d in counted):
                continue
            counted.append((a["ex_date"], dps))
            dps_total += dps
            adjusted = True
    if adjusted:
        close = close + dps_total
    realized = (close / fc["base_price"] - 1.0) * 100.0
    rdir = realized_direction(realized)
    fam_skill = {}
    fams = fc.get("families") or {}
    for fam, s in fams.items():
        if isinstance(s, (int, float)):
            fam_skill[fam] = round(s * sign(realized), 4)
    row.update(
        status="matured", maturity_date=maturity,
        close_at_maturity=series[maturity],
        dividend_adjusted=adjusted,
        realized_move_pct=round(realized, 2),
        realized_direction=rdir,
        direction_hit=(rdir == fc["direction"]),
        move_error_pp=round(abs(fc["expected_move_pct"] - realized), 2),
        in_range=(fc["range_low_pct"] <= realized <= fc["range_high_pct"]),
        family_skill=fam_skill,
        net_skill=(round(fc["net_score"] * sign(realized), 4)
                   if isinstance(fc.get("net_score"), (int, float)) else None),
        sessions_available=len(usable))
    return row


def num(x):
    return x if isinstance(x, (int, float)) else None


def main():
    global PINNED_COMMIT
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ledger_out")
    os.makedirs(out_dir, exist_ok=True)
    gaps = []
    try:
        tree, commit_sha, tree_src = fetch_tree()
    except Exception as e:
        tree, commit_sha, tree_src = {"tree": [], "sha": None}, None, "failed"
        gaps.append(f"archive tree could not be fetched: {e}")
    # Issue #117: pin every body fetch below to this commit.
    PINNED_COMMIT = commit_sha
    entries = [(e["path"], e.get("size") or 0)
               for e in tree.get("tree", []) if e.get("type") == "blob"]

    # ---- enumerate sweeps -------------------------------------------------
    sweeps = {}
    for p, size in entries:
        parts = p.split("/")
        if len(parts) >= 4 and parts[0] == "sweeps":
            key = "/".join(parts[:3])
            s = sweeps.setdefault(key, {"dir": key, "csvs": [], "ensemble": None,
                                        "digest": None})
            rel = "/".join(parts[3:])
            if rel == "ensemble.json":
                s["ensemble"] = p
            elif rel == "digest.json":
                s["digest"] = p
            elif rel.startswith("collected/") and rel.endswith(".csv"):
                s["csvs"].append((p, size))
    sweep_list = [sweeps[k] for k in sorted(sweeps)]
    for s in sweep_list:
        s["date"] = s["dir"].split("/")[1]
        for kind in ("digest", "ensemble"):
            if s[kind]:
                try:
                    # Issue #117: body at the pinned commit.
                    s[kind + "_data"] = json.loads(fetch_text(
                        blob_url(s[kind])))
                except Exception as e:
                    warn(f"{s['dir']}: bad {kind}.json ({e})")
                    s[kind + "_data"] = None
                    # Issue #116: a fetch failure is NOT the same as a
                    # missing file — record it as a gap so the
                    # publisher rejects the run instead of publishing
                    # a ledger that silently drops the sweep.
                    s[kind + "_fetch_failed"] = True
                    gaps.append(f"per-file fetch failed: {s['dir']}: "
                                f"{kind}.json could not be fetched ({e})")
        d = s.get("digest_data") or {}
        e = s.get("ensemble_data") or {}
        s["ticker"] = e.get("ticker") or d.get("ticker")
        if d.get("date"):
            s["date"] = str(d["date"])[:10]
        s["has_ensemble"] = bool(e)
    # Issue #116: only sweeps with NO ensemble.json in the tree count
    # here — a sweep whose ensemble.json exists but failed to fetch is
    # already recorded in gaps (per-file fetch failed) and must not
    # be mislabelled as a legitimately ensemble-less run.
    no_ens = [s["dir"] for s in sweep_list
              if not s["has_ensemble"]
              and not s.get("ensemble_fetch_failed")]
    if no_ens:
        gaps.append(f"{len(no_ens)} sweep(s) carry no ensemble.json "
                    f"(category/single-tool runs): " + "; ".join(no_ens))

    # ---- build actual-close series per ticker -----------------------------
    all_codes = {str(s["ticker"]).split(".")[0].lower()
                 for s in sweep_list if s.get("ticker")}
    series, provenance, sources = {}, {}, {}
    evidenced_series = {}
    # Issue #132: CSV fetch / series-pick failures aggregated here
    # so the validation gate can see them (they used to be warn()
    # + continue and nothing else).
    csv_fetch_failures = []  # (sweep_dir, rel, error)
    series_pick_failures = []  # (sweep_dir, error)
    for s in sweep_list:  # chronological by path sort
        t = s["ticker"]
        if not t:
            continue
        base = num((s.get("ensemble_data") or {}).get("base_price"))
        acc = series.get(t, {})
        foreign = all_codes - {t.split(".")[0].lower()}
        picked, src, ev_picked, ev_src, failures = (None, None, None,
                                                    None, [])
        try:
            picked, src, ev_picked, ev_src, failures = pick_series(
                s, t, base, acc, foreign)
        except Exception as e:
            warn(f"{s['dir']}: series pick failed ({e})")
            series_pick_failures.append((s["dir"], str(e)))
        csv_fetch_failures.extend(
            (s["dir"], rel, err) for rel, err in failures)
        if ev_picked:
            etgt = evidenced_series.setdefault(t, {})
            for d, c in ev_picked.items():
                if d not in etgt or (ev_src and "/egx-data/" in ev_src):
                    etgt[d] = c
        if not picked:
            continue
        tgt = series.setdefault(t, {})
        prov = provenance.setdefault(t, {})
        for d, c in picked.items():
            if d not in tgt or (src and "/egx-data/" in src):
                tgt[d] = c
            prov.setdefault(d, set()).add(s["dir"])
        sources.setdefault(t, []).append(
            {"sweep": s["dir"], "file": src, "points": len(picked),
             "last_date": max(picked)})
    series_summary = {}
    for t, m in sorted(series.items()):
        ds = sorted(m)
        series_summary[t] = {"points": len(ds), "first_date": ds[0],
                             "last_date": ds[-1], "sources": sources.get(t, [])}
    for t, summ in series_summary.items():
        gaps.append(f"{t}: actuals series has {summ['points']} sessions, "
                    f"{summ['first_date']} → {summ['last_date']} "
                    f"(last source: {summ['sources'][-1]['file'] if summ['sources'] else '—'})")
    # Issue #132: record CSV fetch failures as gaps (distinct
    # prefix) and fail closed when no series could be built at all.
    gaps.extend(csv_failure_gaps(series, csv_fetch_failures,
                                 series_pick_failures))
    if STATS["skipped_rows"]:
        gaps.append(f"price-CSV parsing skipped {STATS['skipped_rows']} "
                    "malformed/non-positive row(s) across all candidate files")

    # ---- extract forecasts --------------------------------------------------
    forecasts = []
    for s in sweep_list:
        ens = s.get("ensemble_data")
        if not ens:
            continue
        t = ens.get("ticker") or s["ticker"]
        as_of = str(ens.get("date") or s["date"])[:10]
        base = num(ens.get("base_price"))
        if not t or not base:
            warn(f"{s['dir']}: ensemble missing ticker/base_price; skipped")
            continue
        top_fams = ens.get("family_scores") or {}
        for h in HORIZONS:
            hb = (ens.get("horizons") or {}).get(h)
            if not isinstance(hb, dict):
                continue
            fams = hb.get("families") or top_fams
            sess = hb.get("trading_sessions")
            if not isinstance(sess, int) or sess <= 0:
                sess = DEFAULT_SESSIONS[h]
            forecasts.append({
                "ticker": t, "as_of": as_of, "sweep": s["dir"],
                "horizon": h, "direction": hb.get("direction"),
                "expected_move_pct": num(hb.get("expected_move_pct")),
                "range_low_pct": num(hb.get("range_low_pct")),
                "range_high_pct": num(hb.get("range_high_pct")),
                "confidence": num(hb.get("confidence")),
                "net_score": num(hb.get("net_score")),
                "base_price": base,
                "families": {k: num(v) for k, v in fams.items()
                             if num(v) is not None},
                "sessions": sess,
                "corporate_actions": normalize_actions(ens, hb),
            })

    # ---- score ---------------------------------------------------------------
    # Issue #87 validity guard: a forecast is scored only when its
    # base_price matches the ticker's evidenced price level (closes
    # from files positively tied to the ticker by symbol column or
    # filename) at its as-of date. Price-vs-base validation inside
    # pick_series cannot catch a sweep whose ensemble base was itself
    # manufactured from the wrong ticker's data (the COMI sweep-lite
    # based COMI on POUL's 10.15); such forecasts are invalid, never
    # scored, and excluded from skill/weights.
    rows, invalid = [], []
    for fc in forecasts:
        t = fc["ticker"]
        ev = evidenced_series.get(t, {})
        ev_dates = [d for d in ev if d <= fc["as_of"]]
        if ev_dates:
            level_date = max(ev_dates)
            level = ev[level_date]
            if rel_close(fc["base_price"], level) > VALID_TOL:
                r = dict(fc)
                r.update(status="invalid",
                         invalid_reason=(
                             f"base_price {fc['base_price']} deviates "
                             f"{rel_close(fc['base_price'], level) * 100:.1f}% from the "
                             f"ticker-evidenced close {level} at {level_date} "
                             f"— the sweep's data does not match {t} (issue #87)"))
                rows.append(r)
                invalid.append(r)
                continue
        try:
            rows.append(score_forecast(fc, series.get(t, {}),
                                       provenance.get(t, {}), fc["sweep"]))
        except Exception as e:
            warn(f"scoring failed for {fc}: {e}")
            r = dict(fc); r.update(status="error", error=str(e))
            rows.append(r)
    matured = [r for r in rows if r["status"] == "matured"]
    pending = [r for r in rows if r["status"] == "pending"]
    if invalid:
        gaps.append(f"{len(invalid)} forecast(s) invalidated by the "
                    "issue-#87 guard (base_price inconsistent with the "
                    "ticker-evidenced price level; never scored): " +
                    "; ".join(f"{r['ticker']} as of {r['as_of']} "
                              f"({r['horizon']}) from {r['sweep']}"
                              for r in invalid))
    adjusted_rows = [r for r in matured if r.get("dividend_adjusted")]
    if not any((fc.get("corporate_actions") for fc in forecasts)):
        gaps.append("no archived ensemble carries a corporate_actions block "
                    "yet (the first post-#26 sweep has not run) — the "
                    "dividend-adjustment path is implemented and covered by "
                    "a synthetic check, with zero real adjusted rows so far")
    if not matured:
        gaps.append("no forecast has matured yet: every archived price "
                    "series ends 2026-11-12, so even the earliest forecasts "
                    "(as of 2026-11-12) have zero sessions after their date "
                    "in the archive; later sweeps will extend the series "
                    "and mature them")

    # ---- aggregates ---------------------------------------------------------
    def agg(subset):
        n = len(subset)
        if not n:
            return {"n": 0, "hit_rate": None, "mean_abs_error_pp": None,
                    "range_coverage": None}
        return {"n": n,
                "hit_rate": round(sum(r["direction_hit"] for r in subset) / n, 3),
                "mean_abs_error_pp": round(
                    sum(r["move_error_pp"] for r in subset) / n, 2),
                "range_coverage": round(
                    sum(r["in_range"] for r in subset) / n, 3)}
    by_horizon = {h: agg([r for r in matured if r["horizon"] == h])
                  for h in HORIZONS}
    by_ticker = {}
    for t in sorted({r["ticker"] for r in rows}):
        by_ticker[t] = {
            "found": sum(1 for r in rows if r["ticker"] == t),
            "matured": sum(1 for r in matured if r["ticker"] == t),
            "pending": sum(1 for r in pending if r["ticker"] == t),
            "invalid": sum(1 for r in invalid if r["ticker"] == t)}
    fam_vals = {}
    for r in matured:
        for fam, v in (r.get("family_skill") or {}).items():
            fam_vals.setdefault(fam, []).append(v)
        if r.get("net_skill") is not None:
            fam_vals.setdefault("ensemble (net_score)", []).append(r["net_skill"])
    family_skill = {fam: {"mean_skill": round(sum(v) / len(v), 3), "n": len(v)}
                    for fam, v in sorted(fam_vals.items())}

    ledger = {
        "tool": "calibration-ledger", "version": 1,
        "source": {"repo": REPO, "branch": BRANCH,
                   "tree_sha": tree.get("sha"),
                   # Issue #117: the commit every body was fetched at.
                   "commit_sha": commit_sha, "tree_via": tree_src},
        "counts": {"sweeps": len(sweep_list),
                   "sweeps_with_ensemble": sum(1 for s in sweep_list if s["has_ensemble"]),
                   "forecasts": len(rows), "matured": len(matured),
                   "pending": len(pending), "invalid": len(invalid),
                   "dividend_adjusted": len(adjusted_rows)},
        "by_ticker": by_ticker, "by_horizon": by_horizon,
        "family_skill": family_skill,
        "series": series_summary,
        "forecasts_detail": rows,
        "gaps": gaps, "warnings": WARNINGS,
    }
    with open(os.path.join(out_dir, "ledger.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1, ensure_ascii=False)

    # Measured-weights feedback (issue #28): family skill becomes a
    # bounded multiplicative factor on the ensemble's base weights.
    # The ensemble multiplies its own table by these factors, so the
    # base table lives in exactly one place (ensemble.py). A family
    # needs >= MIN_N matured forecasts before it may move at all,
    # and the clamp keeps any single family within [0.5x, 1.5x].
    MIN_N, CLAMP = 3, (0.5, 1.5)
    FAMILIES = ("price-forecast", "technicals", "sentiment", "agent",
                "fundamentals")
    factors = {}
    for fam in FAMILIES:
        v = family_skill.get(fam)
        if v and v["n"] >= MIN_N:
            factors[fam] = {"factor": round(max(CLAMP[0], min(
                CLAMP[1], 1.0 + v["mean_skill"])), 3),
                "skill": v["mean_skill"], "n": v["n"]}
        else:
            factors[fam] = {"factor": 1.0,
                            "skill": v["mean_skill"] if v else None,
                            "n": v["n"] if v else 0}
    weights_doc = {"tool": "ensemble-weights", "version": 1,
                   "built_from": "calibration-ledger",
                   "min_n": MIN_N, "clamp": list(CLAMP),
                   "factors": factors}
    with open(os.path.join(out_dir, "weights.json"), "w",
              encoding="utf-8") as f:
        json.dump(weights_doc, f, indent=1, ensure_ascii=False)

    # ---- markdown -------------------------------------------------------------
    L = ["# 🐊 Borsagator — calibration ledger (v1)", "",
         f"Source: `{REPO}` branch `{BRANCH}` (tree {str(tree.get('sha'))[:8]}, "
         f"commit {str(commit_sha)[:8] if commit_sha else '—'}). "
         f"Sweeps archived: {ledger['counts']['sweeps']} "
         f"({ledger['counts']['sweeps_with_ensemble']} with an ensemble).", "",
         f"**Forecasts found: {len(rows)} · matured: {len(matured)} · "
         f"pending: {len(pending)} · invalid: {len(invalid)} · "
         f"dividend-adjusted: {len(adjusted_rows)}**", ""]
    L += ["## By ticker", "",
          "| Ticker | Found | Matured | Pending | Invalid | Series span |",
          "|---|---|---|---|---|---|"]
    for t, b in by_ticker.items():
        ss = series_summary.get(t, {})
        span = f"{ss.get('first_date','—')} → {ss.get('last_date','—')}" if ss else "—"
        L.append(f"| {t} | {b['found']} | {b['matured']} | {b['pending']} | "
                 f"{b.get('invalid', 0)} | {span} |")
    L += ["", "## By horizon (matured only)", "",
          "| Horizon | n | Direction hit rate | Mean |error| (pp) | Range coverage |",
          "|---|---|---|---|---|"]
    for h in HORIZONS:
        a = by_horizon[h]
        fmt = lambda v, suf="": "—" if v is None else f"{v}{suf}"
        L.append(f"| {h} | {a['n']} | {fmt(a['hit_rate'])} | "
                 f"{fmt(a['mean_abs_error_pp'])} | {fmt(a['range_coverage'])} |")
    L += ["", "## Family skill (mean of family_score × sign(realized), matured only)", "",
          "| Family | Mean skill | n |", "|---|---|---|"]
    if family_skill:
        for fam, v in family_skill.items():
            L.append(f"| {fam} | {v['mean_skill']:+.3f} | {v['n']} |")
    else:
        L.append("| — | no matured forecasts yet | 0 |")
    L += ["", "## Forecasts", "",
          "| Ticker | As of | Horizon | Dir | Expected % | Realized % | Hit | |Err| pp | In range | Adj | Status |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["status"] == "matured":
            f2 = lambda v: "—" if v is None else f"{v:+.2f}"
            f0 = lambda v: "—" if v is None else f"{v:.2f}"
            L.append(f"| {r['ticker']} | {r['as_of']} | {r['horizon']} | {r['direction']} | "
                     f"{f2(r.get('expected_move_pct'))} | {f2(r.get('realized_move_pct'))} | "
                     f"{'✅' if r.get('direction_hit') else '❌'} | {f0(r.get('move_error_pp'))} | "
                     f"{'✅' if r.get('in_range') else '❌'} | "
                     f"{'💰' if r.get('dividend_adjusted') else ''} | matured {r.get('maturity_date', '')} |")
        elif r["status"] == "invalid":
            L.append(f"| {r['ticker']} | {r['as_of']} | {r['horizon']} | {r['direction']} | "
                     f"{r['expected_move_pct']:+.2f} | — | — | — | — | | "
                     f"invalid — {r.get('invalid_reason', '')} |")
        else:
            L.append(f"| {r['ticker']} | {r['as_of']} | {r['horizon']} | {r['direction']} | "
                     f"{r['expected_move_pct']:+.2f} | — | — | — | — | | "
                     f"pending ({r.get('sessions_available', 0)}/{r['sessions']} sessions) |")
    L += ["", "## Data gaps & notes", ""]
    for g in gaps:
        L.append(f"- {g}")
    for w in WARNINGS:
        L.append(f"- ⚠️ {w}")
    L += ["", "_Skill is provisional until a meaningful number of forecasts "
          "have matured; a family is only as good as its measured record._"]
    with open(os.path.join(out_dir, "ledger.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("ledger:", ledger["counts"])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # the ledger must never crash a workflow
        print("ledger failed (non-fatal):", e)
