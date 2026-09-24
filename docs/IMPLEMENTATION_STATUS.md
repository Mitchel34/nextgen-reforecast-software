# Implementation status

Planning status updated 23 September 2026; local package validation below was performed on 18 September and CI on 22 September. Package version: `0.1.0a1`. The first implementation increment is an installable **offline planning foundation**; it is not a complete reforecast generator or hosted web application.

## Implemented and locally verified

- Strict campaign JSON validation, canonical UTC issue/lead arithmetic, unchanged history-origin checks, nested output accounting and resource limits.
- Deterministic specification/plan identities and bounded resident input checks that refuse symlinks, placeholders, changed files, unknown identities and unsafe paths.
- `init`, `plan`, `ledger`, `report` and `doctor` commands with structured errors and explicit blocked states. New outputs publish atomically without overwriting existing files. The supplied template produces 36 expected keys and no discharge values.
- An exact historical V3 runtime profile and 198-entry staging inspection: two runtime artifacts, 15 source preimage/overlay entries and 181 fixture members. This is an offline identity inventory, not an executed native runtime.
- A substantive manuscript draft, claim/evidence register, verified bibliography, figure/table plan and predeclared experiment protocol/matrix. Physical results remain pending.

Validation: **54 local tests passed** on Python 3.14.7/macOS. A built wheel installed in a separate virtual environment and passed **nine CLI checks outside the source tree**. The tests cover input and time contracts, bounds, missing/corrupt assets, safe file handling, profile identity and atomic output behavior. Independent code review found a one-byte read-budget overshoot during file growth; it was corrected and covered by four regression tests. Planner support is explicitly Linux/macOS. Full details and source identities are in [VALIDATION.json](VALIDATION.json).

The [active GitHub Actions workflow](../.github/workflows/tests.yml) passed on Python 3.11, 3.12, 3.13 and 3.14 on Linux on 22 September: **54 tests passed in each of four jobs**, including fresh package installation. [Run 35765301098](https://github.com/Mitchel34/nextgen-reforecast-software/actions/runs/35765301098) tested commit `1ee028871daf00b3bb76f2416c5a2b5626ab7aee`; exact results are retained in [VALIDATION.json](VALIDATION.json). The earlier workflow-scope blocker was resolved by using the authenticated GitHub CLI credential for publication.

## Milestone progress

| Milestone | State | Next concrete completion step |
|---|---|---|
| M0 Feasibility | Complete | Preserve existing dossier |
| M1 Planning foundation | Implemented; local installation and four-version Linux CI verified | Develop versioned lead-retention and provenance extensions without weakening existing contracts |
| M2 Runtime/example closure | Inspection tools and build/closure specification implemented | Restore exact missing fixture assets; resolve unknown hashes, dependency/component source attestations and middleware loading; establish a working Linux ARM64 build environment |
| M3 Physical execution | Not implemented | Complete M2, then implement adapter and run the declared Watauga reference |
| M4 Reliability/performance | Protocol defined; physical execution not started | Implement synthetic process/commit fixtures, then qualified physical failure/replay and equal-resource trials |
| M5 Transfer/reproduction | Not started | Qualify New River and recruit an independent researcher after a complete example exists |
| M6 Manuscript | Substantive development draft and evidence scaffolding | Fill measured results from M3–M5; confirm journal requirements, authorship and declarations |
| M7 Release/submission | Not ready | Resolve license/redistribution, freeze source/image/data, archive artifacts and complete final review |

## September roadmap integration

The additional owner roadmap is [preserved with its hash](source_material/MANIFEST.json). All 24 sections are mapped in [the reconciliation](ROADMAP_RECONCILIATION.md); [18 prioritized work packages](DEVELOPMENT_BACKLOG.md) define owners, dependencies, tests and a conditional first ten-working-day cycle. The [manuscript plan](../paper/DEVELOPMENT_PLAN.md) maps questions, sections and figures to required evidence; the claim register now contains 45 claims after the 23 September literature update. These planning/source-review changes do not change the planner/runtime code or physical qualification status.

The [EM&S reading and writing guide](../paper/RELATED_WORK_AND_WRITING_GUIDE.md) adds nine selected journal references, verified bibliographic records, source-access limits and guidance for every major draft section and planned visual. The draft now aligns with the plan's five research questions and distinguishes browser usability from operator reproduction. The journal guide again returned HTTP 403 on 23 September; formatting compliance remains unverified. No new model execution, software tests or user-study results are claimed by this documentation update.

## Open physical and publication dependencies

The [23 September product objectives](PRODUCT_OBJECTIVES_AND_USER_JOURNEYS.md) record nine objectives and seven researcher journeys, separating owner direction from research-informed proposals. A hosted graphical interface, minimal location/date/lead inputs and automatic preparation now define the intended product. Proposed WEB-01–WEB-07 packages and the [UX evaluation protocol](UX_EVALUATION_PROTOCOL.md) supplement the engine backlog. No web code, scientific acquisition, model execution, deployment or user study was performed for this documentation update; existing validation counts and physical status are unchanged.

The [CFE drainage mapping review](CFE_PARAMETER_FINDING.md) verified the upstream `mean.slope` to `mean.slope_1km` generator change and recomputed prior isolated-CFE saved results: Watauga median inherited excess is +102.838% in the first 18 post-warmup hours and +2.485% over 52 evaluation weeks. This separate source experiment is not a new public-runtime test or a coupled reforecast result. M2 now also requires resolving source-field semantics and deployed-library identity before qualifying a release configuration. Any adopted parameter correction requires new configuration identities, antecedent history and references; the historical profile remains unchanged.

The preserved Watauga fixture inventory has **132 dataless members**; **131 member hashes remain unresolved** in the current source records. A separate complete production history uses a different origin and is not a valid substitute. The 18 September environment check found no responding local Docker daemon; this has not been rechecked for the roadmap update. Complete component/toolchain identities, library loading, data redistribution and a project-wide release license remain unresolved. The official journal guide returned HTTP 403, so journal-specific compliance is not certified.

`run` and `resume` explicitly return unavailable. No hydrologic model, native build, cloud resource, paid job, manuscript submission or external maintainer message was executed for this public-package increment; the separately reviewed prior isolated-CFE investigation is identified above. Original Reforecast/HYDRA/thesis workspaces remained read-only. Original outline files and the completed feasibility dossier remain unchanged.

The next implementation slice should close the exact Watauga fixture and native build while developing synthetic process/commit/replay mechanics locally. It must preserve the origin, scientific treatments, component restrictions and `math.isclose` comparison rule declared in [the protocol](../benchmarks/PROTOCOL.md).
