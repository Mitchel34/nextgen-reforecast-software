# Separate compatible Noah configuration — 10 October 2026

`watauga-public-rebuild-v2` is a separately identified diagnostic configuration. It changes two Noah model options to the documented defaults of the exact pinned Noah source. Weather, geometry, CFE parameters, routing configuration and runtime bytes remain unchanged. The failed v1 inputs and execution attempts remain preserved. The [adapter](../scripts/public_fixture/repair_noah_compatibility.py), [strict tests](../tests/test_noah_compatibility.py), [new recipe](../fixtures/watauga-public-v2/recipe.json) and [evidence](evidence/watauga-noah-compatibility-v2-20261010.json) record the scientific change explicitly.

The v1 initialization printed a fatal model-option error and stopped, despite returning process status zero. That process status cannot establish model completion. Routing subsequently had no completed land outputs. An independent reference must pass its full expected output axis, timestep and finite-value checks before routing starts or a reference is admitted. No complete physical reference resulted from that initialization.

The configuration generator's current template supplied `stomatal_resistance_option=4` and `evap_srfc_resistance_option=5`, which are incompatible with the pinned Noah component. The [exact namelist reader](https://github.com/NOAA-OWP/noah-owp-modular/blob/0abb891b48b043cc626c4e4bbd0efe54ad357fe1/src/NamelistRead.f90) accepts those fields only in ranges 1–3 and 1–4, respectively. The new revision uses value 1 for both, exactly as declared by [the pinned example namelist](https://github.com/NOAA-OWP/noah-owp-modular/blob/0abb891b48b043cc626c4e4bbd0efe54ad357fe1/run/namelist.input). This is a documented compatibility baseline for deterministic diagnostics, without a claim that those defaults are calibrated or optimal for Watauga.

| Field | Failed v1 value | Compatible v2 value | Pinned interpretation |
|---|---:|---:|---|
| `stomatal_resistance_option` | 4 | 1 | Noah soil-moisture factor for stomatal resistance |
| `evap_srfc_resistance_option` | 5 | 1 | Sakaguchi and Zeng (2009) surface resistance to evaporation/sublimation |
| `canopy_stom_resist_option` | 1 | 1 | Ball–Berry canopy stomatal resistance, unchanged |

These meanings come from [the pinned option definitions](https://github.com/NOAA-OWP/noah-owp-modular/blob/0abb891b48b043cc626c4e4bbd0efe54ad357fe1/src/OptionsType.f90). The soil-moisture factor option must not be mislabeled as the Ball–Berry canopy option.

The preflight checks all **17** model-option fields. The namelist reader contains **16** numeric range guards; the seventeenth field, `crop_model_option`, is restricted to zero by the documented implementation. The adapter also refuses `subsurface_option=3`, which satisfies the numeric range guard but is explicitly documented as unimplemented. It refuses missing, duplicate, unknown or noninteger options. The exact source archive, reader, option definitions and default namelist are hash-bound; the adapter verifies the source guards against its admitted closed option set before writing anything.

| Model option | Pinned numeric range | V2 value |
|---|---|---:|
| `precip_phase_option` | 1–7 | 1 |
| `runoff_option` | 1–8 | 3 |
| `drainage_option` | 1–8 | 8 |
| `frozen_soil_option` | 1–2 | 1 |
| `dynamic_vic_option` | 1–3 | 1 |
| `dynamic_veg_option` | 1–9 | 4 |
| `snow_albedo_option` | 1–2 | 1 |
| `radiative_transfer_option` | 1–3 | 3 |
| `sfc_drag_coeff_option` | 1–2 | 1 |
| `canopy_stom_resist_option` | 1–2 | 1 |
| `crop_model_option` | 0 only, documented implementation | 0 |
| `snowsoil_temp_time_option` | 1–3 | 3 |
| `soil_temp_boundary_option` | 1–2 | 2 |
| `supercooled_water_option` | 1–2 | 1 |
| `stomatal_resistance_option` | 1–3 | 1 |
| `evap_srfc_resistance_option` | 1–4 | 1 |
| `subsurface_option` | 1–3; 3 unimplemented and refused | 2 |

The new private receipt is `.local/public-fixture-20261010/native-admitted-v2/ADMISSION.json`, admission identity `3c55890840e80768bc0647abf04d1b24a6c8bc061fec5a67de875bdc91334dfe`. Its separate scientific configuration identity is `e05ec5ed5ceea3d5894e6691f7120f75aea1db6d951c9585b34b4ea34fd5dee6`. It derives from v1 admission `e878e6697bb1e6f95eadd3d116110873d778c23f9a923db6f4d9daea83fa09d9`.

There are 291 files and 12,250,007 input bytes. Exactly 93 Noah files change two assignments apiece; the other 198 files remain byte-identical. Parent source files, reports and component-source bytes were reverified after the copy. The adapter initializes no models. Seven focused synthetic tests pass, including rejection of both actual invalid template values, every option's range endpoints, documented unimplemented selections, malformed option sets, corrupted sources/parents, unexpected recipe changes and overwrite attempts.

V2 still retains the candidate drainage parameter, unqualified terrain-source derivation, declared radiation sampling, cold initial conditions and full-reach gauge surrogate from the [earlier scientific review](PUBLIC_WATAUGA_SCIENTIFIC_ADMISSION_2026-10-10.md). Supported options alone do not establish state convergence, hydrologic skill, historical causal availability, shared-history recovery or release suitability. A separately frozen v2 protocol and successful complete output acceptance are required before physical references are reported.
