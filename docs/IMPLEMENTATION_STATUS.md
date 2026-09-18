# Implementation status

Updated 18 September 2026. Package version: `0.1.0a1`. The first implementation increment is an installable **offline planning foundation**; it is not a complete reforecast generator.

## Implemented and locally verified

- Strict campaign JSON validation, canonical UTC issue/lead arithmetic, unchanged history-origin checks, nested output accounting and resource limits.
- Deterministic specification/plan identities and bounded resident input checks that refuse symlinks, placeholders, changed files, unknown identities and unsafe paths.
- `init`, `plan`, `ledger`, `report` and `doctor` commands with structured errors and explicit blocked states. New outputs publish atomically without overwriting existing files. The supplied template produces 36 expected keys and no discharge values.
- An exact historical V3 runtime profile and 198-entry staging inspection: two runtime artifacts, 15 source preimage/overlay entries and 181 fixture members. This is an offline identity inventory, not an executed native runtime.
- A substantive manuscript draft, claim/evidence register, verified bibliography, figure/table plan and predeclared experiment protocol/matrix. Physical results remain pending.

Validation: **54 local tests passed** on Python 3.14.7/macOS. A built wheel installed in a separate virtual environment and passed **nine CLI checks outside the source tree**. The tests cover input and time contracts, bounds, missing/corrupt assets, safe file handling, profile identity and atomic output behavior. Independent code review found a one-byte read-budget overshoot during file growth; it was corrected and covered by four regression tests. Planner support is explicitly Linux/macOS. Full details and source identities are in [VALIDATION.json](VALIDATION.json).

A [GitHub Actions template](../ci/tests.yml) covers Python 3.11, 3.12, 3.13 and 3.14 on Linux. GitHub rejected activation because the publishing credential lacks `workflow` scope. The template is preserved outside `.github/workflows/` so the code and manuscript can be published. Remote CI has not run; activation and platform verification remain outstanding.

## Milestone progress

| Milestone | State | Next concrete completion step |
|---|---|---|
| M0 Feasibility | Complete | Preserve existing dossier |
| M1 Planning foundation | Implemented and locally verified | Activate CI with an authorized workflow credential, verify the remote matrix and resolve any platform failures |
| M2 Runtime/example closure | Inspection tools and build/closure specification implemented | Restore exact missing fixture assets; resolve unknown hashes, dependency/component source attestations and middleware loading; establish a working Linux ARM64 build environment |
| M3 Physical execution | Not implemented | Complete M2, then implement adapter and run the declared Watauga reference |
| M4 Reliability/performance | Protocol defined; physical execution not started | Implement synthetic process/commit fixtures, then qualified physical failure/replay and equal-resource trials |
| M5 Transfer/reproduction | Not started | Qualify New River and recruit an independent researcher after a complete example exists |
| M6 Manuscript | Substantive development draft and evidence scaffolding | Fill measured results from M3–M5; confirm journal requirements, authorship and declarations |
| M7 Release/submission | Not ready | Resolve license/redistribution, freeze source/image/data, archive artifacts and complete final review |

## Open physical and publication dependencies

The preserved Watauga fixture inventory has **132 dataless members**; **131 member hashes remain unresolved** in the current source records. A separate complete production history uses a different origin and is not a valid substitute. The local Docker CLI currently has no responding daemon. Complete component/toolchain identities, library loading, data redistribution and a project-wide release license remain unresolved. The official journal guide returned HTTP 403, so journal-specific compliance is not certified.

`run` and `resume` explicitly return unavailable. No hydrologic model, native build, cloud resource, paid job, manuscript submission or external maintainer message was executed. Original Reforecast/HYDRA/thesis workspaces remained read-only. Original outline files and the completed feasibility dossier remain unchanged.

The next implementation slice should close the exact Watauga fixture and native build while developing synthetic process/commit/replay mechanics locally. It must preserve the origin, scientific treatments, component restrictions and `math.isclose` comparison rule declared in [the protocol](../benchmarks/PROTOCOL.md).
