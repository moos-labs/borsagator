#!/usr/bin/env python3
"""GDELT GKG 2.0 streaming filter (INS-DATA-002 item 2 / G3).

Builds an entity-tagged article INDEX for the EGX33 universe from the free
GDELT bulk files. No key, no signup. GKG gives URL + metadata only, never
article text; this script never fetches article text. No verdicts.

Pipeline (Muhammad's GO, Moos Slack 1795726615.743939, 2026-11-26):
  masterfilelist -> parallel HTTPS fetch -> unzip in memory -> filter rows
  on the alias table (evaluation/gdelt_alias_table.csv) plus Egyptian
  outlet domains -> matched rows appended as JSON lines.

Restart-safe by file name: STATE/done.txt records every fully processed
GKG file; reruns skip it. Matches are appended (fsync) BEFORE the done
marker, so a crash reprocesses at most one file; --finalize dedupes on
(gkg_record_id, url).

Rows kept when EITHER:
  - a V2Organizations entry matches a ticker alias (word-boundary,
    case/punctuation-insensitive) and no per-ticker block pattern matches
    (reason "alias" or "both"), OR
  - SourceCommonName is an Egyptian outlet domain (reason "eg_domain";
    candidates for a later alias-free pass, kept with no ticker).

Fetch mode:
  gdelt_gkg_filter.py --aliases evaluation/gdelt_alias_table.csv \
      --start 20240501000000 --end 20240531235959 \
      --master state/masterfilelist.txt \
      --master-translation state/masterfilelist-translation.txt \
      --state state --out out --workers 6 [--budget-seconds 100]

pyahocorasick and pyarrow are optional speed/format dependencies of this
backfill tool only (not worker runtime; requirements.txt stays untouched).
Without pyahocorasick the prefilter falls back to one combined regex
(about 25x slower per file); without pyarrow --finalize writes CSV.

Finalize mode:
  gdelt_gkg_filter.py --finalize --out out
      -> out/matches.parquet (if pyarrow installed) else out/matches.csv,
         out/alias_hit_summary.csv (per ticker x matched org entry counts)
"""
import argparse, csv, io, json, os, re, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

# GKG 2.x full-format column positions (0-based). English files have 26
# columns; translation files insert a SourceCollectionIdentifier at index 2
# (27 columns), shifting everything after it by one.
C_ID, C_DATE = 0, 1

def col_offsets(ncols):
    off = 1 if ncols >= 27 else 0
    return 2 + off, 3 + off, 6 + off, 13 + off, 14 + off  # source, url, themes, orgs, tone

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

def _needle(alias_norm):
    # Normalized alias -> regex over RAW text: case-insensitive, any
    # non-word run where the normalized form has a space.
    return r"[^\w]+".join(re.escape(p) for p in alias_norm.split(" "))

def load_aliases(path):
    """Return (alias_items, block_map, prefilter_re). alias_items: list of
    (padded-normalized alias, tickers) sorted longest first."""
    alias_map, block_map = {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a = norm(r["alias"])
            if not a:
                continue
            alias_map.setdefault(a, set()).add(r["ticker"])
            if r["block_patterns"]:
                block_map.setdefault(r["ticker"], set()).update(
                    norm(b) for b in r["block_patterns"].split("|") if b.strip())
    needles = sorted(alias_map) + sorted(norm(d) for d in EG_DOMAINS)
    prefilter = _make_prefilter(needles)
    alias_items = sorted(alias_map.items(), key=lambda kv: -len(kv[0]))
    return alias_items, block_map, prefilter

def match_orgs(org_field, alias_items, block_map):
    """Match V2Organizations entries ('Name,charoffset';'-separated) against
    aliases. Returns (tickers, matched raw entry names)."""
    tickers, entries = set(), []
    for ent in org_field.split(";"):
        name = ent.rsplit(",", 1)[0] if "," in ent else ent
        n = " " + norm(name) + " "
        if len(n) <= 2:
            continue
        for a, ts in alias_items:
            if " " + a + " " in n:
                ok = ts - {t for t in ts
                           if any(" " + b + " " in n for b in block_map.get(t, ()))}
                if ok:
                    tickers |= ok
                    entries.append(name.strip())
                break  # most specific (longest) alias wins for this entry
    return tickers, entries

def is_eg_domain(source):
    s = source.lower().strip()
    return any(s == d or s.endswith("." + d) for d in EG_DOMAINS)

def parse_tone(field):
    p = field.split(",")
    return (p + [""] * 7)[:7]

def _make_prefilter(needles):
    """Line prefilter. Fast path: pyahocorasick over the NORMALIZED line
    (pip install pyahocorasick; the 4 TB full run wants it). Fallback: one
    combined regex over the normalized line. Needles are normalized aliases
    plus Egyptian outlet domains."""
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


def process_blob(name, stream, blob, alias_items, block_map, prefilter):
    out = []
    text = blob.decode("utf-8", errors="replace")
    for line in text.split("\n"):
        if not line or not prefilter(norm(line)):
            continue
        cols = line.split("\t")
        if len(cols) < 26:
            continue
        i_src, i_url, i_themes, i_orgs, i_tone = col_offsets(len(cols))
        if len(cols) <= i_tone:
            continue
        src = cols[i_src]
        eg = is_eg_domain(src)
        tickers, entries = match_orgs(cols[i_orgs], alias_items, block_map)
        if not tickers and not eg:
            continue
        reason = ("both" if eg else "alias") if tickers else "eg_domain"
        tone = parse_tone(cols[i_tone])
        out.append({
            "file": name, "stream": stream, "gkg_record_id": cols[C_ID],
            "date": cols[C_DATE], "source": src, "url": cols[i_url],
            "tickers": sorted(tickers), "matched_org_entries": sorted(set(entries)),
            "reason": reason, "tone": tone[0], "positive": tone[1],
            "negative": tone[2], "word_count": tone[6],
            "themes": cols[i_themes][:500],
        })
    return out

def list_files(master_specs, start, end):
    """master_specs: [(path, stream)]. Yields (url, stream) sorted, filtered
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
    req = Request(url, headers={"User-Agent": "gdelt-gkg-filter/1.0 (research index)"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()

def run_fetch(a):
    os.makedirs(a.state, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    done_path = os.path.join(a.state, "done.txt")
    done = set()
    if os.path.exists(done_path):
        done = set(open(done_path).read().split())
    alias_items, block_map, prefilter = load_aliases(a.aliases)
    specs = []
    if a.master:
        specs.append((a.master, "english"))
    if a.master_translation:
        specs.append((a.master_translation, "translation"))
    files = [(u, s) for u, s in list_files(specs, a.start, a.end)
             if u.rsplit("/", 1)[-1] not in done]
    matches_path = os.path.join(a.out, "matches.jsonl")
    t0, n_done, n_bytes, n_rows = time.time(), 0, 0, 0
    print(f"todo={len(files)} done_prev={len(done)}", flush=True)

    def work(item):
        url, stream = item
        name = url.rsplit("/", 1)[-1]
        try:
            raw = fetch(url)
            z = zipfile.ZipFile(io.BytesIO(raw))
            blob = z.read(z.namelist()[0])
        except Exception as e:
            return name, stream, 0, None, f"{type(e).__name__}: {e}"
        rows = process_blob(name, stream, blob, alias_items, block_map, prefilter)
        return name, stream, len(raw), rows, None

    batch = max(a.workers * 4, 8)
    with open(done_path, "a", encoding="utf-8") as done_f, \
         open(matches_path, "a", encoding="utf-8") as out_f, \
         ThreadPoolExecutor(max_workers=a.workers) as ex:
        i = 0
        while i < len(files):
            chunk = files[i:i + batch]
            for name, stream, nbytes, rows, err in ex.map(work, chunk):
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
            i += batch
            el = time.time() - t0
            rate = n_bytes / 1e6 / el if el else 0
            print(f"progress {n_done}/{len(files)} rows={n_rows} "
                  f"mb={n_bytes/1e6:.0f} rate={rate:.1f}MB/s elapsed={el:.0f}s", flush=True)
            if a.budget_seconds and el > a.budget_seconds:
                print(f"budget exhausted; rerun to resume", flush=True)
                break
    print(f"chunk done: processed={n_done} remaining={len(files)-n_done} rows={n_rows}", flush=True)

def run_finalize(a):
    rows, seen = [], set()
    with open(os.path.join(a.out, "matches.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
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
    counts, days = {}, {}
    for r in rows:
        d = r["date"][:8]
        for t in r["tickers"]:
            days.setdefault(t, set()).add(d)
            for e in r["matched_org_entries"]:
                counts[(t, e)] = counts.get((t, e), 0) + 1
    with open(os.path.join(a.out, "alias_hit_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "org_entry", "rows", "ticker_distinct_days"])
        for (t, e), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            w.writerow([t, e, n, len(days[t])])
    eg_only = sum(1 for r in rows if r["reason"] == "eg_domain")
    print(f"rows={len(rows)} alias_rows={len(rows)-eg_only} eg_domain_only={eg_only} -> {wrote} + alias_hit_summary.csv")

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
        a.start = a.start.ljust(14, "0")
        a.end = a.end.ljust(14, "9")
        run_fetch(a)

if __name__ == "__main__":
    main()
