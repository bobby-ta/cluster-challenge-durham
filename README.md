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

## Friday 23 October results and submission update

Part D has now completed the overnight Grid campaign; see
[`docs/part-d.md`](docs/part-d.md) for measured methods, limitations, and
report-ready values. The **95 successful / 97 recorded** runs are represented
by the read-only exports in `analysis/overnight-20261022T224854Z/`.

The matching raw evidence is preserved in
`results/{dine,dine2}/grid-overnight-20261022T224854Z/`: **44 DINE + 53 DINE2
records**, including both failed runs. Verify coverage with:

```bash
python3 analysis/check_overnight_raw.py
```

See [`docs/overnight-raw-audit-20261023.md`](docs/overnight-raw-audit-20261023.md)
for the import audit. The raw campaign retains its original layout and bytes;
the generic collector leaves it to the separate overnight analysis.

To regenerate the four team-presentation/report-ready PDFs **without running
new cluster jobs**:

```bash
python3 analysis/plot_overnight_exports.py
python3 -m unittest discover -s analysis -p 'test_*.py'
```

The generated figures are `report/figs/overnight-20261022T224854Z/submission_*.pdf`.
The source export CSVs and original figures are not modified. `plots.py`
remains the **teammate GCC campaign** plotter; the new script is the separate
**Clang overnight** plotter. Do not concatenate the two families by the common
`cpu-avx2`/`cpu-avx512` labels.

For the team's two-page LaTeX submission, the **ready-to-insert** Part D
paragraphs are in `report/part-d-insert.tex`. Move the first two paragraphs
into the existing `Grid` section, and the last two into `Grid vs. LIKWID`.
Keep the separately sourced A best-case tuning paragraph. Do not copy the
helper file unchanged into the report: its explanatory comments intentionally
retain the placement and duplicate-heading cautions. The report still awaits
final B/C wording and layout verification against the strict two-page limit.

### If you want to refresh the teammate analysis from raw jobs

```bash
python3 analysis/collect.py
(cd analysis && python3 plots.py)
```

Run the collector **before** the generic plotter. The repaired collector keeps
build/runtime, host, affinity, and test-case provenance so valid but
non-comparable jobs are not merged into attractive yet incorrect scaling lines.
Legacy separate counter jobs without explicit pairing IDs stay separate; use
the separately validated overnight whole-process counter CSV for the submitted
roofline. The ordinary offline tests check both these provenance requirements
and the overnight exported values.

### What this archive does not prove

The earlier overnight RAR contained derived CSVs and publication figures.
The subsequent raw-results ZIP now supplies all 97 matching per-job records,
benchmark outputs, build flags and runtime logs. Campaign-level Slurm
`accounting.tsv` and `jobs.tsv` remain absent, so this evidence does not establish
complete resource accounting for the team.

The original B report's DINE cache figure uses a known-excluded half-node
SMT dataset (12200764) in its all-core panel; remove or regenerate that panel
before the final team report. See `docs/submission-review.md` for other
submission checks. The queue closes at **16:00 BST on Friday 23 October**.
