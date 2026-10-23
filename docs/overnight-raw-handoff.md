# Kai's overnight raw evidence handoff — 23 October 2026

The processed overnight exports and four plots were already included in the
23 October team archive. The subsequent complete raw-results ZIP supplies the
source `record.json`, `result.json` and Grid logs in their original campaign
directories. These files are now included in this checkout. Verify them with:

```bash
python3 analysis/check_overnight_raw.py
```

The import script below is for copying from the original COSMA working
directory when needed. Campaign-level Slurm accounting was not included in
the supplied ZIP and must be obtained separately.

## Locate the original source

On COSMA, check the campaign's actual installation directory:

```bash
ls -ld "$HOME/durham_overnight_20261022/cluster-challenge-durham-main/results/dine/grid-overnight-20261022T224854Z"
ls -ld "$HOME/durham_overnight_20261022/cluster-challenge-durham-main/results/dine2/grid-overnight-20261022T224854Z"
```

The runner's default installation path and the exported `SUMMARY.md` agree on
this location. If `DURHAM_OVERNIGHT_DIR` was overridden, locate the directory
before importing; do not reconstruct raw records from CSVs.

## Import without overwriting teammate results

Apply this patch to the current **Git checkout** of the team repository (or
extract its companion ZIP at the checkout root). From that checkout, run:

```bash
bash scripts/import_overnight_raw.sh
```

You can specify the source and destination explicitly:

```bash
bash scripts/import_overnight_raw.sh \
  "$HOME/durham_overnight_20261022/cluster-challenge-durham-main" \
  "$PWD"
```

This imports only the two `results/{dine,dine2}/grid-overnight-...` trees,
plus `overnight-state/accounting.tsv` and `jobs.tsv` when present. Existing
targets are left untouched. It does not submit any jobs or mutate other runs.
The verifier checks every `analysis/overnight-20261022T224854Z/runs.csv`
entry against an original `record.json`, including failures.

If the verifier reports missing files, investigate on COSMA before saying the
entire 97-invocation dataset has been preserved. Keep failures for audit;
analysis already excludes them from numerical conclusions.

## Upload through GitHub as a reviewed change

Use the *actual* Git clone. An extracted RAR alone cannot be pushed because
it has no `.git` history. Check with `git rev-parse --is-inside-work-tree`.
With the team's normal branch policy:

```bash
git status --short
git switch -c work/overnight-raw-20261023
git add scripts/import_overnight_raw.sh analysis/check_overnight_raw.py \
  docs/overnight-raw-handoff.md docs/overnight-raw-audit-20261023.md \
  .gitattributes README.md GITHUB_UPDATE.md docs/part-d.md docs/submission-review.md \
  results/dine/grid-overnight-20261022T224854Z \
  results/dine2/grid-overnight-20261022T224854Z
git diff --cached --stat
git diff --cached --check
git commit -m "data: preserve COSMA Grid overnight raw job evidence"
git push -u origin work/overnight-raw-20261023
```

If `source-accounting.tsv` or `source-jobs.tsv` was imported, stage it
separately with `git add analysis/overnight-20261022T224854Z/source-*.tsv`.
Ask the report owner to review the PR; do not force-push into teammates' work.

Review any raw files for credentials or personal data before uploading to a
**public** repository. Paths, usernames and job commands can appear in logs.
If the raw collection is too large or unsuitable for GitHub, share a private
compressed archive with the team and keep the derived exports in Git.
