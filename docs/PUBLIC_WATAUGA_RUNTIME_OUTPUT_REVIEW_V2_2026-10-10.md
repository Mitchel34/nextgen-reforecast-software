# Independent runtime and output review of the second Watauga diagnostic

All three new serial jobs completed their land and external routing stages. An independently authored offline reviewer verified the preserved receipts, inputs and complete output axes. The outputs are admitted as diagnostic reference material with explained upstream unit-interface warnings. This is not scientific or public-release qualification.

The sealed [review receipt](evidence/public-watauga-runtime-output-review-v2-20261010.json) has identity `ca9b6c2f7ee71bd0d89ede40b3d88ddcdb0a54a3487947e2c64aba3f03130c3a`. Its [reviewer](../scripts/runtime/review_physical_outputs.py) imports none of the executor, normalizer or reference auditor. Review used preserved local artifacts and made zero model invocations or changes to frozen sources, inputs, runtime, or original research folders.

## Checks and disposition

| Case | Catchment rows × 15 fields | Nexus rows | Routing rows × 3 variables | Preserved raw files | Recorded model memory peak |
| --- | ---: | ---: | ---: | ---: | ---: |
| History: 786 hours | 24,366 | 9,432 | 292,392 | 44 | 364,023,808 bytes |
| Issue 2022-01-01 23:00Z: 785 hours | 24,335 | 9,420 | 292,020 | 44 | 361,238,528 bytes |
| Issue 2022-01-02 00:00Z: 786 hours | 24,366 | 9,432 | 292,392 | 44 | 360,800,256 bytes |

The reviewer independently checked all 291 case input files against the admission inventory; canonical seals for the protocol, admission, freeze, launch reservations, host receipts, process receipts and normalization receipts; and the frozen byte identities of every reference tool and the private host orchestrator. Six ordered model-process reservations match the native and routing receipts. Each process returned zero with complete native output, unchanged inputs and no termination or postlaunch verification error. Native outputs remain unchanged after routing. Every preserved log and raw output matches its receipt binding.

For 31 catchments and 12 nexuses per case, all native interval-start timestamps, step indices, row widths and complete lengths are correct. Every value is finite; catchment runoff and nexus flow are nonnegative. The routing coordinates contain all 31 admitted waterbody features and every 300-second interval end. In-image normalization reports the qualified environment's netCDF4 **1.6.3** and NumPy **1.26.4**. The frozen normalizer source matches the executed source binding in every receipt.

A second reader, host h5py **3.16.0** with NumPy **2.5.4**, independently inspected the raw NetCDF/HDF5 coordinates, units, float32 fields and missing-value sentinels. Every flow, velocity and depth value in all **876,804** normalized rows exactly matches the corresponding raw float32 value: **zero mismatches**, without a numerical tolerance. The different reader was used only for review; it did not modify runtime dependencies or execute a model.

Actual Docker inspection and Linux cgroup receipts verify the immutable ARM64 image, two-CPU quota, 8 GiB memory and swap ceiling, 256 PID ceiling, no network, read-only root, dropped capabilities, no new privileges, no host mounts and the three admitted tmpfs limits. Model-stage PID peaks were nine; all memory-limit/OOM event counts were zero. Recorded combined logical-job durations were 15.65, 15.53 and 17.80 seconds, all below 1,800 seconds. Host storage/free-space receipts remained inside the agreed bounds; all three container stop/remove receipts completed. Recorded resource peaks precede normalization, so a separate normalization peak is not claimed.

## Unit-conversion warning investigation

Native stderr is approximately 40 MB per case. Every conversion warning is explained by the frozen source and configured variable set; none is discarded or suppressed.

| Warning | History | Issue 23Z | Issue 00Z | Explanation per catchment-hour |
| --- | ---: | ---: | ---: | --- |
| Unable to convert `m` to `1` | 341,124 | 340,690 | 341,124 | 14 meter-valued CFE outputs |
| Unable to parse output units `none` | 48,732 | 48,670 | 48,732 | Two zero-valued SLOTH-to-CFE inputs |
| Unable to parse input units `none` | 24,366 | 24,335 | 24,366 | One CFE runoff-scheme code |

These are exactly **17 warnings for every catchment-hour**. The remaining nine distinct messages in each native log are UDUNITS XML definition-override notices. There are no other distinct native messages and no failed QINSUR or EVAPOTRANS conversion reported.

The exact source path is:

1. At NGen commit `9175b640a4e6f1d90e58e0a65662174d08f052ef`, `Bmi_Multi_Formulation.cpp:294–320` serializes the configured output variables through `get_var_value_as_double`. `Bmi_Multi_Formulation.hpp:564` requests literal units `1` from the nested provider. The source-bound CFE commit `a349a953ef239ae7470a8365cf614283d7e6ca80`, `src/bmi_cfe.c:245–260`, declares all 14 physical output fields in **meters** and `SURF_RUNOFF_SCHEME` in `none`.
2. NGen `Bmi_Module_Formulation.cpp:169–210` reads the original scalar, attempts conversion, logs the exception, and returns that **same scalar** on failure. The warnings concern output serialization, not successful conversion to dimensionless quantities. CFE output units in the protocol must therefore be taken from the pinned BMI metadata; meter-valued data were preserved without an array reinterpretation or scale change.
3. CFE input metadata at `src/bmi_cfe.c:316–321` declares Schaake ice in `m`, matching its SLOTH declaration. Xinanjiang ice fraction and soil-moisture profile are declared `none`, while SLOTH declares `1`. NGen `Bmi_Module_Formulation.cpp:676–680` requests each receiver's declared unit before setting that input, accounting for the two output-unit parse warnings.
4. Every frozen realization sets both affected SLOTH fields to exactly **0.0**, with no input aliases. At SLOTH commit `48cd8082878fdb8a6f0e2337a5b375be5b71384c`, `src/sloth.cpp:42–46` obtains inputs solely from aliases, `:216–232` copies configured values, `:239–241` changes only time during update, and `:411–412` creates an alias only when supplied. Their fixed zero values follow from the source and immutable configuration. They were **not directly instrumented at runtime**; this is an explicit source-bound inference.
5. Noah commit `0abb891b48b043cc626c4e4bbd0efe54ad357fe1`, `bmi/bmi_noahowp.f90:645–647`, declares QINSUR and EVAPOTRANS in `m/s`; CFE requests `mm h-1` and `m s-1` respectively. The separate [inert UDUNITS receipt](evidence/udunits-diagnostic-check-20261010.json) proved the required factor **3.6 × 10⁶** and identity conversion in the pinned runtime. No corresponding conversion failure occurs in any native log. This does not directly measure every runtime flux conversion.

The review receipt binds the bytes and source commits of every file used in this trace. The staged historical framework includes declared shared-history overlays: `Bmi_Multi_Formulation.cpp` and `CsvPerFeatureForcingProvider.hpp` differ from the pinned upstream archive, while `Bmi_Multi_Formulation.hpp` and `Bmi_Module_Formulation.cpp` are byte-identical to it. Source review found the output access and conversion-fallback paths unchanged; the CSV exception belongs to the explicitly enabled shared-history mode, which these serial references do not use. The trace describes those source paths and their agreement with the actual warning counts; it does not supply a missing binary build attestation. The existing historical binary/source provenance and clean-build limitations still apply. Literal dimensionless output requests and invalid `none` unit labels require a coherent upstream interface repair before release. Any repaired configuration or model must receive a new experiment identity; these completed reference bytes stay intact.

## Limits carried forward

These checks establish complete and preserved diagnostic output, finite values, exact routing normalization and an explained warning inventory. They do not establish drainage/terrain parameter validity, cold-state convergence, forecast skill, historical causal weather availability, exact gauge-segment equivalence, shared-history branching, checkpoint completeness, speedup or equivalence to original E03. The declared radiation sampling and full-reach gauge-surrogate conventions remain. Clean-build/compiler attestation and redistribution rights remain separate release gates.

The independent reviewer also passed targeted corrupt-seal and symlink-evidence refusal checks. No additional worker or model process was required for this review.
