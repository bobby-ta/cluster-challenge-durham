#!/usr/bin/env python3
"""Count our testbed jobs for the time-efficiency mark.

    python3 analysis/job_count.py [--since 2026-10-19]

do022 is shared by every team, so a job counts as ours if its id appears in results/
(directory names, runlog.csv, Slurm .out names) or its user is in TEAM_USERS (config/team.env).
Writes job_count.csv (node x experiment x state, with node-hours) and prints the totals.
Needs sacct, so run it on COSMA.
"""
import csv, os, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
OUT = ROOT / "analysis" / "data"


def our_ids():
    """job id -> (node, experiment) for every job that left something in results/."""
    ids = {}
    for d in RESULTS.glob("*/*/*/"):
        node, exp, job = d.parts[-3:]
        ids.setdefault(job.split("_", 1)[0], (node, exp))
    log = RESULTS / "runlog.csv"
    if log.exists():
        with log.open(newline="") as f:
            for r in csv.DictReader(f):
                ids.setdefault(r["job"].split("_", 1)[0], (r["node"], r["experiment"]))
    for f in (RESULTS / "slurm").glob("*.out"):
        m = re.match(r"(.+?)-(dine2?)-(\d+)", f.name)
        if m:
            ids.setdefault(m.group(3), (m.group(2), m.group(1)))
    return ids


def team_users():
    env = (ROOT / "config" / "team.env").read_text()
    m = re.search(r'TEAM_USERS="([^"]*)"', env)
    return {u for u in (m.group(1).split() if m else []) if not u.startswith("TODO")}


def seconds(t):
    days, _, t = t.rpartition("-")
    parts = [int(p) for p in t.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(days) if days else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def main():
    since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else "2026-10-19"
    cmd = ["sacct", "-a", "-A", "do022", "-S", since, "-X", "-P", "-n",
           "-o", "JobID,User,Partition,JobName,State,Elapsed"]
    lines = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines()
    ids, users = our_ids(), team_users()
    agg = defaultdict(lambda: [0, 0.0])
    for line in lines:
        jobid, user, part, name, state, elapsed = line.split("|")
        base = jobid.split("_", 1)[0]
        if base not in ids and user not in users:
            continue
        node = part.removeprefix("ciuk-")
        exp = ids.get(base, (node, name))[1]
        key = (node, exp, state.split()[0])
        agg[key][0] += 1
        agg[key][1] += seconds(elapsed) / 3600
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "job_count.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node", "experiment", "state", "jobs", "node_hours"])
        for (node, exp, state), (n, h) in sorted(agg.items()):
            w.writerow([node, exp, state, n, f"{h:.2f}"])
    total = sum(v[0] for v in agg.values())
    hours = sum(v[1] for v in agg.values())
    done = sum(v[0] for k, v in agg.items() if k[2] == "COMPLETED")
    print(f"job_count.csv: {len(agg)} rows; {total} jobs ({done} completed), {hours:.1f} node-hours"
          f"{'' if users else ' (TEAM_USERS unset: matched by results/ job ids only)'}")


if __name__ == "__main__":
    main()
