# Submission review and Part D handoff

Team: **UCLuster Too**\
Users: **dc-loke1, dc-ge2, dc-huan6, dc-ta1**\
Review date: 23 October 2026

## Current conclusion

The evidence supports a substantial Part D contribution without starting another broad benchmark campaign. The teammate snapshot contains completed Grid tuning runs and valid DINE LIKWID measurements. Kai's overnight analysis supplies the consistent scaling series and process-wide counter estimates. Submission readiness still depends on integrating those sources correctly, checking the final artifacts, and retaining the source-run evidence. A completed Slurm job or a generated summary does not alone certify scientific validity.

The brief asks for maximum compute performance and memory bandwidth. It does not make a DINE2 LIKWID thread sweep mandatory. A valid full-node DINE2 ceiling can address the maximum-performance requirement. A thread sweep is useful additional evidence for a bandwidth-saturation explanation, if the team already has a corrected one.

## Evidence and remaining actions

| Area | Evidence available | Remaining action or limit |
|---|---|---|
| DINE strong scaling | Overnight medians at fixed L, up to 32 physical-core threads; all 44 source records retained | Imported, recalculated and plotted from verified export; raw records match the export |
| DINE2 strong scaling | Overnight medians at fixed L, up to 64 physical-core threads; all 53 source records retained | Imported, recalculated and plotted from verified export; raw records match the export |
| Weak scaling | Matched exact pairs: L24/T2 to L48/T32 on both nodes. Additional DINE2 pair L24/T4 to L48/T64 | Label these within-node tests. The additional DINE2 full-node pair has a different work-per-thread baseline |
| Counter roofline | Six process-wide SP/DRAM estimates. Full-node rows are simultaneous measurements | Use SP roofs and explicit whole-process labels. Keep lower-thread separate-pass estimates approximate |
| A's best configurations | Raw JSON reproduces 361.403 GFLOP/s DINE and 864.215 GFLOP/s DINE2 medians | Keep separate from the overnight scaling build. Preserve repeat ranges and clarify 128 SMT threads versus 64 cores |
| DINE LIKWID | Valid corrected bandwidth and compute runs in the teammate snapshot | Select and cite a consistent dataset for ceilings. Do not mix nearly identical medians from different campaigns |
| DINE2 LIKWID | Overnight full-node ceilings are available through the supplied analysis. Legacy teammate sweeps have documented pinning exclusions | Check the full-node source records for B/C's maximum-performance discussion. Do not reuse excluded sweeps or invent a saturation thread count |
| Report and figures | Four verified PDF figures live in `report/figs/overnight-20261022T224854Z/submission_*.pdf`; insert-ready paragraphs are `report/part-d-insert.tex` | Team must insert D into `report/report.tex`, complete B/C, compile and confirm the strict two-page report limit |
| Presentation | `docs/slides-D.md` supplies three D slides with notes and viva answers | Merge into the team deck. This Markdown file is not a completed PPTX or PDF presentation |
| Provenance | Teammate raw tuning files and all 97 overnight records are retained, including both failed smoke runs | Run `python3 analysis/check_overnight_raw.py`; see `docs/overnight-raw-audit-20261023.md`. Campaign-level Slurm accounting remains absent; provenance coverage alone does not validate every numerical interpretation |

## Part D numbers to carry into the report

### Strong scaling

| Node | L | One-thread median | Full-node median | Speedup | Efficiency |
|---|---:|---:|---:|---:|---:|
| DINE, 32 threads | 24 | 21.598 GFLOP/s | 352.596 GFLOP/s | 16.325× | 51.0% |
| DINE, 32 threads | 32 | 20.384 GFLOP/s | 350.573 GFLOP/s | 17.198× | 53.7% |
| DINE2, 64 threads | 24 | 35.217 GFLOP/s | 768.923 GFLOP/s | 21.834× | 34.1% |
| DINE2, 64 threads | 32 | 32.462 GFLOP/s | 695.397 GFLOP/s | 21.422× | 33.5% |

These are DWF FP32 kernel rates from the overnight series. They must not be pooled with instrumented whole-process rates or the separate GCC tuning build.

The three-run full-node ranges are 348.711–353.276 GFLOP/s at L24 and 350.496–355.694 at L32 for DINE. They are 762.063–781.156 at L24 and 691.578–705.664 at L32 for DINE2. The supplied `grid.csv` reproduces the reported medians exactly. These repeat ranges describe observed variation and are not statistical confidence intervals.

### Exact weak scaling

- DINE: L24/T2 to L48/T32, 165,888 four-dimensional lattice sites per thread in both cases, 56.4% retention of throughput per thread.
- DINE2, matched pair: L24/T2 to L48/T32, 165,888 sites per thread in both cases, 32.1% retention.
- DINE2, additional full-node pair: L24/T4 to L48/T64, 82,944 sites per thread in both cases, 31.4% retention.
- Fixed Ls = 12. Work and threads increase by the same factor of 16. Use the first two pairs for a thread-count/workload-matched cross-node comparison and identify the different baseline in the additional DINE2 pair.

### Counter scope

The full-node simultaneous rows give DINE 259.329 SP GFLOP/s and 164.734 GB/s, or 1.574 SP FLOP/DRAM byte. DINE2 gives 505.858 SP GFLOP/s and 243.573 GB/s, or 2.077 SP FLOP/DRAM byte. These are whole-process values across multiple phases. They cannot be assigned to an isolated L24/L32 DWF kernel.

### Grid AXPY versus LIKWID

At L64, the Grid memory benchmark uses 3,072 MiB and reaches median useful-byte rates of 174.383 GB/s on DINE and 350.429 GB/s on DINE2. The corresponding temporal LIKWID triad medians are 178.608 and 393.154 GB/s, giving ratios of 97.6% and 89.1%. Use decimal GB/s consistently. Keep this useful-byte comparison separate from hardware-counter DRAM traffic. Small cache-sensitive cases can report rates above the DRAM roof without contradicting it.

## Code risks addressed by the integration review

The repaired collector and plotter address the following issues. **All 26 offline tests pass**, including provenance, failed-group and counter-pairing regressions; the separately validated overnight CSV generator also passes its numeric checks. The raw-record verifier now checks all 97 exported invocations against the supplied source records. These checks verify local processing and record coverage; campaign-level Slurm accounting remains a separate requirement.

1. **Tagged experiments hidden from plots.** The old plot selector expected untagged `grid` experiments and could omit `grid-cover-scaling`. The selector must accept an explicit baseline family while excluding tuning and instrumentation from the same curve.
2. **Mixed provenance.** Grouping only by node, nominal config, threads and L can combine different compilers, runtimes or affinity layouts. Keep build, runtime, host/placement and workload metadata available, and aggregate only compatible observations.
3. **Counter failure concealed by a later successful pass.** A failed MEM pass followed by a successful FLOPS_SP pass must not make the entire directory look valid. Gate each group against its own completion evidence.
4. **Incompatible counter pairing.** Join SP and DRAM only from the same run or an explicit matching pair with compatible provenance, workload and runtime. Never pair by thread count alone.
5. **Bandwidth unit mismatch.** Grid can label binary GiB/s-like output as GB/s. Preserve the original field and convert to decimal GB/s consistently before comparing with LIKWID.
6. **Runtime aggregation error.** A summary `STAT` maximum is a maximum, not the sum of replicated per-core runtime fields. Preserve the aggregation meaning when applying runtime-matching checks.
7. **Distinct overnight raw-record format.** The teammate collector and the overnight `record.json` format differ. All 97 source records are now imported; the generic collector excludes those directories and preserves the separate overnight analysis path.
8. **Stale files mistaken for fresh output.** Remove or mark generated figures whose current source data is absent. Verify all figures referenced by the report come from the selected input snapshot.

Synthetic unit tests can check these parsing and calculation rules. They do not prove that the original jobs used the intended hardware or that a missing raw counter log was valid.

## Wording corrections that affect the conclusions

- DINE's L32 half-node spread result improves over compact placement by 35.4%. Avoid a blanket statement that spreading hurts.
- DINE2's socket-ordering effect is supported by tested configurations and some same-host comparisons, but compiler/runtime and host differences prevent a complete causal attribution. Use “consistent with affinity and NUMA sensitivity.”
- Call the small-L results “small-lattice” or “cache-sensitive.” Total L3 size alone does not prove all live fields fit in each relevant cache domain.
- Label theoretical peaks by precision and clock assumption. Base-clock peaks and all-core extrapolations of maximum turbo are different from measured sustained ceilings.
- Installed DIMM speeds are unverified in `analysis/peaks.py`. Treat the 409.6 and 563.2 GB/s bandwidth figures as theoretical interface upper bounds.
- Team identity in the submission is UCLuster Too with all four users. Keep historical raw metadata unchanged even if earlier runs contain a placeholder or a different campaign label. Explain that difference in provenance notes.
- `docs/part-d.md` has been replaced with the completed campaign guide. The previous statements about missing Grid results no longer apply.

## Final submission gate

Before upload, one team member should confirm each item:

- [ ] The report PDF is at most two pages and contains no TODOs, blank B/C/D sections, broken references or clipped figures.
- [ ] The report states the exact benchmark metric, precision, lattice, thread count, repeat statistic and build family for every headline number.
- [ ] Strong-scaling, exact weak-scaling and process-wide roofline results are present with their limitations.
- [ ] B/C's maximum compute and memory bandwidth conclusions use valid measurements on both nodes. Invalid early DINE2 pinning runs remain excluded.
- [ ] Source data for the overnight analysis remains available, with raw JSON/logs and metadata where provided. Missing raw evidence is disclosed rather than silently treated as verified.
- [ ] The integration tests pass, and the report figures regenerate from the packaged inputs.
- [ ] A final job/time-efficiency count uses the chosen campaign cut-off. The old “205 jobs, 178 completed, 28.5 node-hours” snapshot is not automatically a final total and may not include Kai's rescue campaign.
- [ ] The team deck includes D's results and complies with the presentation requirements in the brief.
- [ ] Team name and usernames match across the report, cover, presentation and submission metadata.

No additional overnight submission is required solely to produce stronger-looking coverage. Prioritize a complete, traceable report from the measurements already available. Run only a targeted missing measurement if the final evidence audit identifies a genuine requirement that cannot be supported by existing valid data.
