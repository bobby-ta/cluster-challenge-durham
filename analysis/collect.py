#!/usr/bin/env python3
"""Gather usable runs under results/ into tidy CSVs in analysis/data/.

    python3 analysis/collect.py [results_dir]

Writes likwid.csv (likwid-bench), grid.csv (Benchmark_Grid flops), grid_axpy.csv
(Grid's own memory benchmark) and perfctr.csv (likwid-perfctr on Grid).
Safe to re-run at any time; it always rebuilds from the raw files.
"""
import csv, hashlib, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results"
OUT = ROOT / "analysis" / "data"

# Exclude whole jobs, including their usable single-core rows, to keep reruns separate.
# See issue #2. The old DINE compute jobs are retained only for plots.py's validated reuse.
EXCLUDED_JOBS = {
    "12200764": "DINE sizes: all-core rows used 32 SMT threads on 16 physical cores",
    "12203200": "DINE2 compute: SMT pinning; DINE's AVX reuse was not validated here",
    "12203201": "DINE2 bandwidth: SMT pinning, full node was not measured",
    "12203202": "DINE2 sizes: all-core rows used 64 SMT threads on 32 physical cores (socket 0)",
}


def meta(run_dir):
    m = {}
    f = run_dir / "meta.txt"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.startswith("---"):
                k, v = line.split("=", 1)
                m[k.strip()] = v.strip()
    return m


def runlog_rows():
    """Keep every group result; a later successful group must not hide a failure."""
    logged = {}
    runlog = RESULTS / "runlog.csv"
    if runlog.exists():
        with runlog.open(newline="") as f:
            for row in csv.DictReader(f):
                key = (row["node"], row["experiment"], row["job"])
                logged.setdefault(key, []).append(row)
    return logged


def log_group(row):
    match = re.match(r"perfctr\s+(\S+)(?:\s|$)", row.get("note", ""))
    return match.group(1) if match else None


def completion(run_dir, logged, group=None):
    """Gate each measurement, conservatively retaining unlogged legacy data.

    General job failures apply to every group. Group-specific failures only apply
    to that group. Unlogged legacy output remains inspectable, but is not treated
    as verified counter evidence. Repeated conflicting statuses fail closed.
    """
    key = tuple(run_dir.parts[-3:])
    rows = logged.get(key, [])
    relevant = [r for r in rows if group is None or log_group(r) in (None, group)]
    status = meta(run_dir).get("status", "").strip().lower()
    if status and status != "ok":
        return False, f"meta status={status}"
    failed = [r for r in relevant if r.get("status", "").strip().lower() != "ok"]
    if failed:
        return False, f"runlog status={failed[0].get('status')}: {failed[0].get('note', '')}"
    if relevant or status == "ok":
        return True, "recorded-ok"
    if rows:  # Other groups exist, but this group has no completion evidence.
        return False, "no completion entry for this group"
    return True, "legacy-unlogged"


def runs(node_glob, exp_glob, allow_group_failures=False):
    # results/<node>/<experiment>/<job>/
    logged = runlog_rows()
    for d in sorted(RESULTS.glob(f"{node_glob}/{exp_glob}/*/")):
        node, exp, job = d.parts[-3:]
        reason = EXCLUDED_JOBS.get(job.split("_", 1)[0])
        if exp.startswith("grid") and (d / "record.json").exists():
            # Overnight has stricter validation and a different build/runtime
            # schema. Its campaign adapter owns integration, not this collector.
            reason = "record.json campaign: use its validated overnight adapter"
        if allow_group_failures:
            # File-level completion() below checks individual perfctr groups.
            general = {k: [r for r in rows if log_group(r) is None]
                       for k, rows in logged.items()}
            accepted, evidence = completion(d, general)
        else:
            accepted, evidence = completion(d, logged)
        if not reason and not accepted:
            reason = evidence
        if reason:
            print(f"SKIP {d}: {reason}", file=sys.stderr)
            continue
        # Older completed measurements may have no runlog entry. Explicit exclusions
        # above cover known bad jobs; absence from the log alone is not a failure.
        yield d


def argument(args, name):
    """Read a recorded KEY=value (including spaces) up to the next KEY=."""
    match = re.search(r"(?:^|\s)" + re.escape(name) + r"=(.*?)(?=\s+[A-Z_]+=|$)", args)
    return match.group(1).strip() if match else ""


def fingerprint(path, strip_addresses=False):
    if not path.is_file() or not path.stat().st_size:
        return ""
    text = path.read_text(errors="replace")
    if strip_addresses:
        text = re.sub(r"0x[0-9a-fA-F]+", "ADDRESS", text)
    return hashlib.sha256(text.encode()).hexdigest()


def grid_metadata(d):
    """Identity for controlled curves; missing build/runtime/host isolates a run.

    Host is intentionally retained: default OMP_PLACES=cores had different
    effective placements on gc007. A later audited adapter may combine machines
    with demonstrably equivalent topology, but this collector does not assume it.
    """
    node, exp, job = d.parts[-3:]
    m = meta(d)
    args = m.get("args", "")
    t = argument(args, "T")
    if not t.isdigit() or int(t) <= 0:
        print(f"SKIP {d}: no positive T=... in meta.txt", file=sys.stderr)
        return None
    base = {"node": node, "experiment": exp, "job": job, "threads": int(t),
            "git": m.get("git", ""), "config": m.get("GRID_CONFIG", ""),
            "bind": m.get("OMP_PROC_BIND", ""), "omp_places": m.get("OMP_PLACES", ""),
            "numactl": argument(args, "NUMACTL"), "max_l": argument(args, "MAX_L"),
            "grid_extra": argument(args, "GRID_EXTRA"), "host": m.get("host", ""),
            "cpu": m.get("cpu", ""), "env_root": m.get("GRID_ENV_ROOT", ""),
            "build_fingerprint": fingerprint(d / "build-flags.txt"),
            "runtime_fingerprint": fingerprint(d / "ldd.txt", strip_addresses=True)}
    keys = ("node", "experiment", "config", "bind", "omp_places", "numactl", "max_l",
            "grid_extra", "host", "cpu", "env_root", "build_fingerprint", "runtime_fingerprint")
    identity = {k: base[k] for k in keys}
    missing = [k for k in ("build_fingerprint", "runtime_fingerprint", "host", "config", "max_l")
               if not base[k]]
    if missing:
        identity["unverified_run"] = job
    base["provenance_status"] = "recorded" if not missing else "isolated-missing-" + ",".join(missing)
    base["provenance_id"] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    base["counter_pair_id"] = m.get("COUNTER_PAIR_ID", "") or argument(args, "COUNTER_PAIR_ID")
    return base


def positive(value):
    try:
        return math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError):
        return False


def write(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        # Do not leave an old plot input behind when the source runs disappear.
        (OUT / name).unlink(missing_ok=True)
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
        with f.open(newline="") as source:
            for r in csv.DictReader(source):
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


def grid_results(data):
    """Select one per-L result source, avoiding duplicate flops/results entries."""
    if isinstance(data, dict):
        for name in ("results", "flops"):
            if name in data:
                found = []
                _find_results(data[name], found)
                if found:
                    return found
    found = []
    _find_results(data, found)
    return found


def workload_fingerprint(data):
    """Observed benchmark cases, excluding measured performance values.

    Matching --max-L alone is insufficient when a memory limit changes which
    cases actually execute. Include the axpy cases in a whole-process pairing.
    """
    if not isinstance(data, dict):
        return ""
    cases = [(r.get("L"), r.get("Precision", ""), sorted(k for k in r if k.startswith("Gflops_")))
             for r in grid_results(data)]
    axpy = [(r.get("L"), r.get("size_MB")) for r in data.get("axpy", []) if isinstance(r, dict)]
    other = {k: [(r.get("L"), r.get("Precision", ""), r.get("size_MB"))
                 for r in values if isinstance(r, dict) and "L" in r]
             for k, values in data.items() if isinstance(values, list) and k not in ("axpy", "results")}
    return hashlib.sha256(json.dumps({"flops": cases, "axpy": axpy, "other": other},
                                     sort_keys=True).encode()).hexdigest()[:16] if cases else ""


def grid():
    flops, axpy = [], []
    logged = runlog_rows()
    for d in runs("*", "grid*", allow_group_failures=True):
        metadata = grid_metadata(d)
        if metadata is None:
            continue
        for jf in d.glob("result*.json"):
            group = jf.stem.removeprefix("result-") if jf.stem.startswith("result-") else None
            accepted, evidence = completion(d, logged, group)
            if not accepted:
                print(f"SKIP {jf}: {evidence}", file=sys.stderr)
                continue
            try:
                with jf.open() as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                print(f"SKIP {jf}: incomplete/unreadable JSON", file=sys.stderr)
                continue  # run killed mid-write
            base = {**metadata, "file": jf.name, "completion_evidence": evidence}
            seen = set()
            for r in grid_results(data):
                key = (r["L"], r.get("Precision", ""))
                if key in seen:
                    continue
                seen.add(key)
                metrics = {k: v for k, v in r.items() if k.startswith("Gflops_") and positive(v)}
                if not positive(r["L"]) or not metrics:
                    continue
                flops.append({**base, "L": r["L"], "precision": r.get("Precision", ""),
                              **metrics})
            for r in data.get("axpy", []) if isinstance(data, dict) else []:
                if not positive(r.get("GBps")):
                    continue
                # Benchmark_Grid divides bytes by 1024^3 despite naming this
                # field GBps. Keep the raw value and export decimal GB/s.
                raw = float(r["GBps"])
                axpy.append({**base, **r, "Grid_raw_GiBps": raw,
                             "GBps": raw * 2**30 / 1e9,
                             "bandwidth_unit": "GB/s", "source_bandwidth_unit": "GiB/s"})
    write("grid.csv", flops)
    write("grid_axpy.csv", axpy)


# Metrics we want from likwid-perfctr (names differ a bit between Intel and AMD groups).
PERF_METRICS = re.compile(r"(Runtime \(RDTSC\)|Memory bandwidth|Memory data volume|"
                          r"[SD]P \[MFLOP/s\]|AVX.*\[MFLOP/s\]|Operational intensity|L3 bandwidth)", re.I)


def perfctr():
    rows = []
    logged = runlog_rows()
    for d in runs("*", "grid*", allow_group_failures=True):
        metadata = grid_metadata(d)
        if metadata is None:
            continue
        for f in d.glob("perfctr-*.csv"):
            group = f.stem.removeprefix("perfctr-")
            accepted, evidence = completion(d, logged, group)
            if not accepted:
                print(f"SKIP {f}: {evidence}", file=sys.stderr)
                continue
            seen = {}
            for cells in csv.reader(f.read_text().splitlines()):
                if not cells:
                    continue
                name = cells[0].strip()
                if not PERF_METRICS.search(name):
                    continue
                nums = []
                for cell in cells[1:]:
                    try:
                        value = float(cell)
                        if math.isfinite(value):
                            nums.append(value)
                    except ValueError:
                        pass
                if not nums:
                    continue
                key = name.removesuffix(" STAT")
                # STAT columns are Sum, Min, Max, Avg. Runtime is wall time,
                # never the sum of per-core elapsed times. Do not sum ratios.
                if key.startswith("Operational intensity") and (len(nums) > 1 or name.endswith("STAT")):
                    continue
                if name.endswith("STAT"):
                    if key.startswith("Runtime"):
                        if len(nums) < 3:
                            continue
                        value, aggregation = nums[2], "max"
                    else:
                        value, aggregation = nums[0], "sum"
                elif key.startswith("Runtime"):
                    value, aggregation = max(nums), "max"
                else:
                    value, aggregation = sum(nums), "sum"
                if name.endswith("STAT") or key not in seen:
                    seen[key] = (value, aggregation)
            runtime = next((v for k, (v, _) in seen.items() if k.startswith("Runtime (RDTSC)")), None)
            jf = d / f"result-{group}.json"
            json_ok = False
            workload = ""
            if jf.is_file():
                try:
                    data = json.loads(jf.read_text())
                    json_ok = any(any(k.startswith("Gflops_") and positive(v) for k, v in r.items())
                                  for r in grid_results(data))
                    workload = workload_fingerprint(data)
                except (ValueError, OSError):
                    pass
            pair_id = metadata["counter_pair_id"] or "run:" + "/".join(d.parts[-3:])
            for k, (v, aggregation) in seen.items():
                if not positive(v):
                    continue
                rows.append({**metadata, "group": group, "metric": k, "value": v,
                             "measurement_id": "/".join(d.parts[-3:]) + "/" + group,
                             "counter_pair_id": pair_id, "runtime_s": runtime,
                             "workload_fingerprint": workload,
                             "counter_aggregation": aggregation, "scope": "whole_process",
                             "completion_evidence": evidence,
                             "plot_eligible": evidence == "recorded-ok" and json_ok and positive(runtime)})
    write("perfctr.csv", rows)


if __name__ == "__main__":
    likwid()
    grid()
    perfctr()
