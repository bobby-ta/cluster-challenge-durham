"""Regenerate submission figures from the validated overnight CSV exports.

The two experiment families are deliberately separate: this module reads only
the Clang/OpenMPI4 overnight campaign. GCC tuning/LIKWID data from
``analysis/data`` are never pooled into these summaries.

Run from the repository root:
    python3 analysis/plot_overnight_exports.py

The original overnight CSVs and figures are never modified; publication figures
are written to ``report/figs/overnight-20261022T224854Z/submission_*.pdf``.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

CAMPAIGN = "20261022T224854Z"
HERE = Path(__file__).resolve().parent
DATA = HERE / f"overnight-{CAMPAIGN}"
FIGS = HERE.parent / "report" / "figs" / f"overnight-{CAMPAIGN}"


def rows(filename: str, data_dir: Path = DATA) -> list[dict]:
    with (data_dir / filename).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def strong_rows(data_dir: Path = DATA) -> list[dict]:
    data = []
    for r in rows("strong_scaling.csv", data_dir):
        if (
            r["metric"] != "Gflops_dwf4"
            or r["config"] not in ("cpu-avx2", "cpu-avx512")
            or r["placement"] != "compact"
            or r["numa_policy"] != "default"
            or int(r["L"]) not in (24, 32)
        ):
            continue
        if int(r["n"]) != 3:
            raise ValueError(f"Strong-scaling point has fewer than 3 repetitions: {r}")
        data.append(r)
    for node in ("dine", "dine2"):
        for lattice in (24, 32):
            series = [r for r in data if r["node"] == node and int(r["L"]) == lattice]
            if not series or min(int(r["threads"]) for r in series) != 1:
                raise ValueError(f"Missing valid one-core baseline: {node}, L={lattice}")
            one = next(r for r in series if int(r["threads"]) == 1)
            baseline = float(one["median"])
            for r in series:
                t = int(r["threads"])
                if not math.isclose(float(r["speedup"]), float(r["median"]) / baseline, rel_tol=1e-7):
                    raise ValueError(f"Inconsistent exported speedup: {node}, L={lattice}, T={t}")
    return data


def weak_rows(data_dir: Path = DATA) -> list[dict]:
    selected = []
    for r in rows("weak_scaling.csv", data_dir):
        if (r["metric"] == "Gflops_dwf4" and r["placement"] == "compact"
                and r["numa_policy"] == "default" and r["comparison"] == "exact"
                and ((int(r["small_L"]), int(r["small_threads"]), int(r["large_L"]), int(r["large_threads"]))
                     in {(16, 2, 32, 32), (24, 2, 48, 32)})):
            if float(r["workload_mismatch"]) != 0:
                raise ValueError("Exact weak-scaling pair changed sites/thread")
            selected.append(r)
    if len(selected) != 4:
        raise ValueError(f"Expected both matched comparisons on each node, got {len(selected)}")
    return selected


def ceiling(data_dir: Path, node: str, kind: str) -> float:
    chosen = [r for r in rows("ceilings.csv", data_dir) if r["node"] == node and r["kind"] == kind]
    if len(chosen) != 1 or int(chosen[0]["n"]) != 3:
        raise ValueError(f"Expected one median-of-three {kind} ceiling on {node}")
    return float(chosen[0]["median"])


def counter_rows(data_dir: Path = DATA) -> list[dict]:
    result = []
    for r in rows("whole_process_estimates.csv", data_dir):
        if str(r["plot_eligible"]).lower() != "true":
            continue
        if r["placement"] != "compact" or r["numa_policy"] != "default":
            continue
        if r["counter_mode"] not in ("simultaneous", "separate_passes"):
            raise ValueError(f"Unknown counter mode: {r['counter_mode']}")
        for key in ("SP_GFLOPs", "DRAM_GBps", "approximate_SP_FLOP_per_byte"):
            if not math.isfinite(float(r[key])) or float(r[key]) <= 0:
                raise ValueError(f"Bad {key} in {r}")
        intensity = float(r["SP_GFLOPs"]) / float(r["DRAM_GBps"])
        if not math.isclose(intensity, float(r["approximate_SP_FLOP_per_byte"]), rel_tol=1e-8):
            raise ValueError("Counter-derived arithmetic intensity mismatch")
        if r["counter_mode"] == "separate_passes" and float(r["runtime_relative_difference"]) > .2:
            raise ValueError("Separate counter passes differ by more than 20% in runtime")
        result.append(r)
    for node, max_threads in (("dine", 32), ("dine2", 64)):
        full = [r for r in result if r["node"] == node and int(r["threads"]) == max_threads]
        if len(full) != 1 or full[0]["counter_mode"] != "simultaneous":
            raise ValueError(f"No unique simultaneous full-node counter pair on {node}")
    return result


def axpy_l64(data_dir: Path = DATA) -> dict[str, float]:
    import statistics
    out = {}
    for node, threads in (("dine", 32), ("dine2", 64)):
        matches = [r for r in rows("grid_axpy.csv", data_dir)
                   if r["node"] == node and r["mode"] == "extended"
                   and r["placement"] == "compact" and r["numa_policy"] == "default"
                   and int(r["L"]) == 64 and int(r["threads"]) == threads]
        unique_jobs = {r["source"] for r in matches}
        if len(matches) != 3 or len(unique_jobs) != 3:
            raise ValueError(f"Expected three independent L64 axpy runs on {node}")
        for r in matches:
            decimal = float(r["GiBps_reported"]) * 2**30 / 1e9
            if not math.isclose(decimal, float(r["GBps_decimal"]), rel_tol=1e-8):
                raise ValueError("Grid axpy binary/decimal bandwidth conversion failed")
            if not math.isclose(float(r["size_MiB"]), 3072., rel_tol=1e-8):
                raise ValueError("L64 working-set size changed")
        out[node] = statistics.median(float(r["GBps_decimal"]) for r in matches)
    return out


def make_plots(data_dir: Path = DATA, fig_dir: Path = FIGS) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = strong_rows(data_dir)
    w = weak_rows(data_dir)
    c = counter_rows(data_dir)
    axpy = axpy_l64(data_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42})
    palette = {24: "#2074A0", 32: "#DB7B26"}

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.15), sharey=True, layout="constrained")
    for axis, node, last in zip(axes, ("dine", "dine2"), (32, 64)):
        for lattice in (24, 32):
            seq = sorted((r for r in s if r["node"] == node and int(r["L"]) == lattice),
                         key=lambda r: int(r["threads"]))
            xs = [int(r["threads"]) for r in seq]
            ys = [100 * float(r["parallel_efficiency"]) for r in seq]
            axis.plot(xs, ys, "o-", ms=3.4, lw=1.75, color=palette[lattice],
                      label=f"L{lattice}, {ys[-1]:.1f}% at {last}T")
        axis.axhline(100, ls="--", lw=.85, color="#858B91", alpha=.8)
        axis.set_title(node.upper())
        ticks = [1, 2, 4, 8, 16, 32] + ([48, 64] if last == 64 else [])
        axis.set_xscale("log", base=2)
        axis.set_xticks(ticks, labels=[str(t) for t in ticks])
        axis.minorticks_off()
        axis.set_xlim(.85, last * 1.12)
        axis.set_ylim(0, 108)
        axis.set_xlabel("Physical OpenMP threads")
        axis.grid(axis="y", alpha=.2)
        axis.legend(fontsize=7, loc="lower left")
    axes[0].set_ylabel("Strong-scaling efficiency (%)")
    fig.suptitle("Grid FP32 DWF4: fixed L24 and L32, three-run medians", fontsize=10)
    fig.savefig(fig_dir / "submission_strong_scaling.pdf", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.8, 2.9), layout="constrained")
    keys = ((16, 2, 32, 32), (24, 2, 48, 32))
    positions = [0, 1]
    for idx, (node, shift, color) in enumerate((("dine", -.18, "#2074A0"),
                                                ("dine2", .18, "#DB7B26"))):
        vals = []
        for key in keys:
            r = next(r for r in w if r["node"] == node and
                     tuple(int(r[x]) for x in ("small_L", "small_threads", "large_L", "large_threads")) == key)
            vals.append(100 * float(r["per_thread_throughput_retention"]))
        bars = ax.bar([p + shift for p in positions], vals, width=.34, color=color, label=node.upper())
        ax.bar_label(bars, fmt="%.1f%%", padding=2, fontsize=8)
    ax.axhline(100, color="#858B91", ls="--", lw=.9, label="Ideal")
    ax.set_xticks(positions, ["L16 / 2T → L32 / 32T", "L24 / 2T → L48 / 32T"])
    ax.set_ylabel("Per-thread throughput retained (%)")
    ax.set_ylim(0, 115)
    ax.set_title("Exact single-node weak scaling: constant $L^4/T$")
    ax.legend(ncol=3, loc="upper right", fontsize=8)
    fig.savefig(fig_dir / "submission_weak_scaling.pdf", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.2), sharex=True, sharey=True, layout="constrained")
    for ax, node in zip(axes, ("dine", "dine2")):
        p = ceiling(data_dir, node, "FP32_compute")
        bw = ceiling(data_dir, node, "DRAM_non-temporal")
        x = [10 ** (-1 + n * .025) for n in range(160)]
        y = [min(p, bw * a) for a in x]
        ax.plot(x, y, color="#2C4656", lw=1.6, label="Empirical NT roof")
        for r in (r for r in c if r["node"] == node):
            intensity = float(r["approximate_SP_FLOP_per_byte"])
            throughput = float(r["SP_GFLOPs"])
            th = int(r["threads"])
            marker = "o" if r["counter_mode"] == "simultaneous" else "s"
            ax.scatter([intensity], [throughput], marker=marker, s=41, zorder=3,
                       color="#DB7B26" if marker == "o" else "#2074A0", edgecolors="white")
            ax.annotate(f"{th}T", (intensity, throughput), xytext=(5, 5),
                        textcoords="offset points", fontsize=7)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(.7, 80)
        ax.set_ylim(8, 16000)
        ax.grid(alpha=.15, which="both")
        ax.set_title(f"{node.upper()}: roof {bw:.0f} GB/s, {p:.0f} GFLOP/s")
        ax.set_xlabel("Whole-process SP FLOP / DRAM byte")
    axes[0].set_ylabel("Whole-process FP32 GFLOP/s")
    fig.suptitle("Measured aggregate counter points (squares: separate passes; circles: simultaneous)", fontsize=9)
    fig.savefig(fig_dir / "submission_roofline.pdf", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.8, 3.1), layout="constrained")
    labels = ["DINE · 32 cores", "DINE2 · 64 cores"]
    x = [0, 1]
    grid_vals = [axpy[n] for n in ("dine", "dine2")]
    temporal = [ceiling(data_dir, n, "DRAM_temporal") for n in ("dine", "dine2")]
    left = ax.bar([p - .18 for p in x], grid_vals, width=.34,
                  color="#2074A0", label="Grid FP64 axpy, L64")
    right = ax.bar([p + .18 for p in x], temporal, width=.34,
                   color="#DB7B26", label="LIKWID temporal triad")
    ax.bar_label(left, fmt="%.1f", padding=2, fontsize=8)
    ax.bar_label(right, fmt="%.1f", padding=2, fontsize=8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Useful-byte bandwidth (decimal GB/s)")
    ax.set_ylim(0, 445)
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Separate full-node benchmark runs; different kernels and working sets")
    fig.savefig(fig_dir / "submission_axpy_vs_likwid.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Verified all overnight export comparisons and wrote 4 publication figures to", fig_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--figures", type=Path, default=FIGS)
    args = parser.parse_args()
    make_plots(args.data, args.figures)
