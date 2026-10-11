"""Bounded decoded-weather content checks, not source or runtime qualification.

CSV fixtures are independently authored adapter contracts. They are not the
original research files and are not read by a native model in this module.
"""
from __future__ import annotations

from copy import deepcopy
import csv
from datetime import timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from .campaign import (
    CampaignError, _AssetRefusal, _asset_path, _canonical, _format_time,
    _identifier, _integer, _nonfinite, _object, _open_resident, _pairs,
    _read_bounded, _SHA256, _time,
)

MAX_MANIFEST_BYTES = 1024 * 1024
MAX_CSV_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100_000
MAX_CATCHMENTS = 1024
MAX_HISTORY_HOURS = 100_000
MAX_SOURCE_OBJECTS = 4096
MAX_SOURCE_SEGMENTS = 4096
MAX_SEGMENT_BYTES = 16 * 1024 * 1024
_HOUR = timedelta(hours=1)
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
TIME_COLUMNS = (
    "catchment_id", "provider_time_utc", "precip_source_time_utc",
    "other_source_time_utc", "issue_time_utc", "lead_hour",
)
OUTPUT_UNITS = {
    "precip_rate": "kg m-2 s-1", "TMP_2maboveground": "K",
    "SPFH_2maboveground": "kg kg-1", "UGRD_10maboveground": "m s-1",
    "VGRD_10maboveground": "m s-1", "PRES_surface": "Pa",
    "DSWRF_surface": "W m-2", "DLWRF_surface": "W m-2",
}
HISTORY_VARIABLES = dict(zip(
    ("APCP", *tuple(OUTPUT_UNITS)[1:]), OUTPUT_UNITS,
))
FORECAST_VARIABLES = dict(zip(
    ("RAINRATE", "T2D", "Q2D", "U2D", "V2D", "PSFC", "SWDOWN", "LWDOWN"),
    OUTPUT_UNITS,
))
HISTORY_UNITS = {key: OUTPUT_UNITS[value] for key, value in HISTORY_VARIABLES.items()}
HISTORY_UNITS["APCP"] = "kg m-2"
FORECAST_UNITS = {key: OUTPUT_UNITS[value] for key, value in FORECAST_VARIABLES.items()}
HISTORY_TRANSFORMATION = {
    "id": "aorc_end_label_to_hourly_provider", "version": "1",
    "precipitation": {"source_variable": "APCP", "source_units": "kg m-2",
                      "output_variable": "precip_rate", "output_units": "kg m-2 s-1",
                      "source_time_offset_hours": 1, "divisor": 3600},
    "other_fields_time": "same_label_engineering_interpretation",
    "shortwave_interpretation": "unresolved_same_label",
}
FORECAST_TRANSFORMATION = {
    "id": "nwm_rate_to_hourly_provider", "version": "1",
    "precipitation": {"source_variable": "RAINRATE", "source_units": "kg m-2 s-1",
                      "output_variable": "precip_rate", "output_units": "kg m-2 s-1",
                      "source_time_offset_hours": 1, "divisor": 1},
    "other_fields_time": "forecast_valid_end_label",
    "shortwave_interpretation": "declared_source_interval_unqualified",
}
MANIFEST_FIELDS = {
    "schema_version", "evidence_class", "role", "payload", "catchment_ids",
    "start_time_utc", "stop_time_utc_exclusive", "units", "source", "transformation",
}


class ForcingError(CampaignError):
    """Malformed or unsafe forcing contract, before scientific admission."""


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: Any, where: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ForcingError(f"{where} must be a lowercase SHA-256 digest")


def _text(value: Any, where: str) -> None:
    if (not isinstance(value, str) or not value or len(value) > 2048
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ForcingError(f"{where} must be bounded nonempty text without control characters")


def _axis(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CATCHMENTS:
        raise ForcingError(f"{where} must contain 1..{MAX_CATCHMENTS} catchments")
    for item in value:
        _identifier(item, where)
    if len(set(value)) != len(value):
        raise ForcingError(f"{where} cannot contain duplicate catchments")
    return sorted(value)


def _resident_bytes(path: Path, maximum: int) -> bytes:
    try:
        fd, before = _open_resident(path, maximum)
        try:
            data = _read_bounded(fd, before.st_size)
            after = os.fstat(fd)
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ForcingError("Forcing input changed during read")
        finally:
            os.close(fd)
        return data
    except (OSError, _AssetRefusal) as exc:
        raise ForcingError(f"Cannot read resident forcing input: {exc}") from exc


def _manifest(value: dict) -> dict:
    """Validate shape and bounds; scientific agreement is checked separately."""
    if len(_canonical(value)) > MAX_MANIFEST_BYTES:
        raise ForcingError("Forcing manifest exceeds the 1 MiB bound")
    _object(value, MANIFEST_FIELDS, "forcing manifest")
    if value["schema_version"] not in ("forcing-manifest/0.1", "forcing-manifest/0.2"):
        raise ForcingError("Unsupported forcing manifest schema")
    if value["evidence_class"] not in ("synthetic", "source_declared"):
        raise ForcingError("evidence_class must be synthetic or source_declared")
    if value["role"] not in ("history", "forecast"):
        raise ForcingError("role must be history or forecast")
    payload = _object(value["payload"], {"path", "sha256", "size_bytes"}, "payload")
    _asset_path(payload["path"], "payload.path")
    _sha(payload["sha256"], "payload.sha256")
    _integer(payload["size_bytes"], 1, MAX_CSV_BYTES, "payload.size_bytes")
    _axis(value["catchment_ids"], "catchment_ids")
    _time(value["start_time_utc"], "start_time_utc")
    _time(value["stop_time_utc_exclusive"], "stop_time_utc_exclusive")
    if not isinstance(value["units"], dict) or not value["units"]:
        raise ForcingError("units must be a nonempty object")
    source = _object(value["source"], {
        "kind", "product", "issue_time_utc", "objects", "decoder_sha256", "grid_sha256",
    }, "source")
    for field in ("kind", "product"):
        _text(source[field], f"source.{field}")
    if source["issue_time_utc"] is not None:
        _time(source["issue_time_utc"], "source.issue_time_utc")
    for field in ("decoder_sha256", "grid_sha256"):
        _sha(source[field], f"source.{field}")
    objects = source["objects"]
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_SOURCE_OBJECTS:
        raise ForcingError(f"source.objects must contain 1..{MAX_SOURCE_OBJECTS} declarations")
    identities = set()
    segment_count = 0
    for item in objects:
        fields = {"object_key", "generation", "size_bytes", "sha256"}
        segmented = value["schema_version"] == "forcing-manifest/0.2"
        _object(item, fields | ({"segments"} if segmented else set()), "source object")
        for field in ("object_key", "generation"):
            _text(item[field], f"source object.{field}")
        _integer(item["size_bytes"], 1, 2**53 - 1, "source object.size_bytes")
        if not segmented or item["sha256"] is not None:
            _sha(item["sha256"], "source object.sha256")
        if segmented:
            segments = item["segments"]
            if not isinstance(segments, list):
                raise ForcingError("Source segments must be a list")
            segment_count += len(segments)
            if segment_count > MAX_SOURCE_SEGMENTS:
                raise ForcingError("Source segment count exceeds bound")
            if item["sha256"] is None and not segments:
                raise ForcingError("Sparse source requires fetched segment identities")
            if item["sha256"] is not None and segments:
                raise ForcingError("Whole-object and sparse identities must be separate declarations")
            end = 0
            for segment in segments:
                _object(segment, {"start_byte", "size_bytes", "sha256"}, "source segment")
                _integer(segment["start_byte"], 0, item["size_bytes"] - 1, "source segment.start_byte")
                _integer(segment["size_bytes"], 1, MAX_SEGMENT_BYTES, "source segment.size_bytes")
                _sha(segment["sha256"], "source segment.sha256")
                if segment["start_byte"] < end:
                    raise ForcingError("Source segments must be sorted and nonoverlapping")
                end = segment["start_byte"] + segment["size_bytes"]
                if end > item["size_bytes"]:
                    raise ForcingError("Source segment exceeds whole-object size")
        identity = (item["object_key"], item["generation"])
        if identity in identities:
            raise ForcingError("Duplicate source object key/generation")
        identities.add(identity)
    if not isinstance(value["transformation"], dict) or not value["transformation"]:
        raise ForcingError("transformation must be a nonempty object")
    return deepcopy(value)


def load_forcing_manifest(path: Path) -> dict:
    """Load strict resident JSON, refusing placeholders, symlinks and duplicates."""
    try:
        value = json.loads(_resident_bytes(Path(path), MAX_MANIFEST_BYTES).decode("utf-8"),
                           object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ForcingError(f"Cannot parse forcing manifest: {exc}") from exc
    return _manifest(value)


class _Problems:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def add(self, code: str, message: str, sample: Any = None, count: int = 1) -> None:
        entry = self.items.setdefault(code, {"code": code, "message": message, "count": 0, "samples": []})
        entry["count"] += count
        if sample is not None and len(entry["samples"]) < 5:
            entry["samples"].append(sample)

    def list(self) -> list[dict]:
        return [self.items[key] for key in sorted(self.items)]


def _validate(manifest: dict, base_dir: Path, *, role: str, expected_catchment_ids: list[str],
              start_time_utc: str, stop_time_utc_exclusive: str, issue_time_utc: str | None) -> dict:
    m = _manifest(manifest)
    axis = _axis(expected_catchment_ids, "expected_catchment_ids")
    start = _time(start_time_utc, "expected start")
    stop = _time(stop_time_utc_exclusive, "expected exclusive stop")
    hours = (stop - start) // _HOUR
    _integer(hours, 1, MAX_HISTORY_HOURS, "expected hourly intervals")
    expected_count = hours * len(axis)
    if expected_count > MAX_ROWS:
        raise ForcingError(f"Expected catchment-hour product exceeds {MAX_ROWS} rows")
    expected = {"role": role, "catchment_ids": axis, "start_time_utc": start_time_utc,
                "stop_time_utc_exclusive": stop_time_utc_exclusive, "issue_time_utc": issue_time_utc}
    problems = _Problems()
    for field in ("role", "start_time_utc", "stop_time_utc_exclusive"):
        if m[field] != expected[field]:
            problems.add("contract_mismatch", "Manifest disagrees with independently supplied expected contract", field)
    if sorted(m["catchment_ids"]) != axis:
        problems.add("catchment_axis_mismatch", "Manifest catchment axis differs from expected axis")
    source = m["source"]
    expected_kind = "historical_analysis" if role == "history" else "issue_forecast"
    if source["kind"] != expected_kind:
        problems.add("source_kind_mismatch", "Source role cannot substitute analysis weather for issue-specific forecasts")
    if source["issue_time_utc"] != issue_time_utc:
        problems.add("source_issue_mismatch", "Source issue differs from requested issue or history is issue-labelled")
    units = HISTORY_UNITS if role == "history" else FORECAST_UNITS
    mapping = HISTORY_VARIABLES if role == "history" else FORECAST_VARIABLES
    transformation = HISTORY_TRANSFORMATION if role == "history" else FORECAST_TRANSFORMATION
    if m["units"] != units:
        problems.add("units_mismatch", "Required variables and exact source units do not match the adapter contract")
    if _canonical(m["transformation"]) != _canonical(transformation):
        problems.add("transformation_mismatch", "Treatment must use one accumulation conversion for history and no rate conversion for forecasts")
    raw = _resident_bytes(Path(base_dir) / m["payload"]["path"], MAX_CSV_BYTES)
    payload_hash = hashlib.sha256(raw).hexdigest()
    if payload_hash != m["payload"]["sha256"]:
        problems.add("payload_hash_mismatch", "Observed decoded CSV bytes differ from declared SHA-256")
    if len(raw) != m["payload"]["size_bytes"]:
        problems.add("payload_size_mismatch", "Observed decoded CSV bytes differ from declared length")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ForcingError("Decoded weather CSV must be UTF-8") from exc
    if "\x00" in text:
        raise ForcingError("Decoded weather CSV contains a NUL character")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    observed: set[tuple[str, str]] = set()
    normalized: dict[tuple[str, str], dict] = {}
    rows = 0
    try:
        columns = [*TIME_COLUMNS, *mapping]
        if reader.fieldnames != columns:
            problems.add("columns_mismatch", "CSV header must contain each required column exactly once in the declared order")
        else:
            axis_set = set(axis)
            for row in reader:
                rows += 1
                if rows > MAX_ROWS:
                    raise ForcingError(f"CSV exceeds {MAX_ROWS} rows")
                if None in row or any(value is None for value in row.values()):
                    problems.add("row_shape", "CSV row does not have the required field count", rows)
                    continue
                catchment = row["catchment_id"]
                provider_label = row["provider_time_utc"]
                key = (catchment, provider_label)
                if key in observed:
                    problems.add("duplicate_rows", "Duplicate catchment/provider-hour key", list(key))
                observed.add(key)
                try:
                    provider = _time(provider_label, "provider_time_utc")
                    precip_time = _time(row["precip_source_time_utc"], "precip_source_time_utc")
                    other_time = _time(row["other_source_time_utc"], "other_source_time_utc")
                except CampaignError:
                    problems.add("invalid_clock", "Rows require canonical hourly UTC timestamps", rows)
                    continue
                if catchment not in axis_set or not start <= provider < stop:
                    problems.add("extra_rows", "Row lies outside the expected catchment/hour product", list(key))
                try:
                    end = provider + _HOUR
                except OverflowError:
                    problems.add("invalid_clock", "Provider interval exceeds supported calendar", rows)
                    continue
                if precip_time != end:
                    problems.add("precipitation_clock", "Precipitation source must label the end of this hourly provider interval", rows)
                expected_other = provider if role == "history" else end
                if other_time != expected_other:
                    problems.add("other_fields_clock", "Other-field source labels disagree with the declared treatment", rows)
                if role == "history":
                    if row["issue_time_utc"] != "" or row["lead_hour"] != "":
                        problems.add("history_issue_label", "Historical rows cannot carry a forecast issue or lead", rows)
                else:
                    lead = (provider - start) // _HOUR + 1
                    if row["issue_time_utc"] != issue_time_utc or row["lead_hour"] != str(lead):
                        problems.add("forecast_issue_lead", "Row issue and canonical lead must match provider and valid hours", rows)
                values = {}
                for source_name, output_name in mapping.items():
                    try:
                        literal = row[source_name]
                        decimal = Decimal(literal)
                        if not decimal.is_finite():
                            problems.add("nonfinite_value", "Required weather values cannot be NaN or infinity", {"row": rows, "variable": source_name})
                            continue
                        if not _DECIMAL.fullmatch(literal):
                            raise ValueError("Expected ASCII decimal syntax")
                        number = float(decimal)
                    except (ValueError, InvalidOperation):
                        problems.add("invalid_value", "Required weather values must be finite numbers", {"row": rows, "variable": source_name})
                        continue
                    if not math.isfinite(number):
                        problems.add("nonfinite_value", "Required weather values cannot be NaN or infinity", {"row": rows, "variable": source_name})
                        continue
                    if decimal != 0 and number == 0:
                        problems.add("numeric_underflow", "Nonzero source values cannot become zero in the provider representation", {"row": rows, "variable": source_name})
                    if output_name == "precip_rate":
                        if decimal < 0:
                            problems.add("negative_precipitation", "Accumulation/rate cannot be negative", rows)
                        number /= 3600 if role == "history" else 1
                        if decimal != 0 and number == 0:
                            problems.add("numeric_underflow", "Nonzero precipitation cannot become zero during conversion", rows)
                    values[output_name] = number
                normalized[key] = {"catchment_id": catchment, "provider_time_utc": provider_label,
                                   "values": values}
    except csv.Error as exc:
        raise ForcingError(f"Malformed or excessive-field CSV: {exc}") from exc
    expected_keys = {(catchment, _format_time(start + index * _HOUR))
                     for catchment in axis for index in range(hours)}
    missing = expected_keys - observed
    if missing:
        problems.add("missing_rows", "Required catchment/provider-hour rows are absent", count=len(missing))
        problems.items["missing_rows"]["samples"] = [list(key) for key in sorted(missing)[:5]]
    blockers = problems.list()
    qualification_blockers = [
        {"code": "source_truth_unverified", "message": "Source object identities and issue metadata are declarations; upstream bytes and attributes were not independently authenticated."},
        {"code": "source_version_unqualified", "message": "Declared product, grid and decoder fingerprints do not establish a qualified source version or model-release history."},
        {"code": "source_availability_unknown", "message": "Archive presence and issue labels do not establish weather availability at the historical issue time."},
        {"code": "shortwave_interpretation_unqualified", "message": "The declared radiation timing convention has no independent physical qualification here."},
    ]
    if m["evidence_class"] == "synthetic":
        qualification_blockers.append({"code": "synthetic_evidence_only", "message": "Synthetic values validate software contracts, not real forcing or physical experiments."})
    report = {
        "schema_version": "forcing-validation/0.1", "role": role,
        "evidence_class": m["evidence_class"], "expected_contract": expected,
        "expected_rows": expected_count, "observed_rows": rows,
        "content_valid": not blockers, "execution_ready": False,
        "source_metadata_status": "declared_unverified", "source_truth_verified": False,
        "operational_availability_verified": False, "physical_qualification": False,
        "blockers": blockers, "qualification_blockers": qualification_blockers,
        "manifest_sha256": _digest(m), "payload_sha256": payload_hash,
        "source_metadata_sha256": _digest(source), "transformation_sha256": _digest(m["transformation"]),
        "expected_contract_sha256": _digest(expected),
        "normalized_payload_sha256": _digest([normalized[key] for key in sorted(normalized)]) if not blockers else None,
        "output_units": deepcopy(OUTPUT_UNITS),
        "scope": "Bounded decoded CSV checks only; no acquisition, imputation, runtime launch or execution admission.",
    }
    return {**report, "validation_identity_sha256": _digest(report)}


def validate_history(manifest: dict, base_dir: Path, *, expected_catchment_ids: list[str],
                     start_time_utc: str, stop_time_utc_exclusive: str) -> dict:
    """Check every historical interval [start, stop) against an external axis."""
    return _validate(manifest, base_dir, role="history", expected_catchment_ids=expected_catchment_ids,
                     start_time_utc=start_time_utc, stop_time_utc_exclusive=stop_time_utc_exclusive,
                     issue_time_utc=None)


def validate_forecast_issue(manifest: dict, base_dir: Path, *, expected_catchment_ids: list[str],
                            issue_time_utc: str) -> dict:
    """Require all 18 leads, even when the campaign retains fewer products."""
    issue = _time(issue_time_utc, "issue_time_utc")
    try:
        stop = _format_time(issue + 18 * _HOUR)
    except OverflowError as exc:
        raise ForcingError("Forecast target exceeds the supported calendar") from exc
    return _validate(manifest, base_dir, role="forecast", expected_catchment_ids=expected_catchment_ids,
                     start_time_utc=issue_time_utc, stop_time_utc_exclusive=stop, issue_time_utc=issue_time_utc)


def evaluate_gap_policy(report: dict, policy: str = "fail") -> dict:
    """Permit a recorded forecast exclusion only for missing rows; never history.

    This verifies report consistency, not authenticity. Callers must produce or
    revalidate reports from the current bound bytes before relying on them.
    """
    if policy not in ("fail", "exclude_issue"):
        raise ForcingError("Only fail and exclude_issue are supported; imputation is unavailable")
    if not isinstance(report, dict) or report.get("schema_version") != "forcing-validation/0.1":
        raise ForcingError("Expected a forcing validation report")
    payload = {key: value for key, value in report.items() if key != "validation_identity_sha256"}
    if report.get("validation_identity_sha256") != _digest(payload):
        raise ForcingError("Forcing validation report identity changed")
    codes = {item["code"] for item in report["blockers"]}
    if report["content_valid"]:
        decision = "accept_content"
    elif policy == "exclude_issue" and report["role"] == "forecast" and codes == {"missing_rows"}:
        decision = "exclude_issue"
    else:
        decision = "fail"
    result = {
        "schema_version": "forcing-gap-decision/0.1", "policy": policy, "decision": decision,
        "validation_identity_sha256": report["validation_identity_sha256"],
        "excluded_issue_time_utc": report["expected_contract"]["issue_time_utc"] if decision == "exclude_issue" else None,
        "excluded_generated_rows": report["expected_rows"] if decision == "exclude_issue" else 0,
        "retained_population_requires_recalculation": decision == "exclude_issue",
        "imputation_applied": False, "execution_ready": False,
    }
    return {**result, "gap_decision_sha256": _digest(result)}
