#!/usr/bin/env python3
import csv, sys, math, statistics as st
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "/home/borg/pnl.csv"
rows = []
with open(path, newline="") as f:
    r = csv.DictReader(f)
    rows = [x for x in r]

by_svc = defaultdict(list)
for x in rows:
    by_svc[x["service"]].append(x)

def f(x, k): 
    try: return float(x[k])
    except: return math.nan

print(f"{'service':12} | {'n':>4} {'last_equity':>12} {'last_pnl':>10} {'min_pnl':>10} {'max_pnl':>10} {'avg_pnl':>10}")
for svc, xs in by_svc.items():
    last = xs[-1]
    pnl_series = [f(x,"pnl") for x in xs if x.get("pnl")]
    last_equity = f(last,"equity")
    last_pnl = f(last,"pnl")
    mn = f"{min(pnl_series):.2f}" if pnl_series else "n/a"
    mx = f"{max(pnl_series):.2f}" if pnl_series else "n/a"
    avg = f"{st.fmean(pnl_series):.2f}" if pnl_series else "n/a"
    print(f"{svc:12} | {len(xs):4d} {last_equity:12.2f} {last_pnl:10.2f} {mn:10} {mx:10} {avg:10}")
