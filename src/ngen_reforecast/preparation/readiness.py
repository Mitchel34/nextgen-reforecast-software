"""Bounded, caller-evidence preparation reports; no acquisition or admission.

Receipts are supplied separately by a trusted preparation adapter. Their
hashes bind a declared check to a study; this module neither reads the cited
artifact nor authenticates a verifier or establishes scientific readiness.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import re

from . import (
    RequestPreparationError, _json_text, _snapshot_json, _utc,
    policy_sha256, request_policy, validate_request,
)


REPORT_VERSION = "preparation-result/0.1"
RECEIPT_VERSION = "preparation-check-receipt/0.1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:00:00Z\Z")
_HOUR = timedelta(hours=1)
# Fixed order makes omitted checks explicit and reports deterministic.
_CHECKS = {
    "location_resolution": "Resolve and version the submitted outlet, gauge/reach mapping and complete upstream domain without substituting a watershed.",
    "initialization": "Select and qualify an initialization origin before the first requested issue; retain its scientific justification.",
    "source_coverage": "Check initialization/history and every requested issue's full 18-hour forcing window, including source gaps and units.",
    "input_bundle": "Prepare and content-verify inputs for the complete study; bind source, domain, configuration and transformation identities.",
    "runtime_identity": "Verify the supported runtime and its exact source, binary, component and routing identities.",
    "reference_set": "Bind qualified independent references to the exact requested population and scientific/input/runtime identities.",
    "scientific_profile": "Qualify scientific parameters, forcing/time semantics and initialization for this study; diagnostic metadata alone is insufficient.",
}
CHECK_IDS = tuple(_CHECKS)


def _fail(code, field, message):
    raise RequestPreparationError(code, field, message)


def _canonical(value):
    if type(value) is dict:
        return {key: _canonical(value[key]) for key in sorted(value)}
    if type(value) is list:
        return [_canonical(item) for item in value]
    # Shared requests contain only integer numeric fields. JSON 6.0 and 6
    # have the same browser representation and must have the same identity.
    if type(value) is float and value.is_integer():
        return int(value)
    return value


def _hash(value):
    return hashlib.sha256(_json_text(_canonical(value)).encode("utf-8")).hexdigest()


def _time(value, field):
    if type(value) is not str or not _TIME.fullmatch(value):
        _fail("INVALID_INITIALIZATION_ORIGIN", field,
              "Use an exact hourly UTC timestamp YYYY-MM-DDTHH:00:00Z.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        _fail("INVALID_INITIALIZATION_ORIGIN", field, "Use a real UTC calendar hour.")


def _binding(request, origin_time_utc):
    forecast = request["study"]["mode"] == "reforecast"
    if origin_time_utc is not None:
        if not forecast:
            _fail("MODE_NOT_IMPLEMENTED", "origin_time_utc",
                  "Continuous simulation has no implemented initialization contract.")
        origin = _time(origin_time_utc, "origin_time_utc")
        first = _time(request["study"]["first_issue_time_utc"], "$.study.first_issue_time_utc")
        last_target = _time(request["preview"]["last_physical_valid_time_utc"], "$.preview.last_physical_valid_time_utc")
        if origin >= first:
            _fail("INVALID_INITIALIZATION_ORIGIN", "origin_time_utc",
                  "Initialization must begin before the first requested issue.")
        if (last_target - origin) // _HOUR > request_policy()["max_history_hours"]:
            _fail("PREPARATION_SCOPE_LIMIT_EXCEEDED", "origin_time_utc",
                  "The complete selected history exceeds the existing offline bound; it cannot be shortened silently.")
    location = request["location"]
    scope = {
        "request_sha256": _hash(request),
        "policy_bytes_sha256": policy_sha256(),
        "submitted_location": {"identifier_type": location["identifier_type"],
                               "submitted_identifier": location["submitted_identifier"]},
        "mode": request["study"]["mode"],
        "initialization_origin_utc": origin_time_utc,
        "required_history_interval": {
            "start_time_utc": origin_time_utc,
            "stop_time_utc_exclusive": request["preview"]["last_physical_valid_time_utc"],
            "provider_label": "interval_start",
            "timestep_hours": 1,
        } if forecast and origin_time_utc is not None else None,
        "issue_schedule": deepcopy(request["campaign_translation_proposal"]["issue_schedule"]) if forecast else None,
        "issue_count": request["preview"]["issue_count"] if forecast else None,
        "horizon_hours": 18 if forecast else None,
        "required_source_leads": {"min": 1, "max": 18} if forecast else None,
        "coverage_requirement": "history_and_each_issue_specific_full_forecast_window" if forecast else "undefined_for_proposed_mode",
        "final_physical_target_utc": request["preview"]["last_physical_valid_time_utc"] if forecast else None,
    }
    return {"request_sha256": scope["request_sha256"],
            "scope_sha256": _hash(scope), "scope": scope}


def preparation_binding(serialized_request: dict, *, origin_time_utc: str | None = None) -> dict:
    """Compute the required binding before an adapter supplies check receipts.

    The origin is an explicit caller selection, never inherited from a
    diagnostic example. Its presence does not establish adequate spinup.
    """
    return _binding(validate_request(serialized_request), origin_time_utc)


def _receipts(check_receipts):
    items = _snapshot_json([] if check_receipts is None else check_receipts)
    if type(items) is not list or len(items) > len(CHECK_IDS):
        _fail("INVALID_PREPARATION_RECEIPT", "check_receipts",
              "Supply a bounded list with at most one receipt per supported check.")
    result = {}
    keys = {"receipt_schema_version", "check_id", "status", "binding", "evidence"}
    for index, item in enumerate(items):
        field = f"check_receipts.{index}"
        if type(item) is not dict or set(item) != keys:
            _fail("INVALID_PREPARATION_RECEIPT", field, "Supply only the versioned check receipt fields.")
        check = item["check_id"]
        if (item["receipt_schema_version"] != RECEIPT_VERSION
                or type(check) is not str or check not in _CHECKS or check in result
                or item["status"] not in ("unknown", "missing", "failed", "passed")):
            _fail("INVALID_PREPARATION_RECEIPT", field,
                  "Use the supported version, a unique check ID and an explicit unknown/missing/failed/passed status.")
        binding = item["binding"]
        if (type(binding) is not dict or set(binding) != {"request_sha256", "scope_sha256"}
                or any(type(value) is not str or not _SHA.fullmatch(value) for value in binding.values())):
            _fail("INVALID_PREPARATION_RECEIPT", f"{field}.binding", "Bind the request and complete scope with lowercase SHA-256 identities.")
        evidence = item["evidence"]
        if item["status"] == "unknown":
            if evidence is not None:
                _fail("INVALID_PREPARATION_RECEIPT", f"{field}.evidence", "Unknown means no reported check evidence; use null.")
        elif (type(evidence) is not dict
              or set(evidence) != {"artifact_sha256", "verifier", "evidence_class", "detail"}
              or type(evidence["artifact_sha256"]) is not str or not _SHA.fullmatch(evidence["artifact_sha256"])
              or evidence["evidence_class"] not in ("synthetic", "declared_metadata", "verification_receipt")
              or any(type(evidence[key]) is not str or not evidence[key].strip() or len(evidence[key]) > 2048
                     for key in ("verifier", "detail"))):
            _fail("INVALID_PREPARATION_RECEIPT", f"{field}.evidence",
                  "An observed outcome needs an artifact identity, verifier, evidence class and concise detail.")
        result[check] = item
    return result


def _blocker(code, requirement, message, next_option, evidence=None):
    return {"code": code, "requirement": requirement, "message": message,
            "next_option": next_option, "evidence": deepcopy(evidence)}


def assess_preparation(serialized_request: dict, *, origin_time_utc: str | None = None,
                       check_receipts: list[dict] | None = None) -> dict:
    """Aggregate declared check outcomes without verifying artifacts or executing.

    A mismatched but well-formed receipt becomes an actionable blocker. Bad
    receipt syntax raises RequestPreparationError. Even all-passed receipts
    mean caller-reported checks only; execution and release remain blocked.
    """
    request = validate_request(serialized_request)
    binding = _binding(request, origin_time_utc)
    receipts = _receipts(check_receipts)
    forecast = request["study"]["mode"] == "reforecast"
    blockers, checks = [], []
    for check, action in _CHECKS.items():
        receipt = receipts.get(check)
        status = receipt["status"] if receipt else "unknown"
        evidence = receipt["evidence"] if receipt else None
        if receipt and receipt["binding"] != {key: binding[key] for key in ("request_sha256", "scope_sha256")}:
            status = "evidence_mismatch"
        checks.append({"check_id": check, "status": status,
                       "reported_status": receipt["status"] if receipt else None,
                       "receipt_sha256": _hash(receipt) if receipt else None,
                       "reported_binding": deepcopy(receipt["binding"]) if receipt else None,
                       "evidence": deepcopy(evidence), "artifact_verified_by_this_interface": False})
        if status == "evidence_mismatch":
            blockers.append(_blocker("PREPARATION_EVIDENCE_BINDING_MISMATCH", check,
                                     "The receipt belongs to a different request, policy or initialization scope; its outcome is unusable.",
                                     "Recheck the complete current scope and issue a newly bound receipt; retain the earlier evidence.", evidence))
        elif status != "passed":
            message = {"unknown": "No usable check outcome is reported; availability and qualification remain unknown.",
                       "missing": "The adapter reports a required prerequisite is absent.",
                       "failed": "The adapter reports the check failed; this does not establish that inputs are absent."}[status]
            blockers.append(_blocker(f"{check.upper()}_{status.upper()}", check, message, action, evidence))
    if not forecast:
        blockers.insert(0, _blocker("MODE_NOT_IMPLEMENTED", "mode", "Continuous simulation remains a proposed mode; no issue population is created.", "Define and qualify its separate date and preparation contract."))
    elif origin_time_utc is None:
        blockers.insert(0, _blocker("INITIALIZATION_NOT_SELECTED", "initialization_origin", "No initialization origin is selected, so the complete required history is unknown.", _CHECKS["initialization"]))
    reported_passed = forecast and origin_time_utc is not None and all(item["status"] == "passed" for item in checks)
    blockers.extend([
        _blocker("CAMPAIGN_PROTOCOL_NOT_ADMITTED", "execution_admission", "Preparation receipts do not verify or authorize an identity-bound execution protocol.", "Independently admit the scientific/input/runtime/reference identities and fresh bounded run authority before execution."),
        _blocker("EXECUTION_SERVICE_UNAVAILABLE", "execution_service", "This offline contract does not submit jobs or provide verified downloads.", "Connect a separately implemented and authorized execution/result adapter after preparation checks."),
    ])
    preview = deepcopy(request["preview"])
    issues = []
    if forecast:
        first = _time(request["study"]["first_issue_time_utc"], "$.study.first_issue_time_utc")
        issues = [_utc(first + index * _HOUR) for index in range(int(preview["issue_count"]))]
    report = {
        "preparation_result_schema_version": REPORT_VERSION,
        "artifact_type": "preparation_result",
        "assessment_kind": "offline_caller_evidence_aggregation",
        "status": "blocked",
        "preparation_checks_status": "all_reported_passed" if reported_passed else "incomplete",
        "planning_supported": forecast,
        "execution_ready": False, "release_qualified": False,
        "requested_request": request,
        "requested_population": {"issues_utc": issues if forecast else None,
                                 "preview": preview,
                                 "retained_leads": deepcopy(request["campaign_translation_proposal"]["retained_leads"]) if forecast else None,
                                 "population_status": "complete_requested_issue_list" if forecast else "undefined_for_proposed_mode"},
        "preparation_binding": binding,
        "checks": checks,
        "blockers": blockers,
        "evidence_boundary": {"receipt_source": "caller_supplied_separately_from_request",
                              "artifacts_read_or_verified": False,
                              "verifier_authenticated": False,
                              "freshness_established": False,
                              "scientific_qualification_established": False,
                              "execution_admission_established": False},
    }
    report["identities"] = {"canonicalization": "sorted-json-utf8-v1",
                            "report_sha256": _hash(report),
                            "report_hash_excludes": ["identities"],
                            "establishes_admission": False}
    return report


__all__ = ["REPORT_VERSION", "RECEIPT_VERSION", "CHECK_IDS", "preparation_binding", "assess_preparation"]
