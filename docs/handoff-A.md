# Handoff: A (build + tuning), session started Thu 22 Oct 20:46 BST

**Clone used for everything:** `/cosma/home/do022/dc-ta1/ccd` (fresh `git clone ~/ccd-sync.bundle`;
no earlier clone existed). Jobs write results into this clone.

**Bring A's commits to GitHub** (on your laptop, from the GitHub clone):
```bash
git fetch login8.cosma.dur.ac.uk:/cosma/home/do022/dc-ta1/ccd main:a-cosma && git merge a-cosma && git push
```

## State of the repo (survey, Thu 20:46–21:00)
- Bundle = `main` at `8b8391a` (D, Thu 17:27). Authors: Bobby Ta (setup), Ada Ge (`dc-ge2`; env
  files, dine2 recon + likwid), James Loke (`dc-loke1`; dine recon, likwid, scripts), I-Kai Huang
  (D; `793cd66` Part D analysis + hardened `grid.sbatch`, `8b8391a` `EXCLUDED_JOBS`).
- **No Grid build and no Grid runs** anywhere in the repo; `grid.csv`, `grid_axpy.csv`, `perfctr.csv`
  are empty after `collect.py`. `likwid.csv` has 1737 rows. Figures exist only for DINE likwid
  (bw/flops vs threads, roofline).
- `results/runlog.csv`: 8 lines (2 recon/node, dine likwid-bw ×4 + flops ×1, all ok). DINE2
  likwid jobs 12203200–02 and DINE sizes 12200764 are in `EXCLUDED_JOBS` (SMT pinning). README:
  DINE2 still needs fixed `flops`/`bw` runs (B/C).
- `results/slurm/` is empty in this clone: no Slurm `.out` file was ever committed (see `.gitignore` fix).
- `python3 -m unittest discover -s analysis` **errors on import**: system python3.9 has no matplotlib
  (`plots.py` imports it). Environment issue, not a code bug; `collect.py` itself runs fine.
- `squeue --me`: empty. The do022 queue is busy with other users' Grid jobs (dc-lakh1, dc-nimi1,
  dc-ali3, dc-lam2, dc-li23, dc-simc1); I can't tell whether any is a teammate.
- Existing builds: `/cosma/home/do022/dc-cheu3/ciuk-grid` (layout `jobs/ logs/ workflows/`, not ours,
  probably another team): **not used, not inspected further**. `/cosma*/data` and `/snap*` were
  not searched (site policy forbids scanning them).

## 1. Open items (need you / a teammate)
- Team name + 4 COSMA usernames for `config/team.env` and the `setfacl` grants. Until then the
  build is **only readable by dc-ta1**, so D's jobs cannot use it.

## 2. Done
- `646fc44` `.gitignore`: `!results/**/*.out`, `!results/**/*.log`.
- `1f501b9` `.gitattributes`: `results/runlog.csv merge=union`.
- `10de561` `GRID_ENV_ROOT=/cosma/home/do022/dc-ta1/ciuk-grid` (absolute) in `config/team.env`.
- `355b170` build layout fixed for grid-benchmark `c7457a8` (see Decisions).
- Privacy: `~`, `~/ccd`, `~/ciuk-grid`, `/cosma/apps/do022/dc-ta1` set `go-rwx` + default ACL
  `g::---,o::---` (do022 group = every team on the account).

## 3. Queued jobs
None yet.

## 4. Still to submit before Fri 12:00
TODO after smoke.

## 5. Best case so far
TODO (no Grid data).

## 6. Smoke timing
TODO.

## 7. Decisions
- **Build location:** `$HOME/ciuk-grid` on /cosma/home (965 TB free). No do022 data dir was
  looked for, because policy forbids scanning /cosma5–8 and /snap7–8.
- **Privacy is stricter than `o-rwx`:** `do022` is shared by all teams, so group access is removed
  too (`go-rwx`); teammates get access via `setfacl -m u:<user>:...` only.
- **grid-config.json** (A owns build/): added `"env-script": ""` (else `jq -e` fails in env.sh) and a
  `files/` dir (else bootstrap's `cp files/*` fails); `cpu-avx512` now `-march=sapphirerapids`
  (gcc 14.1); `LDFLAGS` RPATH to gcc 14.1 lib64 first, then the pixi lib dir, so jobs run without
  sourcing env.sh; clang configs use `CXX=clang++` (not `OMPI_CXX`: `mpi-auto` only takes MPI flags
  from `mpicxx`, the compiler is `$CXX`); added `cpu-avx512-clang`.
- **build_grid.sh** sources `config/<node>.env` first, so the build uses the run-time modules
  (gnu_comp/14.1.0, likwid/5.5.1, openmpi/5.0.3), and serialises `build-benchmark.sh` with `flock`
  because both nodes share the source tree.

## 8. For B / C / D
- **Everyone:** `.gitignore` now keeps `results/**/*.out|*.log`; `runlog.csv` merges with `union`.
  Please `git add results/slurm` with your next results commit.
- **D:** TODO Grid ready message.

## 9. Friday morning plan
TODO.
