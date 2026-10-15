# Annual preparation orchestration contract — 15 October 2026

The pure Python [orchestration interface](../src/ngen_reforecast/preparation/orchestration.py) turns one complete reforecast request into a deterministic preparation task plan and reconstructs its declared check state from a checkpoint. This closes an offline planning gap between the full-year researcher request and the existing bounded preparation adapter. It does not dispatch tasks, inspect source assets, acquire data, run models or implement a durable queue.

The milestone passes **82 Python tests**: 22 new orchestration tests and 60 request/readiness/adapter/pinned-admission regressions. Independent source and hash-equivalence review completed without remaining must-fix findings. The [evidence receipt](evidence/preparation-orchestration-increment-20261015.json) binds the tested bytes, resource results and preserved stop attempt. Publication follows reviewed sanitized fast-forward progress to the existing repository with CI skipped; the morning handoff reports remote verification.

## Complete study scope

`plan_preparation(serialized_request, *, origin_time_utc, issues_per_task=2)` revalidates the complete [shared request](BROWSER_REQUEST_CONTRACT.md) and [preparation binding](PREPARATION_RESULT_CONTRACT.md). It requires an explicit exact hourly UTC origin before the first issue. It inherits no diagnostic origin, shortened initialization, source qualification or execution admission.

The plan retains the original request, its complete hourly issue population, retained-lead choice and bound initialization/history interval. It contains:

- One `history_coverage` task for the entire original required history interval. Its provider rows cover `[origin, last_issue + 18 hours)`, following the existing interval-start forcing convention; this is not shortened to the first issue.
- Ordered `forecast_issue_coverage` tasks containing one or two consecutive issue hours. These are subsets to organize checks under the original request identity. Every issue still requires its own source leads **1–18** and all 18 physical updates, including when the user retains only leads 1–6 for export.

A non-leap twelve-month study has **8,760 issues** and, with the default two-issue policy, **4,381 tasks** including history. The planner caps a request at **8,784 issues**, enough for a leap year; this is an offline artifact bound, not a service capacity or source availability promise. A larger valid request is refused with `PLAN_SCOPE_LIMIT_EXCEEDED` and is never clipped. The request policy's initialization/history bounds continue to apply independently. Continuous simulation has no orchestration contract and is refused with `MODE_NOT_IMPLEMENTED`.

The [resident forcing adapter](FORCING_PREPARATION_BROWSER_INCREMENT_2026-10-14.md) currently admits at most two issues for one complete request. This planner does not expand that adapter or give it an annual dispatcher. A forecast task cannot be promoted to a smaller admitted study, submitted through that adapter and then treated as qualification of the original annual request. The full history and all issue-specific windows still require an independently qualified future dispatcher and verifier.

## API example with inert synthetic declarations

```python
from hashlib import sha256

from ngen_reforecast.preparation import normalize_request
from ngen_reforecast.preparation.orchestration import (
    checkpoint_preparation,
    plan_preparation,
    resume_preparation,
    seal_task_receipts,
)

request = normalize_request({
    "identifier_type": "usgs",
    "identifier": "03479000",
    "mode": "reforecast",
    "start_date": "2022-01-01",
    "end_date": "2022-12-31",
    "max_lead_hours": 6,
})
plan = plan_preparation(
    request,
    origin_time_utc="2021-12-01T00:00:00Z",
    issues_per_task=2,
)
assert len(plan["requested_population"]["issues_utc"]) == 8760
assert len(plan["tasks"]) == 4381

# This digest identifies a string in the example. No source was inspected.
synthetic_digest = sha256(b"inert documentation fixture").hexdigest()
receipts = seal_task_receipts(plan, [
    {"task_index": 0, "check_state": "unknown", "evidence": None},
    {
        "task_index": 1,
        "check_state": "failed",
        "evidence": {
            "artifact_sha256": synthetic_digest,
            "evidence_class": "synthetic",
            "detail": "Synthetic failure declaration; no forcing or model read.",
        },
    },
])
checkpoint = checkpoint_preparation(plan, receipts)

# Exact repeat receipt ingestion is idempotent.
assert checkpoint_preparation(plan, receipts, previous=checkpoint) == checkpoint
continuation = resume_preparation(plan, checkpoint)
assert continuation["status"] == "planning_only"
assert continuation["execution_ready"] is False
assert len(continuation["pending_check_task_ids"]) == 4381
```

The functions return detached plain JSON. The caller may serialize a returned plan or checkpoint into its own eligible local artifact, but these functions perform no persistence, worker submission or artifact read/write. Request validation reads only the packaged request-policy.json resource. A checkpoint file is not a model checkpoint.

## Bound plans, receipts and checkpoints

| Artifact | Schema and identity | Validation boundary |
|---|---|---|
| Plan | `preparation-orchestration-plan/0.1`; `plan_identity_sha256` | Rebuild the entire plan from the validated original request, explicit origin and batch policy; reject any changed content, task population, flags or identity |
| Task | `task_identity_sha256` | Bind request hash, original scope hash, origin, task index/kind and the exact history interval or issue subset |
| Receipt | `preparation-task-receipt/0.1`; `receipt_identity_sha256` | Bind the complete plan, original scope, known task identity, declared state and evidence |
| Checkpoint | `preparation-receipt-checkpoint/0.1`; `checkpoint_identity_sha256` | Validate every receipt, order it by plan task order, and bind the resulting receipt set and fixed capability flags |

Hashes stream the existing canonical sorted JSON representation, including equivalent integer-valued number handling and lone-surrogate escaping; equivalence is tested against the shared implementation. They detect content and binding changes; they do not authenticate the caller or verifier, establish source truth, prove evidence-class labels, inspect named artifact bytes or establish freshness. A receipt labeled `verification_receipt` remains a declaration at this boundary.

`seal_task_receipts(plan, records)` accepts records with exactly `task_index`, `check_state` and `evidence`. Task indices must be known integers. A sealing call accepts at most the plan's task count. It adds the plan/scope/task identities and hashes the declaration. It does not perform the declared check.

| Declared state | Evidence and reconstruction meaning |
|---|---|
| `unknown` | Requires `evidence: null`; check remains pending |
| `missing` | Caller declares a missing prerequisite; check remains pending |
| `failed` | Caller declares a failed check; check remains pending |
| `passed` | Caller declares success; task becomes a declared reuse candidate awaiting independent artifact re-verification |

Non-unknown evidence has exactly `artifact_sha256`, `evidence_class` and `detail`: a lowercase 64-character SHA-256, one of `synthetic`, `declared_metadata` or `verification_receipt`, and a nonblank detail of at most 512 characters. An omitted receipt is reconstructed as `not_recorded`, which also remains pending; it is not inferred to mean missing or failed.

`checkpoint_preparation(plan, receipts, *, previous=None)` validates an optional previous checkpoint before merging receipts. Identical duplicates are idempotent, and receipt ordering cannot change the result. Different declarations for the same task are refused with `CONFLICTING_TASK_RECEIPT`; the API does not overwrite old evidence or infer supersession, including a transition from failed or unknown to passed. Replacing a declaration uses the separate [explicit receipt journal](PREPARATION_RECEIPT_JOURNAL_CONTRACT.md); this version 0.1 checkpoint API retains its conflict refusal and never overwrites evidence. Malformed records, unknown tasks, altered receipt hashes, mismatched scopes and edited checkpoints are refused. An invalid checkpoint must not be replaced with an empty one to manufacture a continuation.

Each input and returned plan, receipt set, checkpoint and continuation is separately limited to **8 MiB**, depth **20** and **250,000 nodes**. Inputs must be finite, safe-number, acyclic plain JSON with safe string keys. A reconciled receipt set is bounded by the task population plus exact repeat entries admitted within the input limit; duplicates do not create extra tasks.

## Meaning of resume

`resume_preparation(plan, checkpoint)` validates both artifacts and returns task states in original plan order. `pending_check_task_ids` contains every task without a passed declaration; `declared_reuse_candidate_task_ids` contains passed declarations. Even when `all_checks_declared_passed` is true, it returns:

```json
{
  "status": "planning_only",
  "dispatch_supported": false,
  "execution_ready": false,
  "source_coverage_qualified": false,
  "artifacts_reverified": false,
  "physical_recovery_established": false
}
```

Resume means reconstruction of preparation-check planning state. It establishes no physical restart, durable queue, source availability, crash-safe persistence, current artifact validity or scientific admission. No candidate artifact is read or reused by this interface. Existing scientific/input/runtime/reference checks and physical execution limits remain intact.

## One overnight continuation package

The approved package is the pure annual plan/checkpoint implementation, deterministic synthetic and regression tests, independent review, preservation checks and reviewed sanitized milestone publication to the existing project repository. There is no additional stage approval needed for this package. The target is code, validation evidence and publication readiness by **09:00 UTC on 15 October 2026**, subject to the following shared-resource limits.

| Control | Bound |
|---|---|
| Cost and infrastructure | **$0**; no new external compute resources, data acquisition, physical reforecasts, training, workers or servers |
| Local validation | One serial test process; thread limits set to **1** and process niceness **10** |
| Batch stop | Stop a test batch at **30 seconds** or a sampled RSS above **256 MiB**; sample every **50 ms** (brief overshoot is possible) |
| Shared machine admission | Check before every batch of at most 30 seconds; pause if load is **at least 8** or free memory is **below 20%**; preserve HYDRA priority and avoid competing heavy jobs |
| Deadline | Stop active work by **09:00 UTC, 15 October 2026** and report completed evidence plus any remaining blocker |
| Recovery | Preserve the last valid checkpoint; reject bad or mismatched records, retain the refusal evidence and never reset a ledger or manufacture an empty continuation |

The realistic morning deliverable is a validated, reviewable offline orchestration contract with scope-preservation and deterministic checkpoint tests. An annual physical forecast, qualified annual forcing, execution recovery or measured researcher speed improvement is not promised by this milestone. If review, resource pressure or publication checks prevent completion, retain the coherent local milestone and report the exact unfinished action.

Future real full-year preparation or execution requires one costed, scoped package covering the scientific protocol, domain, initialization, source/reference qualification, resources and run authorization after the current budget-before-training hold. This documentation does not request approval for that later work or imply a compute price. Publication approval covers eligible reviewed code/documentation/evidence summaries; private datasets, raw inputs, credentials and personal notes remain excluded. No license, permission/security setting or billable CI change is included.

## Validation and benchmark interpretation

The final serial batches passed **80 tests in 1.327 seconds wall time** (20 orchestration plus 60 regressions; sampled peak **59,376 KiB RSS**) and **two annual stress tests in 10.098 seconds** (sampled peak **85,552 KiB RSS**). All thread limits were one and process niceness was 10. The initial annual batch was stopped after **2.649 seconds** when sampled RSS reached **268,928 KiB**, above the 262,144 KiB threshold. Replacing temporary whole-artifact hash serialization with byte-equivalent streaming resolved that observed resource failure; the stopped attempt remains in the evidence record. These observations establish compliance for the final bounded test batches, not service capacity.

Independent review covers scope/identity, malformed input bounds, annual idempotence and canonical-hash equivalence. Browser sources are unchanged from the previously tested 77-Node-test milestone; Node tests and the full Python suite were not rerun for this Python-only increment. No model, source download, service, worker or paid CI ran. The evidence receipt identifies the reviewed base and changed source bytes; the commit containing that receipt is the publication candidate.

The annual fixture is a scope test, and synthetic passed receipts exercise declaration handling only. Keep the three intended researcher benchmark measures separate: **hands-on human effort**, **total workflow turnaround**, and **physical model compute**. All three remain **unmeasured** here. Local test wall time, RSS and CPU are validation costs only; they are not researcher-workflow or model-compute results. “50 steps to 10” and “40% faster” remain illustrative targets.
