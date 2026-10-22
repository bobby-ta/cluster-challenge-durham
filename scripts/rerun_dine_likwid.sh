#!/bin/bash
# Fill the gaps left by the timed-out likwid jobs 12200761-64 on DINE. Only the missing data:
#   - bandwidth vs cores: nothing usable yet, so one short job per kernel (~12 min each)
#   - FLOP/s vs cores: old jobs cover 1-16 cores; add 24 and 32, plus 1 and 16 to check overlap
#   - sizes: already good enough, not rerun
# Run from anywhere: scripts/rerun_dine_likwid.sh
set -euo pipefail
S="$(dirname "$0")/submit.sh"

for k in load_avx copy_avx triad_avx triad_mem_avx; do
  KERNELS=$k "$S" dine likwid_bench -t 00:25:00 -- bw
done
THREADS="1 16 24 32" "$S" dine likwid_bench -t 00:20:00 -- flops
