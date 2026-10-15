# Benchmark instrumentation runbook

15 October 2026. The deliverable is a prospective [matched workflow benchmark draft](../benchmarks/MATCHED_WORKFLOW_BENCHMARK_DRAFT.md), bounded instrumentation and deterministic synthetic/fixture tests. No new reforecast, runtime start, download, participant session or measured manual-workflow comparison belongs to this milestone. Synthetic results establish measurement mechanics only.

The current physical path supports the pinned Watauga v2 two-issue diagnostic in the [execution contract](PUBLIC_CAMPAIGN_EXECUTION_CONTRACT.md). Its [11 October acceptance](PUBLIC_CAMPAIGN_EXECUTION_RESULTS_2026-10-11.md) provides prior generation and integrity evidence, not a new speed comparison. A twelve-month researcher workflow remains the eventual target. The annual preparation planner and inert dispatcher do not qualify annual execution or implement shared-history generation.

## Prepare a future measurement package

1. Select one stratum: first use, warm resident inputs or completed-result reuse. Write the exact start, verified-archive endpoint and meaningful-action taxonomy. Freeze manual and software instructions using the same backend generation strategy and required checks.
2. Bind the trial/paired-block IDs; draft/protocol hashes; workload, original history, complete issue/lead/valid-time population and retained export; exact source/runtime/input/reference identities; implementation identities for each arm; and resource/cache/environment conditions. Preserve existing admission checks. Missing required bindings leave the trial blocked.
3. Define order, allowed attempts, assistance, interruption rules and analysis before observation. Reserve fresh namespaces without resetting existing claims, ledgers or archives. Retain all outcomes and the first failure before retries. Do not count undeclared warmups as free work.
4. Verify resident assets and runtime availability without hydrating original research folders. Check current host load and free memory; give active HYDRA/NWM qualification and Selective recovery priority. A previous stopped worker or installed image is not evidence that a runtime is presently available.
5. Obtain the specific execution approval below, plus actual human-operator consent where human effort is measured. This engineering milestone requests no new approval and launches nothing.

The existing diagnostic uses one history and two independently cold-initialized forecasts per generation arm: six native/router stages per arm. All 18 forecast updates remain required when exporting only six leads. The manual and software arms must use that same work; changing to shared history would be a new qualified compute-strategy study.

## Capture and interpret evidence

Use the package's benchmark instrumentation as an observer around already admitted work. It does not launch jobs, acquire inputs, admit science or verify an archive on the caller's behalf. Record generation, preparation, verification and export boundaries explicitly, including failure and interruption endpoints. Bind the resulting record to the frozen trial contract and eligible verification artifacts.

The Python interface is `ngen_reforecast.benchmarking`:

| Interface | Role and boundary |
|---|---|
| `freeze_contract(...)` | Seal the full trial-manifest hash, declared scientific/input/model/reference and environment hashes, CPU/memory/concurrency limits, cache stratum/definition and exact expected keys. The compact product is limited to 4,096 rows and requires all 18 leads per issue; this is not annual capacity. |
| `WorkflowRecorder(...)` | Bind one manual or software arm, run and paired-block aliases, implementation identity and synthetic-fixture or observed-session origin. Record ordered phase boundaries, observed activity intervals, meaningful action aliases and failure/retry/assistance incidents. |
| `finish(...)` | Seal the completed or failed attempt, declared verification binding and optional observed human/resource records. Unknown human and whole-job resource quantities remain `null`; a supplied verification hash is not freshly verified by this function. |
| `assess_pair(...)` | Revalidate bound records and return actionable blockers. Synthetic, failed, incomplete or mismatched pairs do not produce observed speedup claims. Any eligible ratio remains conditional on the caller's declared evidence and the full trial's admission. |
| `compare_fixture_rows(...)` | Exercise exact compact key/unit coverage and the frozen discharge tolerance with supplied fixture rows; it always remains fixture-only and grants no scientific qualification. |

Hash seals detect changed records and bind their content; they do not authenticate an observer, prove declared limits were enforced or inspect the bytes named by a digest. The complete frozen trial manifest supplies the study/order/allowance and enforcement context beyond the compact instrumentation contract. Validate and retain those external receipts before interpreting a pair.

The library permits at most **512 events** per attempt and bounds every artifact to **2 MiB**, 100,000 nodes and depth 12. Phase intervals follow acquisition, preparation, generation, verification and export in that order. Human activity intervals may overlap a running phase, but cannot overlap each other; split mixed activity at its observed boundaries. `human_observation_complete=True` is an observer declaration, not automatic inference. Unclassified human and phase time remains explicit. Keep missing-value reasons in the bound external observation/trial record. Monetary accounting is not implemented; `cost_usd` remains `null`.

`finish` accepts verification fields `manifest_sha256`, `verification_sha256`, `reference_sha256`, `observed_rows` and `outcome="passed-complete-products"`. The reference must equal the frozen scientific reference and row count must equal the complete expected population. Inspect those external records before supplying them. Whole-job resources, when available, require `measurement_sha256`, `scope="whole-job"`, a supported counter method, and nullable `cpu_seconds`, `peak_rss_bytes`, `read_bytes`, `write_bytes` and `output_bytes`. Sampled observer RSS cannot fill a whole-job peak field. Pair assessments bind both attempt identities; fixture comparisons bind canonical content hashes for both inputs. Completed-result reuse can yield an eligible total-elapsed ratio, but its generation ratio is always `null`.

To check only the offline instrumentation mechanics from the repository root:

```sh
PYTHONPATH=src:tests PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_benchmark_workflow -v
```

Use the current shared-host admission and bounded low-priority wrapper when other work is active. The test suite uses tiny fabricated rows and clocks; its observed-session branches patch the clock for deterministic logic checks and are still synthetic test evidence. This command launches no models and collects no researcher observations.

Use monotonic durations for intervals within a run. UTC timestamps identify when the attempt happened; do not subtract independently collected monotonic origins across processes or hosts. Mark fixture clocks/events synthetic. Record CPU and memory scope accurately: observer/self-process counters omit external containers and children unless independently measured. Whole-job enforcement/counters require their own evidence.

Human steps and active/wait/interruption time require actual observation under the frozen taxonomy. Keep these values `null` with reasons until observed. Do not derive hands-on time from script wall time or treat a missing human log as zero effort. Keep assistance, learning, failures and later retests in the record. Publish reviewed pseudonymous aggregates; retain private consent and identity records outside the repository.

Verification must establish the exact complete intended product, its schema/key/unit/quality coverage and applicable reference comparison before a valid-output speed claim. The compact fixture comparator uses discharge units `m3 s-1`; full archive quality/reference checks remain external. Hashing an existing archive is a streaming identity audit; it is not generation time or a fresh full-array semantic audit. Preserve the distinction between raw-byte equality, canonical numerical equality and tolerance-based comparison. The frozen discharge tolerance is symmetric `max(abs_tol, rel_tol * max(abs(a), abs(b)))`; no additive formula or after-the-fact fitting is allowed.

Report wall time, human effort, CPU, memory, output size and observed monetary cost separately. Missing values stay unknown. Show both arm outcomes and all failures before ratios; unequal resources/cache/workload, missing observations or incomplete output invalidate a matched speedup claim. Historical 1,213 s / 490 s timings are resource-confounded and remain unsuitable for that claim.

## Smallest future physical trial requiring approval

The following is a **proposed ceiling**, not a launch instruction or assurance the case fits. Freeze a separate trial manifest and reconcile it with the exact current profile/limits before execution:

| Item needing explicit authorization | Proposed warm-resident paired trial |
|---|---|
| Scientific scope | Exact currently admitted Watauga v2 history and two issues; unchanged original origin, inputs, profile, full leads and independent references |
| Native invocation allowance | One manual arm plus one software arm; three logical jobs/six native-router stages each, **12 stages total**; no extra warmups, repairs, retries or repeat pairs |
| Active work | One logical job at a time; enforced **2 CPUs**, **8 GiB** whole-job memory and **1,800 seconds** per logical job, including descendants |
| Output ceilings | **1 GiB/job**, **4 GiB/arm**, **8 GiB** aggregate new outputs; prospective bounds measured/enforced before continuation |
| Runtime/staging and disk | **12 GiB** aggregate footprint ceiling and **8 GiB** host free-space floor; preserve existing evidence and stop before breaching either |
| Runtime authority and cost | Explicit permission for any required foreground runtime/worker start; resident admitted image/assets only; **$0 new paid resources**, no acquisition, image pull/build, training or cloud provisioning |
| Host admission and stops | Defer under competing work or resource pressure; stop on deadline/memory/output/disk limits, invalid input, integrity/numerical mismatch, unexpected model stage or lost enforcement |
| Operator evidence | Consented observer/operator and frozen manual-action policy if measuring human effort; otherwise keep human metrics unmeasured |

After approval, perform and retain preflight before launching the first arm. If the supported automated endpoint or an enforcement prerequisite is absent, report that specific blocker; do not change the workload or bypass checks to obtain a number. Preserve failure receipts and remaining allowance. A new allowance or changed scientific/resource recipe requires a prospective amendment and the applicable authority.

One completed matched pair would establish a bounded pilot observation and expose measurement gaps. General performance estimates require a separately frozen repeat/order plan. Independent researcher reproduction requires an immutable accessible candidate and a separate operator; it is not delivered by this zero-call milestone.

## Current handoff boundary

Use the milestone's source-bound validation receipt for exact test counts, measured local test cost, implementation hashes and reviewed commit. Those are engineering validation costs. No physical-run speed, hands-on effort, twelve-month turnaround, invoice cost or new independent reproduction result is claimed. Existing protocol/matrix bytes and historical results remain unchanged.

The intended identity of the owner's two historical HYDRA reforecasts still needs confirmation. Inspected candidates have different issue populations and periods; their elapsed times cannot supply a matched manual/software baseline. Confirm their identity for provenance without delaying the current software instrumentation or introducing an accuracy-scoring dependency.
