"""Bounded append-only declaration supersession, without persistence or dispatch.

The caller owns storage and its trusted latest journal identity. Hash chains
validate the supplied history; they do not authenticate evidence, detect an
unanchored rollback or serialize concurrent writers in an external store.
"""

from .orchestration import (
    _SHA, _checkpoint, _fail, _hash, _plan, _receipt_set, _snapshot, _validate_checkpoint,
    seal_task_receipts,
)


JOURNAL_VERSION = "preparation-receipt-journal/0.1"
REVISION_VERSION = "preparation-receipt-revision/0.1"
MAX_REVISIONS = 64
MAX_UPDATES_PER_REVISION = 2
_FLAGS = {"dispatch_supported": False, "execution_ready": False,
          "artifacts_reverified": False, "source_coverage_qualified": False,
          "physical_recovery_established": False, "durable_storage_established": False}


def _genesis(plan, checkpoint):
    return _hash({"journal_schema_version": JOURNAL_VERSION,
                  "plan_identity_sha256": plan["plan_identity_sha256"],
                  "scope_sha256": plan["preparation_binding"]["scope_sha256"],
                  "base_checkpoint_identity_sha256": checkpoint["checkpoint_identity_sha256"]})


def _journal(plan, base, revisions, head):
    body = {"journal_schema_version": JOURNAL_VERSION,
            "plan_identity_sha256": plan["plan_identity_sha256"],
            "scope_sha256": plan["preparation_binding"]["scope_sha256"],
            "base_checkpoint": base, "revisions": revisions,
            "revision_count": len(revisions), "revision_head_sha256": head, **_FLAGS}
    # Bound the complete artifact before hashing or returning it. The base is
    # never compacted to make room for new events; a full journal must refuse.
    body = _snapshot(body)
    return _snapshot({**body, "journal_identity_sha256": _hash(body)})


def _revision(plan, value):
    revision = _snapshot(value)
    fields = {"revision_schema_version", "plan_identity_sha256", "scope_sha256",
              "revision_index", "parent_revision_identity_sha256", "updates", "revision_identity_sha256"}
    if type(revision) is not dict or set(revision) != fields or revision["revision_schema_version"] != REVISION_VERSION:
        _fail("INVALID_RECEIPT_REVISION", "revision", "Supply exactly the supported sealed revision fields.")
    if (revision["plan_identity_sha256"] != plan["plan_identity_sha256"]
            or revision["scope_sha256"] != plan["preparation_binding"]["scope_sha256"]):
        _fail("RECEIPT_REVISION_SCOPE_MISMATCH", "revision", "A revision must bind the complete original plan and scope.")
    if (type(revision["revision_index"]) is not int or not 1 <= revision["revision_index"] <= MAX_REVISIONS
            or type(revision["parent_revision_identity_sha256"]) is not str
            or not _SHA.fullmatch(revision["parent_revision_identity_sha256"])):
        _fail("INVALID_RECEIPT_REVISION", "revision", "Use a bounded integer revision and exact parent SHA-256.")
    updates = revision["updates"]
    if type(updates) is not list or not 1 <= len(updates) <= MAX_UPDATES_PER_REVISION:
        _fail("RECEIPT_REVISION_LIMIT_EXCEEDED", "updates", "A revision contains one or two task replacements.")
    seen = set()
    for update in updates:
        if type(update) is not dict or set(update) != {"task_index", "expected_receipt_sha256", "receipt", "reason"}:
            _fail("INVALID_RECEIPT_REVISION", "updates", "Supply the task index, expected prior identity, replacement receipt and reason.")
        index, expected = update["task_index"], update["expected_receipt_sha256"]
        if type(index) is not int or not 0 <= index < len(plan["tasks"]):
            _fail("INVALID_RECEIPT_REVISION", "task_index", "Use a known integer task index.")
        if index in seen:
            _fail("DUPLICATE_REVISION_TASK", "updates", "Each task appears at most once per atomic revision.")
        seen.add(index)
        if expected is not None and (type(expected) is not str or not _SHA.fullmatch(expected)):
            _fail("INVALID_RECEIPT_REVISION", "expected_receipt_sha256", "Use the prior receipt SHA-256, or null only for an unrecorded task.")
        if type(update["reason"]) is not str or not update["reason"].strip() or len(update["reason"]) > 512:
            _fail("INVALID_RECEIPT_REVISION", "reason", "Give a nonblank supersession reason up to 512 characters.")
        receipt = _receipt_set(plan, [update["receipt"]])[0]
        if receipt["task_identity_sha256"] != plan["tasks"][index]["task_identity_sha256"]:
            _fail("RECEIPT_REVISION_SCOPE_MISMATCH", "task_index", "The replacement receipt must belong to the named original task.")
        if receipt["receipt_identity_sha256"] == expected:
            _fail("RECEIPT_REVISION_NO_CHANGE", "updates", "Do not append unchanged evidence; replay the original sealed revision instead.")
    indices = [item["task_index"] for item in updates]
    if indices != sorted(indices):
        _fail("INVALID_RECEIPT_REVISION", "updates", "Use canonical increasing task order within a revision.")
    body = {key: value for key, value in revision.items() if key != "revision_identity_sha256"}
    if revision["revision_identity_sha256"] != _hash(body):
        _fail("RECEIPT_REVISION_IDENTITY_MISMATCH", "revision", "The sealed revision content changed.")
    return revision


def _advance(plan, active, revision, head, index):
    if revision["revision_index"] != index or revision["parent_revision_identity_sha256"] != head:
        _fail("STALE_RECEIPT_REVISION", "revision", "The revision does not extend this exact current history; no branch is merged.")
    # Compare all replacements against the pre-revision state before applying
    # any of them. Caller objects remain untouched on either failure or success.
    for update in revision["updates"]:
        task = plan["tasks"][update["task_index"]]["task_identity_sha256"]
        current = active.get(task)
        actual = current["receipt_identity_sha256"] if current else None
        if update["expected_receipt_sha256"] != actual:
            _fail("STALE_TASK_RECEIPT", "expected_receipt_sha256", "The expected receipt is not current; preserve both histories for review.")
    for update in revision["updates"]:
        active[update["receipt"]["task_identity_sha256"]] = update["receipt"]


def _state(plan, value):
    journal = _snapshot(value)
    if (type(journal) is not dict or journal.get("journal_schema_version") != JOURNAL_VERSION
            or "base_checkpoint" not in journal or type(journal.get("revisions")) is not list):
        _fail("INVALID_PREPARATION_JOURNAL", "journal", "Supply the complete supported journal with its original checkpoint and revision history.")
    if len(journal["revisions"]) > MAX_REVISIONS:
        _fail("RECEIPT_REVISION_LIMIT_EXCEEDED", "revisions", "The bounded pilot journal supports at most 64 revisions; history cannot be reset or compacted implicitly.")
    if type(journal.get("revision_count")) is not int or journal["revision_count"] != len(journal["revisions"]):
        _fail("PREPARATION_JOURNAL_MISMATCH", "revision_count", "The exact integer revision count must match the retained history.")
    base = _validate_checkpoint(plan, journal["base_checkpoint"])
    active = {item["task_identity_sha256"]: item for item in base["receipts"]}
    head = _genesis(plan, base)
    revisions = []
    for index, value in enumerate(journal["revisions"], 1):
        revision = _revision(plan, value)
        _advance(plan, active, revision, head, index)
        revisions.append(revision)
        head = revision["revision_identity_sha256"]
    expected = _journal(plan, base, revisions, head)
    if _hash(journal) != _hash(expected):
        _fail("PREPARATION_JOURNAL_MISMATCH", "journal", "Journal binding, flags, count, tip, content or identity changed.")
    return expected, active


def start_preparation_journal(plan: dict, checkpoint: dict | None = None) -> dict:
    """Keep the complete validated original checkpoint as immutable evidence."""
    plan = _plan(plan)
    base = _validate_checkpoint(plan, checkpoint) if checkpoint is not None else _checkpoint(plan, [])
    return _journal(plan, base, [], _genesis(plan, base))


def seal_receipt_revision(plan: dict, journal: dict, records: list[dict]) -> dict:
    """Seal explicit expected-parent replacements; perform no declared check."""
    plan = _plan(plan)
    journal, active = _state(plan, journal)
    if journal["revision_count"] >= MAX_REVISIONS:
        _fail("RECEIPT_REVISION_LIMIT_EXCEEDED", "revisions", "This journal has reached its explicit pilot bound; preserve it intact.")
    records = _snapshot(records)
    if type(records) is not list or not 1 <= len(records) <= MAX_UPDATES_PER_REVISION:
        _fail("RECEIPT_REVISION_LIMIT_EXCEEDED", "records", "Seal one or two explicit replacements per revision.")
    expected_fields = {"task_index", "expected_receipt_sha256", "check_state", "evidence", "reason"}
    if any(type(item) is not dict or set(item) != expected_fields for item in records):
        _fail("INVALID_RECEIPT_REVISION", "records", "Supply task_index, expected_receipt_sha256, check_state, evidence and reason only.")
    receipts = seal_task_receipts(plan, [{key: item[key] for key in ("task_index", "check_state", "evidence")} for item in records])
    # Sorting distinct task indices gives one deterministic operation identity
    # for equivalent batches, independent of caller record order.
    updates = [{"task_index": item["task_index"], "expected_receipt_sha256": item["expected_receipt_sha256"],
                "receipt": receipt, "reason": item["reason"]} for item, receipt in zip(records, receipts)]
    updates.sort(key=lambda item: item["task_index"])
    body = {"revision_schema_version": REVISION_VERSION,
            "plan_identity_sha256": plan["plan_identity_sha256"], "scope_sha256": plan["preparation_binding"]["scope_sha256"],
            "revision_index": journal["revision_count"] + 1,
            "parent_revision_identity_sha256": journal["revision_head_sha256"], "updates": updates}
    revision = _revision(plan, {**body, "revision_identity_sha256": _hash(body)})
    _advance(plan, active, revision, journal["revision_head_sha256"], journal["revision_count"] + 1)
    # A candidate that cannot fit the complete resulting journal is refused
    # now rather than inviting callers to erase old evidence before applying.
    _journal(plan, journal["base_checkpoint"], journal["revisions"] + [revision], revision["revision_identity_sha256"])
    return revision


def apply_receipt_revision(plan: dict, journal: dict, revision: dict, *, expected_journal_identity_sha256: str) -> dict:
    """Apply an anchored declaration update, or acknowledge its exact replay."""
    plan = _plan(plan)
    journal, active = _state(plan, journal)
    if (type(expected_journal_identity_sha256) is not str
            or expected_journal_identity_sha256 != journal["journal_identity_sha256"]):
        _fail("STALE_PREPARATION_JOURNAL", "expected_journal_identity_sha256", "The supplied journal differs from the caller's pinned current identity.")
    revision = _revision(plan, revision)
    if any(item["revision_identity_sha256"] == revision["revision_identity_sha256"] for item in journal["revisions"]):
        return journal
    if journal["revision_count"] >= MAX_REVISIONS:
        _fail("RECEIPT_REVISION_LIMIT_EXCEEDED", "revisions", "The journal revision bound is reached; no evidence is replaced or dropped.")
    _advance(plan, active, revision, journal["revision_head_sha256"], journal["revision_count"] + 1)
    return _journal(plan, journal["base_checkpoint"], journal["revisions"] + [revision], revision["revision_identity_sha256"])


def resume_preparation_journal(plan: dict, journal: dict) -> dict:
    """Reconstruct declarations; currentness requires an external trusted tip."""
    plan = _plan(plan)
    journal, active = _state(plan, journal)
    current, pending, candidates = [], [], []
    for task in plan["tasks"]:
        identity = task["task_identity_sha256"]
        receipt = active.get(identity)
        if receipt:
            current.append(receipt)
        (candidates if receipt and receipt["check_state"] == "passed" else pending).append(identity)
    return _snapshot({"journal_identity_sha256": journal["journal_identity_sha256"],
                      "plan_identity_sha256": plan["plan_identity_sha256"],
                      "revision_head_sha256": journal["revision_head_sha256"], "revision_count": journal["revision_count"],
                      "current_task_receipts": current, "pending_check_task_ids": pending,
                      "declared_reuse_candidate_task_ids": candidates, "all_checks_declared_passed": not pending,
                      "status": "planning_only", "freshness_established": False, **_FLAGS})


__all__ = ["start_preparation_journal", "seal_receipt_revision", "apply_receipt_revision", "resume_preparation_journal"]
