"""Audit CFE drainage mapping against bound bytes; never qualify a model run."""
from __future__ import annotations

from copy import deepcopy
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import Path
import re

from .campaign import _asset_path, _canonical, _integer, _object, _pairs, _nonfinite
from .forcing import _axis, _resident_bytes, _sha, _text

MAX_CONFIG_BYTES = 256 * 1024
MAX_TABLE_BYTES = 4 * 1024 * 1024
MAX_LIBRARY_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
VARIANTS = {"inherited_diagnostic": "mean.slope", "candidate_1km": "mean.slope_1km"}
TARGET_KEYS = {"soil_params.slop", "soil_params.slope"}
_NUMBER = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_VALUE = re.compile(rf"({_NUMBER})\[(1|m/m)\]\Z")


def _number(text):
    if not re.fullmatch(_NUMBER, text):
        raise ValueError("Numeric values must use ASCII decimal syntax without whitespace or separators")
    value = Decimal(text)
    approximate = float(value)
    if not math.isfinite(approximate) or (value != 0 and approximate == 0):
        raise ValueError("Numeric value overflows or underflows a C double")
    return value


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _asset(value, limit, where):
    _object(value, {"path", "sha256", "size_bytes"}, where)
    _asset_path(value["path"], f"{where}.path")
    _sha(value["sha256"], f"{where}.sha256")
    _integer(value["size_bytes"], 1, limit, f"{where}.size_bytes")


def _manifest(value):
    if len(_canonical(value)) > MAX_MANIFEST_BYTES:
        raise ValueError("Configuration manifest exceeds 1 MiB")
    _object(value, {"schema_version", "evidence_class", "variant", "catchment_ids", "attributes",
                    "source", "mapping", "generator", "cfe_library", "configurations"}, "configuration manifest")
    if value["schema_version"] != "cfe-mapping-manifest/0.1":
        raise ValueError("Unsupported CFE mapping manifest schema")
    if value["evidence_class"] not in ("synthetic", "source_declared"):
        raise ValueError("evidence_class must be synthetic or source_declared")
    if not isinstance(value["variant"], str) or value["variant"] not in VARIANTS:
        raise ValueError("Unknown CFE mapping variant")
    _axis(value["catchment_ids"], "catchment_ids")
    _asset(value["attributes"], MAX_TABLE_BYTES, "attributes")
    _asset(value["cfe_library"], MAX_LIBRARY_BYTES, "cfe_library")
    _object(value["source"], {"hydrofabric_sha256", "field_units", "field_meanings"}, "source")
    _sha(value["source"]["hydrofabric_sha256"], "source.hydrofabric_sha256")
    for key in ("field_units", "field_meanings"):
        _object(value["source"][key], {"mean.slope", "mean.slope_1km"}, f"source.{key}")
        for field, item in value["source"][key].items():
            _text(item, f"source.{key}.{field}")
    _object(value["mapping"], {"source_field", "target_parameter", "purpose", "transformation", "target_units"}, "mapping")
    for key, item in value["mapping"].items():
        _text(item, f"mapping.{key}")
    _object(value["generator"], {"revision", "configuration_family"}, "generator")
    revision = value["generator"]["revision"]
    if revision is not None and (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision)):
        raise ValueError("generator.revision must be a full lowercase Git commit or null when unknown")
    _text(value["generator"]["configuration_family"], "generator.configuration_family")
    items = value["configurations"]
    if not isinstance(items, list) or not 1 <= len(items) <= 1024:
        raise ValueError("configurations must contain 1..1024 entries")
    for item in items:
        _object(item, {"catchment_id", "asset"}, "configuration")
        _axis([item["catchment_id"]], "configuration.catchment_id")
        _asset(item["asset"], MAX_CONFIG_BYTES, "configuration.asset")
    paths = [value["attributes"]["path"], value["cfe_library"]["path"], *[i["asset"]["path"] for i in items]]
    if len(paths) != len(set(paths)):
        raise ValueError("Each bound asset must have a distinct path")
    if sum(i["asset"]["size_bytes"] for i in items) > 16 * 1024 * 1024:
        raise ValueError("Configuration files exceed aggregate 16 MiB bound")
    return deepcopy(value)


def load_configuration_manifest(path):
    try:
        value = json.loads(_resident_bytes(Path(path), MAX_MANIFEST_BYTES), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot parse configuration manifest: {exc}") from exc
    return _manifest(value)


def validate_configuration(manifest, base_dir, *, expected_catchment_ids):
    """Check declared mapping and actual source/config/library bytes, without loading code.

    The external catchment axis must come from the separately reviewed domain.
    No scalar conversion, clipping, config rewriting or model loading occurs.
    """
    m = _manifest(manifest)
    axis = _axis(expected_catchment_ids, "expected_catchment_ids")
    blockers, warnings, observed, pairs = [], [], [], []
    field = VARIANTS[m["variant"]]

    def block(code, message):
        blockers.append({"code": code, "message": message})

    def read(asset, limit):
        try:
            raw = _resident_bytes(Path(base_dir) / asset["path"], min(limit, asset["size_bytes"]))
        except (ValueError, OSError) as exc:
            block("asset_unavailable", f"{asset['path']}: {exc}")
            observed.append({"path": asset["path"], "sha256": None, "size_bytes": None})
            return None
        sha = hashlib.sha256(raw).hexdigest()
        observed.append({"path": asset["path"], "sha256": sha, "size_bytes": len(raw)})
        if sha != asset["sha256"] or len(raw) != asset["size_bytes"]:
            block("asset_identity_mismatch", asset["path"])
            return None
        return raw

    if _axis(m["catchment_ids"], "catchment_ids") != axis:
        block("catchment_axis_mismatch", "Manifest axis differs from the expected domain")
    expected_mapping = {"source_field": field, "target_parameter": "soil_params.slop",
                        "purpose": "cfe_bottom_drainage", "transformation": "identity", "target_units": "1"}
    if m["mapping"] != expected_mapping:
        block("mapping_mismatch", "Source field, purpose, target, units and identity transformation must match this variant")
    if m["variant"] == "candidate_1km":
        if m["source"]["field_units"][field] != "1" or m["source"]["field_meanings"][field] != "bottom_drainage_modifier":
            block("source_metadata_mismatch", "Candidate source must declare a dimensionless bottom-drainage modifier")
    else:
        warnings.append({"code": "inherited_mapping_concern", "message": "Inherited mean.slope is diagnostic reproduction only"})

    attributes = {}
    raw = read(m["attributes"], MAX_TABLE_BYTES)
    if raw is not None:
        try:
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True)
            if reader.fieldnames != ["catchment_id", "mean.slope", "mean.slope_1km"]:
                raise ValueError("Attribute CSV must have exactly catchment_id,mean.slope,mean.slope_1km columns")
            for number, row in enumerate(reader, 1):
                if number > 1024:
                    raise ValueError("Attribute table exceeds 1024 rows")
                if None in row or any(v is None or v == "" for v in row.values()):
                    raise ValueError("Attribute row has missing or extra fields")
                cid = row["catchment_id"]
                _axis([cid], "attribute.catchment_id")
                if cid in attributes:
                    raise ValueError("Duplicate attribute catchment")
                vals = {key: _number(row[key]) for key in VARIANTS.values()}
                attributes[cid] = vals
            if sorted(attributes) != axis:
                block("attribute_axis_mismatch", "Attribute catchments differ from the expected domain")
        except (ValueError, InvalidOperation, UnicodeError, csv.Error) as exc:
            block("attribute_table_invalid", str(exc))
            attributes = {}

    cids = [i["catchment_id"] for i in m["configurations"]]
    if sorted(cids) != axis:
        block("configuration_axis_mismatch", "Exactly one configuration per expected catchment is required")
    for item in m["configurations"]:
        raw = read(item["asset"], MAX_CONFIG_BYTES)
        if raw is None:
            continue
        cid = item["catchment_id"]
        try:
            targets = []
            text = raw.decode("ascii").replace("\r\n", "\n")
            if any(ord(c) < 32 and c not in "\n\t" or ord(c) == 127 for c in text):
                raise ValueError("CFE configuration contains unsupported control characters")
            for line in text.split("\n"):
                if not line or line.startswith("#"):
                    continue
                key, separator, value = line.partition("=")
                if key.strip() in TARGET_KEYS:
                    if key != key.strip():
                        raise ValueError("Drainage key whitespace differs from the literal CFE parser")
                    if not separator:
                        raise ValueError("Drainage parameter has no equals sign")
                    targets.append(value)
            if len(targets) != 1:
                raise ValueError("Exactly one soil_params.slop or soil_params.slope assignment is required")
            match = _VALUE.fullmatch(targets[0])
            if not match:
                raise ValueError("Drainage assignment must be a finite number with explicit [1] or [m/m] units")
            actual = _number(match[1])
            if cid in attributes:
                expected = attributes[cid][field]
                if actual != expected:
                    block("drainage_value_mismatch", f"{cid}: generated drainage differs from declared source field")
                pairs.append({"catchment_id": cid, "source_field": field,
                              "source_decimal": str(expected), "configuration_decimal": str(actual)})
            if not 0 <= actual <= 1:
                if m["variant"] == "candidate_1km":
                    block("candidate_out_of_range", f"{cid}: candidate drainage is outside the documented 0..1 range")
                else:
                    warnings.append({"code": "inherited_out_of_range", "message": f"{cid}: inherited drainage outside documented 0..1 range"})
        except (ValueError, InvalidOperation, UnicodeError) as exc:
            block("configuration_invalid", f"{cid}: {exc}")
    read(m["cfe_library"], MAX_LIBRARY_BYTES)
    qualification = [
        "source_attribute_units_and_derivation_unverified", "generator_execution_unattested",
        "loaded_library_and_complete_configuration_unqualified", "coupled_candidate_history_and_response_unqualified",
    ]
    if m["variant"] == "inherited_diagnostic":
        qualification.append("inherited_mean_slope_mapping_known_concern")
    report = {"schema_version": "cfe-mapping-validation/0.1", "evidence_class": m["evidence_class"],
              "variant": m["variant"], "content_valid": not blockers, "execution_ready": False,
              "source_metadata_status": "declared_unverified", "loaded_library_attested": False,
              "generator_status": "unknown" if m["generator"]["revision"] is None else "declared_unverified",
              "complete_configuration_validated": False, "expected_catchment_ids": axis,
              "manifest_sha256": _digest(m), "source_metadata_sha256": _digest(m["source"]),
              "mapping_sha256": _digest(m["mapping"]), "generator_metadata_sha256": _digest(m["generator"]),
              "observed_assets": observed, "parameter_pairs": pairs, "blockers": blockers,
              "warnings": warnings, "qualification_blockers": qualification}
    report["validation_identity_sha256"] = _digest(report)
    return report
