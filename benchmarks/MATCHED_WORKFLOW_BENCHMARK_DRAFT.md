# Matched workflow benchmark draft

Version **0.1**, 15 October 2026. This version freezes the engineering design below before any new benchmark observations. It is a **draft measurement contract**, not a frozen trial manifest, an execution allowance or a performance result. A later trial must bind its actual immutable artifacts and receive the required execution authority before observation. Amendments retain this version and state the reason and affected trials.

The research question is whether the software reduces the time and effort needed to produce the **same valid reforecast product**, and whether another operator can reproduce that product. Hydrologic accuracy scoring is outside this benchmark. Preserve the existing scientific admission and output-integrity checks; no new USGS scoring gate is introduced.

## Scope and comparison

The intended researcher journey is choosing a site and historical issue period, preparing inputs, generating and verifying reforecasts, then obtaining an archive. A twelve-month single-site journey is the eventual benchmark target. The currently supported physical execution case is narrower:

| Binding | Current public Watauga v2 diagnostic |
|---|---|
| Site and routed reach | USGS `03479000`, full reach `1017693` |
| Original cold origin | `2021-12-01T00:00:00Z` |
| History stop, exclusive | `2022-01-02T18:00:00Z`; 786 hourly updates |
| Issue hours | `2022-01-01T23:00:00Z`, `2022-01-02T00:00:00Z` |
| Physical forecast leads | All 18 updates for each issue; 36 unique issue/lead records |
| Export choice | Freeze the retained leads before observation; retaining 1–6 still requires all 18 physical updates |
| Execution strategy | Three independently cold-initialized logical jobs: one history and two forecasts; six native/router stages per arm |

The [public execution contract](../docs/PUBLIC_CAMPAIGN_EXECUTION_CONTRACT.md) and exact sealed profile, input, runtime and reference identities control admission. An annual planner test does not extend that physical qualification. The public executor does not yet implement the shared-history optimization; changing the compute strategy would require a separate qualified comparison.

The first proposed comparison is **manual orchestration versus software orchestration of the same admitted backend work**. Freeze both instructions and the meaningful user actions before observing an attempt. Both arms must perform the same original history, forecast population, physical leads, checks and export. A scripted synthetic baseline exercises measurement mechanics only. An unsupported automated endpoint leaves a physical comparison blocked.

Keep these strata separate:

| Stratum | Start and endpoint |
|---|---|
| First use | Declared clean-environment setup through a verified accessible archive; record acquisition/setup costs and prerequisites explicitly |
| Warm resident inputs | Already resident, verified inputs and admitted runtime through a verified accessible archive; preparation verification remains in scope |
| Completed-result reuse | Existing completed result through fresh verification and export; no new generation is implied |

Record caches and reusable state precisely. A new output directory alone is not a cold cache. Do not flush host caches or disturb other projects. Results from different strata do not share a speedup denominator.

## Trial manifest frozen before observation

Bind a unique trial and paired-block identity, this document's version/hash, the planned question, arm order, allowed attempts and analysis rule. Freeze an exact workload identity separately from each arm's implementation identity:

The compact instrumentation contract binds the full trial manifest's SHA256. Each attempt names its paired block; cross-block attempts cannot form an eligible pair. Its JSON seal is an identity for declarations, not approval or independent authentication.

| Common to both arms | Bound separately for each arm |
|---|---|
| Site/domain, origin, complete history and issue list, source and retained leads, forcing/parameter/configuration bytes, model/component/runtime identities, reference bytes and comparison presets | Orchestration implementation commit and clean/dirty patch identity, interface/build identity and exact commands/instructions |
| Generation strategy, job/stage counts, required verification and archive contents, cache stratum and initial reusable state | Fresh attempt/output namespace, event/receipt identities and observed attempt outcome |
| Architecture/OS/runtime environment, numerical threads, enforced CPU/memory/wall/output limits, acquisition policy and shared-host admission conditions | Actual resource counters, timestamps, user actions, assistance, interruptions, failures and retries |

Enforcement evidence is required; a requested CPU count or host CPU count is not an enforced limit. An allocated-vCPU-time calculation is capacity exposure, not observed CPU consumption. Unknown host effects and different resource/cache conditions make a pair unsuitable for a matched speedup claim.

Choose order before observation, with randomization or counterbalancing for a larger study. Record learning, prior familiarity and first-attempt/retest status. Preserve every assigned attempt and every planned pair, including blocked, failed, interrupted and incomplete ones. Allow no hidden warmups, repairs, retries or exclusions. Amend the manifest prospectively before extending an allowance.

Human participation requires the declared consent/access and assistance policy. Use pseudonymous operator identifiers in publishable records. The [browser-study evidence contract](../docs/UX_EVIDENCE_CONTRACT.md) still governs participant evidence and descriptive UX claims; this draft supplies the prospective matched-design direction and does not retrospectively turn existing UX records into comparative evidence.

## Measurements and missingness

Record monotonic elapsed durations within each attempt and UTC timestamps for provenance. Separate acquisition, preparation, generation, verification and export, with explicit phase boundaries and a common end-to-end endpoint. Do not add overlapping intervals as though they were sequential. Retain instrumentation overhead and unexplained/unassigned time.

| Measure | Required interpretation |
|---|---|
| Workflow turnaround | Actual elapsed start-to-verified-archive time for the declared stratum; report failed/incomplete endpoints separately |
| Human steps | Observed meaningful actions under the frozen action taxonomy, such as selecting a scope or resolving a reported blocker; no keypress, source-line or command-line count proxy |
| Hands-on time | Observed active human intervals; distinguish system wait and interruptions without double-counting overlaps |
| Assistance and recovery | First directional assistance, later assistance, original failure, retry relationship and eventual outcome retained separately |
| Resources | Scope-labeled wall/CPU time, memory and generated bytes from supported counters; identify self-process versus whole-job/child-inclusive measurements |
| Monetary cost | Observed attributable charges and accounting basis, or `null` with a reason; no inferred invoice or price from a CPU quota |

`null` means unknown or unmeasured and requires a reason. Zero means an observed zero. Program wall time does not establish human effort, and process CPU time does not establish total model CPU. Synthetic clocks and events must remain labeled synthetic. No manual timing or completed human action may be inferred from an agent's code path.

## Product integrity and reproducibility

Before calculating a valid-output performance comparison, require the complete expected product, successful mandatory checks and retained verification evidence. Check exact site/issue/lead/valid-time keys, units and quality labels; refuse missing, duplicate, extra, malformed or nonfinite rows. Preserve full physical-output/reference checks before retained-lead export. A compact product check alone does not revalidate complete physical arrays.

Bind raw artifact hashes and canonical numerical comparison results separately. Byte identity is sufficient for those same bytes; differences in serialization require a declared canonical comparison and may not be silently ignored. For discharge in `m3 s-1`, the inherited prospective tolerance is:

```text
abs(a - b) <= max(1e-6, 1e-5 * max(abs(a), abs(b)))
```

This is a symmetric maximum rule. Other fields and units require their own presets frozen before inspection. Retain counts and magnitudes of every difference; never fit a tolerance to observed differences. Existing exact-reference admission continues to require exact agreement where its contract specifies that stricter check.

Repeated stability requires actual independent executions with retained inputs, outputs and failures. Independent researcher reproducibility additionally requires a separate operator and an accessible immutable candidate/environment, with assistance and rights recorded. Fixture tests, replaying a receipt and an agent's own run do not establish that result. Automatic physical recovery remains unsupported; deterministic fault tests establish only their tested mechanics.

## Analysis and claims

Report each arm's measured values, completion status, verification coverage, missingness and resource context before any ratios. A speed ratio requires a complete eligible matched pair with the same endpoint and declared denominator; a zero or missing denominator yields no ratio. Report all pairs and retain adverse outcomes. One pair can check the measurement procedure but cannot establish a general speed or usability improvement.

Keep software-test cost, workflow turnaround, human effort and physical-model compute distinct. “50 steps to 10” and “40% faster” are illustrative targets, never observations. The historical 1,213 s / 490 s weekly comparison used unequal allocations (4 vCPUs versus 24 + 8 vCPUs), different historical identities and no matched human observations. It is unsuitable as equal-resource speedup evidence for this implementation. Historical two-domain production receipts are provenance/context, not a matched baseline for this Watauga v2 trial.

This amendment does not alter the original [protocol](PROTOCOL.md), E03/E04 fixture identities, invocation ledgers or experiment matrix. The instrumentation milestone executes zero model calls. The [runbook](../docs/BENCHMARK_INSTRUMENTATION_RUNBOOK.md) states the next admission and measurement steps.
