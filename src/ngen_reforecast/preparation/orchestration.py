"""Pure annual preparation task plans and declared-receipt checkpoints.

No task is dispatched. Reconciliation reconstructs pending *preparation
checks*, not a physical restart or durable service. Receipt hashes identify
caller declarations; they do not authenticate evidence or verify freshness.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import math
import re

from . import RequestPreparationError, _json_text, _utc, validate_request
from .readiness import _time, preparation_binding


PLAN_VERSION = "preparation-orchestration-plan/0.1"
RECEIPT_VERSION = "preparation-task-receipt/0.1"
CHECKPOINT_VERSION = "preparation-receipt-checkpoint/0.1"
MAX_PLAN_ISSUES = 366 * 24
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_NODES = 250_000
_HOUR = timedelta(hours=1)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_STATES = ("unknown", "missing", "failed", "passed")
_ESCAPED = re.compile(r'["\\\x00-\x1f\ud800-\udfff]')
_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _fail(code, field, message):
    raise RequestPreparationError(code, field, message)


def _hash(value):
    """Stream the existing sorted canonical JSON identity without large copies."""
    digest = hashlib.sha256()

    def emit(item):
        if type(item) is dict:
            yield "{"
            for index, key in enumerate(sorted(item)):
                if index:
                    yield ","
                yield from emit(key)
                yield ":"
                yield from emit(item[key])
            yield "}"
        elif type(item) is list:
            yield "["
            for index, child in enumerate(item):
                if index:
                    yield ","
                yield from emit(child)
            yield "]"
        else:
            if type(item) is float and item.is_integer():
                item = int(item)
            text = json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            yield _SURROGATE.sub(lambda match: f"\\u{ord(match[0]):04x}", text)

    for chunk in emit(value):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def _snapshot(value):
    """Separate bounds for annual plans/checkpoints, not request JSON limits."""
    nodes, encoded_bytes, ancestors = 0, 0, set()

    def charge(count):
        nonlocal encoded_bytes
        encoded_bytes += count
        if encoded_bytes > MAX_ARTIFACT_BYTES:
            _fail("ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED", "$", "Each plan, receipt set or checkpoint is limited to 8 MiB.")

    def string_bytes(item):
        # Count before escaping/encoding so repeated strings and large keys
        # cannot allocate a serialization much larger than the accepted bound.
        if len(item) + 2 > MAX_ARTIFACT_BYTES - encoded_bytes:
            _fail("ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED", "$", "The artifact exceeds the UTF-8 byte limit.")
        charge(2)
        if item.isascii() and not _ESCAPED.search(item):
            charge(len(item))
            return
        for char in item:
            point = ord(char)
            if char in '"\\\b\f\n\r\t':
                charge(2)
            elif point < 32 or 0xD800 <= point <= 0xDFFF:
                charge(6)
            else:
                charge(1 if point < 128 else 2 if point < 2048 else 3 if point < 65536 else 4)

    def copy(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_ARTIFACT_NODES or depth > 20:
            _fail("ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED", "$", "The artifact exceeds bounded depth or node limits.")
        if item is None or type(item) is bool:
            charge(4 if item is None or item is True else 5)
            return item
        if type(item) in (int, float):
            if abs(item) > 2**53 - 1 or not math.isfinite(item):
                _fail("INVALID_ORCHESTRATION_ARTIFACT", "$", "Use finite safe JSON numbers.")
            charge(len(_json_text(item)))
            return item
        if type(item) is str:
            string_bytes(item)
            return item
        if type(item) not in (dict, list) or id(item) in ancestors:
            _fail("INVALID_ORCHESTRATION_ARTIFACT", "$", "Use acyclic plain JSON data only.")
        if len(item) > MAX_ARTIFACT_NODES:
            _fail("ORCHESTRATION_ARTIFACT_LIMIT_EXCEEDED", "$", "Too many JSON members.")
        charge(2 + max(0, len(item) - 1))
        ancestors.add(id(item))
        if type(item) is list:
            result = [copy(child, depth + 1) for child in item]
        else:
            result = {}
            for key, child in item.items():
                if type(key) is not str or key in {"__proto__", "constructor", "prototype"}:
                    _fail("INVALID_ORCHESTRATION_ARTIFACT", "$", "Use safe string JSON keys.")
                string_bytes(key)
                charge(1)
                result[key] = copy(child, depth + 1)
        ancestors.remove(id(item))
        return result

    return copy(value, 0)


def plan_preparation(serialized_request: dict, *, origin_time_utc: str,
                     issues_per_task: int = 2) -> dict:
    """Partition an entire request without changing its scientific scope."""
    request = validate_request(serialized_request)
    if request["study"]["mode"] != "reforecast":
        _fail("MODE_NOT_IMPLEMENTED", "$.study.mode", "Continuous simulation has no preparation orchestration contract.")
    if type(issues_per_task) is not int or not 1 <= issues_per_task <= 2:
        _fail("INVALID_BATCH_POLICY", "issues_per_task", "Choose one or two issues per planning task; this does not widen the existing adapter.")
    if origin_time_utc is None:
        _fail("INITIALIZATION_NOT_SELECTED", "origin_time_utc", "Select an explicit origin; no diagnostic origin or shortened initialization is inherited.")
    binding = preparation_binding(request, origin_time_utc=origin_time_utc)
    count = int(request["preview"]["issue_count"])
    if count > MAX_PLAN_ISSUES:
        _fail("PLAN_SCOPE_LIMIT_EXCEEDED", "$.study", "This annual planner supports at most 8,784 issues. The larger request remains intact; it is not clipped.")
    first = _time(request["study"]["first_issue_time_utc"], "$.study.first_issue_time_utc")
    issues = [_utc(first + index * _HOUR) for index in range(count)]
    common = {"request_sha256": binding["request_sha256"], "scope_sha256": binding["scope_sha256"],
              "origin_time_utc": origin_time_utc}
    history = {**common, "task_index": 0, "task_kind": "history_coverage",
               "issues_utc": [], "history_interval": deepcopy(binding["scope"]["required_history_interval"])}
    tasks = [{**history, "task_identity_sha256": _hash(history)}]
    for offset in range(0, count, issues_per_task):
        task = {**common, "task_index": len(tasks), "task_kind": "forecast_issue_coverage",
                "issues_utc": issues[offset:offset + issues_per_task], "history_interval": None}
        tasks.append({**task, "task_identity_sha256": _hash(task)})
    body = {
        "plan_schema_version": PLAN_VERSION, "kind": "offline_preparation_task_plan",
        "request": request, "preparation_binding": binding,
        "batch_policy": {"issues_per_task": issues_per_task, "max_plan_issues": MAX_PLAN_ISSUES,
                         "history_tasks": "one_complete_original_interval", "forecast_source_leads": {"min": 1, "max": 18}},
        "requested_population": {"issues_utc": issues, "preview": deepcopy(request["preview"])},
        "tasks": tasks,
        "dispatch_supported": False, "execution_ready": False, "source_coverage_qualified": False,
        "limitations": ["Current forcing adapter cannot dispatch this annual plan or split its scope into smaller admitted studies.",
                        "The original full history interval and every issue-specific 18-hour source window still require independent qualification.",
                        "No model, source asset, worker, acquisition or artifact verification is performed."],
    }
    return _snapshot({**body, "plan_identity_sha256": _hash(body)})


def _plan(value):
    plan = _snapshot(value)
    if type(plan) is not dict or plan.get("plan_schema_version") != PLAN_VERSION:
        _fail("INVALID_PREPARATION_PLAN", "$", "Supply a supported complete preparation plan.")
    try:
        expected = plan_preparation(plan["request"], origin_time_utc=plan["preparation_binding"]["scope"]["initialization_origin_utc"],
                                    issues_per_task=plan["batch_policy"]["issues_per_task"])
    except (KeyError, TypeError):
        _fail("INVALID_PREPARATION_PLAN", "$", "Supply all original request, initialization and batch-policy fields.")
    if _hash(plan) != _hash(expected):
        _fail("PREPARATION_PLAN_MISMATCH", "$", "Plan content, task population or identity differs from the complete rebuilt request.")
    return plan


def _evidence(value, state):
    if state == "unknown":
        if value is not None:
            _fail("INVALID_TASK_RECEIPT", "evidence", "Unknown check evidence must be null.")
        return
    if (type(value) is not dict or set(value) != {"artifact_sha256", "evidence_class", "detail"}
            or type(value["artifact_sha256"]) is not str or not _SHA.fullmatch(value["artifact_sha256"])
            or value["evidence_class"] not in ("synthetic", "declared_metadata", "verification_receipt")
            or type(value["detail"]) is not str or not value["detail"].strip() or len(value["detail"]) > 512):
        _fail("INVALID_TASK_RECEIPT", "evidence", "Observed outcomes require an artifact SHA-256, explicit evidence class and nonblank detail up to 512 characters.")


def seal_task_receipts(plan: dict, records: list[dict]) -> list[dict]:
    """Bind caller outcomes in bulk; hashes neither authenticate nor verify them."""
    plan = _plan(plan)
    records = _snapshot(records)
    if type(records) is not list or len(records) > len(plan["tasks"]):
        _fail("TASK_RECEIPT_LIMIT_EXCEEDED", "records", "Supply at most one candidate per task in a sealing call.")
    receipts = []
    for record in records:
        if type(record) is not dict or set(record) != {"task_index", "check_state", "evidence"}:
            _fail("INVALID_TASK_RECEIPT", "records", "Supply task_index, check_state and evidence only.")
        index, state = record["task_index"], record["check_state"]
        if type(index) is not int or not 0 <= index < len(plan["tasks"]) or state not in _STATES:
            _fail("INVALID_TASK_RECEIPT", "records", "Use a known integer task index and unknown/missing/failed/passed state.")
        _evidence(record["evidence"], state)
        body = {"receipt_schema_version": RECEIPT_VERSION,
                "plan_identity_sha256": plan["plan_identity_sha256"],
                "scope_sha256": plan["preparation_binding"]["scope_sha256"],
                "task_identity_sha256": plan["tasks"][index]["task_identity_sha256"],
                "check_state": state, "evidence": record["evidence"]}
        receipts.append({**body, "receipt_identity_sha256": _hash(body)})
    return _snapshot(receipts)


def _receipt_set(plan, receipts):
    receipts = _snapshot(receipts)
    if type(receipts) is not list or len(receipts) > 2 * len(plan["tasks"]):
        _fail("TASK_RECEIPT_LIMIT_EXCEEDED", "receipts", "The receipt set exceeds the bounded task population.")
    by_task = {task["task_identity_sha256"]: task for task in plan["tasks"]}
    accepted = {}
    fields = {"receipt_schema_version", "plan_identity_sha256", "scope_sha256", "task_identity_sha256", "check_state", "evidence", "receipt_identity_sha256"}
    for receipt in receipts:
        if type(receipt) is not dict or set(receipt) != fields or receipt["receipt_schema_version"] != RECEIPT_VERSION:
            _fail("INVALID_TASK_RECEIPT", "receipts", "Use the complete supported task receipt schema.")
        task_id = receipt["task_identity_sha256"]
        if (type(task_id) is not str or task_id not in by_task
                or receipt["plan_identity_sha256"] != plan["plan_identity_sha256"]
                or receipt["scope_sha256"] != plan["preparation_binding"]["scope_sha256"]):
            _fail("TASK_RECEIPT_SCOPE_MISMATCH", "receipts", "A receipt belongs to a different plan, original scope or task subset.")
        if receipt["check_state"] not in _STATES:
            _fail("INVALID_TASK_RECEIPT", "check_state", "Unsupported check state.")
        _evidence(receipt["evidence"], receipt["check_state"])
        body = {key: value for key, value in receipt.items() if key != "receipt_identity_sha256"}
        if receipt["receipt_identity_sha256"] != _hash(body):
            _fail("TASK_RECEIPT_IDENTITY_MISMATCH", "receipts", "The recorded receipt content changed.")
        if task_id in accepted and _hash(accepted[task_id]) != _hash(receipt):
            _fail("CONFLICTING_TASK_RECEIPT", "receipts", "Conflicting evidence for one task requires an explicit future supersession contract; nothing is overwritten.")
        accepted[task_id] = receipt
    return [accepted[task["task_identity_sha256"]] for task in plan["tasks"] if task["task_identity_sha256"] in accepted]


def _checkpoint(plan, receipts):
    body = {"checkpoint_schema_version": CHECKPOINT_VERSION,
            "plan_identity_sha256": plan["plan_identity_sha256"],
            "scope_sha256": plan["preparation_binding"]["scope_sha256"],
            "receipts": _receipt_set(plan, receipts),
            "dispatch_supported": False, "execution_ready": False,
            "artifacts_reverified": False, "physical_recovery_established": False}
    return _snapshot({**body, "checkpoint_identity_sha256": _hash(body)})


def _validate_checkpoint(plan, value):
    value = _snapshot(value)
    if type(value) is not dict or "receipts" not in value:
        _fail("INVALID_PREPARATION_CHECKPOINT", "$", "Supply the complete serialized receipt checkpoint.")
    expected = _checkpoint(plan, value["receipts"])
    if _hash(value) != _hash(expected):
        _fail("PREPARATION_CHECKPOINT_MISMATCH", "$", "Checkpoint content, binding, flags or identity changed; do not manufacture a new empty continuation.")
    return expected


def checkpoint_preparation(plan: dict, receipts: list[dict], *, previous: dict | None = None) -> dict:
    """Merge declared receipts deterministically; exact duplicates are idempotent."""
    plan = _plan(plan)
    prior = _validate_checkpoint(plan, previous)["receipts"] if previous is not None else []
    incoming = _receipt_set(plan, receipts)
    # Both sets already passed input bounds and identity checks. Merge before
    # serializing so a repeated complete annual set stays idempotent at 8 MiB.
    accepted = {item["task_identity_sha256"]: item for item in prior}
    for item in incoming:
        identity = item["task_identity_sha256"]
        if identity in accepted and _hash(accepted[identity]) != _hash(item):
            _fail("CONFLICTING_TASK_RECEIPT", "receipts", "Conflicting evidence for one task requires an explicit future supersession contract; nothing is overwritten.")
        accepted[identity] = item
    return _checkpoint(plan, list(accepted.values()))


def resume_preparation(plan: dict, checkpoint: dict) -> dict:
    """Reconstruct pending checks only. No prior artifact is read or reused."""
    plan = _plan(plan)
    checkpoint = _validate_checkpoint(plan, checkpoint)
    recorded = {receipt["task_identity_sha256"]: receipt for receipt in checkpoint["receipts"]}
    tasks, pending, candidates = [], [], []
    for task in plan["tasks"]:
        identity = task["task_identity_sha256"]
        receipt = recorded.get(identity)
        state = receipt["check_state"] if receipt else "not_recorded"
        (candidates if state == "passed" else pending).append(identity)
        tasks.append({"task_identity_sha256": identity, "task_index": task["task_index"],
                      "declared_check_state": state, "artifact_reverified": False})
    return _snapshot({"plan_identity_sha256": plan["plan_identity_sha256"],
            "checkpoint_identity_sha256": checkpoint["checkpoint_identity_sha256"],
            "status": "planning_only", "tasks": tasks,
            "pending_check_task_ids": pending, "declared_reuse_candidate_task_ids": candidates,
            "all_checks_declared_passed": not pending,
            "dispatch_supported": False, "execution_ready": False,
            "source_coverage_qualified": False, "artifacts_reverified": False,
            "physical_recovery_established": False,
            "next_action": "Independently reverify any candidate artifacts and qualify the complete original scope before a separately authorized preparation dispatcher can act."})


__all__ = ["plan_preparation", "seal_task_receipts", "checkpoint_preparation", "resume_preparation"]
