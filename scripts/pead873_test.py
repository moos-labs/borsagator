#!/usr/bin/env python3
"""PEAD pre-registered test (#873), one price source per run.
usage: python3 pead873_test.py EVENTS.csv PRICE_DIR SOURCE[yahoo|egxpy] [CAPITAL_ACTIONS_DIR]
Design as relayed (check against PR #873 text before the cycle run):
 - entry = close of the first session strictly after the announcement date (T+1; no close-of-T row)
 - return = 21-session log return from the entry close: log(close[e+21]/close[e])
 - abnormal = return minus the equal-weight average of the same 21-session log return over all tickers in PRICE_DIR (same dates)
 - groups: profit_direction up vs down; gap = mean(up) - mean(down), pooled primary, plus type=interim / annual
 - bootstrap over announcement DATES (resample dates with replacement, 10000 draws), one-sided 5%: p = share of draws with gap <= 0, plus the 5th percentile
 - gap reported before and after a 1.0 point round-trip cost (gap - 1.0 percentage point)
 - events within 5 calendar days of a capital-action date of the same ticker are excluded (if CAPITAL_ACTIONS_DIR given)
 - egxpy: leading volume-0 stub bars dropped. Never combine sources; run once per source.
Prices: CSV per ticker named TICKER*.csv with date and close columns (Yahoo: date,close ; egxpy: Date,Close,Volume).
"""
import sys,csv,glob,os,json,math,bisect
import numpy as np
from datetime import datetime as D
ev_f,pdir,src=sys.argv[1:4];cadir=sys.argv[4] if len(sys.argv)>4 else None
H=21;DRAWS=10000;COST=1.0
px={}
for f in glob.glob(os.path.join(pdir,'*.csv')):
    t=os.path.basename(f).split('.')[0].split('_')[0].upper()+'.CA'
    rows=list(csv.DictReader(open(f)));k0=rows[0].keys()
    kd=[k for k in k0 if k.lower().startswith('date')][0];kc=[k for k in k0 if k.lower()=='close'][0]
    kv=next((k for k in k0 if k.lower()=='volume'),None)
    if src=='egxpy' and kv:
        i0=next((i for i,r in enumerate(rows) if float(r[kv] or 0)>0),0);rows=rows[i0:]
    px[t]={r[kd][:10]:float(r[kc]) for r in rows if r[kc]}
dates=sorted({d for s in px.values() for d in s});di={d:i for i,d in enumerate(dates)}
def ret(t,i):
    s=px.get(t)
    if not s or i+H>=len(dates):return None
    a=s.get(dates[i]);b=s.get(dates[i+H])
    return math.log(b/a) if a and b else None
cad={}
if cadir:
    for f in glob.glob(os.path.join(cadir,'*.json')):
        L=[]
        for a in json.load(open(f)):
            for k in('announcingDate','effectiveDate','recordDate','completionDate'):
                try:L.append(D.strptime(a[k],'%d %B %Y'))
                except:pass
        cad[os.path.basename(f)[:-5]+'.CA']=L
bench={}
def ew(i):
    if i not in bench:
        v=[r for t in px for r in [ret(t,i)] if r is not None];bench[i]=np.mean(v) if v else None
    return bench[i]
rows=[];skipped={'capital_action':0,'no_price':0}
for r in csv.DictReader(open(ev_f)):
    t=r['ticker'];ad=D.strptime(r['announcement_date'],'%Y-%m-%d')
    if any(abs((x-ad).days)<=5 for x in cad.get(t,[])):skipped['capital_action']+=1;continue
    i=bisect.bisect_right(dates,r['announcement_date'])  # first session strictly after T
    x=ret(t,i);b=ew(i) if i<len(dates) else None
    if x is None or b is None:skipped['no_price']+=1;continue
    rows.append((r['type'],r['profit_direction']=='up',(x-b)*100,r['announcement_date']))
print('source',src,'events scored',len(rows),'skipped',skipped)
rng=np.random.default_rng(873)
def run(sub,label):
    if sum(s[1] for s in sub)<2 or sum(not s[1] for s in sub)<2:print(label,'n',len(sub),'too few in a group');return
    ds=sorted({s[3] for s in sub});by={d:[s for s in sub if s[3]==d] for d in ds}
    def gap(L):
        u=[s[2] for s in L if s[1]];d=[s[2] for s in L if not s[1]]
        return np.mean(u)-np.mean(d) if u and d else None
    g0=gap(sub);bs=[]
    for _ in range(DRAWS):
        L=[s for d in rng.choice(len(ds),len(ds)) for s in by[ds[d]]];g=gap(L)
        if g is not None:bs.append(g)
    bs=np.array(bs)
    print('%-8s n=%d up=%d down=%d dates=%d gap before cost %+.2f, after 1pt cost %+.2f | bootstrap one-sided p(gap<=0)=%.4f, 5th pct %+.2f (cost-adjusted 5th pct %+.2f)'%(label,len(sub),sum(s[1] for s in sub),sum(not s[1] for s in sub),len(ds),g0,g0-COST,(np.sum(bs<=0)+1)/(len(bs)+1),np.percentile(bs,5),np.percentile(bs,5)-COST))
run(rows,'pooled')
for ty in('interim','annual'):run([s for s in rows if s[0]==ty],ty)
