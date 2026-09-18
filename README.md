# NextGen Reforecast Software

A research software project for constructing auditable NextGen reforecast campaigns with shared historical state and independent forecast branches.

**Current stage: software design and extraction feasibility.** This repository contains the supplied project outline and a completed read-only feasibility dossier. It does not yet provide an installable generator, a qualified public runtime, or a complete independently runnable example. CLI examples in the outline are proposals.

## Project material

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

The proposed tool separates reforecast generation from downstream forecast correction and evaluation. The initial design targets a narrowly qualified Linux runtime with continuous historical initialization, independent hourly 18-hour forecasts, explicit forcing and time semantics, verified output commits, and documented history-replay recovery.

Existing research workspaces and the separate private HYDRA repository remain read-only during this investigation. Large research archives, original model code, datasets, binaries, credentials, and cloud infrastructure are not copied into this repository.

## License status

A public software license has not been selected. See [LICENSE_STATUS.md](LICENSE_STATUS.md). This repository is not an official NOAA or CIROH distribution.
