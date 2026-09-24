# NextGen Reforecast Software

A research software project for constructing auditable NextGen reforecast campaigns with shared historical state and independent forecast branches.

The intended hosted web application lets a hydrologist select a watershed or USGS/NWM identifier, a supported historical period and forecast lead preferences. The service acquires and prepares inputs, supplies inspectable scientific defaults, executes on supported Linux infrastructure and returns research datasets with provenance and verification evidence. Researchers should need no command line, Python or local modeling installation. The project builds on the NextGen ecosystem and keeps forecast generation separate from downstream HYDRA/ML correction.

**Current stage: installable offline planning foundation (`0.1.0a1`).** The package provides campaign validation, expected issue/lead ledgers, planning reports and historical runtime inspection. Physical NextGen execution and recovery are not implemented or qualified yet. The repository also contains a completed feasibility dossier and a substantive manuscript draft. CLI examples in the original outline remain proposals except where implemented below.

## Start here

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

The example includes no scientific inputs. `plan`, `report` and `doctor` intentionally return exit code **2** when requirements remain unresolved, while providing their reports. The expected ledger contains 36 issue/lead keys, not generated discharge. Asset inspection never starts a model, downloads data or hydrates placeholders. `run` and `resume` return an explicit unavailable status. See the user guide for resource bounds, schema and exit codes.

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

The source and receipt references resolve to a private preservation snapshot; this public dossier does not include the underlying research implementation or data. The next engineering milestone is a reproducible pinned build and one complete Watauga fixture, followed by an independent reference comparison.

## Scope

The proposed product combines a browser interface and automatic input preparation with a narrowly qualified Linux runtime: continuous historical initialization, independent hourly 18-hour forecasts, explicit forcing and time semantics, verified output commits, and documented history-replay recovery. Continuous historical simulation, published-study recipes and controlled comparisons are additional design proposals recorded in the objectives. The hosted application does not exist yet; the installable commands above are the current offline foundation and future operator interface.

Existing research workspaces and the separate private HYDRA repository remain read-only throughout development. Large research archives, original model code, datasets, binaries, credentials, and cloud infrastructure are not copied into this repository.

## License status

A public software license has not been selected. See [LICENSE_STATUS.md](LICENSE_STATUS.md). This repository is not an official NOAA or CIROH distribution.
