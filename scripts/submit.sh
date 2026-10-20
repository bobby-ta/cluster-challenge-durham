#!/bin/bash
# Thin wrapper so every job gets the right partition, REPO path and log location.
#   scripts/submit.sh <dine|dine2> <job> [sbatch options...] [-- job args...]
# Examples:
#   scripts/submit.sh dine recon
#   scripts/submit.sh dine2 likwid_bench -- threads
#   scripts/submit.sh dine grid --array=1,2,4,8,16,24,32
#   MAX_L=48 TAG=L48 scripts/submit.sh dine grid --array=16,32
#   PERFCTR="MEM FLOPS_SP" TAG=perfctr scripts/submit.sh dine grid --array=1,8,32
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd); export REPO
NODE=${1:?dine|dine2}; JOB=${2:?job name}; shift 2
SB=(); while [[ $# -gt 0 && $1 != -- ]]; do SB+=("$1"); shift; done; [[ ${1:-} == -- ]] && shift
mkdir -p "$REPO/results/slurm"
sbatch -p "ciuk-$NODE" -A do022 --export=ALL \
  -o "$REPO/results/slurm/%x-$NODE-%A_%a.out" "${SB[@]}" "$REPO/slurm/$JOB.sbatch" "$@"
