# Linux runtime closure progress — 10 October 2026

A dedicated Linux ARM64 worker now boots, the exact historical component image is available, and the exported historical executable resolves its required middleware in a bounded inert loader check. **The complete native build and first physical experiment remain unqualified.** This advances RF-008 and UO-04/05 without changing the historical runtime profile, Watauga recipe, numerical tolerances or experiment budget.

The [observation receipt](evidence/linux-runtime-closure-20261010.json) records fresh measurements, preserved failures and remaining gates. The [recovered build options](../native/RECOVERED_BUILD_OPTIONS_20261010.json) are a partial historical recipe. They do not replace the incomplete [build recipe](../native/BUILD_RECIPE.md), [first physical experiment](FIRST_PHYSICAL_EXPERIMENT.md), or [runtime qualification contract](RUNTIME_QUALIFICATION.md).

## Established in this increment

| Deliverable | Fresh evidence | What it establishes |
|---|---|---|
| Isolated worker | Colima 0.10.3 / Lima 2.2.0, VZ, Ubuntu 24.04.4, Linux 6.8.0-117, ARM64; 2 CPUs and 8 GiB configured; Docker 29.5.2 responds | A local Linux execution environment exists; this is not the hosted research service |
| Exact component image | Historical manifest `2e75ab75…` and configuration verified; all 23 compressed layer hashes and all 23 uncompressed diffIDs verified, then imported | The recorded image is retrievable and its privately staged contents are identified |
| Upstream sources | Archives at the exact framework, t-route, CFE, NoahOWP, SLOTH and NetCDF-CXX commits; 1,968 files checked against Git blob identities, with SHA-256 inventories | Those source bytes are available; archives do not implicitly include their gitlinks or prove binary provenance |
| Custom V3 source | Five public preimages and ten resident preserved overlay files match all historical SHA-256 pins; deterministic patch passes `git apply --check`, applies, and final overlay hashes match | The recorded framework overlay can be restored in private staging without writing to the original research copies |
| Historical build evidence | Resident `BUILD_EXPORT.json` and `CMakeCache.txt` recovered with recorded hashes | CMake 3.31.8, Boost 1.86.0, NetCDF-C 4.8.1 and the exact cached feature switches are known; the compiler/development dependency lock is incomplete |
| Exported executable and middleware | Exact `ee65c774…` executable and `09b65b5c…` middleware supplied by the separate Watauga custody lane; both hashes rechecked inside the pinned image | Historical exported bytes are available for inert inspection |
| Inert dependency resolution | `readelf` and the glibc loader's `--list` complete with exit 0; middleware resolves specifically to `/tmp/probe/libiso_c_bmi.so`; all listed dependencies resolve | This layout resolves the required exported middleware; no executable main, BMI model function, routing step or forecast ran |

The worker has no host filesystem mounts, no SSH agent forwarding, no change to the global Docker context and a private Docker configuration. The unrelated `ngiab` and `harmony-lq0` profiles remain stopped. The task uses ignored project staging plus a dedicated short worker directory, whose exact private paths are retained locally. The short directory is needed because Lima resolves aliases before constructing macOS Unix sockets. [Colima configuration](https://github.com/abiosoft/colima/blob/v0.10.3/config/files.go) and [Lima path handling](https://github.com/lima-vm/lima/blob/v2.2.0/pkg/limatype/dirnames/dirnames.go) were checked before setup.

After the coordinator froze the source, all **155 Python tests passed on this Linux ARM64 worker with Python 3.12.3**. The [separate test receipt](evidence/linux-arm64-input-tests-20261010.json) records every transferred source hash and the tar hash. The suite used an isolated guest directory and a service limited to 2 CPUs, 256 MiB and 120 seconds, without installation or host mounts. These are software-contract tests, not model qualification. The worker was then stopped successfully; its disk, exact imported image and configuration remain available for reuse.

## Source and library identity findings

The image's `ngen_url` and `troute_url` files identify exactly the historical framework and external routing commits. Its runtime contains Rocky Linux 9.6, glibc 2.34, GCC-family runtime libraries 11.5.0, NetCDF 4.8.1, SQLite 3.34.1 and UDUNITS 2.2.28. The routing environment has Python 3.9.21, NumPy 1.26.4, pandas 2.3.3 and netCDF4 1.6.3. This older internal routing interpreter is distinct from the public coordinator package's Python 3.11+ requirement. Full installed package metadata is in the receipt; no routing computation was performed.

| Actual component file in pinned image | SHA-256 |
|---|---|
| `libcfebmi.so.1.0.0` | `f54e29c81e2b86c0233f2530e929e18fe9226c421225b90263fa8128ec4ae56a` |
| `libsurfacebmi.so` | `6e17db8089cfa99e140fb7152c3dbec260c9a38f3bd7d6512e7dd063bec5dc74` |
| `libslothmodel.so.1.0.0` | `39884bb6370071c04d318c6563315237e982ec3d8f165e8e2df6db89251d5a42` |

These three files were extracted inertly from a digest-verified OCI layer into private staging; their hashes also match inspection inside the running image. A framework gitlink plus a library hash still does not establish the complete component build attestation.

The image's built-in `libiso_c_bmi.so` has SHA-256 `df6fd63f…`, which differs from the required historical exported `09b65b5c…` middleware. The successful check supplied the exact export explicitly. The executable still records its historical private-build RPATH. Final packaging must preserve deliberate library resolution or introduce and separately qualify changed native bytes.

## Bounds and retained failures

Setup used a 300-second deadline, 2 CPUs, 8 GiB memory, 8 GiB root disk and 4 GiB data disk. The acquisition ceiling was 4 GiB of compressed payload; the combined staging and worker limit was 12 GiB of allocated disk, with at least 8 GiB host free. Verified bulk payloads total 950,649,934 bytes, including the worker image, component image and six source archives. Small metadata requests are separate from that measured bulk total. At receipt creation, combined allocated staging was approximately 4.38 GiB and host free space approximately 17.20 GiB. Setup and import were watched every two seconds; both completed within their declared bounds.

The inert ELF check used the exact image digest, no network, a read-only root, dropped capabilities, no new privileges, 64-process ceiling, 256 MiB memory, 2 CPUs and an 8 MiB temporary filesystem under a 60-second timeout. It completed in 0.172 seconds. This is a dependency inspection duration, not model runtime or an efficiency benchmark.

Two utility mistakes are retained: the imported OCI annotation tag did not resolve through Docker's tag lookup, so subsequent operations used the verified digest; and an embedded Python quotation error caused one package-list subcommand to fail despite the surrounding shell's final success. The package inventory was repeated through a direct Python argument vector and verified separately. Neither failure consumed a physical experiment invocation.

## Remaining build and scientific gates

1. Recover the detailed historical build receipt and build wrapper through permitted resident evidence, or define a separately identified controlled rebuild. The original detailed receipt is dataless; it was not opened or hydrated. Its absence must not be filled with current compiler defaults.
2. Seal the exact compiler, binutils, CMake, Boost headers and all development dependency content. The component image contains runtime libraries but no `gcc`, `g++`, `gfortran` or `cmake` command on its PATH. It is not a complete historical builder.
3. Finish the selected source/dependency graph and component source/options/toolchain/library attestations. The verified NetCDF-CXX submodule supplies the fallback identified in the historical cache; other source gitlinks are not claimed restored or required without inspecting the selected build path.
4. Complete a relocatable installation and application-level library binding, then perform the admitted clean build under the existing 2-CPU, 8-GiB, 30-minute, network-disabled recipe. This increment ran no compiler.
5. Combine runtime evidence with the separately verified Watauga bundle and diagnostic scientific-input admission. Only then review the original 786-hour, two-issue reference experiment for execution. No new physical invocation, shortened history, alternative weather or changed parameter profile is authorized by this receipt.
6. Resolve artifact-specific redistribution terms and the project license before distributing inherited source, binaries, images or data in a release. The public changes here contain metadata and documentation, not those payloads.

For the manuscript, this supports a measured infrastructure and provenance-recovery description. It provides no new clean-build result, hydrologic equivalence, forecast skill, acceleration, recovery, hosted usability or release qualification claim.
