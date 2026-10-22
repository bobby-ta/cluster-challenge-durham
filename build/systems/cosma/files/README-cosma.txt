COSMA DINE/DINE2 environment for grid-benchmark (CIUK 2026, Durham subchallenge).
Toolchain: COSMA modules gnu_comp/14.1.0 + openmpi/5.0.3 (sourced from config/<node>.env by
build/build_grid.sh, same as at run time); pixi cpu-linux env supplies autotools, gmp, mpfr, hdf5,
fftw, openssl, zlib (and clang 20 for the *-clang configs). Binaries carry an RPATH to the gcc 14
runtime first, then the pixi lib dir, so they run without sourcing env.sh.
