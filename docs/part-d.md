# Part D — completed Grid scaling and roofline contribution

Campaign `20261022T224854Z` on COSMA for **UCLuster Too** (users `dc-loke1`,
`dc-ge2`, `dc-huan6`, `dc-ta1`). This replaces the obsolete guide which said no
Grid results existed. All calculations use the imported and validated exports
at `analysis/overnight-20261022T224854Z/`; the teammate GCC results stay
independent from this Clang/OpenMPI4.1 run.

## Regenerate all four submission figures

From the repository root on any machine with Python 3 and Matplotlib:

```bash
python3 analysis/plot_overnight_exports.py
python3 -m unittest discover -s analysis -p 'test_*.py'
```

Files will be written to `report/figs/overnight-20261022T224854Z/` as
`submission_strong_scaling.pdf`, `submission_weak_scaling.pdf`,
`submission_roofline.pdf`, and `submission_axpy_vs_likwid.pdf`. The original
campaign CSVs and source figures are preserved. The generator checks three
repetitions per scaling point, numerical speedup identity, exact weak pairs,
counter eligibility, and the decimal bandwidth unit conversion.

## Strong scaling

Hold `L`, node, Clang build, NUMA policy, compact physical-core placement and
MPI rank count fixed. Use one MPI rank, one OpenMP thread per physical core,
explicit socket/core-ordered affinity; three independent jobs per point. The
benchmarked Grid FP32 `Gflops_dwf4` DWF implementation keeps `Ls=12` fixed.
With baseline T0=1 and throughput P(T), speedup=P(T)/P(1) and
efficiency=P(T)/(T*P(1)). For other baselines, efficiency= speedup*T0/T.

| Node | L | 1-thread GF/s | Full-node GF/s | Speedup | Efficiency |
|---|---:|---:|---:|---:|---:|
| DINE, 32 physical cores | 24 | 21.598 | 352.596 | 16.325 | 51.0% |
| DINE, 32 physical cores | 32 | 20.384 | 350.573 | 17.198 | 53.7% |
| DINE2, 64 physical cores | 24 | 35.217 | 768.923 | 21.834 | 34.1% |
| DINE2, 64 physical cores | 32 | 32.462 | 695.397 | 21.422 | 33.5% |

Full-node throughput is greater on DINE2, though its linear-scaling efficiency
is lower. There is no uniform saturation core count; DINE2 at L24 even fell
from 409.625 GF/s at 24 threads to 388.874 at 32, then rose again.

## Weak scaling

The exact `L24/2T → L48/32T` comparison increases `L^4` and physical threads
by 16×, preserving sites per thread. Per-thread throughput retention is
**56.4% DINE** and **32.1% DINE2**. The separate full-node DINE2 exact pair
`L24/4T → L48/64T` retains 31.4%; its baseline is different so it is not the
matched cross-node comparison. The approximate `L24/8T → L32/24T` changes
sites/thread by +5.35% and must be labelled approximate if shown.

## Empirical ceilings and whole-process counters

| Node | Measured FP32 GF/s | Non-temporal DRAM GB/s | Temporal DRAM GB/s | NT ridge flop/byte |
|---|---:|---:|---:|---:|
| DINE | 3341.109 | 230.589 | 178.608 | 14.49 |
| DINE2 | 9287.286 | 397.917 | 393.154 | 23.34 |

The preferred simultaneous full-node `MEM_SP` counter pairs yield aggregate
**259.329 GF/s, 164.734 GB/s, 1.574 flop/byte** on DINE and **505.858
GF/s, 243.573 GB/s, 2.077 flop/byte** on DINE2. One-thread/eight-thread
points combine separate MEM and FLOPS_SP passes; their runtime disagreement is
at most 3.5% but they remain approximate.

These ratios include setup, multiple lattice sizes and non-DWF kernels,
including FP64 axpy traffic. They are **not per-lattice DWF operational
intensities**. Comparing them with the empirical non-temporal roof puts the
whole-process aggregate on the memory-side of the roofline; it does not prove
that every individual DWF kernel is DRAM-bound. Do not combine the
259/506 GF/s whole-process numbers with 350/695 GF/s DWF-only performance to
form artificial arithmetic intensities.

## FP64 axpy versus LIKWID useful-byte bandwidth

For L64 (3072 MiB working set), Grid axpy's median decimal bandwidth is
**174.383 GB/s** on DINE and **350.429 GB/s** on DINE2, at 32 and 64
physical cores. The separately measured temporal LIKWID triad yields 178.608
and 393.154 GB/s. Grid reaches **97.6% / 89.1%** of those independent
kernel useful-byte rates; the ratio is not hardware efficiency. Grid reports
binary GiB/s and `grid_axpy.csv` converts by `2^30/10^9`. Small lattice
axpy rates are partly cache-served and cannot be called DRAM bandwidth.

## Build provenance and remaining tasks

- The teammate's A-side tuning uses GCC14/OpenMPI5; this overnight campaign
  uses Clang20/OpenMPI4.1, `--enable-unified=no`, recovered `--device-mem
  32768` MiB, physical socket/core ordered `OMP_PLACES`, and LIKWID count-only
  `-c`. Never group these by only the reused labels `cpu-avx2`/`cpu-avx512`.
- The teammate's separately verified eligible best medians are 361.403
  GF/s on DINE (L48, GCC, 32T), 864.215 on DINE2 (L24, GCC, 128 SMT
  threads, socket ordered). Preserve these A results, explicitly separate
  from the overnight scaling campaign.
- `runs.csv`: 97 unique recorded invocations, 95 successful, two historical
  original smoke failures; both smokes were successfully replaced. Figures
  use validated successful exports. The subsequent raw-results ZIP supplies
  all 97 matching records, benchmark outputs, build flags and runtime logs.
  Run `python3 analysis/check_overnight_raw.py` to check coverage; see
  `docs/overnight-raw-audit-20261023.md`. Campaign-level Slurm accounting and
  the final four-user resource totals still need to be collected separately.
- The latest brief requires maximum bandwidth and compute on both nodes but
  does not mandate a DINE2 LIKWID 1-to-64-core saturation sweep. That
  optional deeper study should not delay integration of valid D data.
- DINE2 legacy LIKWID jobs 12203200–12203202 are excluded for SMT pinning.
  DINE's legacy all-core cache plot also contains an excluded half-node SMT
  dataset (`12200764`) and needs replacement or removal.

For slides, see `docs/slides-D.md`. For team submission checks, see
`docs/submission-review.md`.

## Optional DINE2 socket-placement contribution

The supplied `partD_socket_patch_20261023.zip` adds a separate GCC AVX-512
close-versus-spread comparison, its PDF/PNG figure, and
`report/part-d-socket-insert.tex`. Keep this comparison separate from the
Clang/OpenMPI overnight curves and A's existing best-case results.

The figure and paragraph are imported artifacts. The ZIP and the repository
at integration time contain no raw `grid-final-one-socket` or
`grid-final-two-socket` jobs, so their numerical claims cannot yet be
independently reproduced from this checkout. The existing tracked `grid.csv`
also predates the collector's provenance fields. Regenerating that CSV alone
does not supply the missing jobs.

To reproduce the figure after importing the original job records:

```bash
python3 analysis/collect.py
python3 analysis/plot_dine2_socket.py
```

Import each job's `meta.txt`, `build-flags.txt`, `ldd.txt`, `result.json`,
and completion entry in `results/runlog.csv`. The plot requires three distinct
completed jobs per placement/thread setting, FP32 rows at L24/L32 and
24/32 threads, and matching host, build, runtime and workload metadata. It
rejects missing measurements or incompatible provenance. A separately
collected CSV can be supplied with `--data /path/to/grid.csv`; `--output`
selects the PDF path and also writes a PNG beside it. Paths default to this
repository regardless of the current working directory.

For the report, the fragment is compatible with the existing LaTeX preamble.
From `report/`, place `\input{part-d-socket-insert}` within the Grid section
only after reviewing the evidence and two-page space budget. The optional
figure uses `\includegraphics[width=\linewidth]{dine2_socket_placement.pdf}`
with the existing `\graphicspath{{figs/}}`. Neither is automatically inserted
into `report.tex`.

## Earlier local audit and legacy counter placement

The separate 22 October local audit of `ciuk_durham_evidence.zip` recorded
189 STREAM processes and 24 LIKWID processes, with no Benchmark_Grid output.
All raw processes recorded exit status 0, and every STREAM log reported
numerical validation. The CSV review flags were still `no`; those flags did
not indicate failed STREAM numerical checks. The LIKWID logs and saved
socket-domain ordering showed one thread per physical core across both
sockets. STREAM recorded thread counts without per-thread affinity, so its
placement remained unverified.

That archive's compute kernels (`peakflops_avx_fma` and
`peakflops_avx512_fma`) were FP64 and cannot supply Grid's FP32 ceiling.
Its measurements are separate from the overnight exports above. The earlier
audit also found a successful one-thread DINE2 FLOPS_DP counter smoke test
in recon job `12202855`, superseding the missing-module result from `12202559`.
That smoke test alone did not establish MEM or FLOPS_SP counter readiness.

The repository's legacy `slurm/grid.sbatch` still uses
`-C N:0-$((T-1))` for counters. On the audited nodes that LIKWID domain
ordering interleaves SMT siblings, so it does not select one thread per
physical core at T>1. Resolve and record placement before using new runs
from that launcher to explain baseline scaling. The overnight campaign used
its separately recorded physical-core placement and count-only `-c` mode.
