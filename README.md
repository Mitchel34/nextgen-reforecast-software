# NextGen Reforecast Software

A research software project for constructing auditable NextGen reforecast campaigns with shared historical state and independent forecast branches.

The intended hosted web application lets a hydrologist select a watershed or USGS/NWM identifier, a supported historical period and forecast lead preferences. The service acquires and prepares inputs, supplies inspectable scientific defaults, executes on supported Linux infrastructure and returns research datasets with provenance and verification evidence. Researchers should need no command line, Python or local modeling installation. The project builds on the NextGen ecosystem and keeps forecast generation separate from downstream HYDRA/ML correction.

**Current stage: planning, input validation and pinned diagnostic campaign execution (`0.1.0a5`), with a local browser interaction prototype.** The public package provides offline planning/provenance and a new `prepare` → `run` → `verify` → `export` operator path for exact Watauga v2 inputs and sealed references. Complete physical arrays are compared before a whole-campaign result is atomically committed; retained leads select exported rows only. The Linux export/image runtime is admitted for these diagnostics. Automatic hosted researcher execution, recovery, clean-build qualification and scientific release remain unfinished. The completed feasibility dossier and evidence-bound manuscript remain in this repository.

The [installed execution acceptance](docs/PUBLIC_CAMPAIGN_EXECUTION_RESULTS_2026-10-11.md) passed 293 Python tests, 17 browser contract tests and 14 installed CLI checks. Six fresh model stages reproduced the complete sealed canonical arrays; all 36 generated issue/lead rows were verified before exporting 12 selected rows. [Public Linux CI](https://github.com/Mitchel34/nextgen-reforecast-software/actions/runs/38115725913) passes all five jobs, including Python 3.11–3.14. The [publication receipt](docs/evidence/public-campaign-execution-publication-20261011.json) freshly rechecks the installed package, source assets and completed archive. All workflow writes stayed in this repository; later metadata drift in the original Reforecast folder is recorded in the [preservation audit](docs/evidence/public-campaign-preservation-publication-audit-20261011.json).

## Start here

- [Matched generation-workflow benchmark draft](benchmarks/MATCHED_WORKFLOW_BENCHMARK_DRAFT.md) and [instrumentation runbook](docs/BENCHMARK_INSTRUMENTATION_RUNBOOK.md) — prospective speed, reproducibility and effort measurements; synthetic mechanics grant no performance result
- [Compatible public Watauga fixture v2](fixtures/watauga-public-v2/README.md) — source-bound Noah revision, development inputs and remaining qualification
- [Independent physical references](docs/PUBLIC_WATAUGA_REFERENCE_RESULTS_V2_2026-10-10.md) — complete outputs, exact antecedent-prefix agreement and retained failures
- [Diagnostic Linux runtime](docs/LINUX_DIAGNOSTIC_QUALIFICATION_2026-10-10.md) — immutable execution identities and remaining clean-build gates
- [Public-fixture working plan](docs/PUBLIC_WATAUGA_FIXTURE_PLAN.md) — separate preparation identity and zero model-invocation allowance
- [Scientific input and runtime increment — 10 October](docs/INPUT_RUNTIME_INCREMENT_2026-10-10.md) — current assignments and evidence boundaries
- [Active multiagent kickoff — 10 October](docs/IMPLEMENTATION_KICKOFF_2026-10-10.md) — assignments, contracts and integration boundaries
- [Working plan and reassessment — 24 September](docs/WORKING_PLAN.md) — saved baseline, three resolved planning concerns and remaining decisions
- [Product objectives and user experience pathways](docs/PRODUCT_OBJECTIVES_AND_USER_JOURNEYS.md) — owner requirements, proposed study modes and build mappings
- [User experience evaluation protocol](docs/UX_EVALUATION_PROTOCOL.md) — task scenarios, acceptance criteria and evidence scorecard
- [Implementation plan and acceptance milestones](IMPLEMENTATION_PLAN.md)
- [Development backlog and first work cycle](docs/DEVELOPMENT_BACKLOG.md)
- [22 September roadmap reconciliation](docs/ROADMAP_RECONCILIATION.md)
- [Current implementation and validation status](docs/IMPLEMENTATION_STATUS.md)
- [User guide](docs/USER_GUIDE.md) and [architecture](docs/ARCHITECTURE.md)
- [Manuscript draft](paper/MANUSCRIPT.md) and [claim/evidence register](paper/CLAIMS.csv)
- [Manuscript development plan](paper/DEVELOPMENT_PLAN.md)
- [Environmental Modelling & Software reading and writing guide](paper/RELATED_WORK_AND_WRITING_GUIDE.md) — nine selected references mapped to manuscript sections and visuals
- [Predeclared benchmark protocol](benchmarks/PROTOCOL.md)
- [Runtime qualification and missing assets](docs/RUNTIME_QUALIFICATION.md)

## Install and try the planning commands

For the browser interaction prototype, see [web/README.md](web/README.md). It collects and reviews a researcher request, including unknown coverage and preparation blockers. It does not acquire inputs, run models or download a verified scientific dataset.

Python 3.11 or later on Linux or macOS:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
ngen-reforecast init my-campaign
ngen-reforecast plan my-campaign/campaign.json
ngen-reforecast ledger my-campaign/campaign.json --output my-campaign/expected.csv
ngen-reforecast report my-campaign/campaign.json --output my-campaign/plan.md
ngen-reforecast doctor profiles/nextgen-arm64-v3.json
```

The example includes no scientific inputs. `plan`, `report` and `doctor` intentionally return exit code **2** when requirements remain unresolved, while providing their reports. The expected ledger contains 36 issue/lead keys, not generated discharge. Asset inspection never starts a model, downloads data or hydrates placeholders. `prepare` and `run` support only the separately admitted Watauga v2 diagnostic; `resume` remains unavailable. See the user guide for resource bounds, schema and exit codes.

The [schema 1.1 campaign contract](docs/CAMPAIGN_CONTRACT.md) adds UTC cadence schedules and selected retained leads. The [planning provenance contract](docs/PROVENANCE_CONTRACT.md) explains `lock` and `verify-lock`. These extend offline planning; they do not qualify a physical runtime.

## Project material

- [Technical foundation and software roadmap supplied 22 September](docs/source_material/TECHNICAL_FOUNDATION_2026-09-22.md) — preserved design input; see the reconciliation for current implementation and evidence status
- [Software and manuscript outline](nextgen_Software/SOFTWARE_AND_MANUSCRIPT_OUTLINE.md)
- [Formatted outline](nextgen_Software/SOFTWARE_AND_MANUSCRIPT_OUTLINE.docx)
- [Investigation instructions](nextgen_Software/AGENT_INFORMATION_REQUEST.md)
- [Preserved source inspection notes](nextgen_Software/SOURCE_INSPECTION_NOTES.md)

The six original files under `nextgen_Software/` are preserved byte-for-byte. Statements in those original documents about repository creation describe their preparation date. Repository creation and publication were subsequently authorized by the project owner.

## Feasibility findings

Start with the [executive feasibility report](reports/reforecast_software_feasibility_20260918T045854Z/EXECUTIVE_FEASIBILITY.md) and [prioritized extraction backlog](reports/reforecast_software_feasibility_20260918T045854Z/EXTRACTION_BACKLOG.md).

- [Capability evidence](reports/reforecast_software_feasibility_20260918T045854Z/CAPABILITY_EVIDENCE.csv)
- [Source and version map](reports/reforecast_software_feasibility_20260918T045854Z/SOURCE_VERSION_MAP.json)
- [State and recovery](reports/reforecast_software_feasibility_20260918T045854Z/STATE_AND_RECOVERY.md)
- [Data and configuration](reports/reforecast_software_feasibility_20260918T045854Z/DATA_AND_CONFIGURATION.md)
- [Minimum example assets and gaps](reports/reforecast_software_feasibility_20260918T045854Z/MINIMAL_EXAMPLE_MANIFEST.json)
- [Upstream overlap and licenses](reports/reforecast_software_feasibility_20260918T045854Z/UPSTREAM_OVERLAP_AND_LICENSES.md)
- [Benchmark evidence and proposed tests](reports/reforecast_software_feasibility_20260918T045854Z/BENCHMARK_EVIDENCE_AND_PLAN.md)
- [Checks actually performed](reports/reforecast_software_feasibility_20260918T045854Z/CHECKS_ACTUALLY_PERFORMED.md)

The review supports a narrow extraction path but does not establish a complete public runnable example. Existing land state is inherited through live process branching; recovery relies on replaying the same historical inputs. The required Watauga fixture currently has missing resident assets. Historic numerical receipts and their exact version limits are recorded separately from newly performed read/hash checks.

The source and receipt references resolve to a private preservation snapshot; this public dossier does not include the underlying research implementation or data. Three independently initialized serial references are now sealed for the separate compatible public Watauga v2 fixture, and the installed operator campaign path reproduces their complete canonical outputs. Next milestones qualify shared-history continuation, a reproducible clean build and artifact access/rights before independent reproduction. Historical exact-file restoration remains a separate unresolved track.

## Scope

The proposed product combines a browser interface and automatic input preparation with a narrowly qualified Linux runtime: continuous historical initialization, independent hourly 18-hour forecasts, explicit forcing and time semantics, verified output commits, and documented history-replay recovery. Continuous historical simulation, published-study recipes and controlled comparisons are additional design proposals recorded in the objectives. The local browser prototype prepares a request; a hosted execution service does not exist yet. The installable commands above are the offline foundation and future operator interface.

Existing research workspaces and the separate private HYDRA repository remain read-only throughout development. Large research archives, inherited code, scientific datasets, binaries and credentials are not published in this repository. Verified source/runtime/input copies acquired for this increment remain in ignored private staging; their status is documented separately.

## License status

A public software license has not been selected. See [LICENSE_STATUS.md](LICENSE_STATUS.md). This repository is not an official NOAA or CIROH distribution.
