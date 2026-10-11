"""Bind diagnostic input adaptations to pinned component source contracts.

No model is initialized. The sealed preparation and assembly remain untouched.
This qualifies an input contract, not hydrologic skill or release suitability.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_domain as domain
from ngen_reforecast.campaign import _asset_path, _pairs, _nonfinite

CFE_OUTPUTS = ["RAIN_RATE", "GIUH_RUNOFF", "INFILTRATION_EXCESS", "DIRECT_RUNOFF",
               "NASH_LATERAL_RUNOFF", "DEEP_GW_TO_CHANNEL_FLUX", "SOIL_TO_GW_FLUX",
               "Q_OUT", "POTENTIAL_ET", "ACTUAL_ET", "GW_STORAGE", "SOIL_STORAGE",
               "SOIL_STORAGE_CHANGE", "SURF_RUNOFF_SCHEME", "NWM_PONDED_DEPTH"]
ARCHIVES = {
    "ngen-9175b640a4e6f1d90e58e0a65662174d08f052ef.tar.gz": (
        "22fc17bd44ec763b3002360effafcd0b2d194a8b0a9289d30f18b95321407598",
        ["src/realizations/catchment/Bmi_Multi_Formulation.cpp",
         "include/realizations/catchment/Bmi_Formulation.hpp", "src/core/HY_Features.cpp"]),
    "NoahOWP-0abb891b48b043cc626c4e4bbd0efe54ad357fe1.tar.gz": (
        "59f2c8cbba8f0b4b638e21e29c6a2ec2ea01d126ccbe12a71efc4a3d1de4f9d0",
        ["src/DateTimeUtilsModule.f90", "src/RunModule.f90", "src/UtilitiesModule.f90",
         "src/AtmProcessing.f90", "bmi/bmi_noahowp.f90"]),
    "CFE-a349a953ef239ae7470a8365cf614283d7e6ca80.tar.gz": (
        "085a083c534aed42e15338dd97a017e41a2c05cab9f910cbb63d15d6b7665142",
        ["src/bmi_cfe.c", "configs/README.md"]),
    "troute-533fbd98362efdafae62392308727de4f0d4cc20.tar.gz": (
        "b25a31958789a12e779434e99cb5ae9cf90dbb372cee3bcd30f873c63d130584",
        ["src/troute-network/troute/HYFeaturesNetwork.py"]),
}


def contract_sources(runtime_root):
    """Read only bounded resident archive bytes; never execute source code."""
    bindings, contents = [], {}
    for name, (expected, suffixes) in ARCHIVES.items():
        path = Path(runtime_root) / "downloads" / name
        raw = domain.bounded_bytes(path, 64 * 1024 * 1024)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise domain.PreparationError("component source archive hash differs")
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for suffix in suffixes:
                members = [m for m in archive.getmembers() if m.name.endswith("/" + suffix)]
                if len(members) != 1 or not members[0].isfile() or members[0].size > 1024 * 1024:
                    raise domain.PreparationError("component source member differs")
                member = members[0]
                payload = archive.extractfile(member).read()
                bindings.append({"archive": name, "archive_sha256": expected, "member": member.name,
                                 **domain.binding(path, payload)})
                contents[name.split("-")[0] + "/" + suffix] = payload.decode("utf-8")
    return bindings, contents


def read_assembly(root):
    raw = domain.bounded_bytes(Path(root) / "ASSEMBLY.json", 8 * 1024 * 1024)
    report = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    expected = report.pop("assembly_identity_sha256")
    if hashlib.sha256(domain.canonical(report)).hexdigest() != expected:
        raise domain.PreparationError("assembly report identity differs")
    report["assembly_identity_sha256"] = expected
    if report["schema_version"] != "public-native-input-assembly/0.1" or not report["new_fixture"]:
        raise domain.PreparationError("new public input assembly required")
    assets, total = {}, 0
    if not 1 <= len(report["files"]) <= 512:
        raise domain.PreparationError("assembly file bound exceeded")
    for item in report["files"]:
        rel = _asset_path(item["path"], "assembly file")
        if rel in assets or not isinstance(item["bytes"], int) or item["bytes"] < 0:
            raise domain.PreparationError("assembly asset declaration differs")
        total += item["bytes"]
        if total > 32 * 1024 * 1024:
            raise domain.PreparationError("assembly byte bound exceeded")
        payload = domain.bounded_bytes(Path(root) / rel, min(item["bytes"], 2 * 1024 * 1024))
        if domain.binding(Path(root) / rel, payload) != {k: item[k] for k in ("bytes", "sha256")}:
            raise domain.PreparationError("assembly payload differs")
        assets[rel] = payload
    return report, assets


def routing_crosswalk(gpkg, cats, selected_reach):
    """Verify each catchment routes through its own reach, including the cut."""
    domain.bounded_bytes(gpkg, 2 * 1024 * 1024)
    with sqlite3.connect("file:" + str(gpkg) + "?mode=ro&immutable=1", uri=True) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise domain.PreparationError("geometry SQLite integrity differs")
        rows = connection.execute("SELECT id, divide_id, toid FROM flowpaths").fetchall()
        areas = dict(connection.execute("SELECT divide_id, areasqkm FROM divides"))
        parameters = connection.execute('SELECT link, Length_m, n, nCC, BtmWdth, TopWdth, TopWdthCC, ChSlp, So FROM "flowpath-attributes"').fetchall()
    if len(rows) != len(cats) or set(areas) != set(cats) or len(areas) != len(cats):
        raise domain.PreparationError("catchment/reach axis differs")
    mapping = {}
    for reach, cat, downstream in rows:
        if cat not in cats or reach != "wb-" + cat.removeprefix("cat-") or cat in mapping:
            raise domain.PreparationError("catchment does not map uniquely to its own reach")
        if not re.fullmatch(r"nex-\d+", downstream) or not math.isfinite(areas[cat]) or areas[cat] <= 0:
            raise domain.PreparationError("invalid downstream or catchment area")
        mapping[cat] = {"reach_id": reach, "numeric_routing_id": int(reach[3:]),
                        "downstream_nexus_id": downstream, "area_sq_km": areas[cat]}
    if set(mapping) != set(cats) or selected_reach not in {value["reach_id"] for value in mapping.values()}:
        raise domain.PreparationError("selected reach is outside routing domain")
    if any(not re.fullmatch(r"(?:wb-)?\d+", str(row[0])) for row in parameters):
        raise domain.PreparationError("routing parameter key differs")
    parameter_ids = {int(str(row[0]).removeprefix("wb-")) for row in parameters}
    if len(parameters) != len(cats) or parameter_ids != {v["numeric_routing_id"] for v in mapping.values()}:
        raise domain.PreparationError("routing parameter axis differs")
    for row in parameters:
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in row[1:]):
            raise domain.PreparationError("nonpositive or invalid routing channel parameter")
    reaches = {value["reach_id"] for value in mapping.values()}
    terminal = [v for v in mapping.values() if "wb-" + v["downstream_nexus_id"][4:] not in reaches]
    if len(terminal) != 1 or terminal[0]["reach_id"] != selected_reach:
        raise domain.PreparationError("routing cut is not the selected single outlet")
    counts = Counter(row[2] for row in rows)
    return {"catchments": mapping, "shared_confluence_nexuses": {k: v for k, v in sorted(counts.items()) if v > 1},
            "selected_outlet": terminal[0], "lateral_input": "cat-* Q_OUT timestep depth [m]",
            "conversion_to_m3_per_s": "Q_OUT * area_sq_km * 1000000 / 3600",
            "nexus_aggregate_lateral_assignment_admitted": False}


def noah_last_label(raw, original_stop, last_label):
    text = raw.decode("ascii")
    previous = original_stop.strftime("%Y%m%d%H%M")
    target = last_label.strftime("%Y%m%d%H%M")
    text, count = re.subn(r'(\benddate\s*=\s*")' + previous + r'(")',
                         lambda m: m[1] + target + m[2], text)
    if count != 1:
        raise domain.PreparationError("Noah inclusive endpoint assignment differs")
    return text.encode("ascii")


def route_catchment_input(raw):
    text = raw.decode("ascii")
    old = 'qlat_file_pattern_filter: "nex-*"'
    if text.count(old) != 1:
        raise domain.PreparationError("routing nexus input selector differs")
    text = text.replace(old, 'qlat_file_pattern_filter: "cat-*"\n        qlat_file_value_col: "Q_OUT"')
    if text.count('stream_output_type: ".nc"') != 1:
        raise domain.PreparationError("routing output selector differs")
    if text.count("stream_output_internal_frequency: 60") != 1:
        raise domain.PreparationError("routing output frequency differs")
    return text.replace("stream_output_internal_frequency: 60", "stream_output_internal_frequency: 5").encode("ascii")


def qualify(assembly_root, runtime_root, recipe_path, destination):
    report, assets = read_assembly(assembly_root)
    recipe_raw = domain.bounded_bytes(recipe_path, 1024 * 1024)
    recipe = json.loads(recipe_raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    if recipe["fixture_id"] != "watauga-public-rebuild-v1" or report["catchment_ids"] != recipe["domain"]["catchment_ids"]:
        raise domain.PreparationError("externally frozen fixture axis differs")
    source_bindings, _ = contract_sources(runtime_root)
    cats = report["catchment_ids"]
    if len(report["jobs"]) != 3:
        raise domain.PreparationError("expected three bounded diagnostic jobs")
    jobs, crosswalks = [], []
    for job in report["jobs"]:
        name = _asset_path(job["path"], "job")
        stop = domain.hourly_time(job["stop_time_utc_exclusive"])
        last_label = stop - timedelta(hours=1)
        origin = domain.hourly_time(job["origin_time_utc"])
        count = int((stop - origin).total_seconds() / 3600)
        if job["provider_hours_per_catchment"] != count or count not in (785, 786):
            raise domain.PreparationError("diagnostic interval differs")
        gpkg_rel = name + "/config/public-watauga.gpkg"
        if domain.binding(Path(assembly_root) / gpkg_rel, assets[gpkg_rel])["sha256"] != recipe["domain"]["geometry_sha256"]:
            raise domain.PreparationError("frozen public geometry differs")
        crosswalks.append(routing_crosswalk(Path(assembly_root) / gpkg_rel, cats, recipe["gauge"]["routed_flowpath_id"]))
        for cat in cats:
            rel = name + f"/config/cat_config/NOAH-OWP-M/{cat}.input"
            assets[rel] = noah_last_label(assets[rel], stop, last_label)
        realization_rel = name + "/config/realization.json"
        realization = json.loads(assets[realization_rel], object_pairs_hook=_pairs, parse_constant=_nonfinite)
        if realization["time"] != {"start_time": origin.strftime("%Y-%m-%d %H:%M:%S"),
                                  "end_time": last_label.strftime("%Y-%m-%d %H:%M:%S"), "output_interval": 3600}:
            raise domain.PreparationError("native inclusive clock differs")
        multi = realization["global"]["formulations"][0]["params"]
        multi.update(output_variables=CFE_OUTPUTS, output_header_fields=CFE_OUTPUTS, output_precision=17)
        realization.pop("routing", None)  # External t-route is a separately recorded model process.
        assets[realization_rel] = (json.dumps(realization, indent=2) + "\n").encode()
        route_rel = name + "/config/troute.yaml"
        assets[route_rel] = route_catchment_input(assets[route_rel])
        jobs.append({**job, "noah_inclusive_enddate": last_label.strftime("%Y%m%d%H%M"),
                     "noah_advertised_timestep_count": count, "routing_process": "external_pinned_t_route",
                     "routing_output_interval_seconds": 300, "catchment_output_variables": CFE_OUTPUTS,
                     "catchment_output_precision": 17, "cfe_parameter_bytes_preserved": True})
    if any(value != crosswalks[0] for value in crosswalks):
        raise domain.PreparationError("job routing crosswalks differ")
    destination = domain.fresh_directory(destination, [Path(assembly_root), Path(runtime_root)])
    for rel, payload in assets.items():
        path = destination / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(payload)
    for job in jobs:
        for rel in ("outputs/ngen", "outputs/troute"):
            (destination / job["path"] / rel).mkdir(parents=True)
    original_after, _ = read_assembly(assembly_root)
    after_bindings, _ = contract_sources(runtime_root)
    if original_after != report or after_bindings != source_bindings:
        raise domain.PreparationError("sealed inputs or source contracts changed")
    result = {"schema_version": "public-diagnostic-input-admission/0.1", "fixture_id": recipe["fixture_id"],
              "prior_assembly_identity_sha256": report["assembly_identity_sha256"],
              "recipe": domain.binding(recipe_path, recipe_raw), "source_contracts": source_bindings,
              "adapter": domain.binding(Path(__file__)), "catchment_ids": cats, "jobs": jobs,
              "routing_crosswalk": crosswalks[0],
              "files": [{"path": rel, **domain.binding(destination / rel, payload)} for rel, payload in sorted(assets.items())],
              "input_contract_admitted": True, "native_model_invocations": 0, "runtime_admitted": False,
              "physical_reference_validated": False, "release_scientifically_qualified": False,
              "interpretation_limits": ["Candidate drainage and Noah terrain source derivation remain unqualified",
                  "Declared cold initial states and 31-day history do not establish convergence",
                  "Point radiation sampling held across each hour is a declared diagnostic convention",
                  "Selected full reach is a surrogate for the interior gauge, not an exact gauge segment",
                  "Current archive generations do not establish historical causal availability",
                  "Input admission does not establish shared-history branching or model execution"]}
    result["admission_identity_sha256"] = hashlib.sha256(domain.canonical(result)).hexdigest()
    (destination / "ADMISSION.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assembly_root", "runtime_root", "recipe_path", "destination"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = qualify(args.assembly_root, args.runtime_root, args.recipe_path, args.destination)
    print(json.dumps({"admission_identity_sha256": result["admission_identity_sha256"],
                      "input_contract_admitted": True, "native_model_invocations": 0}))


if __name__ == "__main__":
    main()
