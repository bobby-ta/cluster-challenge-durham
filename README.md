# cluster-challenge-durham
Durham leg of the CIUK Cluster Challenge 2026. The team plan is in `docs/team-plan.pdf`.

## Layout
```
config/      team.env (team name, users, Grid install root), dine.env / dine2.env (modules per queue)
slurm/       job scripts: recon, likwid_bench (threads|sizes), grid (array task id = thread count)
scripts/     submit.sh (always submit through this), campaign.sh (queue the core runs for one node)
build/       build_grid.sh + grid-config.json (Grid and Benchmark_Grid via aportelli/grid-benchmark)
analysis/    collect.py (results -> analysis/data/*.csv), plots.py (-> report/figs), peaks.py (theory)
results/     <node>/<experiment>/<jobid>/   raw output + meta.txt for every job; runlog.csv
report/      report.tex (2 pages A4, hard limit)
docs/        team plan
```

## Quick start on COSMA
```bash
ssh login8.cosma.dur.ac.uk
git clone <this repo> ~/ccd && cd ~/ccd
vi config/team.env                                   # team name + users

scripts/submit.sh dine  recon                        # first job on each queue
scripts/submit.sh dine2 recon
# Read results/<node>/recon/*/: fix the module names in config/*.env, pick the Grid SIMD config,
# fill in analysis/peaks.py. Check perfctr-smoke.txt says counters work.

build/build_grid.sh dine  cpu-avx2 8                 # on the login node (pixi needs internet)
build/build_grid.sh dine2 <config> 8

scripts/submit.sh dine likwid_bench -- threads       # single smoke run before the full campaign
scripts/submit.sh dine grid --array=32               # also tells you how long one Grid run takes
scripts/campaign.sh dine 3                           # then queue everything
```

Knobs for `slurm/grid.sbatch` (environment variables, see the header): `MAX_L`, `TAG`, `PERFCTR`,
`TIMELINE`, `NUMACTL`, `GRID_EXTRA`, `GRID_CONFIG`, `OMP_PROC_BIND`.
Always set `TAG` for anything that isn't a default run, so it lands in its own experiment directory
and the default scaling plots stay clean.

## Rules we follow
- Every job uses `--exclusive` and submits through `scripts/submit.sh`. Never hand-edit `results/`.
- Commit results straight after jobs finish: `git add results && git commit -m "results: <what>"`.
- Every compiler flag is in `build/systems/cosma/grid-config.json` and gets copied into each run dir.
- Queues close **Fri 23 Oct 16:00**. Final reruns must be submitted by Fri 12:00.
- If you make a shared directory on COSMA, lock it with `setfacl` so other teams can't read it.

## Analysis
```bash
python3 analysis/collect.py && (cd analysis && python3 plots.py)
```

`collect.py` skips the bad job IDs listed with reasons in `EXCLUDED_JOBS`, plus runs
whose `runlog.csv` status is not `ok`. Missing log entries alone do not reject older runs.
Exclusions cover whole jobs, including any usable single-core rows; raw results stay intact.
Only DINE jobs 12200761–12200763 retain the existing even-thread, compact AVX compute
reuse at half the recorded thread count. DINE2 requires fixed `flops`/`bw` runs.
Rooflines use the same compute selection and fixed bandwidth runs. Figures with no
valid source data are removed when plotting, so old charts cannot survive an exclusion.

Part D (Grid scaling, weak scaling, counters and roofline): see [`docs/part-d.md`](docs/part-d.md).
Run the offline collector/plot tests with `python3 -m unittest discover -s analysis -p 'test_*.py'`.
