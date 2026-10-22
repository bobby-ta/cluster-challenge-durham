#!/bin/bash
#SBATCH -J build
#SBATCH -A do022
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 00:58:00
# Compile Grid + Benchmark_Grid on a compute node (much faster than the login node's 8-job limit).
# Prepare each config on the login node first (internet):  PREPARE_ONLY=1 build/build_grid.sh <node> <config>
# Then:  scripts/submit.sh dine build -- dine:cpu-avx2 dine2:cpu-avx512 ...
# -march is explicit in every config, so DINE2 binaries can be compiled on a DINE node.
# The builds share the node's hardware threads; full logs go to $GRID_ENV_ROOT/logs.
EXPERIMENT="build"
source "$REPO/slurm/common.sh"

(( $# > 0 )) || { log_run fail "no <node>:<config> given"; exit 2; }
NJOBS=$(( $(nproc) / $# ))
record_meta "builds=$* njobs=$NJOBS"
mkdir -p "$GRID_ENV_ROOT/logs"

builds=("$@"); pids=()
for nc in "${builds[@]}"; do
  log="$GRID_ENV_ROOT/logs/build-${nc/:/-}-$run_id.log"
  "$REPO/build/build_grid.sh" "${nc%%:*}" "${nc#*:}" "$NJOBS" > "$log" 2>&1 &
  pids+=($!)
done
status=0
for i in "${!pids[@]}"; do
  nc=${builds[$i]}; log="$GRID_ENV_ROOT/logs/build-${nc/:/-}-$run_id.log"
  if wait "${pids[$i]}"; then
    log_run ok "$nc ${SECONDS}s"
  else
    status=1; log_run fail "$nc ${SECONDS}s"
  fi
  tail -n 40 "$log" > "$RUN_DIR/build-${nc/:/-}.tail.txt"
done
exit "$status"
