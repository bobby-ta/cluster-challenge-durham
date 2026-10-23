#!/usr/bin/env bash
# Copy Kai's original 22 October COSMA overnight evidence into a team checkout.
# Does not run jobs, delete files, overwrite existing output, or push to GitHub.
set -euo pipefail

campaign=20261022T224854Z
source_repo="${1:-$HOME/durham_overnight_20261022/cluster-challenge-durham-main}"
target_repo="${2:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}"

if (( $# > 2 )); then
    printf 'Usage: bash scripts/import_overnight_raw.sh [overnight-source-repo] [team-target-repo]\n' >&2
    exit 2
fi

if [[ ! -d "$source_repo" ]]; then
    printf 'Source repository does not exist: %s\n' "$source_repo" >&2
    printf 'Check: ls -ld "$HOME/durham_overnight_20261022/cluster-challenge-durham-main"\n' >&2
    exit 1
fi
if [[ ! -f "$target_repo/analysis/overnight-$campaign/runs.csv" ]]; then
    printf 'The target has no matching overnight export runs.csv: %s\n' "$target_repo" >&2
    printf 'Apply the existing Part D analysis update before importing raw evidence.\n' >&2
    exit 1
fi

source_repo=$(cd -- "$source_repo" && pwd -P)
target_repo=$(cd -- "$target_repo" && pwd -P)
if [[ "$source_repo" == "$target_repo" ]]; then
    printf 'Source and target are the same directory; nothing to import.\n' >&2
    exit 1
fi

# Preflight both directories before copying either one.
for node in dine dine2; do
    source_dir="$source_repo/results/$node/grid-overnight-$campaign"
    if [[ ! -d "$source_dir" ]]; then
        printf 'Missing raw directory: %s\n' "$source_dir" >&2
        exit 1
    fi
    count=$(find "$source_dir" -type f -name record.json | wc -l)
    if (( count == 0 )); then
        printf 'No record.json files found in %s\n' "$source_dir" >&2
        exit 1
    fi
    printf 'Found %s raw %s job records.\n' "$count" "$node"
done

for node in dine dine2; do
    relative="results/$node/grid-overnight-$campaign"
    if [[ -e "$target_repo/$relative" ]]; then
        printf 'Already present, leaving unchanged: %s\n' "$relative"
        continue
    fi
    mkdir -p -- "$target_repo/results/$node"
    cp -a -- "$source_repo/$relative" "$target_repo/results/$node/"
    printf 'Copied: %s\n' "$relative"
done

# Preserve campaign-level Slurm accounting independently of the team's logs.
for filename in accounting.tsv jobs.tsv; do
    source_file="$source_repo/overnight-state/$filename"
    target_file="$target_repo/analysis/overnight-$campaign/source-$filename"
    if [[ -f "$source_file" && ! -e "$target_file" ]]; then
        cp -a -- "$source_file" "$target_file"
        printf 'Copied: analysis/overnight-%s/source-%s\n' "$campaign" "$filename"
    fi
done

python3 "$target_repo/analysis/check_overnight_raw.py" "$target_repo"

if [[ -d "$target_repo/.git" ]]; then
    printf '\nGit changes to review before staging:\n'
    git -C "$target_repo" status --short -- results/dine/grid-overnight-$campaign \
        results/dine2/grid-overnight-$campaign analysis/overnight-$campaign
else
    printf '\nThe target has no .git directory. Copy these files into your actual Git clone before committing.\n'
fi
