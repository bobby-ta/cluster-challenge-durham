# Slides: A (setup, best-case tuning, time efficiency)

Team: TODO-team-name. Users: TODO ×4 (fill from `config/team.env`).

## Slide 1: Setup: two very different nodes
- DINE: 2× EPYC 7302 (Zen 2), 32 cores, 2 NUMA, L3 16 MiB per 2-core CCX, 512 GB DDR4.
  Peak 3.07 TFLOP/s SP, 409.6 GB/s.
- DINE2: 2× Xeon Gold 6430 (Sapphire Rapids), 64 cores, 2 NUMA, 60 MiB L3/socket, 2 TB DDR5.
  Peak 8.6 TFLOP/s SP at base (vendor upper bound), ≤563 GB/s.
- Same stack on both nodes: GCC 14.1, Open MPI 5.0.3 (1 rank), Grid e2d607f via grid-benchmark c7457a8, LIKWID 5.5.1.
  `-march=znver2` / `-march=sapphirerapids -mno-avx512fp16`.
- Pinning: OMP close/cores; DINE2 numbers sockets even/odd. One gotcha.
- Table: report Table 1 (hardware + peaks).

## Slide 2: Best-case Grid throughput
- Knobs tried: binding (close/spread), NUMA (first-touch/interleave), SMT, compiler (gcc/clang),
  Wilson kernel (`--dslash-unroll`, `--dslash-asm`), threads (full/half node), L ≤ 48.
- Best per node: TODO(A) GFLOP/s dwf4 SP (median of ≥3), config, % of SP peak.
- Why: memory-bound kernel. Knobs that move bytes (NUMA, L3 fit) matter; FLOP knobs barely matter. TODO confirm.
- Figure: bar chart of median dwf4 per tag per node with min/max whiskers (`tuning_summary.csv`).

## Slide 3: Time efficiency
- TODO(A) jobs, node-hours, % completed (`analysis/data/job_count.csv`).
- Arrays where the task id is the thread count, ≤ 1 h exclusive jobs, repeats as separate submissions
  (honest error bars), overnight queue kept topped up.
- Everything reproducible: `scripts/submit.sh`, and each run has `meta.txt` (git hash, modules, env),
  `build-flags.txt`, `ldd.txt`, `runlog.csv`.
- Lessons: SMT pinning invalidated early likwid runs (EXCLUDED_JOBS); smoke first, then campaign.
