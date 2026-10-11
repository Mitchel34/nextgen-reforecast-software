"""Prepare a separately identified public domain; never run a model or fetch data.

The operator acquires and binds public bytes first. Pinned NGIAB templates are
external inputs, with their MIT notice retained in the private generated bundle.
This adapter is independently authored and does not import upstream generators.
"""
from __future__ import annotations

import argparse
import csv
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ngen_reforecast.campaign import _open_resident, _read_bounded

ADAPTER_VERSION = "public-domain-preparation/0.1"
SOURCE_SHA = "983300473d8edf8f27d8c3214077c5fa8e58fc301241ee3cd949d9defb4e3217"
SOURCE_BYTES = 74813440
UPSTREAM_REVISION = "2b41ba2f038445ddbfe01d8cbe266e2aa9b5e635"
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_NETWORK_ROWS = 100000
MAX_CATCHMENTS = 1024
TABLE_KEYS = {
    "divides": "divide_id", "divide-attributes": "divide_id",
    "flowpaths": "id", "flowpath-attributes": "id",
    "flowpath-attributes-ml": "id", "network": "id", "nexus": "id",
    "hydrolocations": "id", "pois": "id",
}
TEMPLATES = {
    "cfe": "modules/data_sources/config/catchment/cfe.ini",
    "noah": "modules/data_sources/config/catchment/noah-owp-modular-init.namelist.input",
    "routing": "modules/data_sources/ngen-routing-template.yaml",
    "realization": "modules/data_sources/config/realization/cfe-nom.json",
    "license": "LICENSE",
}


class PreparationError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def bounded_bytes(path, maximum):
    fd, before = _open_resident(Path(path), maximum)
    try:
        raw = _read_bounded(fd, before.st_size)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise PreparationError("source changed during read")
        return raw
    finally:
        os.close(fd)


def binding(path, raw=None):
    raw = bounded_bytes(path, MAX_SOURCE_BYTES) if raw is None else raw
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def hourly_time(value):
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:00:00Z", value):
        raise PreparationError("canonical hourly UTC time required")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def upstream_closure(rows, reach):
    """Traverse through nexuses to a reach itself, excluding adjacent outlets.

    Public network rows repeat reach IDs for contributing NHD features. A NULL
    id is not a graph vertex and must not connect otherwise unrelated rivers.
    """
    if not re.fullmatch(r"wb-\d+", reach):
        raise PreparationError("explicit wb-<number> reach required")
    if len(rows) > MAX_NETWORK_ROWS:
        raise PreparationError("network row bound exceeded")
    reverse, cats_by_node, outgoing = {}, {}, {}
    for node, downstream, cat in rows:
        if node is None:
            continue
        if not isinstance(node, str) or not isinstance(downstream, str):
            raise PreparationError("invalid network node")
        if cat is not None and not re.fullmatch(r"cat-\d+", cat):
            raise PreparationError("invalid catchment id")
        outgoing.setdefault(node, set()).add(downstream)
        reverse.setdefault(downstream, set()).add(node)
        cats_by_node.setdefault(node, set()).add(cat)
    if reach not in outgoing:
        raise PreparationError("reach is absent")
    if any(len(ends) != 1 for ends in outgoing.values()):
        raise PreparationError("ambiguous downstream network")
    pending, seen = [reach], set()
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        pending.extend(reverse.get(node, set()))
    # Detect cycles explicitly within the selected component.
    for seed in seen:
        chain, node = set(), seed
        while node in seen and node in outgoing:
            if node in chain:
                raise PreparationError("cyclic selected network")
            chain.add(node)
            node = next(iter(outgoing[node]))
    catchments = sorted({cat for node in seen for cat in cats_by_node.get(node, ()) if cat})
    if not 1 <= len(catchments) <= MAX_CATCHMENTS:
        raise PreparationError("catchment bound exceeded")
    outlet = next(iter(outgoing[reach]))
    return {"reach": reach, "outlet_nexus": outlet, "nodes": sorted(seen | {outlet}),
            "catchment_ids": catchments}


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def fresh_directory(destination, sources):
    destination = Path(os.path.abspath(destination))
    if destination == ROOT / ".local" or ROOT / ".local" not in destination.parents:
        raise PreparationError("development preparation destination must be under repository .local")
    for parent in (destination.parent, *destination.parents):
        if parent.is_symlink():
            raise PreparationError("destination symlink refused")
    for source in sources:
        source = Path(os.path.abspath(source))
        if destination == source or source in destination.parents:
            raise PreparationError("destination is inside a source")
    destination.mkdir(parents=False, exist_ok=False)
    return destination


def read_templates(source_root):
    receipt = json.loads(bounded_bytes(source_root / "SOURCE_RECEIPT.json", 1048576))
    if receipt.get("commit") != UPSTREAM_REVISION:
        raise PreparationError("unexpected upstream revision")
    declared = {row["path"]: row for row in receipt["files"]}
    result, observed = {}, {}
    for name, rel in TEMPLATES.items():
        raw = bounded_bytes(source_root / rel, 1048576)
        identity = binding(source_root / rel, raw)
        if identity != {key: declared[rel][key] for key in ("bytes", "sha256")}:
            raise PreparationError("template bytes differ from acquisition receipt")
        result[name] = raw.decode("utf-8")
        observed[rel] = identity
    if "MIT License" not in result["license"] or "Alabama  Water Institute" not in result["license"]:
        raise PreparationError("expected template notice absent")
    return result, observed


def envelope(blob):
    if len(blob) < 40 or blob[:2] != b"GP" or (blob[3] >> 1) & 7 != 1:
        raise PreparationError("XY GeoPackage envelope required")
    values = struct.unpack(("<" if blob[3] & 1 else ">") + "dddd", blob[8:40])
    if not all(math.isfinite(x) for x in values) or values[0] > values[1] or values[2] > values[3]:
        raise PreparationError("invalid geometry envelope")
    return [values[0], values[2], values[1], values[3]]


def number(row, name, low=None, high=None, integral=False):
    value = row[name]
    if type(value) not in (int, float) or not math.isfinite(value):
        raise PreparationError(f"{name} is missing or nonfinite")
    if low is not None and value < low or high is not None and value > high:
        raise PreparationError(f"{name} is outside selected development bounds")
    if integral and int(value) != value:
        raise PreparationError(f"{name} must be integral")
    return int(value) if integral else value


def configuration_values(row, transform):
    x, y = number(row, "centroid_x"), number(row, "centroid_y")
    lon, lat = transform(x, y)
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise PreparationError("invalid transformed centroid")
    terrain_raw = number(row, "mean.slope", 0, 89.999999)
    return {
        "cfe": {"bexp": number(row, "mode.bexp_soil_layers_stag=2", 0),
                "dksat": number(row, "geom_mean.dksat_soil_layers_stag=2", 0),
                "psisat": number(row, "geom_mean.psisat_soil_layers_stag=2", 0),
                "slope": number(row, "mean.slope_1km", 0, 1),
                "smcmax": number(row, "mean.smcmax_soil_layers_stag=2", 0, 1),
                "smcwlt": number(row, "mean.smcwlt_soil_layers_stag=2", 0, 1),
                "max_gw_storage": number(row, "mean.Zmax", 0) / 1000,
                "gw_Coeff": number(row, "mean.Coeff", 0),
                "gw_Expon": number(row, "mode.Expon", 0),
                "gw_storage": "0.05", "refkdt": number(row, "mean.refkdt", 0)},
        "noah": {"lat": lat, "lon": lon,
                 "terrain_slope": math.degrees(math.atan(math.tan(math.radians(terrain_raw)) / 100)),
                 "azimuth": number(row, "circ_mean.aspect", 0, 360),
                 "ISLTYP": number(row, "mode.ISLTYP", 1, 19, True),
                 "IVGTYP": number(row, "mode.IVGTYP", 1, 20, True)},
    }


def prepare(source, destination, template_root, *, expected_sha256, expected_bytes,
            reach, gauge_id, start_time_utc, stop_time_utc_exclusive, transform=None):
    start, stop = hourly_time(start_time_utc), hourly_time(stop_time_utc_exclusive)
    hours = int((stop - start).total_seconds() / 3600)
    if not 1 <= hours <= 100000 or not re.fullmatch(r"\d{8}", gauge_id):
        raise PreparationError("invalid interval or gauge")
    source, template_root = Path(source), Path(template_root)
    before = binding(source)
    if before != {"sha256": expected_sha256, "bytes": expected_bytes}:
        raise PreparationError("source hash or byte length mismatch")
    templates, template_bindings = read_templates(template_root)
    if transform is None:
        from pyproj import Transformer
        transform = Transformer.from_crs(5070, 4326, always_xy=True).transform
    uri = Path(os.path.abspath(source)).as_uri() + "?mode=ro&immutable=1"
    with closing(sqlite3.connect(uri, uri=True)) as source_db:
        source_db.execute("PRAGMA query_only=ON")
        source_db.row_factory = sqlite3.Row
        network = source_db.execute("SELECT DISTINCT id,toid,divide_id FROM network WHERE id IS NOT NULL LIMIT ?",
                                    (MAX_NETWORK_ROWS + 1,)).fetchall()
        domain = upstream_closure(network, reach)
        cats, nodes = domain["catchment_ids"], domain["nodes"]
        placeholders = ",".join("?" for _ in cats)
        attributes = source_db.execute(f'SELECT * FROM "divide-attributes" WHERE divide_id IN ({placeholders}) ORDER BY divide_id', cats).fetchall()
        if [row["divide_id"] for row in attributes] != cats:
            raise PreparationError("attribute axis differs from domain")
        geometry = source_db.execute(f'SELECT divide_id,geom,areasqkm FROM divides WHERE divide_id IN ({placeholders}) ORDER BY divide_id', cats).fetchall()
        if [row["divide_id"] for row in geometry] != cats:
            raise PreparationError("geometry axis differs from domain")
        columns = source_db.execute("SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns WHERE table_name='divides'").fetchall()
        if [tuple(row) for row in columns] != [("divides", "geom", 5070)]:
            raise PreparationError("unexpected geometry CRS/schema")
        bounds = [envelope(row["geom"]) for row in geometry]
        combined = [min(b[0] for b in bounds), min(b[1] for b in bounds), max(b[2] for b in bounds), max(b[3] for b in bounds)]
        values = [configuration_values(row, transform) for row in attributes]
        destination = fresh_directory(destination, [source.parent, template_root])
        config = destination / "config"
        config.mkdir()
        subset = config / "public-watauga.gpkg"
        counts = {}
        with closing(sqlite3.connect(subset)) as out:
            for name, key in TABLE_KEYS.items():
                allowed = cats if key == "divide_id" else nodes
                sql = source_db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
                if not sql:
                    raise PreparationError(f"required source table missing: {name}")
                out.execute(sql[0])  # one CREATE TABLE; no source triggers/extensions execute
                rows = source_db.execute(f"SELECT * FROM {quote(name)} WHERE {quote(key)} IN ({','.join('?' for _ in allowed)}) ORDER BY fid", allowed).fetchall()
                counts[name] = len(rows)
                if rows:
                    out.executemany(f"INSERT INTO {quote(name)} VALUES ({','.join('?' for _ in rows[0])})", [tuple(row) for row in rows])
            for name in ("gpkg_spatial_ref_sys", "gpkg_contents", "gpkg_geometry_columns"):
                sql = source_db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()[0]
                out.execute(sql)
                rows = source_db.execute(f"SELECT * FROM {quote(name)}").fetchall()
                selected = []
                for row in rows:
                    if name == "gpkg_spatial_ref_sys" or row["table_name"] in TABLE_KEYS:
                        items = dict(row)
                        if name == "gpkg_contents":
                            items.update({k: None for k in ("min_x", "min_y", "max_x", "max_y")})
                        selected.append(tuple(items.values()))
                if selected:
                    out.executemany(f"INSERT INTO {quote(name)} VALUES ({','.join('?' for _ in selected[0])})", selected)
            out.execute("PRAGMA application_id=1196444487")
            out.execute("PRAGMA user_version=10300")
            out.commit()
        for cat, value in zip(cats, values):
            for model, extension in (("cfe", "ini"), ("noah", "input")):
                folder = config / "cat_config" / ("CFE" if model == "cfe" else "NOAH-OWP-M")
                folder.mkdir(parents=True, exist_ok=True)
                kwargs = {**value[model], "start_datetime": start.strftime("%Y%m%d%H%M"), "end_datetime": stop.strftime("%Y%m%d%H%M")}
                (folder / f"{cat}.{extension}").write_text(templates[model].format(**kwargs))
        (destination / "NGIAB_TEMPLATE_LICENSE.txt").write_text(templates["license"])
        (config / "troute.yaml").write_text(templates["routing"].format(
            geo_file_path="./config/public-watauga.gpkg", cpu_pool=2, time_step_size=300,
            start_datetime=start.strftime("%Y-%m-%d %H:%M:%S"), nts=hours * 12,
            max_loop_size=hours * 12, binary_nexus_file_folder_comment="#"))
        realization = json.loads(templates["realization"])
        realization["time"].update(start_time=start.strftime("%Y-%m-%d %H:%M:%S"),
                                   end_time=stop.strftime("%Y-%m-%d %H:%M:%S"), output_interval=3600)
        (config / "realization.json").write_text(json.dumps(realization, indent=2) + "\n")
        with (destination / "cfe-attributes.csv").open("w", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["catchment_id", "mean.slope", "mean.slope_1km"])
            writer.writerows((row["divide_id"], row["mean.slope"], row["mean.slope_1km"]) for row in attributes)
    if binding(source) != before:
        raise PreparationError("source changed during preparation; generated bundle is invalid")
    files = [{"path": str(path.relative_to(destination)), **binding(path)}
             for path in sorted(destination.rglob("*")) if path.is_file()]
    report = {
        "schema_version": ADAPTER_VERSION, "fixture_kind": "new_public_development_fixture",
        "gauge_id": gauge_id, **domain, "source": before,
        "upstream_template_revision": UPSTREAM_REVISION, "template_bindings": template_bindings,
        "adapter": binding(Path(__file__)), "start_time_utc": start_time_utc,
        "stop_time_utc_exclusive": stop_time_utc_exclusive, "history_hours": hours,
        "geometry": {"path": "config/public-watauga.gpkg", **binding(subset), "table": "divides",
                     "id_column": "divide_id", "geometry_column": "geom", "crs": "EPSG:5070",
                     "envelope": combined, "catchment_area_sqkm": sum(row["areasqkm"] for row in geometry)},
        "table_counts": counts, "files": files,
        "configuration": {"cfe_drainage_source": "mean.slope_1km", "cfe_drainage_transform": "identity",
            "noah_terrain_transform": "degrees(arctan(tan(radians(mean.slope))/100))",
            "groundwater_storage_ratio": 0.05, "cfe_soil_storage_ratio": 0.05,
            "routing_step_seconds": 300, "routing_cpu_pool": 2,
            "streamflow_assimilation": False, "waterbody_breaks": False,
            "source_attribute_units_status": "unverified",
            "native_realization_status": "template_pending_weather_assembly",
            "template_forcing_provider": "NetCDF", "template_forcing_path": "./forcings/forcings.nc",
            "full_scientific_configuration_validated": False},
        "domain_cut": {"selected_gauge_output": reach, "terminal_nexus": domain["outlet_nexus"],
                       "terminal_downstream_is_outside_subset": True,
                       "adjacent_downstream_tributaries_excluded": True,
                       "gauge_output_is_junction_sum": False},
        "qualification_blockers": ["Gauge/reach resolution requires independent source review",
            "Source-attribute units and derivation require qualification",
            "Noah parameter tables and loaded component compatibility require runtime qualification",
            "Weather payloads, source clocks and spatial weights remain separate inputs",
            "NetCDF template does not consume separately prepared provider CSV files; native assembly is incomplete",
            "Terminal network cut and gauge output selection require runtime qualification",
            "Generated endpoint interpretation requires native runtime qualification"],
        "execution_ready": False, "historical_fixture_restored": False,
    }
    report["preparation_identity_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    (destination / "DOMAIN_PREPARATION.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--templates", required=True, type=Path)
    parser.add_argument("--reach", required=True)
    parser.add_argument("--gauge", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--stop-exclusive", required=True)
    parser.add_argument("--source-sha256", default=SOURCE_SHA)
    parser.add_argument("--source-bytes", type=int, default=SOURCE_BYTES)
    args = parser.parse_args()
    report = prepare(args.source, args.destination, args.templates, expected_sha256=args.source_sha256,
                     expected_bytes=args.source_bytes, reach=args.reach, gauge_id=args.gauge,
                     start_time_utc=args.start, stop_time_utc_exclusive=args.stop_exclusive)
    print(json.dumps({"catchment_count": len(report["catchment_ids"]),
                      "preparation_identity_sha256": report["preparation_identity_sha256"],
                      "execution_ready": report["execution_ready"]}))


if __name__ == "__main__":
    main()
