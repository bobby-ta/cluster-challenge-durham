# Part D — Grid performance and roofline

Owner: D. These steps use the same `results/`, `analysis/` and `report/figs/` workflow as the team plan.

## Current evidence (22 October)

- The repository contains DINE2 hardware recon (`results/dine2/recon/12202559/`), confirming **2 × Xeon Gold 6430**, 64 physical cores and 2 NUMA domains.
- That recon ran without LIKWID on `PATH`, so its counter smoke test is **inconclusive**. Re-run it with the working compiler and LIKWID modules before diagnosing counter permissions.
- The supplied repository snapshot contains **no Grid runs or Grid counter data**. All Grid performance, scaling and roofline results are still pending.
- `analysis/peaks.py` now includes DINE2 vendor *upper bounds* (2.1 GHz base, 3.4 GHz max turbo, eight channels at up to DDR5-4400). Installed DIMM speed and sustained all-core clocks still need confirmation; the advertised maximum is not a measurement.

## 1. Check one Grid run per node

Use the teammate's submission wrapper; **never benchmark on the login node**.

```bash
cd ~/ccd                 # adjust to where you cloned this repo on COSMA
scripts/submit.sh dine  grid --array=8
scripts/submit.sh dine2 grid --array=8
```

After completion, look for `result.json`, `grid.out`, `meta.txt`, `ldd.txt` and `build-flags.txt` under `results/<node>/grid/<jobid>_<threads>/`. A successful Grid job must have exit code 0, a complete JSON file and usable `Gflops_dwf4` results for both **L=24 and L=32**. `--max-L 32` measures both sizes in one run.

## 2. Strong scaling

Repeat each thread-count array three times, only after the smoke runs are good:

```bash
for r in 1 2 3; do
  scripts/submit.sh dine  grid --array=1,2,4,8,12,16,24,32
  scripts/submit.sh dine2 grid --array=1,2,4,8,12,16,24,32,48,64
done
```

Use FP32 `Gflops_dwf4` with the same build, lattice size and binding policy. For each L:

- Speedup at T cores = median GFLOP/s at T / median GFLOP/s at 1.
- Parallel efficiency = speedup / T. When the one-core run is missing, use the smallest available T as the declared baseline.
- Compare where scaling slows with B/C's bandwidth-versus-threads results. Note cache effects and NUMA placement as hypotheses unless measured.

## 3. Weak scaling

Increasing L without increasing the thread count is a **problem-size sweep**, not weak scaling. Compare pairs with nearly equal `L^4 / threads`. Examples:

- L=24, 8 threads: 41,472 sites/thread.
- L=32, 24 threads: 43,691 sites/thread (about 5.3% larger).

The plotted quantity is the ratio of **GFLOP/s per thread** at L=32 versus L=24. Ideal weak scaling would give approximately 1, subject to the roughly matched per-thread workload. The analysis pipeline automatically looks for pairs within 10% sites/thread, producing `grid_weak_scaling_<node>` when data exists.

## 4. Counters and the roofline

After the LIKWID smoke test works, collect a *separate* tagged experiment:

```bash
PERFCTR='MEM FLOPS_SP' TAG=perfctr scripts/submit.sh dine  grid --array=1,8,16,32
PERFCTR='MEM FLOPS_SP' TAG=perfctr scripts/submit.sh dine2 grid --array=1,8,16,64
```

These commands run Grid **twice**, once per LIKWID group, and cover the *whole benchmark* (initialisation, multiple lattice sizes, axpy, and Dirac kernels). MEM and FLOPS_SP counters are therefore from different executions. Treat a bandwidth/FLOP ratio assembled from them as an approximate whole-run operational intensity, **not an exact L=24 or L=32 Dirac-kernel measurement**. If counters remain unavailable, label any Grid roofline position based on assumed arithmetic intensity as an **estimate**.

The roofline must use a matching **single-precision** compute ceiling (`peakflops_sp_*`), because the required Grid flags disable FP64. FP64 LIKWID peak values cannot stand in for a Grid FP32 ceiling. Use the corresponding measured memory-bandwidth ceiling and record whether temporal or non-temporal stores were used.

Grid's `axpy` result is under `grid_axpy.csv`, while `Gflops_dwf4` is under `grid.csv`. Distinguish the two kernels when comparing memory bandwidth against LIKWID; the Wilson arithmetic-intensity estimate from the plan must not be silently assigned to domain-wall.

## 5. Collect results and make report figures

```bash
python3 analysis/collect.py
(cd analysis && python3 plots.py)
python3 -m unittest discover -s analysis -p 'test_*.py'
```

Expected outputs when the matching raw runs exist:

- `analysis/data/grid.csv`: per-L FP32/FP64 results, threads, source file, compiler config and binding.
- `analysis/data/grid_axpy.csv`: Grid memory benchmark observations.
- `analysis/data/perfctr.csv`: recorded counter metrics, with their group names.
- `report/figs/grid_scaling_<node>.{pdf,png}`: strong scaling and relative efficiency.
- `report/figs/grid_weak_scaling_<node>.{pdf,png}`: approximately matched weak-scaling pairs.
- `report/figs/grid_vs_L.{pdf,png}`: problem-size sensitivity at the largest available thread count.
- `report/figs/roofline_<node>.{pdf,png}`: measured ceilings and any available process-wide counter estimates.

The graph generator only plots untagged `grid` runs, so compiler tuning and perfctr passes do not contaminate the baseline. Source results remain unchanged. `collect.py` removes stale generated CSVs when their raw sources are absent.

## 6. Write sections 3 and 4

Keep the final report within the two-page limit. Each numerical statement needs a matching raw run or figure. Include:

1. Grid's median FP32 throughput for L=24 and L=32 on each node at one core and full node; speedup and efficiency.
2. Where throughput saturates and whether the bandwidth knee in B/C's LIKWID experiments occurs at similar thread counts.
3. A weak-scaling comparison from matched `L^4 / threads` pairs, with the mismatch acknowledged.
4. Grid's measured/estimated position relative to the **FP32** roofline, plus its axpy-versus-LIKWID memory bandwidth comparison.
5. The fastest Grid result, with exact build, binding, NUMA, thread count and lattice size. Keep tuned runs separate from the default scaling series.

Leave fields blank when a measurement is missing. The current ZIP is a work in progress, and the report should not contain a numerical Grid conclusion until those jobs exist.
