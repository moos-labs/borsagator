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
directory (delete config.json + done.txt + absent.txt + transient.txt:
the absence and transient checkpoints are NOT bound to the configuration,
so a stale absent.txt would exclude a basename a fresh master serves from
a new location before it is ever fetched), or also delete matches.jsonl to
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
      with macro rows present also -> out/macro_matches.parquet (or .csv)
         and out/macro_theme_summary.csv (theme, family, rows, distinct_days)

Macro channel (INS-MACRO-NEWS-001, opt-in via --themes
  evaluation/gdelt_macro_themes.csv): a second, independent capture
  channel for MENA macro research. Rows are captured when a GKG line
  carries at least one configured V1Themes token (exact token match; the
  lookup lists only tokens verified to exist in GDELT theme output, with
  usage counts) AND at least one MENA geo signal from V2EnhancedLocations
  (FIPS10-4 country code in field 3, e.g. EG Egypt / MU Oman / WE West
  Bank / GZ Gaza, or an exact name rule such as suez). EPU_POLICY and
  WB_696_PUBLIC_SECTOR_MANAGEMENT are kind=feature tokens: recorded on
  captured rows as count features, never row filters. Broad buckets like
  GENERAL_HEALTH are excluded by omission from the lookup.
  Macro rows go to out/macro_matches.jsonl (slim schema: file, stream,
  gkg_record_id, date, source, url, themes, families, theme_families,
  features, geo[:5], tone, positive, negative, word_count), never into
  matches.jsonl. State is independent too: STATE/macro_done.txt and
  STATE/macro_config.json (same atomic bind + refuse-on-mismatch semantics
  as config.json; a fresh bind refuses a non-empty macro_matches.jsonl).
  done.txt and matches.jsonl are byte-identical whether or not --themes is
  passed.
  Shard pickup with no progress lost: git pull the merged branch, restart
  the same command plus --themes evaluation/gdelt_macro_themes.csv. The
  company channel resumes from done.txt untouched; macro_done.txt starts
  empty, so files already processed before the restart are reprocessed
  once, macro-only (downloaded once, company rows not rewritten), until
  macro_done.txt catches up; from then on both channels run in the same
  pass.

Only https://data.gdeltproject.org URLs are fetched (http master-list
entries are upgraded); files over 200 MB are refused. pyahocorasick and
pyarrow are optional speed/format dependencies of this backfill tool only
(not worker runtime; requirements.txt stays untouched). Without
pyahocorasick the prefilter falls back to one combined regex (about 25x
slower per file); without pyarrow --finalize writes CSV.
"""
import argparse, contextlib, csv, hashlib, io, json, os, re, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# 27-column GKG 2.x layout, both streams (see module docstring).
C_ID, C_DATE, C_SOURCE, C_URL, C_THEMES, C_LOCS, C_ORGS, C_TONE = 0, 1, 3, 4, 7, 10, 14, 15
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

def load_aliases(path, extra_needles=()):
    """Return (alias_items, block_map, require_map, prefilter). alias_items:
    list of (normalized alias, tickers) sorted longest first. require_map is
    keyed by normalized alias (not ticker): a context gate on that alias,
    e.g. the generic short aliases, never on full-name aliases. extra_needles
    are added to the line prefilter (macro theme capture)."""
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
    needles += sorted(extra_needles)
    prefilter = _make_prefilter(needles)
    alias_items = sorted(alias_map.items(), key=lambda kv: -len(kv[0]))
    return alias_items, block_map, require_map, prefilter

def load_themes(path):
    """Macro theme lookup (evaluation/gdelt_macro_themes.csv). Returns
    (theme_to_family, geo_countries, geo_names, feature_tokens, sha256 of
    the file). kind=theme rows are exact V1Themes tokens that capture a
    row; kind=feature rows are exact tokens counted on captured rows but
    never capturing one themselves (EPU_POLICY, WB_696_PUBLIC_SECTOR_MANAGEMENT);
    kind=geo rows are 'country:<FIPS code>' matched on V2EnhancedLocations
    field 3 or 'name:<substring>' matched on the lowercased location full
    name. A row is captured only when BOTH a theme and a geo rule match
    (Egypt/Suez/MENA scope, per the INS-MACRO-NEWS-001 design)."""
    theme2family, geo_countries, geo_names, features = {}, set(), set(), set()
    with open(path, newline="", encoding="utf-8") as f:
        raw = f.read()
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    for r in csv.DictReader(io.StringIO(raw)):
        kind, val = (r.get("kind") or "").strip(), (r.get("value") or "").strip()
        if not val:
            continue
        if kind == "theme":
            theme2family[val] = (r.get("family") or "").strip()
        elif kind == "feature":
            features.add(val)
        elif kind == "geo" and val.startswith("country:"):
            geo_countries.add(val.split(":", 1)[1].strip())
        elif kind == "geo" and val.startswith("name:"):
            geo_names.add(val.split(":", 1)[1].strip().lower())
    return theme2family, geo_countries, geo_names, features, sha

def match_macro(themes_field, locs_field, theme2family, geo_countries,
                geo_names, feature_tokens=frozenset()):
    """Capture a row for the macro channel: at least one exact V1Themes token
    in the lookup AND at least one V2EnhancedLocations entry matching the geo
    rules. Returns (matched {theme: family}, sorted families, geo hits,
    feature hits) or None. Theme matching is exact-token, never substring;
    geo hits are kept as location names (capped) for review. Feature tokens
    (EPU_POLICY, WB_696_PUBLIC_SECTOR_MANAGEMENT) are counted on captured
    rows but never capture a row by themselves."""
    matched = {}
    feats = []
    for tok in themes_field.split(";"):
        tok = tok.strip()
        fam = theme2family.get(tok)
        if fam is not None:
            matched[tok] = fam
        elif tok in feature_tokens:
            feats.append(tok)
    if not matched:
        return None
    geo_hits = []
    for ent in locs_field.split(";"):
        parts = ent.split("#")
        if len(parts) < 3:
            continue
        fullname, cc = parts[1], parts[2]
        if cc in geo_countries:
            geo_hits.append(fullname or cc)
        elif any(n in fullname.lower() for n in geo_names):
            geo_hits.append(fullname)
    if not geo_hits:
        return None
    return matched, sorted(set(matched.values())), geo_hits[:5], feats

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

def process_blob(name, stream, blob, alias_items, block_map, require_map, prefilter,
                 macro=None, do_company=True, do_macro=False):
    """Returns (rows, macro_rows, n_malformed). Lines with != 27 columns are
    skipped, never parsed with a guessed layout. macro is the load_themes()
    triple; do_company/do_macro select the channels computed for THIS file
    (a file already in done.txt still gets macro-only processing until it
    lands in macro_done.txt)."""
    out, macro_out = [], []
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
        if do_company:
            eg = is_eg_domain(src)
            by_ticker = match_orgs(cols[C_ORGS], alias_items, block_map, require_map)
            if by_ticker or eg:
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
        if do_macro and macro is not None:
            theme2family, geo_countries, geo_names, feature_tokens = macro
            mm = match_macro(cols[C_THEMES], cols[C_LOCS],
                             theme2family, geo_countries, geo_names,
                             feature_tokens)
            if mm is not None:
                matched, families, geo_hits, feats = mm
                tone = parse_tone(cols[C_TONE])
                macro_out.append({
                    "file": name, "stream": stream, "gkg_record_id": cols[C_ID],
                    "date": cols[C_DATE], "source": src, "url": cols[C_URL],
                    "themes": sorted(matched), "families": families,
                    "theme_families": matched, "features": feats,
                    "geo": geo_hits,
                    "tone": tone[0], "positive": tone[1],
                    "negative": tone[2], "word_count": tone[6],
                })
    return out, macro_out, n_malformed

def list_files(master_specs, start, end):
    """master_specs: [(path, stream)]. (url, stream) pairs sorted, filtered
    to 14-digit timestamp prefixes in [start, end]."""
    files = []
    seen = {}   # (stream, basename) -> url: 959n F3 dedup / conflict check
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
                    key = (stream, base)
                    if key in seen:
                        if seen[key] != url:
                            # Same archive name, different URL: which bytes
                            # belong to the done marker is undecidable.
                            sys.exit(f"master listing names {base} twice with "
                                     f"different URLs ({stream}); refusing")
                        continue   # an exact duplicate entry is scheduled once
                    seen[key] = url
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

def reconcile_orphan_rows(path, done_names):
    """Rows are fsynced BEFORE the file's done marker, so a stop between the
    two leaves rows for a file that is not done; resume re-selects that file
    and would append them again. Drop every row whose `file` is not in
    done_names (atomic rewrite) so the replay writes them exactly once.
    Unparseable lines are kept. Returns the number of rows dropped."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return 0
    def _is_orphan(line):
        try:
            nm = json.loads(line).get("file")
        except (ValueError, AttributeError):
            nm = None
        return nm is not None and nm not in done_names

    # Pass 1: count orphans without retaining any line (bounded memory).
    dropped = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if _is_orphan(line):
                dropped += 1
    if dropped:
        # Pass 2: stream the surviving rows to the temp file.
        tmp = path + ".tmp"
        with open(path, encoding="utf-8") as f, open(tmp, "w", encoding="utf-8") as out:
            for line in f:
                if not _is_orphan(line):
                    out.write(line)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        fsync_dir(os.path.dirname(os.path.abspath(path)))
    return dropped


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


def fsync_dir(path):
    """fsync a directory so newly created entries survive an OS crash."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def makedirs_durable(path):
    """makedirs that also makes every directory it CREATED durable: each new
    directory is fsynced, and so is its parent (the parent holds the new
    entry). Ancestors that already existed are only synced as the parent of
    the first new one. Errors propagate."""
    path = os.path.abspath(path)
    created = []
    p = path
    while p and not os.path.isdir(p):
        created.append(p)
        nxt = os.path.dirname(p)
        if nxt == p:
            break
        p = nxt
    os.makedirs(path, exist_ok=True)
    for d in created:
        fsync_dir(d)
        fsync_dir(os.path.dirname(d))
    # 959n F1: a retry finds the directory already there (created == []) yet
    # the first attempt may have died before the entry naming it was synced.
    # Always sync the parent that holds its entry (the directory's own
    # contents are synced by the caller's fsync_dir(state/out)).
    fsync_dir(os.path.dirname(path))


# Exit status for a retryable checkpoint I/O failure (EX_TEMPFAIL); every
# other sys.exit(<message>) is a deterministic configuration refusal (1).
CHECKPOINT_IO_EXIT = 75


@contextlib.contextmanager
def ck_setup(opened=()):
    """Checkpoint creation, opening and the initial directory sync are
    retryable I/O: an OSError here exits CHECKPOINT_IO_EXIT with safe=0
    (the checkpoint is not authorised for publication) instead of escaping
    as exit 1. `opened` holds files already open, closed best-effort first.
    Deliberate configuration refusals are SystemExit messages and pass
    through unchanged."""
    try:
        yield
    except OSError as e:
        for f in list(opened):
            try:
                f.close()
            except OSError:
                pass
        print(f"gkg-filter-checkpoint-error safe=0 setup {type(e).__name__}", flush=True)
        sys.exit(CHECKPOINT_IO_EXIT)


def run_fetch(a):
    with ck_setup():
        makedirs_durable(a.state)
        makedirs_durable(a.out)
    a.start = a.start.ljust(14, "0")
    a.end = a.end.ljust(14, "9")
    aliases_sha = hashlib.sha256(open(a.aliases, "rb").read()).hexdigest()
    config = {"aliases_sha256": aliases_sha, "start": a.start, "end": a.end,
              "out": os.path.abspath(a.out)}
    config_path = os.path.join(a.state, "config.json")
    if os.path.exists(config_path):
        with ck_setup():          # a read OSError is retryable (75), not a refusal
            with open(config_path, encoding="utf-8") as _f:
                _txt = _f.read()
        try:
            old = json.loads(_txt)
        except ValueError as e:
            sys.exit(f"state config unreadable ({e}); rebind with a fresh --out "
                     f"directory AND a fresh --state (the other channel's config still names the old out dir), "
                     f"or rebuild only this channel in the existing out dir: delete {config_path}, done.txt, absent.txt, transient.txt and matches.jsonl")
        if old != config:
            sys.exit(f"state config mismatch: {old} vs {config}; rebind with a "
                     f"fresh --out directory AND a fresh --state (the other channel's config still names the old out dir), "
                     f"or rebuild only this channel in the existing out dir (delete {config_path}, done.txt, absent.txt and transient.txt, "
                     f"and matches.jsonl)")
    else:
        probe = os.path.join(a.out, "matches.jsonl")
        if os.path.exists(probe) and os.path.getsize(probe) > 0:
            sys.exit(f"{probe} has rows from a previous configuration; use a "
                     f"fresh --out directory or delete it before rebinding")
        # atomic publish: temp + fsync + replace, before any archive is done
        tmp = config_path + ".tmp"
        with ck_setup():
            with open(tmp, "w") as f:
                json.dump(config, f, indent=1)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, config_path)
    done_path = os.path.join(a.state, "done.txt")
    matches_path = os.path.join(a.out, "matches.jsonl")
    # absent.txt: files GDELT answered with HTTP 404 (permanent). Kept
    # apart from done.txt (never marks a file done) and written per file
    # with fsync as discovered, so a budget-killed run still records
    # them and a resumed run does not re-download them.
    absent_path = os.path.join(a.state, "absent.txt")
    # transient.txt: one line per TRANSIENT failure of a file (never absent,
    # never done). Persisted across runs so a later run scans files that
    # have not failed (or failed less often) before repeating the failures.
    transient_path = os.path.join(a.state, "transient.txt")
    for pth in (matches_path, done_path, absent_path, transient_path):
        with ck_setup():
            cut = truncate_incomplete_tail(pth)
        if cut:
            print(f"truncated {cut} bytes of incomplete tail in {pth}", flush=True)
    # Checkpoint READS are retryable I/O too: an OSError here is exit 75
    # (safe=0, nothing published), never an exit-1 the worker could archive.
    done, absent, transient = set(), set(), {}
    with ck_setup():
        if os.path.exists(done_path):
            with open(done_path, encoding="utf-8") as _f:
                done = set(_f.read().split())
        if os.path.exists(absent_path):
            with open(absent_path, encoding="utf-8") as _f:
                absent = set(_f.read().split())
        if os.path.exists(transient_path):
            with open(transient_path, encoding="utf-8") as _f:
                for nm in _f.read().split():
                    transient[nm] = transient.get(nm, 0) + 1
    with ck_setup():
        n_orphan = reconcile_orphan_rows(matches_path, done)
    if n_orphan:
        print(f"reconciled {n_orphan} rows of files not marked done in {matches_path}", flush=True)
    macro = None
    macro_done = set()
    macro_matches_path = os.path.join(a.out, "macro_matches.jsonl")
    md_path = os.path.join(a.state, "macro_done.txt")
    if getattr(a, "themes", None):
        theme2family, geo_countries, geo_names, feature_tokens, tsha = load_themes(a.themes)
        macro = (theme2family, geo_countries, geo_names, feature_tokens)
        mcfg = {"themes_sha256": tsha, "start": a.start, "end": a.end,
                "out": os.path.abspath(a.out)}
        mcfg_path = os.path.join(a.state, "macro_config.json")
        if os.path.exists(mcfg_path):
            with ck_setup():
                with open(mcfg_path, encoding="utf-8") as _f:
                    _txt = _f.read()
            try:
                oldm = json.loads(_txt)
            except ValueError as e:
                sys.exit(f"macro state config unreadable ({e}); rebind with a fresh --out "
                         f"directory AND a fresh --state (the other channel's config still names the old out dir), "
                         f"or rebuild only this channel in the existing out dir: delete {mcfg_path}, macro_done.txt, absent.txt, transient.txt and macro_matches.jsonl")
            if oldm != mcfg:
                sys.exit(f"macro state config mismatch: {oldm} vs {mcfg}; rebind with a "
                         f"fresh --out directory AND a fresh --state (the other channel's config still names the old out dir), "
                         f"or rebuild only this channel in the existing out dir (delete {mcfg_path}, macro_done.txt, absent.txt and transient.txt, "
                         f"and macro_matches.jsonl)")
        else:
            if os.path.exists(macro_matches_path) and os.path.getsize(macro_matches_path) > 0:
                sys.exit(f"{macro_matches_path} has rows from a previous configuration; use a "
                         f"fresh --out directory or delete it before rebinding")
            tmp = mcfg_path + ".tmp"
            with ck_setup():
                with open(tmp, "w") as f:
                    json.dump(mcfg, f, indent=1)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, mcfg_path)
        for pth in (macro_matches_path, md_path):
            with ck_setup():
                cut = truncate_incomplete_tail(pth)
            if cut:
                print(f"truncated {cut} bytes of incomplete tail in {pth}", flush=True)
        with ck_setup():
            if os.path.exists(md_path):
                with open(md_path, encoding="utf-8") as _f:
                    macro_done = set(_f.read().split())
            n_orphan = reconcile_orphan_rows(macro_matches_path, macro_done)
        if n_orphan:
            print(f"reconciled {n_orphan} rows of files not marked done in {macro_matches_path}", flush=True)
    extra_needles = ([norm(t) for t in macro[0]] + [norm(n) for n in macro[2]]) if macro else ()
    alias_items, block_map, require_map, prefilter = load_aliases(a.aliases, extra_needles=extra_needles)
    specs = []
    if a.master:
        specs.append((a.master, "english"))
    if a.master_translation:
        specs.append((a.master_translation, "translation"))
    files = []
    for u, s in list_files(specs, a.start, a.end):
        name = u.rsplit("/", 1)[-1]
        if name in absent:
            continue
        need_c = name not in done
        need_m = macro is not None and name not in macro_done
        if need_c or need_m:
            files.append((u, s, need_c, need_m))
    # Stable sort: fewest recorded transient failures first, listing order
    # inside a tier. Files never attempted (or never failed) run before
    # repeat failures, so a failing prefix cannot starve the rest.
    files.sort(key=lambda it: transient.get(it[0].rsplit("/", 1)[-1], 0))
    t0, n_done, n_bytes, n_rows, n_mrows, n_malformed = time.time(), 0, 0, 0, 0, 0
    n_unfinished, n_absent = 0, 0
    print(f"todo={len(files)} done_prev={len(done)} macro_done_prev={len(macro_done)} "
          f"absent_prev={len(absent)} prefilter={prefilter.engine}", flush=True)

    def work(item):
        url, stream, need_c, need_m = item
        name = url.rsplit("/", 1)[-1]
        try:
            raw = fetch(url)
            z = zipfile.ZipFile(io.BytesIO(raw))
            blob = z.read(z.namelist()[0])
        except Exception as e:
            # A listed file that GDELT answers with HTTP 404 is ABSENT
            # (permanent, e.g. a translation file it never served); any
            # other failure is transient or corrupt and stays unfinished.
            tag = "absent: " if isinstance(e, HTTPError) and e.code == 404 else ""
            return name, stream, 0, None, None, 0, need_c, need_m, f"{tag}{type(e).__name__}: {e}"
        rows, mrows, bad = process_blob(name, stream, blob, alias_items, block_map,
                                        require_map, prefilter, macro=macro,
                                        do_company=need_c, do_macro=need_m)
        return name, stream, len(raw), rows, mrows, bad, need_c, need_m, None

    batch = max(a.workers * 4, 8)
    state_dir = os.path.dirname(os.path.abspath(done_path))
    opened = []

    def _open(path):
        f = open(path, "a", encoding="utf-8")
        opened.append(f)
        return f
    with ck_setup(opened):
        done_f = _open(done_path)
        absent_f = _open(absent_path)
        out_f = _open(matches_path)
        macro_f = _open(macro_matches_path) if macro else None
        mdone_f = _open(md_path) if macro else None
        transient_f = _open(transient_path)
        # New checkpoint files exist only once their directory entry is durable;
        # per-record fsync below persists contents only.
        fsync_dir(state_dir)
        if os.path.abspath(a.out) != state_dir:
            fsync_dir(os.path.abspath(a.out))
    ck_err = None
    phase = "data"
    try:
      try:
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            i = 0
            while i < len(files):
                chunk = files[i:i + batch]
                for name, stream, nbytes, rows, mrows, bad, need_c, need_m, err in ex.map(work, chunk):
                    if err:
                        # NOT marked done either way: retried on the next run.
                        phase = "record"   # absent/transient records only
                        if err.startswith("absent: "):
                            n_absent += 1
                            if name not in absent:
                                absent.add(name)
                                absent_f.write(name + "\n")
                                absent_f.flush()
                                os.fsync(absent_f.fileno())
                            print(f"absent {name}: {err[len('absent: '):]}", flush=True)
                        else:
                            n_unfinished += 1
                            transient_f.write(name + "\n")
                            transient_f.flush()
                            os.fsync(transient_f.fileno())
                            print(f"skip {name}: {err}", flush=True)
                        phase = "data"
                        continue
                    if need_c:
                        for r in rows:
                            out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        out_f.flush()
                        os.fsync(out_f.fileno())
                        done_f.write(name + "\n")
                        done_f.flush()
                        os.fsync(done_f.fileno())
                    if need_m:
                        for r in mrows:
                            macro_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        macro_f.flush()
                        os.fsync(macro_f.fileno())
                        mdone_f.write(name + "\n")
                        mdone_f.flush()
                        os.fsync(mdone_f.fileno())
                    n_done += 1
                    n_bytes += nbytes
                    n_rows += len(rows)
                    n_mrows += len(mrows)
                    n_malformed += bad
                i += batch
                el = time.time() - t0
                rate = n_bytes / 1e6 / el if el else 0
                print(f"progress {n_done}/{len(files)} rows={n_rows} macro_rows={n_mrows} malformed={n_malformed} "
                      f"mb={n_bytes/1e6:.0f} rate={rate:.1f}MB/s elapsed={el:.0f}s", flush=True)
                if a.budget_seconds and el > a.budget_seconds and i < len(files):
                    print("budget exhausted; rerun to resume", flush=True)
                    break
      except OSError as e:
        # A checkpoint write/fsync failed. Never fall through to the
        # unfinished summary: that reads as a clean pass. A failed
        # absent/transient record loses only a skip hint (the file is
        # neither done nor absent, so it is retried): the checkpoint is
        # safe to reuse. A failed match/done write leaves its tail to the
        # next run's repair and is reported as NOT safe.
        ck_err = (phase == "record", e)
    finally:
        # Attempt EVERY close: a failing close must not skip the others or
        # bypass the checkpoint exit. A close error on a match/done file
        # leaves that data uncertain (safe=0); on absent/transient only a
        # skip hint is at risk.
        data_close_err = hint_close_err = None
        for f, is_data in ((done_f, True), (out_f, True), (macro_f, True),
                           (mdone_f, True), (absent_f, False), (transient_f, False)):
            if f is None:
                continue
            try:
                f.close()
            except OSError as e:
                if is_data:
                    data_close_err = data_close_err or e
                else:
                    hint_close_err = hint_close_err or e
    close_err = data_close_err or hint_close_err
    if close_err is not None and ck_err is None:
        ck_err = (True, close_err)
    if ck_err is not None:
        safe = ck_err[0] and data_close_err is None
        print(f"gkg-filter-checkpoint-error safe={int(safe)} {type(ck_err[1]).__name__}", flush=True)
        sys.exit(CHECKPOINT_IO_EXIT)
    print(f"chunk done: processed={n_done} remaining={len(files)-n_done} rows={n_rows} macro_rows={n_mrows}", flush=True)
    # Machine-readable: files that failed for a reason other than a
    # permanent HTTP 404 (unfinished) and files GDELT does not serve (absent).
    print(f"gkg-filter-status unfinished={n_unfinished} absent={n_absent}", flush=True)

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
    mpath = os.path.join(a.out, "macro_matches.jsonl")
    if os.path.exists(mpath):
        mrows, mseen, m_corrupt = [], set(), 0
        with open(mpath, "rb") as f:
            for raw_line in f:
                try:
                    r = json.loads(raw_line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    m_corrupt += 1  # interrupted append; skip, do not block
                    continue
                k = (r["gkg_record_id"], r["url"])
                if k in mseen:
                    continue
                mseen.add(k)
                mrows.append(r)
        mrows.sort(key=lambda r: (r["date"], r["gkg_record_id"]))
        mflat = [{
            "gkg_record_id": r["gkg_record_id"], "date": r["date"], "stream": r["stream"],
            "source": r["source"], "url": r["url"], "themes": ";".join(r["themes"]),
            "families": ";".join(r["families"]), "features": ";".join(r["features"]),
            "geo": ";".join(r["geo"]),
            "tone": r["tone"], "positive": r["positive"], "negative": r["negative"],
            "word_count": r["word_count"],
        } for r in mrows]
        mcols = ["gkg_record_id", "date", "stream", "source", "url", "themes",
                 "families", "features", "geo", "tone", "positive", "negative", "word_count"]
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            pq.write_table(pa.Table.from_pylist(mflat, schema=pa.schema([(c, pa.string()) for c in mcols])),
                           os.path.join(a.out, "macro_matches.parquet"))
            mwrote = "macro_matches.parquet"
        except ImportError:
            mwrote = "macro_matches.csv"
            with open(os.path.join(a.out, mwrote), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=mcols)
                w.writeheader()
                w.writerows(mflat)
        tcounts, tdays, tfam = {}, {}, {}
        for r in mrows:
            d = r["date"][:8]
            for t, f2 in r["theme_families"].items():
                tdays.setdefault(t, set()).add(d)
                tcounts[t] = tcounts.get(t, 0) + 1
                tfam[t] = f2
        with open(os.path.join(a.out, "macro_theme_summary.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["theme", "family", "rows", "distinct_days"])
            for t, n in sorted(tcounts.items(), key=lambda kv: (-kv[1], kv[0])):
                w.writerow([t, tfam[t], n, len(tdays[t])])
        print(f"macro_rows={len(mrows)} corrupt_lines_skipped={m_corrupt} -> "
              f"{mwrote} + macro_theme_summary.csv")

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--aliases", default="evaluation/gdelt_alias_table.csv")
    p.add_argument("--themes", help="macro theme lookup CSV (evaluation/gdelt_macro_themes.csv); "
                   "enables the parallel macro channel (macro_matches.jsonl + macro_done.txt)",
                   default=None)
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
