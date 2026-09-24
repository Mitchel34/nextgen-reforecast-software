# Product objectives and user experience pathways

Recorded 23 September 2026 from the owner's product discussion and the subsequent literature review. This is the planning baseline for the researcher experience. It supersedes earlier assumptions that users must supply prepared model inputs, know Python or a command line, or wait for a later release to receive a hosted interface. The existing [implementation milestones](../IMPLEMENTATION_PLAN.md) and [engine backlog](DEVELOPMENT_BACKLOG.md) retain their identifiers and scientific qualification requirements.

**Implementation state:** these are target experiences, not delivered capabilities. The public package remains an offline planning foundation. This update records requirements and evaluation criteria; it does not launch development, acquire scientific datasets, execute models, provision hosting, or authorize spending. See [implementation status](IMPLEMENTATION_STATUS.md).

## Product purpose and primary user

A hydrologist should be able to select a watershed or station, a supported historical period, and forecast preferences in a browser. The service should acquire and prepare the necessary inputs, perform the supported experiment on Linux infrastructure, and return an understandable, traceable dataset suitable for research.

The primary user understands the scientific question but may have no experience with Python, terminals, containers, model configuration files, or cloud administration. Required starting information is:

- A watershed, USGS gauge identifier, or NWM reach identifier. The service resolves the identifier and asks the user to confirm the outlet and upstream domain on a map.
- The historical period of interest, within demonstrated input and model support.
- Whether forecasts are wanted and, when applicable, how far ahead they should extend.

USGS gauges and NWM reaches have different identifier systems; retain both the submitted identifier and the resolved, versioned mapping. A watershed name alone may need outlet clarification. Account access is a service prerequisite, not an additional scientific input.

The standard experience supplies a documented, qualified model configuration and initialization policy. Researchers can inspect those choices before submission. Supported advanced settings may be added without making them prerequisites for an ordinary study. The interface must distinguish forecast horizon, forecast issue frequency, and output timestep.

## Objective register

**Owner direction** records explicit requirements or the owner's stated quality objective. **Design proposal** records a research-informed recommendation to evaluate during planning; saving it does not imply final approval or implementation. All delivery states below are planned.

| ID | Objective | Decision status | Observable success | Pathways |
|---|---|---|---|---|
| UO-01 | Require only practical study information | Owner direction | A new user can define a supported study from location, dates, and forecast preference without assembling files or specifying private paths | UX-01, UX-02, UX-05 |
| UO-02 | Make a hosted graphical interface the primary experience | Owner direction | The normal workflow completes in a browser without a terminal, Python, notebook, or local modeling installation | UX-01–UX-07 |
| UO-03 | Acquire and prepare inputs automatically | Owner direction | A supported submission resolves watershed geometry, parameters, historical weather and, when needed, issue-specific forecast weather; preparation and failures are visible | UX-01, UX-02, UX-05 |
| UO-04 | Execute remotely in one supported Linux environment initially | Owner direction | Computation continues independently of the browser; users can return from their computers to inspect the same campaign | UX-01, UX-02, UX-06 |
| UO-05 | Deliver understandable and trustworthy research outputs | Design proposal supporting the owner's research purpose | Users can identify what ran, what is missing, units and time meanings, and download results with provenance and a methods report | UX-05, UX-07 |
| UO-06 | Offer distinct historical-simulation and reforecast modes | Design proposal; clarify the owner's “if” forecast-lead preference | Users can explain the selected mode and receive the corresponding continuous-time or issue/lead dataset | UX-01, UX-02 |
| UO-07 | Support exact published-study recipes | Design proposal from the literature review | A qualified recipe preserves the publication's actual settings and distinguishes a tutorial from the full published experiment | UX-03, UX-07 |
| UO-08 | Support controlled adaptation and comparison | Design proposal from the literature review | A copied experiment identifies its changes, preserves the original, and compares compatible outputs with an explicit shared population | UX-04, UX-07 |
| UO-09 | Produce independently usable, reproducible deliverables | Owner quality direction; detailed evaluation targets proposed | Hydrologists outside the development team complete supported tasks; assistance, failures and scientific reproduction are recorded separately | UX-01–UX-07 |

The owner has selected the hosted experience and remote Linux direction. Framework, hosting provider, account mechanism, funding model and storage policy are not selected by this document.

The [24 September working-plan reassessment](WORKING_PLAN.md) preserves this product direction and resolves the candidate-release, first-experiment and browser-evidence handoffs. The [UX evidence contract](UX_EVIDENCE_CONTRACT.md) now defines the future versioned records used to evaluate these journeys. It adds no adopted mode, hosting provider or completed capability.

## Shared experience contract

Every new experiment follows **Find location → Choose study → Check coverage → Review → Submit → Monitor → Inspect/download**. Published recipes can prefill these steps. Comparison starts from a preserved experiment and creates a new identity.

Before submission, show the outlet/domain, study mode and period, selected model/parameter profile, initialization duration and rationale, weather sources, issue schedule and requested leads where applicable, output locations, coverage exceptions, and resource limits. Surface concise explanations with expandable scientific details. The service calculates initialization requirements rather than asking ordinary users to invent a spin-up duration; never represent an adopted duration as universally converged.

Use explicit campaign stages: Draft, Checking availability, Needs attention, Ready, Queued, Preparing, Running, Verifying, Complete, Partial, Failed and Cancelled. Final state-transition details are a design task. Download availability and verified product counts must be independent of an optimistic progress indicator. Distinguish stopping a job from resuming it later; only expose controls with implemented semantics.

Submission authorizes only the input acquisition and compute described within the service's established user entitlement and resource limits. It does not request separate approval for every file. Changing scientific defaults or gap treatments must be visible and create a new experiment identity as appropriate. Resource estimates must be measured or identified as uncertain/unavailable; do not promise completion time or savings from an unbenchmarked configuration.

## UX-01 — Create a continuous historical simulation

**Question:** “How does this supported model simulate streamflow in this watershed over these historical dates?” **Objectives:** UO-01–UO-06, UO-09. **Status:** proposed mode, not implemented.

1. Search for a location and confirm its upstream boundary and outlet.
2. Choose **Historical simulation**, dates, and default output locations; inspect the supplied scientific settings if desired.
3. Review supported coverage, the preceding initialization interval, and any limitations.
4. Submit; follow automatic preparation and execution; inspect the verified hydrograph and download the research package.

**Expected product:** continuous streamflow indexed by location and valid time, with units, quality/completeness status, experiment identity, provenance and methods. Comparison with USGS observations is offered where compatible observations exist; their absence must not be confused with failure to simulate.

**Acceptance:** a participant completes the supported case without coding or preparing files; can explain that the weather is historical rather than an archived forecast; identifies the actual output period and initialization period; and retrieves a dataset whose expected keys and units pass verification. This mode is not represented as a zero-hour reforecast. Missing required initialization weather routes to UX-05.

## UX-02 — Generate historical reforecasts

**Question:** “What would this defined model experiment have predicted at successive historical issue times?” **Objectives:** UO-01–UO-06, UO-09. **Status:** core intended product; physical execution and web experience not implemented.

1. Resolve the watershed; choose **Historical reforecasts**, a study period and desired lead horizon.
2. Review the default issue frequency, output timestep, initialization policy and archived forecast-weather source. The date picker distinguishes complete, incomplete and unsupported periods.
3. Review expected issue and output counts, gap decisions and resource bounds; submit.
4. Inspect progress by issue, then explore individual forecasts and results by lead time; download the verified archive.

**Expected product:** location, forecast issue, lead, valid time, discharge, units and quality status, bound to the model/parameter/domain/run identities. Several forecasts for one valid time remain separate.

**Acceptance:** a user correctly reads an example issued at 12:00 UTC with a three-hour lead as targeting 15:00 UTC; the service checks antecedent history and weather through the final target; forecast branches cannot alter history or siblings; failed/excluded issues remain visible; and exported rows match the declared generated/retained population. Hourly output is not evidence of one-hour forecast skill. Historical reforecasts do not automatically recreate operational NWM forecasts or operational data availability.

**Initial constraint:** the candidate physical profile uses 18 hourly execution steps. Requested retention within 1–18 is planned; current schema 1.0 still requires all 18. A six-hour requested product must not be advertised as six hours of native execution or proportional compute savings until that capability is separately qualified. Longer horizons are future capabilities, not universal NextGen limitations.

## UX-03 — Reproduce a published study

**Question:** “Can I repeat this publication's experiment and compare my result with its reference?” **Objectives:** UO-02, UO-05, UO-07, UO-09. **Status:** proposed curated workflow.

1. Select a supported study card with citation, recipe version, artifact availability and reproduction evidence status.
2. Choose the exact published experiment or a separately labeled demonstration; see their differences before submission.
3. Review the fixed location, dates, model/runtime, forcing, initialization, calibrated parameters, calibration settings or trained weights, and evaluation definition.
4. Execute the qualified recipe; inspect the comparison with its declared reference and tolerance; download the reproduction receipt.

**Acceptance:** selecting the exact recipe cannot silently apply tutorial defaults, current upstream parameters, fewer calibration iterations or new model versions. The original citation and artifact identities persist. Missing original artifacts yield **Reproduction unavailable** with specific missing items. A failed scientific comparison remains a failed comparison even if the job exited successfully. Editing a scientific setting creates an adaptation under UX-04, not a claim of exact reproduction.

A recipe may itself require calibration or other capabilities outside the initial engine. Only admit it after those steps and distribution rights are qualified; a study-card interface does not establish support for every reviewed paper.

## UX-04 — Adapt and compare an experiment

**Question:** “What changes when I alter this supported scientific choice?” **Objectives:** UO-02, UO-05, UO-08, UO-09. **Status:** proposed advanced workflow.

1. Duplicate a completed experiment or recipe and select a supported change, such as parameters, dates, location or forcing source.
2. Review an explicit difference summary and which preparation/state work must be recomputed.
3. Submit the new experiment; preserve the original and its products.
4. Compare compatible outputs using the same metric definitions and an explicitly identified common period, locations, issues and leads.

**Acceptance:** the change creates a new scientific identity; parameter or historical-weather changes invalidate reuse of incompatible antecedent state; comparisons disclose different coverage and sample sizes; and the interface does not label a changed experiment an exact reproduction. A changed watershed or forecast horizon may require separate comparisons instead of a misleading joined score. Generic model training, arbitrary uploaded native code and arbitrary formulations are not implied by this pathway.

## UX-05 — Resolve location, coverage and preparation problems

**Question:** “Can this study run, and what can I do if it cannot?” **Objectives:** UO-01–UO-03, UO-05, UO-09. **Status:** required cross-cutting experience.

1. Present ambiguous gauge/reach matches with map context and require a deliberate choice before compute submission.
2. Explain unsupported geography/model combinations, archive bounds, missing intervals, absent observations, and temporary source failures in plain language.
3. Preserve the draft and offer scientifically valid actions: correct the identifier, revise dates, retry a transient lookup, or use a supported alternative as a new recorded experiment.
4. If a forecast-issue exclusion policy is supported, show the exact excluded issues and resulting population before acceptance.

**Acceptance:** an unsafe or unsupported request stops before physical execution with an actionable explanation. Missing historical intervals are not silently skipped; historical weather is never silently substituted for forecast weather; no automatic imputation changes the scientific experiment. Required upstream failure must not appear as “no data exist.” A successful blocked-case test means the user understands and resolves or deliberately abandons the request; it does not require forcing the model to run.

## UX-06 — Monitor and recover a campaign

**Question:** “Can I leave, return and recover unfinished work without losing or changing the experiment?” **Objectives:** UO-02, UO-04, UO-05, UO-09. **Status:** planned.

1. Submit once and receive a persistent campaign identity with stage and verified progress.
2. Close the browser, return from another session and find the same job and outputs.
3. On failure, see affected work, completed products, recovery eligibility, and estimated additional work when evidence supports an estimate.
4. Request the supported recovery action and inspect the final receipt, including retries and replay.

**Acceptance:** browser disconnect does not cancel computation; repeated submission/retry cannot create duplicate authoritative results; access is scoped to authorized users; completed issues are reverified before reuse. Recovery preserves original inputs and origin, replaying history where necessary. A routing snapshot is not described as a complete land-state checkpoint. The UI reports replay work honestly and never promises instant resume.

## UX-07 — Inspect, verify, download and share results

**Question:** “Can I understand, use and describe this dataset in my research?” **Objectives:** UO-02, UO-05, UO-07–UO-09. **Status:** planned.

1. Open the map/hydrograph with explicit time zone, units, selected locations and, for forecasts, issue/lead controls.
2. Inspect expected versus verified products, excluded/failed work and scientifically relevant limitations.
3. Download a small human-readable preview and the complete supported research export, manifest and methods report.
4. Obtain a stable experiment reference; any public sharing is a separate explicit user action with a visible access scope.

**Acceptance:** plotting does not merge forecasts sharing a valid time; partial results are unmistakably labeled; verified downloads round-trip to the correct schema and identity; observed/model units and time alignment are checked before comparison. Reports describe actual execution and missing work rather than only the intended plan. Reproduction, numerical agreement and predictive skill remain distinct claims. Export formats, retention duration and public-sharing implementation remain design decisions.

## Mapping journeys to build responsibilities

Existing RF work packages are necessary engine/research work, not a complete hosted-product backlog. These additional **proposed** planning packages identify service responsibilities; they are not deployed services, assigned implementation tasks or infrastructure authorizations.

| Proposed package | Responsibility and journey coverage | Engine interfaces and staged evidence inputs | Acceptance evidence |
|---|---|---|---|
| WEB-01 | Identifier resolution, map/outlet confirmation and supported domain preparation; UX-01/02/05 | RF-003/005A/007 preparation interfaces; RF-009A admitted domain inputs; supplies later RF-015 user evaluation | Correct gauge/reach crosswalk, domain display and ambiguous/unsupported-location cases |
| WEB-02 | Source availability and bounded automatic acquisition; UX-01/02/05 | RF-003/004/005A/007/009A | Coverage through initialization/final target; exact input inventory; recoverable source failures |
| WEB-03 | Browser experiment forms, defaults and review; UX-01/02/05 | RF-002/003/006/007 | Usable forms backed by the same versioned scientific contracts; simulation mode requires its own explicit contract |
| WEB-04 | Account/project access, job API/queue, worker isolation and resource limits; UX-01/02/06 | RF-008/010/011/012/014 | Durable job state, duplicate-submission protection, access boundaries and actual recovery evidence |
| WEB-05 | Results explorer, download, methods/provenance and explicit sharing; UX-07 | RF-003/012 | Correct display, full export round trip, completeness and access scope |
| WEB-06 | Qualified study recipes and experiment differences/comparison; UX-03/04 | RF-003/005/013 contracts/evidence and RF-016 study definitions; feeds RF-015 reproduction | Recipe/reference identity, exact versus adapted labels and comparable populations |
| WEB-07 | Independent UX evaluation and release evidence; all journeys | Versioned prototypes for early evaluation; admitted WEB paths and qualified RF-010–RF-014 evidence for real runs; supplies RF-015/RF-018 completion | [Evaluation protocol](UX_EVALUATION_PROTOCOL.md), assistance/failure records and evidence at the claimed level |

This table maps integration interfaces and staged evidence, not whole-package finish-to-start dependencies. RF-007's preparation interface and WEB-01/WEB-02 are developed together; final browser acceptance closes the combined workflow. RF-015 domain candidates can inform design before external evaluation, but completing RF-015 or the RF-018 release is never a prerequisite for building the interface or performing WEB-07. WEB-07's completed evaluation evidence feeds those final gates. Prototype evaluation can begin before real-model qualification and cannot substitute for it.

Before implementation assignments, freeze the shared experiment definition, mode-specific time/output schema, acquisition limits, scientific lock, job states, error categories and result-manifest interfaces. Each agent assignment must name its UO/UX IDs, owned files/interfaces, acceptance evidence and reviewer. Deliver code, meaningful tests, a browser example and documentation together. UI mockups cannot qualify physical output; backend tests cannot establish independent usability.

## Release and manuscript implications

- **First usable hosted release:** a hydrologist completes UX-02 through UX-05/06/07 for a clearly supported watershed and period, with automatic preparation and actual qualified model execution. The continuous-simulation mode in UX-01 is recommended for the same product but remains a mode decision; it must be separately implemented and verified.
- **Internal engineering increments:** CLI/planner tools, prepared-input fixtures and operator installation tests remain valuable prerequisites. They do not fulfill the owner-facing browser acceptance criterion.
- **Independent evaluation:** follow [UX_EVALUATION_PROTOCOL.md](UX_EVALUATION_PROTOCOL.md). Record prototype usability, simulated service mechanics, qualified science execution and external-researcher reproduction separately. No experience metrics have been measured for these pathways.
- **Manuscript:** retain existing scientific questions and extend Q5's evidence to browser task completion, user understanding and assistance. Do not claim novelty from browser hosting or gauge/date preparation alone. Optional UX-03/04 claims require their own completed evidence.

## Research grounding and limits

The [23 September EM&S reading and writing guide](../paper/RELATED_WORK_AND_WRITING_GUIDE.md) extends this grounding with reproducibility, evaluation and user-centered-design literature. It maps those references to the manuscript and existing build responsibilities; it does not adopt additional study modes, a hosting stack or a scientific recipe.

The preceding conversation reviewed representative publications and their linked materials; it was not a systematic literature census or an executed reproduction. The following findings motivate proposals rather than expanding the initial supported model set automatically:

- [Patel et al., NGIAB (2025)](https://doi.org/10.1016/j.envsoft.2025.106666) and its [Provo run package](https://www.hydroshare.org/resource/88e0ebf2719c492381efcb27fba71032/) show continuous historical simulation, calibration and evaluation with prepared artifacts.
- [Nassar et al., cloud NextGen JupyterHub (2026)](https://doi.org/10.1016/j.envsoft.2026.107031) and [published notebooks](https://www.hydroshare.org/resource/27045581bdea4808a393330f2417379c/) demonstrate existing gauge/date preparation in a notebook environment. The inspected [calibration notebook](https://www.hydroshare.org/resource/27045581bdea4808a393330f2417379c/data/contents/NextGen_Calibration.ipynb) defaults to six iterations and an October 2020 training start; the paper reports 200 iterations and an October 2019 calibration start. This is a recipe-versus-demonstration distinction, not proof of a scientific error. Recheck versioned artifacts before reproducing the paper.
- [Foroumandi et al., ensemble assimilation (2025)](https://doi.org/10.1016/j.envsoft.2024.106306) evaluates daily sequential CFE predictions and assimilation. The review did not identify a complete multi-lead archived-weather reforecast recipe.
- [Araki et al., soil-moisture evaluation (2025)](https://doi.org/10.1111/1752-1688.70002) studies daily CFE component simulations; [Machine Learning for a Heterogeneous Water Modeling Framework (2025)](https://doi.org/10.1111/1752-1688.70000) addresses model selection and regionalization. Neither establishes a generic issue/lead reforecast reproduction pathway.
- [Bravo and Temimi's 2026 conference abstract](https://ciroh.ua.edu/abstracts/assessing-the-use-of-the-model-for-prediction-across-scales-atmosphere-mpas-forecasts-for-streamflow-prediction-using-the-nextgen-in-a-box/) explicitly studies forecast lead time with MPAS/NGIAB. Its six-hour GFS input interval does not establish the hydrologic forecast horizon; an exact executable study package was not verified.
- The [July 2026 NRDS catalog](https://github.com/CIROH-UA/ngen-datastream/blob/main/docs/nrds/DATASTREAMS.md) documents 18-hour and 240-hour forecasts, alongside cold-start and timestamp qualifications. A running forecast testbed is not evidence that every historical source is available or that its state initialization matches this project's experiment.

## Decisions to resolve before build assignments

| Decision | Current position | What resolves it |
|---|---|---|
| Meaning of “no forecast leads” | Recommend explicit continuous historical simulation | Owner confirms mode semantics; engine/schema/evaluation contract is defined |
| Initial geography, domain limits and lead support | Narrow qualified Linux profile; no promise of arbitrary watersheds | Complete real fixtures, routing/capability admission and archive inventory |
| Scientific defaults | Inspectable, versioned and qualified; no silent calibration/mapping changes | Profile-specific initialization, parameter and forcing evidence |
| Pilot access and funding | Accounts, job quotas and bounded study sizes proposed | Service operator, available infrastructure and explicit resource policy |
| Retention, export and sharing | Downloadable reproducible package; public sharing explicit | Storage/access policy and formats tested with target researchers |
| First publication recipe | Provo/Logan artifacts are candidates, not supported recipes | Rights, exact versions/settings, admitted runtime and reference reproduction |
| UX release thresholds | Proposed protocol; no invented completion-time target | Formative external-user sessions, then a frozen release protocol |

No decision here changes the read-only status of the original research workspaces or the preserved outline, source roadmap and feasibility dossier.
