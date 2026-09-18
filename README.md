# NextGen Reforecast Software

A research software project for constructing auditable NextGen reforecast campaigns with shared historical state and independent forecast branches.

**Current stage: software design and extraction feasibility.** This repository starts with the supplied project outline. It does not yet provide an installable generator, a qualified public runtime, or a complete independently runnable example. CLI examples in the outline are proposals.

## Project material

- [Software and manuscript outline](nextgen_Software/SOFTWARE_AND_MANUSCRIPT_OUTLINE.md)
- [Formatted outline](nextgen_Software/SOFTWARE_AND_MANUSCRIPT_OUTLINE.docx)
- [Investigation instructions](nextgen_Software/AGENT_INFORMATION_REQUEST.md)
- [Preserved source inspection notes](nextgen_Software/SOURCE_INSPECTION_NOTES.md)

The six original files under `nextgen_Software/` are preserved byte-for-byte. Statements in those original documents about repository creation describe their preparation date. Repository creation and publication were subsequently authorized by the project owner.

## Scope

The proposed tool separates reforecast generation from downstream forecast correction and evaluation. The initial design targets a narrowly qualified Linux runtime with continuous historical initialization, independent hourly 18-hour forecasts, explicit forcing and time semantics, verified output commits, and documented history-replay recovery.

Existing research workspaces and the separate private HYDRA repository remain read-only during this investigation. Large research archives, original model code, datasets, binaries, credentials, and cloud infrastructure are not copied into this repository.

## License status

A public software license has not been selected. See [LICENSE_STATUS.md](LICENSE_STATUS.md). This repository is not an official NOAA or CIROH distribution.
