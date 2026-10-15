# Bounded preparation dispatch contract — 15 October 2026

The [dispatch interface](../src/ngen_reforecast/preparation/dispatch.py) selects a small ordered group of preparation checks from an exact [receipt journal](../src/ngen_reforecast/preparation/journal.py) and seals caller outcomes into a candidate receipt revision. It performs **zero task dispatches**. It supplies no adapter invocation, declared source-artifact read, worker, queue, persistence, scientific qualification or physical execution. Validation reads only the packaged request-policy resource.

This is the next offline protocol layer after the [complete-study planner](PREPARATION_ORCHESTRATION_CONTRACT.md) and explicit receipt supersession. It adds a reproducible selection envelope and refuses result sealing against a different journal, rather than letting a changed task population or stale receipt identity enter the candidate silently. All original scientific admission checks remain in force.

Validation passes **123 targeted Python tests**, including **21 new dispatcher tests** (20 small plus one annual) and 102 journal/orchestration/request/readiness/adapter/pinned-admission regressions. Independent source review found no remaining must-fix findings. The [evidence receipt](evidence/preparation-dispatch-increment-20261015.json) binds tested bytes and resource observations; [the morning handoff](OVERNIGHT_SOFTWARE_HANDOFF_2026-10-15.md) records the practical next steps.

## Selection and binding

`plan_preparation_dispatch(plan, journal, *, max_tasks=2)` validates the complete original plan and supplied journal. It returns a detached plain-JSON `preparation-dispatch-envelope/0.1` with a content-derived `dispatch_identity_sha256`. The envelope binds:

- The original `plan_identity_sha256` and complete preparation binding: request, policy, scope, explicit global initialization origin, full required history, issue schedule and required source leads **1–18**.
- The exact supplied `journal_identity_sha256`, `revision_head_sha256` and revision count.
- Each selected original task and its current `expected_receipt_sha256`, or null only when unrecorded.
- The history task's active declared state and receipt identity, the fixed selection policy, resource bounds and false capability flags.

If the history task lacks an active `passed` declaration, it is selected alone. A passed history declaration permits selection of pending forecast checks in increasing original task order. This is an ordering prerequisite only: its artifact remains unverified and its scientific qualification remains false. Tasks with active passed declarations are skipped as declared reuse candidates; this API does not reuse or reverify their artifacts.

`max_tasks` must be the integer 1 or 2. The envelope independently caps selected forecast issue hours at **two**, without splitting a task or skipping a pending task to fit more work. With the planner's default two issues per task, at most one forecast task is selected. With one issue per task, at most two forecast tasks are selected. History always retains the entire original interval, regardless of this forecast selection bound. No request is shortened or promoted to a smaller study.

The envelope records one as the maximum parallel-task allowance and zero performed task dispatches, payload bytes read, model/acquisition calls, workers/processes started and cost. These describe this inert contract; they reserve no host resources and enforce no future adapter time, memory or storage budget. Plans, envelopes and outcomes retain the orchestration artifact limits of 8 MiB, depth 20 and 250,000 nodes per input or output.

An all-declared-passed journal yields `status: no_pending_checks` with no selected tasks. It still grants no source qualification, artifact freshness or execution readiness. Sealing a result for an empty envelope is refused with `NO_PREPARATION_DISPATCH_TASKS` and creates no empty revision.

## Candidate outcomes and explicit application

`seal_dispatch_result(plan, journal, envelope, outcomes)` first rebuilds the envelope against the supplied current journal and rejects any content, selection, prerequisite, resource or identity change. Outcomes must contain exactly one entry for every selected task, with no omissions, extras or duplicates. Each has exactly:

```json
{
  "task_index": 0,
  "check_state": "unknown",
  "evidence": null,
  "reason": "Explicit synthetic check declaration; no source artifact inspected."
}
```

The journal contract checks states, evidence and a nonblank reason of at most 512 characters. Unknown outcomes require null evidence; missing, failed and passed outcomes require the existing bounded evidence declaration. The dispatcher injects the selected task's exact prior receipt identity and delegates to `seal_receipt_revision`. It returns a `preparation-dispatch-result-candidate/0.1` with the sealed `receipt_revision`, envelope and base journal identities, and a content-derived `result_identity_sha256`.

Equivalent outcome order produces the same candidate. Sealing changes no journal and performs no declared check. A caller applies the candidate only through the existing explicit journal boundary:

```python
candidate = seal_dispatch_result(plan, journal, envelope, outcomes)
updated = apply_receipt_revision(
    plan,
    journal,
    candidate["receipt_revision"],
    expected_journal_identity_sha256=journal["journal_identity_sha256"],
)
```

The caller must obtain that current anchor from its trusted state, not infer it from an old candidate. The journal preserves the original checkpoint and all prior revisions, applies the complete revision atomically in returned JSON, and acknowledges an exact already-recorded revision idempotently when supplied with the current journal anchor. A competing revision from the old parent is refused. Re-sealing outcomes with an old envelope after any journal change is refused with `STALE_PREPARATION_DISPATCH`, even if that change concerned another task. Replanning against the new journal produces a new envelope and explicit prior-receipt preconditions.

Hashes bind supplied content; they authenticate no caller, verifier, evidence class or source. The APIs validate only the supplied journal. An old journal paired with its own old envelope cannot reveal an unanchored rollback by itself. Trusted latest-tip storage and durable compare-and-swap across external writers remain future controller requirements. This contract implements no lock, exactly-once delivery guarantee, crash-safe queue or physical recovery.

## Scientific and capacity limits

Every envelope and candidate retains `dispatch_supported`, `execution_ready`, `artifacts_reverified`, `source_coverage_qualified` and `physical_recovery_established` as false. Even a caller result labeled passed or `verification_receipt` cannot change those fields.

The existing resident-forcing adapter accepts one complete request with at most two issues and independently bounded history/catchment workload. An annual plan's task subset remains bound to the complete annual request and global history; it cannot be submitted as a smaller admitted study to manufacture annual coverage. Before any actual future adapter acts, it needs an independently implemented and authorized contract for the full original domain, history, issue-specific full 18-hour sources, references, runtime, protocol and resource budget.

The journal permits at most **64 revisions**, each replacing one or two task receipts. A complete annual checkpoint may be its immutable base, but the revision limit is a bounded protocol pilot and cannot complete all 4,381 default annual tasks from an empty journal. Pending work at that bound is refused with `PREPARATION_DISPATCH_CAPACITY_EXCEEDED`. No automatic compaction, fresh journal, dropped history, larger bound or task clipping creates annual campaign capacity.

The deterministic cases cover history ordering, task/issue bounds, exact outcome population, detached data, full-scope identity, tampered envelopes, stale and competing candidates, explicit supersession and duplicate revision replay. The separate annual fixture preserves all 8,760 issues, the original history origin and final physical target while producing only a bounded inert envelope and candidate. No test supplies actual forcing, executes a forecast or establishes source coverage.

This work uses the existing overnight resource and stop limits in the orchestration contract. Hands-on researcher effort, end-to-end workflow turnaround and physical model compute remain separate **unmeasured** quantities. Software test wall time and sampled memory are engineering validation observations, not evidence for the illustrative “50 steps to 10” or “40% faster” targets.

## Validation observations

The final serial small batch passed **119 tests in 2.763 seconds wall time**, with **61,216 KiB sampled peak RSS**. The four annual cases passed in **24.235 seconds**, with **87,040 KiB sampled peak RSS**. Each used one numerical thread, niceness 10, a 30-second wall stop and a sampled 256 MiB RSS stop. Neither final batch hit a stop. The annual cases include a complete 4,381-receipt journal base and leap-year duplicate ingestion; the new dispatcher annual case is a sparse journal with a bounded inert result and does not establish actual annual capacity. Browser sources and scientific admission/runtime/profile/adapter bytes are unchanged; Node tests and the full Python suite were not rerun.

Review added deterministic checks for explicit history-pass invalidation/reinstatement and pending work at the journal cap. The publication candidate contains this contract and its bound evidence; exact remote/public file verification and zero triggered Actions runs are recorded after publication in the morning handoff response. No new dependency, service, actual input acquisition, forecast, training or paid resource was used.
