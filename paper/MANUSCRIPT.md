# Sharing historical state while preserving independent forecasts: a reproducible reforecast workflow for NextGen

**Working research-article draft, updated 23 September 2026.** Target: *Environmental Modelling & Software*. Working software name: `ngen-reforecast`; the name and long-term upstream home are unresolved. Author list, order, affiliations, corresponding author and ORCIDs are pending author confirmation. This is an evidence-bound development draft, not a submission-ready paper or a report of completed new model experiments.

The public planning implementation is being developed independently from the historical runtime described below. Present-tense statements about that runtime refer to inspected preserved source or receipts. Public runtime integration, physical benchmarks and independent reproduction remain future work. Claim identifiers refer to [CLAIMS.csv](CLAIMS.csv); the controlling experiment specification is [the benchmark protocol](../benchmarks/PROTOCOL.md).

The owner's [22 September technical roadmap](../docs/source_material/TECHNICAL_FOUNDATION_2026-09-22.md) supplies product direction and motivating examples. Its capability descriptions and historical examples are not treated as newly verified results. The [manuscript development plan](DEVELOPMENT_PLAN.md) assigns section responsibilities, evidence dependencies and release requirements.

The 23 September [EM&S related-work guide](RELATED_WORK_AND_WRITING_GUIDE.md) adds verified readings and a section-by-section narrative map. The blockquoted drafting guides below are editorial notes, not submission prose or evidence of completed experiments; remove them when preparing the final article.

## Abstract

> **Drafting guide:** R1 Patel, R2 Nassar and R5 Choi (2023). Write last: researcher problem, bounded contribution, evaluation, measured findings and scope. Explain the practical result before implementation detail; retain pending status until results exist. See the [section map](RELATED_WORK_AND_WRITING_GUIDE.md#section-by-section-authoring-map).

Hydrologic reforecasts require repeated predictions initialized from a consistent historical trajectory. Reconstructing that trajectory separately for every forecast can repeat substantial work, but sharing state introduces requirements for clock alignment, process isolation, forcing provenance and recovery. We propose a narrowly scoped NextGen campaign tool that will advance a continuous historical parent, construct independent forecast branches at declared issue times, and publish outputs only after numerical, temporal and transaction checks. Recovery will reconstruct history from the original bound origin and reuse verified forecast commits; it will not require a claim of portable land-state checkpointing. A preserved two-domain application motivates the design, while its measurements remain distinct from validation of the public implementation. The evaluation will compare branches with independent sequential references, test failure and replay behavior, measure execution under equal resource limits, and assess reproduction by another researcher. The expected contribution is a verifiable state-sharing contract and its evaluated implementation. No new physical equivalence, efficiency or usability result is available at this draft stage; those measurements are prerequisites for a final research-article abstract and conclusions.

**Keywords:** hydrologic reforecast; NextGen; state initialization; reproducibility; process isolation; recovery.

## 1. Introduction

> **Drafting guide:** R1/R2 establish existing NextGen workflows; R8 Houtkamp and R9 Swain ground researcher access. Lead with the study a hydrologist wants to perform, then existing solutions and the precise remaining responsibilities. Browser access and automated preparation alone are not new contributions.

A reforecast campaign combines a historical reconstruction with a sequence of counterfactual forecast trajectories. Each issue should begin from the physical state implied by the same antecedent forcing, model parameters and initialization policy. Forecast weather then replaces historical weather within that branch, while the historical trajectory continues independently toward subsequent issues. An archive can contain plausible discharge values even when this separation is violated. Examples include moving a precipitation interval by one hour, inheriting an input-file offset shared with another process, or allowing an incomplete forecast to suppress a later retry. These are scientific reproducibility problems as well as software defects. [C01–C03]

The NextGen ecosystem already provides substantial infrastructure for model execution and research workflows. Patel et al. (2025) describe NGIAB's containerization of NextGen. DataStreamCLI documents a workflow from preprocessing to simulation, and the CIROH description of the NextGen Research DataStream presents a reproducible numerical prediction system built from this ecosystem. These projects establish the context for integration; general automation, container packaging and reproducible NextGen forecasting are not proposed as new contributions here. [C04; Patel et al., DOI: https://doi.org/10.1016/j.envsoft.2025.106666; DataStreamCLI: https://github.com/CIROH-UA/datastreamcli; Laser et al., https://hub.ciroh.org/blog/nextgen-research-datastream-april-2026/]

Nassar et al. (2026) further describe a browser-accessible JupyterHub workflow for NextGen preparation, simulation, calibration and evaluation. Its historical Logan River example establishes a close precedent for remote research access. Our proposed no-code campaign experience must therefore be evaluated through the specific tasks and scientific contracts it supports, rather than presented as the first browser-based NextGen environment. [C44; [Nassar et al.](https://doi.org/10.1016/j.envsoft.2026.107031)]

The narrower research question is whether continuous historical state reconstruction can be shared across forecast issues while preserving a measurable contract for independent branches, recoverable work and source-bound outputs. Sharing live state may avoid repeating initialization, but an efficiency claim requires a fair reference, equal resources and complete accounting. Recovery is also consequential: a routing snapshot alone cannot recreate the hidden state of the land components and their couplers. The software must state which state is retained, which state is reconstructed, and what missing inputs prevent reconstruction. [C05–C07]

We will evaluate five questions. First, do forecast outputs agree with independent references under declared tolerances and exact issue clocks? Second, can a forecast alter its parent or a sibling through memory, routing or external file state? Third, does interruption followed by historical replay preserve the scientific experiment and avoid duplicate committed forecasts? Fourth, what execution and recovery costs occur under fixed resources? Fifth, can an independent operator reproduce the released experiment and can a hydrologist complete the supported browser workflow without local installation or code? These distinct reproduction and usability exercises organize the planned evidence rather than presuppose favorable results. [C08, C45]

The proposed package will expose explicit campaign, runtime and asset contracts while reusing qualified domain preparation, forcing and evaluation tools. Its first physical profile is deliberately restricted. Reusability will be demonstrated within that profile before compatibility is extended. Version identifiers, licenses, dependency relationships and provenance are release deliverables consistent with the FAIR4RS principles; their presence alone will not be treated as proof that another researcher can reproduce a result. [C09; Barker et al., 2022, https://doi.org/10.1038/s41597-022-01710-x]

## 2. Computational problem and scientific contract

> **Drafting guide:** R3 Foroumandi models explicit experiment definition; R6 Essawy clarifies reproduction terminology; R7 Bennett links evaluation to purpose. Define state, intervals and issue/lead keys before mechanisms. These citations do not establish our specific timing rules, tolerances or initialization policy.

This draft uses **NWM** for NOAA's National Water Model system and products, **NextGen** for the modeling framework, and **research reforecast** for an experiment with an explicitly identified realization, parameterization, domain, initialization and archived forecast meteorology. A retrospective trajectory advances under historical meteorology; a reforecast branch advances under the meteorology associated with its historical issue. Using NWM meteorological products does not establish that the research realization reproduces operational NWM initial states or forecasts. This terminology follows the supplied technical brief and the [primary-source ecosystem review](../docs/ECOSYSTEM_AND_DISSEMINATION.md), and defines the study's product boundary. [C37]

### 2.1. Historical state and issue time

Let \(H\) be the initialization origin, \(\Delta t=1\) hour, and \(I_j\) an issue time on the same UTC grid. Let \(\theta\) collect the geometry, physical realization, parameters, component and runtime identities, routing mode, and explicitly declared data treatments. The complete conceptual state \(S_h(t;\theta)\) includes land stores, component clocks, coupler and forcing-provider state, routing state, and any external process or file state needed to continue the trajectory. This definition is a contract, not a claim that every hidden component variable has a portable serializer. [C02, C05]

The historical trajectory follows

\[
S_h(t+\Delta t)=\Phi_\theta\{S_h(t),F_h[t,t+\Delta t)\}.
\]

At issue \(I_j\), the parent has consumed precisely \([H,I_j)\). It has not consumed historical or forecast forcing for an interval beginning at \(I_j\). The branch begins from a continuation-equivalent state \(S_j(I_j)\), uses forecast forcing \(F_j\), and advances according to

\[
S_j(I_j+k\Delta t)=\Phi_\theta\{S_j(I_j+(k-1)\Delta t),F_j[k]\},
\quad k=1,\ldots,18.
\]

The provider label of \(F_j[k]\) is \(I_j+(k-1)\Delta t\), while the output target is \(I_j+k\Delta t\). Issue time, provider interval start and output target will be separate fields. The parent will continue only with \(F_h\); a completed forecast will never update historical state. Exact integer-hour arithmetic and UTC serialization will avoid dependence on daylight-saving transitions. [C02–C03]

Forecast valid time is \(t_{valid}=I_j+L\), where \(L\) is the retained lead. Different issues can forecast the same valid time and must remain distinct records. The intended scientific key therefore includes realization/variant, domain, location, issue, lead and valid time, with a separate run identity for execution provenance. An export indexed only by location and valid time would discard this distinction. Provider interval labels remain a separate validation surface. [C38]

Initialization will be reported as an explicit experimental choice: initial-condition configuration, historical origin, first retained issue and elapsed antecedent history. The supplied roadmap describes a production origin of 18 July 2018 00:00 UTC and first retained issue of 17 September 2018 00:00 UTC, an adopted 61-day interval. Those dates are a reported historical production example, also documented in the preserved dossier; this update does not rerun that campaign or establish hydrologic convergence after 61 days. The separate 2021-origin Watauga qualification candidate in section 4 keeps its original recipe. Neither elapsed duration alone nor successful execution warrants describing a realization as fully spun up. [C39]

### 2.2. Forcing semantics and state identity

The preserved research profile uses different precipitation conventions for history and forecasts. Its historical adapter reads AORC accumulation at the next hourly label and divides once by 3,600 to obtain a rate. Its forecast adapter consumes already decoded NWM rain rates without that additional conversion. Other historical fields use a same-label engineering interpretation, and shortwave temporal uncertainty remains documented. The public adapter will carry these conventions explicitly and test them against source metadata; merely recognizing a column name will not establish a valid conversion. [C10]

A scientific state identity will bind geometry, parameterization, origin, historical forcing and treatments, physical components and routing assumptions. An issue identity will additionally bind its forecast source, source generation, lead coverage and output selection. Shared geometry or overlapping valid times will not authorize sharing scientifically different state. Conversely, nested output gauges can use the same physical parent when all state-defining inputs agree. Outputs will retain their gauge identity without multiplying the number of independently initialized domains. [C11]

Unavailable intervals, nonfinite values, duplicate labels and mismatched source generations will be rejected. Any permitted interpolation or geometry treatment must be an explicit, versioned scientific input. Historical gap treatments that use future information will be labeled retrospective; they will not support a claim about the information available to an operational forecast at issue time. [C12]

Lineage will distinguish historical state inputs from issue-specific forecast inputs and retain source timestamps, represented intervals, units, transformations and exact source identities. Missing, unavailable, imputed, substituted and excluded inputs are different states. A retrospective field must not silently replace missing forecast meteorology. The owner's brief repeats reports of historical weather gaps in June and November 2024 and exclusion of the 15 April 2021 17:00 UTC forecast issue; these are reported historical treatments to be bound to their source and output lineage, not new results or proof of source availability. Atmospheric product versions will remain unknown where exact provenance does not establish them. [C40–C41]

### 2.3. Parameter mapping and scientific variants

> **Drafting guide:** Use R3/R7 for controlled-experiment framing only. The [CFE finding](../docs/CFE_PARAMETER_FINDING.md), its sources and future coupled qualification support this case; none of the selected journal papers validates our proposed mapping correction.

The project owner reports that the existing inputs use `mean.slope` for the CFE drainage parameter. The review verified saved Watauga originals and single-parameter variants against the isolated experiment's input manifest; the original hydrofabric extraction and historical generator/library provenance remain unresolved. Upstream NGIAB preprocessing [PR #74](https://github.com/CIROH-UA/NGIAB_data_preprocess/pull/74), merged on 3 February 2025, changes CFE's `slope` mapping from `mean.slope` to `mean.slope_1km`. Its complete changes also affect Noah terrain slope, coordinates, Noah defaults and partition handling. An isolated CFE-mapping comparison therefore cannot represent the effect of applying that entire PR. The verification record and remaining provenance questions are tracked in [the CFE parameter finding](../docs/CFE_PARAMETER_FINDING.md). [C32–C33]

Parameter-map provenance will be part of the scientific identity. Reproducing the historical profile will test the runtime against that original profile; evaluating an alternative CFE mapping will require a separately identified variant with all other inputs controlled. These answer different questions. A change of parameters can change antecedent state and must not inherit the original variant's recovery identity or numerical-reference acceptance. Historical configurations and the feasibility dossier remain preserved evidence. [C35]

## 3. Software design and methods

> **Drafting guide:** R1/R2 supply architecture and user-sequence examples; R4 Choi (2021) and R6 Essawy connect execution to retained artifacts. Explain the browser journey and each subsystem's responsibility before native internals. Add complementary workflow/architecture schematics; move detailed commands to the supplement.

### 3.1. Explicit planning and runtime qualification

The initial public increment implements an offline planning foundation: campaign validation, interval arithmetic, issue ledgers and bounded resident-asset verification. Its `init`, `plan`, `ledger`, `report` and `doctor` commands have local installation and software-contract validation; `run` and `resume` explicitly report that execution is unavailable. Exact test counts and environments are recorded in `docs/VALIDATION.json` and `docs/IMPLEMENTATION_STATUS.md`. These are offline implementation checks, not physical-model results. Native execution will require a separately qualified adapter, a complete fixture and exact build identities. A plan or successful file inventory will not launch a model or certify runtime readiness. [C13]

The technical roadmap proposes a broader workflow for issue scheduling, selectable leads within 1–18 hours, preparation, execution, verification and export. Support for each option will be tied to its implementation and qualification evidence. The initial physical recipe still has eighteen hourly branch steps; retaining fewer output leads and changing the simulated horizon are different operations, and neither implies a shorter-horizon runtime has been qualified. YAML examples and proposed commands in the brief are not documentation of additional implemented interfaces. [C43]

The intended native profile uses Linux ARM64, SLOTH/NoahOWP/CFE, a single-threaded land parent and child-owned channel routing. It excludes MPI, embedded Python in the land engine, reservoir and assimilation routing, and portable cross-host branching. The pinned framework, source overlays, middleware loading path, image digest and component artifacts must be resolved together. A stock container or an engine source commit cannot identify every linked physical library. [C14]

### 3.2. Branch construction and isolation

Inspected historical V3 source checks that the parent has one thread, advances the router to the issue boundary, snapshots the channel continuation state and forks the live land process. In the child, it reopens recognized read-only files into independent open-file descriptions, abandons inherited routing ownership, starts its own router and restores the channel state. The parent waits for an isolation acknowledgement before advancing. Unknown writable handles are grounds to refuse branching. These are inspected implementation mechanisms; the public rebuild will need its own qualification. [C15]

The design addresses several different isolation surfaces. Copy-on-write memory separates subsequent address-space updates, but duplicated descriptors can still share offsets and external files can still be shared. Child ownership therefore includes file descriptions, output paths, routing processes and descendant-process cleanup. Observed parent clocks and available state diagnostics will be compared before and after branch perturbations. Because these diagnostics cannot enumerate all hidden component state, numerical continuation tests and explicit component restrictions will supplement them. [C16]

### 3.3. Committed forecasts and recovery

An issue will count as complete only after the child has been reaped with zero exit status, its native receipt agrees with the requested clock, its gauge/lead keys are complete and unique, and its numerical outputs satisfy declared validity checks. Output data, checksums and identity bindings will be staged together, synchronized and atomically published within the qualified local filesystem. The public implementation will test filesystem and interruption assumptions rather than extend local rename semantics to arbitrary object stores. [C17]

For durable recovery, the design distinguishes three artifacts: a live inherited process state; a channel-only routing snapshot; and a committed discharge archive. Neither of the latter two is a complete land checkpoint. After parent or host loss, recovery will recreate the original realization at \(H\), replay the same historical inputs, verify previous forecast commits and suppress only their forecast launches. Suppressing a completed issue must not skip historical state updates. A child that fails after the parent advances may similarly require replay to recreate its issue state. [C06–C07, C18]

This approach exchanges checkpoint generality for replay cost and input-retention requirements. It can preserve the original scientific experiment only if its runtime and full antecedent inputs remain available. A missing weather object will stop recovery; changing the origin, substituting forcing or silently changing parameters would define another experiment. Replay planning and durable replay equivalence are separate capabilities. The latter remains to be demonstrated for the new implementation. [C18]

### 3.4. Traceable archive and release boundary

The planned archive will bind each output key to campaign, runtime, domain, issue and source manifests. Byte checksums will detect corruption; they do not authenticate a malicious writer and do not establish scientific validity by themselves. Deterministic normalized records will be compared separately from timing logs and other intentionally variable metadata. An output archive also excludes much of the state and forcing required for reproduction, so its size cannot be reported as the complete reproducibility footprint. [C19]

The release will separate independently authored core code from inherited native integration, third-party components and data. Licensing, notices, source-to-binary attestations and fixture redistribution remain unresolved at this stage. The public repository is therefore a development resource, not yet a licensed and independently qualified runtime distribution. [C20]

## 4. Evaluation protocol

> **Drafting guide:** R3/R5/R7 place experiment definitions before outcomes; R8 informs user-task evaluation. Separate fidelity, isolation, recovery, resources and usability. R5's expert-coauthor competency ratings are not independent hydrologist task evidence and do not validate our proposed UX thresholds.

The evaluation specification in `benchmarks/PROTOCOL.md` and `EXPERIMENT_MATRIX.json` separates new unit tests, synthetic mechanics, physical qualification and independent researcher reproduction. Each trial will retain its immutable inputs, environment, command, outcome, diagnostics and raw measurements. Runs that fail validation, time out or require assistance will remain in the record. Acceptance decisions will precede performance summaries. [C08]

The first physical case will reconstruct the original Watauga qualification window: 31 catchments, origin 2021-12-01 00:00 UTC, issues at 2022-01-01 23:00 and 2022-01-02 00:00 UTC, and historical continuation to 2022-01-02 18:00 UTC. This corresponds to 786 historical updates and two independent 18-hour forecasts. The exact original fixture must first be restored and bound; a differently initialized production history is not interchangeable. [C21]

For each issue, an independent sequential reference will initialize at the same origin, consume the same historical bytes to the issue and then the same forecast bytes for eighteen hours. A same-weather branch versus uninterrupted history will be an additional control. Discharge comparisons will use complete keys, finite values and the preserved `math.isclose` criterion \(|q-q_{ref}|\leq\max\{10^{-6},10^{-5}\max(|q|,|q_{ref}|)\}\), with discharge in cubic metres per second. Exact clocks and counts have zero tolerance. Other physical variables will require unit-specific thresholds before measurement; the discharge threshold will not be silently applied to all state variables. [C22]

Isolation and recovery experiments will perturb only one branch, vary admitted concurrency, inject child or parent termination at named transaction boundaries, and corrupt bound inputs and commits. Success will require unchanged unaffected trajectories, no partial output accepted as complete, no duplicate committed issue, and recovered output agreement with an uninterrupted reference. A refusal under missing inputs is an expected successful integrity response, not a successful recovered simulation. [C23]

Performance experiments will use identical workloads and fixed whole-job CPU and memory limits. Comparisons will report total wall and CPU time, initialization and forecast phases, validation and I/O, whole-job memory accounting, storage and replay overhead. A sequential per-issue reference is scientifically transparent but may repeat history; it will not be presented as the fastest available competing strategy without examining qualified alternatives. Warm-cache and first-use measurements will be distinguished. Five paired trials will initially summarize variation descriptively; no universal scalability or cost claim will follow from this small design. [C24]

New River will provide a second physical domain with two nested outputs, after its fixture and explicit geometry treatments are available. A final independent researcher exercise will use the frozen release and documented example on a qualified clean environment, including one configuration-only variation. Another automated agent on the developer's machine will not count as that external reproduction. [C25]

Separately, the proposed browser study will evaluate the admitted [researcher journeys](../docs/PRODUCT_OBJECTIVES_AND_USER_JOURNEYS.md) using the [UX protocol](../docs/UX_EVALUATION_PROTOCOL.md). It will retain unassisted completion, assistance, expected blocks, failures and understanding of the resulting experiment. Prototype, synthetic-service, physical-workflow and independent-reproduction evidence remain distinct. No user sessions have been conducted for this draft. [C45]

## 5. Historical motivating evidence and pending new results

> **Drafting guide:** R1/R5 distinguish demonstration from performance; R2 shows a task-ordered example. Once measured, organize new findings by Q1–Q5 with failures and denominators visible. Preserve the historical and isolated-CFE evidence below as separate categories; other papers' results cannot fill our empty result slots.

### 5.1. Preserved runtime receipts

The preserved application used a 31-catchment Watauga domain and a 393-catchment New River domain, with two outputs in the latter. These total 424 unique catchments and two initialized domains. An inspected historical weekly receipt records 168 issues per domain, eighteen leads, and 9,072 gauge forecast rows. Its serial/concurrent comparison reports all keyed discharge values within absolute and relative tolerances of \(10^{-6}\) and \(10^{-5}\), with nonzero maximum differences for two gauges. This is historical tolerance agreement for the binary identified by `f4d4690c…`, not bitwise equality or a result for the public rebuild. [C26; dossier `BENCHMARK_EVIDENCE_AND_PLAN.md`]

That receipt reports workflow times of 1,213 and 490 seconds, but the compared configurations used different CPU allocations. These times are retained as context and will not support an equal-resource algorithmic speedup claim. Configured child limits also exceeded the observed concurrency: the largest observed outstanding counts were three for New River and two for Watauga. A configured limit is not evidence that this many children ran simultaneously. [C27]

A later V3 Watauga day-custody receipt uses native identity `ee65c774…` and the matched middleware identity. It records 786 historical updates, two branches, 36 forecast rows and two day acknowledgements, with reported zero differences for its selected parent and branch diagnostics. This concerns the preserved V3 custody test; it does not establish full land restart or inherit the older weekly binary's qualification automatically. The historical receipts were inspected, but all raw arrays were not independently recomputed in the feasibility investigation. [C28]

### 5.2. Inspected prior isolated CFE sensitivity

Following the owner's report, an existing isolated CFE investigation was supplied for inspection. Its receipts identify CFE source commit `f9182dfb3d81c407c66c5b782114173893c30cf2`, which is not attested as the library used by the historical coupled runtime. The reviewed driver compares inherited and candidate `mean.slope_1km` parameter variants by changing only CFE's `slop` before fresh initialization of each variant/scenario. Synthetic forcing supplies 5 mm/h during the first six hours of each 168-hour week and zero otherwise, with potential evaporation of 0.1 mm/h. A 104-week warmup precedes a 52-week (364-day) evaluation. Noah coupling, channel routing, observed weather and streamflow observations are absent. [C34; [finding record](../docs/CFE_PARAMETER_FINDING.md)]

The saved paired-result arithmetic was independently recomputed during this review; CFE itself was not rerun. For each catchment, the percentage is `100 * (inherited / candidate - 1)`, and the reported summary is the unweighted median across 31 valid pairs, with none excluded. The short-window metric sums `flux_Qout_m * 1000` over simulation hours 17,472 through 17,489, giving CFE runoff depth in millimetres for the first 18 evaluation hours immediately after warmup at synthetic storm onset. It is not an average over forecast issue times or all weekly storms. [C34]

| Evaluation window | Median per-catchment difference (%) | Minimum–maximum across catchments (%) |
|---|---:|---:|
| First 18 hours at synthetic storm onset | +102.84 | +20.16 to +220.15 |
| Full 52 weeks (8,736 hours) | +2.485 | +2.114 to +4.186 |

These values are recomputed summaries of saved outputs from a prior isolated experiment. Their source artifacts and hashes are recorded in [the sanitized evidence receipt](../docs/evidence/cfe-sensitivity-review.json); the underlying bundle is not yet publicly deposited. The smaller full-window contrast does not establish a general long-term bound on sensitivity. Neither catchment median establishes area-weighted basin runoff, routed gauge discharge, predictive skill, the coupled-model response or the effect of changing a complete reforecast campaign. The controlled CFE comparison also cannot represent all modifications in upstream PR #74. [C34–C36]

### 5.3. Public-implementation results

**New public-implementation results are pending.** No physical-equivalence table, resource figure, failure-recovery outcome or independent-user result is supplied in this draft. The located qualification fixture contains 181 files, of which 132 were dataless at the recorded inspection. Restoration, distribution terms and build/component provenance must be resolved before new physical results can be claimed. Planner tests will establish only their tested software contracts. [C21, C29]

## 6. Discussion and limitations

> **Drafting guide:** R2/R5/R6/R8 frame access, reproducibility, tradeoffs and sustained use. Answer the five questions before discussing extensions. Explain what remains burdensome for researchers, where the qualified scope ends, and how maintenance affects reuse. Keep execution fidelity separate from hydrologic skill.

The proposed contribution is a tested relationship among historical state, forecast branches and durable evidence. It will be valuable only if that relationship survives realistic model integration and failure. Explicit unsupported configurations are part of the method: process forking is sensitive to threads and external state, while routing snapshots depend on topology and variable layout. Passing tests for one component stack cannot establish compatibility with arbitrary BMI realizations. [C14–C16]

Replay recovery is scientifically interpretable because it preserves the original initialization experiment, but it may become expensive for long antecedent histories. The benchmark will quantify that cost rather than describe daily output custody as physical checkpointing. Input retention is equally important. Source locators, checksum lists and small discharge archives are useful records, but none can replace missing forcing bytes. [C18–C19]

Hydrologic predictive skill is distinct from workflow equivalence. A faithfully reproduced realization may be biased, and agreement between two executions does not validate parameter choices, precipitation timing or retrospective gap treatments. The accompanying HYDRA research concerns forecast correction and hydrologic performance; this paper will center on computational correctness, resources, recovery and reuse. Shared archive origins will be disclosed without reusing a correction result as evidence of runtime reliability. [C30]

The intended architecture makes HYDRA an optional downstream archive consumer alongside other statistical, evaluation and ML workflows. The generator will not require a correction model or use correction skill as its acceptance criterion. A bounded export demonstration will need to preserve the full issue/lead/valid-time key, scientific variant and forcing/state lineage so that downstream researchers can define their own information and verification policies. That demonstration remains future work until an export adapter and qualified archive exist. [C42]

The isolated CFE sensitivity makes this distinction concrete. Successful branch/reference agreement under the same mapping could coexist with a scientifically consequential parameter-mapping problem. The proposed response is to retain the historical runtime comparison, reproduce the isolated experiment from its bound sources, and qualify an explicitly different physical profile before assessing any coupled or full-campaign effect. Recomputing saved-output arithmetic does not establish model reproducibility or equivalence to the deployed component. The observed isolated contrasts cannot support a causal explanation of historical forecast errors or a claim that an alternative variant improves forecasts. [C32, C34–C36]

Upstream integration and maintenance remain open design decisions. The feasibility comparison identifies overlapping tools and candidate interfaces, but does not prove that an equivalent contract is absent elsewhere. Maintainer discussion and version-specific comparison must precede any priority claim. A thin independently maintained package, an upstream extension or a workflow profile should be selected according to demonstrated integration and maintenance needs. [C04, C31]

## 7. Provisional conclusion

> **Drafting guide:** R1/R5 provide examples of bounded software conclusions. State the supported contribution, intended user and strongest limitation in that order. Add no claims absent from our results; current conclusions remain provisional.

A reproducible reforecast workflow requires more than repeated model launches: it requires agreement about the initialized state, the interval consumed at each issue, branch ownership, completion and recovery. This draft defines those contracts and an evaluation that can reject their implementation. Historical receipts motivate the work but do not qualify the new public software. The final conclusion will depend on completed physical references, equal-resource measurements, interruption experiments and independent reproduction; no claim of demonstrated efficiency or finished software is made here. [C08, C29]

## Availability and declarations — to be completed before submission

> **Drafting guide:** R1/R4/R6 and FAIR4RS inform concrete artifact identification. List the exact code, environment, input, output and analysis versions with access terms and reproduction instructions. Published examples do not replace the current journal guide or author-confirmed declarations.

**Software and data.** The development repository is https://github.com/Mitchel34/nextgen-reforecast-software. The paper release commit/tag, archive DOI, compatible image digest, complete licensed fixture deposit and durable benchmark deposit are pending. Preserved source/receipt aliases in the public dossier point to evidence that is not entirely redistributed. A public repository URL is not a substitute for a complete reproducibility deposit. The final availability statement must identify access terms and exact versioned artifacts actually used. [C20, C29]

**Authorship and contributions.** Author identities, order, affiliations, corresponding author, ORCIDs and CRediT roles require confirmation. No author approval or institutional endorsement is asserted.

**Funding, interests and acknowledgements.** Funding identifiers, funder roles, competing interests and acknowledgements are pending factual confirmation. This draft does not assert that funding or competing interests are absent.

**AI assistance.** AI tools assisted draft preparation and initial software work. The authors must verify all text, code, evidence and citations and supply the disclosure required by the applicable journal policy. Final tool/use wording and author responsibility statements remain to be reviewed.

**Journal requirements.** The official guide returned HTTP 403 on 18 September and again on 23 September 2026. Exact article category, length, submission files and declarations have not been certified; see [JOURNAL_REQUIREMENTS.md](JOURNAL_REQUIREMENTS.md).

## References and evidence map

> **Drafting guide:** Use the [R1–R9 reading set](RELATED_WORK_AND_WRITING_GUIDE.md) selectively where it supports a claim or method. Descriptive papers, exact software/data versions and our experimental receipts serve different citation roles. Retain access limits and do not cite an unread layout as inspected.

Bibliographic entries are in [references.bib](references.bib), with access and verification notes in [SOURCE_VERIFICATION.md](SOURCE_VERIFICATION.md). Internal methodological evidence is mapped per claim in [CLAIMS.csv](CLAIMS.csv), principally to the preserved dossier under `reports/reforecast_software_feasibility_20260918T045854Z/`. Claims supported only by inspected historical source or receipts retain that qualification until matched new experiments are available.
