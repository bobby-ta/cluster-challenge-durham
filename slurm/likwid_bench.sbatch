#!/bin/bash
#SBATCH -J lbench
#SBATCH -A do022
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 00:55:00
# likwid-bench sweeps. One job = one mode, all kernels, all thread counts, so it fits in < 1 h.
# Usage (via scripts/submit.sh): likwid_bench.sbatch <mode>
#   threads : bandwidth and flops vs thread count, compact and scatter placement
#   sizes   : bandwidth vs working-set size (L1 -> DRAM), 1 thread and all cores
# Override kernels with KERNELS="triad_avx ..." and thread list with THREADS="1 2 4 ...".
EXPERIMENT=likwid-${1:?mode}
source "$REPO/slurm/common.sh"
record_meta "$@"
cd "$RUN_DIR"

available=$(likwid-bench -a | awk '{print $1}' | tr -d ':')
pick() { for k in "$@"; do grep -qx "$k" <<<"$available" && echo "$k"; done; true; }

FLOP_KERNELS=$(pick peakflops peakflops_sse peakflops_avx peakflops_avx_fma peakflops_avx512 peakflops_avx512_fma \
                    peakflops_sp peakflops_sp_avx peakflops_sp_avx_fma peakflops_sp_avx512 peakflops_sp_avx512_fma)
BW_KERNELS=$(pick load_avx copy_avx copy_mem_avx store_avx store_mem_avx stream_avx stream_mem_avx \
                  triad_avx triad_mem_avx daxpy_avx load_avx512 copy_avx512 stream_avx512 triad_avx512)
KERNELS=${KERNELS:-"$FLOP_KERNELS $BW_KERNELS"}
NUMA=$(likwid-topology | awk '/NUMA domains:/{print $3}')
THREADS=${THREADS:-"$(seq -s ' ' 1 1 4) 6 8 12 16 20 24 28 32 48 64 96 128"}
REPEATS=${REPEATS:-3}

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

case "$1" in
threads)
  for k in $KERNELS; do
    # Flop kernels: keep data in L1 (16 kB/thread). Bandwidth kernels: 2 GB total, far beyond L3.
    if [[ $k == peakflops* ]]; then per=16; else per=0; fi
    for t in $THREADS; do
      (( t > NCORES )) && continue
      if [[ $per != 0 ]]; then size="$((per*t))kB"; else size=2GB; fi
      # compact: likwid fills the node domain core by core
      run "$k" compact "$t" "$size" -W "N:$size:$t"
      # scatter: spread evenly over NUMA domains (only when it divides)
      if (( NUMA > 1 && t >= NUMA && t % NUMA == 0 )); then
        if [[ $per != 0 ]]; then dsize="$((per*t/NUMA))kB"; else dsize="$((2048/NUMA))MB"; fi
        args=(); for ((m=0; m<NUMA; m++)); do args+=(-W "M$m:$dsize:$((t/NUMA))"); done
        run "$k" scatter "$t" "$size" "${args[@]}"
      fi
    done
  done ;;
sizes)
  SIZES=${SIZES:-"8kB 16kB 24kB 32kB 64kB 128kB 256kB 512kB 1MB 2MB 4MB 8MB 16MB 32MB 64MB 128MB 256MB 512MB 1GB 2GB"}
  for k in ${KERNELS_SIZES:-$(pick load_avx copy_avx triad_avx stream_avx)}; do
    for s in $SIZES; do
      run "$k" single 1 "$s" -W "N:$s:1"
      # all cores: size is per thread, so scale the total
      num=${s%[kMG]B}; u=${s#$num}
      run "$k" all "$NCORES" "$s" -W "N:$((num*NCORES))$u:$NCORES"
    done
  done ;;
*) echo "unknown mode $1"; exit 1 ;;
esac

log_run ok "$(wc -l < out.csv) rows"
