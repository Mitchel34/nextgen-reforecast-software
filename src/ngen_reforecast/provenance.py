"""Deterministic offline planning locks; never execution admission or signatures.

These snapshots bind declared metadata and resident input bytes. Scientific
interpretation, source truth, model qualification and rights remain unverified.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .campaign import (
    CampaignError, _AssetRefusal, _canonical, _nonfinite, _object,
    _open_resident, _pairs, _read_bounded, normalize_campaign, plan_campaign,
)

MAX_LOCK_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE_BYTES = 1024 * 1024
EVIDENCE_FIELDS = (
    "runtime", "source_objects", "transformations", "gap_policy",
    "scientific_configuration", "output_schema",
)
LOCK_FIELDS = {
    "schema_version", "kind", "campaign", "evidence", "unknown_evidence",
    "experiment_identity_sha256", "domain_identities", "execution_ready",
    "metadata_status", "lock_sha256",
}


class ProvenanceError(CampaignError):
    """A planning lock is malformed, changed, or has unbound input bytes."""


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _evidence(value: dict | None) -> dict:
    if value is None:
        return dict.fromkeys(EVIDENCE_FIELDS)
    _object(value, set(EVIDENCE_FIELDS), "evidence")
    for field, item in value.items():
        if item is not None and (not isinstance(item, dict) or not item):
            raise ProvenanceError(f"evidence.{field} must be null or a nonempty metadata object")
    data = _canonical(value)
    if len(data) > MAX_EVIDENCE_BYTES:
        raise ProvenanceError("Evidence exceeds the 1 MiB metadata bound")
    return json.loads(data)


def _payload(spec: dict, evidence: dict | None) -> dict:
    campaign = normalize_campaign(spec)
    context = _evidence(evidence)
    common = {key: value for key, value in campaign.items() if key != "domains"}
    payload = {
        "schema_version": "planning-lock/0.1",
        "kind": "planning_provenance",
        "campaign": campaign,
        "evidence": context,
        "unknown_evidence": [field for field in EVIDENCE_FIELDS if context[field] is None],
        "experiment_identity_sha256": _digest({"campaign": campaign, "evidence": context}),
        "domain_identities": [
            {"domain_id": domain["domain_id"],
             "identity_sha256": _digest({"campaign": common, "domain": domain, "evidence": context})}
            for domain in campaign["domains"]
        ],
        "execution_ready": False,
        "metadata_status": "declared_unvalidated",
    }
    return {**payload, "lock_sha256": _digest(payload)}


def seal_lock(spec: dict, base_dir: Path, evidence: dict | None = None) -> dict:
    """Bind a plan only when every declared asset role and resident hash passes.

    Unknown scientific/runtime metadata stays null. Even fully declared metadata
    does not make this an execution lock; RF-004/005/007 admission is separate.
    The caller publishes the returned value atomically without overwriting files.
    """
    lock = _payload(spec, evidence)
    if len(_canonical(lock)) > MAX_LOCK_BYTES:
        raise ProvenanceError("Planning lock exceeds the 8 MiB bound")
    plan = plan_campaign(lock["campaign"], Path(base_dir), check_assets=True)
    failures = [item for item in plan["blockers"] if item["code"] != "runtime_not_qualified"]
    if failures:
        codes = sorted({item["code"] for item in failures})
        raise ProvenanceError(f"Cannot seal planning lock: input identity checks failed: {', '.join(codes)}")
    return lock


def _validate_lock(lock: dict) -> None:
    _object(lock, LOCK_FIELDS, "planning lock")
    if len(_canonical(lock)) > MAX_LOCK_BYTES:
        raise ProvenanceError("Planning lock exceeds the 8 MiB bound")
    expected = _payload(lock["campaign"], lock["evidence"])
    if _canonical(lock) != _canonical(expected):
        raise ProvenanceError("Planning lock content, identity or fixed evidence boundary changed")


def load_lock(path: Path) -> dict:
    """Read bounded resident JSON without symlink following or hydration."""
    try:
        fd, before = _open_resident(Path(path), MAX_LOCK_BYTES)
        try:
            data = _read_bounded(fd, before.st_size)
            after = os.fstat(fd)
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ProvenanceError("Planning lock changed during read")
        finally:
            os.close(fd)
        lock = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, _AssetRefusal) as exc:
        raise ProvenanceError(f"Cannot load planning lock: {exc}") from exc
    _validate_lock(lock)
    return lock


def verify_lock(lock: dict, base_dir: Path) -> dict:
    """Recheck snapshot consistency and current bytes, never model readiness."""
    _validate_lock(lock)
    plan = plan_campaign(lock["campaign"], Path(base_dir), check_assets=True)
    failures = [item for item in plan["blockers"] if item["code"] != "runtime_not_qualified"]
    return {
        "schema_version": "planning-lock-verification/0.1",
        "lock_sha256": lock["lock_sha256"],
        "metadata_integrity": True,
        "input_bytes_verified": not failures,
        "execution_ready": False,
        "scientific_semantics_verified": False,
        "unknown_evidence": lock["unknown_evidence"],
        "blockers": plan["blockers"],
        "assets": plan["assets"],
        "scope": "Planning snapshot and resident bytes only; not authenticity, rights or physical qualification.",
    }
