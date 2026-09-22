# Software and manuscript implementation plan

Approved work direction: 18 September 2026. The owner requested a plan followed by agent implementation toward a completed software product and accompanying manuscript. This advances beyond the completed feasibility-only stage. The original design and dossier remain preserved evidence.

**Updated 22 September 2026.** The additional [technical foundation and software roadmap](docs/source_material/TECHNICAL_FOUNDATION_2026-09-22.md) is preserved verbatim with a checksum. This plan incorporates that direction into the existing public repository rather than creating a duplicate. [Roadmap reconciliation](docs/ROADMAP_RECONCILIATION.md) maps the supplied sections and milestone labels onto current capabilities and the M0–M7 gates below. The [development backlog](docs/DEVELOPMENT_BACKLOG.md) and [manuscript development plan](paper/DEVELOPMENT_PLAN.md) provide the next assignments and acceptance checks.

## Target outcome

Deliver a versioned `ngen-reforecast` package that lets another researcher describe a supported domain, physical realization, historical origin, archived forecast forcing and issue schedule; construct independent forecasts from a continuous historical trajectory; verify outputs and lineage; and recover by explicit history replay. Deliver an Environmental Modelling & Software research-article manuscript whose claims are supported by the released code and retained experiments.

Initial physical qualification scope: Linux ARM64, pinned NextGen V3 integration, SLOTH/NoahOWP/CFE, channel-only t-route, hourly timesteps and eighteen-hour branches, Watauga plus New River with its two nested outputs. The existing offline interface runs on Linux/macOS; this does not qualify native execution there. The product roadmap adds researcher-selected retained leads within 1–18 and issue schedules independent of the hourly model timestep. Explicit irregular issue lists already work in the planner; cadence expansion and retained-lead selection are planned. Complete portable land checkpoints, arbitrary BMI realizations, reservoir/assimilation routing, ML correction and a hosted service are outside the first release.

The primary user is a hydrologist or environmental researcher working with Python, a configuration file or a notebook. The intended product is a campaign specification, reproducible execution and a research-ready archive with a Methods report. Domain preparation, meteorological regridding, general NextGen deployment and downstream evaluation should use compatible ecosystem tools through documented adapters. HYDRA is an optional downstream consumer, not a package dependency or the software paper's success criterion.

## Milestones, dependencies and acceptance

| Milestone | Work and owner | Completion evidence | Dependencies / current status |
|---|---|---|---|
| M0 — Feasibility | Completed dossier: source, state, data, licenses, benchmark evidence | Nine required reports and manifests; preserved read-only sources | Complete; source snapshot is historical evidence, not new-build validation |
| M1 — Installable planning foundation | Planner agent + coordinator: package, strict campaign schema, offline planner, issue ledger, bounded resident-asset checks, CLI, docs and CI | Fresh-environment installation; deterministic plan/ledger; malformed-time/hash/path/profile tests; unavailable assets explicitly block; no implicit model/network action | Implemented; local installation and four-version Linux CI verified; details in implementation status |
| M2 — Runtime and example closure | Runtime agent: pinned source/preimage/build profile, input/runtime verification, exact missing-asset restoration manifest and reproducible build recipe | Complete source/build/dependency lock; artifact hashes; qualified middleware loading; all fixture assets resident and authorized for redistribution; clean Linux ARM64 build | Tooling exists; the 18 September inventory recorded 132 dataless fixture files and no responding local Docker daemon. Recheck residency/environment before native work; component provenance, parameter semantics and data rights remain open |
| M3 — Complete local execution path | Runtime and coordinator: one Watauga campaign, live branch adapter, child isolation, transactional issue commits, status, export and report | Fresh real-reference run; exact clocks/source identities; documented tolerance; retained diagnostics; verified output keys; working user tutorial | Requires M1 + M2; synthetic fixtures test mechanics separately and never stand in for hydrology |
| M4 — Reliability and resource study | Test/benchmark lane: parent/sibling isolation, serial/concurrent invariance, child/parent interruption, replay recovery, malformed inputs and equal-resource measurements | Executed predeclared matrix, full failures retained, no duplicate commits, reference-equivalent outputs, measured replay overhead and whole-job resources | Requires M3; fix workload/resources/tolerances before measurements; historical receipts remain a separate evidence class |
| M5 — Transfer and usability | Runtime + independent reviewer: New River and independent clean-environment reproduction/configuration variation | Both domains verified; nested outputs counted once by domain; independent operator record; explicit supported platform/profile matrix | Requires M3/M4 and complete second-domain assets; another agent on the same machine is not independent researcher reproduction |
| M6 — Manuscript and reproducibility package | Manuscript agent throughout M1–M5: substantive draft, claims register, references, figure/table plan, methods and reproducibility supplement | Every abstract/result/conclusion claim maps to released feature + evidence; figures regenerate from retained measurements; current journal instructions checked; author/declaration details confirmed | Substantive development draft written; experimental results and final claims depend on M3–M5 |
| M7 — Release and submission readiness | Coordinator + author: license/notices, archival deposit, tagged source/image/data, user/developer docs, clean installation and final manuscript review | Release checklist all satisfied, versioned reproducibility identifiers, external reproduction, approved authorship and complete journal package | Distribution rights and final publishing/submission actions must be concrete; no manuscript submission, maintainer messages or paid infrastructure is implied |

## First implementation increment

1. Implement an independently authored, dependency-light Python core for strict JSON campaign input, UTC interval/issue arithmetic, profile restrictions, identity hashes and a bounded offline resident-file inventory. JSON is the first supported interchange; YAML support can be added behind the same schema later.
2. Provide `init`, `plan`, `ledger`, `report` and runtime `doctor` commands as their implementations become available. Unimplemented `run`, `resume` and export functionality must be clearly unavailable. A plan is not permission, launch readiness or evidence of a model run.
3. Bind a historical Linux ARM64 V3 runtime profile to exact source, executable, middleware and image identities. Produce a precise asset-closure and build checklist instead of hydrating or altering source placeholders.
4. Write the article introduction, formal state/time contract, design rationale, evaluation protocol and limitations now. Mark methods not yet implemented as planned and leave results explicitly unmeasured. Maintain a machine-readable claim/evidence register.
5. Integrate and test the package, exercise the CLI on a supplied planning example and adversarial cases, review agent changes, update status and publish a tested progress commit to the existing public repository. Preserve all six original outline files and the completed dossier.

## Contracts that must survive extraction

- Parent historical state at issue I has consumed intervals [origin,I); branch provider labels start at I, and outputs target I+1h through I+18h. A forecast never updates parent history.
- Historical precipitation and forecast rain-rate semantics are distinct. No double conversion, shifted label, implicit imputation or undisclosed source substitution is allowed.
- A domain/state identity includes geometry, realization, parameters, historical forcing/treatments and origin. Nested output gauges do not imply independent domains or authorize sharing different physical configurations.
- A forecast counts as complete only after zero-exit child reaping, key/clock/numeric validation, bound checksums and atomic output publication. A channel snapshot or forecast archive is not a full land checkpoint.
- Recovery preserves original origin and input/runtime identities, verifies existing commits and replays history while suppressing completed issues. Missing/corrupt assets must fail explicitly.
- Historical receipt, new unit test, new synthetic execution, new real-model qualification and independent researcher reproduction are distinct evidence categories.

## Scope and decisions

**18 September parameter amendment:** resolve the [CFE drainage attribute mismatch](docs/CFE_PARAMETER_FINDING.md) during M2 before qualifying the release parameterization. The merged upstream generator replacement and the checked isolated sensitivity motivate this gate; they do not establish a corrected coupled reforecast. Preserve the inherited historical fixture, bind any candidate as a separate configuration, rebuild its antecedent state from the original origin, and predeclare a one-factor coupled comparison. Add source-column/units/transformation conformance to the future configuration adapter; offline file hashes alone cannot satisfy this requirement.

All code, tests, reports, temporary outputs and build products go in this repository or its ignored local directories. Original Reforecast/HYDRA/thesis workspaces remain read-only, including Git metadata, caches and iCloud placeholders. Do not force hydration. Use resident copies with identities from the dossier.

New implementation, ordinary local dependency setup and bounded tests are authorized by the current request. Keep large data/model runs, native compilation, cloud jobs and spending out of the first increment until their exact assets, execution environment and bounded experiment recipe are established. No paid resource has been requested. The 18 September local validation used Python 3.14.7 and found a Docker CLI without a responding daemon. The 22 September roadmap review did not recheck the native environment; real container qualification remains unestablished.

Keep third-party licenses and source ownership visible. Independently authored core code can be developed while distribution terms are resolved. Do not silently copy inherited code/binaries/data into the public repository or select a blanket license for them. No project-wide license is selected in this increment. The final package name, contributor rights, author affiliations, archival target and external reproducer are release decisions, not reasons to block the first implementation work.

## Agent allocation and integration

- **Planner agent:** `src/ngen_reforecast/campaign.py`, campaign schema, example campaign and focused planner tests.
- **Runtime agent:** `src/ngen_reforecast/runtime.py`, historical runtime profile, runtime verification tests, native/build/asset closure documentation.
- **Manuscript agent:** `paper/` and `benchmarks/` only; substantive draft, references, evidence register and bounded evaluation protocol.
- **Coordinator:** CLI, package metadata, user docs, CI, integration tests, code review, validation, status and Git publication. Integrate after each lane reports its stable interface; do not rewrite another running lane's files.

Progress is tracked in `docs/IMPLEMENTATION_STATUS.md`. Completion is determined by the acceptance evidence above, not by generated file count or a passing synthetic demonstration.

## Next development cycle

Use the stable work-package IDs, dependencies and tests in [the backlog](docs/DEVELOPMENT_BACKLOG.md). Work can begin on bounded offline contracts while native assets are being resolved; physical execution remains dependent on M2.

| Parallel lane | First concrete deliverable | Completion evidence |
|---|---|---|
| Campaign experience | Versioned retained-lead selection and schedule expansion, preserving schema 1.0 behavior | Exact issue/lead counts for hourly, sparse and event schedules; valid-time arithmetic; invalid ranges and excessive expansion rejected; reports distinguish retained products from required physical steps |
| Provenance and input semantics | Schemas for source identities, forcing intervals/units, parameter mappings and explicit gap policies | Unknown identities remain unknown; historical and forecast roles cannot be silently substituted; imputation/exclusion lineage is explicit; CFE and radiation questions stay visible |
| Runtime and fixture | Source/build/library closure plus an exact complete qualification fixture | Verified resident inputs, versioned component provenance and bounded reproducible reference recipe; no substitution of production or shorter-history inputs |
| Execution mechanics | Local synthetic process lifecycle, commit validation and replay bookkeeping | Tested child ownership, incomplete-output refusal, duplicate suppression and interruption recovery, labelled as synthetic mechanics |
| Manuscript | Revised framing, methods contracts and a table/figure-to-evidence map | Every claim has an evidence class; result slots remain unmeasured until their experiment receipts exist; supported researcher workflow is distinct from the historical implementation |

The proposed 20-hour/two-issue tutorial is a separate fixture-design task. Its short execution window does not supply antecedent state. Preserve the existing 786-hour Watauga qualification history and the owner-reported July 2018 production origin as distinct experiments. Any shorter tutorial needs an explicit initialization policy and its own expected outputs; it cannot inherit the existing fixture's evidence.

The researcher-facing target workflow is `init → plan → prepare → run → status/resume → verify → export → report`. Today only offline `init`, `plan`, `ledger`, planning `report` and `doctor` are implemented. YAML, locked executable campaigns, physical execution/recovery, output verification and Parquet/NetCDF/Zarr/TEEHR adapters remain backlog items. Reference and optimized execution must share the same scientific configuration and be evaluated separately from any parameter correction.

AGU26 is an optional dissemination opportunity, not an implementation acceptance gate. Confirm event-specific eligibility using [the current source review](docs/ECOSYSTEM_AND_DISSEMINATION.md) before preparing a submission; a late-breaking deadline is not a general reopening for software abstracts. No conference or journal submission is authorized by this development plan.
