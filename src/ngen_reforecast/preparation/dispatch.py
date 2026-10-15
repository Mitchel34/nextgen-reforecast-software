"""Inert bounded preparation submissions bound to an exact receipt journal.

These APIs select checks and seal caller-result candidates only. They never
call an adapter, read a source artifact, start work or qualify a study. A
history pass is a declaration used for ordering, not verified history.
"""

from __future__ import annotations

from copy import deepcopy

from . import RequestPreparationError
from .journal import MAX_REVISIONS, resume_preparation_journal, seal_receipt_revision
from .orchestration import _hash, _plan, _snapshot


DISPATCH_VERSION = "preparation-dispatch-envelope/0.1"
RESULT_VERSION = "preparation-dispatch-result-candidate/0.1"
MAX_TASKS = 2
MAX_FORECAST_ISSUES = 2


def _fail(code, field, message):
    raise RequestPreparationError(code, field, message)


def _resources():
    return {"task_dispatches_performed": 0, "payload_bytes_read": 0,
            "model_calls": 0, "acquisition_calls": 0, "workers_started": 0,
            "processes_started": 0, "cost_usd": 0}


def _flags():
    return {"dispatch_supported": False, "execution_ready": False,
            "artifacts_reverified": False, "source_coverage_qualified": False,
            "physical_recovery_established": False}


def _envelope(plan, resumed, max_tasks):
    if type(max_tasks) is not int or not 1 <= max_tasks <= MAX_TASKS:
        _fail("INVALID_PREPARATION_DISPATCH_BOUNDS", "max_tasks", "Choose one or two tasks; this contract cannot dispatch them.")
    active = {receipt["task_identity_sha256"]: receipt for receipt in resumed["current_task_receipts"]}
    history = plan["tasks"][0]
    history_receipt = active.get(history["task_identity_sha256"])
    history_state = history_receipt["check_state"] if history_receipt else "not_recorded"
    pending = set(resumed["pending_check_task_ids"])
    if pending and resumed["revision_count"] >= MAX_REVISIONS:
        _fail("PREPARATION_DISPATCH_CAPACITY_EXCEEDED", "journal", "This journal has reached its 64-revision pilot bound. Preserve its evidence; do not reset or expand it to manufacture annual capacity.")
    selected, issues = [], 0
    # A history declaration orders checks. It cannot grant artifact reuse,
    # source qualification or permission to call the existing adapter.
    candidates = [history] if history_state != "passed" else plan["tasks"][1:]
    for task in candidates:
        identity = task["task_identity_sha256"]
        if identity not in pending:
            continue
        count = len(task["issues_utc"])
        if len(selected) >= max_tasks or issues + count > MAX_FORECAST_ISSUES:
            break
        receipt = active.get(identity)
        selected.append({**deepcopy(task), "expected_receipt_sha256": receipt["receipt_identity_sha256"] if receipt else None})
        issues += count
    body = {
        "dispatch_schema_version": DISPATCH_VERSION,
        "kind": "inert_preparation_dispatch_envelope",
        "status": "candidate_checks_selected" if selected else "no_pending_checks",
        "plan_identity_sha256": plan["plan_identity_sha256"],
        "preparation_binding": deepcopy(plan["preparation_binding"]),
        "journal_identity_sha256": resumed["journal_identity_sha256"],
        "revision_head_sha256": resumed["revision_head_sha256"],
        "revision_count": resumed["revision_count"],
        "selection_policy": "history_declaration_then_original_pending_task_order",
        "history_precondition": {
            "task_identity_sha256": history["task_identity_sha256"],
            "declared_check_state": history_state,
            "receipt_identity_sha256": history_receipt["receipt_identity_sha256"] if history_receipt else None,
            "satisfied_by_declaration": history_state == "passed",
            "artifact_reverified": False, "scientific_qualification_established": False,
        },
        "selected_tasks": selected,
        "bounds": {"max_tasks": max_tasks, "max_selected_forecast_issues": MAX_FORECAST_ISSUES,
                   "selected_task_count": len(selected), "selected_forecast_issue_count": issues,
                   "max_parallel_tasks": 1, "max_journal_revisions": MAX_REVISIONS},
        "resource_use": _resources(),
        **_flags(),
        "limitations": [
            "No preparation adapter or worker is invoked; every result remains a caller declaration.",
            "The full original scope, origin, history and all 18 source leads require independent qualification before any actual adapter can act.",
            "An annual task subset is not a smaller admitted study; the existing two-issue whole-request adapter cannot dispatch it.",
            "The 64-revision journal is a bounded protocol pilot, not annual campaign capacity or durable concurrency control.",
        ],
    }
    return _snapshot({**body, "dispatch_identity_sha256": _hash(body)})


def plan_preparation_dispatch(plan: dict, journal: dict, *, max_tasks: int = 2) -> dict:
    """Select at most two checks and two issue hours without starting work."""
    plan = _plan(plan)
    resumed = resume_preparation_journal(plan, journal)
    return _envelope(plan, resumed, max_tasks)


def _validate_envelope(plan, resumed, envelope):
    envelope = _snapshot(envelope)
    if type(envelope) is not dict or envelope.get("dispatch_schema_version") != DISPATCH_VERSION:
        _fail("INVALID_PREPARATION_DISPATCH", "envelope", "Supply the complete supported inert dispatch envelope.")
    if envelope.get("plan_identity_sha256") != plan["plan_identity_sha256"]:
        _fail("PREPARATION_DISPATCH_SCOPE_MISMATCH", "envelope", "The envelope belongs to another complete request, scope or batch policy.")
    if (envelope.get("journal_identity_sha256") != resumed["journal_identity_sha256"]
            or envelope.get("revision_head_sha256") != resumed["revision_head_sha256"]):
        _fail("STALE_PREPARATION_DISPATCH", "envelope", "The journal changed after selection. Preserve the old candidate and plan against the current complete journal.")
    bounds = envelope.get("bounds")
    if type(bounds) is not dict or "max_tasks" not in bounds:
        _fail("INVALID_PREPARATION_DISPATCH", "envelope.bounds", "The envelope must retain its bounded selection policy.")
    expected = _envelope(plan, resumed, bounds["max_tasks"])
    if _hash(envelope) != _hash(expected):
        _fail("PREPARATION_DISPATCH_MISMATCH", "envelope", "Envelope content, selected checks, prerequisites, resource bounds or identity changed.")
    return expected


def seal_dispatch_result(plan: dict, journal: dict, envelope: dict, outcomes: list[dict]) -> dict:
    """Seal one exact selected outcome set into a candidate journal revision.

    The journal module applies the returned revision only with its separate
    explicit current-journal anchor. Identical candidate sealing is stable;
    this function never applies, persists or executes the candidate.
    """
    plan = _plan(plan)
    resumed = resume_preparation_journal(plan, journal)
    envelope = _validate_envelope(plan, resumed, envelope)
    selected = envelope["selected_tasks"]
    if not selected:
        _fail("NO_PREPARATION_DISPATCH_TASKS", "envelope", "No pending check is selected. An empty envelope creates no candidate revision or scientific qualification.")
    outcomes = _snapshot(outcomes)
    if type(outcomes) is not list or len(outcomes) != len(selected):
        _fail("INVALID_PREPARATION_DISPATCH_OUTCOMES", "outcomes", "Supply exactly one outcome for each selected task, with no omissions or extras.")
    selected_by_index = {task["task_index"]: task for task in selected}
    by_index = {}
    for outcome in outcomes:
        if type(outcome) is not dict or set(outcome) != {"task_index", "check_state", "evidence", "reason"}:
            _fail("INVALID_PREPARATION_DISPATCH_OUTCOMES", "outcomes", "Each outcome has task_index, check_state, evidence and reason only.")
        index = outcome["task_index"]
        if type(index) is not int or index not in selected_by_index or index in by_index:
            _fail("INVALID_PREPARATION_DISPATCH_OUTCOMES", "outcomes.task_index", "Task indices must be known selected integers without duplicates.")
        by_index[index] = outcome
    records = [{**by_index[task["task_index"]], "expected_receipt_sha256": task["expected_receipt_sha256"]}
               for task in selected]
    revision = seal_receipt_revision(plan, journal, records)
    body = {
        "result_schema_version": RESULT_VERSION,
        "kind": "inert_preparation_dispatch_result_candidate",
        "plan_identity_sha256": plan["plan_identity_sha256"],
        "scope_sha256": plan["preparation_binding"]["scope_sha256"],
        "dispatch_identity_sha256": envelope["dispatch_identity_sha256"],
        "based_on_journal_identity_sha256": resumed["journal_identity_sha256"],
        "based_on_revision_head_sha256": resumed["revision_head_sha256"],
        "receipt_revision": revision,
        "resource_use": _resources(),
        **_flags(),
    }
    return _snapshot({**body, "result_identity_sha256": _hash(body)})


__all__ = ["plan_preparation_dispatch", "seal_dispatch_result"]
