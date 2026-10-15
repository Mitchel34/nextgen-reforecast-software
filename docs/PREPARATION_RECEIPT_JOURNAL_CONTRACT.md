# Preparation receipt journal contract — 15 October 2026

The pure Python [receipt journal interface](../src/ngen_reforecast/preparation/journal.py) adds explicit, append-only supersession to the [preparation plan/checkpoint contract](PREPARATION_ORCHESTRATION_CONTRACT.md). A caller can retain a failed declaration and record a later passed declaration, with the expected prior receipt and a reason. The original checkpoint and every revision remain in the returned journal. This is one bounded engineering milestone; no check, declared source-artifact read, dispatcher, persistence service or physical recovery is performed. Validation reads only the packaged request-policy resource.

The milestone passes **102 targeted Python tests**: 20 journal tests and 82 orchestration/request/readiness/adapter/pinned-admission regressions. Independent source review found no remaining must-fix findings. The [evidence receipt](evidence/preparation-receipt-journal-increment-20261015.json) binds tested bytes and bounded local observations; remote publication verification follows in the morning handoff.

## API and retained scope

| API | Result |
|---|---|
| `start_preparation_journal(plan, checkpoint=None)` | Validate the complete original plan and optional version 0.1 checkpoint, retain the base checkpoint unchanged, and return an empty revision history; an omitted checkpoint gives a validated empty base |
| `seal_receipt_revision(plan, journal, records)` | Validate the supplied history and seal one or two explicit task replacements as the next revision; inspect no declared artifact |
| `apply_receipt_revision(plan, journal, revision, *, expected_journal_identity_sha256)` | Validate the caller's pinned journal identity, then apply the exact next revision or acknowledge an exact already-retained replay |
| `resume_preparation_journal(plan, journal)` | Validate and replay the retained declarations, returning current task receipts, pending checks and declared reuse candidates in original plan order |

The journal schema is `preparation-receipt-journal/0.1`; the revision schema is `preparation-receipt-revision/0.1`. The base is the complete validated `preparation-receipt-checkpoint/0.1`, with its original binding and content identity. It is immutable within this history. The journal keeps the original plan/scope identities, so revision work cannot change the study, initialization origin, history interval, issue population or full source leads 1–18. Existing scientific admission checks remain intact.

The pilot admits at most **64 revision batches**, each containing **one or two updates**. The complete resulting journal, including its unchanged base and all historical revisions, must fit **8 MiB**, depth **20** and **250,000 nodes** under the existing bounded plain-JSON rules. Sealing checks that the complete candidate journal fits before returning its revision. Reaching a bound refuses further append; it does not compact history, replace the base or reset a ledger. Exact replay of an already retained revision can still be acknowledged at the revision-count limit.

A default annual plan has **4,381 tasks** for 8,760 issues, including its complete history task. A journal starting with an empty base can record at most **128 task updates** under this pilot bound. It cannot progress all annual tasks from empty, and this limit must not be bypassed by treating smaller studies as qualification of the original annual plan. A populated base remains retained evidence, not independently verified annual source coverage.

## Explicit expected-parent updates

Each input record to `seal_receipt_revision` has exactly:

```text
task_index
expected_receipt_sha256
check_state
evidence
reason
```

`task_index` is a known integer index in the original plan, and a task may appear at most once in a batch. `check_state` and `evidence` follow the existing task receipt contract: states are `unknown`, `missing`, `failed` and `passed`; unknown requires null evidence, while other states require a declared artifact SHA-256, evidence class and detail. The journal does not check the artifact or authenticate these labels.

`expected_receipt_sha256` must equal the currently active receipt's content identity. Use `null` only when that task has no recorded receipt. A recorded `unknown` receipt still has a receipt hash and must be named by that hash; it is not interchangeable with an unrecorded task. `reason` is a nonblank string of at most 512 characters explaining the supersession. Any state can be explicitly superseded, including invalidating a prior pass to failed or unknown, or recording changed evidence with the same state. An identical replacement is refused as `RECEIPT_REVISION_NO_CHANGE`; use the original sealed revision for retry.

The sealed revision retains each expected prior identity, replacement receipt and reason in canonical increasing task order. Its `revision_index` is exactly the next integer, and `parent_revision_identity_sha256` is the supplied journal's exact current revision head. The initial head is a genesis hash bound to the journal schema, complete plan/scope identities and original base checkpoint identity. Every later head is the preceding revision's content hash.

`revision_identity_sha256` deterministically identifies the complete revision, including its parent, index, replacements and reasons. Equivalent record order yields the same sealed operation. This content hash acts as the operation's replay key; there is no independently chosen request key or authority token. A changed reason or evidence is a different operation.

## Inert failed-to-passed example

This example uses a two-issue synthetic study. Both outcomes are declarations over an inert string; no forcing asset is read or verified.

```python
from hashlib import sha256

from ngen_reforecast.preparation import normalize_request
from ngen_reforecast.preparation.orchestration import (
    checkpoint_preparation, plan_preparation, seal_task_receipts,
)
from ngen_reforecast.preparation.journal import (
    apply_receipt_revision, resume_preparation_journal,
    seal_receipt_revision, start_preparation_journal,
)

request = normalize_request({
    "identifier_type": "usgs", "identifier": "03479000",
    "mode": "reforecast", "start_date": "2022-01-01",
    "end_date": "2022-01-01", "start_hour_utc": 0,
    "end_hour_utc": 1, "max_lead_hours": 6,
})
plan = plan_preparation(request, origin_time_utc="2021-12-01T00:00:00Z")
evidence = {
    "artifact_sha256": sha256(b"inert journal example").hexdigest(),
    "evidence_class": "synthetic",
    "detail": "Synthetic declaration; no physical input inspected.",
}
failed = seal_task_receipts(plan, [
    {"task_index": 1, "check_state": "failed", "evidence": evidence},
])
base = checkpoint_preparation(plan, failed)
journal = start_preparation_journal(plan, base)
revision = seal_receipt_revision(plan, journal, [{
    "task_index": 1,
    "expected_receipt_sha256": failed[0]["receipt_identity_sha256"],
    "check_state": "passed", "evidence": evidence,
    "reason": "Explicit synthetic recheck example; no source qualification.",
}])
changed = apply_receipt_revision(
    plan, journal, revision,
    expected_journal_identity_sha256=journal["journal_identity_sha256"],
)
assert changed["base_checkpoint"] == base
assert base["receipts"][0]["check_state"] == "failed"
assert resume_preparation_journal(plan, changed)["current_task_receipts"][0]["check_state"] == "passed"
assert changed["execution_ready"] is False

# Use the current pinned journal identity when acknowledging the same operation.
assert apply_receipt_revision(
    plan, changed, revision,
    expected_journal_identity_sha256=changed["journal_identity_sha256"],
) == changed
```

The identity read directly from the in-memory object is sufficient for this isolated example. A real storage caller needs an independent trusted latest identity to establish which object is current.

## Atomic refusal and exact replay

All updates in a batch are compared with the pre-revision active receipt set before any replacement is applied. The functions return detached JSON and do not mutate caller objects on success or failure. A stale expected task receipt refuses the whole revision. No partial replacement or fallback checkpoint is returned.

The history validator reconstructs state from the original base and every retained revision, checking strict schemas, exact task/plan/scope bindings, receipt/revision hashes, sequential indices, chained parent hashes and the final journal identity, flags, count and head. Unknown fields, duplicate tasks, altered evidence, changed base checkpoints, dropped/reordered history, gaps and exceeded limits are refused. A sibling revision sealed from an earlier head is not merged, even if its revision number is edited to the next number. Preserve conflicting histories for review; do not reset the journal or manufacture an empty continuation.

After validation and the caller-anchor check, applying the exact content hash of any already retained revision returns the current journal unchanged. This remains true after later revisions have superseded that task again. Replay acknowledges the historical operation without restoring its older receipt or dropping later events. A tampered operation does not qualify as replay.

| Refusal | Meaning |
|---|---|
| `STALE_PREPARATION_JOURNAL` | Supplied journal does not match the caller's pinned identity |
| `STALE_RECEIPT_REVISION` | Revision index or parent does not extend this exact history |
| `STALE_TASK_RECEIPT` | A replacement names a prior receipt that is not current |
| `RECEIPT_REVISION_SCOPE_MISMATCH` | Revision or replacement belongs to another original scope/task |
| `RECEIPT_REVISION_IDENTITY_MISMATCH` | Sealed revision content changed |
| `PREPARATION_JOURNAL_MISMATCH` | Journal content, bindings, count, flags, head or identity changed |
| `RECEIPT_REVISION_LIMIT_EXCEEDED` / `ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED` | Preserve the bounded history intact; no implicit compaction or reset |

Malformed schemas, invalid reasons and duplicate/no-change updates also produce structured `RequestPreparationError` refusals under their specific codes.

## Currentness, persistence and execution boundaries

`apply_receipt_revision` requires the keyword-only `expected_journal_identity_sha256` anchor. It must match the supplied validated journal. Comparing with an independently retained trusted latest identity can reject an old journal supplied by mistake. Reading both the journal and its expected identity from the same stale or untrusted source does not detect rollback. Hashes establish content relationships, not authority, freshness or authentication.

No trusted latest store, atomic file replacement, interprocess lock, concurrent-writer serialization or crash-safe persistence is implemented. A future storage adapter must independently maintain the latest identity and atomically compare-and-swap it together with the complete journal. Two callers holding the same old identity can each compute valid sibling journals locally; this pure API cannot prevent one external writer from overwriting the other. `resume_preparation_journal` validates the supplied history only and cannot determine whether a newer journal exists elsewhere.

Even if every current declaration says passed, all of these remain false:

```json
{
  "freshness_established": false,
  "dispatch_supported": false,
  "execution_ready": false,
  "source_coverage_qualified": false,
  "artifacts_reverified": false,
  "physical_recovery_established": false,
  "durable_storage_established": false
}
```

The result retains `status: planning_only`. A declared pass makes a task a reuse candidate awaiting independent artifact re-verification. It does not dispatch that task. Actual preparation dispatch remains unsupported by this journal, including a journal whose declarations all passed; the existing two-issue forcing adapter is not widened. No physical state, scientific admission, source availability, durable queue or model-recovery capability is inferred.

## Milestone evidence

Final serial validation passed **99 small tests in 2.009 seconds wall time** (sampled peak **59,472 KiB RSS**) and **three annual tests in 18.925 seconds** (sampled peak **84,832 KiB RSS**). The annual journal case retains a fully populated **4,381-receipt** synthetic base and explicitly supersedes two receipts; it does not verify actual annual data. The other annual cases cover non-leap population and repeated ingestion of all 8,785 leap-year task declarations. Each batch used one numerical thread, niceness 10, a 30-second wall stop and a sampled 256 MiB RSS stop; neither final batch hit a stop. Independent read-only source/test review completed. Browser sources and scientific admission/runtime/profile/adapter bytes remain unchanged; Node tests and the full Python suite were not rerun. Publication is reviewed sanitized fast-forward progress with CI skipped; the commit containing the evidence receipt is the candidate, and exact remote verification is reported separately. Work remains within the existing lightweight continuation and shared-resource limits, with no physical forecasts, source acquisition, training, new external resources or spending. This contract records the implemented engineering boundary and does not start a new planning campaign or request another stage approval.

Hands-on human effort, total workflow turnaround and physical model compute remain separate and **unmeasured**. Synthetic test time or RSS records only the cost of local software validation; it establishes no researcher speed improvement or physical compute saving.
