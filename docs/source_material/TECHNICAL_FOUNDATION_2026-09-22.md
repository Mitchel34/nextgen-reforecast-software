# NextGen Reforecast Generation: Technical Foundation and Software Roadmap

**Project:** `nextgen_Software` / working name `ngen-reforecast`  
**Purpose:** Research software for constructing reproducible historical NextGen streamflow forecast archives  
**Primary users:** Hydrologists, Earth scientists, environmental modelers, and hydrologic AI/ML researchers  
**Target journal:** *Environmental Modelling & Software*  
**Near-term dissemination target:** AGU26, San Francisco, 7–11 December 2026  
**Report date:** 22 September 2026

## Executive summary

The central opportunity for `nextgen_Software` is not to create another way to install or execute the NextGen Water Resources Modeling Framework. That ecosystem already includes the core `ngen` engine, NextGen In A Box (NGIAB), the NextGen Forcings Engine, DataStreamCLI, the NextGen Research DataStream (NRDS), T-Route, and related preprocessing and evaluation tools. NextGen itself is explicitly a **model-agnostic framework rather than a single hydrologic model**: hydrologic formulations are connected through standardized interfaces and executed over the NextGen hydrofabric.

The software opportunity is instead to make a difficult research workflow substantially easier and more defensible:

> **Given a watershed, a supported NextGen realization, historical meteorological forcing, an archive of forecast meteorology, an initialization policy, and a historical issue schedule, automatically construct a reproducible archive of independent short-range historical forecasts while preserving hydrologic state, forecast-time semantics, forcing provenance, recovery information, and verification evidence.**

This is a **reforecast-generation problem**, not merely a model-execution problem.

Our existing HYDRA/NextGen work has already demonstrated the core mechanism. A continuous historical NextGen simulation reconstructs antecedent hydrologic conditions. At selected historical issue times, an independent forecast branch inherits the physical state at that instant, switches from historical meteorology to the meteorological forecast that was associated with that issue, advances for up to 18 hours, routes the resulting flows, saves the issue–lead forecast, and terminates. The historical parent continues independently and is never altered by its forecast children.

That concept should become the scientific and software foundation of `nextgen_Software`.

The project should therefore be positioned as **reforecast infrastructure for NextGen**, complementing rather than duplicating NGIAB, NRDS, DataStreamCLI, ForcingProcessor, T-Route, and TEEHR. This boundary is particularly important because NGIAB has already been published in *Environmental Modelling & Software* as an open-source containerization and end-to-end deployment solution for NextGen.

---

# 1. National Water Model, NextGen, and reforecasts are different things

A major source of confusion for researchers entering this ecosystem is that the National Water Model, the NextGen framework, a retrospective simulation, an operational forecast, and a reforecast are related but are not interchangeable concepts.

## 1.1 National Water Model

The National Water Model is NOAA's national hydrologic prediction system. Its operational configurations combine meteorological forcing, land-surface/hydrologic processes, channel routing, reservoirs, data assimilation, and other components to produce hydrologic analyses and forecasts.

NOAA currently describes the NWM short-range configuration as cycling hourly and producing deterministic hourly forecasts out to 18 hours, with HRRR/RAP meteorological forcing and initial conditions supplied from the Analysis and Assimilation configuration.

Conceptually:

**meteorological forecast → land/hydrologic response → runoff/lateral inflow → river routing → streamflow forecast**

Operational NWM forecasting therefore benefits from a continuously maintained modeling system and operationally produced initial states.

A researcher attempting to reconstruct a forecast from years ago generally does **not** have that complete operational state available.

That is the fundamental reason a reforecast is difficult.

## 1.2 NextGen

The Next Generation Water Resources Modeling Framework, normally called **NextGen**, is an execution and integration framework rather than one fixed model.

NOAA describes it as language- and model-agnostic. A NextGen **formulation** can contain one or several hydrologic models/modules associated with a basin, and different formulations can in principle be assigned to different portions of a domain.

The framework uses several important concepts:

| Concept | Function |
|---|---|
| Hydrofabric | Defines catchments, river-network topology, nexuses, attributes, and model spatial units |
| Realization | Defines which formulations/components execute and how they are configured |
| BMI | Basic Model Interface used to expose models implemented in C, C++, Fortran, Python, etc. |
| Forcing | Meteorological inputs mapped onto the model's spatial units |
| Hydrologic formulation | Noah-OWP-Modular, CFE, LSTM, or another supported process/model combination |
| Routing | Typically T-Route for converting lateral flows into routed river discharge |
| Time configuration | Defines start, end, output interval, and associated simulation timing |

NOAA's current `ngen` interface therefore expects a hydrofabric, selected catchments/nexuses, a realization configuration, and optionally partitioning/routing configuration.

This architecture is exactly what makes the framework attractive for environmental research: the experiment can vary model components without rewriting the entire water-prediction system.

## 1.3 NextGen is becoming part of the NWM evolution

The published NGIAB paper describes NextGen as the framework intended for the next major evolution of the National Water Model and states that NGIAB contains many of the components expected for NWM v4.

We should therefore be careful with terminology in the software and manuscript:

**NWM** should refer to NOAA's National Water Model system/products.

**NextGen** should refer to the modeling framework.

**Our reforecast** should refer to a research experiment executed using a specifically identified NextGen formulation, parameterization, hydrofabric, forcing archive, and initialization procedure.

We should not describe a research NextGen run as though it reproduces an archived operational NWM forecast unless that equivalence has actually been demonstrated.

---

# 2. What a hydrologic reforecast actually is

A normal retrospective hydrologic simulation asks:

> Given historical weather, what would the model simulate through this historical period?

A reforecast asks something fundamentally different:

> If a forecast had been issued at historical time \(t_i\), what would this model have predicted using only the model state and forecast meteorology associated with that issue?

That creates two dimensions of time:

**Issue time:** when the forecast begins.

**Lead time:** how far into the future the forecast extends.

The corresponding valid time is

\[
t_\mathrm{valid}=t_\mathrm{issue}+L
\]

where \(L\) is the forecast lead.

A reforecast dataset therefore cannot be treated as an ordinary streamflow time series. Multiple historical forecasts may verify at the same valid time because they originated from different issue times.

The fundamental data key should therefore resemble:

`realization + domain + location + issue_time + lead_hour + valid_time`

rather than merely:

`location + timestamp`.

This distinction is essential for forecast verification, AI post-processing, forecast-error prediction, event analysis, and lead-dependent skill evaluation.

---

# 3. The reforecast architecture developed during the HYDRA research

Our existing implementation provides a concrete reference architecture.

The current research configuration reconstructs one continuous historical trajectory and generates independent short-range branches from it. The present realization couples **Noah-OWP-Modular, CFE, SLOTH, and T-Route**. The current regional implementation contains 424 unique catchments: a 393-catchment New River domain containing the nested 73-catchment South Fork study area and a separate 31-catchment Watauga domain. These should be described as our **initial qualified configurations**, not as proof that all NextGen formulations work with the approach.

The conceptual experiment is:

```text
Historical forcing H
        │
        ▼
t0 ───► t1 ───► t2 ───► ... ───► tn
        historical hydrologic state X(t)

                 issue ti
                    │
                    ├──── forecast forcing Fi ───► +1 h
                    │                           ─► +2 h
                    │                           ...
                    │                           ─► +18 h
                    │
                    └──── parent history continues under H
```

The scientific contract is that a forecast begins from the state \(X(t_i)\) reached by the continuous historical model at the issue boundary, while the forecast branch advances under issue-specific forecast forcing \(F_i\). The child branch must not modify the continuing historical state or its sibling branches.

This distinction is arguably the most important concept the public software needs to communicate.

---

# 4. Historical state reconstruction

Historical forecast meteorology alone is insufficient to reproduce a hydrologic forecast.

The model also needs reasonable estimates of antecedent conditions such as soil water, groundwater/storage variables, snow/land states where relevant, runoff-memory states, and channel-routing state.

Our current solution reconstructs those states with a **continuous historical simulation**.

The production experiment begins its continuous history at **18 July 2018 00:00 UTC**, while retained forecasts begin **17 September 2018 00:00 UTC**, producing an adopted 61-day initialization interval. Importantly, this interval is a research convention; existing evidence does not establish universal hydrologic convergence after 61 days.

The public software should therefore expose initialization explicitly rather than hiding it.

A user should be able to specify something equivalent to:

```yaml
initialization:
  origin: 2018-07-18T00:00:00Z
  first_issue: 2018-09-17T00:00:00Z
  historical_forcing: AORC
  state_policy: shared_history
```

The generated report should state the initialization duration while avoiding claims such as "fully spun up" unless the user supplies evidence supporting that claim.

---

# 5. Historical meteorology versus forecast meteorology

This is the second fundamental distinction.

## Historical spine

Our continuous historical trajectory uses **AORC-based catchment meteorology**.

For the existing implementation, the physical weather channels are:

precipitation, 2-m temperature, 2-m specific humidity, eastward and northward 10-m wind, surface pressure, downward shortwave radiation, and downward longwave radiation.

## Forecast branch

At an historical issue time, the branch does **not** continue using AORC.

It switches to archived, issue-specific NWM short-range meteorological fields corresponding to `f001` through `f018`.

This is what transforms the experiment from a retrospective simulation into a forecast reconstruction.

Our inspected implementation explicitly uses archived forecast meteorology for those branches and does not substitute AORC into the forecast period.

This distinction should become a hard validation rule in the software:

> Future retrospective/reanalysis meteorology must never silently replace historical forecast meteorology in a reforecast campaign.

The NextGen Forcings Engine already supports production of compatible forcings from AORC, HRRR, GFS, CFS, and other meteorological products, including catchment-scale CSV/NetCDF outputs. `nextgen_Software` should reuse or adapt these capabilities rather than create another meteorological regridding system.

---

# 6. Exact 1–18 hour temporal semantics

This deserves first-class treatment in the software because an apparently small one-hour error can invalidate an entire forecast archive.

In our current implementation, forecast lead \(k\) uses a runtime forcing row labeled:

\[
t_\mathrm{issue}+(k-1)\mathrm{h}
\]

and produces a routed streamflow target corresponding to:

\[
t_\mathrm{issue}+k\mathrm{h}.
\]

Thus:

| Lead | Forcing interval begins | Forecast verifies |
|---:|---|---|
| 1 | issue + 0 h | issue + 1 h |
| 2 | issue + 1 h | issue + 2 h |
| … | … | … |
| 18 | issue + 17 h | issue + 18 h |

The current archive records `issue_epoch`, `lead_hour`, and `valid_epoch`, with UTC used throughout.

`nextgen_Software` should enforce these semantics centrally rather than leaving them to model-specific scripts.

Every forcing row should retain both its source timestamp and its physical interval semantics.

Every forecast output should retain both issue and valid time.

Every validation procedure should test clocks.

No file name should be treated as sufficient evidence of temporal interpretation.

---

# 7. How the existing state-aware branch mechanism works

The optimized research implementation goes beyond repeatedly launching NextGen from scratch.

At each selected historical issue:

1. The continuous historical parent reaches the precise issue boundary.
2. Current T-Route/channel state is snapshotted.
3. The single-threaded native process forks, which allows the child to inherit the live in-memory land-model state.
4. The child isolates file handles and output writers from the parent.
5. The child switches to the forecast forcing associated with that issue.
6. A new routing service starts and restores the channel snapshot.
7. The branch runs exactly 18 land/routing steps.
8. Its output is validated and recorded.
9. The child terminates.
10. The parent continues its historical simulation and is unaffected by the forecast.

The inspected implementation contains explicit guards checking that parent input positions and routing time have not changed during branching.

This shared-history architecture potentially eliminates a huge amount of duplicated state reconstruction during large reforecast campaigns.

However, it introduces an important portability limitation.

---

# 8. Current state-checkpoint limitation

We do **not** currently have a demonstrated complete portable serialized checkpoint representing every necessary land-model, coupling, forcing-provider, and routing state.

The channel portion can be snapshotted, but the land-model state in the optimized pathway is inherited through the process address space.

Consequently, the current recovery strategy after losing the historical parent is:

**replay historical forcing from a bound origin → skip already verified forecast outputs → reconstruct state until the unfinished issue is reached.**

That is scientifically legitimate if the replay is deterministic and correctly bound to the original configuration, but it is not equivalent to instantaneous restart from a complete model checkpoint.

Version 1 of the software should state this plainly.

Portable complete checkpointing should be treated as a later capability unless NextGen's evolving formulation serialization work provides a sufficiently complete solution.

---

# 9. Customizing a reforecast campaign for 1–18 h research forecasts

The user-facing abstraction should be a **campaign specification**, not a collection of scripts.

A researcher should configure roughly these dimensions:

| Setting | Example |
|---|---|
| Domain | Watauga / hydrofabric subset |
| Realization | Noah-OWP-Modular + CFE + SLOTH |
| Routing | T-Route |
| Historical forcing | AORC |
| Forecast forcing | archived NWM short-range meteorology |
| Initialization origin | 2018-07-18 |
| First retained issue | 2018-09-17 |
| Issue interval | 1 h, 3 h, 6 h, daily, selected events |
| Horizon | 1–18 h |
| Outputs | selected gauges/reaches or domain outputs |
| Runtime policy | shared history / reference replay |
| Evaluation observations | optional USGS streamflow |
| Storage | local filesystem / object-storage adapter |

The forecast horizon should therefore be configurable:

```yaml
forecast:
  min_lead_hours: 1
  max_lead_hours: 18
```

A researcher interested only in 1–6 h prediction should not have to retain 7–18 h products.

Likewise, the issue schedule should be independent of the model timestep. An experiment might generate forecasts hourly, every three hours, at a specific UTC issue hour, or only during selected events.

The software planner should calculate the resulting number of issue–lead forecasts before execution.

---

# 10. Proposed researcher workflow

The product promise already established for this project is appropriate: a hydrologist comfortable with Python, a configuration file, or a notebook should not need to patch C++/Fortran, manage process descriptors, or manually repair interrupted forecast campaigns.

A coherent CLI could therefore be:

```text
ngen-reforecast init
ngen-reforecast plan campaign.yml
ngen-reforecast prepare campaign.yml
ngen-reforecast run campaign.lock.yml
ngen-reforecast status RUN_ID
ngen-reforecast resume RUN_ID
ngen-reforecast verify RUN_ID
ngen-reforecast export RUN_ID
ngen-reforecast report RUN_ID
```

The important feature is not the exact command names. It is that each phase has a scientific meaning.

**Plan** resolves capabilities, issue counts, dates, required inputs, model versions, expected outputs, storage, and computational requirements without running the experiment.

**Prepare** constructs or locates hydrofabric/configuration/forcing assets.

**Run** executes a locked experiment.

**Resume** reconstructs state according to the campaign's declared recovery policy.

**Verify** checks clocks, output completeness, hashes, branch isolation evidence, and numerical requirements.

**Export** converts the archive into researcher-friendly Parquet/NetCDF/Zarr or evaluation formats.

**Report** automatically documents what was actually executed.

---

# 11. Relationship to the existing NextGen ecosystem

This needs to be very explicit in both the README and manuscript.

NGIAB already makes NextGen substantially easier to deploy in Docker, cloud, and HPC environments.

DataStreamCLI already automates substantial preprocessing-to-execution workflows.

ForcingProcessor/NextGen Forcings Engine already transforms meteorological datasets into NextGen-compatible inputs.

NRDS already operates reproducible, open NextGen-based datastreams on AWS, including CFE/Noah-OWP-Modular configurations and an LSTM-based datastream routed with T-Route.

TEEHR already provides hydrologic evaluation infrastructure.

Therefore:

```text
Hydrofabric / domain tools
        ↓
ForcingProcessor / NextGen Forcings Engine
        ↓
NGIAB / NextGen runtime
        ↓
┌─────────────────────────────────────────────┐
│ ngen-reforecast                            │
│                                             │
│ historical-state reconstruction             │
│ issue scheduling                            │
│ state-aware branching                       │
│ historical forecast forcing selection       │
│ issue/lead/valid-time semantics              │
│ recovery + transactional execution          │
│ archive provenance + verification            │
└─────────────────────────────────────────────┘
        ↓
reforecast archive
        ↓
TEEHR / statistics / HYDRA / ML / calibration
```

The project should integrate with that ecosystem rather than replace it.

---

# 12. Recommended software architecture

| Component | Responsibility |
|---|---|
| Campaign planner | Validate dates, horizon, issue schedule, realization, resources, forcing sources and expected products |
| Domain adapter | Resolve hydrofabric subsets, gauge/reach relationships, nested domains and parameters |
| Forcing adapter | Prepare/cache historical and forecast forcing while retaining units, source IDs and temporal semantics |
| Historical-state runtime | Execute one continuous historical trajectory and expose qualified issue boundaries |
| Forecast-branch runtime | Create independent state-aware forecast trajectories |
| Campaign controller | Manage concurrency, retries, commits, interrupted campaigns and budgets |
| Archive/provenance layer | Store issue–lead outputs, hashes, model/source versions and lineage |
| Verification layer | Test coverage, clocks, branch isolation, numerical validity and reproduction |
| Export layer | Produce Parquet/NetCDF/Zarr/TEEHR-friendly research datasets |
| Report generator | Produce a human-readable Methods/provenance/resource report from manifests |

Python should be the researcher-facing orchestration layer.

Native NextGen changes should be kept as small, documented, and version-pinned as possible.

Long term, the preferred outcome would be a maintained NextGen hook or upstream-compatible interface rather than a permanently divergent fork.

---

# 13. Provenance needs to be a product feature

A major scientific contribution of this software can be that provenance becomes difficult to accidentally lose.

Every forecast should be traceable to:

**experiment → run → issue → model build → realization → parameters → hydrofabric → historical forcing → forecast forcing → initialization origin → branch execution → routing → output**

The archive should preserve, whenever available:

- exact NextGen source/tag/commit;
- component versions;
- container digest;
- hydrofabric identity;
- parameter files;
- historical-forcing source;
- exact forecast objects;
- forcing transformations and units;
- issue time;
- lead;
- valid time;
- model/routing configuration;
- initialization origin;
- recovery/retry events;
- checksums;
- execution hardware;
- wall time and CPU usage;
- validation status.

Unknown provenance should be represented as **unknown**, never reconstructed by guessing from calendar dates.

Our own archive already illustrates why this matters: the available NWM grid fingerprints do not constitute a complete authoritative model-release transition history, and shortwave-radiation timing retains an unresolved temporal interpretation.

---

# 14. Forcing gaps and imperfect historical data

Research software must not silently "fix" historical data.

Our existing archive contains documented missing historical-weather inputs in June and November 2024. The current reconstruction records the imputation and conservatively propagates the potential lineage of those modifications; one corrupted archived forecast issue, 15 April 2021 17:00 UTC, was excluded instead of fabricated.

This suggests an important product principle:

**missing, substituted, imputed, rejected, and unavailable are different states.**

The campaign configuration should contain an explicit forcing-gap policy such as:

```yaml
forcing_gaps:
  policy: fail | exclude_issue | approved_imputation
  preserve_lineage: true
```

Every affected output should carry provenance showing which policy was applied.

This is considerably stronger scientifically than allowing missing values to be silently interpolated inside preprocessing scripts.

---

# 15. Reference mode versus optimized mode

A publication-quality implementation should contain two execution concepts.

### Reference execution

For a small campaign, reconstruct each issue independently using an intentionally simple procedure.

It will be computationally expensive, but conceptually transparent.

### Shared-history execution

Advance one historical parent and branch multiple forecasts from that state trajectory.

The scientific publication should test whether the optimized version reproduces the reference version within stated numerical tolerances.

That comparison gives us a stronger manuscript than merely saying the software is fast.

The research question becomes:

> Can shared historical-state reconstruction produce independent historical NextGen forecasts that are numerically equivalent to a transparent reference procedure while substantially reducing redundant computation and supporting reliable recovery?

That is a strong *Environmental Modelling & Software* question.

---

# 16. What should be measured for the software paper

The paper should evaluate four dimensions.

**Correctness.** Forecasts from reference and optimized execution should be compared numerically. Parent-state invariance, sibling independence, forcing identity, issue clocks, lead clocks, routing clocks, and output completeness should be tested.

**Efficiency.** Measure total CPU-core hours, wall time, memory, preprocessing, forcing reads, routing, output storage, and initialization cost. The main comparison should be repeated independent execution versus shared-history branching rather than invented theoretical speedups.

**Reliability.** Deliberately interrupt children, the parent process, output writes, and whole jobs. Confirm that resume/replay produces one canonical committed result per issue and does not silently accept partial files.

**Reproducibility/usability.** Give the released software and a complete small fixture to someone who did not build the system. Have that researcher reproduce the reference archive and modify one supported campaign setting without editing the core source.

Those tests turn a utility into a research contribution.

---

# 17. Initial supported scope

Version 1 should intentionally be narrow.

The existing project design already identifies a sensible first release: the qualified Noah-OWP-Modular/CFE/SLOTH/T-Route profile, deterministic hourly branches through 18 h, Linux execution, prepared or explicitly authorized forcing acquisition, a very small tutorial domain, and the two existing regional domains.

The first release should **not** claim:

universal NextGen formulation support; complete operational NWM reproduction; arbitrary assimilation; arbitrary reservoirs; every routing option; complete portable model checkpointing; nationwide hosted execution; or an integrated machine-learning system.

Those can become future capability profiles.

This narrow scope makes the software substantially more defensible.

---

# 18. Relationship to HYDRA and AI/ML research

`ngen-reforecast` and HYDRA should remain separate products.

`ngen-reforecast` generates the physical forecast archive.

HYDRA consumes the archive.

That means the output schema can support downstream research such as:

```text
(issue, lead, raw NextGen discharge)
        +
antecedent meteorology
        +
recent observations
        ↓
LSTM / Transformer / GRU-Transformer
Mamba-2 / Mamba-Transformer
Chronos / TimesFM / Tesseract experiments
        ↓
predicted forecast error
        ↓
corrected discharge forecast
```

This separation substantially increases the value of the software.

A researcher studying statistical post-processing, deep learning, foundation models, data assimilation, calibration, forecast verification, regionalization, or uncertainty quantification could all use the same physical reforecast archive without adopting HYDRA.

The software paper therefore should not depend on HYDRA outperforming another model.

HYDRA becomes a **demonstration of a downstream scientific use case**, not a required dependency.

---

# 19. Why this fits Environmental Modelling & Software

There is already direct precedent.

Patel et al. published **NextGen In A Box (NGIAB): Open-Source containerization of the NextGen framework to enable community-driven hydrology modeling** in *Environmental Modelling & Software* in 2025. Their contribution centers on making NextGen deployment reproducible across local, cloud, and HPC environments.

That means another generic "we made NextGen easier to run" paper would have substantial overlap.

Our manuscript instead should focus on:

**historical forecast reconstruction rather than general model deployment;**

**state-aware branching rather than ordinary simulation execution;**

**issue–lead temporal semantics rather than normal time-series output;**

**forecast-forcing lineage rather than generic meteorological preprocessing;**

**recoverable multi-year campaigns rather than individual simulations;**

**numerical equivalence and branch-isolation tests;**

and **automatically generated evidence/provenance artifacts suitable for scientific publication.**

That is a considerably more distinct contribution.

A suitable working title remains:

**ngen-reforecast: A state-aware, reproducible workflow for constructing historical NextGen streamflow forecast archives**

---

# 20. Proposed manuscript structure

The eventual *Environmental Modelling & Software* article should be organized around a scientific software argument rather than a long README.

**Introduction** should explain why hydrologic reforecasts are required for forecast verification, post-processing, ML, calibration, and forecast-system research, and why retrospective simulations are insufficient.

**Reforecast definition and requirements** should formally define historical state, issue time, forecast branch, lead, valid time, forcing availability, and realization identity.

**Software architecture** should describe the planner, forcing/domain adapters, state runtime, branch runtime, scheduler, recovery protocol, archive, provenance, and reporting system.

**Verification and experiments** should describe reference execution, optimized execution, numerical tolerances, branch-isolation tests, failure testing, hardware, workloads, and independent reproduction.

**Results** should report correctness, runtime/resource behavior, reliability, recovery cost, and external reproduction.

**Research demonstration** should build a bounded regional reforecast archive and demonstrate an export/evaluation workflow. HYDRA can appear here as one downstream consumer.

**Discussion** should address limitations, operational-state differences, atmospheric forecast-system changes, initialization assumptions, portability, integration with NGIAB/NRDS, and future checkpointing.

**Conclusions** should state only the capabilities established by released experiments.

---

# 21. Development roadmap

The existing milestone structure remains appropriate and should now be interpreted as the route toward both software release and publication:

| Stage | Exit condition |
|---|---|
| M0 — Evidence and scope | Map deployed implementation to repository; establish upstream overlap, licensing and actual supported capabilities |
| M1 — Public core | Clean reproducible build with configuration replacing author-specific paths/services |
| M2 — Reference fixture | Another machine can execute a tiny complete reforecast and match expected outputs |
| M3 — Verification/benchmark | Reference-vs-shared-history equivalence, concurrency, corruption and recovery tests completed |
| M4 — Researcher transfer | External researcher completes tutorial and a configuration-only modification |
| M5 — Research release | Tagged source, container, fixture, benchmark data, documentation and archived DOI |
| M6 — Manuscript | Evidence-linked *Environmental Modelling & Software* submission |

This extends the existing M0–M5 release concept rather than replacing it.

---

# 22. Immediate development priorities for `nextgen_Software`

The highest-value work now is not adding more model formulations.

The priority is turning the existing proven research machinery into a clean scientific contract.

The next implementation cycle should therefore establish:

**Campaign schema → reference fixture → provenance schema → temporal validator → reproducible build → reference executor → shared-history executor → verification suite → restart/replay testing → campaign report.**

Only after those pieces are solid should we substantially expand model combinations or cloud abstractions.

One especially valuable artifact would be a **20-hour / two-issue real NextGen fixture** containing everything required to execute the complete experiment offline or from precisely versioned public assets.

That fixture can become the golden reference for CI, documentation, external replication, and the manuscript.

---

# 23. AGU26 opportunity

AGU26 will be held **7–11 December 2026 in San Francisco**. The normal abstract deadline of 5 August has already passed, but AGU currently lists a **29 September 2026 late-breaking abstract deadline**.

That leaves a very short opportunity to present the reforecast-software work separately or incorporate it into an appropriate existing AGU26 presentation, provided the work satisfies the late-breaking submission requirements.

For AGU, the most compelling visual story would be:

```text
Traditional approach

issue 1:  [rebuild years of state] → 18-h forecast
issue 2:  [rebuild years of state] → 18-h forecast
issue 3:  [rebuild years of state] → 18-h forecast
...

Shared-history approach

historical state ──────────────────────────────►
          ├── issue 1 → 18-h forecast
             ├── issue 2 → 18-h forecast
                ├── issue 3 → 18-h forecast
                   ...
```

Accompany that with measured numerical-equivalence results, resource savings, and a small reproducible user workflow.

The AGU presentation can therefore function as a public research preview, while the journal article provides the deeper software-validation evidence.

---

# 24. Long-term vision

The eventual software should allow an environmental scientist to express:

> "I want historical 1–18 h NextGen streamflow forecasts for this watershed, using this model formulation, over these years, at this issue frequency."

and have the system determine:

the necessary hydrofabric; model configuration; historical initialization; meteorological history; archived forecast forcing; issue schedule; computational plan; restart strategy; forecast archive; validation tests; provenance records; and Methods-ready report.

The researcher should receive not merely a directory of streamflow files but a **scientifically auditable reforecast experiment**.

That is the product.

And that is also the manuscript contribution.

---

## Project definition to carry forward

**`nextgen_Software` should become an open, state-aware reforecast campaign system for the NextGen Water Resources Modeling Framework that enables hydrologists and environmental scientists to construct reproducible short-range historical streamflow forecast archives without having to manually solve historical-state reconstruction, forecast-forcing alignment, branch isolation, campaign recovery, provenance, and issue–lead temporal bookkeeping.**

The first supported scientific profile should reproduce the already developed Noah-OWP-Modular/CFE/SLOTH/T-Route, AORC-history, archived-NWM-forecast, 1–18 h workflow before expanding to additional formulations.

Its research contribution should be demonstrated through **correctness, computational efficiency, reliability, provenance, and independent reproducibility**, not merely interface convenience.