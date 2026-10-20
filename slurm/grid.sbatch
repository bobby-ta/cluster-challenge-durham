#!/bin/bash
#SBATCH -J grid
#SBATCH -A do022
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 00:58:00
# One Benchmark_Grid run with a given OpenMP thread count.
# Submit as an array where the task id IS the thread count:
#   scripts/submit.sh dine grid --array=1,2,4,8,16,24,32
# Knobs (env, passed through by sbatch --export=ALL):
#   MAX_L        (default 32; one run covers every L up to MAX_L, including 24 and 32)
#   OMP_PROC_BIND / OMP_PLACES (default close / cores)
#   GRID_CONFIG  (overrides config/<node>.env, e.g. a clang build)
#   PERFCTR      (e.g. "MEM FLOPS_SP": wrap the run in likwid-perfctr with these groups, one run each)
#   TIMELINE     (1 = sample counters every 1 s instead of whole-run totals)
#   NUMACTL      (e.g. "--interleave=all")
#   GRID_EXTRA   (extra Grid flags, e.g. "--shm 2048")
#   TAG          (free-text label stored in the experiment name, e.g. "clang", "interleave")
EXPERIMENT="grid${TAG:+-$TAG}"
source "$REPO/slurm/common.sh"

T=${SLURM_ARRAY_TASK_ID:-${THREADS:?set THREADS or use an array}}
MAX_L=${MAX_L:-32}
export OMP_NUM_THREADS=$T
export OMP_PROC_BIND=${OMP_PROC_BIND:-close}
export OMP_PLACES=${OMP_PLACES:-cores}
BIN=$(find "$GRID_ENV_ROOT/$NODE_TAG/prefix/gridbench_$GRID_CONFIG" -name Benchmark_Grid -type f -perm -u+x 2>/dev/null | head -1)
[[ -n $BIN ]] || { log_run fail "no Benchmark_Grid for $NODE_TAG/$GRID_CONFIG"; exit 1; }

record_meta "T=$T MAX_L=$MAX_L PERFCTR=${PERFCTR:-} NUMACTL=${NUMACTL:-} GRID_EXTRA=${GRID_EXTRA:-}"
cd "$RUN_DIR"
ldd "$BIN" > ldd.txt
cat "$GRID_ENV_ROOT/$NODE_TAG/build-flags-$GRID_CONFIG.txt" > build-flags.txt 2>/dev/null || true

ARGS=(--no-benchmark-flops-fp64 --no-benchmark-flops-sp4-2as --no-benchmark-flops-sp4-f
      --no-benchmark-flops-su4 --mpi 1.1.1.1 --max-L "$MAX_L" ${GRID_EXTRA:-})
PRE=(); [[ -n ${NUMACTL:-} ]] && PRE=(numactl $NUMACTL)
# Leave 3 min for bookkeeping; a killed run still leaves its stdout behind.
LIMIT=55m

if [[ -z ${PERFCTR:-} ]]; then
  SECONDS=0
  timeout $LIMIT "${PRE[@]}" "$BIN" "${ARGS[@]}" --json-out result.json > grid.out 2>&1 \
    && log_run ok "T=$T L<=$MAX_L ${SECONDS}s" || log_run fail "T=$T exit $? ${SECONDS}s"
else
  # likwid-perfctr pins the threads itself (-C), so turn OpenMP binding off to avoid fighting it.
  export OMP_PROC_BIND=false; unset OMP_PLACES
  for g in $PERFCTR; do
    SECONDS=0
    # Totals go to perfctr-<g>.csv. TIMELINE=1 instead samples every second (to stderr), which lets
    # you cut out setup and look at the Dirac phases only, since we cannot add markers to Grid.
    if [[ -n ${TIMELINE:-} ]]; then MODE=(-t 1s); ERR="timeline-$g.txt"; else MODE=(-O -o "perfctr-$g.csv"); ERR="grid-$g.err"; fi
    timeout $LIMIT likwid-perfctr -C "N:0-$((T-1))" -g "$g" "${MODE[@]}" \
      "${PRE[@]}" "$BIN" "${ARGS[@]}" --json-out "result-$g.json" > "grid-$g.out" 2>"$ERR" \
      && log_run ok "perfctr $g T=$T ${SECONDS}s" || log_run fail "perfctr $g T=$T exit $?"
  done
fi
