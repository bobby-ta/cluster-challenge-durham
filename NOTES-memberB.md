# Member B notes: DINE likwid-bench

## Done so far
- **Tue 21 Oct, 23:32:** ran DINE recon (job 12198164) on `b113`. The CPU is an AMD EPYC 7302. Performance counters work (`perfctr works` in `results/runlog.csv`).
- **Wed 22 Oct, ~02:30:** queued the likwid-bench campaign on `ciuk-dine` (4 jobs, all pending at submission):

  | Job | Mode | Purpose |
  |---|---|---|
  | 12200761 | `threads` | repeat 1: bandwidth + FLOP/s vs thread count, compact and scatter |
  | 12200762 | `threads` | repeat 2 |
  | 12200763 | `threads` | repeat 3 |
  | 12200764 | `sizes`   | bandwidth vs working-set size, 8 kB to 2 GB, 1 thread and 32 cores |

  Commands used:
  ```bash
  for r in 1 2 3; do scripts/submit.sh dine likwid_bench -- threads; done
  scripts/submit.sh dine likwid_bench -- sizes
  ```
  Repeats are separate jobs so they land on different nodes and at different times, which gives
  honest error bars. Each job also repeats every measurement 3 times (`REPEATS=3`).
  The mode for each job ID is assumed from the submission order.

- **Skipped:** the single smoke run before queueing the repeats.

## To do this morning
1. Check that the jobs ran:
   ```bash
   sacct -j 12200761,12200762,12200763,12200764 --format=JobID,State,Elapsed,NodeList
   ls results/dine/likwid-threads/ results/dine/likwid-sizes/
   ```
2. Look at the output in each run dir: `out.csv` (rows present, MBps/MFlops filled in) and `errors.txt` (should not exist).
   If any job shows `TIMEOUT`, the rows it wrote are still there. Rerun only the missing kernels:
   `KERNELS="..." scripts/submit.sh dine likwid_bench -- threads`
3. Check the job logs in `results/slurm/lbench-dine-*.out`.
4. Commit: `git add results && git commit -m "results: dine likwid threads x3 + sizes"`
5. Run the analysis: `python3 analysis/collect.py && (cd analysis && python3 plots.py)`
6. Still outstanding from the plan:
   - Fix module names in `config/dine.env` (the openmpi line is still a TODO).
   - Fill in `analysis/peaks.py`, using DIMM speed and NPS mode from the recon `likwid-topology` output.
   - Fill in the team name and users in `config/team.env`. They are still `TODO`, so the queued jobs' `meta.txt` will record `TODO`.
7. Wednesday analysis (plan §4): where bandwidth saturates (per NUMA domain and per socket), FLOP/s vs peak, compact vs scatter. Fill gaps (NT-store kernels, a single-NUMA-domain run). Start bullet notes for report §2.1.
