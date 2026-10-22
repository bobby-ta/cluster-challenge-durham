#!/usr/bin/env python3
"""Make every report figure from analysis/data/*.csv (run collect.py first).

    python3 analysis/plots.py            # -> report/figs/*.pdf (vector, for LaTeX) + .png

Medians over repeats are plotted; min-max as a band so the variance is visible.
"""
from pathlib import Path

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
    """Fixed compute runs plus the specifically validated legacy DINE AVX runs."""
    compute = d.kernel.str.startswith("peakflops", na=False)
    # DINE's even compact AVX rows matched the fixed run after converting SMT
    # threads to physical cores. This comparison does not establish reuse on DINE2.
    old = d[(d.node == "dine") & d.job.astype(str).isin(["12200761", "12200762", "12200763"])
            & (d["mode"] == "threads") & compute & d.kernel.str.contains("avx", na=False)
            & (d.placement == "compact") & (d.threads % 2 == 0)].assign(threads=lambda x: x.threads // 2)
    fixed = d[(d["mode"] == "flops") & compute & (d.placement == "compact")]
    return pd.concat([old, fixed]).assign(GFlops=lambda x: x.MFlops / 1e3)


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
            for ax, pl in zip(axes, ["single", "all"]):
                for i, (k, g) in enumerate(s[s.placement == pl].groupby("kernel")):
                    band(ax, g, "kB", "GBps", SERIES[i], k)
                ax.set(xscale="log", yscale="log", xlabel="working set per thread [kB]",
                       ylabel="GB/s", title=f"{node}: {'1 thread' if pl == 'single' else 'all cores'}")
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


def grid_plots(df):
    # The challenge disables FP64. Never mix FP32 and FP64 values in one curve.
    if "precision" in df.columns:
        df = df[df.precision.str.upper() == "FP32"]
    df = df[df.experiment == "grid"]  # untagged only; tuning runs have TAG
    if df.empty:
        print("grid plots: no default FP32 runs yet")
        return
    metric = "Gflops_dwf4" if "Gflops_dwf4" in df else [c for c in df if c.startswith("Gflops_")][0]
    for node, d in df.groupby("node"):
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 2.4))
        for i, (L, g) in enumerate(d[d.L.isin([16, 24, 32, 48])].groupby("L")):
            band(a1, g, "threads", metric, SERIES[i], f"L={L}")
            s = g.groupby("threads")[metric].median()
            if len(s):
                baseline = min(s.index)
                eff = s / (s[baseline] * (s.index / baseline))
                a2.plot(eff.index, eff.values, marker="o", color=SERIES[i], label=f"L={L}")
        a1.set(xlabel="OpenMP threads", ylabel="GFLOP/s", title=f"{node}: {metric} strong scaling")
        a2.set(xlabel="OpenMP threads", ylabel="relative efficiency", ylim=(0, 1.1),
               title=f"{node}: vs smallest measured thread count")
        a1.legend(); a2.legend()
        save(fig, f"grid_scaling_{node}")

        # Weak scaling requires increasing the problem and threads together.
        # L=24 at T and L=32 at approximately 3.16*T have similar sites/core.
        pairs = weak_pairs(d, metric)
        if pairs:
            fig, ax = plt.subplots(figsize=ONE_COL)
            labels = [f"{t1} to {t2}" for t1, t2, _, _ in pairs]
            ax.bar(range(len(pairs)), [p[2] for p in pairs], color=SERIES[0], width=0.7)
            ax.axhline(1.0, color=INK2, ls="--", lw=1)
            ax.set(xticks=list(range(len(pairs))), xticklabels=labels,
                   xlabel="threads: L=24 to L=32 (sites/core within 10%)",
                   ylabel="per-core GFLOP/s ratio", title=f"{node}: approximate weak scaling")
            save(fig, f"grid_weak_scaling_{node}")

    # GFLOP/s vs L at fixed full-node threads: problem-size and cache sensitivity.
    fig, ax = plt.subplots(figsize=ONE_COL)
    for i, (node, d) in enumerate(df.groupby("node")):
        best = d[d.threads == d.threads.max()]
        band(ax, best, "L", metric, SERIES[i], f"{node} ({best.threads.max()} thr)")
    ax.set(xlabel="local lattice L (volume L^4)", ylabel="GFLOP/s", title=f"{metric} vs problem size")
    ax.legend()
    save(fig, "grid_vs_L")


def roofline(lk, perf):
    """Ceilings from likwid-bench measurements, Grid's points from likwid-perfctr."""
    import numpy as np
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
        if perf is not None:
            p = perf[perf.node == node].pivot_table(index="threads", columns="metric", values="value")
            fl = [c for c in p if "MFLOP/s" in c and "SP" in c]
            bw = [c for c in p if c.startswith("Memory bandwidth")]
            if fl and bw:
                x, y = p[fl[0]] / p[bw[0]], p[fl[0]] / 1e3
                ax.scatter(x, y, color=SERIES[1], s=20, zorder=3, label="Grid (perfctr)")
                for th, xi, yi in zip(p.index, x, y):
                    ax.annotate(f"{th}t", (xi, yi), xytext=(3, -8), textcoords="offset points",
                                fontsize=6, color=INK2)
        ax.set(xscale="log", yscale="log", xlabel="arithmetic intensity [FLOP/byte]",
               ylabel="GFLOP/s", title=f"{node}: roofline")
        ax.legend(loc="upper left")
        save(fig, f"roofline_{node}")


if __name__ == "__main__":
    lk, gr, pf = load("likwid.csv"), load("grid.csv"), load("perfctr.csv")
    if lk is None:
        lk = pd.DataFrame(columns=["node", "mode", "job", "kernel", "placement",
                                   "threads", "MBps", "MFlops"])
    likwid_plots(lk)
    if gr is not None:
        grid_plots(gr)
    roofline(lk, pf)
