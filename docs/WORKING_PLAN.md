# Working plan and reassessment — 24 September 2026

This is the current coordination summary for the software and accompanying *Environmental Modelling & Software* manuscript. It preserves the existing M0–M7, RF-001–RF-018 and proposed WEB-01–WEB-07 identifiers. Detailed contracts remain in their linked documents. The owner requested this planning revision; it does not start the implementation cycle, scientific acquisition, model execution, user recruitment, hosting, spending or submission.

## Saved baseline

The previous working plan is preserved at Git commit [`78cfb92db53b6d58d8b8de9d056e067597f568f5`](https://github.com/Mitchel34/nextgen-reforecast-software/tree/78cfb92db53b6d58d8b8de9d056e067597f568f5). The [baseline manifest](planning/2026-09-24_BASELINE.json) records exact paths, byte lengths and SHA-256 values for 17 controlling documents, with immutable links to their previous contents. Saving this baseline does not duplicate or modify the original research folders or preserved source material.

## Product objective

A hydrologist supplies a watershed/USGS/NWM identifier, eligible dates and forecast preferences in a browser. The service resolves and explains the study, acquires and prepares inputs, runs the supported model on Linux, and returns verified results with provenance and a methods report. No local model installation, Python, notebook or terminal is required for the ordinary researcher pathway. The [objective and journey register](PRODUCT_OBJECTIVES_AND_USER_JOURNEYS.md) controls the experience.

The first usable product must complete the core reforecast journey and its coverage/error, monitoring/recovery and download pathways: UX-02, UX-05, UX-06 and UX-07. Continuous historical simulation, exact publication recipes and experiment comparisons remain separately identified proposals. They are not silently added to the first release by this reassessment.

## Resolution of the three review concerns

| Concern | Working-plan resolution | Completion boundary |
|---|---|---|
| Release required before independent reproduction, while reproduction is required before release | [RELEASE_SEQUENCE.md](RELEASE_SEQUENCE.md) defines an immutable, licensed, accessible `REPRODUCTION_CANDIDATE` as E09's input. Final release follows evaluation and required fixes/retesting. Engine and browser candidates can advance independently at appropriate evidence levels. | Planning sequence resolved; license, candidate artifacts and independent results still pending |
| Ambiguous first physical experiment and parameter gates | [FIRST_PHYSICAL_EXPERIMENT.md](FIRST_PHYSICAL_EXPERIMENT.md) and protocol 0.3 distinguish diagnostic baseline admission from release-profile qualification. The initial original Watauga recipe and origin stay fixed. New reference outputs are produced after input/build admission; they are not required before their own first generation. | Governing sequence resolved; complete assets, build, scientific-default decision and physical evidence still pending |
| Browser evidence missing from the manuscript results pipeline | [UX_EVIDENCE_CONTRACT.md](UX_EVIDENCE_CONTRACT.md) defines a separate versioned browser-study manifest and results package, linked to Q5 and Table 5. E09 remains operator reproduction. | Evidence handoff resolved; template is not a conducted study or measured result |

The benchmark [protocol](../benchmarks/PROTOCOL.md) and [matrix](../benchmarks/EXPERIMENT_MATRIX.json) control physical admission, experiment definitions, numerical thresholds and invocation bounds. The [UX protocol](UX_EVALUATION_PROTOCOL.md) and linked study manifest control browser tasks and their evidence. The release sequence controls candidate-to-final handoff. None overrides another's scientific requirements. An amendment must update both human-readable and machine-readable contracts when it changes either.

## Reassessed order of work

| Order | Existing packages | Reviewable deliverable | Exit evidence |
|---|---|---|---|
| 1. Establish the build and input path | RF-005A/008/009A; M2 | Obtainable, source-bound runtime/input inventory; first-experiment admission record; selected qualified build environment and bounded recipe | Fresh inspection at kickoff; exact missing items assigned; no inherited qualification or replacement of unavailable inputs |
| 2. Freeze shared interfaces and prototype the core journey | RF-002/003/004/006/007; WEB-01/02/03/04/05 | Browser-request translation, scientific lock, availability/error model, job states, result manifest and a clearly labeled interaction prototype | Reviewed contracts; exact time/key examples; owned files and integration reviewers; early UX evidence labeled at its actual level |
| 3. Produce a real independent reference, then qualify execution mechanics | RF-010/009B/011/012/014; M3/M4 | Original-fixture sequential reference and source-bound outputs; shared-history comparison and verified commit/replay behavior | Applicable E03 and reliability evidence, with known scientific concerns retained and release-candidate qualification separate |
| 4. Close the scientific profile and one browser-to-dataset path | RF-005B and applicable physical requalification; WEB-01–05 | Explicit release-default decision and a supported reforecast request that acquires/prepares/runs/verifies/exports real results | Same scientific identity across released inputs/runtime/results; UX-02/05/06/07 run receipts and tested access/resource behavior |
| 5. Complete measured scope and transfer | RF-013/015; M4/M5; WEB-07 | Equal-resource measurements, New River qualification and versioned browser evaluation package | Full declared workloads/trials/failures; correct domain counting; usability evidence separate from physical correctness |
| 6. Evaluate candidates and finalize release-linked manuscript | RF-015/016/018; M5–M7; WEB-07 | Accessible reproduction candidate → E09; browser-study candidate → UX results; final manifest, reproducible figures and evidence-bound manuscript | Findings resolved or claims narrowed; affected fixes retested; exact released artifacts match all final claims |

Orders 1 and 2 can proceed in parallel after a future implementation kickoff. Manuscript methods and literature work can continue alongside every stage. Prototype completion does not unblock a physical experiment; a blocked native build does not prevent bounded contract/design work. Stage 5 browser studies can begin earlier at prototype/synthetic evidence levels, while final physical-use claims wait for the qualified path. Candidate preparation can begin once its own required evidence is complete; it never waits on final release.

The [existing ten-working-day cycle](DEVELOPMENT_BACKLOG.md#first-ten-working-days) remains an engine increment, not a promise of a finished hosted service. The web work needs comparable task-level estimates and ownership after shared contracts and service constraints are frozen. No calendar completion estimate is newly adopted.

## Decisions that remain open

| Decision | Current working position | Required decision record / owner role | Needed before |
|---|---|---|---|
| Supported geography and study size | Start with explicitly admitted domains; Watauga/New River qualification does not establish arbitrary-basin support | Versioned domain/source coverage and exclusion matrix; domain and forcing leads | A live request is advertised as runnable |
| Browser date meaning and issue cadence | Issue dates versus valid dates and endpoint inclusion remain unresolved; use examples that show forecast targets beyond the selected issue period | Browser-request/time contract shared with the engine; product and scientific leads | Form/API behavior is frozen |
| Default model, parameters and initialization | Inspectable profile-specific defaults; calibration policy and initialization rationale require a decision; no unqualified convergence claim | Scientific-default record with provenance, comparison endpoints, unacceptable behaviors and reviewer; scientific lead | Release-profile physical qualification |
| Meaning of no forecast leads | Explicit continuous simulation is proposed | Owner's mode decision, followed by mode-specific schema and acceptance evidence | That mode is included in the release |
| Service operation | One supported Linux execution environment; provider/stack/accounts/operator/funding not selected | Account/access, queue/cancellation/recovery, job/resource budgets and operational ownership; service lead and owner for resource commitments | Hosted implementation depends on those choices or external compute is provisioned |
| Export, retention and sharing | Downloadable results and explicit sharing; no format or retention duration selected | One tested research export plus preservation of the inputs/artifacts required for the promised reproduction period; archive/service leads | Results are promised to users or deleted by a retention rule |
| License and asset rights | Core license unselected; artifact-specific terms still require closure | Selected core license and exact source/component/data notices and access terms; release coordinator and owner | Licensed reproduction candidate is distributed |
| Paper claims and UX thresholds | Describe task completion/comprehension within the tested sample and resource costs against the named reference | Freeze study outcomes after formative design; introduce a matched comparison only if claiming comparative ease/speed; manuscript and UX leads | Recruitment and measured comparisons |

These are deliberate open decisions, not delegated permission to guess. Technical leads should bring concrete proposals with consequences; the coordinator integrates them. Resolve owner choices when they become necessary, using the already confirmed minimal-input/browser direction. No need to ask ordinary researchers to choose model internals that the supported profile should supply.

## Manuscript and agent handoffs

The [manuscript plan](../paper/DEVELOPMENT_PLAN.md), [related-work guide](../paper/RELATED_WORK_AND_WRITING_GUIDE.md) and [figure/table plan](../paper/FIGURE_TABLE_PLAN.md) remain the writing baseline. Q1–Q4 address computational fidelity, isolation, recovery and resource use. Q5 separates clean-environment operator reproduction from browser task completion. Comparative superiority, improved forecast skill, arbitrary-domain support and production-scale performance require evidence beyond the currently proposed descriptive studies.

At kickoff, every agent task names UO/UX and RF/WEB IDs, owned files, input/output contracts, required evidence, reviewer and stop conditions. A handoff contains actual artifacts, exact revisions, validation commands/outcomes, unresolved dependencies and the claims newly supported. Review shared interfaces before parallel agents implement them. One manuscript lead integrates terminology and argument; evidence owners verify factual claims.

## Readiness after this revision

The three reviewed coordination concerns are resolved at the planning level. The project is ready to turn agreed interfaces into bounded implementation assignments once the listed prerequisite choices for each task are concrete. It is not yet a runnable hosted product, qualified public model distribution, completed user study or submission-ready manuscript. Historical native/asset observations must be refreshed when runtime work begins. Existing offline validation is unchanged by this documentation revision.

The next useful implementation checkpoint is a demonstrated path from a supported browser request to a verified downloadable dataset, with the independent reference and scientific profile established underneath it. Native/input closure and a clear core-journey prototype should expose feasibility and usability issues early, before broader features are promised.
