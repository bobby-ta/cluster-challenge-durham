#!/usr/bin/env python3
"""Plot the controlled 23 October DINE2 close-versus-spread experiment.

This is deliberately separate from the Clang/OpenMPI overnight campaign.
Run from any directory after ``python3 analysis/collect.py``:

    python3 analysis/plot_dine2_socket.py

Reads the collector's verified result.json rows, requires three independent
Slurm jobs per configuration, checks identical hardware/build/runtime identity,
and draws min--max whiskers around three-run median FP32 DWF4 throughput.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "analysis" / "data" / "grid.csv"
DEFAULT_FIGURE = ROOT / "report" / "figs" / "dine2_socket_placement.pdf"
MODES = {"grid-final-one-socket": "one socket", "grid-final-two-socket": "two sockets"}
THREADS = (24, 32)
LATTICES = (24, 32)


def load_verified(csv_path: Path):
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    required = ("node", "experiment", "job", "threads", "L", "precision", "file",
                "completion_evidence", "config", "bind", "host", "cpu", "omp_places",
                "max_l", "build_fingerprint", "runtime_fingerprint", "Gflops_dwf4")
    if not rows or any(key not in rows[0] for key in required):
        raise ValueError("Missing validated collector fields; run analysis/collect.py")

    selected = []
    for row in rows:
        if (row["node"] != "dine2" or row["experiment"] not in MODES
                or row["file"] != "result.json" or row["precision"] != "FP32"
                or int(row["threads"]) not in THREADS or int(row["L"]) not in LATTICES):
            continue
        if row["completion_evidence"] != "recorded-ok":
            raise ValueError(f"Unverified completion for {row['job']}")
        if row["config"] != "cpu-avx512":
            raise ValueError(f"Unexpected build configuration for {row['job']}")
        expected_bind = "close" if row["experiment"] == "grid-final-one-socket" else "spread"
        if row["bind"] != expected_bind:
            raise ValueError(f"Unexpected binding for {row['job']}: {row['bind']}")
        if not row["build_fingerprint"] or not row["runtime_fingerprint"]:
            raise ValueError(f"Missing build/runtime provenance for {row['job']}")
        rate = float(row["Gflops_dwf4"])
        if not 0 < rate < 100000:
            raise ValueError(f"Invalid DWF4 performance for {row['job']}: {rate}")
        selected.append(row)

    if not selected:
        raise ValueError(
            "No final DINE2 socket-placement runs found; import the "
            "grid-final-one-socket and grid-final-two-socket job records, "
            "then run analysis/collect.py"
        )

    # The host, compiler output and OMP_PLACES must match. PROC_BIND is the
    # intentionally changed variable, and should not appear in this identity.
    identity_fields = ("host", "cpu", "config", "git", "omp_places", "numactl", "max_l",
                       "grid_extra", "env_root", "build_fingerprint", "runtime_fingerprint")
    identities = {tuple(r.get(field, "") for field in identity_fields) for r in selected}
    if len(identities) != 1:
        raise ValueError("Final placement runs differ in host/build/runtime; cannot pool them")

    grouped = defaultdict(list)
    for row in selected:
        grouped[(row["experiment"], int(row["L"]), int(row["threads"]))].append(row)
    results = {}
    for mode in MODES:
        for lattice in LATTICES:
            for threads in THREADS:
                key = (mode, lattice, threads)
                group = grouped[key]
                jobs = {r["job"] for r in group}
                if len(group) != 3 or len(jobs) != 3:
                    raise ValueError(f"Expected exactly 3 independent jobs for {key}; got {sorted(jobs)}")
                data = [float(r["Gflops_dwf4"]) for r in group]
                results[key] = {"median": statistics.median(data), "min": min(data),
                                "max": max(data), "jobs": sorted(jobs)}
    return results, selected[0]["host"]


def make_figure(results, host: str, output: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(8.0, 3.7))
    fig.subplots_adjust(left=.095, right=.985, top=.87, bottom=.25)
    xpos = list(range(4))
    labels = [f"L{lattice} · {threads}T" for lattice in LATTICES for threads in THREADS]
    colors = {"grid-final-one-socket": "#2074A0", "grid-final-two-socket": "#DB7B26"}
    width = 0.34
    for mode, offset in (("grid-final-one-socket", -width / 2),
                         ("grid-final-two-socket", width / 2)):
        values, lo, hi = [], [], []
        for lattice in LATTICES:
            for threads in THREADS:
                d = results[(mode, lattice, threads)]
                values.append(d["median"])
                lo.append(d["median"] - d["min"])
                hi.append(d["max"] - d["median"])
        bars = ax.bar([x + offset for x in xpos], values, width=width,
                      color=colors[mode], label=MODES[mode].capitalize())
        ax.errorbar([x + offset for x in xpos], values, yerr=[lo, hi], fmt="none",
                    ecolor="#272727", elinewidth=1, capsize=2.5, zorder=4)
        if mode == "grid-final-two-socket":
            for i, bar in enumerate(bars):
                lattice, threads = LATTICES[i // len(THREADS)], THREADS[i % len(THREADS)]
                close = results[("grid-final-one-socket", lattice, threads)]["median"]
                gain = (values[i] / close - 1) * 100
                ax.annotate(f"+{gain:.1f}%", (bar.get_x() + bar.get_width()/2, hi[i] + values[i]),
                            xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8)

    ax.set_xticks(xpos, labels)
    ax.set_ylim(0, 710)
    ax.set_ylabel("FP32 DWF4 throughput (GFLOP/s)")
    ax.set_title("DINE2 socket placement · GCC AVX-512 · 3 independent repeats")
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    fig.text(.5, .035, f"Same {host.split('.')[0]} node, build and OMP_PLACES; "
                         "only OMP_PROC_BIND changes (close → spread). "
                         "Whiskers: min–max.",
             ha="center", fontsize=8)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    fig.savefig(output.with_suffix(".png"), dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_FIGURE)
    args = parser.parse_args()
    results, host = load_verified(args.data)
    for lattice in LATTICES:
        for threads in THREADS:
            one = results[("grid-final-one-socket", lattice, threads)]["median"]
            two = results[("grid-final-two-socket", lattice, threads)]["median"]
            print(f"L{lattice} {threads}T: close {one:.3f} | spread {two:.3f} GFLOP/s "
                  f"| {(two / one - 1) * 100:+.1f}%")
    make_figure(results, host, args.output)
    print(f"wrote {args.output} and {args.output.with_suffix('.png')}")


if __name__ == "__main__":
    main()
