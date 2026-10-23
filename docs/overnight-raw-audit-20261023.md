# Overnight Grid raw-evidence audit — 23 October 2026

Team: **UCLuster Too**. Campaign: `20261022T224854Z`.

An original COSMA raw-results archive was provided after the processed
23 October team snapshot. Its two experiment folders contain all **97**
`record.json` files referenced by `analysis/overnight-20261022T224854Z/runs.csv`:

| Node | Original job records |
|---|---:|
| DINE | 44 |
| DINE2 | 53 |
| **Total** | **97** |

The original run export contains **95 successful** and **2 failed**
invocations. The complete archive includes the failed records rather than
omitting them. The matching `runs.csv` and other exported `.csv` files were
byte-identical to those already present in the 23 October team snapshot;
the earlier copy additionally contained publication plots.

The supplied handoff identifies the original archive as
`kai-grid-overnight-raw-20261023.tar.gz` and reports this SHA-256 (the original
tarball was not independently checked during this Git import):
`0d5c91cb76eff3e8661a45ad90480e163b63e3d9ebc4443e8070eaf4936a2e12`.

The ZIP checked and imported into the team checkout is
`kai_overnight_raw_complete_github_update_20261023.zip`, SHA-256:
`8bece8ea53ef7c15775ce557f646ad2c405b2b15a68089b8e62bade10bdbdfa7`.
Its 1,313 raw files were copied byte-for-byte. The 97 exported source paths
match the 97 raw records exactly, with no missing or extra records. All 11
shared fields in each CSV row match its raw record, including the two failed
smoke runs (`12208680` and `12208686`, both exit code 6). The existing generic
collector excludes these `record.json` campaign directories, preserving the
separate overnight and teammate build families.

Run-level provenance can be rechecked after importing the directories:

```bash
python3 analysis/check_overnight_raw.py
```

This check validates the original record path, campaign, node, job identity,
JSON parseability, successful/failed status and the presence of output for
completed scaling/smoke jobs. It is a provenance check, **not** a rerun of
the numerical analysis or a claim that every counter isolates DWF4.

The archive does not contain `overnight-state/accounting.tsv` or `jobs.tsv`.
Run-level source evidence is therefore now available, but complete Slurm
accounting for all four team members still needs to be collected separately
if required for the testbed time-efficiency mark.

Original logs can contain account names, filesystem paths and environment
details. Review their contents before adding these raw directories to a
public GitHub repository. Keep the two original campaign/build families
separate from the teammate GCC campaign when deriving comparisons.
