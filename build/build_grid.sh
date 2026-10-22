#!/bin/bash
# Build Grid + Benchmark_Grid with aportelli/grid-benchmark (the harness the UK NNSS
# benchmark uses, pinned to the same commits).
#   build/build_grid.sh <dine|dine2> <config> [njobs]
# <config> is a name from build/systems/cosma/grid-config.json.
#
# Pixi downloads the toolchain, so run the bootstrap on the login node (it needs internet).
# The compile is heavy: either run it on the login node with a modest njobs, or prepare on the
# login node and compile in a job (no internet needed once the Grid source is cloned):
#   PREPARE_ONLY=1 build/build_grid.sh <node> <config>       # login: pixi env + Grid clone/bootstrap
#   scripts/submit.sh dine build -- <node>:<config> ...       # job: compile + install
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

GRID_SRC="$ENV_DIR/build/Grid/$CONFIG"
GRID_PREFIX="$ENV_DIR/prefix/grid_$CONFIG"
# The steps of grid-benchmark's build-grid.sh, split so the clone (internet) can happen on the
# login node and the compile in a job. Same configure options, same prefix layout.
grid_env() {  # load env.sh and the config's "env" block into this shell
  set +u; source "$ENV_DIR/env.sh" "$CONFIG"; set -u
  ENTRY=$(jq ".configs[]|select(.name==\"$CONFIG\")" "$ENV_DIR/grid-config.json")
  [[ -n $ENTRY ]] || { echo "error: no config $CONFIG"; exit 1; }
  eval "$(jq -er '.env|to_entries|map("export \(.key)=\"\(.value|tostring)\"")|.[]' <<< "$ENTRY")"
}
grid_prepare() {
  git clone https://github.com/paboyle/Grid.git "$GRID_SRC"
  git -C "$GRID_SRC" checkout "$(jq -er .commit <<< "$ENTRY")"
  (cd "$GRID_SRC" && ./bootstrap.sh)   # downloads Eigen
}
grid_compile() {
  local args; read -r -a args <<< "$(jq -r '."config-options"' <<< "$ENTRY")"
  rm -rf "$GRID_SRC/build" "$GRID_PREFIX"
  mkdir "$GRID_SRC/build" && cd "$GRID_SRC/build"
  ../configure --prefix="$GRID_PREFIX" --enable-gparity=no --enable-fermion-reps=no \
    --enable-zmobius=no "${args[@]}"
  make grid-config
  make -j"$NJOBS" -C Grid
  make install -C Grid
  mkdir -p "$GRID_PREFIX/bin" && cp ./grid-config "$GRID_PREFIX/bin"
  cd "$SRC"
}
if [[ ! -d $GRID_SRC ]]; then
  ( grid_env; grid_prepare )
fi
[[ -n ${PREPARE_ONLY:-} ]] && { echo "prepared $GRID_SRC"; exit 0; }
# Skip Grid if it is already installed (e.g. rerunning after a Benchmark_Grid failure).
if [[ ! -x $GRID_PREFIX/bin/grid-config ]]; then
  ( grid_env; grid_compile )
  # A new Grid invalidates the old benchmark objects (build-benchmark.sh reuses its Makefile).
  rm -rf "$ENV_DIR/build/Grid-benchmarks/$CONFIG" "$ENV_DIR/prefix/gridbench_$CONFIG"
fi
# Both nodes share $SRC; only its one-off autotools step must not race.
( flock 9; [[ -f configure ]] || ( set +u; source "$ENV_DIR/env.sh" "$CONFIG"; ./bootstrap.sh ) ) \
  9>"$GRID_ENV_ROOT/src/.benchmark.lock"
./build-benchmark.sh "$ENV_DIR" "$CONFIG" "$NJOBS"

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
