#!/usr/bin/env python3
"""Summarise A's best-case tuning runs (TAG=tune-*) from analysis/data/grid.csv.

    python3 analysis/collect.py && python3 analysis/tuning.py

Writes tuning_summary.csv (one row per node, tag, threads, L, precision) and prints it
sorted by median Gflops_dwf4. The best case per node is the highest median over >= 3 repeats.
Read-only on its inputs; stdlib only, so it runs with the system python3.
"""
import csv, statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "analysis" / "data"
METRICS = ("Gflops_dwf4", "Gflops_wilson")
MIN_REPEATS = 3


def load():
    src = DATA / "grid.csv"
    if not src.exists():
        return []
    with src.open(newline="") as f:
        # perfctr passes write result-<group>.json; only plain runs are timing-clean.
        return [r for r in csv.DictReader(f)
                if r["experiment"].startswith("grid-tune") and r["file"] == "result.json"]


def summarise(rows):
    groups = defaultdict(list)
    for r in rows:
        key = (r["node"], r["experiment"].removeprefix("grid-"), int(r["threads"]),
               int(r["L"]), r["precision"])
        groups[key].append(r)
    out = []
    for (node, tag, threads, L, prec), rs in sorted(groups.items()):
        row = {"node": node, "tag": tag, "threads": threads, "L": L, "precision": prec,
               "n": len(rs), "jobs": " ".join(sorted(r["job"] for r in rs)),
               "config": ";".join(sorted({r["config"] for r in rs})),
               "bind": ";".join(sorted({r["bind"] for r in rs})),
               "numactl": ";".join(sorted({r["numactl"] for r in rs}))}
        for m in METRICS:
            vals = [float(r[m]) for r in rs if r.get(m)]
            row.update({f"{m}_median": statistics.median(vals) if vals else "",
                        f"{m}_min": min(vals) if vals else "",
                        f"{m}_max": max(vals) if vals else ""})
        out.append(row)
    return out


def write(rows):
    dest = DATA / "tuning_summary.csv"
    if not rows:
        dest.unlink(missing_ok=True)
        print("tuning_summary.csv: no data")
        return
    with dest.open("w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"tuning_summary.csv: {len(rows)} rows")


def report(rows):
    key = "Gflops_dwf4_median"
    rows = [r for r in rows if r[key] != ""]
    print(f"\n{'node':6} {'tag':24} {'T':>4} {'L':>3} {'n':>2} {'dwf4 med':>9} {'min':>8} {'max':>8} "
          f"{'wilson med':>10}")
    for r in sorted(rows, key=lambda r: (r["node"], -r[key])):
        print(f"{r['node']:6} {r['tag']:24} {r['threads']:>4} {r['L']:>3} {r['n']:>2} "
              f"{r[key]:>9.1f} {r['Gflops_dwf4_min']:>8.1f} {r['Gflops_dwf4_max']:>8.1f} "
              f"{r['Gflops_wilson_median'] or float('nan'):>10.1f}")
    for node in sorted({r["node"] for r in rows}):
        mine = [r for r in rows if r["node"] == node]
        ok = [r for r in mine if r["n"] >= MIN_REPEATS]
        if ok:
            b = max(ok, key=lambda r: r[key])
            print(f"\nBEST {node} (median of n={b['n']}): {b[key]:.1f} GFLOP/s dwf4 SP, "
                  f"{b['tag']} T={b['threads']} L={b['L']} config={b['config']} "
                  f"bind={b['bind']} numactl={b['numactl'] or '-'} jobs={b['jobs']}")
        else:
            print(f"\nBEST {node}: no setting has {MIN_REPEATS} repeats yet")
        m = max(mine, key=lambda r: r["Gflops_dwf4_max"])
        print(f"MAX  {node} (single run): {m['Gflops_dwf4_max']:.1f} GFLOP/s dwf4 SP, "
              f"{m['tag']} T={m['threads']} L={m['L']}")


if __name__ == "__main__":
    summary = summarise(load())
    write(summary)
    report(summary)
