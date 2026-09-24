# First physical experiment decision

Recorded 24 September 2026. This is a planning decision for RF-005A, RF-008, RF-009A/B, RF-010 and E03. It resolves ordering ambiguities in the saved plan, whose prior bytes are bound by [2026-09-24_BASELINE.json](planning/2026-09-24_BASELINE.json) at commit `78cfb92db53b6d58d8b8de9d056e067597f568f5`. It authorizes no acquisition, native build, model run or cloud resources by itself. No physical result is recorded here.

## Decision and scope

The first physical task remains **restoration and diagnostic reproduction of the original Watauga 786-hour/two-issue baseline**, starting with the independent sequential-reference phases of existing E03. The next implementation assignments must follow the staged prerequisites below. [Protocol 0.3](../benchmarks/PROTOCOL.md) and [EXPERIMENT_MATRIX.json](../benchmarks/EXPERIMENT_MATRIX.json) implement this order without adding runs or changing numerical criteria.

The baseline has a known CFE drainage-attribute concern. RF-005A may admit it for diagnostic reproduction only after its source mapping, original values, transformations, configuration and loaded-library identities are bound and the concern is explicit. Reproducing that baseline answers whether the released execution method preserves its declared experiment. It does not decide which parameterization should be released for new scientific studies.

RF-005B's original/candidate coupled comparison follows availability of the reference executor. It requires a separate predeclared manifest and invocation allowance. A candidate change evolves a new antecedent trajectory from the original origin and receives new configuration/profile and reference identities. Neither historical reference agreement nor the prior isolated CFE sensitivity result certifies the corrected coupled candidate.

## Bound experiment

| Item | Fixed value |
|---|---|
| Domain and output | Watauga; 31 catchments; USGS `03479000` at nexus `1017693` |
| Original history origin | `2021-12-01T00:00:00Z` |
| Issues, in order | `2022-01-01T23:00:00Z`; `2022-01-02T00:00:00Z` |
| Historical updates before each issue | 767; 768 |
| Parent historical stop, exclusive | `2022-01-02T18:00:00Z`; 786 total updates |
| Forecast provider labels | Each issue + 0 through 17 hours |
| Forecast targets | Each issue + 1 through 18 hours |
| Expected archived-forecast keys | 18 per issue; 36 unique gauge/issue/lead records |
| Model treatment | Original pinned SLOTH/NoahOWP/CFE and channel-only t-route, with original parameter and weather treatments |
| Physical invocation envelope | 4 total vCPUs; 8 GiB whole-job memory; 4 GiB generated output; 1,800 seconds |
| E03 allowance | Five variants, one invocation each; no extra pilot or candidate-sensitivity runs implied |
| Discharge comparison | Symmetric `math.isclose`, relative `1e-5`, absolute `1e-6` m³/s; complete keys and finite/nonnegative discharge |

The full 786-hour history belongs to the parent/control workload and bound input coverage. Each independent issue reference integrates from the original origin to that issue, then its 18 forecast intervals. It is not required to append extra historical steps after the forecast. This preserves the existing reference workload.

## Staged prerequisites and evidence

| Stage | Required before entering | Evidence produced; downstream use |
|---|---|---|
| Build and loader admission — RF-008 | Complete permitted source/preimage/overlay, toolchain, component, routing and dependency identities; bounded build recipe; working Linux ARM64 environment | Clean build attestation, actual loaded-artifact identities and loader resolution; startup/profile/thread guards; enforced whole-job bounds. This establishes readiness to test physical behavior, not physical equivalence |
| Input and diagnostic admission — RF-005A/RF-009A | Exact original geometry, configuration, parameters and historical/forecast input bytes; source/rights/transform records; content and interval validation; named diagnostic purpose | Sealed execution-input manifest and original baseline treatment; known CFE concern retained. Existing historical reference identities remain preserved |
| Independent reference generation — RF-010 / E03 variants 1–2 | Both admission records; E02 mechanics and resource-enforcement prerequisite; exact reference recipe and clock tables; no shared branch-controller dependency | Separate processes initialize at the same original origin and generate issue-specific reference outputs. Check clocks, complete keys, finite/nonnegative values and successful process completion; seal generated references and receipts |
| Complete baseline E03 — variants 3–5 / RF-011/RF-009B | Valid sealed references; control/branch implementations and their own admitted inputs | Uninterrupted-history control, same-weather shared branches, archived-weather shared branches; complete comparisons and parent/sibling diagnostics. Only a complete passing E03 opens its dependent physical groups |
| Candidate parameter qualification — RF-005B | Available reference executor; separately frozen paired experiment, candidate identity, original/candidate histories and explicit run allowance | Coupled sensitivity evidence and parameter disposition. A profile adopted for release requires its own applicable reference, equivalence and reliability evidence |

The future runner must distinguish input admission from outputs pending generation. A new reference hash is legitimately absent before reference generation; unknown required input identities are not. Once a reference is generated, its hash is sealed before any comparison consumes it. Existing historical output identities are never overwritten with new hashes; if historical bytes are used as a comparison target, their integrity and scientific compatibility must be checked first.

The current offline `doctor` remains a historical-profile inspector and still cannot admit physical execution. These stages specify future tooling and review evidence; changing documentation does not alter its behavior.

## E03 order and stop conditions

1. Run `sequential_reference_issue_1` within its existing invocation allowance. It initializes independently, consumes the exact history to issue 1, switches to issue-1 weather and emits its 18 targets. Validate and seal its receipt/output.
2. Run `sequential_reference_issue_2` independently under the same rules for issue 2; validate and seal it.
3. Run `uninterrupted_history_control`, preserving the complete declared historical trajectory.
4. Run `same_weather_shared_branches` and compare against the corresponding sealed control evidence.
5. Run `archived_weather_shared_branches` and compare all 36 keys against the two independent references.

Preserve failed attempts and stop dependent work on an unexplained clock, identity, lineage or numerical failure. A deadline or memory-limit failure remains a failure. Extra physical attempts, a larger envelope or a new treatment require a recorded protocol amendment before running them; they cannot consume an unrecorded retry allowance. E03 reference generation alone does not constitute a passing E03 or permit performance/recovery claims.

If any exact execution input cannot be restored, the first physical task remains **blocked** with the missing fields and source path recorded in a safe closure report. Do not shorten the original history, use 2018 production inputs, replace real forcing with synthetic weather, or insert the proposed compact 20-hour fixture under this experiment's identity. Propose a separate fixture and protocol decision, preserving the historical baseline and explaining what claims the alternative can support. A compact integration fixture would not establish hydrologic convergence merely by running successfully.

## Transition to reproduction and release

Use [RELEASE_SEQUENCE.md](RELEASE_SEQUENCE.md) after the applicable profile and evidence are ready. An immutable, licensed and accessible **REPRODUCTION_CANDIDATE** enters E09; independent reproduction therefore does not depend on an already completed final release. The frozen example preserves its experiment identity, while its supported variation receives a new linked identity and explicit differences. Changes after evaluation produce a new candidate and relevant retests, retaining the earlier record.

The final release depends on candidate reproduction, admitted browser-user evidence under [UX_EVIDENCE_CONTRACT.md](UX_EVIDENCE_CONTRACT.md), and disposition of fixes/retests. Browser-user sessions are separate from physical E09's six-invocation ceiling. None of these planning stages recruits participants, runs models or publishes a final release.
