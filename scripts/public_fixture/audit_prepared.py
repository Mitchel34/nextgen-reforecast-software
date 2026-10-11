"""Audit a prepared public fixture offline; never invoke a native model.

Acquisition and domain receipts remain separate source evidence. This command
checks retained response/payload bytes, builds truthful sparse-source manifests,
and compares decoded weather with every generated provider CSV.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ngen_reforecast.campaign import _asset_path, _canonical, _nonfinite, _pairs
from ngen_reforecast.forcing import (
    _resident_bytes, FORECAST_TRANSFORMATION, FORECAST_UNITS, FORECAST_VARIABLES,
    HISTORY_TRANSFORMATION, HISTORY_UNITS, HISTORY_VARIABLES, MAX_SEGMENT_BYTES,
    OUTPUT_UNITS, validate_forecast_issue, validate_history,
)


def digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def load(path):
    return json.loads(_resident_bytes(path, 16 * 1024**2),
                      object_pairs_hook=_pairs, parse_constant=_nonfinite)


def sealed_receipt(path):
    value = load(path)
    declared = value["preparation_identity_sha256"]
    if digest({k: v for k, v in value.items() if k != "preparation_identity_sha256"}) != declared:
        raise ValueError("Preparation receipt identity mismatch")
    return value


def safe_staging(path):
    path = Path(os.path.abspath(path))
    if ROOT / ".local" not in path.parents:
        raise ValueError("Only project-local ignored staging is admitted")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("Staging symlink refused")
        try:
            flags = getattr(part.lstat(), "st_flags", 0)
        except FileNotFoundError:
            continue
        if flags & getattr(stat, "UF_DATALESS", 0):
            raise ValueError("Nonresident staging path refused")
    return path


def payload_bytes(base, binding, maximum):
    _asset_path(binding["path"], "payload.path")
    raw = _resident_bytes(base / binding["path"], maximum)
    if len(raw) != binding["size_bytes"] or hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        raise ValueError("Prepared payload identity mismatch")
    return raw


def merge_segments(records):
    """Merge fetched ranges only after checking identical overlapping bytes."""
    merged = []
    for start, raw in sorted(records, key=lambda item: item[0]):
        if merged and start <= merged[-1][0] + len(merged[-1][1]):
            prior_start, prior = merged[-1]
            overlap = min(len(raw), prior_start + len(prior) - start)
            if prior[start - prior_start:start - prior_start + overlap] != raw[:overlap]:
                raise ValueError("Overlapping source ranges disagree")
            merged[-1] = (prior_start, prior + raw[overlap:])
        else:
            merged.append((start, raw))
    return [{"start_byte": start + offset, "size_bytes": len(raw[offset:offset + MAX_SEGMENT_BYTES]),
             "sha256": hashlib.sha256(raw[offset:offset + MAX_SEGMENT_BYTES]).hexdigest()}
            for start, raw in merged for offset in range(0, len(raw), MAX_SEGMENT_BYTES)]


def source_objects(weather, root):
    full, ranges = {}, {}
    if not 1 <= len(weather["source_responses"]) <= 2000:
        raise ValueError("Source response count exceeds preparation bound")
    if sum(r["response_size_bytes"] for r in weather["source_responses"]) > 768 * 1024**2:
        raise ValueError("Retained source bytes exceed preparation bound")
    for record in weather["source_responses"]:
        name = record["relative_cache_path"]
        _asset_path(name, "cache path")
        raw = _resident_bytes(root / "raw" / name, MAX_SEGMENT_BYTES)
        if len(raw) != record["response_size_bytes"] or hashlib.sha256(raw).hexdigest() != record["response_sha256"]:
            raise ValueError("Retained source response identity mismatch")
        url = record["url"]
        if record["byte_range_inclusive"] is None:
            if record["whole_object_sha256"] != record["response_sha256"]:
                raise ValueError("Whole-response SHA mismatch")
            if url.startswith("https://noaa-nws-aorc-v1-1-1km.s3.amazonaws.com/"):
                identity = {"object_key": url, "generation": record["etag"], "size_bytes": len(raw),
                            "sha256": record["response_sha256"], "segments": []}
                if url in full and full[url] != identity:
                    raise ValueError("AORC object changed within preparation")
                full[url] = identity
        else:
            if record["whole_object_sha256"] is not None:
                raise ValueError("Sparse response cannot declare a whole-object hash")
            start, stop = record["byte_range_inclusive"]
            if stop - start + 1 != len(raw):
                raise ValueError("Retained range length mismatch")
            key = (urlsplit(url).path.removeprefix("/national-water-model/"), record["generation"])
            ranges.setdefault(key, []).append((start, raw))
    forecast = {}
    for item in weather["source_objects"]:
        key = (item["name"], item["generation"])
        if key not in ranges:
            raise ValueError("No retained regional ranges for forecast object")
        forecast[item["name"]] = {"object_key": item["name"], "generation": item["generation"],
                                  "size_bytes": int(item["size"]), "sha256": None,
                                  "segments": merge_segments(ranges.pop(key))}
    if ranges:
        raise ValueError("Unbound forecast range object")
    return list(full.values()), forecast


def provider_matches(weather, base, decoded, role, issue=None):
    mapping = HISTORY_VARIABLES if role == "history" else FORECAST_VARIABLES
    normalized = []
    expected = {}
    for row in csv.DictReader(decoded.decode().splitlines()):
        values = {out: float(row[source]) / (3600 if source == "APCP" else 1)
                  for source, out in mapping.items()}
        key = (row["catchment_id"], row["provider_time_utc"])
        if key in expected:
            raise ValueError("Duplicate decoded provider key")
        expected[key] = values
    token = datetime.strptime(issue, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y%m%dT%H00Z") if issue else None
    prefix = f"provider/forecast/{token}/" if token else "provider/history/"
    for binding in weather["payloads"]:
        if not binding["path"].startswith(prefix):
            continue
        cat = Path(binding["path"]).stem
        reader = csv.DictReader(payload_bytes(base, binding, 32 * 1024**2).decode().splitlines())
        if reader.fieldnames != ["time", *OUTPUT_UNITS]:
            raise ValueError("Native provider CSV columns differ")
        for row in reader:
            if set(row) != {"time", *OUTPUT_UNITS} or any(value is None for value in row.values()):
                raise ValueError("Native provider row width differs")
            hour = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ")
            values = {name: float(row[name]) for name in OUTPUT_UNITS}
            key = (cat, hour)
            if key not in expected or values != expected.pop(key):
                raise ValueError("Provider weather differs from decoded transformation")
            normalized.append({"catchment_id": cat, "provider_time_utc": hour, "values": values})
    if expected:
        raise ValueError("Missing native provider rows")
    return digest(sorted(normalized, key=lambda row: (row["catchment_id"], row["provider_time_utc"])))


def expected_contract(recipe, domain, weather):
    """Use the separately frozen recipe, never the payload's own population."""
    if recipe["schema_version"] != "public-fixture-recipe/0.1" or recipe["fixture_id"] != "watauga-public-rebuild-v1":
        raise ValueError("Unsupported public fixture recipe")
    declared = recipe["domain"]
    for key, actual in (("preparation_identity_sha256", domain["preparation_identity_sha256"]),
                        ("catchment_ids", domain["catchment_ids"]),
                        ("geometry_sha256", domain["geometry"]["sha256"])):
        if declared[key] != actual:
            raise ValueError("Domain differs from frozen recipe")
    axis = recipe["weather"]["issue_times_utc"]
    if len(axis) != 2 or sorted(set(axis)) != axis or weather["issue_times_utc"] != axis:
        raise ValueError("Forecast issue population differs from frozen recipe")
    for key in ("origin_time_utc", "stop_time_utc_exclusive", "preparation_identity_sha256"):
        if weather[key] != recipe["weather"][key]:
            raise ValueError("Weather differs from frozen recipe")
    if domain["start_time_utc"] != recipe["weather"]["origin_time_utc"] or domain["stop_time_utc_exclusive"] != recipe["weather"]["stop_time_utc_exclusive"]:
        raise ValueError("Domain clocks differ from frozen recipe")
    if weather["source_objects"] != recipe["weather"]["forecast_objects"] or len(weather["source_objects"]) != 36:
        raise ValueError("Forecast object population differs from frozen recipe")
    expected_keys = {f"nwm.{issue[:10].replace('-', '')}/forcing_short_range/nwm.t{issue[11:13]}z.short_range.forcing.f{lead:03}.conus.nc"
                     for issue in axis for lead in range(1, 19)}
    if {item["name"] for item in weather["source_objects"]} != expected_keys:
        raise ValueError("Forecast source keys do not cover the frozen issue/lead axis")
    return axis


def audit(domain_path, weather_path, output, recipe_path=ROOT / "fixtures/watauga-public-v1/recipe.json"):
    domain_path, weather_path, output = map(safe_staging, (domain_path, weather_path, output))
    domain, weather = sealed_receipt(domain_path), sealed_receipt(weather_path)
    recipe = load(recipe_path)
    issues = expected_contract(recipe, domain, weather)
    cats = domain["catchment_ids"]
    if cats != weather["catchment_ids"] or domain["geometry"]["sha256"] != weather["domain_sha256"]:
        raise ValueError("Domain/weather axis or geometry mismatch")
    history_sources, forecast_sources = source_objects(weather, weather_path.parent)
    reports, manifests, decoded_payloads = [], [], []
    for issue in [None, *issues]:
        role = "forecast" if issue else "history"
        start = issue or domain["start_time_utc"]
        stop = (datetime.strptime(issue, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=18)).strftime("%Y-%m-%dT%H:%M:%SZ") if issue else domain["stop_time_utc_exclusive"]
        token = datetime.strptime(issue, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y%m%dT%H00Z") if issue else None
        name = f"decoded/forecast-{token}.csv" if issue else "decoded/history.csv"
        bindings = [v for v in weather["payloads"] if v["path"] == name]
        if len(bindings) != 1:
            raise ValueError("Decoded payload binding is missing or ambiguous")
        binding = bindings[0]
        raw = payload_bytes(weather_path.parent, binding, 32 * 1024**2)
        prefix = f"nwm.{issue[:10].replace('-', '')}/forcing_short_range/nwm.t{issue[11:13]}z." if issue else None
        manifest = {"schema_version": "forcing-manifest/0.2", "evidence_class": "source_declared",
                    "role": role, "payload": binding, "catchment_ids": cats,
                    "start_time_utc": start, "stop_time_utc_exclusive": stop,
                    "units": FORECAST_UNITS if issue else HISTORY_UNITS,
                    "transformation": FORECAST_TRANSFORMATION if issue else HISTORY_TRANSFORMATION,
                    "source": {"kind": "issue_forecast" if issue else "historical_analysis",
                               "product": "NWM-v2.1-short-range" if issue else "AORC-v1.1-current-archive",
                               "issue_time_utc": issue, "decoder_sha256": weather["recipe_sha256"],
                               "grid_sha256": digest(weather["forecast_grid" if issue else "history_grid"]),
                               "objects": [v for k, v in forecast_sources.items() if k.startswith(prefix)] if issue else history_sources}}
        if issue:
            report = validate_forecast_issue(manifest, weather_path.parent, expected_catchment_ids=cats, issue_time_utc=issue)
        else:
            report = validate_history(manifest, weather_path.parent, expected_catchment_ids=cats,
                                      start_time_utc=domain["start_time_utc"], stop_time_utc_exclusive=domain["stop_time_utc_exclusive"])
        if not report["content_valid"] or provider_matches(weather, weather_path.parent, raw, role, issue) != report["normalized_payload_sha256"]:
            raise ValueError("Decoded/native-provider content admission failed")
        reports.append(report)
        manifests.append(manifest)
        decoded_payloads.append((binding["path"], raw))
    output.mkdir(exist_ok=False)
    (output / "decoded").mkdir()
    for name, raw in decoded_payloads:
        (output / name).write_bytes(raw)
    for manifest, report in zip(manifests, reports):
        token = manifest["source"]["issue_time_utc"] or "history"
        token = token.replace(":", "").replace("-", "")
        (output / f"{token}.manifest.json").write_bytes(_canonical(manifest) + b"\n")
        (output / f"{token}.validation.json").write_bytes(_canonical(report) + b"\n")
    result = {"schema_version": "public-fixture-content-audit/0.1", "fixture_id": "watauga-public-rebuild-v1",
              "expected_recipe_sha256": digest(recipe),
              "domain_preparation_identity_sha256": domain["preparation_identity_sha256"],
              "weather_preparation_identity_sha256": weather["preparation_identity_sha256"],
              "audit_adapter_sha256": hashlib.sha256(_resident_bytes(Path(__file__), 1048576)).hexdigest(),
              "content_valid": True, "provider_matches_decoded": True,
              "retained_source_response_hashes_checked": len(weather["source_responses"]),
              "history_rows": reports[0]["expected_rows"], "forecast_rows": sum(r["expected_rows"] for r in reports[1:]),
              "forcing_validation_identities": [r["validation_identity_sha256"] for r in reports],
              "execution_ready": False, "physical_qualification": False, "model_invocations": 0,
              "qualification_blockers": weather["qualification_blockers"] + domain["qualification_blockers"]}
    result["audit_identity_sha256"] = digest(result)
    (output / "AUDIT.json").write_bytes(_canonical(result) + b"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True, type=Path)
    parser.add_argument("--weather", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.domain, args.weather, args.output), indent=2))
