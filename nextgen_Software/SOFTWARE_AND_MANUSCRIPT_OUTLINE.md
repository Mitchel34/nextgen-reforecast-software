# NextGen reforecast generation: software and manuscript concept

**Prepared for:** Mitchel Carson  
**Target journal:** Environmental Modelling & Software  
**Status:** Proposed design and publication outline; not a completed software release or a report of new experiments.  
**Working software name:** `ngen-reforecast` (descriptive placeholder; availability and community naming approval have not been checked).

## Executive recommendation

Develop a reusable, state-aware reforecast campaign tool, separate from HYDRA's forecast-correction models. Its purpose should be to help another researcher specify a watershed, a supported physical realization, historical initialization, archived forecast forcing, and an issue schedule; generate independent historical forecast trajectories; and obtain a verifiable, documented archive.

**Proposed central contribution:** a tested workflow for sharing continuous historical state reconstruction across forecast issues while preserving branch independence, time/forcing provenance, recoverability, and reproducible outputs.

The strongest manuscript would evaluate whether this workflow reproduces a transparent reference implementation, reduces repeated work, survives interruptions without changing the scientific experiment, and can be used by researchers other than its developer. It should not depend on a HYDRA neural model winning or on the raw physical forecast having high skill.

| Research product | Main question | Primary evidence |
|---|---|---|
| Proposed software paper | Can other researchers construct auditable reforecast campaigns efficiently and correctly? | Numerical equivalence, branch isolation, recovery, resource use, transfer and independent execution |
| HYDRA hydrology paper | When do external corrections improve discharge forecasts and hydrologic behavior? | Forecast skill, information ablations, temporal evaluations, events and observation robustness |

The reforecast archive may support both papers. Their contribution statements, principal experiments, and main figures should remain distinct, and shared software/data/methods should be cross-referenced.

**Important precedent:** Patel et al. (2025) already published *NextGen In A Box (NGIAB): Open-Source containerization of the NextGen framework to enable community-driven hydrology modeling* in this target journal. This is evidence of topical fit and a direct reason not to pitch another generic NextGen installation or automation wrapper. [S1–S3]

<!-- PAGE -->
## 1. Journal positioning and the existing ecosystem

### Recommended article identity

Plan a full research article centered on software design and evaluation, accompanied by an openly archived versioned implementation and executable examples. Treat the manuscript as an argument about a reusable computational method, not an expanded README or a dataset announcement.

The journal's indexed scope includes advances in environmental modelling and software. Its full current author guide could not be retrieved in this review. Exact article-category options, length limits, abstract/highlight rules, mandatory availability wording, and submission declarations therefore require a final check; this outline does not certify compliance with them. [S1]

### Reuse rather than reproduce the surrounding infrastructure

| Existing project | Established role in maintainer documentation | Recommended relationship |
|---|---|---|
| NextGen / Community NextGen | Engine and component framework used by the project | Pin the tested source/build; isolate and document the native reforecast extension |
| NGIAB | Containerized NextGen deployment; local/cloud and HPC distributions | Reuse a compatible environment; a stock image must not be assumed to contain custom hooks [S3] |
| DataStreamCLI | Preprocessing-to-execution workflow; integrations with NGIAB, forcing tools and evaluation | Build an adapter or proposed extension, rather than another general simulation launcher [S4] |
| ForcingProcessor and NGIAB Data Preprocess | Catchment forcing conversion, hydrofabric preparation and run configuration | Reuse qualified capabilities, retaining source/time/unit identities [S5–S6] |
| NextGen Research DataStream | Repeated research forecasts with publicly available configuration, forcing and output resources | Cite, compare scope and coordinate integration; do not imply that reproducible NextGen forecasting is new [S7] |
| TEEHR ecosystem | Hydrologic evaluation tools | Provide an export adapter after interface verification; avoid building another evaluation platform [S3, S7] |

Public documentation establishes substantial overlap in automation and reproducibility. It does **not**, by itself, establish whether the exact multi-year shared-history/independent-branch contract proposed here is absent from current upstream code. Record compared versions and ask maintainers before making a priority claim.

### Defensible novelty boundary

The strongest potential contribution is the combination of explicit temporal semantics, efficient state reuse, branch-isolation verification, recoverable campaign execution and evidence-bearing archive outputs. Process forking, containers, scheduling, hashing, reforecasts and metadata are not individually new. Whether their implementation here constitutes a sufficiently distinct advance depends on comparison and evaluation.

If existing community tools already provide the same contract, contribute the missing capabilities upstream and publish the demonstrated methodological improvement, rather than manufacturing a separate platform for branding.

<!-- PAGE -->
## 2. What exists and what still needs to become reusable

The supplied code review establishes a genuine historical-branch workflow. In the preserved native runtime, the parent is checked to be single-threaded, routing state is snapshotted, a child is forked, the child selects forecast forcing and starts an independent routing process, and the parent waits for an isolation acknowledgement before advancing. Read-only file descriptions are reopened rather than merely duplicated. This is more than an outer loop over a model executable. [P2–P3]

| Existing evidence | Implication for a public tool | Remaining qualification |
|---|---|---|
| Live land-state inheritance and routing snapshot/restore | A useful kernel can be extracted rather than reinvented | Independent numerical reference, supported component combinations and fork-safety tests |
| Two physical domains and three gauge outputs | Demonstrates the motivating regional use case | Configuration-only transfer; nested gauges are not separate executed basins |
| Versioned source and runtime receipts, custom source overlay | Enables provenance reconstruction | Complete source-to-binary attestations and a clean build recipe |
| Per-issue/daily preservation and checksummed records | Starting point for an auditable archive | Transaction semantics, corrupted-output tests and external reproduction |
| A preserved runtime contract describing replay-based recovery | Recovery need not require a universal component serializer | Bind claims to actual executed receipts for the final runtime version |
| Retained numerical/forcing exceptions | Can become transparent configuration and diagnostics | Remove site-specific hidden assumptions; do not silently repair them |

The manuscript's current realization couples Noah-OWP-Modular, CFE and SLOTH with t-route, and has specific routing and assimilation restrictions. It covers 424 unique catchments in two domains; the 73-catchment South Fork area is nested within the 393-catchment New River domain, while Watauga contains 31 catchments. These are the initial supported profile and demonstrations, not evidence of universal NextGen compatibility. [P1, sections 2.1–2.2; P4]

### The most consequential existing limit

A complete portable land-state checkpoint is not established. The preserved v2 contract instead describes recovery by replaying the same historical forcing from a bound origin, while reusing verified committed forecasts and suppressing their re-execution. That is a legitimate design with potentially substantial recovery cost. It is not equivalent to instantaneous restoration of all model components. [P2, section 2; P5, recovery section]

The contracts and audits were inspected; their historical runtime experiments were not rerun for this outline. Development-stage contracts are not automatically proof of the final production implementation. The next agent response should resolve that version/evidence mapping.

<!-- PAGE -->
## 3. Software scope and the researcher experience

### Product promise

Given a supported model profile, a domain, historical and forecast forcing sources, an initialization origin, and a historical issue schedule, the tool will construct a traceable collection of independent forecasts and a report explaining exactly how it was produced.

The initial target user is a hydrologist comfortable with a configuration file or notebook but not with patching C++/Fortran interfaces, handling child-process file descriptors, or repairing interrupted batch campaigns.

### A deliberately narrow first release

Support the existing qualified CFE/Noah/SLOTH/t-route profile, deterministic hourly branches to eighteen hours, existing-data and approved-download preparation paths, a documented Linux execution environment, and both a small example and the two existing domains. Permit other horizons, realizations and execution targets only through explicit capability checks. Gauge observations should be optional for archive generation and separate for evaluation; lack of USGS targets must not delete valid physical forecasts.

Do not make version 1 a new hydrologic engine, calibration package, public warning system, continental hosting service, graphical modelling workbench or ML training suite. Candidate A/B postprocessors should consume its outputs through a stable adapter, not become dependencies of the generator.

### Proposed command-line interface — not implemented commands

```text
ngen-reforecast init --example watauga-small
ngen-reforecast plan campaign.yml --offline
ngen-reforecast prepare campaign.yml
ngen-reforecast run campaign.lock.yml
ngen-reforecast status RUN_ID
ngen-reforecast resume RUN_ID --strategy history-replay
ngen-reforecast verify RUN_ID
ngen-reforecast export RUN_ID --format parquet
ngen-reforecast report RUN_ID
```

`plan` should report unsupported settings, missing assets, expected issue/lead counts, disk estimates and unmeasured costs without launching scientific work. `prepare` may fetch data only with explicit authorization and byte limits; it must accept already-held files. `run` binds an immutable resolved configuration and an execution budget. `resume` reports its state-reconstruction strategy and reserve before restarting. `verify` reports exactly which checks passed, failed or remain untested.

The report should include a provenance summary, coverage by issue/lead, component/runtime identities, forcing substitutions and affected lineage, recovery events, validation outcomes, resource measurements, and draft Methods facts. Unknown items must remain unknown. A generated report is not a certification of forecast skill.

**Practical usability target:** another researcher completes the small tutorial and a configuration-only variation without the author's private filesystem, cloud account, Codex conversation or credentials. Set timing/resource targets after benchmarking, not as invented product claims.

<!-- PAGE -->
## 4. Architecture and scientific contracts

### Recommended modules

| Module | Responsibility |
|---|---|
| Campaign specification and planner | Validate domain, dates, horizon, realization, initialization, forcing policy, resource budget and output policy; create the expected-output ledger |
| Domain/configuration adapter | Consume prepared hydrofabric or existing subsetting tools; resolve gauge/reach mappings; preserve parameter provenance; deduplicate compatible nested outputs |
| Forcing adapter and cache | Identify exact historical and forecast sources; map units and interval support; validate coverage; cache by source and transformation identity |
| Historical-state runtime | Advance one historical trajectory per compatible domain/realization/state policy; expose qualified issue boundaries |
| Branch execution adapter | Inherit or reconstruct issue state, select forecast forcing, isolate routing and outputs, validate terminal clocks |
| Campaign controller and recovery | Bound concurrency, handle interruptions, record attempts and commit verified issues without overwrite |
| Archive, verification and reporting | Produce versioned data, provenance, checks, summaries and optional evaluation exports |

Use Python for the public orchestration interface and retain a narrowly scoped native runtime adapter for capabilities that cannot be implemented safely outside NextGen. Prefer a maintained hook or small version-pinned patch series over a permanently diverging copy of the engine. Keep provider and scheduler interfaces replaceable, but implement only interfaces actually exercised.

### Time and state are the central scientific contract

Let historical state X(t) be generated from a declared origin using historical forcing H. At issue t_i, forecast state begins at the same physical model time and advances under forecast forcing F_i. The forecast branch never updates the continuing historical state.

```text
Historical state: X(t0) --H--> X(t1) --H--> X(t2) --H--> ...
At each selected ti:
    branch starts from X(ti)
    branch advances using Fi to ti + horizon
    branch outputs are independent of all later history and sibling branches
```

Distinguish source-file label, interval start/end, forecast issue, lead, target valid time, publication time where known, and retrieval time. For accumulated/averaged forcings, the interval is part of the data, not a guess based on a filename. Never relabel future retrospective weather as historical forecast meteorology.

A fixed hydrologic realization does not establish an unchanged atmospheric forecast system over all archive years. Preserve forcing-source versions and known transitions. Reconstructed historical states are also not archived operational analysis states, and a specified spinup interval is not proof of convergence. [P1, section 2.2]

Sharing applies only when the domain, realization, parameters, forcing treatment and state policy are compatible. Different physical parameterizations cannot silently share one historical state. Nested-gauge deduplication is appropriate only when both outputs truly come from the same qualified physical domain.

<!-- PAGE -->
## 5. State transfer, failure recovery and platform support

### Three distinct capabilities

| Capability | Proposed release treatment | Evidence required |
|---|---|---|
| Live-state branching | Core fast mode for a pinned, qualified runtime | Single-thread preconditions, independent handles/routers, ordering tests and numerical reference |
| History-only replay | Core reference/recovery mode where fully implemented | Identical source/configuration bindings; no silent cold start; verified reuse of committed outputs; measured replay cost |
| Portable component checkpointing | Future adapter, not a blanket promise | Full land/coupler/provider/routing state round trip; clocks and hidden/native state included |

A file containing channel flow, or the variables visible through a BMI interface, must not be described as a complete checkpoint unless completeness has been demonstrated. A source patch and container digest must both be retained when both are necessary to reproduce the runtime. [P2–P5]

### Commit and recovery semantics

Use separate experiment, run and attempt identities. A forecast is committed only after its child exits successfully, required rows and timestamps are validated, numeric checks pass, and checksums are written. Retries may execute work again but must yield one canonical committed result for each scientific issue identity. Partial files must never count as success.

Local publication can use a validated atomic commit mechanism. Object-store backends require their own manifest/commit protocol; local rename assumptions must not be carried over untested. Corrupt or conflicting existing commits should fail verification, not be silently overwritten.

Test child failure separately from parent/host failure. If the parent has already advanced past an issue, re-running that issue requires a qualified state reconstruction path. A completed output archive is not itself sufficient to recreate the lost land state.

### Initial platform recommendation

Release a Linux execution profile with a tested container and a Python client usable from the researcher's laptop. Qualify Linux ARM64 and x86-64 separately. The preserved generation audit identifies a Linux ARM64 image; it does not establish native macOS runtime portability. In particular, the inspected code uses Linux-oriented process/file handling. [P3–P4]

NGIAB already provides Docker and HPC-oriented distributions. Reuse these where compatible, but validate the custom runtime and resources independently. Do not infer compatibility with MPI, arbitrary OpenMP configurations, reservoirs, assimilation or every BMI component. [S3]

Local development on the M1 Pro need not make MLX part of the generator: this software concerns hydrologic execution and data orchestration, not neural fitting. Keep cloud and HPC schedulers as optional adapters. Deterministic recipes and manifests—not an LLM service—should be sufficient to execute the released software.

<!-- PAGE -->
## 6. Archive, provenance and report specification

### Primary dataset

The canonical forecast key should include experiment/realization identity, domain, location/reach, issue time, lead or lead duration, and ensemble member when relevant. An eighteen-hour forecast is a trajectory indexed by issue and lead, not an ordinary single-valued time series. Different issues verifying at the same time must remain distinct.

| Record | Minimum information |
|---|---|
| Forecast row | Location, domain, issue, lead, valid time, discharge, units, realization and forcing references, issue status |
| Issue record | Expected versus generated leads, initial-state lineage, attempt/commit identity, scientific treatment flags, failure or exclusion reason |
| Input manifest | Original object identity, retained bytes/checksum where available, retrieval time, publication/vintage status, interval/units, transformations |
| Runtime lock | Engine revision and overlay; component and routing identities; container digest/architecture; compiler/build options where recoverable |
| Domain record | Hydrofabric version, topology, mapping evidence, contributing areas, parameters and calibration-provenance status |
| Recovery record | Failure boundary, committed outputs reused, state reconstruction method, resumed issues, time and resource overhead |
| Verification record | Exact check, reference identity, tolerance, measured discrepancy, outcome and known limits |

Use a documented columnar archive with a simple CSV export initially; add NetCDF/xarray/TEEHR adapters when verified. Preserve native diagnostic outputs for small equivalence fixtures even if production runs retain only selected reaches. Required state/forcing evidence cannot be deleted merely to reduce the output size claimed in a benchmark.

### Reproducibility versus source availability

A URL is a locator, not proof that the original bytes remain available. An object checksum proves identity only when those bytes can be obtained. Distinguish an output-reproduction bundle, a bounded physical-rerun bundle, and a full-campaign reconstruction recipe. State which tier is delivered and which remote resources it requires.

Version a complete, redistributable small example where rights permit. Pin source bodies or provide a documented retrieval path and hash verification. Missing historical forcing should stop execution by default; a permitted replacement policy must be explicit and propagated into downstream lineage. Missing forecast forcing should mark the issue incomplete or excluded, never manufacture zero forcing silently. Historical imputation may affect later states beyond the edited window. [P1, section 2.2]

### Generated researcher report

Produce a human-readable report and matching JSON facts: study definition; physical components; initialization; forcing/time conventions; expected/generated/verified issue counts; input gaps and substitutions; source/build provenance; numerical verification; failures/recovery; compute/storage; and limitations. Observation matching is a separate report layer with its own quality and availability rules.

Use version identifiers, licenses, machine-readable citation metadata, detailed provenance and references to dependencies as release criteria. These recommendations align with FAIR4RS but do not by themselves demonstrate full FAIR compliance. [S8]

<!-- PAGE -->
## 7. Publication evidence: experiments that matter

The paper needs new software-evaluation evidence. The existing archive demonstrates a motivating use case, not every release claim. No experiments below have been executed as part of this outline.

| Test | Comparison | Evidence to report |
|---|---|---|
| Reference equivalence | Transparent history-to-issue execution followed by forecast forcing versus shared-history branch | Exact clock/source agreement and predeclared numeric comparisons at gauges, additional reaches and selected state diagnostics |
| Parent isolation | Historical run with no branches versus historical run with normal and deliberately perturbed children | Parent trajectory unchanged within justified tolerance; later branches unaffected by sibling-only forcing changes |
| Concurrency invariance | Serial versus qualified worker counts and completion orders | Same scientific outputs, bounded memory, no shared-offset or output-collision defects |
| Recovery correctness | Uninterrupted campaign versus controlled child/parent interruption and recovery | Same final key set and values; no duplicate committed issues; recovery strategy and extra work |
| Malformed-input handling | Shifted labels, missing leads, nonfinite forcing, wrong units/configurations, corrupt commits | Expected explicit failures or declared exclusions; no silent successful dataset |
| Efficiency | Supported reference/replay and optimized modes on identical workload/hardware | Initialization, preprocessing, forecast, I/O and recovery costs separated; end-to-end time and completed-issue throughput |
| Transfer and usability | Clean installation and configuration-only change by another researcher | Success/failure, time to first verified forecast, interventions, documentation defects and supported environments |
| Hydrologic demonstration | Existing domains; raw output diagnostics and observation comparisons | Physical plausibility, bias and event behavior without confusing model accuracy with runtime correctness |

### Reference design must not exaggerate the gain

A simple repeated-history implementation is useful as a correctness oracle and an explanation of avoidable work, but can be an inefficient straw-man performance baseline. Also compare the best practical supported serial/state-reuse workflow. If a checkpoint path is available, compare it fairly; if not, mark it unimplemented rather than pretending it is slower.

Conceptually, repeating history to every issue costs approximately the sum of all antecedent-history work plus all forecast work. Shared-history execution incurs one historical pass plus the forecast work and branching overhead. This motivates a benchmark; it does not predict an achieved speedup. For both modes count preprocessing, data movement, startup, storage and failure recovery, not just the inner model loop.

Record CPU core-hours, wall time, actual available cores, compiler/runtime versions, throughput, disk/read/write volumes and whole-job memory. For copy-on-write processes, naive sums of process RSS can double-count shared pages; use a stated whole-job or proportional/unique-memory measurement. Report cold- and warm-cache conditions separately where caching matters. Keep monetary costs as dated measured accounting, not current-price guesses.

<!-- PAGE -->
## 8. A small but convincing demonstration ladder

### First: fast correctness fixtures

Use a deterministic synthetic state model to exercise clocks, branch-only perturbations, out-of-order completion, commit conflicts, and failure cleanup without expensive hydrology. These tests establish runtime mechanics only, not hydrologic equivalence.

Then use a short real-model fixture with the supported realization and actual archived forecast forcing. Include all required histories and output diagnostics. Establish the reference before tuning execution. The preserved runtime contract describes a bounded 20-hour/two-issue Watauga qualification design, but a design document is not a substitute for locating the actual result receipt and the exact version it tested. [P5]

### Second: both existing physical domains

Use the 31-catchment Watauga and 393-catchment New River domains over fixed windows long enough to exercise repeated branches, more than one day boundary, routing, archive publication and recovery. A seven-day window is a reasonable proposed starting workload, subject to the fixture's measured budget. The two New River gauges share one run. [P1, Table 1]

Test at least one quiet interval and one rapidly changing flow interval when available from held inputs. Increase worker count only within a measured capability envelope. Do not infer large-domain performance or correctness from the small fixture.

### Third: independent replication and transfer

Have a researcher outside the original implementation effort create the reference example from the release, then change the time window and a documented configuration option without editing core code. Prefer an additional prepared domain outside the two development domains if it can be obtained within an approved scope. A different gauge inside the same domain is a useful export test, not strong evidence of geographical generalization.

A second compatible physical realization is especially useful if the paper claims extensibility across model combinations. Otherwise narrow the public claim to the tested realization and demonstrate configurable domains, schedules and output selections. Do not make every possible NextGen component a first-release prerequisite.

### Fourth: use the existing archive without pretending it was regenerated

Present the full historical archive as the motivating production case, using its original receipts with exact labels. Existing coverage and timing records may support descriptive evidence. Targeted clean-room verification runs supply stronger controlled evidence for the new release. The paper should distinguish original campaign results, newly replicated fixtures, and projected large-campaign costs.

No need to regenerate the entire multi-year archive merely to prepare an outline. A release paper will, however, require some newly authorized model execution to demonstrate the refactored software and its tests. Existing observations and saved forecasts alone cannot establish that a new public build produces the same results.

<!-- PAGE -->
## 9. Proposed manuscript outline

### Recommended working title

**ngen-reforecast: A state-aware, reproducible workflow for constructing historical NextGen streamflow forecast archives**

Alternative, if efficiency becomes the demonstrated central result: **Shared-history execution for efficient and auditable hydrologic reforecast generation with NextGen**. These are working titles, not claims that the proposed name is available or upstream-approved.

### Abstract architecture

Start with the need for issue-resolved historical forecasts for model evaluation, calibration and postprocessing. Identify the implementation problem: historical initialization, forecast-specific weather, independent branch states, temporal alignment and repeatable campaign recovery. Introduce the software and its supported scope. State the actual equivalence, performance, reliability and independent-use results once measured. End with the enabled research use and explicit limits. Do not insert placeholder speedups or assert a broad compatibility result before it exists.

### Sections and their scientific jobs

| Section | Content and purpose |
|---|---|
| 1. Introduction | Why reforecast archives are useful; why running a retrospective simulation is not enough; adjacent NextGen tools and general forecasting workflows; exact contribution and non-goals |
| 2. Reforecast definition and requirements | Historical-state and forecast branches; issue/valid/availability time; realization identity; expected-output contract; requirements from the original campaign |
| 3. Software design and implementation | Planner and adapters; forcing transformations; state-transfer/runtime mechanism; scheduler, commits, recovery, archive schema and provenance; supported/unsupported configurations |
| 4. Verification and evaluation methods | Independent reference; isolation/ordering/failure tests; hardware and workloads; performance accounting; domains; replication/usability protocol; tolerances |
| 5. Results | Actual correctness outcomes, failures, resource tradeoffs, recovery overhead and independent use; every unsupported claim remains excluded |
| 6. Research demonstration | Reproduce a small regional campaign; illustrate issue–lead outputs and a simple evaluation/export; use HYDRA only as a downstream consumer example |
| 7. Discussion | Which design choices generalize; integration with NGIAB/NRDS; portability and maintenance; initialization/forcing/parameter limits; recovery tradeoffs; comparison with existing tools |
| 8. Conclusions | Supported contributions and limits; what another researcher can actually reproduce |
| Software/data availability and declarations | Versioned source/archive/container identifiers; documentation; licenses and dependency credit; minimal data fixture; benchmark artifacts; limitations; author and AI-assistance declarations as required |

Detailed commands, schema definitions, source inventories, installation troubleshooting, test lists and benchmark receipts belong in documentation and supplements. The paper should explain the important design decisions and evidence rather than enumerate every script.

### Provisional contribution statements

A configuration-driven campaign definition preserving issue–lead and forcing-state lineage; a qualified shared-history execution method that does not alter the chosen physical equations; a recovery protocol with explicit state and output semantics; and a reproducible comparison establishing correctness and practical value. Each statement must be linked to a released feature and an experiment, or removed from the final claims.

<!-- PAGE -->
## 10. Main figures, tables and companion documentation

| Figure | Message |
|---|---|
| 1. Historical spine and independent branches | Distinguish retrospective state reconstruction from forecast meteorology, show no child feedback, and mark the precise issue boundary |
| 2. Ecosystem and software architecture | Existing NextGen/NGIAB/forcing/evaluation tools in neutral styling; new campaign/runtime/provenance responsibilities clearly separated |
| 3. Numerical equivalence and isolation | Reference versus optimized errors, parent and sibling invariance, and clock/source agreement across the bounded fixtures |
| 4. Efficiency and recovery tradeoffs | Completed issues per resource budget, stage-level runtime, memory, concurrency and interruption overhead; no invented scaling curves |
| 5. Archive and scientific use | An issue–lead coverage view, single-issued hydrographs and provenance trace to the original forcing and state lineage |
| 6. Independent reproduction/transfer | Environments and scenarios attempted, completed tasks, interventions and limitations; use measured outcomes rather than an unsupported ease-of-use claim |

Useful main tables are an ecosystem/capability comparison, supported runtime profile, experimental workload/hardware matrix, and verification outcomes. A command-line screenshot or decorative dashboard should not replace numerical evidence.

### Software documentation should be a separate deliverable

The user guide should cover installation, a small worked example, configuring another supported domain, forcing policies and gap handling, runtime limits, interruptions and recovery, output interpretation, and how to generate a citable release bundle. The developer guide should define each adapter, state-transfer guarantees, schema/version rules, test-fixture requirements, and contribution workflow.

A campaign report should be generated from manifests and evidence, while the journal paper should analyze the design across cases. Keep these three documents distinct: user guide, per-campaign report, research article.

### Proposed repository organization

```text
ngen-reforecast/
  src/ngen_reforecast/       # public API, CLI, planner and adapters
  native/                   # version-bound shared-history integration
  schemas/                  # configuration, manifests, output records
  profiles/                 # tested component/runtime combinations
  examples/                 # complete small examples and expected results
  tests/                    # unit, synthetic-runtime and real-model tiers
  benchmarks/               # protocols, manifests, runner scripts
  docs/                     # user, developer and recovery guides
  paper/                    # manuscript sources and figure-generation code
  CITATION.cff
  LICENSE
  pyproject.toml
```

This is a proposed extraction boundary, not a claim that the current project already has this structure. Large data and credentials stay outside the source repository, with versioned example/benchmark deposits and explicit source manifests.

<!-- PAGE -->
## 11. Release plan, governance and acceptance risks

| Milestone | Deliverable and exit condition |
|---|---|
| M0. Evidence and scope | Deployed source-to-repository map, upstream overlap inventory, runtime capability table and rights/dependency inventory |
| M1. Public-core extraction | Clean build with pinned native integration; explicit configuration; no author-specific paths or private services required |
| M2. Small reproducible example | Another machine executes a complete example; identity, clock and numeric checks pass against a declared reference |
| M3. Reliability and benchmark study | Bounded equivalence/concurrency/recovery tests with retained adverse outcomes and resource receipts |
| M4. Transfer and documentation | External researcher trial and configuration-only variation; limitations and maintenance responsibilities documented |
| M5. Release and manuscript | Archived source version, compatible image, minimal data and benchmark artifacts; evidence-linked claims and journal requirements rechecked |

Do not assign calendar promises before the agent establishes which components are already qualified, which can be extracted, and which require native-runtime work. Reuse historical receipts as evidence only when their source/build identities match the released code, or explicitly state the difference.

### Governance and license decisions

Coordinate early with Community NextGen/NGIAB/DataStreamCLI maintainers about package placement, native hooks, interfaces, naming and long-term maintenance. A separate thin package with upstream contributions may be easier to sustain than a large fork, but the correct home depends on actual integration boundaries and maintainer interest.

Inventory licenses and provenance at file, dependency, binary and data levels before selecting the public license. DataStreamCLI currently declares GPL-3.0-or-later; other dependencies have their own terms. Do not copy a permissive license across inherited third-party code without review. No legal compatibility determination is made by this outline. [S4]

Release metadata should identify the exact source tag/commit, version DOI or comparable persistent identifier, container digest, supported platform matrix, data/example identifiers, citation instructions and active maintenance contact. Preserve the paper release even as later versions evolve. [S8]

### Main publication risks and their remedies

**Too much overlap:** a generic wrapper repeats existing NGIAB/DataStreamCLI work. Remedy: compare exact responsibilities and demonstrate a distinct state/history/recovery contribution.

**Strong reproducibility language, weak proof:** a container and hashes are not independent rerun evidence. Remedy: provide a complete small fixture, independent reference and external execution.

**Overbroad compatibility:** the known runtime imposes important component and routing constraints. Remedy: publish a tested profile and require capability tests for every expansion.

**Conflating correct execution with accurate hydrology:** a verified workflow can reproduce a biased realization. Remedy: diagnose the raw outputs honestly and separate runtime equivalence from predictive skill.

**Unmaintainable extraction:** native patches, hidden files and author-specific paths remain necessary. Remedy: keep exact overlays, build recipes, fallback/recovery behavior and a realistic maintainer plan.

**Duplicating the HYDRA paper:** the same archive dominates both results. Remedy: the software paper's main contribution must be its new correctness, efficiency, reliability and researcher-use evidence.

<!-- PAGE -->
## 12. Information needed from the codebase agents

A new full multi-gigabyte review bundle is unnecessary. Request a targeted, read-only software-extraction dossier answering six questions:

**Source ownership:** Which current files implement planning, source preparation, state branching, routing, commits, recovery and reports? Which deployed copies differ from repository files, and which upstream patch is indispensable?

**Qualified state behavior:** Which state-transfer and replay paths were actually executed, on which versions, domains and platforms? Locate the receipts and distinguish tests defined from tests passed. What hidden/native state or process constraints remain?

**Minimum independent example:** What is the smallest complete redistributable fixture, including historical inputs and archived forecast forcing, that a new researcher can run? What exact build, command and expected results are known? Which assets are missing or only remote locators?

**Generalization boundary:** Which gauges, component realizations, horizons, routing modes and hardware architectures work through configuration alone? Which are hard-coded, unsupported or untested?

**Performance evidence:** What measurements exist for history initialization, forecast execution, preprocessing, storage and recovery? Which comparisons are like-for-like? Which claimed savings need a new controlled benchmark?

**Release viability:** What licensing, source-to-binary, packaging, data-rights, iCloud-placeholder, credential and upstream-integration issues need resolution? Who can maintain each required part?

The companion AGENT_INFORMATION_REQUEST.md provides an executable instruction prompt for this dossier. It authorizes new report files only; it does not authorize refactoring, downloads, native builds, model runs, cloud jobs, commits or publication.

### Recommended next decision

Approve the direction as a separate software-methods paper, then resolve extraction and compatibility before expanding features. The best first public result is a small, independently reproducible campaign with an honest recovery story—not a polished interface around an unqualified private runtime.

## Evidence and reference notes

External sources were checked for this outline. Maintainer documentation is evidence of documented behavior, not independent verification of the software. The NGIAB article's bibliographic identity was verified using maintainer citation metadata; its full publisher text was not retrieved. The complete current journal guide was not accessible. New design choices throughout this outline are proposals.

**[S1] Journal scope and guide:** Environmental Modelling & Software, Elsevier/ScienceDirect. Indexed journal scope retrieved; full author guide inaccessible. https://www.sciencedirect.com/journal/environmental-modelling-and-software ; https://www.sciencedirect.com/journal/environmental-modelling-and-software/publish/guide-for-authors

**[S2] NGIAB journal precedent:** Patel et al. (2025), *NextGen In A Box (NGIAB): Open-Source containerization of the NextGen framework to enable community-driven hydrology modeling*. Environmental Modelling & Software 193, 106666. DOI: 10.1016/j.envsoft.2025.106666. Maintainer citation record: https://github.com/CIROH-UA/NGIAB_data_preprocess/blob/main/CITATION.cff

**[S3] NGIAB documentation:** CIROH Hub, *NextGen In A Box*. https://hub.ciroh.org/docs/products/ngiab-ecosystem/ngiab/

**[S4] DataStreamCLI:** CIROH-UA, README and declared license. https://github.com/CIROH-UA/datastreamcli

**[S5] ForcingProcessor:** CIROH-UA, README. https://github.com/CIROH-UA/forcingprocessor

**[S6] NGIAB Data Preprocess:** CIROH-UA, README. https://github.com/CIROH-UA/NGIAB_data_preprocess

**[S7] NRDS:** Laser, Patel and Vemula (25 March 2026), *The NextGen Research DataStream (NRDS): A Reproducible Numerical Prediction System for Accelerating Research to Operations in Hydrology*, CIROH institutional technical article, not a peer-reviewed journal paper. https://hub.ciroh.org/blog/nextgen-research-datastream-april-2026/

**[S8] Research software principles:** Barker et al. (2022), *Introducing the FAIR Principles for research software*. Scientific Data 9, 622. https://doi.org/10.1038/s41597-022-01710-x

**[P1] Supplied manuscript:** HYDRA_WRR_DRAFT.docx, especially sections 2.1–2.3 and 5.5. Historical research configuration, not a new public software validation.

**[P2] Prior independent review:** HYDRA_independent_review/HYDRA_CODE_REVIEW.md, sections 1–2. Scoring and code-review evidence; no new physical replay in that review.

**[P3] Runtime source:** SOURCE_EVIDENCE_EXCERPTS.md, E1; original member evidence/nextgen-shared-build.jUE2nu/ngen-v3-day01/include/shared_history/Runtime.hpp.

**[P4] Generation audit:** HYDRA_review/docs/REFORECAST_AND_DATA_AUDIT.md in the supplied 20260917T233206Z core archive. Source/receipt inspection, not a new simulation.

**[P5] Preserved runtime contract:** HYDRA_review/evidence/NextGen_Reforecast/native/shared_history_driver/V2_RUNTIME_CONTRACT.md, dated 5 September 2026. Development-stage interface and qualification boundary; actual final-version claims require matched receipts.

SOURCE_INSPECTION_NOTES.md in this concept package records narrow archive excerpts and SHA-256 identities for P4/P5. It intentionally does not repackage the complete codebase or proprietary/private materials.
