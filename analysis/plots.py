#!/usr/bin/env python3
"""Make every report figure from analysis/data/*.csv (run collect.py first).

    python3 analysis/plots.py            # -> report/figs/*.pdf (vector, for LaTeX) + .png

Medians over repeats are plotted; min-max as a band so the variance is visible.
"""
from pathlib import Path
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from peaks import NODES, peaks

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "analysis" / "data"
FIGS = ROOT / "report" / "figs"

# Categorical slots in fixed order (validated palette); text stays in neutral ink.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRIDC = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "legend.fontsize": 7,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRIDC, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.5, "lines.markersize": 4,
    "legend.frameon": False, "figure.dpi": 150,
})
ONE_COL = (3.4, 2.3)  # fits one column of a two-column A4 report


def save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIGS / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def discard(name):
    """Remove generated figures whose valid source measurements are now absent."""
    for ext in ("pdf", "png"):
        (FIGS / f"{name}.{ext}").unlink(missing_ok=True)


def load(name):
    f = DATA / name
    return pd.read_csv(f) if f.exists() else None


def ref_line(ax, y, label):
    ax.axhline(y, color=INK2, lw=1, ls="--")
    ax.set_ylim(0, max(ax.get_ylim()[1], y * 1.12))
    ax.annotate(label, (1, y), xycoords=("axes fraction", "data"), ha="right", va="bottom",
                color=INK2, fontsize=7)


def below(ax, ncol=2):
    """Legend under the axes, so it can never sit on top of data or reference lines."""
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=ncol)
    ax.figure.set_size_inches(ONE_COL[0], ONE_COL[1] + 0.5)


def band(ax, g, x, y, color, label, ls="-"):
    s = g.groupby(x)[y].agg(["median", "min", "max"]).reset_index()
    ax.plot(s[x], s["median"], marker="o", color=color, ls=ls, label=label)
    ax.fill_between(s[x].to_numpy(dtype=float), s["min"].to_numpy(dtype=float),
                    s["max"].to_numpy(dtype=float), color=color, alpha=0.15, lw=0)


def flops_rows(d):
    """Fixed compute runs only (one thread per physical core), same method on both nodes.

    The legacy DINE "threads" jobs 12200761-3 (2 SMT threads per core) matched the fixed run
    for AVX kernels but are left out so DINE and DINE2 use an identical method.
    """
    compute = d.kernel.str.startswith("peakflops", na=False)
    fixed = d[(d["mode"] == "flops") & compute & (d.placement == "compact")]
    return fixed.assign(GFlops=lambda x: x.MFlops / 1e3)


def likwid_plots(df):
    for node in sorted(set(NODES) | set(df.node)):
        d = df[df.node == node]
        pk = peaks(node)
        # Bandwidth vs cores
        bw = d[d["mode"] == "bw"]
        if len(bw):
            fig, ax = plt.subplots(figsize=ONE_COL)
            for i, k in enumerate(k for k in ["load_avx", "copy_avx", "triad_avx", "triad_mem_avx",
                                              "stream_avx", "copy_mem_avx", "stream_mem_avx"]
                                  if k in set(bw.kernel)):
                for pl, ls in [("compact", "-"), ("scatter", ":")]:
                    g = bw[(bw.kernel == k) & (bw.placement == pl)].assign(GBps=lambda x: x.MBps / 1e3)
                    if len(g):
                        band(ax, g, "threads", "GBps", SERIES[i], f"{k} ({pl})", ls)
            if pk:
                ref_line(ax, pk["gbs"], f"theoretical {pk['gbs']:.0f} GB/s")
            ax.set(xlabel="cores (1 thread each)", ylabel="GB/s", title=f"{node}: memory bandwidth vs cores")
            below(ax)
            save(fig, f"likwid_bw_threads_{node}")
        else:
            discard(f"likwid_bw_threads_{node}")

        # Flops vs threads
        fl = flops_rows(d)
        if len(fl):
            fig, ax = plt.subplots(figsize=ONE_COL)
            for i, (k, g) in enumerate(fl.groupby("kernel")):
                band(ax, g, "threads", "GFlops", SERIES[i % len(SERIES)], k)
            if pk:
                ref_line(ax, pk["gflops_sp"], "SP peak (base clock)")
                ref_line(ax, pk["gflops_dp"], "DP peak (base clock)")
            ax.set(xlabel="cores (1 thread each)", ylabel="GFLOP/s", title=f"{node}: compute vs cores")
            below(ax)
            save(fig, f"likwid_flops_threads_{node}")
        else:
            discard(f"likwid_flops_threads_{node}")

        # Bandwidth vs working set
        s = d[d["mode"] == "sizes"].copy()
        if len(s):
            s["kB"] = s["size"].str.extract(r"(\d+)").astype(float)[0] * \
                s["size"].str.extract(r"([kMG])B")[0].map({"k": 1, "M": 1024, "G": 1024**2})
            s["GBps"] = s.MBps / 1e3
            fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.3))
            ncores = int(s[s.placement == "all"].threads.max()) if (s.placement == "all").any() else 0
            for ax, pl in zip(axes, ["single", "all"]):
                for i, (k, g) in enumerate(s[s.placement == pl].groupby("kernel")):
                    band(ax, g, "kB", "GBps", SERIES[i], k)
                title = "1 core" if pl == "single" else f"all {ncores} cores, 1 thread each"
                ax.set(xscale="log", yscale="log", xlabel="working set per thread",
                       ylabel="GB/s", title=f"{node}: {title}")
                ticks = [16, 256, 4096, 65536, 1048576]
                ax.set_xticks(ticks, ["16 kB", "256 kB", "4 MB", "64 MB", "1 GB"])
                ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
                ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(subs=(1, 2, 5)))
                ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
                ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
                # Cache capacity one thread can use: all cores share each L3 between l3_cores threads
                n = NODES[node]
                l3 = n["l3_kb"] if pl == "single" else n["l3_kb"] / n["l3_cores"]
                lines = [(n["l1_kb"], "L1"), (n["l2_kb"], "L2"), (l3, "L3")]
                if 0.67 < l3 / n["l2_kb"] < 1.5:  # L2 and the L3 share coincide: one line
                    lines = [lines[0], (n["l2_kb"], "L2 ≈ L3 share")]
                for kb, name in lines:
                    ax.axvline(kb, color="0.6", ls="--", lw=0.8, zorder=0)
                    ax.text(kb, 1.0, f" {name}", transform=ax.get_xaxis_transform(),
                            va="top", ha="left", fontsize=7, color="0.4")
            axes[0].legend()
            save(fig, f"likwid_bw_sizes_{node}")
        else:
            discard(f"likwid_bw_sizes_{node}")


def weak_pairs(d, metric, small=24, large=32, tolerance=0.10):
    """Match lattice sizes where L^4/threads differs by at most tolerance."""
    summary = d.groupby(["L", "threads"])[metric].median()
    small_t = sorted(t for l, t in summary.index if l == small)
    large_t = sorted(t for l, t in summary.index if l == large)
    pairs = []
    for t1 in small_t:
        target = small**4 / t1
        if not large_t:
            continue
        t2 = min(large_t, key=lambda t: abs(large**4 / t - target))
        mismatch = abs(large**4 / t2 - target) / target
        if mismatch <= tolerance:
            p1, p2 = summary[(small, t1)], summary[(large, t2)]
            if p1 > 0:
                pairs.append((t1, t2, (p2 / t2) / (p1 / t1), mismatch))
    return pairs


def scaling_rows(df):
    """Only deliberate, uninstrumented FP32 scaling measurements.

    Re-collect old CSVs to obtain provenance IDs. Missing identity is not a licence
    to pool different builds or the gc007/default-placement runtime behaviour.
    """
    required = {"node", "experiment", "precision", "file", "provenance_id"}
    if df is None or not required.issubset(df.columns):
        print("grid plots: re-run collect.py for explicit scaling/provenance columns")
        return pd.DataFrame()
    return df[(df.experiment.isin(["grid", "grid-cover-scaling"]))
              & (df.precision.str.upper() == "FP32") & (df.file == "result.json")
              & df.provenance_id.notna()].copy()


def series_label(d):
    r = d.iloc[0]
    host = str(r.get("host", "unknown-host")).split(".")[0]
    return f"{r.get('config', 'unknown-build')} / {host} / {str(r.provenance_id)[:6]}"


def grid_plots(df):
    # The challenge disables FP64. Never mix FP32 and FP64 values in one curve.
    nodes = set(NODES) | (set(df.node) if df is not None and "node" in df else set())
    for node in nodes:
        discard(f"grid_scaling_{node}")
        discard(f"grid_weak_scaling_{node}")
    discard("grid_vs_L")
    df = scaling_rows(df)
    if df.empty:
        print("grid plots: no eligible FP32 scaling runs")
        return
    metric = "Gflops_dwf4" if "Gflops_dwf4" in df else [c for c in df if c.startswith("Gflops_")][0]
    df = df[pd.to_numeric(df[metric], errors="coerce").map(lambda v: math.isfinite(v) and v > 0)]
    if df.empty:
        return
    for node, d in df.groupby("node"):
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 2.4))
        many = d.provenance_id.nunique() > 1
        weak = []
        i = 0
        for _, series in d.groupby("provenance_id"):
            detail = series_label(series)
            for L, g in series[series.L.isin([16, 24, 32, 48])].groupby("L"):
                label = f"L={L} / {detail}" if many else f"L={L}"
                color = SERIES[i % len(SERIES)]
                band(a1, g, "threads", metric, color, label)
                s = g.groupby("threads")[metric].median()
                if len(s):
                    baseline = min(s.index)
                    eff = s / (s[baseline] * (s.index / baseline))
                    a2.plot(eff.index, eff.values, marker="o", color=color, label=label)
                i += 1
            # Never match a small lattice from one build/host with a large one
            # from another. Missing pairs remain missing, not interpolated.
            weak.extend((detail, *pair) for pair in weak_pairs(series, metric))
        a1.set(xlabel="OpenMP threads", ylabel="GFLOP/s", title=f"{node}: {metric} strong scaling")
        a2.set(xlabel="OpenMP threads", ylabel="relative efficiency", ylim=(0, 1.1),
               title=f"{node}: vs smallest T within each series")
        a1.legend(fontsize=5 if many else 7)
        a2.legend(fontsize=5 if many else 7)
        save(fig, f"grid_scaling_{node}")

        # Weak scaling requires increasing the problem and threads together.
        # L=24 at T and L=32 at approximately 3.16*T have similar sites/core.
        if weak:
            fig, ax = plt.subplots(figsize=ONE_COL)
            labels = [f"{t1} to {t2}" + (f"\n{detail}" if many else "")
                      for detail, t1, t2, _, _ in weak]
            ax.bar(range(len(weak)), [p[3] for p in weak], color=SERIES[0], width=0.7)
            ax.axhline(1.0, color=INK2, ls="--", lw=1)
            ax.set(xticks=list(range(len(weak))), xticklabels=labels,
                   xlabel="threads: L=24 to L=32 (sites/core within 10%)",
                   ylabel="per-core GFLOP/s ratio", title=f"{node}: approximate weak scaling")
            save(fig, f"grid_weak_scaling_{node}")

    # Highest measured T within each provenance series need not be full-node.
    fig, ax = plt.subplots(figsize=ONE_COL)
    for i, ((node, _), d) in enumerate(df.groupby(["node", "provenance_id"])):
        best = d[d.threads == d.threads.max()]
        band(ax, best, "L", metric, SERIES[i % len(SERIES)],
             f"{node}, {best.threads.max()}t / {series_label(d)}")
    ax.set(xlabel="local lattice L (volume L^4)", ylabel="GFLOP/s",
           title=f"{metric}: highest measured T per series")
    ax.legend(fontsize=5)
    save(fig, "grid_vs_L")


def counter_points(perf, runtime_tolerance=0.10):
    """Whole-process estimates with no implicit cross-job or cross-build pairing.

    Separate passes must share an explicit pair ID (or the same Slurm task),
    provenance, thread count and measurement scope, with RDTSC runtimes agreeing
    within 10%. More than one candidate per group is ambiguous and is omitted.
    This is a screening criterion, not proof that two runs executed identical work.
    """
    required = {"node", "threads", "provenance_id", "counter_pair_id", "measurement_id",
                "scope", "plot_eligible", "metric", "value", "runtime_s", "workload_fingerprint"}
    if perf is None or not required.issubset(perf.columns):
        if perf is not None:
            print("roofline: legacy counter CSV has no pairing provenance; re-collect")
        return []
    eligible = perf.plot_eligible.astype(str).str.lower().isin(["true", "1"])
    p = perf[eligible & (perf.scope == "whole_process")].copy()
    points = []
    keys = ["node", "provenance_id", "threads", "counter_pair_id", "workload_fingerprint"]
    for identity, pair in p.groupby(keys, dropna=False):
        if any(pd.isna(v) or str(v) == "" for v in identity):
            continue
        passes = []
        for source, g in pair.groupby("measurement_id"):
            # Duplicate metric rows can be multiple runs/files; never average them.
            if g.metric.duplicated().any():
                continue
            sp = g[g.metric == "SP [MFLOP/s]"]
            bw = g[g.metric.str.startswith("Memory bandwidth")]
            times = pd.to_numeric(g.runtime_s, errors="coerce").dropna().unique()
            if len(times) != 1 or not math.isfinite(times[0]) or times[0] <= 0:
                continue
            passes.append({"source": source, "sp": float(sp.iloc[0].value) if len(sp) == 1 else None,
                           "bw": float(bw.iloc[0].value) if len(bw) == 1 else None,
                           "runtime": float(times[0])})
        simultaneous = [(a, a, "simultaneous") for a in passes if a["sp"] and a["bw"]]
        candidates = simultaneous
        if not simultaneous:
            sp, bw = [a for a in passes if a["sp"]], [a for a in passes if a["bw"]]
            if len(sp) == len(bw) == 1:
                candidates = [(sp[0], bw[0], "separate_passes")]
        for a, b, mode in candidates:
            difference = abs(a["runtime"] - b["runtime"]) / max(a["runtime"], b["runtime"])
            if difference > runtime_tolerance:
                continue
            if not all(math.isfinite(v) and v > 0 for v in (a["sp"], b["bw"])):
                continue
            points.append({"node": identity[0], "provenance_id": identity[1], "threads": identity[2],
                           "SP_GFLOPs": a["sp"] / 1e3, "DRAM_GBps": b["bw"] / 1e3,
                           "approximate_SP_FLOP_per_byte": a["sp"] / b["bw"],
                           "counter_mode": mode, "runtime_relative_difference": difference,
                           "FLOPS_SP_source": a["source"], "MEM_source": b["source"]})
    return points


def roofline(lk, perf):
    """Ceilings from likwid-bench measurements, Grid's points from likwid-perfctr."""
    import numpy as np
    points = counter_points(perf)
    for node in sorted(set(NODES) | set(lk.node)):
        d = lk[lk.node == node]
        fl = flops_rows(d)
        sp = fl[fl.kernel.str.startswith("peakflops_sp", na=False)].MFlops.max() / 1e3
        dp = fl[~fl.kernel.str.startswith("peakflops_sp", na=False)].MFlops.max() / 1e3
        bw = d[(d["mode"] == "bw") & d.kernel.str.contains("triad|stream", na=False)]
        mem = bw.MBps.max() / 1e3
        if any(pd.isna([sp, mem])):
            discard(f"roofline_{node}")
            continue
        fig, ax = plt.subplots(figsize=ONE_COL)
        ai = np.logspace(-2, 2, 200)
        ax.plot(ai, np.minimum(sp, mem * ai), color=INK, lw=1.5, label="SP roof (measured)")
        if not pd.isna(dp):
            ax.plot(ai, np.minimum(dp, mem * ai), color=INK2, lw=1, ls="--", label="DP roof (measured)")
        for mode, marker in [("simultaneous", "o"), ("separate_passes", "x")]:
            selected = [p for p in points if p["node"] == node and p["counter_mode"] == mode]
            if selected:
                x = [p["approximate_SP_FLOP_per_byte"] for p in selected]
                y = [p["SP_GFLOPs"] for p in selected]
                ax.scatter(x, y, color=SERIES[1], s=20, zorder=3, marker=marker,
                           label="whole-process " + mode.replace("_", " "))
                for point, xi, yi in zip(selected, x, y):
                    ax.annotate(f"{point['threads']}t", (xi, yi), xytext=(3, -8), textcoords="offset points",
                                fontsize=6, color=INK2)
        ax.set(xscale="log", yscale="log", xlabel="approx. whole-process SP FLOP / DRAM byte",
               ylabel="GFLOP/s", title=f"{node}: roofline")
        ax.legend(loc="upper left")
        save(fig, f"roofline_{node}")


if __name__ == "__main__":
    lk, gr, pf = load("likwid.csv"), load("grid.csv"), load("perfctr.csv")
    if lk is None:
        lk = pd.DataFrame(columns=["node", "mode", "job", "kernel", "placement",
                                   "threads", "MBps", "MFlops"])
    likwid_plots(lk)
    grid_plots(gr)
    roofline(lk, pf)
