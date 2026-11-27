#!/usr/bin/env python3
"""GDELT GKG 2.0 streaming filter (INS-DATA-002 item 2 / G3).

Builds an entity-tagged article INDEX for the EGX33 universe from the free
GDELT bulk files. No key, no signup. GKG gives URL + metadata only, never
article text; this script never fetches article text. No verdicts.

Pipeline (Muhammad's GO, Moos Slack 1795726615.743939, 2026-11-26):
  masterfilelist -> parallel HTTPS fetch -> unzip in memory -> filter rows
  on the alias table (evaluation/gdelt_alias_table.csv) plus Egyptian
  outlet domains -> matched rows appended as JSON lines.

Layout: every GKG 2.x file in the archive, English AND translation, has 27
columns with identical positions (Moos review on #815: verified on
2024-05-15 09:00 both streams and the first 2015-02-18 file): record id 0,
date 1, SourceCollectionIdentifier 2, SourceCommonName 3,
DocumentIdentifier 4, Themes 7, V2EnhancedOrganizations 14, V2Tone 15.
Lines with any other column count are malformed: skipped and counted per
file, never parsed with a guessed layout.

Restart-safe by file name: STATE/done.txt records every fully processed
GKG file; reruns skip it. Matches are appended (fsync) BEFORE the done
marker, so a crash reprocesses at most one file; --finalize dedupes on
(gkg_record_id, url) and skips any truncated/corrupted line an interrupted
append can leave, counting them. STATE/config.json binds the state dir to
the alias table hash, date range and out dir; it is written atomically
(temp file, fsync, os.replace) before any archive is recorded done. A
mismatch or unreadable config refuses to run: rebind with a FRESH --out
directory (delete config.json + done.txt), or also delete matches.jsonl to
reuse the out dir -- a fresh bind never inherits prior matches, and an
unchanged config keeps them so normal restarts keep working.

Rows kept when EITHER:
  - a V2Organizations entry matches a ticker alias (word-boundary,
    case/punctuation-insensitive), no per-ticker block pattern matches,
    and - when the alias carries require_patterns in the alias table - at
    least one require pattern also matches the same entry (reason "alias"
    or "both"), OR
  - SourceCommonName is an Egyptian outlet domain (reason "eg_domain";
    candidates for a later alias-free pass, kept with no ticker).

Alias-table hygiene after the 2024-05 pilot (six false-hit patterns in
docs/gdelt-gkg-pilot-2024-05.md): require_patterns is a per-ALIAS context
gate - the alias only matches entries that also contain one of its
patterns (EFIH "e-Finance"/"eFinance" and MTIE "MM Group" require
"egypt"; OCDI "SODIC" requires "egypt|development"). PHDC and CIRA carry
block patterns (squash-club phrases, "Cira Center/Centre"). SAUD is
restricted to the Egypt aliases ("Al Baraka Bank Egypt", "Al Baraka
Egypt"); the bare "Al Baraka Bank" alias is dropped.

Fetch mode:
  gdelt_gkg_filter.py --aliases evaluation/gdelt_alias_table.csv \
      --start 20240501000000 --end 20240531235959 \
      --master state/masterfilelist.txt \
      --master-translation state/masterfilelist-translation.txt \
      --state state --out out --workers 6 [--budget-seconds 100]

Finalize mode:
  gdelt_gkg_filter.py --finalize --out out
      -> out/matches.parquet (if pyarrow installed) else out/matches.csv,
         out/alias_hit_summary.csv (per ticker x matched org entry counts,
         paired per ticker so multi-issuer rows never cross-pair)

Only https://data.gdeltproject.org URLs are fetched (http master-list
entries are upgraded); files over 200 MB are refused. pyahocorasick and
pyarrow are optional speed/format dependencies of this backfill tool only
(not worker runtime; requirements.txt stays untouched). Without
pyahocorasick the prefilter falls back to one combined regex (about 25x
slower per file); without pyarrow --finalize writes CSV.
"""
import argparse, csv, hashlib, io, json, os, re, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

# 27-column GKG 2.x layout, both streams (see module docstring).
C_ID, C_DATE, C_SOURCE, C_URL, C_THEMES, C_ORGS, C_TONE = 0, 1, 3, 4, 7, 14, 15
N_COLS = 27

ALLOWED_HOST = "data.gdeltproject.org"
MAX_FILE_BYTES = 200 * 1000 * 1000

EG_DOMAINS = {
    "ahram.org.eg", "almasryalyoum.com", "youm7.com", "masrawy.com",
    "shorouknews.com", "elwatannews.com", "dostor.org", "elfagr.org",
    "vetogate.com", "alwafd.org", "akhbarelyom.com", "albawabhnews.com",
    "almalnews.com", "amwalalghad.com", "egypttoday.com",
    "dailynewsegypt.com", "enterprise.press", "arabfinance.com",
    "mubasher.info", "egyptindependent.com", "egx.com.eg", "elbalad.news",
    "cairo24.com", "almesryoon.com", "misr365.com", "elwatan.org",
}

# translate-based normalization: every non-alphanumeric codepoint -> space
# (one-time table build, then ~3x faster than a regex sub per line).
_NORM_TABLE = {i: 32 for i in range(0x110000) if not chr(i).isalnum()}

def norm(s):
    return " ".join(s.lower().translate(_NORM_TABLE).split())

def _make_prefilter(needles):
    """Line prefilter. Fast path: pyahocorasick over the NORMALIZED line
    (pip install pyahocorasick; the 4 TB full run wants it). Fallback: one
    combined regex over the normalized line. Needles are normalized aliases
    plus normalized Egyptian outlet domains."""
    try:
        import ahocorasick

        automaton = ahocorasick.Automaton()
        for i, n in enumerate(needles):
            automaton.add_word(n, i)
        automaton.make_automaton()

        def hit(norm_line):
            return any(True for _ in automaton.iter(norm_line))

        hit.engine = "ahocorasick"
        return hit
    except ImportError:
        pat = re.compile("|".join(sorted((re.escape(n) for n in needles),
                                         key=len, reverse=True)))

        def hit(norm_line):
            return pat.search(norm_line) is not None

        hit.engine = "regex"
        return hit

def load_aliases(path):
    """Return (alias_items, block_map, require_map, prefilter). alias_items:
    list of (normalized alias, tickers) sorted longest first. require_map is
    keyed by normalized alias (not ticker): a context gate on that alias,
    e.g. the generic short aliases, never on full-name aliases."""
    alias_map, block_map, require_map = {}, {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a = norm(r["alias"])
            if not a:
                continue
            alias_map.setdefault(a, set()).add(r["ticker"])
            if r["block_patterns"]:
                block_map.setdefault(r["ticker"], set()).update(
                    norm(b) for b in r["block_patterns"].split("|") if b.strip())
            req = r.get("require_patterns") or ""
            if req:
                require_map.setdefault(a, set()).update(
                    norm(b) for b in req.split("|") if b.strip())
    needles = sorted(alias_map) + sorted(norm(d) for d in EG_DOMAINS)
    prefilter = _make_prefilter(needles)
    alias_items = sorted(alias_map.items(), key=lambda kv: -len(kv[0]))
    return alias_items, block_map, require_map, prefilter

def match_orgs(org_field, alias_items, block_map, require_map):
    """Match V2Organizations entries ('Name,charoffset';'-separated) against
    aliases. Returns {ticker: set(matched raw entry names)} so multi-issuer
    rows never cross-pair a ticker with another ticker's entry. An alias
    with require_patterns matches an entry only when one of its patterns
    also appears in the entry; a require-fail falls through to shorter
    aliases, a successful match (even fully blocked) stops at the longest."""
    by_ticker = {}
    for ent in org_field.split(";"):
        name = ent.rsplit(",", 1)[0] if "," in ent else ent
        n = " " + norm(name) + " "
        if len(n) <= 2:
            continue
        for a, ts in alias_items:
            if " " + a + " " in n:
                reqs = require_map.get(a, ())
                if reqs and not any(" " + q + " " in n for q in reqs):
                    continue  # context-gated alias; try shorter ones
                ok = ts - {t for t in ts
                           if any(" " + b + " " in n for b in block_map.get(t, ()))}
                for t in ok:
                    by_ticker.setdefault(t, set()).add(name.strip())
                break  # most specific (longest) alias wins for this entry
    return by_ticker

def is_eg_domain(source):
    s = source.lower().strip()
    return any(s == d or s.endswith("." + d) for d in EG_DOMAINS)

def parse_tone(field):
    p = field.split(",")
    return (p + [""] * 7)[:7]

def process_blob(name, stream, blob, alias_items, block_map, require_map, prefilter):
    """Returns (rows, n_malformed). Lines with != 27 columns are skipped,
    never parsed with a guessed layout."""
    out = []
    n_malformed = 0
    text = blob.decode("utf-8", errors="replace")
    for line in text.split("\n"):
        if not line or not prefilter(norm(line)):
            continue
        cols = line.split("\t")
        if len(cols) != N_COLS:
            n_malformed += 1
            continue
        src = cols[C_SOURCE]
        eg = is_eg_domain(src)
        by_ticker = match_orgs(cols[C_ORGS], alias_items, block_map, require_map)
        if not by_ticker and not eg:
            continue
        reason = ("both" if eg else "alias") if by_ticker else "eg_domain"
        tone = parse_tone(cols[C_TONE])
        entries = sorted({e for es in by_ticker.values() for e in es})
        out.append({
            "file": name, "stream": stream, "gkg_record_id": cols[C_ID],
            "date": cols[C_DATE], "source": src, "url": cols[C_URL],
            "tickers": sorted(by_ticker),
            "matched_by_ticker": {t: sorted(es) for t, es in sorted(by_ticker.items())},
            "matched_org_entries": entries,
            "reason": reason, "tone": tone[0], "positive": tone[1],
            "negative": tone[2], "word_count": tone[6],
            "themes": cols[C_THEMES][:500],
        })
    return out, n_malformed

def list_files(master_specs, start, end):
    """master_specs: [(path, stream)]. (url, stream) pairs sorted, filtered
    to 14-digit timestamp prefixes in [start, end]."""
    files = []
    for path, stream in master_specs:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) != 3:
                    continue
                url = parts[2]
                base = url.rsplit("/", 1)[-1]
                if not base.endswith(".gkg.csv.zip"):
                    continue
                ts = base.split(".")[0]
                if ts.isdigit() and len(ts) == 14 and start <= ts <= end:
                    files.append((url, stream))
    return sorted(files)

def fetch(url, timeout=90):
    parts = urlsplit(url)
    if parts.netloc != ALLOWED_HOST:
        raise ValueError(f"refusing non-GDELT host: {parts.netloc or url[:40]}")
    if parts.scheme == "http":
        url = "https" + url[len("http"):]
    elif parts.scheme != "https":
        raise ValueError(f"refusing non-HTTPS scheme: {parts.scheme}")
    req = Request(url, headers={"User-Agent": "gdelt-gkg-filter/1.0 (research index)"})
    with urlopen(req, timeout=timeout) as r:
        data = r.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"file over {MAX_FILE_BYTES} bytes")
    return data

def truncate_incomplete_tail(path):
    """Drop a trailing partial line (no final newline) left by a crash
    mid-append, so the next append does not glue onto it. Works on bytes:
    0x0A never occurs inside a UTF-8 multi-byte sequence, so cutting
    after the last newline is byte-safe. Returns the bytes removed. The
    removed record belongs to a file not yet marked done (matches are
    written before the done marker), so it is replayed on the next run."""
    if not os.path.exists(path):
        return 0
    size = os.path.getsize(path)
    if size == 0:
        return 0
    with open(path, "r+b") as f:
        f.seek(size - 1)
        if f.read(1) == b"\n":
            return 0
        pos, cut = size, 0
        while pos > 0:
            step = min(65536, pos)
            pos -= step
            f.seek(pos)
            i = f.read(step).rfind(b"\n")
            if i >= 0:
                cut = pos + i + 1
                break
        f.truncate(cut)
        f.flush()
        os.fsync(f.fileno())
    return size - cut


def run_fetch(a):
    os.makedirs(a.state, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    a.start = a.start.ljust(14, "0")
    a.end = a.end.ljust(14, "9")
    aliases_sha = hashlib.sha256(open(a.aliases, "rb").read()).hexdigest()
    config = {"aliases_sha256": aliases_sha, "start": a.start, "end": a.end,
              "out": os.path.abspath(a.out)}
    config_path = os.path.join(a.state, "config.json")
    if os.path.exists(config_path):
        try:
            old = json.load(open(config_path))
        except (json.JSONDecodeError, OSError) as e:
            sys.exit(f"state config unreadable ({e}); rebind with a fresh --out "
                     f"directory: delete {config_path} and done.txt")
        if old != config:
            sys.exit(f"state config mismatch: {old} vs {config}; rebind with a "
                     f"fresh --out directory (delete {config_path} and done.txt), "
                     f"or delete matches.jsonl as well to reuse the out dir")
    else:
        probe = os.path.join(a.out, "matches.jsonl")
        if os.path.exists(probe) and os.path.getsize(probe) > 0:
            sys.exit(f"{probe} has rows from a previous configuration; use a "
                     f"fresh --out directory or delete it before rebinding")
        # atomic publish: temp + fsync + replace, before any archive is done
        tmp = config_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(config, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, config_path)
    done_path = os.path.join(a.state, "done.txt")
    matches_path = os.path.join(a.out, "matches.jsonl")
    for pth in (matches_path, done_path):
        cut = truncate_incomplete_tail(pth)
        if cut:
            print(f"truncated {cut} bytes of incomplete tail in {pth}", flush=True)
    done = set()
    if os.path.exists(done_path):
        done = set(open(done_path, encoding="utf-8").read().split())
    alias_items, block_map, require_map, prefilter = load_aliases(a.aliases)
    specs = []
    if a.master:
        specs.append((a.master, "english"))
    if a.master_translation:
        specs.append((a.master_translation, "translation"))
    files = [(u, s) for u, s in list_files(specs, a.start, a.end)
             if u.rsplit("/", 1)[-1] not in done]
    t0, n_done, n_bytes, n_rows, n_malformed = time.time(), 0, 0, 0, 0
    print(f"todo={len(files)} done_prev={len(done)} prefilter={prefilter.engine}", flush=True)

    def work(item):
        url, stream = item
        name = url.rsplit("/", 1)[-1]
        try:
            raw = fetch(url)
            z = zipfile.ZipFile(io.BytesIO(raw))
            blob = z.read(z.namelist()[0])
        except Exception as e:
            return name, stream, 0, None, 0, f"{type(e).__name__}: {e}"
        rows, bad = process_blob(name, stream, blob, alias_items, block_map,
                                 require_map, prefilter)
        return name, stream, len(raw), rows, bad, None

    batch = max(a.workers * 4, 8)
    with open(done_path, "a", encoding="utf-8") as done_f, \
         open(matches_path, "a", encoding="utf-8") as out_f, \
         ThreadPoolExecutor(max_workers=a.workers) as ex:
        i = 0
        while i < len(files):
            chunk = files[i:i + batch]
            for name, stream, nbytes, rows, bad, err in ex.map(work, chunk):
                if err:
                    print(f"skip {name}: {err}", flush=True)
                    continue  # NOT marked done: retried on the next run
                for r in rows:
                    out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                out_f.flush()
                os.fsync(out_f.fileno())
                done_f.write(name + "\n")
                done_f.flush()
                os.fsync(done_f.fileno())
                n_done += 1
                n_bytes += nbytes
                n_rows += len(rows)
                n_malformed += bad
            i += batch
            el = time.time() - t0
            rate = n_bytes / 1e6 / el if el else 0
            print(f"progress {n_done}/{len(files)} rows={n_rows} malformed={n_malformed} "
                  f"mb={n_bytes/1e6:.0f} rate={rate:.1f}MB/s elapsed={el:.0f}s", flush=True)
            if a.budget_seconds and el > a.budget_seconds:
                print("budget exhausted; rerun to resume", flush=True)
                break
    print(f"chunk done: processed={n_done} remaining={len(files)-n_done} rows={n_rows}", flush=True)

def run_finalize(a):
    rows, seen, n_corrupt = [], set(), 0
    with open(os.path.join(a.out, "matches.jsonl"), "rb") as f:
        for raw_line in f:
            try:
                # decode per line: a split multi-byte char in an
                # interrupted append must not stop the whole export
                r = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                n_corrupt += 1  # interrupted append; skip, do not block
                continue
            k = (r["gkg_record_id"], r["url"])
            if k in seen:
                continue
            seen.add(k)
            rows.append(r)
    rows.sort(key=lambda r: (r["date"], r["gkg_record_id"]))
    flat = [{
        "gkg_record_id": r["gkg_record_id"], "date": r["date"], "stream": r["stream"],
        "source": r["source"], "url": r["url"], "tickers": ";".join(r["tickers"]),
        "matched_org_entries": ";".join(r["matched_org_entries"]), "reason": r["reason"],
        "tone": r["tone"], "positive": r["positive"], "negative": r["negative"],
        "word_count": r["word_count"], "themes": r["themes"],
    } for r in rows]
    cols = ["gkg_record_id", "date", "stream", "source", "url", "tickers",
            "matched_org_entries", "reason", "tone", "positive", "negative",
            "word_count", "themes"]
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        pq.write_table(pa.Table.from_pylist(flat, schema=pa.schema([(c, pa.string()) for c in cols])),
                       os.path.join(a.out, "matches.parquet"))
        wrote = "matches.parquet"
    except ImportError:
        wrote = "matches.csv"
        with open(os.path.join(a.out, wrote), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(flat)
    # Per ticker x matched org entry, paired per ticker (no cross-pairing).
    counts, days = {}, {}
    for r in rows:
        d = r["date"][:8]
        for t in r["tickers"]:
            days.setdefault(t, set()).add(d)
            entries = r.get("matched_by_ticker", {}).get(t) or r["matched_org_entries"]
            for e in entries:
                counts[(t, e)] = counts.get((t, e), 0) + 1
    with open(os.path.join(a.out, "alias_hit_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "org_entry", "rows", "ticker_distinct_days"])
        for (t, e), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            w.writerow([t, e, n, len(days[t])])
    eg_only = sum(1 for r in rows if r["reason"] == "eg_domain")
    print(f"rows={len(rows)} alias_rows={len(rows)-eg_only} eg_domain_only={eg_only} "
          f"corrupt_lines_skipped={n_corrupt} -> {wrote} + alias_hit_summary.csv")

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--aliases", default="evaluation/gdelt_alias_table.csv")
    p.add_argument("--master")
    p.add_argument("--master-translation")
    p.add_argument("--start", default="20150218235900")  # first GKG 2.0 file
    p.add_argument("--end", default="99999999999999")
    p.add_argument("--state", default="state")
    p.add_argument("--out", default="out")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--budget-seconds", type=float, default=0)
    p.add_argument("--finalize", action="store_true")
    a = p.parse_args()
    if a.finalize:
        run_finalize(a)
    else:
        if not a.master and not a.master_translation:
            p.error("fetch mode needs --master and/or --master-translation")
        run_fetch(a)

if __name__ == "__main__":
    main()
