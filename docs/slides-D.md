# Part D presentation content

Team: **UCLuster Too**\
Users: **dc-loke1, dc-ge2, dc-huan6, dc-ta1**\
Evidence date: 23 October 2026\
Overnight campaign: `20261022T224854Z`

These three slides cover D's contribution. Keep A's compiler/affinity tuning results in A's section. All rates below are decimal GFLOP/s or GB/s. Thread counts refer to OpenMP threads in one MPI rank on one node. The overnight baseline uses physical cores, reaching 32 threads on DINE and 64 on DINE2.

## Slide D1: Strong scaling at fixed lattice size

### On-slide content

**FP32 domain-wall Dslash, fixed L and fixed Ls = 12**

| Node | L | 1-thread GFLOP/s | Full-node GFLOP/s | Speedup | Efficiency |
|---|---:|---:|---:|---:|---:|
| DINE, 32 threads | 24 | 21.598 | 352.596 | 16.325× | 51.0% |
| DINE, 32 threads | 32 | 20.384 | 350.573 | 17.198× | 53.7% |
| DINE2, 64 threads | 24 | 35.217 | 768.923 | 21.834× | 34.1% |
| DINE2, 64 threads | 32 | 32.462 | 695.397 | 21.422× | 33.5% |

- One consistent overnight build and placement policy per node.
- Three repetitions per scaling point. Present medians with the observed spread.
- DINE2 gives higher throughput, while its efficiency relative to one thread is lower at full node.

**Figure:** strong-scaling panels in `report/figs/submission_scaling.pdf`.

### Speaker notes, approximately 45 seconds

“For strong scaling, we keep the lattice fixed and increase the number of physical cores. At L32, DINE reaches about 351 GFLOP/s, or 17.2 times its one-thread throughput. DINE2 reaches about 695 GFLOP/s, or 21.4 times its one-thread throughput. DINE2 has twice as many physical cores, so its absolute throughput is higher but its full-node parallel efficiency is lower. These curves use the same build and placement within each node's series. The GFLOP/s values measure the DWF kernel, so we calculate speedup from those rates rather than from the duration of the whole Slurm job.”

**Method:** `speedup(T) = P(T) / P(1)` and `efficiency(T) = speedup(T) / T`, using the same lattice, kernel, precision, build and policy. If a different baseline T0 is used, efficiency is `P(T) / P(T0) × T0 / T` and T0 must appear in the caption. A benchmark harness may vary iteration counts, so elapsed job time cannot substitute for fixed-work kernel time.

## Slide D2: Exact weak-scaling pairs

### On-slide content

**Constant lattice volume per thread, with Ls = 12 fixed**

| Node | Smaller case | Larger case | L^4 per thread | Throughput per thread retained |
|---|---|---|---:|---:|
| DINE | L24, 2 threads | L48, 32 threads | 165,888 | 56.4% |
| DINE2 | L24, 2 threads | L48, 32 threads | 165,888 | 32.1% |

- Doubling each of four lattice dimensions increases work 16×. Threads also increase 16×.
- Retention = `[P_large / T_large] / [P_small / T_small]`. Ideal retention is 100%.
- These pairs match the workload and thread counts across nodes. DINE2's separate 4-to-64-thread test retains 31.4% at 82,944 sites/thread.

**Figure:** weak-scaling panels in `report/figs/submission_scaling.pdf`.

### Speaker notes, approximately 40 seconds

“Weak scaling asks whether each thread can maintain its throughput when the total problem grows. Here the lattice doubles from 24 to 48 in every dimension, so its volume grows by sixteen. We increase the thread count from two to thirty-two on both nodes. DINE retains 56.4 percent of its throughput per thread, and DINE2 retains 32.1 percent. These pairs have the same work per thread and the same thread counts across machines. DINE2's additional four-to-sixty-four-thread test gives 31.4 percent. All these experiments run inside one node, where more threads still share finite socket memory bandwidth. The larger lattice can also change cache reuse.”

**Scope:** this is weak scaling across cores within one node. It does not measure multi-node MPI scaling. A fixed-thread lattice-size sweep is a separate experiment. Smaller exact pairs, such as L12 at T1 and L24 at T16, can be supplementary but may cross cache regimes and should not replace the larger-workload result.

## Slide D3: Counter evidence and the empirical roofline

### On-slide content

**Whole-process counter measurements**

| Node and threads | SP compute rate | DRAM rate | SP FLOP / DRAM byte |
|---|---:|---:|---:|
| DINE, 32 | 259.329 GFLOP/s | 164.734 GB/s | 1.574 |
| DINE2, 64 | 505.858 GFLOP/s | 243.573 GB/s | 2.077 |

- Full-node rows collect SP and DRAM counters simultaneously.
- Lower-thread rows use separate passes, with workload and runtime consistency checks.
- Roofs use measured LIKWID **SP** compute and memory bandwidth ceilings.
- Counter scope includes setup, several lattice sizes and multiple kernels. Label points **whole process**.

**Figure:** `report/figs/submission_roofline.pdf`.

### Speaker notes, approximately 45 seconds

“The hardware counters provide a second view of the benchmark. At full node, we measure both SP operations and DRAM traffic in the same execution. DINE averages 259 GFLOP/s over the whole process and DINE2 averages 506. Those values differ from the DWF kernel rates because the counters also cover initialization and the other benchmark phases. We divide these process-wide rates to place aggregate points on an empirical single-precision roofline. This supports an overall comparison with the measured compute and bandwidth ceilings. It does not give an isolated DWF arithmetic intensity, so we do not attach these coordinates to an individual L24 or L32 kernel.”

**Method:** `P_roof(I) = min(P_SP_ceiling, B_DRAM_ceiling × I)`. Use matching units and precision. Keep measured ceilings separate from base-clock and maximum-turbo theoretical bounds. A ratio assembled from different counter executions is approximate even when runtimes are close. A whole-process point cannot by itself prove the bottleneck of one kernel.

### Supporting comparison: Grid AXPY versus LIKWID

Use this small table in the roofline slide's notes or as an optional appendix slide if the team has space.

| Full physical-core node | Grid AXPY at L64 | LIKWID temporal triad | Ratio |
|---|---:|---:|---:|
| DINE | 174.383 GB/s | 178.608 GB/s | 97.6% |
| DINE2 | 350.429 GB/s | 393.154 GB/s | 89.1% |

These are medians of three repetitions. L64 corresponds to 3,072 MiB in the Grid memory benchmark, avoiding the obviously cache-sized comparisons. The rates use decimal GB/s and a useful-byte convention. This comparison addresses the memory benchmark directly. It does not replace measured DRAM-traffic counters, which include physical memory transactions such as write allocation according to the selected kernel and counter definition.

Short explanation: “The large Grid AXPY case achieves about 98 percent of the temporal triad rate on DINE and 89 percent on DINE2. The benchmark's small-lattice bandwidths can exceed a DRAM ceiling because caches serve much of their traffic. We compare the large case and keep useful-byte bandwidth separate from hardware-measured DRAM traffic.”

## Link to A's tuning section

The overnight campaign and A's tuning campaign use different compiler/MPI/runtime settings. Treat them as distinct experiment families. Configuration labels such as `cpu-avx2` are not sufficient evidence of identical builds.

| A's best median FP32 DWF4 result at L ≥ 24 | Configuration | Three-run range |
|---|---|---|
| DINE: **361.403 GFLOP/s** | GCC AVX2, L48, 32 threads, close/cores, default NUMA | 350.137–362.715 GFLOP/s |
| DINE2: **864.215 GFLOP/s** | GCC AVX-512, L24, 128 SMT threads on 64 physical cores, socket-ordered affinity | 863.567–880.442 GFLOP/s |

Useful transition: “Our scaling study fixes the software and placement within each series. A's separate tuning study changes those choices and reports the best repeatable configuration.”

At fixed L24 in A's socket-ordered DINE2 runs, increasing from 64 threads to 128 SMT threads raises the median from 794.524 to 864.215 GFLOP/s, approximately 8.8%. Host variation still contributes to uncertainty. Avoid dividing A's winning result by an overnight one-thread baseline to create a new scaling efficiency.

## Viva questions and short answers

**Why does DINE2 have lower parallel efficiency despite higher throughput?**\
Efficiency divides speedup by the number of threads. DINE2 has twice as many physical cores and a faster one-thread baseline. Shared bandwidth, synchronization and placement can prevent throughput growing in direct proportion to core count. The curves demonstrate sublinear scaling. They do not uniquely isolate the cause.

**Why does weak scaling lose efficiency if work per thread stays constant?**\
Threads within a node share memory controllers and cache resources. Increasing threads does not create proportional DRAM bandwidth. A larger lattice can also reduce cache reuse. Exact work-per-thread matching controls workload size per thread, not those hardware effects.

**Did you measure MPI scaling?**\
The submitted scaling series uses one MPI rank with OpenMP threads inside one node. It measures shared-memory scaling. Multi-node or hybrid MPI experiments would answer another question and are not implied by these results.

**Are the 259 and 506 GFLOP/s counter values the same metric as the best DWF result?**\
No. They average SP operations across the entire instrumented execution. `Gflops_dwf4` times a specific kernel. Both are useful, but their scopes differ.

**Why use an SP roof instead of the more familiar DP peak?**\
The required benchmark configuration disables FP64. A DP ceiling would use the wrong precision and distort the percentage of peak.

**Why not label every small lattice cache-resident?**\
Aggregate cache size alone does not prove that every live field fits in the relevant shared-cache domains. We describe small-lattice or cache-sensitive results unless we establish the full working set and its placement.

**Does DINE2 need another full LIKWID thread sweep before submission?**\
The brief asks for maximum compute and memory bandwidth. Valid full-node measurements can address those requirements. A corrected thread sweep would strengthen a saturation explanation, but its absence does not make another campaign mandatory. Excluded incorrectly pinned runs remain excluded.

**What makes the result reproducible?**\
Keep source JSON, raw counter logs, CPU placement, build flags and runtime provenance together. The report gives medians and experiment definitions, and the plotting pipeline rebuilds figures from identified evidence. A derived CSV alone does not verify that the original runtime configuration matched its labels.

## Source and delivery notes

- Overnight numerical analysis: campaign `20261022T224854Z`, especially `whole_process_estimates.csv`, the scaling summaries and per-run records. Preserve the imported directory structure and provenance.
- The supplied overnight archive contains derived analysis and figures, without the raw job directories. The calculations can be checked against its CSVs, but independent validation of the original run configurations requires the raw records retained on COSMA.
- Tuning: `analysis/data/tuning_summary.csv` plus the original `results/<node>/grid-tune-*/<job>/result.json` and metadata.
- Expected final report: `report/report.pdf`, with source `report/report.tex`.
- This file supplies content and speaker notes. It is not a rendered presentation deck. Integrate it into the team's existing presentation without duplicating A's setup or best-case slides.
