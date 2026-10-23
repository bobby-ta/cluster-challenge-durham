# Updating the existing GitHub repository

This package was built from teammate snapshot `af91e8a74f9e81cc48db966127bd75ae3d9d8933`
and the separately supplied overnight campaign CSV/figure archive. No GitHub
remote was modified here.

## Safest path using Git

1. In your own current clone, run `git status --short`. If the worktree has
   changes, commit them on their current branch or save a separate backup.
   Do not overwrite teammate work you have not pulled yet.
2. Run `git pull --ff-only` if your branch should include the newest teammate
   commits. If Git refuses, resolve that state explicitly rather than forcing
   a reset.
3. Create a working branch: `git switch -c part-d-overnight-20261023`.
4. Extract the companion **changes-only ZIP** into the top level of the clone.
   It contains paths such as `analysis/collect.py` and
   `analysis/overnight-20261022T224854Z/`, not another nested repository.
   Review overlaps with any teammate files before replacing them.
5. Verify before committing:

   ```bash
   python3 -m unittest discover -s analysis -p 'test_*.py'
   python3 analysis/plot_overnight_exports.py
   git status --short
   git diff --check
   ```

6. Review the teammate collector changes, evidence files, and Part D text, then
   stage only approved changes, commit, and push the feature branch:

   ```bash
   git add README.md GITHUB_UPDATE.md analysis/collect.py analysis/plots.py \
     analysis/test_analysis.py analysis/test_overnight_exports.py \
     analysis/plot_overnight_exports.py \
     analysis/overnight-20261022T224854Z \
     docs/part-d.md docs/slides-D.md docs/submission-review.md \
     report/part-d-insert.tex report/figs/overnight-20261022T224854Z
   git commit -m "analysis: validate and plot Durham overnight Grid results"
   git push -u origin part-d-overnight-20261023
   ```

7. Open a pull request, ask the teammate who owns the report to integrate
   `report/part-d-insert.tex`, and check the resulting two-page PDF. The
   original `report/report.tex` is deliberately **not** overwritten: it
   contains other team members' ongoing sections and layout decisions.

## Two plotting paths

`analysis/collect.py` + `analysis/plots.py` is the repaired **teammate GCC**
pipeline. It now selects tagged Grid scaling runs and retains per-job host,
compiler/runtime and affinity provenance. Recollect before plotting, because
the old `analysis/data/*.csv` lack those new columns.

`analysis/plot_overnight_exports.py` is the **separate overnight Clang**
pipeline. It directly validates the 11 imported CSVs and regenerates four
PDF figures. It does not need access to COSMA and makes no Slurm submissions.

The two build families must not be silently pooled.

## Source evidence limitations

The ZIP includes the overnight derived exports and figures, not original
`record.json`/`result.json`/job logs or the final Slurm accounting. If your
team needs per-run independent verification, export the original COSMA
`results/*/grid-overnight-20261022T224854Z/` files separately and retain
the compiler flags/runtime environments used by that campaign.

The earlier DINE B all-core cache figure partly uses an excluded
half-node SMT run (12200764). Regenerate or remove that panel before final
report submission; see `docs/submission-review.md`.
