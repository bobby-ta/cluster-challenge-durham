#!/bin/bash
#SBATCH -J test_run
#SBATCH -A do022
#SBATCH -p ciuk-dine
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 00:02:00
#SBATCH -o results/slurm/%x-%j.out
# Hello-world job for getting familiar with Slurm on COSMA. Run from the repo root:
#   sbatch scripts/test_run.sh                  # DINE
#   sbatch -p ciuk-dine2 scripts/test_run.sh    # DINE2 (command-line -p overrides the one above)
# Then: squeue -u $USER   and   cat results/slurm/test_run-<jobid>.out

echo "Hello from job $SLURM_JOB_ID ($SLURM_JOB_NAME)"
echo "partition:   $SLURM_JOB_PARTITION"
echo "node:        $(hostname)"
echo "user:        $USER"
echo "submit dir:  $SLURM_SUBMIT_DIR"
echo "working dir: $(pwd)"
echo "stdout file: $SLURM_SUBMIT_DIR/results/slurm/${SLURM_JOB_NAME}-${SLURM_JOB_ID}.out"
echo "cpus:        $(nproc) logical, $(lscpu | sed -n 's/^Model name: *//p')"
echo "date:        $(date -Iseconds)"
