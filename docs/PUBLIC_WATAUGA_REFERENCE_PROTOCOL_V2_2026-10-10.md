# Prospective Watauga reference experiment, version 2

The first independent serial experiment produced no qualified physical reference. The native Fortran component printed `FATAL ERROR model options stomatal_resistance_option should be1-3` and returned process exit code zero through `STOP`; it generated no complete land outputs. The subsequently attempted routing process failed. Version 1 reservations, original protocol/tools, host failure evidence and the third attempt's model receipts/logs remain preserved. The second attempt's output payloads are unavailable because Docker copy failed on tmpfs; that capture loss is recorded explicitly.

Version 2 is a **new prospective scientific configuration**, `watauga-public-rebuild-v2`, with experiment ID `watauga-public-independent-serial-v2`. It is not another run silently substituted into the version 1 identity. The owner authorized runtime/fixture qualification and independent physical references; the separate phase admission records the configuration choice before any new model process starts.

The [machine protocol](PUBLIC_WATAUGA_REFERENCE_PROTOCOL_V2_2026-10-10.json) binds the input admission `3c558908…`, scientific configuration `e05ec5ed…`, runtime qualification `9f3a32d9…`, all seven version 2 tools, full spatial/time axes and per-variable scientific units. Its complete identity is printed in the machine document and externally bound in the freeze receipt. The combined admission and its external frozen SHA remain required before execution.

## Explicit configuration change

Two unsupported Noah fields now use the values in the exact pinned component's `run/namelist.input` example:

| Noah field | Rejected version 1 value | Prospective version 2 value | Pinned supported values |
|---|---:|---:|---|
| `stomatal_resistance_option` | 4 | 1 | 1–3 |
| `evap_srfc_resistance_option` | 5 | 1 | 1–4 |

`stomatal_resistance_option` selects the soil-moisture stress formulation. It is distinct from `canopy_stom_resist_option`, whose value 1 remains unchanged. All remaining 15 model-option fields, initial values, meteorological arrays, CFE parameter files, geometry, origin, catchment/reach axes and runtime component bytes remain fixed. Source-bound preflight checks inspect all 17 model-option fields before admitting this configuration. The selected defaults are documented diagnostic choices; their acceptance by the runtime does not establish a preferred or calibrated hydrologic parameterization.

The [input admission explanation](PUBLIC_WATAUGA_SCIENTIFIC_ADMISSION_2026-10-10.md), version 2 fixture recipe and component-source receipts preserve the complete rationale and source identities. The source is the pinned [NoahOWP component revision](https://github.com/NOAA-OWP/noah-owp-modular/tree/0abb891b48b043cc626c4e4bbd0efe54ad357fe1).

## Zero exit requires complete native output

The version 2 executor checks every native catchment and nexus file after the native process terminates. It requires the complete frozen file axes, all 15 finite CFE variables, every interval-start timestamp and step, nonnegative runoff/nexus flow, and no `FATAL ERROR` in the native logs. A zero exit with incomplete outputs or a fatal log saves a failed receipt and makes the executor return nonzero. The host workflow then stops without reserving or launching routing.

Routing additionally revalidates the complete native output contract and requires the preceding native receipt to state that contract completion succeeded. This second preflight occurs before a routing process can launch. The execution sealer and final output auditor require this completion evidence as well as zero exit, fixed argv, frozen admission, unchanged inputs, matching logs and the durable phase ledger.

## Complete references and units

The three serial cases, cold origin, two 18-hour forecast issues, selected `wb-1017693` reach and full 300 s routed outputs remain as described in the [version 1 protocol explanation](PUBLIC_WATAUGA_REFERENCE_PROTOCOL_2026-10-10.md). Each version 2 job independently replays its antecedent history. Complete arrays are sealed before forecast leads are extracted, and antecedent comparisons use exact equality of each serialized variable in its own units.

The pinned [CFE BMI source](https://github.com/NOAA-OWP/cfe/blob/a349a953ef239ae7470a8365cf614283d7e6ca80/src/bmi_cfe.c) supplies the output-unit declarations and value pointers. The protocol and array artifacts retain metadata for every field:

- `Q_OUT`, runoff components and potential/actual evaporation are water depths in metres for the current 3,600 s land timestep. `Q_OUT × catchment area / 3,600 s` supplies lateral discharge in m³/s.
- **Output `RAIN_RATE` is also current-step water depth in metres**, because its value pointer is `timestep_rainfall_input_m`. Its name does not make it a rate; the meteorological forcing rate is a separate input.
- `GW_STORAGE`, `SOIL_STORAGE` and signed `SOIL_STORAGE_CHANGE` are depths in metres. They are not discharges.
- `SURF_RUNOFF_SCHEME` is a dimensionless integer code, with BMI units declared `none`; `NWM_PONDED_DEPTH` is metres.
- `GIUH_RUNOFF` and `DIRECT_RUNOFF` point to the same current-step direct-runoff quantity. Adding both would double count that component.
- Nexus flows are m³/s. Routed outputs are discharge m³/s, velocity m/s and depth m, on every explicit 300 s coordinate.

No one discharge tolerance is applied to storage or flux-depth variables. Exact serialized-prefix comparisons do not establish spin-up convergence, calibration, forecast skill or restart/state equivalence.

## Separate phase budget

The new phase has its own reservation namespace and permits six planned model processes plus at most three logged repair processes, for a nine-process ceiling. The aggregate actual model-process ceiling across the preserved failed version 1 phase and this phase is 12. Each logical job remains limited to 1,800 s combined land/routing wall time, 1 GiB output, 2 CPUs, 8 GiB RAM and 256 processes, inside a read-only, no-network, no-host-mount container. Aggregate output, staging and free-space limits remain unchanged.

The original Reforecast and historical E03 artifacts remain read-only and retain their identities. This experiment seeks executable diagnostic references for subsequent software verification. Clean-build attestation, scientific release qualification, data redistribution, public hosted execution and manuscript results claims remain governed by their separate evidence requirements.
