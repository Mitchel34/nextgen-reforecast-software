"""Small resident-forcing preparation adapter; no acquisition or execution.

The existing forcing validators check actual decoded bytes against an
independently supplied domain axis and the complete researcher clock scope.
Their source/scientific qualification blockers remain explicit. No decoded
content pass establishes operational source coverage or execution readiness.
"""

from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import re
import time

from ..campaign import CampaignError, _AssetRefusal, _open_resident
from ..forcing import load_forcing_manifest, validate_history, validate_forecast_issue
from . import RequestPreparationError, _snapshot_json, _utc, validate_request
from .readiness import RECEIPT_VERSION, _hash, _time, assess_preparation, preparation_binding


ADAPTER_VERSION = "forcing-preparation-adapter/0.1"
MAX_ISSUES = 2
MAX_CATCHMENTS = 32
MAX_HISTORY_HOURS = 1000
MAX_EXPECTED_ROWS = 50_000
MAX_MANIFEST_BYTES = 64 * 1024
MAX_PAYLOAD_BYTES = 8 * 1024 * 1024
MAX_TOTAL_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_ELAPSED_SECONDS = 5
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_HOUR = timedelta(hours=1)


def _metadata(path, maximum):
    """Preflight with the same symlink/placeholder refusal as the validators."""
    try:
        fd, stat = _open_resident(path, maximum)
    except _AssetRefusal as exc:
        raise CampaignError(f"Resident forcing preflight refused: {exc}") from exc
    try:
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    finally:
        os.close(fd)


def _descriptor(value, binding):
    descriptor = _snapshot_json(value)
    fields = {"evidence_class", "binding", "catchment_ids", "domain_identity_sha256"}
    if type(descriptor) is not dict or set(descriptor) != fields:
        raise RequestPreparationError("INVALID_DOMAIN_DESCRIPTOR", "domain_descriptor", "Supply the separate caller-owned domain descriptor fields.")
    axis = descriptor["catchment_ids"]
    if (descriptor["evidence_class"] != "caller_owned_domain_descriptor"
            or type(axis) is not list or not 1 <= len(axis) <= MAX_CATCHMENTS
            or any(type(item) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", item) for item in axis)
            or len(set(axis)) != len(axis)
            or type(descriptor["domain_identity_sha256"]) is not str
            or not _SHA.fullmatch(descriptor["domain_identity_sha256"])
            or type(descriptor["binding"]) is not dict
            or set(descriptor["binding"]) != {"request_sha256", "scope_sha256"}
            or any(type(item) is not str or not _SHA.fullmatch(item) for item in descriptor["binding"].values())):
        raise RequestPreparationError("INVALID_DOMAIN_DESCRIPTOR", "domain_descriptor", "Use a bounded unique catchment axis and SHA-256 domain/request/scope identities.")
    return descriptor, descriptor["binding"] == {key: binding[key] for key in ("request_sha256", "scope_sha256")}


def check_forcing_preparation(serialized_request: dict, *, domain_descriptor: dict,
                              history_manifest_path: Path | None,
                              forecast_manifest_paths: dict[str, Path], base_dir: Path,
                              origin_time_utc: str | None = None) -> dict:
    """Return adapter evidence plus a preparation-result/0.1 for browser import.

    Paths are explicit local operator inputs, never resolved or downloaded.
    At most two requested issues are checked; oversized studies are refused
    before any forcing read, with their full requested population retained.
    The five-second budget is cooperative between bounded validator calls;
    it does not interrupt a validator or reserve CPU/memory for other tasks.
    """
    request = validate_request(serialized_request)
    binding = preparation_binding(request, origin_time_utc=origin_time_utc)
    started = time.monotonic()
    validations, diagnostics, metadata = [], [], {}
    status = "unknown"
    descriptor_hash = None
    synthetic = False
    completed = False
    bounds = {"max_issues": MAX_ISSUES, "max_catchments": MAX_CATCHMENTS,
              "max_history_hours": MAX_HISTORY_HOURS, "max_expected_rows": MAX_EXPECTED_ROWS,
              "manifest_preflight_bytes": MAX_MANIFEST_BYTES,
              "payload_preflight_bytes": MAX_PAYLOAD_BYTES,
              "total_payload_preflight_bytes": MAX_TOTAL_PAYLOAD_BYTES,
              "validator_hard_payload_bytes_per_call": 32 * 1024 * 1024,
              "cooperative_elapsed_seconds": MAX_ELAPSED_SECONDS}

    def problem(code, message):
        diagnostics.append({"code": code, "message": message})

    def deadline():
        if time.monotonic() - started >= MAX_ELAPSED_SECONDS:
            raise CampaignError("Adapter cooperative time budget exceeded; no further files checked.")

    forecast = request["study"]["mode"] == "reforecast"
    if not forecast:
        problem("MODE_NOT_IMPLEMENTED", "Continuous simulation has no implemented forcing preparation contract.")
    elif origin_time_utc is None:
        problem("INITIALIZATION_NOT_SELECTED", "No files checked before the required history origin is selected.")
    elif binding["scope"]["issue_count"] > MAX_ISSUES:
        status = "failed"
        problem("ADAPTER_SCOPE_LIMIT_EXCEEDED", "This local adapter checks at most two issues; the complete larger study is retained without reads or clipping.")
    else:
        descriptor, matches = _descriptor(domain_descriptor, binding)
        descriptor_hash = _hash(descriptor)
        if not matches:
            status = "failed"
            problem("DOMAIN_BINDING_MISMATCH", "The separate catchment/domain descriptor belongs to another request or initialization scope.")
        else:
            axis = sorted(descriptor["catchment_ids"])
            first = _time(request["study"]["first_issue_time_utc"], "$.study.first_issue_time_utc")
            issues = [_utc(first + index * _HOUR) for index in range(int(binding["scope"]["issue_count"]))]
            history = binding["scope"]["required_history_interval"]
            hours = (_time(history["stop_time_utc_exclusive"], "history.stop") - _time(origin_time_utc, "origin_time_utc")) // _HOUR
            expected_rows = (hours + 18 * len(issues)) * len(axis)
            # Copy caller-owned paths once; concurrent caller edits cannot
            # change validated issue keys or remove a path during iteration.
            manifest_map = (dict(forecast_manifest_paths)
                            if type(forecast_manifest_paths) is dict and len(forecast_manifest_paths) <= MAX_ISSUES else None)
            if hours > MAX_HISTORY_HOURS or expected_rows > MAX_EXPECTED_ROWS:
                status = "failed"
                problem("ADAPTER_SCOPE_LIMIT_EXCEEDED", "The full history/catchment-hour workload exceeds this bounded adapter; no files were checked.")
            elif manifest_map is None or len(manifest_map) > MAX_ISSUES or set(manifest_map) - set(issues):
                raise RequestPreparationError("INVALID_FORECAST_MANIFEST_MAP", "forecast_manifest_paths", "Supply only the exact requested issue keys; other issues cannot substitute or expand this adapter.")
            elif history_manifest_path is None or set(manifest_map) != set(issues) or any(manifest_map[issue] is None for issue in issues):
                status = "missing"
                problem("MANIFEST_NOT_SUPPLIED", "Supply a history manifest and one separate full-horizon forecast manifest for every requested issue.")
            else:
                status = "failed"  # Exceptions and qualification limits never become a pass.
                try:
                    root = Path(base_dir)
                    specs = [("history", None, Path(history_manifest_path))] + [("forecast", issue, Path(manifest_map[issue])) for issue in issues]
                    loaded, total_bytes = [], 0
                    for role, issue, path in specs:
                        deadline()
                        metadata[path] = _metadata(path, MAX_MANIFEST_BYTES)
                        manifest = load_forcing_manifest(path)
                        synthetic = synthetic or manifest["evidence_class"] == "synthetic"
                        payload = root / manifest["payload"]["path"]
                        metadata[payload] = _metadata(payload, MAX_PAYLOAD_BYTES)
                        total_bytes += metadata[payload][2]
                        if total_bytes > MAX_TOTAL_PAYLOAD_BYTES:
                            raise CampaignError("Total preflight payload bytes exceed the bounded adapter.")
                        loaded.append((role, issue, manifest, payload))
                    for role, issue, manifest, payload in loaded:
                        deadline()
                        if _metadata(payload, MAX_PAYLOAD_BYTES) != metadata[payload]:
                            raise CampaignError("Forcing payload changed after adapter preflight.")
                        if role == "history":
                            result = validate_history(manifest, root, expected_catchment_ids=axis,
                                                      start_time_utc=origin_time_utc, stop_time_utc_exclusive=history["stop_time_utc_exclusive"])
                        else:
                            result = validate_forecast_issue(manifest, root, expected_catchment_ids=axis, issue_time_utc=issue)
                        validations.append(result)
                        if _metadata(payload, MAX_PAYLOAD_BYTES) != metadata[payload]:
                            raise CampaignError("Forcing payload changed during adapter validation.")
                    for path, before in metadata.items():
                        deadline()
                        if _metadata(path, MAX_PAYLOAD_BYTES if path in [item[3] for item in loaded] else MAX_MANIFEST_BYTES) != before:
                            raise CampaignError("Manifest or payload changed during preparation checks.")
                    completed = True
                    if all(result["content_valid"] for result in validations):
                        problem("SOURCE_QUALIFICATION_UNRESOLVED", "All decoded content checks passed; upstream truth/version, availability and radiation qualification remain unresolved.")
                    else:
                        problem("FORCING_CONTENT_CHECK_FAILED", "Decoded history or full issue-specific forcing disagrees with the complete independently supplied study contract.")
                except FileNotFoundError as exc:
                    status = "missing"
                    problem("RESIDENT_INPUT_MISSING", "A selected local manifest or payload is absent; this does not establish upstream archive availability. " + str(exc)[:768])
                except (CampaignError, OSError, ValueError, TypeError) as exc:
                    problem("FORCING_INPUT_REFUSED", str(exc)[:1024])

    evidence = {
        "adapter_schema_version": ADAPTER_VERSION,
        "request_sha256": binding["request_sha256"], "scope_sha256": binding["scope_sha256"],
        "domain_descriptor_sha256": descriptor_hash,
        "domain_mapping_authenticated": False,
        "checks_performed": len(validations),
        "complete_check_run": completed,
        "decoded_content_valid": completed and all(item["content_valid"] for item in validations),
        "source_coverage_qualified": False, "execution_ready": False,
        "validations": validations, "diagnostics": diagnostics, "bounds": bounds,
        "acquisition_performed": False, "gap_exclusions_or_imputation_performed": False,
        "population_shortened": False,
    }
    evidence["adapter_identity_sha256"] = _hash(evidence)
    receipts = []
    if status != "unknown":
        qualification = sorted({item["code"] for result in validations for item in result["qualification_blockers"]})
        detail = (f"Resident forcing adapter: {len(validations)} checks; decoded_content_valid={evidence['decoded_content_valid']}. "
                  + " ".join(item["message"] for item in diagnostics)
                  + (" Qualification blockers retained: " + ", ".join(qualification) if qualification else ""))[:2048]
        receipts.append({"receipt_schema_version": RECEIPT_VERSION, "check_id": "source_coverage", "status": status,
                         "binding": {key: binding[key] for key in ("request_sha256", "scope_sha256")},
                         "evidence": {"artifact_sha256": evidence["adapter_identity_sha256"],
                                      "verifier": ADAPTER_VERSION, "evidence_class": "synthetic" if synthetic else "verification_receipt",
                                      "detail": detail}})
    return {"adapter_evidence": evidence,
            "readiness_report": assess_preparation(request, origin_time_utc=origin_time_utc, check_receipts=receipts)}


__all__ = ["ADAPTER_VERSION", "check_forcing_preparation"]
