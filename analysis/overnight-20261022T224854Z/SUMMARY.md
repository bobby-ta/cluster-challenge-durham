# Overnight campaign 20261022T224854Z

## Completion

Planned task entries: 91; submitted Slurm job/array IDs: 24.

Recorded invocations: 97. failed: 2, ok: 95

A task without a record may still be pending or may have failed before writing its record. Consult squeue/sacct and the controller log for scheduler completion.

Only complete, successful JSON with positive FP32 DWF results for every required lattice size enters the numerical summaries.

## dine

| L | Threads | Median GFLOP/s | Repeats | Speedup | Efficiency |
|---:|---:|---:|---:|---:|---:|
| 24 | 1 | 21.598 | 3 | 1.000 | 100.0% |
| 24 | 2 | 39.316 | 3 | 1.820 | 91.0% |
| 24 | 4 | 64.952 | 3 | 3.007 | 75.2% |
| 24 | 8 | 124.353 | 3 | 5.757 | 72.0% |
| 24 | 16 | 215.086 | 3 | 9.958 | 62.2% |
| 24 | 24 | 310.293 | 3 | 14.366 | 59.9% |
| 24 | 32 | 352.596 | 3 | 16.325 | 51.0% |
| 32 | 1 | 20.384 | 3 | 1.000 | 100.0% |
| 32 | 2 | 35.351 | 3 | 1.734 | 86.7% |
| 32 | 4 | 52.454 | 3 | 2.573 | 64.3% |
| 32 | 8 | 111.946 | 3 | 5.492 | 68.6% |
| 32 | 16 | 208.492 | 3 | 10.228 | 63.9% |
| 32 | 24 | 274.240 | 3 | 13.453 | 56.1% |
| 32 | 32 | 350.573 | 3 | 17.198 | 53.7% |

Baseline thread counts: [1]. See strong_scaling.csv for configuration and placement.

Best median L24/L32 DWF comparison point: **358.857 GFLOP/s** at 32 threads, compact, NUMA default, cpu-avx2 (mode extended, 3 successful repeats; range 348.191–359.523).

Highest median individual-lattice DWF throughput: **761.696 GFLOP/s** at L=12, 32 threads, compact, NUMA default, cpu-avx2 (3 repeats). See best_lattice_configurations.csv for all tested configurations.

Weak scaling (exact): L16/1 threads → L32/16 threads retains 60.6% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L16/2 threads → L32/32 threads retains 57.5% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L24/1 threads → L48/16 threads retains 53.0% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L24/2 threads → L48/32 threads retains 56.4% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (approximate): L24/8 threads → L32/24 threads retains 73.5% of per-thread DWF throughput; sites/thread change +5.35%.

Measured DRAM_non-temporal ceiling: 230.589 GB/s (triad_mem_avx, median of 3 full-node measurements).
Measured DRAM_temporal ceiling: 178.608 GB/s (triad_avx, median of 3 full-node measurements).
Measured FP32_compute ceiling: 3341.109 GFLOP/s (peakflops_sp_avx_fma, median of 3 full-node measurements).

## dine2

| L | Threads | Median GFLOP/s | Repeats | Speedup | Efficiency |
|---:|---:|---:|---:|---:|---:|
| 24 | 1 | 35.217 | 3 | 1.000 | 100.0% |
| 24 | 2 | 64.465 | 3 | 1.831 | 91.5% |
| 24 | 4 | 121.772 | 3 | 3.458 | 86.4% |
| 24 | 8 | 206.163 | 3 | 5.854 | 73.2% |
| 24 | 16 | 287.583 | 3 | 8.166 | 51.0% |
| 24 | 24 | 409.625 | 3 | 11.631 | 48.5% |
| 24 | 32 | 388.874 | 3 | 11.042 | 34.5% |
| 24 | 48 | 579.696 | 3 | 16.461 | 34.3% |
| 24 | 64 | 768.923 | 3 | 21.834 | 34.1% |
| 32 | 1 | 32.462 | 3 | 1.000 | 100.0% |
| 32 | 2 | 61.845 | 3 | 1.905 | 95.3% |
| 32 | 4 | 116.494 | 3 | 3.589 | 89.7% |
| 32 | 8 | 206.463 | 3 | 6.360 | 79.5% |
| 32 | 16 | 332.680 | 3 | 10.248 | 64.1% |
| 32 | 24 | 347.635 | 3 | 10.709 | 44.6% |
| 32 | 32 | 427.618 | 3 | 13.173 | 41.2% |
| 32 | 48 | 556.435 | 3 | 17.141 | 35.7% |
| 32 | 64 | 695.397 | 3 | 21.422 | 33.5% |

Baseline thread counts: [1]. See strong_scaling.csv for configuration and placement.

Best median L24/L32 DWF comparison point: **740.009 GFLOP/s** at 64 threads, compact, NUMA default, cpu-avx512 (mode extended, 3 successful repeats; range 728.467–740.652).

Highest median individual-lattice DWF throughput: **2355.408 GFLOP/s** at L=12, 64 threads, compact, NUMA interleave, cpu-avx512 (3 repeats). See best_lattice_configurations.csv for all tested configurations.

Weak scaling (exact): L16/1 threads → L32/16 threads retains 52.3% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L16/2 threads → L32/32 threads retains 33.8% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L16/4 threads → L32/64 threads retains 24.4% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L24/1 threads → L48/16 threads retains 45.6% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L24/2 threads → L48/32 threads retains 32.1% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (exact): L24/4 threads → L48/64 threads retains 31.4% of per-thread DWF throughput; sites/thread change +0.00%.
Weak scaling (approximate): L24/8 threads → L32/24 threads retains 56.2% of per-thread DWF throughput; sites/thread change +5.35%.
Weak scaling (approximate): L24/16 threads → L32/48 threads retains 64.5% of per-thread DWF throughput; sites/thread change +5.35%.

Measured DRAM_non-temporal ceiling: 397.917 GB/s (triad_mem_avx, median of 3 full-node measurements).
Measured DRAM_temporal ceiling: 393.154 GB/s (triad_avx, median of 3 full-node measurements).
Measured FP32_compute ceiling: 9287.286 GFLOP/s (peakflops_sp_avx512_fma, median of 3 full-node measurements).

## Interpretation and limits

- Strong scaling compares a fixed lattice, build and placement. Efficiency uses the smallest successful thread count in that series; a missing one-thread run is not replaced by an invented result.
- Exact weak pairs keep L^4/threads constant (the benchmark fixes the fifth dimension). Cache capacity per thread and socket placement still change, particularly for L16.
- Grid axpy GBps is binary GiB/s in the pinned benchmark. grid_axpy.csv converts it to decimal GB/s. Axpy is FP64 even though the Dirac FLOP benchmarks are FP32.
- The measured roofs keep temporal and non-temporal store kernels separate. Temporal-kernel useful-byte bandwidth excludes possible write-allocate traffic, whereas MEM counters measure controller traffic. Interpret the temporal line as a kernel-specific guide; the non-temporal ceiling is the closer byte-count match for counter-derived points. A roof is empirical, not a hardware specification.
- A successful MEM_SP run supplies simultaneous whole-process SP and DRAM measurements, preferred over separate passes at the same configuration. Other points use separate MEM and FLOPS_SP passes and are approximate; pairs with unavailable timing or more than 20% timing disagreement are excluded from the figure. Setup, multiple sizes and other kernels contribute to both methods. Neither supplies per-lattice DWF arithmetic intensity; FP64 axpy traffic also enters the total DRAM byte count.
- The benchmark itself selects its best implementation for each kernel and lattice; reported repeats are repetitions of that benchmark selection.
- A failed optional counter does not invalidate independent, completed scaling runs. See runs.csv and each raw directory for failures.

Figures: /cosma/home/do022/dc-huan6/durham_overnight_20261022/cluster-challenge-durham-main/report/figs/overnight-20261022T224854Z
