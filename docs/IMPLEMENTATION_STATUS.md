# Implementation status

Updated **10 October 2026** for the authorized [scientific-input/runtime continuation](INPUT_RUNTIME_INCREMENT_2026-10-10.md). Package version: `0.1.0a3`. The product provides offline planning and input-content validation plus a local browser interaction prototype. Automatic scientific preparation, physical execution/recovery and a hosted service remain unfinished.

## Current increment

- **Forcing contents (RF-004):** strict decoded CSV manifests and independently expected catchments/clocks; complete hourly coverage, source issue/lead labels, units, precipitation conversion and numeric validity. Default gap policy fails; explicit incomplete-forecast exclusion is recorded without accepting invalid content. Source authenticity, historical availability, decoder/grid qualification and radiation interpretation remain separate unresolved requirements.
- **CFE mapping (RF-005A):** actual bound attribute/configuration/library bytes support a drainage-only audit. Baseline `mean.slope` remains diagnostic, with known-concern and out-of-range warnings; candidate `mean.slope_1km` requires its separately declared mapping. Unknown generator revision is represented by null. No clipping, angle conversion, configuration changes or model loading occurs.
- **Watauga identity/availability (RF-009A):** verified original sealed contract resolves all 131 previously unknown hashes. Exact resident preservation copies restore 44 of 181 members to ignored private staging. The 137 unavailable members include historical/branch weather and Noah configuration; later nonmatching copies were rejected. The preserved public profile and historical manifests are unchanged.
- **Actual input audit:** all 31 restored CFE drainage values equal the bound GeoPackage's `mean.slope`, and none equals `mean.slope_1km`. The new API checks all 33 bound audit assets with zero content failures, retaining 32 diagnostic warnings and unknown source-unit/generator/loaded-library qualification. No coupled response is inferred.
- **Linux runtime (RF-008):** dedicated Linux ARM64 worker, pinned component image, exact upstream source objects and ten historical overlays acquired/verified. A bounded inert ELF dependency check resolves the exact historical native executable with the exported middleware. Full clean-build and component attestations remain incomplete. No model entry point or native compilation was invoked.
- **Manuscript:** methods, fresh source/configuration findings and the 45-claim evidence register now distinguish content checks, byte restoration, loader resolution and future physical results.

The [integrated validation receipt](evidence/input-runtime-increment-20261010.json) records tested source identities and outcomes. The macOS ARM64 and isolated Linux ARM64 suites each pass **155 Python tests**; the unchanged browser/engine contract suite passes **17 Node tests**. A separately installed wheel passes **20 CLI checks**. [Linux ARM64 test evidence](evidence/linux-arm64-input-tests-20261010.json) binds the streamed sources and bounded guest process. Public CI is tracked separately as it completes. These checks do not constitute a participant study or physical-model experiment. Cross-agent review exposed and fixed ambiguous drainage assignments, nonportable numeric syntax, numeric underflow and an understated-size read-budget loophole. A pre-existing CLI test used the system temporary directory; it now keeps writes in repository-local scratch space and passes without depending on an external `TMPDIR` setting.

Detailed receipts: [forcing contract](FORCING_VALIDATION_CONTRACT.md), [CFE contract](CFE_MAPPING_VALIDATION_CONTRACT.md), [runtime progress](LINUX_RUNTIME_PROGRESS.md), [bundle progress](WATAUGA_BUNDLE_PROGRESS.md), [actual mapping audit](evidence/watauga-cfe-mapping-20261010.json). Staged inherited payloads are private and ignored; the public records contain derived identities, aggregate findings and remaining gaps.

## Preserved prior increments

The earlier `0.1.0a2` [kickoff receipt](evidence/implementation-kickoff-20261010.json) records 80 Python tests, 14 installed-wheel CLI checks and 17 Node/browser-to-engine tests. [Linux CI run 38104732243](https://github.com/Mitchel34/nextgen-reforecast-software/actions/runs/38104732243) passed Python 3.11–3.14 and browser jobs at `bb4da34dfe1a6a84877277da474a687b5bb07a19`. [Internal browser QA](../web/QA_2026-10-10.md) exercised the local request download, errors, stale-review prevention and desktop/narrow layouts. It remains a request prototype with unknown real coverage and no execution service.

That increment implemented campaign schema 1.1 cadence schedules and retained-lead projection, expected-key ledgers, and planning provenance locks. Retaining leads 1–6 still requires all 18 physical updates and their forcing. Planning locks bind bytes and declarations without validating scientific meaning or admitting execution. The earlier [runtime admission receipt](evidence/runtime-admission-20261010.json) described a missing selected Docker socket and unresolved public fixture hashes before the separately authorized continuation; it does not describe the final state of this increment.

The September [foundation record](VALIDATION.json) remains unchanged: 54 local tests, nine installed CLI checks and [four-version CI run 35765301098](https://github.com/Mitchel34/nextgen-reforecast-software/actions/runs/35765301098) at `1ee028871daf00b3bb76f2416c5a2b5626ab7aee`. Historical validation does not test later source changes.

## Physical admission and next work

| Milestone | State | Next concrete completion step |
|---|---|---|
| M0 Feasibility | Complete, preserved | Retain dossier identities |
| M1 Planning/input foundation | Planning, provenance and bounded content checks implemented | Source-authenticated acquisition/decoding, domain resolution and complete scientific execution lock |
| M2 Runtime/example closure | Exact identities resolved; 44 fixture members staged; worker/image/exported loader checked | Recover remaining 137 exact members; close clean-build dependencies, source-to-component attestations and rights |
| M3 Physical execution | Not implemented or newly measured | Complete RF-005A/008/009A admission, then original independent Watauga reference before comparisons |
| M4 Reliability/performance | Protocol unchanged; physical measurements absent | Commit/replay mechanics, then declared physical fault and equal-resource trials |
| M5 Transfer/reproduction | Not started | Qualify New River and test immutable reproduction candidate with independent operator |
| M6 Manuscript | Formal methods and current evidence updated | Actual Q1–Q5 results, verified journal requirements and author declarations |
| M7 Final release/submission | Not ready | Rights/license closure, candidate evaluation, required fixes/retests and final archive/review |

The [working plan](WORKING_PLAN.md), [release sequence](RELEASE_SEQUENCE.md) and [UX evidence contract](UX_EVIDENCE_CONTRACT.md) continue to control dependencies. First physical work remains the original 786-hour Watauga diagnostic fixture. Resolving expected hashes does not restore missing bytes; a different origin, contemporary forcing rebuild or later production file cannot silently replace an unavailable historical member. A corrected CFE profile requires separate antecedent state, scientific identity and qualification.

`run` and `resume` remain unavailable. No model experiment, native build, hosted deployment, paid resource, recruitment, submission or maintainer message occurred in this increment. Original Reforecast/HYDRA/NextGen/thesis sources remain read-only, without hydration. Core licensing, source/domain coverage, scientific defaults and final-release evidence remain open decisions.
