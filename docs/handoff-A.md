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
- **Team name + 4 COSMA usernames** for `config/team.env` and the `setfacl` grants. Until then the build in
  `/cosma/home/do022/dc-ta1/ciuk-grid` is readable only by dc-ta1, so D cannot run Grid from their account.
  All Grid data so far was submitted from dc-ta1 (job ids in §3; their `meta.txt` says `team=TODO-team-name`).
- **D:** unknown whether D queued their own scaling; A's `cover-scaling` (1 repeat) + `perfctr-cover` (T=1 only)
  exist. D must read the DINE2 placement and perfctr-pinning notes in §7/§8.

## 2. Done
- `646fc44` `.gitignore`: `!results/**/*.out`, `!results/**/*.log`.
- `1f501b9` `.gitattributes`: `results/runlog.csv merge=union`.
- `10de561` `GRID_ENV_ROOT=/cosma/home/do022/dc-ta1/ciuk-grid` (absolute) in `config/team.env`.
- `355b170` build layout fixed for grid-benchmark `c7457a8` (see Decisions).
- Privacy: `~`, `~/ccd`, `~/ciuk-grid`, `/cosma/apps/do022/dc-ta1` set `go-rwx` + default ACL
  `g::---,o::---` (do022 group = every team on the account).

## 3. Queued jobs (submitted from `~/ccd`, account dc-ta1)
Format: `time jobid command`. Collect with:
`cd ~/ccd && git add results && git commit -m "results: <what>" && python3 analysis/collect.py && python3 analysis/tuning.py`
```
21:51 12208201 TAG=tune-base MAX_L=48 scripts/submit.sh dine grid --array=16,32
21:51 12208202 TAG=tune-base MAX_L=48 scripts/submit.sh dine2 grid --array=32,64
21:51 12208203 TAG=tune-interleave NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine grid --array=32
21:51 12208204 TAG=tune-interleave NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine2 grid --array=64
21:51 12208205 TAG=tune-smt OMP_PLACES=threads MAX_L=48 scripts/submit.sh dine grid --array=64
21:51 12208206 TAG=tune-smt OMP_PLACES=threads MAX_L=48 scripts/submit.sh dine2 grid --array=128
21:51 12208207 TAG=tune-clang GRID_CONFIG=cpu-avx2-clang MAX_L=48 scripts/submit.sh dine grid --array=32
21:51 12208210 TAG=tune-clang GRID_CONFIG=cpu-avx512-clang MAX_L=48 scripts/submit.sh dine2 grid --array=64
21:51 12208211 TAG=tune-unroll GRID_EXTRA=--dslash-unroll MAX_L=48 scripts/submit.sh dine grid --array=32
21:51 12208212 TAG=tune-unroll GRID_EXTRA=--dslash-unroll MAX_L=48 scripts/submit.sh dine2 grid --array=64
21:53 12208216 TAG=tune-spread OMP_PROC_BIND=spread MAX_L=48 scripts/submit.sh dine grid --array=16
21:53 12208217 TAG=tune-spread OMP_PROC_BIND=spread MAX_L=48 scripts/submit.sh dine2 grid --array=32
21:53 12208218 TAG=tune-spread-interleave OMP_PROC_BIND=spread NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine grid --array=16
21:53 12208219 TAG=tune-spread-interleave OMP_PROC_BIND=spread NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine2 grid --array=32
21:53 12208220 TAG=tune-asm GRID_EXTRA=--dslash-asm MAX_L=48 scripts/submit.sh dine2 grid --array=64
21:53 12208221 TAG=tune-base MAX_L=48 scripts/submit.sh dine grid --array=16,32
21:53 12208222 TAG=tune-base MAX_L=48 scripts/submit.sh dine2 grid --array=32,64
21:53 12208223 TAG=tune-interleave NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine grid --array=32
21:53 12208224 TAG=tune-smt OMP_PLACES=threads MAX_L=48 scripts/submit.sh dine grid --array=64
21:54 12208231 TAG=tune-clang GRID_CONFIG=cpu-avx2-clang MAX_L=48 scripts/submit.sh dine grid --array=32
21:54 12208232 TAG=tune-unroll GRID_EXTRA=--dslash-unroll MAX_L=48 scripts/submit.sh dine grid --array=32
21:54 12208233 TAG=tune-spread OMP_PROC_BIND=spread MAX_L=48 scripts/submit.sh dine grid --array=16
21:54 12208234 TAG=tune-spread-interleave OMP_PROC_BIND=spread NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine grid --array=16
21:54 12208235 TAG=tune-interleave NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine grid --array=32
21:56 12208241 TAG=tune-interleave NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine2 grid --array=64
21:57 12208243 TAG=tune-smt OMP_PLACES=threads MAX_L=48 scripts/submit.sh dine2 grid --array=128
21:57 12208244 TAG=tune-clang GRID_CONFIG=cpu-avx512-clang MAX_L=48 scripts/submit.sh dine2 grid --array=64
21:57 12208245 TAG=tune-unroll GRID_EXTRA=--dslash-unroll MAX_L=48 scripts/submit.sh dine2 grid --array=64
21:59 12208249 TAG=tune-spread OMP_PROC_BIND=spread MAX_L=48 scripts/submit.sh dine2 grid --array=32
22:00 12208263 TAG=tune-spread-interleave OMP_PROC_BIND=spread NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine2 grid --array=32
22:00 12208264 TAG=tune-base MAX_L=48 scripts/submit.sh dine grid --array=16,32
22:02 12208266 TAG=tune-smt OMP_PLACES=threads MAX_L=48 scripts/submit.sh dine grid --array=64
22:02 12208267 TAG=tune-clang GRID_CONFIG=cpu-avx2-clang MAX_L=48 scripts/submit.sh dine grid --array=32
22:02 12208268 TAG=tune-unroll GRID_EXTRA=--dslash-unroll MAX_L=48 scripts/submit.sh dine grid --array=32
22:03 12208271 TAG=tune-base MAX_L=48 scripts/submit.sh dine2 grid --array=32,64
22:03 12208272 TAG=tune-interleave NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine2 grid --array=64
22:03 12208273 TAG=tune-spread OMP_PROC_BIND=spread MAX_L=48 scripts/submit.sh dine grid --array=16
22:03 12208274 TAG=tune-spread-interleave OMP_PROC_BIND=spread NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine grid --array=16
22:05 12208284 TAG=tune-smt OMP_PLACES=threads MAX_L=48 scripts/submit.sh dine2 grid --array=128
22:05 12208285 TAG=tune-clang GRID_CONFIG=cpu-avx512-clang MAX_L=48 scripts/submit.sh dine2 grid --array=64
22:05 12208286 TAG=tune-spread OMP_PROC_BIND=spread MAX_L=48 scripts/submit.sh dine2 grid --array=32
22:05 12208287 TAG=tune-spread-interleave OMP_PROC_BIND=spread NUMACTL=--interleave=all MAX_L=48 scripts/submit.sh dine2 grid --array=32
22:20 12208322 TAG=cover-scaling scripts/submit.sh dine grid --array=1,2,4
22:20 12208323 TAG=cover-scaling scripts/submit.sh dine2 grid --array=1,2,4
22:20 12208324 TAG=cover-scaling scripts/submit.sh dine grid --array=8,12,16
22:20 12208325 TAG=cover-scaling scripts/submit.sh dine2 grid --array=8,12,16
```
Cancelled (no-op `--dslash-*` flag): 12208220, 12208232, 12208245, 12208268. Cancelled (perfctr hang): 12208335.
Later submissions (full list: `sacct -u dc-ta1 -S 2026-10-22 -X -o JobID,JobName,State`): gc007 follow-up
12208364/67/96/99/407/08, clang-smt 12208386/401/14, recons 12208363, 12208434/35/41/81, 12208506/37,
sockorder 12208553–12208600, perfctr-cover T=1 12208409/10/16/27.
**Queued Fri 00:55 (optional DINE2 runs, Bobby's OK):** 12208909/11/13 `tune-smt-sockorder` (gcc, T=128,
`OMP_PLACES='{0,64}:32:2,{1,65}:32:2'`), 12208910/12/14 `tune-sockorder-half` (gcc, T=32, `'{0}:32:2,{1}:32:2'`),
all `-x gc007`, MAX_L=48. When `squeue --me` is empty:
```bash
cd ~/ccd && git add results && git commit -m "results: dine2 smt-sockorder + sockorder-half" \
  && python3 analysis/collect.py && python3 analysis/tuning.py && python3 analysis/job_count.py \
  && git add analysis/data && git commit -m "analysis: final tuning summary and job count"
```

## 4. Still to submit before Fri 12:00
Tuning sweep: all submitted (Thu 22:13). Cover runs are topped up automatically while this session lives;
anything left here was **not yet submitted, so submit it before Fri 12:00** (≤6 pending per partition):
```bash
cd ~/ccd
PERFCTR='MEM FLOPS_SP' TAG=perfctr-cover MAX_L=24 scripts/submit.sh dine grid --array=1
PERFCTR='MEM FLOPS_SP' TAG=perfctr-cover MAX_L=24 scripts/submit.sh dine2 grid --array=1
TAG=cover-scaling scripts/submit.sh dine grid --array=24,32
TAG=cover-scaling scripts/submit.sh dine2 grid --array=24,32,48
PERFCTR='MEM FLOPS_SP' TAG=perfctr-cover scripts/submit.sh dine grid --array=8,16,32
PERFCTR='MEM FLOPS_SP' TAG=perfctr-cover scripts/submit.sh dine2 grid --array=8,16,64
TAG=cover-scaling scripts/submit.sh dine2 grid --array=64
```

## 5. Best case (final for Thursday night, 23:50; `python3 analysis/tuning.py`)
Headline is over the brief's sizes L ≥ 24 (median of 3 separate jobs, dwf4, GFLOP/s SP):

| node | best median | config | L | T | jobs | % SP peak (base / turbo) |
|---|---|---|---|---|---|---|
| DINE | **361.4** (350.1–362.7) | gcc `cpu-avx2`, `close`, `OMP_PLACES=cores`, first-touch | 48 | 32 | 12208201_32 12208221_32 12208264_32 | 11.8 % / 10.7 % of 3072 / 3379 |
| DINE2 | **827.5** (824.4–833.4) | clang `cpu-avx512-clang`, `close`, `OMP_PLACES='{0,64}:32:2,{1,65}:32:2'` (socket-ordered SMT pairs), first-touch, `-x gc007` | 24 | 128 | 12208577_128 12208589_128 12208600_128 | 9.6 % / 5.9 % of 8602 / 13926 |

Single best runs, labelled as maxima: DINE 368.7 (tune-base T=32 L=32); DINE2 878.1 (gcc tune-smt T=128 L=24 on
gc007, whose numbering is already socket-contiguous). Cache-resident L < 24 (not headline): DINE 848.3 (clang L=16),
DINE2 2691.8 median / 2829.9 max (clang socket-ordered, L=12).

Reproduce:
```bash
TAG=tune-base MAX_L=48 scripts/submit.sh dine grid --array=32
TAG=tune-clang-smt-sockorder GRID_CONFIG=cpu-avx512-clang OMP_PLACES='{0,64}:32:2,{1,65}:32:2' MAX_L=48 scripts/submit.sh dine2 grid -x gc007 --array=128
```

**Knobs (L=32 unless stated; hypotheses unless marked measured):**
- *Interleave* hurts on both: DINE −23 % (359→278), DINE2 −14 % (644→557). With first-touch each thread's
  sites live in its own NUMA domain; interleave sends half the traffic across the socket link.
- *SMT* (2 threads/core): DINE −30 % (359→250), DINE2 neutral (644→643). The kernel is bandwidth-bound,
  so hiding latency gains nothing once DRAM is saturated, and on Zen 2 the extra threads also compete for L1/L2.
- *Half node*: DINE T=16 `close` = one socket: 219, vs `spread` (both sockets) 296 (**measured**: memory bandwidth
  of the second socket is worth +35 %). DINE2 T=32 `close` already spans both sockets (even/odd numbering) = 619,
  while `spread` lands on every *other* place = even cores = **socket 0 only** = 433. The same NUMA effect, mirrored.
- *Compiler*: clang ≈ gcc on DINE (−2 %). On DINE2 clang "wins" +47 % at L=24 with default placement, **but
  that is the OpenMP runtime, not the code generator**: clang binaries use LLVM libomp, which (hypothesis,
  consistent with the data) orders `OMP_PLACES=cores` by socket/core rather than by OS CPU number, so they were
  socket-ordered all along. Evidence: gcc with socket-ordered places 788 ≈ clang 740–747 (default or
  socket-ordered) at L=24, and on contiguous-numbered gc007 gcc 796 ≈ clang 759.
- *L*: DINE flat from 24 to 48 (~340–360), consistent with DRAM-bound for all L ≥ 24 (working set ≫ 16 MiB/CCX L3).
  DINE2 peaks at L=24/32 and drops at 48. L ≤ 16 is cache-resident and 2–4× faster on both nodes.
- *`--dslash-unroll/asm`*: no-ops in Benchmark_Grid (see Decisions).
- **Node variance on DINE2 (measured):** every gc007 run is 30–75 % faster at L=24 than the same config on
  gc001/3/4/5/6/8 (base 799 vs ~500; smt 878 vs ~532; interleave 658 vs ~482). Grid axpy at L=48: gc007 340 GB/s
  vs gc003 286 GB/s. Hypothesis: different DIMM population/speed on gc007 (recon was on gc008). DINE nodes agree within 4 %.

- *SMT on DINE2*: +3–10 % on top of good placement (clang 748→828 at L=24 socket-ordered); latency hiding helps
  once cross-socket traffic is gone. On DINE SMT loses 30 %.

**Untested combinations (Friday morning candidates):** gcc + SMT + socket-ordered pairs on even/odd DINE2 nodes
(gcc SMT on gc007 gave the single max 878); half node (T=32) socket-ordered on DINE2 to separate "one socket"
from "alternating" placement.

## 6. Smoke timing (Thu 21:46; jobs 12208156–12208159, all exit 0, `TAG=smoke`)
| node | T | MAX_L | wall (runlog) | dwf4 L=24 | L=32 | L=48 GFLOP/s SP |
|---|---|---|---|---|---|---|
| dine | 8 | 32 | 357 s | 126.6 | 117.5 | – |
| dine | 32 | 48 | 480 s | 334.6 | 345.2 | 348.8 |
| dine2 | 8 | 32 | 185 s | 223.9 | 216.5 | – |
| dine2 | 64 | 48 | 338 s | 505.1 | 645.7 | 437.2 |

- (a) Full node: L≤32 is under ~6 min (DINE) / ~4 min (DINE2) (estimate, not measured), and L≤48 takes 8 min / 5.6 min (measured).
- (b) 1 thread, L≤32: the upper bound is 8 × T=8 time (true only if 1→8 scaled perfectly; it scales worse because it's memory-bound, so
  the real time is lower): **DINE ≤ ~48 min, DINE2 ≤ ~25 min**. Both are under the 55-min `timeout`, so **no `MAX_L=24`
  fallback is needed**. DINE T=1 is the tightest; if it times out, rerun T≤2 with `MAX_L=24`.
- Tuning uses **`MAX_L=48`** (full-node L≤48 run < 30 min).
- `collect.py` parses the runs fine (columns `Gflops_dwf4`, `Gflops_wilson`, `Gflops_staggered`; failed
  12208088/89 dropped by runlog status). `meta.txt` `--- env` shows `GRID_CONFIG` (override works).

## 7. Decisions
- **gc007 follow-up (authorised by Bobby, Thu ~22:30):** `recon -w gc007`; 3× `tune-clang-gc007` and 3×
  `tune-base-gc007` (T=64, MAX_L=48, `-w gc007`); 3× `tune-clang-smt` (clang, OMP_PLACES=threads, T=128,
  random nodes). A gc007 best case is reported **labelled as best node**, next to the random-node median.
- **§7 cover for D queued at 22:20** (no answer about D by the 30-min mark): one repeat of D's strong
  scaling, `TAG=cover-scaling` (default MAX_L=32), split into ≤3-task arrays for the pending cap, plus
  `PERFCTR='MEM FLOPS_SP' TAG=perfctr-cover` at the same thread counts as part-d.md. **T=1 perfctr uses
  `MAX_L=24`**: grid.sbatch gives each perfctr group 3300/2 s = 27.5 min, and DINE T=1 L≤32 may need ~48 min.
- **RULE (after three self-inflicted breakages): never edit `build/`, `slurm/`, `config/` or `scripts/`
  while any job from this clone is queued or running.** Jobs read these files live from NFS; an
  in-place edit or even an atomic `mv` (stale NFS handle on compute nodes) kills them. Queue fixes,
  apply them when `squeue --me` is empty.
- **All four builds pass (21:37):** dine `cpu-avx2` + `cpu-avx2-clang`, dine2 `cpu-avx512` +
  `cpu-avx512-clang` (build jobs 12208099, 12208114; 3–18 min each on a DINE node). `ldd` clean,
  `GRID_UVM` on, Grid e2d607f, grid-benchmark c7457a8. DINE2 binaries can't run `--help` on the
  login node (EPYC 7542, no AVX-512): checked on DINE2 by the smoke runs instead.
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

- **`-mno-avx512fp16` on DINE2:** gcc 14 emits AVX512-FP16 `vmovw` for `-march=sapphirerapids`, which
  the system assembler (binutils 2.35.2, RHEL 9) rejects. Grid's SP kernels use AVX-512F/FMA, never
  FP16 arithmetic, so dropping only that extension is the smallest change; using pixi's binutils 2.46
  via `-B` would also have swapped the linker.
- **Default ACLs removed again:** on this VAST NFSv3 mount a default ACL (`g::---`) made
  autoconf's `configure` non-executable. Privacy does not depend on it: `~` and `~/ciuk-grid` are
  `drwx--S---`, so nobody else can traverse in.
- **Clang:** pixi clang 20.1.8 links against a glibc 2.17 sysroot and cannot link COSMA's
  openmpi (needs glibc 2.34). Clang configs use `CXX="clang++ --sysroot=/ --gcc-toolchain=/cosma/local/gcc/14.1.0"`
  (gcc 14.1 libstdc++, LLVM libomp from pixi). Verified with an MPI+OpenMP test program.
- **`tune-unroll` / `tune-asm` withdrawn (Thu 22:02):** Benchmark_Grid c7457a8 hardcodes
  `OptGeneric` in all four Dslash cases (`Benchmark-Grid/benchmarks/DeoFlops.hpp:218-232`), overwriting
  Grid's `--dslash-unroll/--dslash-asm`. Every `grid.out` says `Using GENERIC Nc` (48×), with or without the
  flag. Changing it needs a source edit (out of scope), so the kernel cannot be tuned. Cancelled my
  pending/running 12208220, 12208232, 12208245, 12208268. Finished 12208211_32 and 12208212_64 stay
  in `results/*/grid-tune-unroll/` and must be read as **base repeats run with a no-op flag**, not as a
  kernel comparison.
- **`--dslash-generic` dropped:** it is Grid's default (`WilsonKernelsStatic::Opt = OptGeneric`), so
  `tune-generic` would duplicate `tune-base`. Candidates: `--dslash-unroll` (both), `--dslash-asm` (DINE2).
- **Benchmark build:** grid-benchmark compiles 18 instantiation files (Sp4/SU4, ~9 min each,
  ~3 GB RSS). These dominate the Benchmark_Grid build.
- **`--enable-unified=no` removed (all configs):** with it, Grid on CPU emulates a separate device
  memory with a 128 MiB software cache; both first smoke runs (12208088_8, 12208089_32) aborted in the
  axpy benchmark with `GRID_ASSERT bytes<DeviceMaxBytes` (163,840,000 > 134,217,728) and would
  otherwise pay host<->"device" copies. Grid's default is unified=yes, and grid-benchmark's own
  `linux-x64` config doesn't set it. Rebuilt everything.
- **Compile in jobs:** `slurm/build.sbatch` (+ offline path in `build_grid.sh`: `PREPARE_ONLY=1` clones and
  bootstraps on the login node, the job compiles). Login node at ≤8 jobs needed ~40 min per node,
  most of it in 18 grid-benchmark instantiation files. Build jobs: 12208097 (dine2 cpu-avx512),
  12208098 (dine cpu-avx2-clang), 12208099 (dine cpu-avx2 + dine2 cpu-avx512-clang); 12208097's
  dine:cpu-avx2 and 12208098's dine2:cpu-avx512-clang lost a race on `systems/cosma` (fixed, `ceb9218`).
- **My own mistakes, for the record:** editing `build_grid.sh` while a build was reading it broke the
  first DINE run after the Grid install (fixed: edits are now swapped in with `mv`, and the script skips
  an installed Grid); a `pkill -f` matched its own shell. No data was affected.

- **Benchmark_Grid rejects `--max-L` < 32** (`Grid : Error : --max-L must be at least 32`), so the team plan's
  `MAX_L=24` fallback for T≤2 is **impossible**. perfctr-cover T=1 (12208332, 12208333) failed on this in 1–2 s;
  resubmitted as one LIKWID group per job (`PERFCTR=MEM` / `PERFCTR=FLOPS_SP`), so each gets the full 55 min.
  Cover-scaling DINE T=2 at L≤32 took 998 s, so T=1 should fit.
- **gc007 recon 12208363 vs gc008 recon 12202855 (measured):** (1) gc007 numbers socket 0 = CPUs 0–31
  (DINE-style), gc008 even/odd; (2) gc007 has HWP (`hwp*` cpu flags) and an active cpufreq driver (800–3400 MHz),
  gc008 has neither. Same CPU, same 2 TB, same NUMA sizes. Hypothesis: different BIOS power profile ⇒
  higher core/uncore clocks on gc007 ⇒ higher bandwidth and Grid throughput. **Consequence:** on DINE2,
  `close` with T ≤ 32 is one socket on gc007 but both sockets elsewhere, so half-node results depend on the node.

- **perfctr with T>1 hangs on DINE (measured, D's `grid.sbatch` path):** 12208335 (T=8/16/32, `-C N:0-(T-1)`)
  hit the 1650 s per-group timeout; every axpy call costs ~12 ms regardless of size (0.06 GB/s at L=8,
  vs ~10 µs normally) = OpenMP threads time-sliced on too few hardware threads. Likely cause (hypothesis):
  likwid's pin library pins threads in creation order, and Open MPI 5 starts helper threads before the
  OpenMP team, so Grid threads double up. T=1 runs are unaffected (12208409/10, 12208416/27 run at normal
  speed). Cancelled 12208335 (mine) during its second group; dropped the DINE2 T>1 perfctr set.
  **Suggested fix for D (untested):** count without pinning and let OpenMP pin: `likwid-perfctr -c N:0-$((T-1))`
  instead of `-C`, keeping `OMP_PROC_BIND=close OMP_PLACES=cores`; or `-C ... -s <skipmask>` to skip the MPI
  threads. Test one T=8 job before a campaign.

- **DINE2 recon of every node (gc001–gc008, measured):** all number cores even/odd per socket **except gc007**
  (contiguous); HWP on all except gc008. Recon jobs: 12208434 gc001, 12208435 gc002, 12208441 gc003,
  12208481 gc004, 12208506 gc005, 12208537 gc006, 12208363 gc007, 12202855 gc008.
- **DINE2 thread placement, the real cause of the "fast gc007" (measured, Thu 23:1x):** DINE2 recons:
  gc001, gc005, gc008 number cores even/odd per socket; gc007 is contiguous (socket 0 = 0–31). HWP is on
  gc001/5/7, off on gc008, so it's **not** HWP. With even/odd numbering and `OMP_PROC_BIND=close OMP_PLACES=cores`,
  Grid thread i and i±1 (which share lattice faces) sit on opposite sockets. Socket-ordered places
  `OMP_PLACES='{0}:32:2,{1}:32:2'` on even/odd node gc004 (12208553_64): dwf4 L24/32/48 = 795/702/624, the
  same as gc007 base (792/703/622) and +58/+9/+42 % over default placement on even/odd nodes (502/644/439).
  Hypothesis for the mechanism: cross-socket halo traffic between neighbouring threads; the size of the
  effect fits it, but it is not measured directly.

## 8. For B / C / D
- **Everyone:** `.gitignore` now keeps `results/**/*.out|*.log`; `runlog.csv` merges with `union`.
  Please `git add results/slurm` with your next results commit.
- **D (and C):** on DINE2 the OS numbers socket 0's cores **even** (0,2,…,62) and socket 1's **odd**,
  SMT siblings 64–127 (`likwid-topology`, recon 12202855). So `OMP_PLACES=cores OMP_PROC_BIND=close`
  with T≤32 spreads over **both** sockets on DINE2, unlike DINE (0–15 socket 0). Worth one line in §3.
  On DINE each 16 MiB L3 slice serves **2 cores** (EPYC 7302: 4 cores per CCD, 2 per CCX).
- **D (most important):** on DINE2's even/odd nodes the default `close/cores` placement costs Grid up to
  ~58 % (L=24) at T=64, because neighbouring threads land on opposite sockets. Socket-ordered
  `OMP_PLACES='{0}:32:2,{1}:32:2'` removes it (see Decisions). Your untagged DINE2 scaling therefore mixes
  node layouts: gc007 is contiguous, the others even/odd. Group by `host=` or state the placement caveat. For
  T<64 the effect differs again (close T=32 = both sockets alternating on even/odd nodes, one socket on gc007).
- **D (important):** DINE2 nodes differ (gc007: contiguous core numbering + HWP/turbo control; gc008: even/odd,
  no cpufreq driver). Check `host=` in each run's `meta.txt` before comparing DINE2 runs; half-node `close`
  runs are one socket on gc007 and two elsewhere. `MAX_L` < 32 is rejected by Benchmark_Grid.
- **C:** the DINE2 node variance is node-comparison material: gc007 30–75 % faster in Grid at L=24, axpy
  340 vs 286 GB/s. Your likwid DINE2 runs: check which host they ran on.
- **D:** `python3 -m unittest` fails on COSMA only because system python3.9 lacks matplotlib.
- **D:** TODO Grid ready message.

## 9. Friday morning plan (submit everything by 12:00; queues close 16:00)
1. Bobby: push A's commits (top of this file); send D/C the messages below; get usernames → A fills
   `config/team.env` (`config: team name and users`) and runs the `setfacl` grants (§3.3) **while no job is queued**.
2. **Already queued Fri 00:55** (12208909–14, see §3): only collect them. These were the commands:
   ```bash
   cd ~/ccd
   for r in 1 2 3; do
     TAG=tune-smt-sockorder OMP_PLACES='{0,64}:32:2,{1,65}:32:2' MAX_L=48 scripts/submit.sh dine2 grid -x gc007 --array=128
     TAG=tune-sockorder-half OMP_PLACES='{0}:32:2,{1}:32:2' MAX_L=48 scripts/submit.sh dine2 grid -x gc007 --array=32
   done
   ```
3. If D wants counters at T>1: fix the perfctr pinning in `grid.sbatch` first (see Decisions), test one T=8 job.
4. Re-run `python3 analysis/job_count.py` after the last job; update report §1 experiment count.
