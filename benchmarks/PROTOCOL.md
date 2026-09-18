# Reforecast correctness, reliability and resource protocol

Version 0.2, 18 September 2026. **Predeclared design; no native or hydrologic experiments in this matrix have been run for the new public implementation.** This revision adds a parameter-semantics gate following review of a prior isolated CFE sensitivity experiment; it does not preregister that already completed experiment retrospectively. Version 0.1 is preserved in Git commit `f55e4e7cf30907b5867e21f2c6a207fa2eb02c04`. The matrix is a specification, not a launcher or authorization to provision resources. Offline tests may be executed by the implementation team and recorded separately. Any changes after pilot measurements must receive a new protocol revision with their reasons preserved.

## 1. Questions and evidence classes

The experiments test continuation equivalence, isolation, committed-output integrity, replay recovery, resource requirements and researcher usability. Hydrologic forecast skill and machine-learning correction are outside the primary study. A numerical failure cannot be excused by an attractive runtime, and a software refusal can be the correct outcome of an invalid input.

Use these evidence classes without promoting one into another:

| Class | Meaning | Admissible claim |
|---|---|---|
| `historical_inspected_receipt` | Preserved receipt inspected in the feasibility dossier | Only the recorded version, scope and diagnostics; raw arrays may not have been rechecked |
| `new_offline_contract` | Executed new planner, schema, asset or identity tests | The tested software contract; no hydrology or fork equivalence |
| `new_synthetic_mechanics` | Executed purpose-built process/transaction fixture | Mechanics under that fixture; no physical-model equivalence |
| `inspected_prior_isolated_cfe_sensitivity` | Prior standalone CFE run artifacts inspected and saved arithmetic recomputed | Parameter sensitivity under the recorded synthetic weather, version and state treatment; no new public-runtime or coupled-reforecast qualification |
| `new_physical_qualification` | Executed exact real-model build, inputs and reference | Qualified profile and measured scope only |
| `independent_reproduction` | Non-developer researcher completes frozen release on qualified clean environment | Observed reproducibility, assistance and usability within that case |

The feasibility dossier remains immutable historical evidence. Its weekly V2 binary and V3 day-custody binary are different; neither certifies a new build. Its 1,213 s / 490 s comparison changes CPU allocations and is not an equal-resource benchmark. New experiment records must never reuse a historical duration as their own result.

## 2. Admission and bounded execution

Before physical execution, seal a run manifest with exact source commit, clean/dirty status and patch identity; framework preimages; all component, middleware and executable hashes; container digest; compiler/dependency identities; CPU architecture; kernel; runtime threading settings; domain/parameters/forcing/reference hashes; source access and redistribution terms; experiment variant; protocol version; limits; and command arguments. Absolute developer paths must not be required for reproduction. Do not include credentials.

All required assets must be resident and verified. Missing or dataless inputs are a blocked experiment, not permission to hydrate an original workspace, substitute another initialization or download scientific data implicitly. In particular, the original Watauga fixture currently lacks 132 resident files according to the preserved manifest. Native execution also needs a working qualified Linux ARM64 environment and a complete build recipe. Current build and asset closure status must be checked before each experiment group.

**Parameter semantics gate.** Resolve the [CFE `mean.slope` / `mean.slope_1km` finding](../docs/CFE_PARAMETER_FINDING.md) for the release configuration. Bind generator and hydrofabric revisions, source-field meanings/units, per-catchment values and transformations, configuration hashes and deployed component provenance. Audit CFE drainage separately from Noah terrain slope and routing slope. The archived fixture and its references remain unchanged. An adopted correction creates a new scientific configuration and antecedent history from the original origin. Each serial/branched equivalence pair must use the same declared treatment; agreement within the inherited treatment cannot certify its parameter meaning. A paired original/candidate coupled sensitivity study needs its own predeclared manifest and invocation bounds before execution; it is not silently added to this matrix's run allowance. No public parameter-content validator or corrected profile has yet been implemented.

The initial proposed envelope is **4 total vCPUs, 8 GiB whole-job memory, 4 GiB generated-output allowance and 1,800 seconds per physical invocation**, including reference and recovery invocations. These are deliberately bounded admission values, not measured requirements or assurance that a case fits. Apply one cgroup to the parent, all children and routing descendants. CPU reservations must include parent and routing work; a host CPU count or scheduler reservation alone is not an enforced limit. Verify counters and enforcement in a synthetic admission test. An environment that cannot provide the stated limits leaves physical cases blocked.

Local synthetic groups have a proposed 120-second per-invocation deadline and a maximum of 12 processes. Start with the smallest admitted smoke/reference case; do not automatically exhaust the entire matrix if it fails. A group fails on an unexplained numerical or lineage difference. Deadlines and out-of-memory outcomes are retained as failures; increasing an envelope requires a new recorded protocol amendment before restarting the affected comparison. No paid infrastructure, fleet, cloud transport or dataset acquisition is part of this protocol.

`EXPERIMENT_MATRIX.json` states the maximum invocation count for each group. Additional fixtures, treatment combinations, debugging runs and parameter searches are not silently part of that bound. Diagnostic runs can be recorded separately but must not replace adverse production trials.

## 3. Exact first physical fixture

Use the original Watauga V3 qualification recipe after exact restoration and sealing:

| Item | Bound value |
|---|---|
| Domain | Watauga, 31 catchments; gauge `03479000` |
| Original origin | `2021-12-01T00:00:00Z` |
| Issue list | `2022-01-01T23:00:00Z`, `2022-01-02T00:00:00Z` |
| Parent historical stop, exclusive | `2022-01-02T18:00:00Z` |
| Historical updates | 786 |
| Forecast provider labels | issue + 0 through 17 hours |
| Forecast targets | issue + 1 through 18 hours |
| Expected rows | 36 unique gauge/issue/lead records |
| Physical profile | Pinned SLOTH/NoahOWP/CFE; channel-only t-route; original parameter and forcing treatments |

The first branch starts after 767 historical updates; the second after 768. Their terminal forecast targets are 2022-01-02 17:00 and 18:00 UTC, respectively. The parent still performs all 786 historical steps. Do not shorten the origin, extend the issue count, or substitute the separate 2018-origin production history while retaining this case name.

The independent sequential reference must use a separately initialized process per issue, consume the exact same historical bytes from origin to issue, and then consume the exact issue-specific forecast bytes. It should bypass the shared-history fork path. Independently validate its clock and forcing adapter against explicit fixture tables. Shared model libraries are acceptable and must be declared; shared branch-controller logic is a confounding dependency. A same-weather uninterrupted-history control is additional to the archived-forecast comparison, not a replacement for it.

## 4. Endpoints and decision rules

**Identity and coverage.** Require exact source/runtime/domain identities; unique `(domain, gauge, issue_utc, lead_hours, target_utc)` keys; exactly 18 leads per gauge/issue; exact clocks, updates and child ownership events; no uncommitted artifact counted as a forecast. Missing rows do not disappear through an inner join. Order-normalized comparisons must first verify both complete key sets. A zero-exit process alone is insufficient.

**Discharge agreement.** Reject NaN, infinity and invalid negative flow under the qualified profile. For every expected row preserve `math.isclose(candidate, reference, rel_tol=1e-5, abs_tol=1e-6)`: `abs(candidate-reference) <= max(1e-6, 1e-5 * max(abs(candidate), abs(reference)))`, with discharge in m³/s. This symmetric maximum rule must not be replaced with an additive absolute-plus-relative threshold. Retain the maximum absolute difference, its key, relative difference where the reference is nonzero, root-mean-square difference, failures and total rows. Near-zero cases are governed by the absolute threshold; do not divide by an arbitrary small constant to hide a failure. The first public qualification retains the historical comparator's rule and tolerance values; any future change requires an explicit protocol amendment.

**State and isolation.** Clocks, step counts and input cursors must agree exactly. Compare every available parent/channel state diagnostic at matched checkpoints, and distinguish those diagnostics from complete state coverage. Freeze a variable/unit-specific tolerance manifest before claiming numerical equivalence for additional land variables; unset tolerances block those claims. A branch-only forcing perturbation must alter its intended branch stimulus, while the parent and sibling continue to their unchanged references. Bitwise state fingerprints, where available, supplement continuation tests and do not prove complete hidden-state coverage.

**Commit and recovery.** Require zero-exit child reaping, complete validated data, bound hashes and atomic commit publication. Inject faults before output, after output but before commit, after commit publication, and after parent advancement. Restart from the original origin and verify every retained commit before suppressing a branch. Recovered valid outputs must agree with the uninterrupted reference and each issue must have exactly one authoritative commit. Changed configuration or missing/corrupt replay inputs must refuse recovery before a new model launch. Output existence without a valid commit is not success.

**Resource accounting.** Measure monotonic wall time; cumulative whole-job user/system CPU time; cgroup memory peak with its accounting definition; I/O counters and output bytes; forecast completions; history and branch updates; phase timings for initialization, historical advancement, branch/routing execution, validation/publication and replay. Do not sum process RSS into a claimed whole-job memory figure. If proportional set size is collected, report its sampling method and coverage separately. Include failed trials and reference cost. Separate data acquisition and preprocessing from model execution; no acquisition benchmark exists unless directly measured.

## 5. Experiments and comparisons

1. **E01 — Offline contract tests.** Verify strict UTC/hour alignment, origin/issue/horizon arithmetic, canonical identities, allowed profile, duplicate keys, unsafe asset paths, symlinks, missing files, damaged hashes, dataless placeholders and bounded reads. Each test writes only to repository-local temporary directories. Unsupported execution commands must fail clearly. Record the exact passing/failing count and environment after execution; this protocol supplies none.
2. **E02 — Synthetic process and transaction mechanics.** Use a separately authored bounded fixture with known state, readable input offsets and child-owned outputs. Exercise out-of-order completion, independent file descriptions, one branch perturbation, failed child, parent termination, deadline cleanup and commit boundaries. The fixture runner and fault hooks remain to be implemented. No synthetic discharge-shaped output is called a hydrologic result.
3. **E03 — Real Watauga references.** Compare same-weather continuation and each of the two archived-forecast branches with independent sequential references. Preserve branch/parent diagnostics and exact keys. Only if this passes may the performance and recovery groups proceed.
4. **E04 — Equal-resource execution.** Compare independent sequential per-issue reference, shared-history concurrency 1, and shared-history concurrency 2 on the same 4-vCPU/8-GiB envelope. Both shared variants perform the same complete historical interval. Report total computational work to explain the baseline's repeated initialization. Examine any qualified durable-state baseline before describing comparative advantage over the best available method. Use five paired blocks with a saved order randomized by seed `20260918`. Use one untimed warm-up per variant, retained separately, and a consistent documented warm-cache procedure. Do not drop host caches or alter unrelated processes. First-use observations can be separately labeled, but cannot be mixed with the warm-cache summary. Report each trial, median, range and paired ratios; do not claim formal population-level inference from five blocks.
5. **E05 — Child failure and issue integrity.** For each named failpoint, use a fresh output root, one controlled injection, then the intended replay recovery. Confirm unchanged previously committed outputs and exactly one authoritative commit per issue. Include one preexisting invalid commit. Repeat each variant three times to expose order-dependent failures.
6. **E06 — Parent loss and replay.** Terminate the parent after the first isolation acknowledgement, between validated output and publication, and after the first authoritative commit. Use process termination on a disposable local run; this does not simulate power loss, kernel loss or every storage failure. Measure replay work and end-to-end recovery time from a declared detection boundary. Three repeats per failpoint. Host-level recovery remains unqualified unless separately designed and executed.
7. **E07 — Source and binding corruption.** Inject missing interval, duplicate interval, shifted provider label, missing lead, nonfinite value, incorrect units, changed generation, altered runtime identity, changed domain configuration and damaged output archive/commit. Each input condition must produce an explicit expected refusal. If the new offline layer cannot inspect content, route that case to the future source adapter; do not mark it passed through file hashing alone.
8. **E08 — Second domain.** Seal a New River fixture with the same initial comparison design, two nested gauge outputs and original scientific treatments, including documented slope changes. Exact dates and hashes remain unset until an original fixture with continuous history is established. Repeat physical reference, concurrency and one replay case. Different physical geometry cannot be disguised as a configuration-only variation. This is transfer within the profile, not evidence for arbitrary basins or parameterizations.
9. **E09 — Independent reproduction.** An independent researcher uses a frozen source release, qualified platform, sealed fixture and published instructions without private paths or unpublished help. Record environment, attempts, failures, elapsed time, questions and assistance; no personal data need be published. They complete the example and one supported issue/output variation while retaining its scientific identity. Authorship or operator role must be stated transparently; a second AI agent on the same host is not the independent researcher.

## 6. Receipts and result retention

Each executed variant gets a unique immutable run directory and a machine-readable receipt containing:

```text
schema_version, protocol_version, experiment_id, variant_id, repeat,
evidence_class, status, start_utc, end_utc, command_argv,
source_commit, dirty_patch_sha256, runtime_manifest_sha256,
campaign_manifest_sha256, fixture_manifest_sha256,
reference_manifest_sha256, host_environment, enforced_limits,
observed_limits, exit_status, stop_reason, fault_injection,
expected_keys_count, actual_keys_count, mismatch_summary,
metrics, raw_artifact_hashes, assistance_record
```

`null` means unmeasured or unknown and requires an explanatory field; zero means a measured zero. Status is one of `passed`, `failed`, `blocked`, `interrupted`; do not turn a skipped prerequisite into a pass. A run status is distinct from publication or archival status. Failed runs retain their logs and metadata with the same custody as successful runs.

The experiment matrix itself keeps `execution_status: not_started`; it is not an accumulating result ledger. Future runner/results tooling must version schemas and bind their own implementation. Publication tables must derive from retained run receipts and report coverage and failure counts, not manually transcribed best runs. Graph generation remains pending real measurements.

## 7. Publication gates

The final manuscript cannot claim a qualified runtime until E03 and the relevant E02/E05–E07 cases pass on the release build; cannot claim a measured resource advantage without E04; cannot claim demonstrated transfer without E08; and cannot claim independent reproducibility without E09. An abstract/conclusion claiming completion must be rewritten against actual receipts and the claims register. Preserve unfavorable outcomes and restrict claims if a gate remains unresolved.
