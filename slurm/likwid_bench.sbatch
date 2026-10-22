#!/bin/bash
#SBATCH -J lbench
#SBATCH -A do022
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 00:30:00
# likwid-bench sweeps. One job = one mode (and, for bw, ideally one kernel), so each job is short.
# Usage (via scripts/submit.sh): likwid_bench.sbatch <mode>
#   flops   : FLOP/s vs cores, all scalar/SSE/AVX peakflops kernels, data in L1   (~20 min)
#   bw      : DRAM bandwidth vs cores, compact and scatter, 2 GB total           (~12 min per kernel)
#   sizes   : bandwidth vs working-set size (L1 -> DRAM), 1 core and all cores
# Override kernels with KERNELS="triad_avx ..." and the core list with THREADS="1 2 4 ...".
# Measured cost per likwid-bench call on DINE: ~6 s (peakflops), ~15 s (2 GB bandwidth).
#
# Pinning: always one thread per physical core. likwid's domains list SMT siblings next to each
# other (DINE: N = 0,32,1,33,...), so -W <dom>:<size>:<t>:1:<SMT> takes every SMT-th entry.
# Without the stride, "32 threads" was really 16 cores x 2 hyperthreads (jobs 12200761-64).
EXPERIMENT=likwid-${1:?mode}
source "$REPO/slurm/common.sh"
record_meta "$@"
cd "$RUN_DIR"

available=$(likwid-bench -a | awk '{print $1}' | tr -d ':')
grep -qw avx512f /proc/cpuinfo && HAS512=1 || HAS512=0
# Keep kernels that exist and that this CPU can execute (AVX-512 ones SIGILL on Zen 2).
pick() { for k in "$@"; do
  [[ $k == *avx512* && $HAS512 == 0 ]] && continue
  grep -qx "$k" <<<"$available" && echo "$k"; done; true; }

SMT=$(lscpu | awk -F: '/Thread\(s\) per core/{gsub(/ /,"",$2); print $2}'); SMT=${SMT:-1}
NUMA=$(likwid-topology | awk '/NUMA domains:/{print $3}')
REPEATS=${REPEATS:-3}
echo "SMT=$SMT NUMA=$NUMA NCORES=$NCORES HAS512=$HAS512" >> meta.txt

# One run; appends "kernel,placement,threads,size,rep,MByte/s,MFlops/s" to out.csv
run() {  # run <kernel> <placement> <threads> <size-per-thread> <workgroup args...>
  local k=$1 pl=$2 t=$3 sz=$4; shift 4
  for rep in $(seq "$REPEATS"); do
    out=$(likwid-bench -t "$k" "$@" 2>&1) || { echo "$out" >> errors.txt; continue; }
    echo "$out" >> raw/"$k".txt
    mbs=$(awk -F'[: \t]+' '/^MByte\/s/{print $2}' <<<"$out")
    mfs=$(awk -F'[: \t]+' '/^MFlops\/s/{print $2}' <<<"$out")
    echo "$k,$pl,$t,$sz,$rep,${mbs:-},${mfs:-}" >> out.csv
  done
}
mkdir -p raw
echo "kernel,placement,threads,size,rep,MBps,MFlops" > out.csv

# compact: fill cores in order (socket 0 first). scatter: same number of cores on every NUMA domain.
compact() { run "$1" compact "$2" "$3" -W "N:$3:$2:1:$SMT"; }
scatter() {  # scatter <kernel> <threads> <total size> <size per domain>
  (( NUMA > 1 && $2 >= NUMA && $2 % NUMA == 0 )) || return 0
  local args=(); for ((m=0; m<NUMA; m++)); do args+=(-W "M$m:$4:$(($2/NUMA)):1:$SMT"); done
  run "$1" scatter "$2" "$3" "${args[@]}"
}

case "$1" in
flops)
  # Placement doesn't matter for in-L1 compute, so compact only. 16 kB per core stays in L1.
  for k in ${KERNELS:-$(pick peakflops peakflops_sse peakflops_avx peakflops_avx_fma peakflops_amd_zen_avx_fma_add \
                             peakflops_sp peakflops_sp_avx peakflops_sp_avx_fma)}; do
    for t in ${THREADS:-1 2 4 8 16 24 32}; do
      (( t > NCORES )) && continue
      compact "$k" "$t" "$((16*t))kB"
    done
  done ;;
bw)
  # 2 GB total, far beyond the 256 MB of L3, so this is DRAM bandwidth.
  for k in ${KERNELS:-$(pick load_avx copy_avx triad_avx triad_mem_avx)}; do
    for t in ${THREADS:-1 2 4 6 8 12 16 24 32}; do
      (( t > NCORES )) && continue
      compact "$k" "$t" 2GB
      scatter "$k" "$t" 2GB "$((2048/NUMA))MB"
    done
  done ;;
sizes)
  SIZES=${SIZES:-"8kB 16kB 24kB 32kB 64kB 128kB 256kB 512kB 1MB 2MB 4MB 8MB 16MB 32MB 64MB 128MB 256MB 512MB 1GB 2GB"}
  for k in ${KERNELS:-$(pick load_avx copy_avx triad_avx)}; do
    for s in $SIZES; do
      run "$k" single 1 "$s" -W "N:$s:1"
      # all cores: size is per thread, so scale the total
      num=${s%[kMG]B}; u=${s#$num}
      run "$k" all "$NCORES" "$s" -W "N:$((num*NCORES))$u:$NCORES:1:$SMT"
    done
  done ;;
*) echo "unknown mode $1 (flops|bw|sizes)"; exit 1 ;;
esac

log_run ok "$(($(wc -l < out.csv) - 1)) rows"
