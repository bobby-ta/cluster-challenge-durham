#!/bin/bash
#SBATCH -J recon
#SBATCH -A do022
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 00:15:00
# Partition is chosen at submit time: scripts/submit.sh <dine|dine2> recon
# First job on each queue: everything we need to know about the node, committed to git.
EXPERIMENT=recon
source "$REPO/slurm/common.sh"
record_meta
cd "$RUN_DIR"

lscpu                          > lscpu.txt
lscpu -e                       > lscpu-e.txt
numactl -H                     > numactl.txt 2>&1 || true
free -g                        > free.txt
cat /proc/meminfo              > meminfo.txt
grep -m1 flags /proc/cpuinfo | tr ' ' '\n' | grep -E 'avx|fma|sse4' > simd-flags.txt
cpupower frequency-info        > cpupower.txt 2>&1 || true
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor > governor.txt 2>&1 || true
cat /proc/sys/kernel/perf_event_paranoid > perf_event_paranoid.txt 2>&1 || true
ls /sys/kernel/mm/transparent_hugepage/ && cat /sys/kernel/mm/transparent_hugepage/enabled > thp.txt 2>&1 || true
module avail                   > module-avail.txt 2>&1 || true
{ gcc --version; g++ --version; clang --version; mpicxx --version; } > compilers.txt 2>&1 || true

likwid-topology -g             > likwid-topology.txt 2>&1 || true
likwid-bench -a                > likwid-bench-kernels.txt 2>&1 || true
likwid-perfctr -a              > likwid-perfctr-groups.txt 2>&1 || true
likwid-perfctr -i              > likwid-perfctr-info.txt 2>&1 || true
# Smoke test: can we actually read counters? (Task 2 depends on this.)
likwid-perfctr -C 0 -g FLOPS_DP likwid-bench -t peakflops -W N:32kB:1 > perfctr-smoke.txt 2>&1 \
  && log_run ok "perfctr works" || log_run warn "perfctr FAILED - see perfctr-smoke.txt"
