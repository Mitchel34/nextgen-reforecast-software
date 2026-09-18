# Pinned native build recipe — incomplete and not executed

This is a staged build specification, not a claim that a clean build works. The first implementation has executed no compiler, container, model or dependency installation for the native runtime. The coordinator observed a Docker CLI but no responding daemon on the development host. The offline doctor does not query or activate it.

## Recorded identities

| Artifact | Historical identity |
|---|---|
| NextGen | `CIROH-UA/ngen` at `9175b640a4e6f1d90e58e0a65662174d08f052ef` plus the explicitly hashed V3 overlay |
| t-route | `CIROH-UA/t-route` at `533fbd98362efdafae62392308727de4f0d4cc20` |
| Component image | `awiciroh/ciroh-ngen-image@sha256:2e75ab75ad1ce8de7755b84b1428ace2b99b8a51a2bb07b0b8970f4ddfd62bff` |
| Executable | `ee65c7748c4d2a7e9f3900fc3a5e8c16c045db90eb34a9b877b7bcc5dc942132`, 3,813,528 bytes |
| Fortran BMI middleware | `09b65b5c2a76df4e8e9b334b9d3c56f39c327955306085cae692484742dcc162`, 74,504 bytes |
| Historical build-export receipt | `932193ac1481273b565b41a0969bfe3a39bee0953698766b6fb2c2110088d40d` |
| Historical CMake version | `3.31.8`; exact compiler and dependency versions are not yet closed |

The historical framework gitlinks identify CFE `a349a953ef239ae7470a8365cf614283d7e6ca80`, NoahOWP `0abb891b48b043cc626c4e4bbd0efe54ad357fe1` and SLOTH `48cd8082878fdb8a6f0e2337a5b375be5b71384c`. These identify source references. They do not attest that the shared libraries inside the image were built from those references.

The five pristine source hashes and ten modified/new source hashes are in the runtime profile. The overlay includes five changed framework files and five `include/shared_history/` headers. Building the upstream commit without that overlay would create a different runtime. The older V2 executable `f4d469…` and V2 `Runtime.hpp` `75969a…` cannot substitute for the V3 artifacts.

## Dependencies to close before compilation

1. Obtain an authorized complete source bundle, including the exact pristine commit, all submodule content, the V3 overlay and a deterministic patch application process. Verify each preimage before applying changes and verify all modified-file hashes after application. The public profile currently binds selected files, not the complete source tree.
2. Seal exact compiler/binutils/CMake, libc, Fortran runtime, Boost, NetCDF, SQLite, UDUNITS and `iso_c_fortran_bmi` identities. The preserved CMake cache reports GCC-family paths and CMake 3.31.8, but not a complete reusable dependency lock. Do not fill unknown versions with current defaults and call that an exact rebuild.
3. Seal the external routing environment, including t-route, Python, NumPy, pandas and compiled dependencies, plus the routing service with SHA-256 `e772e3812f00c22a3926d7a56726ae03ed4b75a22494c4f4889c67d956aff50b`.
4. Bind all three physical component libraries (`libslothmodel.so`, `libsurfacebmi.so`, `libcfebmi.so.1.0.0`) to source, options, toolchain, runtime dependencies, library hashes and notices. The historical framework build disabled external model builds, so it cannot supply this evidence.
5. Verify the image's Linux ARM64 manifest and retained layers against its recorded digest. A digest string alone does not prove retrievability, installed content or permission to redistribute that content. Record an artifact-specific dependency and notice inventory.

## Bounded build stages

The proposed first qualification build uses a local Linux ARM64 worker, two reserved CPUs, 8 GiB memory and a 30-minute wall-time limit. These are proposed ceilings, not measured sufficient resources. Exceeding a ceiling is a recorded failed attempt; increasing it requires an updated declared recipe. The recipe must execute inside the authorized project build area with source and dependency bundles mounted read-only, network disabled during compilation, and all outputs under a fresh build directory. Do not build inside an original research checkout.

The following CMake fragment records known framework options. It is **incomplete and unexecuted** because the remaining options, toolchain, dependency paths, middleware build and complete source lock are not yet sealed:

```text
cmake -S <verified-patched-source> -B <fresh-build-directory>
  -DCMAKE_BUILD_TYPE=Release
  -DNGEN_WITH_MPI=OFF
  -DNGEN_WITH_PYTHON=OFF
  -DNGEN_WITH_ROUTING=OFF
  -DNGEN_WITH_BMI_C=ON
  -DNGEN_WITH_BMI_FORTRAN=ON
  -DNGEN_WITH_UDUNITS=ON
cmake --build <fresh-build-directory> --parallel 2
```

The preserved cache additionally reports NetCDF/SQLite enabled, submodule updates and external model builds disabled, and tests disabled. Recover the exact option names and full CMake invocation from the source and detailed receipt before converting this fragment to an executable build script. The detailed historical build receipt was unavailable in the dossier; no successful command has been inferred.

Capture the complete build command, environment, stdout/stderr, compiler/dependency versions, CMake cache, duration, CPU/memory ceilings and artifact hashes even on failure. Exact rebuilt binary equality is not assumed: if a controlled rebuild produces different bytes, create a separately reviewed identity and qualify its numerical behavior before changing the admitted profile.

## Middleware and runtime closure

The historical executable records RPATH `/work/ngen-v3-day01/extern/iso_c_fortran_bmi/cmake_build`. That is a container build path, not a portable public installation. The next native qualification must inspect its ELF dynamic dependencies and capture the loader's actual resolution to the exported middleware hash above. Presence of a correctly named `.so`, or setting `LD_LIBRARY_PATH` without observing the loader, is insufficient. Decide and document a relocatable layout; if binaries or RPATHs change, record the new identities and qualify them separately.

Run the land process with `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and `NUMEXPR_NUM_THREADS` each set to `1`. Then verify live thread and descriptor ownership as part of real qualification; environment variables alone do not establish safe process branching. The qualified historical scope rejects MPI, embedded Python, built-in routing, multithreaded land execution, waterbodies and assimilation.

Only after build, middleware, component and fixture closure should the complete Watauga bounded reference experiment be executed. Its exact assets and evidence requirements are in [RUNTIME_QUALIFICATION.md](../docs/RUNTIME_QUALIFICATION.md). A build success does not qualify a model run or the manuscript's performance claims.

Evidence: preserved `SOURCE_VERSION_MAP.json`, `STATE_AND_RECOVERY.md` and `UPSTREAM_OVERLAP_AND_LICENSES.md` in `reports/reforecast_software_feasibility_20260918T045854Z/`. No new native build evidence exists yet.
