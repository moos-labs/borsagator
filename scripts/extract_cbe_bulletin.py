#!/usr/bin/env python3
"""Extract Table 15 (91/182/273/364-day T-bill accepted yields, weekly) and
Table 17 (weekly USD/EGP interbank weighted average + market buy/sell)
from one CBE Monthly Statistical Bulletin PDF.

Method: pdftotext -layout to locate the tables' pages, then pdftotext -bbox
for word coordinates. Column mapping for Table 15 uses the Interbank
"From d/m - d/m/yyyy" 2-week ranges printed on the same page: each range
covers one PAIR of weekly T-bill columns, and the range's end-year is the
year for both columns in the pair. Dates come from the "Week Ending" header
(day + month words). Values are matched to columns by nearest x-centre.

Output: JSON on stdout + optional --json-out file.
Usage: extract_bulletin.py <pdf> <bulletin_no> <source_url> [--json-out f]
"""
import json, re, subprocess, sys
from xml.etree import ElementTree as ET

MONTHS = {'jan': 1, 'jan.': 1, 'january': 1, 'feb': 2, 'feb.': 2, 'february': 2,
          'mar': 3, 'mar.': 3, 'march': 3, 'apr': 4, 'apr.': 4, 'april': 4,
          'may': 5, 'june': 6, 'july': 7, 'aug': 8, 'aug.': 8, 'august': 8,
          'sept': 9, 'sept.': 9, 'sep': 9, 'sep.': 9, 'september': 9,
          'oct': 10, 'oct.': 10, 'october': 10, 'nov': 11, 'nov.': 11,
          'november': 11, 'dec': 12, 'dec.': 12, 'december': 12}
NS = '{http://www.w3.org/1999/xhtml}'

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {r.stderr[:300]}")
    return r.stdout

def bbox_words(pdf, page):
    out = run(['pdftotext', '-bbox', '-f', str(page), '-l', str(page), pdf, '-'])
    root = ET.fromstring(out)
    words = []
    for w in root.iter(NS + 'word'):
        txt = w.text or ''
        words.append((float(w.get('xMin')), float(w.get('yMin')),
                      float(w.get('xMax')), float(w.get('yMax')), txt))
    return words

def layout_pages(pdf):
    txt = run(['pdftotext', '-layout', pdf, '-'])
    return txt.split('\f')

def ascii_words(words):
    return [(x0, y0, x1, y1, t) for x0, y0, x1, y1, t in words
            if all(ord(c) < 128 for c in t)]

def find_table15(pdf, pages):
    for i, pg in enumerate(pages, start=1):
        if 'Discount and Interest Rates (contd.)' in pg and 'Treasury Bills' in pg:
            return i
    return None

def find_table17(pdf, pages):
    for i, pg in enumerate(pages, start=1):
        if 'Weekly Exchange Rates' in pg and 'Weighted average' in pg:
            return i
    return None

def parse_table15(pdf, page):
    words = ascii_words(bbox_words(pdf, page))
    # --- "From d/m - d/m/yyyy" ranges (Interbank section): 9 ranges -> 9 pairs
    ranges = []
    for x0, y0, x1, y1, t in words:
        pass
    raw = run(['pdftotext', '-layout', '-f', str(page), '-l', str(page), pdf, '-'])
    # ranges appear as e.g. "From 15/6 -28/6/2021" split across words; rebuild from bbox lines
    rows = {}
    for x0, y0, x1, y1, t in words:
        rows.setdefault(round(y0 / 3), []).append((x0, t))
    range_list = []  # (x_centre, end_year, end_month, end_day, start_month, start_day)
    for k in sorted(rows):
        toks = sorted(rows[k])
        line = ' '.join(t for _, t in toks)
        # token start offsets inside the joined line, for per-match positions
        starts = []
        pos = 0
        for _, t in toks:
            starts.append(pos)
            pos += len(t) + 1
        xs = [x for x, t in toks]
        for m in re.finditer(r'From\s*(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})', line):
            # the match's own 'From' token: the token starting at or before m.start()
            xc = 0
            for j, (xj, txt) in enumerate(toks):
                if starts[j] <= m.start() < starts[j] + len(txt) and txt.startswith('From'):
                    xc = xj + 40
                    break
            else:
                # glued token (e.g. 'From19/6-2/7/2018'): nearest token at/before
                for j in range(len(toks) - 1, -1, -1):
                    if starts[j] <= m.start() and toks[j][1].startswith('From'):
                        xc = xs[j] + 40
                        break
            range_list.append((xc, int(m.group(6)), int(m.group(5)), int(m.group(4)),
                               int(m.group(2)), int(m.group(1))))
    # --- Week Ending date words: scan bands below the "Week Ending" label
    wy = None
    for x0, y0, x1, y1, t in words:
        if t == 'Week':
            wy = y0
    dates = []  # (x_centre, day, month)
    if wy is not None:
        seen_x = set()
        for dy in range(3, 32, 3):
            band = [(x0, y0, t) for x0, y0, x1, y1, t in words if abs(y0 - (wy + dy)) < 4]
            band.sort()
            i = 0
            while i < len(band):
                x0, y0, t = band[i]
                if re.fullmatch(r'\d{1,2}', t) and i + 1 < len(band):
                    mon = band[i + 1][2].lower()
                    if mon in MONTHS and round(x0) not in seen_x:
                        dates.append((((x0 + band[i + 1][0]) / 2), int(t), MONTHS[mon]))
                        seen_x.add(round(x0))
                        i += 2
                        continue
                i += 1
        dates.sort()
    # --- tenor rows: find row label y for each tenor, collect numeric values by x
    tenors = {}
    labels = {'91': '91-day', '182': '182-day', '273': '273-day', '364': '364-day'}
    rowmap = {}
    for x0, y0, x1, y1, t in words:
        rowmap.setdefault(round(y0 / 3), []).append((x0, t))
    for k in sorted(rowmap):
        toks = [t for _, t in sorted(rowmap[k])]
        line = ' '.join(toks)
        m = re.match(r'^(91|182|273|364)\s*-\s*day\s+bills', line)
        if m:
            ten = m.group(1)
            vals = []
            # BAND-BOUNDARY FIX (bulletin 353): a row's values can sit just
            # across the round(y/3) boundary from its label (353 182-day:
            # label y=283.4 -> band 94, values y=283.5 -> band 95), so the
            # label's own band holds no values. Merge k-1/k/k+1 like
            # parse_table17 does. Adjacent tenor rows are ~11pt away, so
            # the +-1 band merge cannot reach another row's values.
            merged = []
            for kk in (k - 1, k, k + 1):
                merged += rowmap.get(kk, [])
            for x0, t in sorted(merged):
                if re.fullmatch(r'\d+\.\d+', t):
                    vals.append(((x0), float(t)))
                elif t == '+' :
                    pass
            tenors[ten] = sorted(vals)
    # column centres from the 91-day row
    if '91' not in tenors or not tenors['91']:
        raise RuntimeError('91-day row not found')
    cols = [x for x, _ in tenors['91']]
    if len(cols) != len(dates):
        raise RuntimeError(f'column/date mismatch: {len(cols)} cols vs {len(dates)} dates')
    # pair mapping: 9 ranges -> pairs (cols 2k, 2k+1); year = range end-year
    if len(range_list) < len(cols) // 2:
        raise RuntimeError(f'only {len(range_list)} From-ranges for {len(cols)//2} pairs')
    range_list.sort()
    out_dates = []
    for k in range(len(cols) // 2):
        _, ey, em, ed, sm, sd = range_list[k]
        crosses = (sm, sd) > (em, ed)  # range spans New Year (e.g. 28/12-10/1)
        for j in (2 * k, 2 * k + 1):
            xc, day, mon = dates[j]
            # a date in the pre-New-Year leg of a crossing range belongs to ey-1
            yr = ey - 1 if (crosses and (mon, day) >= (sm, sd)) else ey
            out_dates.append(f'{yr:04d}-{mon:02d}-{day:02d}')
    series = {}
    for ten, vals in tenors.items():
        row = []
        for xc, day_mon in zip(cols, out_dates):
            if not vals:
                row.append((day_mon, None))
                continue
            best = min(vals, key=lambda v: abs(v[0] - xc))
            if abs(best[0] - xc) > 20:
                row.append((day_mon, None))
            else:
                row.append((day_mon, best[1]))
        series[labels[ten]] = row
    return {'page': page, 'dates': out_dates, 'series': series,
            'n_ranges': len(range_list)}

def parse_table17(pdf, page):
    words = ascii_words(bbox_words(pdf, page))
    # date headers: DD/MM/YYYY tokens, with (x, y)
    dates = []
    for x0, y0, x1, y1, t in words:
        m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', t)
        if m:
            dates.append((((x0 + x1) / 2), y0, f'{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}'))
    # group dates into bands by y (one band = one 8-week block)
    bands = {}
    for xc, y, d in dates:
        bands.setdefault(round(y / 4), []).append((xc, d))
    date_bands = sorted((k * 4, sorted(v)) for k, v in bands.items())
    # value rows, grouped by y-band; merge neighbouring bands (label and
    # numbers can sit 1-3 pts apart in older layouts)
    rawrows = {}
    for x0, y0, x1, y1, t in words:
        rawrows.setdefault(round(y0 / 3), []).append((x0, t))
    rows = {}
    for k in sorted(rawrows):
        merged = []
        for kk in (k - 1, k, k + 1):
            merged += rawrows.get(kk, [])
        rows[k] = merged
    out = []
    for k in sorted(rows):
        toks = sorted(rows[k])
        line = ' '.join(t for _, t in toks)
        kind = None
        if line.startswith('Weighted average'):
            kind = 'ib'
        elif line.startswith('US Dollar') or line.startswith('US dollar'):
            kind = 'mkt'
        if not kind:
            continue
        y = k * 3
        # date band: nearest band with y above this row (within 150 pts)
        band = None
        for by, ds in reversed(date_bands):
            if by < y and y - by < 150:
                band = ds
                break
        if band is None:
            continue
        vals = sorted((x, float(t)) for x, t in toks if re.fullmatch(r'\d+\.\d+', t))
        if not vals:
            continue
        if kind == 'ib':
            for xc, d in band:
                if any(r['date'] == d for r in out):
                    continue
                best = min(vals, key=lambda v: abs(v[0] - xc))
                if abs(best[0] - xc) < 60:
                    out.append({'date': d, 'interbank': best[1]})
        else:
            for xc, d in band:
                cands = sorted(v for v in vals if abs(v[0] - xc) < 60)
                buy = cands[0][1] if cands else None
                sell = cands[1][1] if len(cands) > 1 else None
                for r in out:
                    if r['date'] == d and 'market_buy' not in r:
                        r['market_buy'] = buy
                        r['market_sell'] = sell
    out.sort(key=lambda r: r['date'])
    return {'page': page, 'rows': out}

def main():
    pdf, bno, url = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    pages = layout_pages(pdf)
    p15 = find_table15(pdf, pages)
    p17 = find_table17(pdf, pages)
    res = {'bulletin': bno, 'source_url': url, 'pdf_pages': len(pages)}
    if p15:
        res['table15'] = parse_table15(pdf, p15)
    if p17:
        res['table17'] = parse_table17(pdf, p17)
    out = json.dumps(res, indent=1)
    if len(sys.argv) > 4 and sys.argv[4] == '--json-out':
        open(sys.argv[5], 'w').write(out)
    print(out)

if __name__ == '__main__':
    main()
