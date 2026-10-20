#!/bin/bash
# The core campaign for one node type, queued in one go (run once the recon and build look OK).
#   scripts/campaign.sh <dine|dine2> [repeats]
# Repeats are separate jobs on purpose: they land at different times/nodes, which gives
# honest error bars.
set -euo pipefail
S="$(dirname "$0")/submit.sh"; NODE=${1:?}; R=${2:-3}
NC=${NCORES:-32}   # physical cores (from recon); thread list below assumes 32, adjust for DINE2
THREADS=1,2,4,6,8,12,16,20,24,28,32

for r in $(seq "$R"); do
  "$S" "$NODE" likwid_bench -- threads
  "$S" "$NODE" grid --array=$THREADS
done
"$S" "$NODE" likwid_bench -- sizes
PERFCTR="MEM FLOPS_SP" TAG=perfctr "$S" "$NODE" grid --array=1,8,16,$NC
