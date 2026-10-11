# Linux diagnostic runtime qualification — 10 October 2026

The immutable exported executable and component image are admitted for the separately frozen public Watauga diagnostic reference experiment. This is execution admission for `linux-arm64-export-image-diagnostic-v1`; the historical runtime profile is unchanged, and a clean reproducible builder and release qualification remain open.

The [runtime admission receipt](evidence/linux-diagnostic-admission-20261010.json) has identity `9f3a32d9bb9cf5214b99bf84e40230a2d83deeeb6c27430bd37f00a9ca02578d`. It contains new inert measurements, exact file identities and source checks. This admission record contains **zero model process invocations**; the subsequent reference experiment has its own protocol, launch ledger and outcome receipt under [the physical reference increment](PHYSICAL_REFERENCE_INCREMENT_2026-10-10.md).

## Exact runtime and application layout

The dedicated ARM64 worker resumed successfully in 36.50 seconds. It retains the earlier isolated configuration: 2 CPUs, 8 GiB memory, no host filesystem mounts, no SSH agent forwarding and a private Docker configuration. The resumed allocation was 4,669,407,232 bytes with 22,762,278,912 host bytes free, within the 12 GiB runtime allocation ceiling and 8 GiB host free floor. Only the dedicated `nrf` profile was operated.

The execution container uses the previously verified image manifest `sha256:2e75ab75ad1ce8de7755b84b1428ace2b99b8a51a2bb07b0b8970f4ddfd62bff`. All 23 compressed layers and 23 uncompressed diffIDs were already verified in the [preceding runtime closure](LINUX_RUNTIME_PROGRESS.md). This increment reused those exact bytes, without network acquisition or compiler invocation.

| Application member | Actual SHA-256 | Binding |
|---|---|---|
| `/tmp/runtime/ngen-shared` | `ee65c7748c4d2a7e9f3900fc3a5e8c16c045db90eb34a9b877b7bcc5dc942132` | Exact preserved exported executable |
| `/tmp/runtime/libiso_c_bmi.so` | `09b65b5c2a76df4e8e9b334b9d3c56f39c327955306085cae692484742dcc162` | Exact preserved exported middleware |
| `/dmod/shared_libs/libcfebmi.so.1.0.0` | `f54e29c81e2b86c0233f2530e929e18fe9226c421225b90263fa8128ec4ae56a` | Digest-verified image member |
| `/dmod/shared_libs/libsurfacebmi.so` | `6e17db8089cfa99e140fb7152c3dbec260c9a38f3bd7d6512e7dd063bec5dc74` | Digest-verified image member |
| `/dmod/shared_libs/libslothmodel.so.1.0.0` | `39884bb6370071c04d318c6563315237e982ec3d8f165e8e2df6db89251d5a42` | Digest-verified image member; `libslothmodel.so` resolves to it |

The two exports are transferred through a 3,891,200-byte private tar with SHA-256 `cb93a22392f181fa17d35e9dcbc82258a5c94693f44530fc78adb4bb2597f01a`, then extracted only under the container's `/tmp/runtime`, with mode `0500`. The public repository contains the recipe and file identities, not the inherited payloads.

The native executable's historical cache disables MPI, Python and integrated routing. The cache and export receipt were rechecked against their preserved SHA-256 identities, and the export receipt binds the exact executable hash. Consequently each logical reference has two explicitly recorded model processes: serial land execution followed by external t-route. The image's built-in native executable is not substituted.

The native argument array is:

```text
/tmp/runtime/ngen-shared
config/public-watauga.gpkg
all
config/public-watauga.gpkg
all
config/realization.json
```

The explicit `all` arguments follow the [pinned NextGen argument contract](https://github.com/CIROH-UA/ngen/blob/9175b640a4e6f1d90e58e0a65662174d08f052ef/src/NGen.cpp). The external routing array is `/ngen/.venv/bin/python -m nwm_routing -f config/troute.yaml`, using the immutable image's routing environment. The [pinned integrated adapter](https://github.com/CIROH-UA/ngen/blob/9175b640a4e6f1d90e58e0a65662174d08f052ef/src/routing/Routing_Py_Adapter.cpp) identifies the corresponding routing entry point; the exported native feature switches require invoking it externally here. Native execution does not embed Python, so this layout needs no newly discovered host interpreter or implicit `PYTHONPATH`.

## Dependency, static table and routing checks

Five `readelf`/glibc loader `--list` checks completed with exit zero: the native executable, exported middleware, CFE, NoahOWP and SLOTH. Every dynamic dependency resolved. Both the executable and NoahOWP resolve `libiso_c_bmi.so` specifically to `/tmp/runtime/libiso_c_bmi.so` under the declared library path. This closes the diagnostic application layout; it does not erase the executable's historical RPATH or establish a portable release installation.

The actual image's static Noah tables all match their independently verified source archive at commit `0abb891b48b043cc626c4e4bbd0efe54ad357fe1`:

| Table under `/dmod/datasets/static` | Bytes | SHA-256 |
|---|---:|---|
| `GENPARM.TBL` | 275 | `f9e821ee1928f3ce121c3e3453e79c16e7c311fb07ad0b3c5925001a60a3d0d3` |
| `MPTABLE.TBL` | 56,019 | `3a285fef1e4b6c6f144025f4a416bc0dced61d672af3210b93270a940e7cfeeb` |
| `SOILPARM.TBL` | 6,557 | `1e2275a32d8cd3b48ca693d22c0816df0013f83b6594ac632716361db337d58f` |

All **47 installed t-route Python source files** in `troute` and `nwm_routing` matched their unique source members at commit `533fbd98362efdafae62392308727de4f0d4cc20`. This includes the HYFeatures network reader used to admit catchment lateral flow, the routing main module and output writer. The routing module imported successfully without calling its routing entry point. The receipt records 62 unique installed package/version pairs, including Python 3.9.21, NumPy 1.26.4, pandas 2.3.3 and netCDF4 1.6.3. This internal routing Python is separate from the public coordinator's Python 3.11+ requirement.

A [separate inert UDUNITS receipt](evidence/udunits-diagnostic-check-20261010.json) verifies the installed numeric conversion needed between Noah infiltration and CFE precipitation. The actual `m/s` to `mm h-1` factor is `3600000.0000000005`, agreeing with the required `3.6e6` factor within double precision; `1e-6 m/s` becomes `3.6 mm h-1`. The reciprocal conversion and unchanged `m/s` evaporation rate also passed. This uses the installed UDUNITS library and default six XML database members, all SHA-256 bound in the receipt, following the [official C API](https://docs.unidata.ucar.edu/udunits/current/udunits2lib.html). The [probe source](../scripts/runtime/probe_units.py) matches the executed source hash. It calls no native, BMI or hydrologic function. An initial overly exact Python floating point assertion failed; that source and failed observation are retained, then the numeric check passed at relative tolerance `1e-15`. The existing runtime admission identity is unchanged.

The [independently authored qualifier](../scripts/runtime/qualify_export.py) accepts only the declared local Unix Docker endpoint, exported hashes, immutable image and source-bound static/routing members. Five targeted refusal tests verify rejection of corrupt exports before launching a process, nonlocal endpoints, symlink leaves/parents and oversized files before reading them. Those are software tests, not physical experiments.

## Enforced bounds and remaining evidence

The inert qualification used the exact subsequent container layout: a read-only root, no network, all capabilities dropped, no new privileges, 2 CPUs, 8 GiB cgroup memory and 256 processes. The measured cgroup values were `cpu.max=200000 100000`, `memory.max=8589934592` and `pids.max=256`. Writable filesystems are bounded tmpfs mounts: `/tmp` 64 MiB with execution permitted, `/work` 128 MiB without execution, and `/work/job/outputs` 1 GiB without execution. Each probe has a 60-second host timeout and force-removes its specifically named container if the probe times out. The model experiment separately enforces its combined job deadline, output limit and launch allowance.

The native library path is `/tmp/runtime:/dmod/shared_libs:/usr/local/lib:/usr/lib64`. OpenMP, OpenBLAS and MKL thread counts are fixed at one, and Python bytecode writes are disabled. No host dataset, library or runtime mount is admitted.

The following remain release gates: a complete compiler/development dependency content lock, a reproducible clean native builder, component source/options/toolchain-to-binary attestations, licensed artifact redistribution, numerical branching/recovery/transfer evidence, and independent researcher reproduction. The currently admitted runtime has immutable export/image execution provenance. It must not be described as a newly compiled public runtime or a physically equivalent release profile. Scientific fixture admission and reference-output integrity are separate receipts; parameter suitability, forecast skill, spinup convergence and performance improvements are not established by these inert checks.
