#!/bin/bash
# Build Grid + Benchmark_Grid with aportelli/grid-benchmark (the harness the UK NNSS
# benchmark uses, pinned to the same commits).
#   build/build_grid.sh <dine|dine2> <config> [njobs]
# <config> is a name from build/systems/cosma/grid-config.json.
#
# Pixi downloads the toolchain, so run the bootstrap on the login node (it needs internet).
# The compile is heavy: either run it on the login node with a modest njobs, or wrap it in a
# 1 h job on the target queue with njobs=32.
#
# -march is explicit per config (znver2 for DINE, sapphirerapids for DINE2), never native, because
# the login node is a different CPU. Every flag used ends up in build-flags-<config>.txt,
# which grid.sbatch copies into each run directory. The brief wants all optimisation settings documented.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
source "$REPO/config/team.env"
NODE=${1:?dine|dine2}; CONFIG=${2:?config name}; NJOBS=${3:-8}
# Build with the same modules (gcc 14.1 + openmpi) that the jobs load at run time.
set +u; source "$REPO/config/$NODE.env"; set -u
BENCH_COMMIT=c7457a8   # grid-benchmark commit used by uknnss-benchmark-grid

SRC="$GRID_ENV_ROOT/src/grid-benchmark"
ENV_DIR="$GRID_ENV_ROOT/$NODE"
if [[ ! -d $SRC ]]; then
  git clone https://github.com/aportelli/grid-benchmark.git "$SRC"
  git -C "$SRC" checkout "$BENCH_COMMIT"
fi
rm -rf "$SRC/systems/cosma"
cp -r "$REPO/build/systems/cosma" "$SRC/systems/cosma"

cd "$SRC"
[[ -d $ENV_DIR ]] || ./bootstrap-env.sh "$ENV_DIR" cosma
# bootstrap-env.sh copies the config only once; build-grid.sh reads that copy, so refresh it.
cp "$REPO/build/systems/cosma/grid-config.json" "$ENV_DIR/grid-config.json"
./build-grid.sh "$ENV_DIR" "$CONFIG" "$NJOBS"
# Both nodes share $SRC, where build-benchmark.sh runs autotools; don't let two builds race there.
flock "$GRID_ENV_ROOT/src/.benchmark.lock" ./build-benchmark.sh "$ENV_DIR" "$CONFIG" "$NJOBS"

{
  echo "built=$(date -Iseconds) host=$(hostname) node-target=$NODE config=$CONFIG"
  echo "grid-benchmark=$(git -C "$SRC" rev-parse HEAD)"
  echo "grid=$(git -C "$ENV_DIR/build/Grid/$CONFIG" rev-parse HEAD 2>/dev/null)"
  echo "modules=$(module -t list 2>&1 | tr '\n' ' ')"
  echo "cxx=$("$ENV_DIR/prefix/grid_$CONFIG/bin/grid-config" --cxx 2>/dev/null) cxxflags=$("$ENV_DIR/prefix/grid_$CONFIG/bin/grid-config" --cxxflags 2>/dev/null)"
  echo "ldflags=$("$ENV_DIR/prefix/grid_$CONFIG/bin/grid-config" --ldflags 2>/dev/null)"
  python3 -c "import json,sys; c=[c for c in json.load(open('$REPO/build/systems/cosma/grid-config.json'))['configs'] if c['name']=='$CONFIG'][0]; print(json.dumps(c, indent=1))"
  find "$ENV_DIR" -name config.log -path "*$CONFIG*" -exec grep -m3 -E '^  \\$ .*configure|^CXX=|^CXXFLAGS=' {} \; 2>/dev/null || true
} > "$ENV_DIR/build-flags-$CONFIG.txt"
echo "Binary: $(find "$ENV_DIR/prefix/gridbench_$CONFIG" -name Benchmark_Grid -type f | head -1)"
