# Shared helpers for all job scripts. Source this from inside a job.
# Expects REPO to point at the repo root (the submit scripts export it).
set -eo pipefail   # no -u: Lmod's module function trips over unset variables

: "${REPO:?REPO must be set (submit via scripts/submit.sh)}"
source "$REPO/config/team.env"

case "${SLURM_JOB_PARTITION:-}" in
  ciuk-dine)  source "$REPO/config/dine.env" ;;
  ciuk-dine2) source "$REPO/config/dine2.env" ;;
  *) echo "Unknown partition '${SLURM_JOB_PARTITION:-}'"; exit 1 ;;
esac

# One directory per job (per array task): results/<node>/<experiment>/<jobid>[_<task>]
run_id="${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}${SLURM_ARRAY_TASK_ID:+_$SLURM_ARRAY_TASK_ID}"
RUN_DIR="$REPO/results/$NODE_TAG/${EXPERIMENT:?}/$run_id"
mkdir -p "$RUN_DIR"

# Physical core count of this node (ignores SMT siblings).
NCORES=$(lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l)
NSOCKETS=$(lscpu -p=SOCKET | grep -v '^#' | sort -u | wc -l)

record_meta() {
  {
    echo "team=$TEAM_NAME"
    echo "users=$TEAM_USERS"
    echo "experiment=$EXPERIMENT"
    echo "job=$run_id"
    echo "partition=$SLURM_JOB_PARTITION"
    echo "host=$(hostname)"
    echo "date=$(date -Iseconds)"
    echo "git=$(git -C "$REPO" rev-parse --short HEAD)$(git -C "$REPO" diff --quiet || echo -dirty)"
    echo "ncores=$NCORES nsockets=$NSOCKETS"
    echo "cpu=$(lscpu | sed -n 's/^Model name: *//p')"
    echo "args=$*"
    echo "--- modules"; module list 2>&1 || true
    echo "--- env"; env | grep -E '^(OMP_|GRID_|LIKWID|SLURM_JOB|NODE_TAG)' | sort
  } > "$RUN_DIR/meta.txt"
}

# Append one line to the shared run log (array tasks may finish together, hence flock).
log_run() {  # log_run <status> <note>
  local log="$REPO/results/runlog.csv"
  (
    flock 9
    echo "$(date -Iseconds),$run_id,$NODE_TAG,$EXPERIMENT,$1,\"$2\",$(hostname)" >> "$log"
  ) 9>"$log.lock"
}
