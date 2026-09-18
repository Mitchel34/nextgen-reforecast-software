# Checks actually performed

Investigation date: 18 September 2026 UTC. Four specialist lanes covered runtime/state, forcing/domain/example, packaging/upstream/license and an independent benchmark review; the coordinator reconciled the evidence and repository publication.

## New read-only checks

- Read the six supplied outline files and verified the five payload hashes and byte sizes against the original `MANIFEST.json`; copied those five files plus the manifest unchanged into `nextgen_Software/` in a separate checkout.
- Inspected the organizing Reforecast folder's Git status and no-commit state with `GIT_OPTIONAL_LOCKS=0`; followed its existing `GITHUB_REPOSITORY.md` to the separate private preservation checkout. The latter's HEAD is `2d813c8637ebbe581a1fbe250c2fcc7c4d040684` and its status checks were clean. This is a preservation commit, not an engine revision.
- Read selected resident source, manifests, contracts and historical receipt fields without importing or executing project modules. Used the resident Work preservation copy where the Documents/Desktop copy was dataless. Exact source hashes, flags, aliases and inspections are in `runtime_checks.json`, `forcing_checks.json`, `SOURCE_VERSION_MAP.json` and `MINIMAL_EXAMPLE_MANIFEST.json`.
- The runtime lane calculated 47 bounded resident file hashes, totaling 2,318,780 bytes, and compared relevant identities with retained manifests. Some modules were hash-inventoried rather than reviewed line-by-line; their entries say so.
- The forcing lane inventoried candidate fixture members and named production assets, computed bounded resident hashes, compared selected source and static manifest identities, and checked UTC interval arithmetic. Large full-history CSV contents were not reread or rehashed. The fixture residency and missing data are explicit, not hidden behind source locators.
- Independently read and hashed six small benchmark/production receipts, matching all six sizes and hashes against the preserved source map. `benchmark_receipts.json` contains selected fields with source identities. These are newly verified receipt bytes, not freshly executed models or a revalidation of every original raw event/output.
- Queried live official GitHub metadata, commits, trees and selected source/license files for six upstream projects. Pinned commit URLs, source hashes and interface references are in `UPSTREAM_OVERLAP_AND_LICENSES.md` and `packaging_checks.json`. No upstream source implementation was copied into this repository.
- Captured and compared metadata for 9,117 entries in the protected organizing Reforecast folder, including Git metadata. No additions, removals or differences in mode, size, mtime, ctime, inode or file flags were observed. Atime was intentionally excluded; this is a metadata comparison, not a full scientific-data rehash. The snapshot began after initial read-only inventory and before the parallel source investigation.
- Validated dossier JSON/CSV structure, checked required deliverables, reviewed claim/version consistency, scanned publication files (including Word XML) for common credential formats and checked local Markdown links. The six original supplied files were hash-checked again after staging.

## Authorized new outputs and publication

Writes were restricted to the new feasibility report directory in the software-outline workspace, the new separate public-repository checkout and temporary coordinator-only metadata snapshots. Git initialization, commits, remote creation and pushes were performed only for `Mitchel34/nextgen-reforecast-software`. The user's explicit repository-publication request supersedes the older no-publication instruction preserved in the original prompt. The existing private HYDRA repository was not changed.

The public folder name `nextgen_Software` is the user's requested label. The source was the attached workspace `NextGen_Reforecast_Software_Outline`; no exact pre-existing `nextgen_Software` directory was found in the initial nearby search. The six supplied originals remain unchanged. The root README records that their prior repository-status statements are historical.

## Failed or limited checks

- An initial GitHub CLI query requested an unsupported `visibility` JSON field; it failed without mutation and was corrected to `isPrivate`.
- A broad filename-only Documents search was interrupted without opening source contents; targeted paths and manifests were used instead.
- The Desktop source `git rev-parse` stalled and was stopped at 15 seconds. Its metadata was found dataless and was not retried. Current Desktop HEAD/dirty state remain unavailable; preserved historical identity is labelled historical.
- The first upstream metadata calls used trailing-slash endpoints and returned 404; canonical endpoints succeeded. An unneeded `CIROH-UA/ngiab` lookup returned 404; the documented `NGIAB-CloudInfra` project was then inspected.
- Placeholder source/receipt/example files were skipped. Missing original receipts were not upgraded from README claims to inspected execution evidence. There was no deliberate hydration or repeated forced read.
- Public credential-pattern scanning is a bounded check, not a proof that arbitrary secrets cannot exist. Generated dossier paths use logical aliases; the original owner-supplied documents preserve their original source-path prose.

## Not performed

No hydrologic simulation, forecast generation, ML training/inference, native compilation, dependency install, test suite or existing project script was executed. No dataset, full review ZIP or large prediction array was copied/downloaded for this task. No container was pulled/started, cloud resource created, cloud cost incurred, maintainer message sent, model parameter changed, public license selected, new scientific fixture generated or independent researcher reproduction completed.

No claim is made of complete portable checkpointing, complete data redistribution rights, exhaustive transitive-license review, full binary/source attestation, universal platform support, forecast skill, equal-resource speedup, new journal acceptance evidence or a finished reusable generator. The investigation stops with this dossier and prioritized extraction recommendation as instructed.
