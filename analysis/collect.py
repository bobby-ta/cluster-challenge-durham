#!/usr/bin/env python3
"""Gather every run under results/ into tidy CSVs in analysis/data/.

    python3 analysis/collect.py [results_dir]

Writes likwid.csv (likwid-bench), grid.csv (Benchmark_Grid flops), grid_axpy.csv
(Grid's own memory benchmark) and perfctr.csv (likwid-perfctr on Grid).
Safe to re-run at any time; it always rebuilds from the raw files.
"""
import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results"
OUT = ROOT / "analysis" / "data"


def meta(run_dir):
    m = {}
    f = run_dir / "meta.txt"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.startswith("---"):
                k, v = line.split("=", 1)
                m[k.strip()] = v.strip()
    return m


def runs(node_glob, exp_glob):
    # results/<node>/<experiment>/<job>/
    return sorted(RESULTS.glob(f"{node_glob}/{exp_glob}/*/"))


def write(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        print(f"{name}: no data")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def likwid():
    rows = []
    for d in runs("*", "likwid-*"):
        node, exp, job = d.parts[-3:]
        f = d / "out.csv"
        if not f.exists():
            continue
        for r in csv.DictReader(open(f)):
            rows.append({"node": node, "mode": exp.removeprefix("likwid-"), "job": job, **r})
    write("likwid.csv", rows)


def _find_results(obj, out):
    """Benchmark_Grid JSON nests per-L dicts; find any dict with an L and Gflops_* keys."""
    if isinstance(obj, dict):
        if "L" in obj and any(k.startswith("Gflops_") for k in obj):
            out.append(obj)
        for v in obj.values():
            _find_results(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _find_results(v, out)


def grid():
    flops, axpy = [], []
    for d in runs("*", "grid*"):
        node, exp, job = d.parts[-3:]
        m = meta(d)
        threads = int(re.search(r"T=(\d+)", m.get("args", "T=0")).group(1))
        for jf in d.glob("result*.json"):
            try:
                data = json.load(open(jf))
            except json.JSONDecodeError:
                continue  # run killed mid-write
            base = {"node": node, "experiment": exp, "job": job, "threads": threads,
                    "file": jf.name, "git": m.get("git", "")}
            found = []
            _find_results(data, found)
            for r in found:
                flops.append({**base, "L": r["L"], "precision": r.get("Precision", ""),
                              **{k: v for k, v in r.items() if k.startswith("Gflops_")}})
            for r in data.get("axpy", []) if isinstance(data, dict) else []:
                axpy.append({**base, **r})
    write("grid.csv", flops)
    write("grid_axpy.csv", axpy)


# Metrics we want from likwid-perfctr (names differ a bit between Intel and AMD groups).
PERF_METRICS = re.compile(r"(Runtime \(RDTSC\)|Memory bandwidth|Memory data volume|"
                          r"[SD]P \[MFLOP/s\]|AVX.*\[MFLOP/s\]|Operational intensity|L3 bandwidth)", re.I)


def perfctr():
    rows = []
    for d in runs("*", "grid*"):
        node, exp, job = d.parts[-3:]
        m = meta(d)
        threads = int(re.search(r"T=(\d+)", m.get("args", "T=0")).group(1))
        for f in d.glob("perfctr-*.csv"):
            group = f.stem.removeprefix("perfctr-")
            seen = {}
            for line in f.read_text().splitlines():
                cells = line.split(",")
                name = cells[0]
                if not PERF_METRICS.search(name):
                    continue
                nums = [c for c in cells[1:] if re.fullmatch(r"-?[\d.]+(e[+-]?\d+)?", c)]
                if not nums:
                    continue
                # Multi-thread files have a "... STAT" row whose first number is the Sum;
                # prefer it over the per-thread row.
                key = name.replace(" STAT", "")
                if name.endswith("STAT") or key not in seen:
                    seen[key] = float(nums[0])
            for k, v in seen.items():
                rows.append({"node": node, "job": job, "threads": threads, "group": group,
                             "metric": k, "value": v})
    write("perfctr.csv", rows)


if __name__ == "__main__":
    likwid()
    grid()
    perfctr()
