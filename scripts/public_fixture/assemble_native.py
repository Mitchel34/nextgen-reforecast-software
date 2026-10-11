"""Assemble new serial CSV jobs from sealed public development inputs.

This writes an inspectable input layout. It does not initialize native models,
qualify shared-history execution, or restore the historical benchmark.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import math
from pathlib import Path
import re
import sys
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_domain as domain
from ngen_reforecast.campaign import _asset_path, _pairs, _nonfinite

HOUR = timedelta(hours=1)
FIELDS = ["time", "precip_rate", "TMP_2maboveground", "SPFH_2maboveground",
          "UGRD_10maboveground", "VGRD_10maboveground", "PRES_surface",
          "DSWRF_surface", "DLWRF_surface"]
DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", re.ASCII)
REVISION = "9175b640a4e6f1d90e58e0a65662174d08f052ef"


def sealed_report(path, maximum=8 * 1024 * 1024):
    report = json.loads(domain.bounded_bytes(path, maximum), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    expected = report.pop("preparation_identity_sha256")
    if hashlib.sha256(domain.canonical(report)).hexdigest() != expected:
        raise domain.PreparationError("preparation report identity mismatch")
    report["preparation_identity_sha256"] = expected
    return report


def native_rows(raw, start, stop):
    reader = csv.reader(io.StringIO(raw.decode("ascii")))
    if next(reader, None) != FIELDS:
        raise domain.PreparationError("native provider header differs")
    expected = start
    rows = []
    for row in reader:
        if len(row) != len(FIELDS) or expected >= stop:
            raise domain.PreparationError("unexpected provider row count/width")
        if row[0] != expected.strftime("%Y-%m-%d %H:%M:%S"):
            raise domain.PreparationError("native provider clock differs")
        if any(not DECIMAL.fullmatch(value) or not math.isfinite(float(value)) for value in row[1:]):
            raise domain.PreparationError("native weather contains nonfinite/malformed values")
        rows.append(row)
        expected += HOUR
    if expected != stop:
        raise domain.PreparationError("native provider coverage incomplete")
    return rows


def native_end_time(origin, stop):
    """Pinned Simulation_Time counts inclusive provider labels, adding one."""
    hours = int((stop - origin) / HOUR)
    if not 1 <= hours <= 100000:
        raise domain.PreparationError("native job interval bound exceeded")
    return (stop - HOUR).strftime("%Y-%m-%d %H:%M:%S"), hours


def rewrite_noah_end(raw, expected_stop, job_stop):
    text = raw.decode("ascii")
    pattern = re.compile(r'(\benddate\s*=\s*")' + expected_stop.strftime("%Y%m%d%H%M") + r'(")')
    text, count = pattern.subn(lambda m: m[1] + job_stop.strftime("%Y%m%d%H%M") + m[2], text)
    if count != 1:
        raise domain.PreparationError("Noah end date assignment mismatch")
    return text.encode("ascii")


def write_csv(path, rows):
    with path.open("x", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows(rows)


def assemble(domain_root, weather_root, template_root, destination, source_receipt):
    domain_root, weather_root, template_root = map(Path, (domain_root, weather_root, template_root))
    dr = sealed_report(domain_root / "DOMAIN_PREPARATION.json")
    wr = sealed_report(weather_root / "PREPARATION.json")
    if dr["schema_version"] != domain.ADAPTER_VERSION or wr["schema_version"] != "public-forcing-preparation/0.1":
        raise domain.PreparationError("unsupported preparation schema")
    if dr["historical_fixture_restored"] or wr["historical_benchmark_restored"] or not wr["content_complete"]:
        raise domain.PreparationError("new complete development weather required")
    if dr["catchment_ids"] != wr["catchment_ids"] or dr["geometry"]["sha256"] != wr["domain_sha256"]:
        raise domain.PreparationError("weather/domain identity differs")
    origin = domain.hourly_time(dr["start_time_utc"])
    stop = domain.hourly_time(dr["stop_time_utc_exclusive"])
    if wr["origin_time_utc"] != dr["start_time_utc"] or wr["stop_time_utc_exclusive"] != dr["stop_time_utc_exclusive"]:
        raise domain.PreparationError("weather/domain interval differs")
    issues = [domain.hourly_time(value) for value in wr["issue_times_utc"]]
    if not 1 <= len(issues) <= 8 or sorted(set(issues)) != issues or min(issues) < origin or max(issues) + 18 * HOUR > stop:
        raise domain.PreparationError("invalid bounded issue schedule")
    cats = dr["catchment_ids"]
    if not 1 <= len(cats) <= 1024 or any(not re.fullmatch(r"cat-\d+", cat) for cat in cats):
        raise domain.PreparationError("invalid catchment axis")
    templates, template_bindings = domain.read_templates(template_root)
    native_source = json.loads(domain.bounded_bytes(source_receipt, 1048576))
    if native_source["commit"] != REVISION:
        raise domain.PreparationError("native source revision differs")
    required_sources = {"include/forcing/CsvPerFeatureForcingProvider.hpp",
                        "include/forcing/AorcForcing.hpp",
                        "include/realizations/catchment/Formulation_Constructors.hpp",
                        "include/realizations/catchment/Formulation_Manager.hpp",
                        "include/simulation_time/Simulation_Time.hpp", "src/NGen.cpp"}
    declared_sources = {row["path"]: row for row in native_source["files"]}
    source_bindings = {}
    for rel in sorted(required_sources):
        raw = domain.bounded_bytes(Path(source_receipt).parent / rel, 1048576)
        identity = domain.binding(Path(source_receipt).parent / rel, raw)
        if identity != {key: declared_sources[rel][key] for key in ("bytes", "sha256")}:
            raise domain.PreparationError("native contract source bytes differ")
        source_bindings[rel] = identity
    raw_assets = {}
    total = 0
    for row in dr["files"]:
        rel = _asset_path(row["path"], "domain asset")
        if rel in raw_assets:
            raise domain.PreparationError("duplicate domain asset path")
        total += row["bytes"]
        if total > 16 * 1024 * 1024:
            raise domain.PreparationError("domain source byte bound exceeded")
        raw = domain.bounded_bytes(domain_root / rel, min(row["bytes"], 1048576))
        if domain.binding(domain_root / rel, raw) != {key: row[key] for key in ("bytes", "sha256")}:
            raise domain.PreparationError("domain asset bytes differ")
        raw_assets[rel] = raw
    weather_assets = {row["path"]: row for row in wr["payloads"]}
    if len(weather_assets) != len(wr["payloads"]):
        raise domain.PreparationError("duplicate weather asset path")
    history, forecast = {}, {}
    consumed_weather = []
    for cat in cats:
        for token, begin, end, target in [("history", origin, stop, history)] + [
            ("forecast/" + issue.strftime("%Y%m%dT%H00Z"), issue, issue + 18 * HOUR, forecast) for issue in issues]:
            rel = f"provider/{token}/{cat}.csv"
            row = weather_assets[rel]
            identity = {"bytes": row["size_bytes"], "sha256": row["sha256"]}
            total += identity["bytes"]
            if total > 16 * 1024 * 1024:
                raise domain.PreparationError("input byte bound exceeded")
            raw = domain.bounded_bytes(weather_root / rel, min(identity["bytes"], 1048576))
            if domain.binding(weather_root / rel, raw) != identity:
                raise domain.PreparationError("weather asset bytes differ")
            target[(token, cat)] = native_rows(raw, begin, end)
            consumed_weather.append({"path": rel, **domain.binding(weather_root / rel, raw)})
    destination = domain.fresh_directory(destination, [domain_root, weather_root, template_root])
    jobs = []
    definitions = [("history", stop, None)] + [
        ("serial-" + issue.strftime("%Y%m%dT%H00Z"), issue + 18 * HOUR, issue) for issue in issues]
    for name, job_stop, issue in definitions:
        folder = destination / name
        (folder / "config/cat_config/CFE").mkdir(parents=True)
        (folder / "config/cat_config/NOAH-OWP-M").mkdir(parents=True)
        (folder / "forcings").mkdir()
        ngen_end, count = native_end_time(origin, job_stop)
        (folder / "config/public-watauga.gpkg").write_bytes(raw_assets[dr["geometry"]["path"]])
        for cat in cats:
            (folder / f"config/cat_config/CFE/{cat}.ini").write_bytes(raw_assets[f"config/cat_config/CFE/{cat}.ini"])
            noah = rewrite_noah_end(raw_assets[f"config/cat_config/NOAH-OWP-M/{cat}.input"], stop, job_stop)
            (folder / f"config/cat_config/NOAH-OWP-M/{cat}.input").write_bytes(noah)
            values = history[("history", cat)]
            if issue is not None:
                n_history = int((issue - origin) / HOUR)
                values = values[:n_history] + forecast[("forecast/" + issue.strftime("%Y%m%dT%H00Z"), cat)]
            if len(values) != count:
                raise domain.PreparationError("assembled serial row count differs")
            write_csv(folder / f"forcings/{cat}.csv", values)
        realization = json.loads(raw_assets["config/realization.json"])
        realization["global"]["forcing"] = {"path": "./forcings/", "file_pattern": "{{id}}\\.csv",
                                             "provider": "CsvPerFeature", "enable_cache": False}
        realization["time"].update(start_time=origin.strftime("%Y-%m-%d %H:%M:%S"),
                                   end_time=ngen_end, output_interval=3600)
        (folder / "config/realization.json").write_text(json.dumps(realization, indent=2) + "\n")
        (folder / "config/troute.yaml").write_text(templates["routing"].format(
            geo_file_path="./config/public-watauga.gpkg", cpu_pool=2, time_step_size=300,
            start_datetime=origin.strftime("%Y-%m-%d %H:%M:%S"), nts=count * 12,
            max_loop_size=count * 12, binary_nexus_file_folder_comment="#"))
        (folder / "NGIAB_TEMPLATE_LICENSE.txt").write_bytes(raw_assets["NGIAB_TEMPLATE_LICENSE.txt"])
        for rel in ("outputs/ngen", "outputs/troute"):
            (folder / rel).mkdir(parents=True)
        jobs.append({"path": name, "kind": "history_only" if issue is None else "independent_serial_replay",
                     "issue_time_utc": None if issue is None else issue.strftime("%Y-%m-%dT%H:00:00Z"),
                     "origin_time_utc": dr["start_time_utc"], "stop_time_utc_exclusive": job_stop.strftime("%Y-%m-%dT%H:00:00Z"),
                     "ngen_inclusive_last_provider_time": ngen_end, "provider_hours_per_catchment": count,
                     "history_hours": count if issue is None else int((issue - origin) / HOUR),
                     "forecast_hours": 0 if issue is None else 18,
                     "routing_five_minute_steps": count * 12, "selected_gauge_output": dr["reach"]})
    files = [{"path": str(path.relative_to(destination)), **domain.binding(path)}
             for path in sorted(destination.rglob("*")) if path.is_file()]
    report = {"schema_version": "public-native-input-assembly/0.1", "new_fixture": True,
              "domain_preparation_identity_sha256": dr["preparation_identity_sha256"],
              "weather_preparation_identity_sha256": wr["preparation_identity_sha256"],
              "native_source_revision": REVISION, "native_source_bindings": source_bindings,
              "template_bindings": template_bindings, "assembler": domain.binding(Path(__file__)),
              "catchment_ids": cats, "jobs": jobs, "files": files,
              "consumed_weather_assets": consumed_weather,
              "native_time_semantics": "NGen end_time is inclusive last provider label; physical stop and Noah enddate are separate exclusive interval endpoints",
              "input_layout_assembled": True, "shared_history_execution_qualified": False,
              "historical_fixture_restored": False, "execution_ready": False,
              "qualification_blockers": ["No native execution or loaded-library attestation",
                  "Noah static parameter tables and component/library paths require qualification",
                  "Noah endpoint behavior and routing terminal cut require physical validation",
                  "Hydrofabric attributes, meteorological sampling and physical references require scientific qualification",
                  "Serial input assembly does not establish shared-history branching or complete land-state recovery"]}
    report["assembly_identity_sha256"] = hashlib.sha256(domain.canonical(report)).hexdigest()
    (destination / "ASSEMBLY.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("domain_root", "weather_root", "template_root", "destination", "source_receipt"):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    report = assemble(args.domain_root, args.weather_root, args.template_root, args.destination, args.source_receipt)
    print(json.dumps({"jobs": len(report["jobs"]), "assembly_identity_sha256": report["assembly_identity_sha256"],
                      "input_layout_assembled": True, "execution_ready": False}))


if __name__ == "__main__":
    main()
