# Independent physical references for the public Watauga fixture

This is the separately bounded diagnostic experiment authorized by the owner on 10 October 2026. Its experiment ID is `watauga-public-independent-serial-v1`; its input fixture is `watauga-public-rebuild-v1`. The historical E03 assets, protocol, profile and missing-file evidence retain their existing identities. The earlier public fixture preparation recipe also remains unchanged, including its zero-model preparation allowance.

The machine contract is [PUBLIC_WATAUGA_REFERENCE_PROTOCOL_2026-10-10.json](PUBLIC_WATAUGA_REFERENCE_PROTOCOL_2026-10-10.json). Its SHA identity is `1f38dbced75935cb59d2bfb62c272ae250b03a438e889720724837cf58c28ae1`; the exact file SHA is `f12713e6c03ca6a6f3227cc2946f43cc65821d94fb114d4e5a52e4db870afae7`. It binds all reference tools, the new input-contract admission (`e878e669…`), runtime qualification (`9f3a32d9…`), domain and weather preparations. A combined, separately sealed admission and its externally frozen file SHA are required before the first model process.

## Three independently initialized serial jobs

Each job independently starts at `2021-12-01T00:00:00Z` using the same declared cold Noah and CFE values. Each consumes every antecedent hour again. The history case continues with AORC; each forecast case switches to its own NWM short-range issue at the issue time. No land state or routing checkpoint transfers between jobs.

| Case | Antecedent hours | Forecast hours | Total provider hours | Exclusive physical stop | Routing steps, 300 s |
|---|---:|---:|---:|---|---:|
| History | 786 | 0 | 786 | 2022-01-02 18:00 UTC | 9,432 |
| Issue 2022-01-01 23:00 UTC | 767 | 18 | 785 | 2022-01-02 17:00 UTC | 9,420 |
| Issue 2022-01-02 00:00 UTC | 768 | 18 | 786 | 2022-01-02 18:00 UTC | 9,432 |

All cases use the same 31 catchments and 12 nexus IDs frozen in the machine contract. The selected routed output is **`wb-1017693`**, representing the full selected reach near USGS `03479000`; it is a spatial surrogate for the interior gauge. `nex-1017694` is a terminal nexus identifier. It is not interchangeable with the selected routed reach. The conflicting hydrofabric gauge attribute on `wb-1017846` does not select this experiment's output.

## Executables, clocks and complete output arrays

The exact recovered native export has embedded Python and routing disabled. Each job therefore comprises two independently ledgered model processes:

```text
/tmp/runtime/ngen-shared config/public-watauga.gpkg all config/public-watauga.gpkg all config/realization.json
/ngen/.venv/bin/python -m nwm_routing -f config/troute.yaml
```

Both run in the same new isolated job directory. Routing takes each catchment's `Q_OUT` column from `cat-*` output, preserving the catchment-to-reach crosswalk. The pinned t-route depth-to-discharge conversion uses each catchment's area and the 3,600 s land interval. A confluence's aggregated `nex-*` lateral contribution must not be assigned to one arbitrary incoming reach.

The native framework's inclusive last provider label is one hour before the exclusive physical stop. The pinned Noah time-list contract is also inclusive, so its namelist endpoint is the last provider label. The native catchment and nexus CSV timestamps label the interval start, after an update for that interval; canonical valid times add 3,600 s. Routing NetCDF has an explicit seconds-since-origin coordinate at 300, 600, …, the physical stop. Forecast lead `k` selects the routing coordinate equal to `issue + k × 3,600 s`. Position-only slicing cannot substitute for checking these actual coordinates.

All 15 CFE output variables are retained at native output precision 17, including runoff components, potential/actual evaporation, storage and storage change. The auditor requires every catchment row and every nexus row; runoff and nexus flows must be nonnegative, while a storage change may have either sign. Routing retains every 300 s step for all 31 reaches, with finite nonnegative flow, velocity and depth. The raw routing NetCDF values are the pinned writer's float32 serialization. Missing values, shifted clocks, duplicate steps, ragged rows, missing reaches and an absent selected reach refuse reference admission.

The read-only NetCDF adapter writes a portable full-domain CSV and seals its source file, coordinate/variable contracts, adapter identity and exact library versions. The standard-library auditor separately rechecks the complete axes, preserved model receipts and raw source hashes. It then saves full canonical arrays, binds them by SHA and finally extracts the 18 requested leads. These are complete serialized output references; they do not contain a complete land-model checkpoint.

## Bounds, process reservations and failed attempts

The dedicated Linux worker permits at most 2 CPUs, 8 GiB RAM and 256 processes, with a read-only container root, no network, no host mounts, dropped capabilities and no privilege escalation. Each logical job has a combined 1,800 s land/routing deadline and at most 1 GiB output. Aggregate outputs are limited to 4 GiB; runtime/staging remains within 12 GiB, fixture preparation within 2 GiB, and host free space must remain at least 8 GiB. Normalized CSV and canonical arrays have separate 128 MiB read limits. No paid resources are authorized.

The planned work is six model processes: three land and three routing processes. At most three additional logged failed-stage or repair processes are allowed, giving a **nine-process global ceiling**. Every durable reservation precedes launch and consumes allowance even if the process fails before producing usable results. Each repair preserves the failed attempt, logs and inputs. A configuration/runtime adaptation receives a newly sealed revision and admission before another process launches; the scientific origin, parameter bytes, catchment axis and weather preparations stay fixed. Exhaustion or a material scientific change stops this experiment for reassessment.

`execute_stage.py reserve` records the host's global reservation; `execute_stage.py run` checks frozen admission and case input bytes, executes only the fixed native or routing stage and saves its receipt. Its live output-size watch uses metadata only, because hashing a file while the model is writing would create false failures. Complete content hashes are computed after the process finishes. Container creation, transfer, resource enforcement and process shutdown belong to the independently reviewed host wrapper and are bound in the combined admission.

## Acceptance and interpretation

The execution sealer requires separately reserved zero-exit native and routing stages, unchanged input bytes, matching process logs and unchanged raw land/nexus outputs after routing. The output auditor requires this execution evidence before producing any accepted reference. CSVs alone, or synthetic test fixtures, cannot establish a physical result.

The final reference-set checker binds all three complete references and all 36 issue/lead outputs. It compares each independently replayed antecedent prefix against the history run for every catchment variable, nexus flow and 300 s routed value. Comparison uses exact serialized equality; no numerical tolerance is fitted after observing results. Any difference is preserved with its axis and step rather than erased by a convenient tolerance.

This experiment can establish executable diagnostic references and their consistency. It does not establish hydrologic spin-up convergence, calibrated parameters, forecast skill, historical causal availability of currently published archive objects, shared-history execution, restart equivalence, speedup, fault recovery, restoration of historical E03 or a redistributable public runtime. The clean-build/source attestation and unresolved scientific/data redistribution gates remain explicit in the qualification documents and manuscript.

Primary contracts reviewed for this recipe include the pinned [NGen CLI and routing call](https://github.com/CIROH-UA/ngen/blob/9175b640a4e6f1d90e58e0a65662174d08f052ef/src/NGen.cpp), [land output labels and depth/area conversion](https://github.com/CIROH-UA/ngen/blob/9175b640a4e6f1d90e58e0a65662174d08f052ef/include/core/Layer.hpp), [CFE output variables and units](https://github.com/NOAA-OWP/cfe/blob/a349a953ef239ae7470a8365cf614283d7e6ca80/src/bmi_cfe.c) and [t-route coordinate/output writer](https://github.com/CIROH-UA/t-route/blob/533fbd98362efdafae62392308727de4f0d4cc20/src/troute-network/troute/nhd_io.py). Their staged source bytes and qualification receipts, rather than changing branch names, govern execution.
