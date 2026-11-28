#!/usr/bin/env python3
"""Tests for scripts/gdelt_gkg_filter.py (INS-DATA-002 item 2, G3 pilot).
Standalone, stdlib only, synthetic 27-column GKG rows, no network."""
import contextlib
import csv
import io
import importlib.util
import json
import os
import sys
import tempfile
import time
import tracemalloc
import zipfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    CHECKS["pass" if ok else "fail"] += 1
    if not ok:
        print("FAIL %s %s" % (name, detail))


def load(name, fn):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "scripts", fn))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


G = load("gkg_t", "gdelt_gkg_filter.py")

ALIASES_CSV = os.path.join(ROOT, "evaluation", "gdelt_alias_table.csv")


def gkg_line(rec="20240515000000-T1075", date="20240515000000",
             source="dostor.org", url="https://www.dostor.org/1",
             orgs="Telecom Egypt,123", themes="ECON_STOCKMARKET",
             locs="", tone="1.27,2.22,0.95,3.17,1.5,0.5,400", ncols=27):
    """27-column layout, both streams: id 0, date 1, source-collection-id 2,
    source 3, url 4, themes 7, locations 10, orgs 14, tone 15."""
    cols = [""] * ncols
    if ncols == 27:
        cols[0], cols[1], cols[2] = rec, date, "1"
        cols[3], cols[4] = source, url
        cols[7], cols[10], cols[14], cols[15] = themes, locs, orgs, tone
    return "\t".join(cols)


def loaded():
    return G.load_aliases(ALIASES_CSV)


def test_alias_table_loads():
    items, blocks, reqs, pre = loaded()
    tickers = {t for _, ts in items for t in ts}
    check("38 tickers", len(tickers) == 38, str(len(tickers)))
    check("every alias nonempty", all(a.strip() for a, _ in items))
    check("prefilter hits normalized line",
          pre(G.norm("x Telecom Egypt y")) and not pre(G.norm("x Vodafone y")))
    check("blocks lowercase-normalized",
          all(b == b.lower() for bs in blocks.values() for b in bs))
    check("requires lowercase-normalized",
          all(q == q.lower() for qs in reqs.values() for q in qs))
    check("PHDC block present",
          "club palm hills" in blocks.get("PHDC", set()), str(blocks.get("PHDC")))
    check("require map keyed by alias",
          reqs.get("e finance") == {"egypt"}
          and reqs.get("sodic") == {"egypt", "development"}
          and reqs.get("mm group") == {"egypt"}, str(reqs))


def test_match_orgs_real():
    items, blocks, reqs, _ = loaded()
    bt = G.match_orgs("Telecom Egypt,10;Vodafone Egypt,55", items, blocks, reqs)
    check("ETEL matched", set(bt) == {"ETEL"}, str(bt))
    check("entry captured", bt["ETEL"] == {"Telecom Egypt"}, str(bt))
    bt = G.match_orgs("Talaat Moustafa Group Holdings,3", items, blocks, reqs)
    check("TMGH via alt", set(bt) == {"TMGH"}, str(bt))
    bt = G.match_orgs("Commercial International Bank,7", items, blocks, reqs)
    check("COMI via bank alias", set(bt) == {"COMI"}, str(bt))
    bt = G.match_orgs("المصرية للاتصالات,9", items, blocks, reqs)
    check("ETEL via verified arabic", set(bt) == {"ETEL"}, str(bt))
    bt = G.match_orgs("Telecom Egypt,1;Talaat Moustafa Group,2", items, blocks, reqs)
    check("multi-issuer pairing exact",
          bt.get("ETEL") == {"Telecom Egypt"}
          and bt.get("TMGH") == {"Talaat Moustafa Group"}, str(bt))


def test_match_orgs_blocks_and_noise():
    items, blocks, reqs, _ = loaded()
    check("Club Palm Hills blocked for PHDC",
          G.match_orgs("Club Palm Hills,20", items, blocks, reqs) == {})
    bt = G.match_orgs("Palm Hills Developments,20", items, blocks, reqs)
    check("Palm Hills Developments matches PHDC", set(bt) == {"PHDC"}, str(bt))
    check("no COMI on bare 'Commercial International'",
          G.match_orgs("Negotiations Commercial International,4", items, blocks, reqs) == {})
    check("Telecom Egypt Confidence blocked for ETEL",
          G.match_orgs("Telecom Egypt Confidence,4", items, blocks, reqs) == {})
    check("Egyptian Exchange (the bourse) matches nothing",
          G.match_orgs("Egyptian Exchange,4", items, blocks, reqs) == {})


def test_pilot_six_fixes():
    """The six false-hit patterns from docs/gdelt-gkg-pilot-2024-05.md."""
    items, blocks, reqs, _ = loaded()
    m = lambda orgs: G.match_orgs(orgs, items, blocks, reqs)
    # 1. EFIH: generic 'E Finance' needs Egypt context; full names stand alone
    check("EFIH bare 'E Finance' dropped", m("E Finance,3") == {})
    check("EFIH bare 'eFinance' dropped", m("eFinance,3") == {})
    check("EFIH 'E-Finance Egypt' kept", set(m("E-Finance Egypt,3")) == {"EFIH"})
    check("EFIH full-name variant without context",
          set(m("E-Finance for Digital and Financial Investments SAE,3")) == {"EFIH"})
    check("EFIH canonical (typo) full name without context",
          set(m("E-Finance For Digital and Financial Investements SAE,3")) == {"EFIH"})
    # 2. PHDC: squash-club phrases blocked
    check("PHDC 'Palm Hills Club' blocked", m("Palm Hills Club,3") == {})
    check("PHDC 'Palm Hills Sports Club' blocked", m("Palm Hills Sports Club,3") == {})
    check("PHDC 'Academy Palm Hills' blocked", m("Academy Palm Hills,3") == {})
    check("PHDC developer still matches",
          set(m("Palm Hills Development Company,3")) == {"PHDC"})
    # 3. SAUD: Egypt variants only
    check("SAUD 'Al Baraka Bank Pakistan' dropped", m("Al Baraka Bank Pakistan,3") == {})
    check("SAUD 'Al Baraka Bank Tunisia' dropped", m("Al Baraka Bank Tunisia,3") == {})
    check("SAUD bare 'Al Baraka Bank' dropped", m("Al Baraka Bank,3") == {})
    check("SAUD 'Al Baraka Group' dropped", m("Al Baraka Group,3") == {})
    check("SAUD 'Al Baraka Bank Egypt' kept", set(m("Al Baraka Bank Egypt,3")) == {"SAUD"})
    check("SAUD 'Al Baraka Egypt' kept", set(m("Al Baraka Egypt,3")) == {"SAUD"})
    # 4. CIRA: Philadelphia building blocked
    check("CIRA 'Cira Center' blocked", m("Cira Center,3") == {})
    check("CIRA 'Cira Centre' blocked", m("Cira Centre,3") == {})
    check("CIRA Education kept", set(m("CIRA Education,3")) == {"CIRA"})
    # 5. OCDI: bare 'Sodic' (soil term) needs Egypt/development context
    check("OCDI bare 'Sodic' dropped", m("Sodic,3") == {})
    check("OCDI 'SODIC Egypt' kept", set(m("SODIC Egypt,3")) == {"OCDI"})
    check("OCDI full name without context",
          set(m("Six of October Development and Investment,3")) == {"OCDI"})
    # 6. MTIE: 'MM Group' needs Egypt context; long aliases stand alone
    check("MTIE bare 'MM Group' dropped", m("MM Group,3") == {})
    check("MTIE 'MM Group Egypt' kept", set(m("MM Group Egypt,3")) == {"MTIE"})
    check("MTIE long alias without context",
          set(m("MM Group for Industry and International Trade,3")) == {"MTIE"})
    # require-fail falls through to a shorter alias of another ticker
    bt = m("E Finance,1;Telecom Egypt,2")
    check("require-fail does not eat sibling entries",
          set(bt) == {"ETEL"}, str(bt))


def test_process_blob():
    items, blocks, reqs, pre = loaded()
    lines = "\n".join([
        gkg_line(rec="R1", orgs="Telecom Egypt,10"),
        gkg_line(rec="R2", orgs="Club Palm Hills,5", source="example.com",
                 url="https://example.com/a"),
        gkg_line(rec="R3", orgs="", source="almasryalyoum.com",
                 url="https://www.almasryalyoum.com/news/details/1"),
        gkg_line(rec="R4", orgs="Unrelated Corp,1", source="example.net",
                 url="https://example.net/b"),
        gkg_line(rec="R6", orgs="Telecom Egypt,1;Talaat Moustafa Group,2",
                 source="reuters.com", url="https://www.reuters.com/x"),
        "too\tfew\ttelecom egypt",  # hits the prefilter, then malformed
    ])
    rows, mrows, bad = G.process_blob("20240515000000.gkg.csv.zip", "english",
                               lines.encode(), items, blocks, reqs, pre)
    by_id = {r["gkg_record_id"]: r for r in rows}
    check("R1 alias+both", by_id["R1"]["reason"] == "both"
          and by_id["R1"]["tickers"] == ["ETEL"], str(by_id.get("R1")))
    check("R1 source/url from 27-col positions",
          by_id["R1"]["source"] == "dostor.org"
          and by_id["R1"]["url"] == "https://www.dostor.org/1")
    check("R2 blocked -> dropped", "R2" not in by_id)
    check("R3 eg_domain only, no tickers", by_id["R3"]["reason"] == "eg_domain"
          and by_id["R3"]["tickers"] == [], str(by_id.get("R3")))
    check("R4 noise dropped", "R4" not in by_id)
    check("non-27-col line counted malformed", bad == 1, str(bad))
    check("R6 matched_by_ticker paired",
          by_id["R6"]["matched_by_ticker"] == {
              "ETEL": ["Telecom Egypt"], "TMGH": ["Talaat Moustafa Group"]},
          str(by_id.get("R6")))
    check("tone parsed", by_id["R1"]["tone"] == "1.27"
          and by_id["R1"]["word_count"] == "400")
    check("blob without needles yields nothing",
          G.process_blob("f", "english", gkg_line(
              rec="Z", orgs="Nope,1", source="x.io",
              url="https://x.io/").encode(), items, blocks, reqs, pre) == ([], [], 0))


THEMES_CSV = os.path.join(ROOT, "evaluation", "gdelt_macro_themes.csv")


def test_macro_filter():
    t2f, countries, names, feats, sha = G.load_themes(THEMES_CSV)
    check("macro lookup: verified token present",
          t2f.get("ECON_INFLATION") == "monetary_fx")
    check("macro lookup: fabricated name absent", "ECON_INTERESTRATES" not in t2f)
    check("macro lookup: EPU_POLICY is feature-only",
          "EPU_POLICY" in feats and "EPU_POLICY" not in t2f)
    check("macro lookup: WB_696 is feature-only",
          "WB_696_PUBLIC_SECTOR_MANAGEMENT" in feats
          and "WB_696_PUBLIC_SECTOR_MANAGEMENT" not in t2f)
    check("macro lookup: too-broad bucket excluded", "GENERAL_HEALTH" not in t2f)
    check("macro lookup: geo parsed",
          "EG" in countries and "MU" in countries and "suez" in names)
    check("macro lookup: sha", len(sha) == 64)
    items, blocks, reqs, _ = loaded()
    needles = ([G.norm(t) for t in t2f] + [G.norm(n) for n in names])
    pre = G.load_aliases(ALIASES_CSV, extra_needles=needles)[3]
    macro = (t2f, countries, names, feats)

    def blob(lines):
        return G.process_blob("f", "english", "\n".join(lines).encode(),
                              items, blocks, reqs, pre, macro=macro,
                              do_company=True, do_macro=True)

    loc_eg = "2#Cairo#EG#EG#31.25#30.05#EG"
    loc_us = "2#Washington#US#US#38.9#-77.03#US"
    loc_mu = "2#Muscat#MU#MU#23.6#58.5#MU"
    loc_suez_nocc = "2#Suez Canal#XX#XX#30.5#32.3#XX"
    rows, mrows, bad = blob([
        gkg_line(rec="M1", orgs="Nope,1", source="example.com",
                 url="https://example.com/1", themes="ECON_INFLATION;EPU_POLICY",
                 locs=loc_eg),
        gkg_line(rec="M2", orgs="Nope,1", source="example.com",
                 url="https://example.com/2", themes="ECON_INFLATION", locs=loc_us),
        gkg_line(rec="M3", orgs="Nope,1", source="example.com",
                 url="https://example.com/3", themes="ECON_INFLATION", locs=""),
        gkg_line(rec="M4", orgs="Nope,1", source="example.com",
                 url="https://example.com/4", themes="UNRELATED_TOKEN", locs=loc_eg),
        gkg_line(rec="M5", orgs="Nope,1", source="example.com",
                 url="https://example.com/5", themes="MARITIME", locs=loc_suez_nocc),
        gkg_line(rec="M6", orgs="Nope,1", source="example.com",
                 url="https://example.com/6", themes="ECON_OILPRICE", locs=loc_mu),
        gkg_line(rec="M7", orgs="Nope,1", source="example.com",
                 url="https://example.com/7", themes="EPU_POLICY", locs=loc_eg),
    ])
    by_id = {r["gkg_record_id"]: r for r in mrows}
    check("macro theme+EG captured", "M1" in by_id
          and by_id["M1"]["themes"] == ["ECON_INFLATION"]
          and by_id["M1"]["families"] == ["monetary_fx"]
          and by_id["M1"]["features"] == ["EPU_POLICY"], str(by_id.get("M1")))
    check("macro theme+US dropped", "M2" not in by_id)
    check("macro theme, no geo dropped", "M3" not in by_id)
    check("macro EG-only (no theme) dropped", "M4" not in by_id)
    check("macro suez name-rule captured", "M5" in by_id, str(by_id.get("M5")))
    check("macro FIPS MU captured", "M6" in by_id, str(by_id.get("M6")))
    check("macro feature token never a row filter", "M7" not in by_id)
    check("macro captured rows keep company channel independent",
          all(r["gkg_record_id"] not in {x["gkg_record_id"] for x in rows}
              for r in mrows))
    rows_off, mrows_off, _ = G.process_blob(
        "f", "english", gkg_line(rec="M8", orgs="Nope,1", source="example.com",
                                 url="https://example.com/8",
                                 themes="ECON_INFLATION", locs=loc_eg).encode(),
        items, blocks, reqs, pre)
    check("macro off -> no macro rows", mrows_off == [] and rows_off == [])
    # done-but-not-macro_done: company channel skipped, macro still captured
    rows_c, mrows_c, _ = G.process_blob(
        "f", "english", gkg_line(rec="M9", orgs="Telecom Egypt,9",
                                 themes="ECON_INFLATION", locs=loc_eg).encode(),
        items, blocks, reqs, pre, macro=macro,
        do_company=False, do_macro=True)
    check("done-but-not-macro_done selection",
          rows_c == [] and len(mrows_c) == 1
          and mrows_c[0]["gkg_record_id"] == "M9", str((rows_c, mrows_c)))


def test_list_files_and_range():
    with tempfile.TemporaryDirectory() as d:
        mp = os.path.join(d, "masterfilelist.txt")
        with open(mp, "w") as f:
            f.write("100 md5a https://data.gdeltproject.org/gdeltv2/20240515090000.gkg.csv.zip\n")
            f.write("100 md5b https://data.gdeltproject.org/gdeltv2/20240515091500.gkg.csv.zip\n")
            f.write("100 md5c https://data.gdeltproject.org/gdeltv2/20240601000000.gkg.csv.zip\n")
            f.write("100 md5d https://data.gdeltproject.org/gdeltv2/20240515090000.events.csv.zip\n")
        files = G.list_files([(mp, "english")], "20240501000000", "20240531235959")
        check("only in-range gkg files", [u.rsplit('/',1)[-1] for u, _ in files] ==
              ["20240515090000.gkg.csv.zip", "20240515091500.gkg.csv.zip"], str(files))
        check("stream tag", all(s == "english" for _, s in files))


def test_fetch_guards():
    try:
        G.fetch("https://example.com/evil.zip")
        check("non-GDELT host refused", False)
    except ValueError as e:
        check("non-GDELT host refused", "refusing" in str(e), str(e))
    try:
        G.fetch("ftp://data.gdeltproject.org/x.zip")
        check("non-HTTPS scheme refused", False)
    except ValueError as e:
        check("non-HTTPS scheme refused", "scheme" in str(e), str(e))


def _args(st, out):
    class A:
        pass
    a = A()
    a.aliases, a.state, a.out = ALIASES_CSV, st, out
    a.start, a.end = "20240501000000", "20240531235959"
    a.master, a.master_translation, a.workers, a.budget_seconds = None, None, 1, 0
    return a


def _empty_master(d):
    mp = os.path.join(d, "masterfilelist.txt")
    with open(mp, "w") as f:  # one out-of-range file: nothing to fetch
        f.write("100 md5a https://data.gdeltproject.org/gdeltv2/20200115090000.gkg.csv.zip\n")
    return mp


def test_config_binding():
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "state"), os.path.join(d, "out")
        os.makedirs(st)
        json.dump({"aliases_sha256": "x", "start": "2019", "end": "2020",
                   "out": out}, open(os.path.join(st, "config.json"), "w"))
        try:
            G.run_fetch(_args(st, out))
            check("config mismatch refuses", False)
        except SystemExit as e:
            check("config mismatch refuses", "mismatch" in str(e)
                  and "fresh --out" in str(e), str(e))
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "state"), os.path.join(d, "out")
        os.makedirs(st)
        with open(os.path.join(st, "config.json"), "w") as f:
            f.write('{"aliases_sha256": "x", "sta')  # interrupted write
        try:
            G.run_fetch(_args(st, out))
            check("unreadable config refuses cleanly", False)
        except SystemExit as e:
            check("unreadable config refuses cleanly", "unreadable" in str(e), str(e))
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "state"), os.path.join(d, "out")
        os.makedirs(st)
        os.makedirs(out)
        with open(os.path.join(out, "matches.jsonl"), "w") as f:
            f.write('{"gkg_record_id": "OLD"}\n')  # stale rows, no config
        try:
            G.run_fetch(_args(st, out))
            check("fresh bind with stale matches refuses", False)
        except SystemExit as e:
            check("fresh bind with stale matches refuses",
                  "fresh --out" in str(e), str(e))


def test_config_atomic_and_restart():
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "state"), os.path.join(d, "out")
        a = _args(st, out)
        a.master = _empty_master(d)
        G.run_fetch(a)  # fresh bind, nothing in range to fetch
        check("config written", os.path.exists(os.path.join(st, "config.json")))
        check("no temp file left behind",
              not os.path.exists(os.path.join(st, "config.json.tmp")))
        cfg = json.load(open(os.path.join(st, "config.json")))
        check("config content", cfg["start"] == "20240501000000"
              and cfg["end"] == "20240531235959"
              and cfg["out"] == os.path.abspath(out), str(cfg))
        # normal restart: unchanged config + existing matches must proceed
        with open(os.path.join(out, "matches.jsonl"), "a") as f:
            f.write('{"gkg_record_id": "KEPT"}\n')
        G.run_fetch(_args(st, out))
        check("normal restart proceeds, output preserved",
              os.path.getsize(os.path.join(out, "matches.jsonl")) > 0)
        check("restart wrote no second config tmp",
              not os.path.exists(os.path.join(st, "config.json.tmp")))


def test_restart_and_finalize():
    items, blocks, reqs, pre = loaded()
    with tempfile.TemporaryDirectory() as out:
        blob = gkg_line(rec="R1", orgs="Telecom Egypt,10").encode()
        zpath = os.path.join(out, "z.zip")
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("20240515000000.gkg.csv", blob.decode())
        with zipfile.ZipFile(zpath) as z:
            rows, _, _ = G.process_blob("f", "english", z.read(z.namelist()[0]),
                                     items, blocks, reqs, pre)
        # duplicate lines (reprocess after crash) dedupe in finalize;
        # a truncated line (interrupted append) is skipped, not fatal
        with open(os.path.join(out, "matches.jsonl"), "w") as f:
            for r in rows + rows:
                f.write(json.dumps(r) + "\n")
            f.write('{"gkg_record_id": "BROKEN", "u')

        class A:
            pass
        a = A()
        a.out = out
        G.run_finalize(a)
        summary = list(csv.reader(open(os.path.join(out, "alias_hit_summary.csv"))))
        check("summary header", summary[0] == ["ticker", "org_entry", "rows",
                                               "ticker_distinct_days"])
        check("dedupe on finalize", summary[1][2] == "1", str(summary[1]))
        check("final output written",
              os.path.exists(os.path.join(out, "matches.parquet"))
              or os.path.exists(os.path.join(out, "matches.csv")))


def test_crash_recovery_tail():
    items, blocks, reqs, pre = loaded()
    blob = gkg_line(rec="R1", orgs="Telecom Egypt,10")
    # a record whose text has a 2-byte char; the crash cuts it in half
    good = {"gkg_record_id": "KEEP", "url": "u1", "date": "20240515000000",
            "stream": "english", "source": "s", "tickers": ["T"],
            "matched_org_entries": ["x"], "reason": "r", "tone": "0",
            "positive": "0", "negative": "0", "word_count": "1",
            "themes": "caf\u00e9"}
    line = (json.dumps(good, ensure_ascii=False) + "\n").encode("utf-8")
    partial = json.dumps(dict(good, gkg_record_id="CUT"),
                         ensure_ascii=False).encode("utf-8")
    cut_at = partial.index("\u00e9".encode("utf-8")) + 1  # mid-character
    partial = partial[:cut_at]
    with tempfile.TemporaryDirectory() as d:
        # (a) truncate helper: byte-safe, keeps complete lines only
        m = os.path.join(d, "m.jsonl")
        with open(m, "wb") as f:
            f.write(line + partial)
        removed = G.truncate_incomplete_tail(m)
        check("tail removed, bytes reported", removed == len(partial),
              str(removed))
        check("complete line kept", open(m, "rb").read() == line)
        check("complete file untouched", G.truncate_incomplete_tail(m) == 0
              and open(m, "rb").read() == line)
        e = os.path.join(d, "e.jsonl")
        open(e, "wb").write(partial)
        check("only a partial line leaves an empty file",
              G.truncate_incomplete_tail(e) == len(partial)
              and os.path.getsize(e) == 0)
        check("missing file is a no-op",
              G.truncate_incomplete_tail(os.path.join(d, "none")) == 0)
        # (b) finalize survives a split UTF-8 tail and exports
        out = os.path.join(d, "out")
        os.makedirs(out)
        with open(os.path.join(out, "matches.jsonl"), "wb") as f:
            f.write(line + partial)

        class A:
            pass
        a = A()
        a.out = out
        G.run_finalize(a)
        rows = list(csv.reader(open(os.path.join(out, "matches.csv"))))\
            if os.path.exists(os.path.join(out, "matches.csv")) else None
        summ = list(csv.reader(open(os.path.join(out, "alias_hit_summary.csv"))))
        check("finalize exports despite split UTF-8 tail",
              len(summ) == 2 and summ[1][2] == "1", str(summ))
        # (c) run_fetch truncates before appending: the replayed record
        # is not glued to the prefix and both survive finalize
        st, out2 = os.path.join(d, "st"), os.path.join(d, "out2")
        os.makedirs(out2)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("20240515000000.gkg.csv", blob)
        raw = buf.getvalue()
        orig = (G.list_files, G.fetch)
        G.list_files = lambda specs, s0, e0: [
            ("http://x/20240515000000.gkg.csv.zip", "english")]
        G.fetch = lambda url, timeout=90: raw

        class R:
            pass
        r = R()
        r.state, r.out, r.start, r.end = st, out2, "20240515", "20240515"
        r.aliases, r.master, r.master_translation = ALIASES_CSV, "m", None
        r.workers, r.budget_seconds = 1, 0
        try:
            # first run binds the config with nothing to do, then the
            # crash leaves a complete line plus a split-char partial
            G.list_files = lambda specs, s0, e0: []
            with contextlib.redirect_stdout(io.StringIO()):
                G.run_fetch(r)
            open(os.path.join(out2, "matches.jsonl"), "wb").write(
                line + partial)
            G.list_files = lambda specs, s0, e0: [
                ("http://x/20240515000000.gkg.csv.zip", "english")]
            with contextlib.redirect_stdout(io.StringIO()):
                G.run_fetch(r)
        finally:
            G.list_files, G.fetch = orig
        data = open(os.path.join(out2, "matches.jsonl"), "rb").read()
        lines = data.split(b"\n")
        check("every line parses after resume, none glued",
              data.endswith(b"\n") and all(
                  json.loads(x.decode("utf-8")) for x in lines if x),
              str(lines)[:200])
        check("replayed record present, cut record gone",
              b'"KEEP"' in data and b'"CUT"' not in data
              and data.count(b"R1") >= 1)


def test_unfinished_vs_absent():
    """A listed file answered with HTTP 404 is ABSENT (never makes the run
    unfinished); a transient failure is unfinished. Both stay out of
    done.txt. Fixed synthetic inputs."""
    import urllib.error
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out)
        names = ["20240515000000", "20240515001500", "20240515003000", "20240515004500"]
        orig = (G.list_files, G.fetch)
        G.list_files = lambda specs, s0, e0: [
            ("http://x/%s.gkg.csv.zip" % n, "english") for n in names]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("a.gkg.csv", b"")
        good = buf.getvalue()

        def fake(url, timeout=90):
            if names[1] in url:
                raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
            if names[2] in url:
                raise urllib.error.URLError("timed out")
            if names[3] in url:
                raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
            return good
        G.fetch = fake

        class R:
            pass
        r = R()
        r.state, r.out, r.start, r.end = st, out, "20240515", "20240515"
        r.aliases, r.master, r.master_translation = ALIASES_CSV, "m", None
        r.workers, r.budget_seconds = 1, 0
        buf2 = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf2):
                G.run_fetch(r)
        finally:
            G.list_files, G.fetch = orig
        o = buf2.getvalue()
        check("status line counts 2 unfinished and 1 absent",
              "gkg-filter-status unfinished=2 absent=1\n" in o, o[-200:])
        check("404 is reported as absent, not skip",
              "absent %s.gkg.csv.zip" % names[1] in o and "skip %s.gkg.csv.zip" % names[1] not in o)
        check("transient failure is reported as skip with diagnostics",
              "skip %s.gkg.csv.zip: URLError" % names[2] in o)
        done = open(os.path.join(st, "done.txt")).read().split()
        check("a non-404 HTTP error (403) is unfinished, not absent",
              "skip %s.gkg.csv.zip: HTTPError" % names[3] in o)
        check("only the served file is done", done == ["%s.gkg.csv.zip" % names[0]], str(done))


class _SteppingTime:
    """Scoped clock stub (959m F3): every time() call advances 10 s, so a
    positive budget is exhausted at the first batch check no matter what the
    real clock does (equal reads, backward steps). Other attributes delegate."""
    def __init__(self):
        self.now = 1000.0

    def time(self):
        self.now += 10.0
        return self.now

    def __getattr__(self, name):
        return getattr(time, name)


def _run_fetch_with(st, out, names, fake, budget=0, workers=1):
    """Run run_fetch with a fake list and fetch; returns (stdout, fetched urls)."""
    orig = (G.list_files, G.fetch, G.time)
    if budget:
        G.time = _SteppingTime()
    G.list_files = lambda specs, s0, e0: [
        ("http://x/%s.gkg.csv.zip" % n, "english") for n in names]
    fetched = []

    def rec(url, timeout=90):
        fetched.append(url.rsplit("/", 1)[-1])
        return fake(url)
    G.fetch = rec

    class R:
        pass
    r = R()
    r.state, r.out, r.start, r.end = st, out, "20240515", "20240515"
    r.aliases, r.master, r.master_translation = ALIASES_CSV, "m", None
    r.workers, r.budget_seconds = workers, budget
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            G.run_fetch(r)
    except SystemExit as e:
        e.stdout = buf.getvalue()   # a failing run's stdout stays inspectable
        raise
    finally:
        G.list_files, G.fetch, G.time = orig
    return buf.getvalue(), fetched


def test_absent_persisted_and_skipped():
    """First batch all 404 and the budget expires: the absent identities are
    persisted in absent.txt, the next run skips them (file 9 runs), transient
    failures stay retryable, done.txt behaviour is unchanged."""
    import urllib.error
    names = ["202405150%02d000" % i for i in range(10)]
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("a.gkg.csv", b"")
    good = zbuf.getvalue()
    batch = max(1 * 4, 8)
    check("batch is 8 with one worker", batch == 8)

    def fake(url):
        n = url.rsplit("/", 1)[-1][:-len(".gkg.csv.zip")]
        if n in names[:8]:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        if n == names[8]:
            raise urllib.error.URLError("timed out")
        return good
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out)
        # run 1: tiny positive budget expires after the first batch of 8
        o1, f1 = _run_fetch_with(st, out, names, fake, budget=1e-9)
        ab = open(os.path.join(st, "absent.txt")).read().split()
        check("run 1 fetched only the first batch", len(f1) == 8, str(f1))
        check("all 8 absent identities persisted", ab == ["%s.gkg.csv.zip" % n for n in names[:8]], str(ab))
        check("budget message printed", "budget exhausted" in o1)
        check("nothing done in run 1", not os.path.exists(os.path.join(st, "done.txt"))
              or open(os.path.join(st, "done.txt")).read() == "")
        check("status line of run 1 counts 8 absent", "gkg-filter-status unfinished=0 absent=8\n" in o1)
        # run 2: absent skipped, file 9 transient, file 10 served
        o2, f2 = _run_fetch_with(st, out, names, fake)
        check("run 2 does not re-download absent files", all(n not in f2 for n in
              ["%s.gkg.csv.zip" % x for x in names[:8]]), str(f2))
        check("run 2 reaches files 9 and 10", f2 == ["%s.gkg.csv.zip" % names[8], "%s.gkg.csv.zip" % names[9]], str(f2))
        check("run 2 status: 1 unfinished, 0 absent", "gkg-filter-status unfinished=1 absent=0\n" in o2, o2[-120:])
        check("run 2 prints absent_prev", "absent_prev=8" in o2)
        done = open(os.path.join(st, "done.txt")).read().split()
        check("only the served file is done", done == ["%s.gkg.csv.zip" % names[9]], str(done))
        ab2 = open(os.path.join(st, "absent.txt")).read().split()
        check("transient failure is not recorded absent", len(ab2) == 8 and "%s.gkg.csv.zip" % names[8] not in ab2)
        # run 3: transient file retried, still not absent
        o3, f3 = _run_fetch_with(st, out, names, fake)
        check("run 3 retries the transient file only", f3 == ["%s.gkg.csv.zip" % names[8]], str(f3))
    # a crash mid-run keeps the absent files already discovered
    class Boom(BaseException):
        pass

    def fake2(url):
        n = url.rsplit("/", 1)[-1][:-len(".gkg.csv.zip")]
        if n in names[:2]:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        raise Boom()
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out)
        try:
            _run_fetch_with(st, out, names, fake2)
        except Boom:
            pass
        ab = open(os.path.join(st, "absent.txt")).read().split()
        check("absent files recorded before a mid-run crash", ab == ["%s.gkg.csv.zip" % n for n in names[:2]], str(ab))
        # a crash-truncated tail line is dropped, not glued
        with open(os.path.join(st, "absent.txt"), "a") as f:
            f.write("2024051501")
        o, f4 = _run_fetch_with(st, out, names, lambda u: good)
        ab = open(os.path.join(st, "absent.txt")).read().split()
        check("incomplete absent tail truncated", "truncated" in o and all(x.endswith(".gkg.csv.zip") for x in ab), str(ab))


def _ident(path):
    """(st_dev, st_ino) of a path, or None: descriptors are matched by
    identity, never through procfs."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def test_absent_flushed_before_fsync():
    """Each absent identity is flushed (visible to the file system) before the
    fsync that follows it: a hard kill after the fsync cannot lose the line."""
    import urllib.error
    names = ["202405150%02d000" % i for i in range(3)]
    sizes = []
    real = os.fsync

    box = {}

    def spy(fd):
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino) == _ident(box.get("absent")):
            sizes.append(st.st_size)
        return real(fd)

    def fake(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out)
        box["absent"] = os.path.join(st, "absent.txt")
        os.fsync = spy
        try:
            _run_fetch_with(st, out, names, fake)
        finally:
            os.fsync = real
    line = len("202405150%02d000.gkg.csv.zip\n" % 0)
    check("one fsync per absent file with the line already flushed", sizes == [line, 2 * line, 3 * line], str(sizes))


def test_transient_failures_do_not_starve_later_files():
    """A failing prefix is retried AFTER files that were never attempted, and
    the order survives a restart (persisted in state/transient.txt)."""
    names = ["202405150%02d000" % i for i in range(20)]
    bad = set("%s.gkg.csv.zip" % n for n in names[:8])

    def fake(url):
        raise ValueError("transient")
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        _o1, f1 = _run_fetch_with(st, out, names, fake, budget=1e-9)
        check("run 1 starts in listing order", f1[:8] == ["%s.gkg.csv.zip" % n for n in names[:8]], str(f1))
        tl = open(os.path.join(st, "transient.txt")).read().split()
        check("transient failures persisted one line per failure", len(tl) == 8, str(tl))
        _o2, f2 = _run_fetch_with(st, out, names, fake, budget=1e-9)
        check("run 2 scans never-attempted files first", f2[:8] == ["%s.gkg.csv.zip" % n for n in names[8:16]], str(f2))
        check("transient files stay out of absent.txt and done.txt",
              not open(os.path.join(st, "absent.txt")).read().strip() and not open(os.path.join(st, "done.txt")).read().strip())
        _o3, f3 = _run_fetch_with(st, out, names, fake, budget=1e-9)
        check("run 3 takes the remaining fresh files before any repeat failure", f3[:4] == ["%s.gkg.csv.zip" % n for n in names[16:20]], str(f3))
        check("then the fewest-failure files (listing order inside a tier)", f3[4:8] == ["%s.gkg.csv.zip" % n for n in names[:4]], str(f3))

def test_new_directories_and_their_parents_fsynced():
    """Every directory run_fetch creates (including missing ancestors) is
    fsynced, and so is each one's parent."""
    import urllib.error
    synced = set()
    real = os.fsync

    def spy(fd):
        st = os.fstat(fd)
        synced.add((st.st_dev, st.st_ino))
        return real(fd)

    def fake(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        st, out = os.path.join(d, "a", "b", "st"), os.path.join(d, "c", "out")
        os.fsync = spy
        try:
            _run_fetch_with(st, out, ["202405150%02d000" % i for i in range(2)], fake)
        finally:
            os.fsync = real
        for p in (st, os.path.dirname(st), os.path.join(d, "a"), out, os.path.join(d, "c"), d):
            check("directory %s fsynced" % os.path.relpath(p, d), _ident(p) in synced, str(sorted(synced)))

def test_state_dir_fsynced_after_checkpoint_files_open():
    """The state and output directories are fsynced once, after done.txt,
    absent.txt and matches.jsonl exist (their directory entries are durable
    before any record), and before the first per-record fsync."""
    import urllib.error
    names = ["202405150%02d000" % i for i in range(2)]
    events = []
    real = os.fsync
    box = {}

    def spy(fd):
        # Match the descriptor to a known directory or checkpoint file by
        # (st_dev, st_ino); no procfs.
        st = os.fstat(fd)
        key = (st.st_dev, st.st_ino)
        for dpath in box.get("dirs", ()):
            if _ident(dpath) == key:
                events.append(("dir", dpath, sorted(os.listdir(dpath))))
                return real(fd)
        for fpath in box.get("files", ()):
            if _ident(fpath) == key:
                events.append(("file", os.path.basename(fpath), None))
                return real(fd)
        return real(fd)

    def fake(url):
        if names[0] in url:   # 959o N1: a transient failure so transient.txt exists at the sync
            raise ValueError("transient")
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out)
        os.makedirs(st)  # pre-existing: new-directory syncs are tested separately
        box["dirs"] = [st, out]
        box["files"] = [os.path.join(st, n) for n in ("absent.txt", "done.txt", "transient.txt")] + [os.path.join(out, "matches.jsonl")]
        os.fsync = spy
        try:
            _run_fetch_with(st, out, names, fake)
        finally:
            os.fsync = real
        dirs = [e for e in events if e[0] == "dir"]
        first_file = next((i for i, e in enumerate(events) if e == ("file", "absent.txt", None)), None)
        check("an absent.txt record fsync was observed", first_file is not None, str(events))
        st_real, out_real = os.path.realpath(st), os.path.realpath(out)
        st_ev = [e for e in dirs if os.path.realpath(e[1]) == st_real]
        out_ev = [e for e in dirs if os.path.realpath(e[1]) == out_real]
    check("state dir fsynced exactly once", len(st_ev) == 1, str(events))
    check("state dir fsynced after done.txt and absent.txt exist",
          len(st_ev) == 1 and "done.txt" in st_ev[0][2] and "absent.txt" in st_ev[0][2])
    check("959o N1: transient.txt is present in the state dir at that sync",
          len(st_ev) == 1 and "transient.txt" in st_ev[0][2], str(st_ev))
    first_any = next((i for i, e in enumerate(events) if e[0] == "file"), None)
    check("959o N1: the state-dir sync precedes the FIRST record fsync of any checkpoint file",
          first_any is not None and len(st_ev) == 1 and events.index(st_ev[0]) < first_any, str(events))
    check("output dir fsynced once, after matches.jsonl exists",
          len(out_ev) == 1 and "matches.jsonl" in out_ev[0][2])
    check("directory syncs come before the first absent.txt record fsync",
          first_file is not None and all(events.index(e) < first_file for e in dirs))
    check("per-record fsyncs are kept (one absent record, one transient record)",
          sum(1 for e in events if e[0] == "file" and e[1] == "absent.txt") == 1
          and sum(1 for e in events if e[0] == "file" and e[1] == "transient.txt") == 1, str(events))


def test_budget_marker_only_when_files_remain():
    names = ["202405150%02d000" % i for i in range(8)]
    import io, zipfile
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("x.gkg.csv", "")
    good = zbuf.getvalue()
    for nm, nms, want in (("last batch finishes all files", names, False), ("files remain", names + ["20240515099000"], True)):
        with tempfile.TemporaryDirectory() as d:
            st, out = os.path.join(d, "st"), os.path.join(d, "out")
            os.makedirs(out)
            o, f = _run_fetch_with(st, out, nms, lambda u: good, budget=1e-9)
            check("budget marker %s" % nm, ("budget exhausted" in o) == want)

def test_959m_f1_reconcile_streams():
    """F1: a clean checkpoint is untouched; orphans are dropped by streaming
    (bounded memory), unparseable lines kept."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.jsonl")
        with open(p, "w") as f:
            for i in range(3):
                f.write(json.dumps({"file": "a", "n": i}) + "\n")
            f.write("not json\n")
        before, ino = open(p, "rb").read(), os.stat(p).st_ino
        n = G.reconcile_orphan_rows(p, {"a"})
        check("F1: clean checkpoint is byte-identical, same inode, no temp file", n == 0 and open(p, "rb").read() == before
              and os.stat(p).st_ino == ino and not os.path.exists(p + ".tmp"))
        n = G.reconcile_orphan_rows(p, set())
        check("F1: orphan rows dropped, unparseable line kept", n == 3 and open(p).read() == "not json\n")
        big = os.path.join(d, "big.jsonl")
        pad = "x" * 180
        with open(big, "w") as f:
            for i in range(60000):
                f.write(json.dumps({"file": "a" if i % 2 else "b", "p": pad}) + "\n")
        size = os.path.getsize(big)
        tracemalloc.start()
        n = G.reconcile_orphan_rows(big, {"a"})
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        check("F1: large file reconcile keeps peak memory far below the file size", n == 30000 and peak < size // 20,
              "peak %d size %d" % (peak, size))
        big2 = os.path.join(d, "big2.jsonl")
        with open(big2, "w") as f:
            for i in range(60000):
                f.write(json.dumps({"file": "a", "p": pad}) + "\n")
        tracemalloc.start()
        n = G.reconcile_orphan_rows(big2, {"a"})
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        check("F1: clean large file reconcile also bounded", n == 0 and peak < os.path.getsize(big2) // 20, "peak %d" % peak)


def test_checkpoint_io_failure_and_rebind_text():
    """A failed checkpoint write exits with the distinct retryable status
    (never a clean unfinished summary); config refusals name absent.txt and
    transient.txt in the rebind procedure."""
    import urllib.error
    names = ["202405150%02d000" % i for i in range(2)]
    real = os.fsync
    box = {"fail": False}
    def spy(fd):
        if box["fail"]:
            raise OSError("disk")
        return real(fd)
    def fake(url):
        box["fail"] = True
        raise urllib.error.URLError("transient")
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out); os.makedirs(st)
        os.fsync = spy
        code = text = None
        try:
            try:
                text, _ = _run_fetch_with(st, out, names, fake)
            except SystemExit as e:
                code = e.code
                text = getattr(e, "stdout", "")
        finally:
            os.fsync = real
            box["fail"] = False
        check("a failed transient-record fsync exits with the retryable checkpoint status", code == G.CHECKPOINT_IO_EXIT == 75)
        check("checkpoint failure keeps stdout: safe=1 error line, no normal status summary",
              "gkg-filter-checkpoint-error safe=1" in (text or "") and "gkg-filter-status" not in (text or ""))
        # config mismatch (different out) names the extra checkpoints
        cfg = os.path.join(st, "config.json")
        c = json.load(open(cfg)); c["start"] = "19990101000000"; json.dump(c, open(cfg, "w"))
        try:
            _run_fetch_with(st, out, names, lambda u: b"")
            msg = ""
        except SystemExit as e:
            msg = str(e.code)
            check("a configuration refusal is a message exit, not the checkpoint status", e.code != 75)
        check("rebind procedure names absent.txt and transient.txt", "absent.txt" in msg and "transient.txt" in msg)
        check("959m F2: fresh --out rebind also says to use a fresh --state", "fresh --state" in msg and "fresh --out" in msg, msg)
        src = open(G.__file__, encoding="utf-8").read()
        check("959m F2: all four refusals (company+macro, mismatch+unreadable) name a fresh --state", src.count("AND a fresh --state") == 4)
    check("module docstring rebind procedure names absent.txt and transient.txt", "absent.txt + transient.txt" in G.__doc__)

def test_rebind_retries_previously_absent_basename():
    """Documented rebind (delete config, done, absent, transient) makes a
    fresh master's previously-404 basename be attempted; an ordinary
    same-configuration restart keeps absent.txt and does not refetch it."""
    import urllib.error
    names = ["20240515000000"]
    def nf(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out); os.makedirs(st)
        _, f1 = _run_fetch_with(st, out, names, nf)
        _, f2 = _run_fetch_with(st, out, names, nf)
        check("same-configuration restart keeps absent.txt (not refetched)", len(f1) == 1 and f2 == [])
        for fn in ("config.json", "done.txt", "absent.txt", "transient.txt"):
            os.remove(os.path.join(st, fn))
        _, f3 = _run_fetch_with(st, out, names, nf)
        check("after the documented rebind the previously absent basename is attempted again", len(f3) == 1)

def test_959k_setup_and_close_failures():
    """Checkpoint setup and close I/O errors take the retryable exit 75."""
    names = ["202405150%02d000" % i for i in range(2)]
    # setup: the first directory fsync fails -> 75 with safe=0, never a traceback
    real = os.fsync
    def bad(fd): raise OSError("disk")
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out)
        os.fsync = bad
        code = text = None
        try:
            try:
                _run_fetch_with(st, out, names, lambda u: b"")
            except SystemExit as e:
                code, text = e.code, getattr(e, "stdout", "")
        finally:
            os.fsync = real
        check("setup I/O failure exits 75", code == 75)
        check("setup I/O failure is safe=0 and prints no status summary",
              "gkg-filter-checkpoint-error safe=0" in text and "gkg-filter-status" not in text, text)
    # close failures: a data file close error is safe=0, a transient-only one is safe=1
    for target, want in (("done.txt", "safe=0"), ("transient.txt", "safe=1")):
        with tempfile.TemporaryDirectory() as d:
            st, out = os.path.join(d, "st"), os.path.join(d, "out")
            os.makedirs(out)
            orig_open = open
            class Bad:
                def __init__(self, f): self._f = f
                def __getattr__(self, n): return getattr(self._f, n)
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def close(self):
                    self._f.close(); raise OSError("close failed")
            def fake_open(path, *a, **k):
                f = orig_open(path, *a, **k)
                return Bad(f) if os.path.basename(str(path)) == target else f
            G.open = fake_open
            code = text = None
            try:
                try:
                    _run_fetch_with(st, out, names, lambda u: b"")
                except SystemExit as e:
                    code, text = e.code, getattr(e, "stdout", "")
            finally:
                del G.open
            check("close failure on %s exits 75 with %s" % (target, want),
                  code == 75 and ("gkg-filter-checkpoint-error " + want) in text, "%s %s" % (code, text))


def test_959l_reads_retryable_and_replay_reconciled():
    """Checkpoint READ errors are retryable (75); malformed config stays a
    message. Rows of a file with no done mark are dropped before the replay."""
    import urllib.error
    names = ["20240515000000", "20240515001500"]
    nm = ["%s.gkg.csv.zip" % n for n in names]

    def nf(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "st"), os.path.join(d, "out")
        os.makedirs(out)
        _run_fetch_with(st, out, names[:1], nf)          # creates config.json etc.
        # --- M1: a read OSError on each checkpoint file takes exit 75, safe=0
        for target in ("done.txt", "absent.txt", "transient.txt", "config.json"):
            open(os.path.join(st, target), "a").close()
            orig_open = open

            def bad_open(path, *a, _t=target, **k):
                mode = a[0] if a else k.get("mode", "r")
                if os.path.basename(str(path)) == _t and "r" == mode[:1] and "+" not in mode:
                    raise OSError("read failed")
                return orig_open(path, *a, **k)
            G.open = bad_open
            code = text = None
            try:
                try:
                    _run_fetch_with(st, out, names, nf)
                except SystemExit as e:
                    code, text = e.code, getattr(e, "stdout", "")
            finally:
                del G.open
            check("read OSError on %s exits 75 safe=0" % target,
                  code == 75 and "gkg-filter-checkpoint-error safe=0" in text, "%s %s" % (code, text))
        # malformed config is a message exit, not 75
        with open(os.path.join(st, "config.json"), "w") as f:
            f.write("{not json")
        try:
            _run_fetch_with(st, out, names, nf); code = None
        except SystemExit as e:
            code = e.code
        check("malformed config stays a message refusal", code not in (None, 75) and "unreadable" in str(code), str(code))
        os.remove(os.path.join(st, "config.json"))
        os.remove(os.path.join(st, "absent.txt"))
        # --- m4: rows without a done mark are dropped, rows with one are kept
        _run_fetch_with(st, out, names[:1], nf)          # rewrites config.json
        os.remove(os.path.join(st, "absent.txt"))
        mp = os.path.join(out, "matches.jsonl")
        with open(mp, "w") as f:
            f.write(json.dumps({"file": nm[0], "r": 1}) + "\n")
            f.write(json.dumps({"file": nm[1], "r": 2}) + "\n")
            f.write(json.dumps({"file": nm[1], "r": 3}) + "\n")
        with open(os.path.join(st, "done.txt"), "w") as f:
            f.write(nm[0] + "\n")
        o, _ = _run_fetch_with(st, out, names, nf)
        left = [json.loads(l)["r"] for l in open(mp)]
        check("rows of the not-done file are dropped before replay, done file rows kept",
              left == [1] and "reconciled 2 rows" in o, "%s %s" % (left, o))
        check("reconcile is a no-op when every row's file is done",
              G.reconcile_orphan_rows(mp, {nm[0]}) == 0 and [json.loads(l)["r"] for l in open(mp)] == [1])


def test_959n_filter_f1_f2_f3():
    # F1: a retry finds the directory present (nothing "created") but must
    # still sync the parent that holds its entry.
    with tempfile.TemporaryDirectory() as d:
        target = os.path.join(d, "state")
        os.makedirs(target)
        seen = []
        real = G.fsync_dir
        G.fsync_dir = lambda p: (seen.append(os.path.realpath(p)), real(p))[1]
        try:
            G.makedirs_durable(target)
        finally:
            G.fsync_dir = real
        check("959n F1: existing dir on retry: the parent entry is synced",
              os.path.realpath(d) in seen, str(seen))
    # F2: both unreadable-config messages name the matches file to delete.
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "state"), os.path.join(d, "out")
        os.makedirs(st)
        with open(os.path.join(st, "config.json"), "w") as f:
            f.write('{"aliases_sha256": "x", "sta')
        try:
            G.run_fetch(_args(st, out)); msg = ""
        except SystemExit as e:
            msg = str(e)
        check("959n F2: company unreadable-config message names matches.jsonl",
              "unreadable" in msg and msg.rstrip().endswith("matches.jsonl"), msg)
    with tempfile.TemporaryDirectory() as d:
        st, out = os.path.join(d, "state"), os.path.join(d, "out")
        os.makedirs(st)
        with open(os.path.join(st, "macro_config.json"), "w") as f:
            f.write('{"themes_sha256": "x", "sta')
        ma = _args(st, out)
        ma.themes = os.path.join(ROOT, "evaluation", "gdelt_macro_themes.csv")
        try:
            G.run_fetch(ma); msg = ""
        except SystemExit as e:
            msg = str(e)
        check("959n F2: macro unreadable-config message names macro_matches.jsonl",
              "macro state config unreadable" in msg and msg.rstrip().endswith("macro_matches.jsonl"), msg)
    # 959o F1: invalid UTF-8 in a saved config is a refusal message, not a traceback.
    for _name, _macro in (("config.json", False), ("macro_config.json", True)):
        with tempfile.TemporaryDirectory() as d:
            st, out = os.path.join(d, "state"), os.path.join(d, "out")
            os.makedirs(st)
            with open(os.path.join(st, _name), "wb") as f:
                f.write(b'{"k": "\xff\xfe bad"}')
            ma = _args(st, out)
            if _macro:
                ma.themes = os.path.join(ROOT, "evaluation", "gdelt_macro_themes.csv")
            try:
                G.run_fetch(ma); res = ("returned", "")
            except SystemExit as e:
                res = ("exit", e.code)
            except Exception as e:  # a traceback is the defect
                res = ("traceback", type(e).__name__)
            check("959o F1: invalid UTF-8 %s is a refusal message (not a traceback, not 75)" % _name,
                  res[0] == "exit" and isinstance(res[1], str) and "unreadable" in res[1], str(res))
    # F3: an exactly duplicated listing line is scheduled once; the same
    # archive name with two different URLs refuses.
    with tempfile.TemporaryDirectory() as d:
        mp = os.path.join(d, "m.txt")
        u1 = "https://data.gdeltproject.org/gdeltv2/20240515090000.gkg.csv.zip"
        u2 = "http://data.gdeltproject.org/gdeltv2/20240515090000.gkg.csv.zip"
        u3 = "https://data.gdeltproject.org/gdeltv2/20240515091500.gkg.csv.zip"
        with open(mp, "w") as f:
            f.write("1 a %s\n1 a %s\n1 b %s\n" % (u1, u1, u3))
        files = G.list_files([(mp, "english")], "20240501000000", "20240531235959")
        check("959n F3: a duplicated record is listed once", files == [(u1, "english"), (u3, "english")], str(files))
        with open(mp, "w") as f:
            f.write("1 a %s\n1 a %s\n" % (u1, u2))
        try:
            G.list_files([(mp, "english")], "20240501000000", "20240531235959"); msg = ""
        except SystemExit as e:
            msg = str(e)
        check("959n F3: same name, different URL refuses", "twice with different URLs" in msg, msg)
        # an out-of-window conflict is not scheduled, so it does not refuse
        files = G.list_files([(mp, "english")], "20240601000000", "20240631235959")
        check("959n F3: out-of-window entries are ignored", files == [], str(files))


def main():
    for fn in (test_crash_recovery_tail, test_alias_table_loads, test_match_orgs_real,
               test_match_orgs_blocks_and_noise, test_pilot_six_fixes,
               test_process_blob, test_macro_filter, test_list_files_and_range,
               test_fetch_guards, test_config_binding,
               test_config_atomic_and_restart, test_restart_and_finalize,
               test_unfinished_vs_absent, test_absent_persisted_and_skipped, test_absent_flushed_before_fsync,
               test_state_dir_fsynced_after_checkpoint_files_open,
               test_new_directories_and_their_parents_fsynced, test_transient_failures_do_not_starve_later_files, test_budget_marker_only_when_files_remain, test_checkpoint_io_failure_and_rebind_text, test_rebind_retries_previously_absent_basename, test_959k_setup_and_close_failures, test_959l_reads_retryable_and_replay_reconciled, test_959m_f1_reconcile_streams, test_959n_filter_f1_f2_f3):
        fn()
    print("test_gdelt_gkg_filter: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
