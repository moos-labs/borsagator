#!/usr/bin/env python3
"""Tests for scripts/gdelt_gkg_filter.py (INS-DATA-002 item 2, G3 pilot).
Standalone, stdlib only, synthetic 27-column GKG rows, no network."""
import csv
import importlib.util
import json
import os
import sys
import tempfile
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
             tone="1.27,2.22,0.95,3.17,1.5,0.5,400", ncols=27):
    """27-column layout, both streams: id 0, date 1, source-collection-id 2,
    source 3, url 4, themes 7, orgs 14, tone 15."""
    cols = [""] * ncols
    if ncols == 27:
        cols[0], cols[1], cols[2] = rec, date, "1"
        cols[3], cols[4] = source, url
        cols[7], cols[14], cols[15] = themes, orgs, tone
    return "\t".join(cols)


def loaded():
    return G.load_aliases(ALIASES_CSV)


def test_alias_table_loads():
    items, blocks, pre = loaded()
    tickers = {t for _, ts in items for t in ts}
    check("38 tickers", len(tickers) == 38, str(len(tickers)))
    check("every alias nonempty", all(a.strip() for a, _ in items))
    check("prefilter hits normalized line",
          pre(G.norm("x Telecom Egypt y")) and not pre(G.norm("x Vodafone y")))
    check("blocks lowercase-normalized",
          all(b == b.lower() for bs in blocks.values() for b in bs))
    check("PHDC block present",
          "club palm hills" in blocks.get("PHDC", set()), str(blocks.get("PHDC")))


def test_match_orgs_real():
    items, blocks, _ = loaded()
    bt = G.match_orgs("Telecom Egypt,10;Vodafone Egypt,55", items, blocks)
    check("ETEL matched", set(bt) == {"ETEL"}, str(bt))
    check("entry captured", bt["ETEL"] == {"Telecom Egypt"}, str(bt))
    bt = G.match_orgs("Talaat Moustafa Group Holdings,3", items, blocks)
    check("TMGH via alt", set(bt) == {"TMGH"}, str(bt))
    bt = G.match_orgs("Commercial International Bank,7", items, blocks)
    check("COMI via bank alias", set(bt) == {"COMI"}, str(bt))
    bt = G.match_orgs("المصرية للاتصالات,9", items, blocks)
    check("ETEL via verified arabic", set(bt) == {"ETEL"}, str(bt))
    bt = G.match_orgs("Telecom Egypt,1;Talaat Moustafa Group,2", items, blocks)
    check("multi-issuer pairing exact",
          bt.get("ETEL") == {"Telecom Egypt"}
          and bt.get("TMGH") == {"Talaat Moustafa Group"}, str(bt))


def test_match_orgs_blocks_and_noise():
    items, blocks, _ = loaded()
    check("Club Palm Hills blocked for PHDC",
          G.match_orgs("Club Palm Hills,20", items, blocks) == {})
    bt = G.match_orgs("Palm Hills Developments,20", items, blocks)
    check("Palm Hills Developments matches PHDC", set(bt) == {"PHDC"}, str(bt))
    check("no COMI on bare 'Commercial International'",
          G.match_orgs("Negotiations Commercial International,4", items, blocks) == {})
    check("Telecom Egypt Confidence blocked for ETEL",
          G.match_orgs("Telecom Egypt Confidence,4", items, blocks) == {})
    check("Egyptian Exchange (the bourse) matches nothing",
          G.match_orgs("Egyptian Exchange,4", items, blocks) == {})


def test_process_blob():
    items, blocks, pre = loaded()
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
    rows, bad = G.process_blob("20240515000000.gkg.csv.zip", "english",
                               lines.encode(), items, blocks, pre)
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
              url="https://x.io/").encode(), items, blocks, pre) == ([], 0))


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
    items, blocks, pre = loaded()
    with tempfile.TemporaryDirectory() as out:
        blob = gkg_line(rec="R1", orgs="Telecom Egypt,10").encode()
        zpath = os.path.join(out, "z.zip")
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("20240515000000.gkg.csv", blob.decode())
        with zipfile.ZipFile(zpath) as z:
            rows, _ = G.process_blob("f", "english", z.read(z.namelist()[0]),
                                     items, blocks, pre)
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


def main():
    for fn in (test_alias_table_loads, test_match_orgs_real,
               test_match_orgs_blocks_and_noise, test_process_blob,
               test_list_files_and_range, test_fetch_guards,
               test_config_binding, test_config_atomic_and_restart,
               test_restart_and_finalize):
        fn()
    print("test_gdelt_gkg_filter: %d passed, %d failed"
          % (CHECKS["pass"], CHECKS["fail"]))
    sys.exit(1 if CHECKS["fail"] else 0)


if __name__ == "__main__":
    main()
