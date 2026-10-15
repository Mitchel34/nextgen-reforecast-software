# Selected first matched manual/software trial

**MWP-WAT-V2-01, selection specification v0.1, 15 October 2026.** Select the public Watauga v2 two-issue diagnostic as one warm-resident-input paired procedural pilot. This fixes the workload, endpoint, comparison and measurement rules before observations. The [machine-readable selection](selected-trial-watauga-v2-01.json) binds the exact profile and reference identities. **Selection is complete; execution admission is blocked.** Final adapter, instructions, installation, environment and observation hashes remain required before sealing the actual trial manifest. No model calls, runtime starts, downloads, held-out accuracy work or spending are authorized by this selection.

The question is whether campaign automation reduces researcher effort and turnaround while producing the same verified product with the same backend work. This first pilot checks measurement mechanics. It cannot establish a general speedup, independent researcher reproduction, annual throughput or superiority of a hosted interface.

## Fixed first workload and endpoint

| Item | Selected value for both arms |
|---|---|
| Trial/block | `MWP-WAT-V2-01` / `MWP-WAT-V2-01-B01` |
| Site | USGS `03479000`, Watauga, selected routed feature `wb-1017693`; full-reach surrogate for the interior gauge |
| Domain axes | Exactly the pinned 31 catchments, 12 nexuses and 31 routed reaches; preserve all axes |
| Original cold origin | `2021-12-01T00:00:00Z`; identical declared cold states, parameters and forcing/time treatment |
| History job | 786 hourly provider updates; stop `2022-01-02T18:00:00Z` exclusive |
| First forecast | Issue `2022-01-01T23:00:00Z`; 767 antecedent updates plus 18 forecast updates = 785; stop `2022-01-02T17:00:00Z` exclusive |
| Second forecast | Issue `2022-01-02T00:00:00Z`; 768 antecedent updates plus 18 forecast updates = 786; stop `2022-01-02T18:00:00Z` exclusive |
| Backend work | Three independent cold-origin jobs in history/first-issue/second-issue order; 2,357 total hourly land updates and 28,284 five-minute routing steps per reach across the three jobs; six native/router stages per arm |
| Generated population | All 36 site/issue/lead/valid-time rows, leads 1–18; valid time = issue + lead |
| Retained product | Leads 1–6 for both issues, 12 rows, selected only after all physical output checks |
| Common endpoint | Fresh accessible **verified export directory**, with result manifest and complete retained payload; no ZIP or browser-download claim |

Use exactly `watauga-public-rebuild-v2`: the profile file SHA256 is `163f4c3067d38f09d671140bdab8493d51741d97b32e3e22d073f92259392ba0`; scientific configuration is `e05ec5ed5ceea3d5894e6691f7120f75aea1db6d951c9585b34b4ea34fd5dee6`; independent reference set is `3ac59c420b3b96a5c45f2dea53dc149524e496a5063356944246cf08c25963d2`. The profile binds every case-input and reference file, native export, middleware, image, routing source, units, warning inventory and scientific treatment. Input paths may move together; bytes may not change. Source identity is not proof of present residency: preflight must reverify the actual resident assets used.

This is the smallest currently supported case with independently sealed physical references **and** a successful public installed-package execution. See [reference results](../docs/PUBLIC_WATAUGA_REFERENCE_RESULTS_V2_2026-10-10.md), [execution acceptance](../docs/PUBLIC_CAMPAIGN_EXECUTION_RESULTS_2026-10-11.md) and [execution contract](../docs/PUBLIC_CAMPAIGN_EXECUTION_CONTRACT.md). Those are prior results, not new measurements. Prior HYDRA candidate campaigns have different periods, issue populations and initialization histories; they cannot be the two arms or supply a speed denominator. Shared site names, catchment counts or native exports do not establish identical geometry/configuration. Historical New River/Watauga production domains and the unequal-CPU 1,213/490-second weekly comparison are separate evidence.

## Fair manual baseline and software arm

Freeze the existing core at `95424895a4e7cc55891fc4ed2a3872bb2a464880` as the baseline candidate. Common physics, safety checks, stage execution, normalization, full-array audit and archive/export code are shared. Bind any additional manual bridge and observer wrapper by source hash before the actual trial. A core-code change requires a prospectively recorded candidate revision and affected offline checks before launch.

The manual baseline is a capable operator using a safe **one-job-at-a-time helper**, as in the prior independent reference workflow. It is not unnecessary hand editing or six invented human steps because six physical processes exist. The helper may enforce/stage/reserve/run/check native and routing work within the one explicitly selected job. It must not automatically submit the next job or call the software's whole-campaign orchestrator. The operator explicitly submits and reviews history, then each forecast, then finalizes the campaign. The software arm submits the complete campaign once and performs that orchestration automatically. Both arms receive the same task, templates, validators, mandatory reviews, export and documentation quality.

| Task category, in order | Manual path | Software path |
|---|---|---|
| Scope confirmation | Confirm the prescribed site, origin, two issues, full leads and retained projection | Same |
| Preparation | Create the declared campaign, bind the resident bundle and pass the common preparation/admission checks | Same public `prepare` behavior |
| Fresh attempt | Initialize its new claim, six-stage ledger and output/archive/export namespaces | Same fresh-identity requirement |
| Generation | Explicitly submit one job; inspect its genuine completion/check receipt; repeat for the other two jobs | Submit the complete campaign; observe its automatically ordered jobs and genuine status |
| Verification/archive | Invoke the common finalize/audit/atomic-commit helper after all three captures exist | Same finalize/audit/atomic-commit checks within the campaign workflow |
| Delivery | Independently verify the completed result, export to a fresh directory, verify and inspect accessibility | Same endpoint and checks |

Each observed meaningful decision, submission, inspection, correction or recovery action receives an event ID and task/job label. Repeated actions count when actually performed. Command count, keystrokes and code lines are not step counts. Automated internal operations are not human actions. These categories specify the task, not an observed number of steps. Preserve help, mistakes, first assistance and every actual action rather than forcing a target count.

**Manual bridge blocker:** current low-level tools exist, but the published reference driver depends on its historical private layout and completed ledger. The common archive layer requires genuine campaign `CAPTURE.json`, per-case `HOST_EXECUTION.json`, stage reservations, container/cgroup evidence and inventories. Implement and fixture-test a bounded per-job/manual capture-and-finalize bridge; never fabricate these records or relax archive acceptance. Do not rerun the historical ledger. The bridge and exact executable manual instructions are not yet delivered by this planning task.

## Cache, environment and resource control

Use one dedicated already installed local Linux ARM64 runtime and the same Mac host/guest configuration in both arms. Freeze actual OS/kernel/architecture, VM allocation, Python/dependency versions, runtime socket alias, installed wheel/tree hashes and all adapter/instrumentation hashes in the final manifest. Current presence and availability have not been rechecked by this selection. Model image digest is `sha256:2e75ab75ad1ce8de7755b84b1428ace2b99b8a51a2bb07b0b8970f4ddfd62bff`; runtime identity is `9f3a32d9bb9cf5214b99bf84e40230a2d83deeeb6c27430bd37f00a9ca02578d`. No image pull/build or alternate runtime is allowed.

Each arm starts with the same verified resident fixture/runtime/reference bytes and no completed-result reuse, land checkpoint reuse or forecast-state carryover. Each logical job uses a fresh cold process/container; the origin is preserved. A documented common asset preflight is outside the task timer; the normal operator preparation checks remain inside it for both arms. Host/guest page caches are retained, uncontrolled and disclosed. Do not flush caches or run hidden model warmups. Fresh directories do not imply cold cache. Fixed order can warm the second arm, so one pair supports procedural observations only.

| Prospective enforced bound | Value |
|---|---|
| Concurrency | One active logical job, no simultaneous arms or competing numerical workloads |
| Model container | 2 CPU hard quota, 8 GiB memory/swap limit, 256 PIDs, numerical threads 1, no network/host mounts, read-only root; same existing isolation settings |
| Model allowance | Exactly six stage reservations per arm, **12 total**; zero warmups, extra repairs, retries or fault-injection runs |
| Logical-job deadline | 1,800 seconds across native/router and the associated operations counted by the pinned job timer; setup/host work is additionally subject to the outer arm stop |
| Outer stops | 7,200 seconds per timed arm; 14,400 seconds aggregate timed arms, including human waiting/interruption; require an independently tested stop/cleanup mechanism |
| Generated bytes | 1 GiB/job, 4 GiB/arm, 8 GiB aggregate new outputs |
| Runtime/staging and disk | 12 GiB aggregate footprint ceiling; 8 GiB host free-space floor, including archive/export copies in accounting |
| Shared-host admission | No competing numerical qualification/recovery job; pause before starting if load1m >= 8 or reported free memory < 20%; monitor during work, retain pressure-related aborts |
| Cost/acquisition | $0 new paid resources; no cloud provisioning, downloads, image pulls/builds or training |

These are ceilings, not turnaround estimates or proof the case fits. The old profile's repair reservations do not grant this trial extra stages. Freeze fresh per-arm allowances and an aggregate 12-stage guard. No old claim, result, failure or ledger may be deleted/reset. Use separate campaign aliases `mwp-wat-v2-01-manual` and `mwp-wat-v2-01-software`, with fresh lock/run/protocol identities while the scientific workload remains identical. If pressure or another project needs the host before a subsequent job, abort the attempt and retain it; do not silently remove waiting time or resume into a performance pair.

## Timing and human observation rules

Assign one trained operator familiar with both paths, using the same prescribed task and equivalent documentation. A separate observer records human events with consent, pseudonymous IDs and controlled private evidence. Allow one common 20-minute documentation orientation covering both paths before the pair; record its actual duration and prior familiarity separately. It is excluded setup cost in this warm-resident pilot, not a model warmup or practice trial. Freeze **manual then software**, one assigned attempt each, with the learning/cache/order limitation explicit. Later estimation needs separately approved repeats and counterbalanced order. An agent-only execution leaves human actions and hands-on time `null`; it is not an observed researcher trial. A developer/operator pilot does not establish independent researcher reproduction.

| Clock or metric | Frozen boundary/interpretation |
|---|---|
| Total turnaround, primary wall metric | Start at the observer's task-reveal event; the operator begins immediately. End only after fresh export verification and accessibility inspection. Include ordinary help, waits, overhead, failures and interruptions. Record UTC provenance and one monotonic clock per attempt. |
| Acquisition | Excluded by the warm-resident stratum; record `not_applicable: resident-inputs`, not an invented zero download time. |
| Preparation | Task start through successful common resident-asset checks and fresh lock/namespace setup; no scientific input editing. |
| Generation/capture | First admitted job setup through raw capture, normalization and cleanup for the last of the three jobs; preserve individual native/router and per-job timings. Mandatory within-job checks remain included. |
| Verification/archive | Complete physical audits, exact independent-reference comparison and atomic archive commit, followed by independent completed-result verification. |
| Export | Fresh export publication, required fresh verification and accessibility inspection. |
| Human effort | Observe mutually exclusive active hands-on, system-wait and interruption intervals on a separate axis; retain unclassified gaps. An activity may overlap a running system phase; do not add the two axes together. Missing records remain null with reasons. |
| Compute | Report native/router stage wall times and the scope-labeled cgroup CPU deltas actually measured. Existing snapshots omit later normalization and host verification; never call them whole-workflow CPU. Record container memory and host-verifier memory separately, identifying sampling versus true peaks. Whole-workflow CPU/I/O stay null unless a validated descendant-inclusive collector is added. |
| Monetary cost | No new paid resource; attributable observed charges remain null without accounting evidence, not inferred from CPU quota × wall time. |

**Observer blocker:** current CLI `run` combines `execute_campaign` and `commit_result`. Its full duration is execution-plus-archival work. A source-bound observer boundary/wrapper must expose the genuine execution/finalization transition and be fixture-tested before reporting separate phases. Shared instrumentation overhead remains in total wall time. The current recorder expects ordered phases, so its `generation` interval must follow the boundary above; pure model-stage durations are separate nested evidence.

The existing recorder also requires all five phases for a completed attempt. The observer adapter must represent acquisition's excluded/not-applicable status explicitly without turning a bookkeeping interval into observed download time or inventing a measured zero. Until that fixture-tested representation exists, the final phase record is blocked.

## Exact product success and failure handling

Each arm must independently reproduce the sealed references for **all** catchment fields, nexus flows and routed flow/velocity/depth, including complete antecedents. Require exact canonical axes, clocks, units, metadata and numeric values. Only the already permitted prospective protocol-envelope identity differs in the full-array comparison. The inherited generic discharge tolerance does **not** relax this exact diagnostic gate.

Require all 36 unique expected site/issue/lead/valid-time records before the 12-row export. Units remain `m3 s-1`, quality remains `unqualified_diagnostic`, and the full-reach/cold-state/weather/parameter limitations remain disclosed. Independently verify every manifest-bound byte and the final export. Compare scientific product fields exactly across arms; only `run_id`, `execution_lock_sha256`, `protocol_identity_sha256` and exported `result_identity_sha256` may differ where present. Other scientific/runtime/reference identities may not be dropped. Preserve raw hashes even when canonical comparison is used. The old 203-file count is historical; freeze required payload classes rather than forcing a future receipt count.

Fail on missing/duplicate/extra keys, changed inputs/runtime, fatal or incomplete native output even with exit 0, unexpected warnings, nonfinite values, reference mismatch, corruption, lost enforcement, extra stages or breached time/memory/output/disk limits. Quiesce owned model work safely and retain genuine partial/failure evidence and occupied reservations. Do not publish a completed pointer/export for an incomplete result. Stop the paired block on either arm's failure; preserve both assignment outcomes and spent allowance. An unstarted second arm remains unattempted. There is no automatic retry/resume or physical recovery claim. Any repair/retry is a separate prospectively amended protocol and approval; its first failure remains in the record.

## Launch blockers and exact future approval

Before seeking the final run approval, complete: (1) the reviewed manual per-job/capture/finalize bridge and executable instructions, with no campaign-loop shortcut; (2) fixture-tested observer and outer/aggregate resource guards; (3) verified installed candidate/adapter/tool hashes and actual resident assets/image/environment; (4) operator/observer consent and observation policy; and (5) the final actual trial manifest, expected fresh per-arm lock hashes and planned **absent** claim/ledger/output namespace bindings. Timed preparation must produce the expected lock bytes at a fresh path. Create durable claims and stage reservations only during the specifically authorized attempt through the approved bridge/executor; precreating a claim would consume/refuse the intended run. Do not spend native calls to discover these software prerequisites. Current selection status is `blocked_not_authorized`.

The concrete request, **after those prerequisites are reviewable**, is:

> Authorize MWP-WAT-V2-01-B01: one manual-then-software warm-resident Watauga v2 paired pilot, using the fixed 786/785/786-hour jobs and 36 generated/12 retained rows. Permit only a required start of the existing dedicated local runtime, one active 2-CPU/8-GiB job, 1,800 seconds per logical job, the 7,200-second arm/14,400-second aggregate timed stops, 1-GiB/job, 4-GiB/arm and 8-GiB total generated outputs, a 12-GiB runtime/staging ceiling and 8-GiB disk floor. Permit at most six native/router stages per arm, 12 total, zero repairs/retries/warmups, $0 new paid resources and no downloads/pulls/builds/cloud/training. Retain every outcome and stop on admission, integrity, pressure or resource failure. Human measurements require the separately agreed operator/observer consent.

This planning request grants none of that execution authority. Approval cannot waive missing scientific/input/reference or enforcement evidence. No new accuracy scoring is needed for this software question.

## Later twelve-month scaling trial

Nominate the same site for UTC issues `2022-01-01T00:00:00Z` through `2023-01-01T00:00:00Z` exclusive: **8,760 issues, 157,680 generated lead rows and 52,560 retained leads-1–6 rows**. Preserve the `2021-12-01T00:00:00Z` origin and required full history through `2023-01-01T17:00:00Z` exclusive (9,521 hours). This is a target workload, not admitted assets or launch authority.

First qualify annual forcing/domain/reference coverage, a working annual executor/export, streaming complete-population instrumentation beyond the current 4,096-row pilot bound, and separately budgeted time/memory/storage. Select one qualified backend strategy prospectively for both workflow arms; do not require an intentionally inferior manual interface or silently substitute shared history on one side. A separate serial-versus-shared-history compute study needs its own qualification and comparison. Freeze representative manual batch tooling, repeated/counterbalanced operator design and the annual resource allowance before observations. Existing annual preparation tests and this two-issue pilot do not authorize or predict annual execution cost.
