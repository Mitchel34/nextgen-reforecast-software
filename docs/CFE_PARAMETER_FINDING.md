# CFE drainage attribute finding

18 September 2026. Status: upstream mapping verified; saved isolated-sensitivity arithmetic independently recomputed; coupled reforecast attribution and deployed-library qualification remain unresolved. The preserved configuration, original research folders and historical dossier are unchanged.

## Verified upstream change

[NGIAB preprocessing PR #74](https://github.com/CIROH-UA/NGIAB_data_preprocess/pull/74/files) merged on 3 February 2025 as `978960e4a2f71125ebf700ddc036026fcbb1f7e6`. Its generator changes the CFE `slope` argument from the hydrofabric attribute `mean.slope` to `mean.slope_1km`. The [relevant commit](https://github.com/CIROH-UA/NGIAB_data_preprocess/commit/48bd640ecc83f78f32aa06f3120039e2e527b651) also changes Noah-OWP slope, coordinates and attribute extraction. The full PR includes other configuration changes. Applying the whole patch would not isolate CFE drainage sensitivity. Exact identities are recorded in [the upstream receipt](evidence/ngiab-pr74.json).

The inspected historical [CFE header](https://github.com/NOAA-OWP/cfe/blob/a349a953ef239ae7470a8365cf614283d7e6ca80/include/cfe.h#L55-L80) describes `slop` as a bottom-drainage modifier. Its [initialization](https://github.com/NOAA-OWP/cfe/blob/a349a953ef239ae7470a8365cf614283d7e6ca80/src/bmi_cfe.c#L3189-L3192) multiplies saturated conductivity, `slop` and timestep length to obtain the primary drainage coefficient. The hydrofabric column names alone do not establish their units, derivation or suitability for every library version. A source gitlink also does not attest the deployed shared library.

## Checked sensitivity evidence

The owner supplied an existing isolated-CFE investigation. We inspected resident artifacts read-only and recomputed percentages from its saved paired CSV. A separate agent independently recomputed the same statistics from the raw run-summary CSV. We did not compile or rerun CFE during this review. Source hashes and verification scope are retained in [the sensitivity receipt](evidence/cfe-sensitivity-review.json); the underlying private bundle has not been deposited with this repository.

The experiment used CFE source `f9182dfb3d81c407c66c5b782114173893c30cf2`, distinct from the historical framework's CFE gitlink and not attested as the production library. Each configuration variant was set before fresh initialization. The warmed scenario applies a 30-mm liquid-water pulse over the first six hours of each week and constant prescribed PET of 0.1 mm/hour. It uses 104 weeks of warmup and 52 weeks (364 days) of evaluation, without Noah-OWP, channel routing, observed weather or observed discharge.

The metric is catchment runoff depth: the driver sums `flux_Qout_m × 1000` in millimetres. The short window is the first 18 hours immediately after warmup, at the synthetic storm onset, not an average over forecast issues or all weekly storms. Each catchment percentage is `100 × (inherited / candidate − 1)`; statistics are unweighted across the 31 Watauga catchments. All 31 paired denominators are positive; none were excluded.

| Saved-output endpoint | Median inherited excess | Catchment range |
|---|---:|---:|
| First 18 evaluation hours | +102.838% | +20.156% to +220.148% |
| Complete 52-week evaluation | +2.485% | +2.114% to +4.186% |

The approximately twofold short-window ratio and much smaller long-window excess are consistent with a substantial change in timing and flow partitioning under this imposed regime. They do not establish a corresponding routed Watauga discharge change, quantify historical forecast bias, demonstrate improved predictive skill, or place a universal bound on long-run sensitivity. The median of catchment percentages is not an area-weighted basin total. The 52-week difference must not be presented as an 18-hour result or vice versa.

## Required next qualification

1. Bind the actual generator revision, hydrofabric version and column metadata, original and candidate values for every catchment, all transformations, generated configuration hashes and deployed CFE library identity. Audit CFE drainage separately from Noah terrain slope and routing reach slope. Do not repair the value by an undocumented angle conversion, division or clipping rule.
2. Preserve the archived baseline. Create separately identified candidate configurations and a separate campaign identity; changed parameters require rebuilding antecedent history from the same original origin. Existing output CSVs or land state cannot be rescaled or reused as a corrected trajectory.
3. Freeze a bounded paired coupled experiment before running it. Hold forcing, issue times, geometry, Noah settings, routing, non-CFE parameters and resources fixed; change only CFE `slop`. Compare independently evolved original and candidate histories. Any branch-only state experiment is a separate treatment.
4. Retain water-budget terms, soil/groundwater storage, surface/lateral/groundwater runoff, routed volumes, event timing and longer windows, with both absolute and relative differences. Parameter sensitivity and workflow equivalence answer different questions: matching serial and branched outputs can reproduce the same configuration error.
5. Add source-field and transformation checks to the future configuration adapter. Current `doctor` verifies identities, not numerical parameter meaning; this requirement is not yet implemented as a validator. Revised profiles must pass their own physical qualification and cannot inherit old output references.

The historical CFE BMI setter for `slope` calls soil-reservoir initialization, which also resets soil storage. A future storm-time parameter perturbation must explicitly account for that state change. The reviewed isolated experiment avoids it by changing the configuration before initialization.

The original [benchmark protocol](../benchmarks/PROTOCOL.md) is amended to require resolving this mapping before release-profile qualification. Historical reproduction remains useful when explicitly labelled as reproduction of the inherited configuration; it does not certify the inherited parameterization as scientifically suitable.
