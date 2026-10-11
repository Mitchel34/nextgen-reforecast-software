"""Read every pinned t-route NetCDF coordinate/value into a bound portable CSV.

Run with the qualified image's exact netCDF4 environment. No models are loaded.
"""
from __future__ import annotations

import argparse
import csv
from datetime import timedelta
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c


def normalize(protocol_path, case_id, output_root, destination):
    import netCDF4
    import numpy as np
    protocol = c.verify(c.load(protocol_path), "protocol_identity_sha256")
    cases = [case for case in protocol["cases"] if case["case_id"] == case_id]
    if len(cases) != 1:
        raise c.ReferenceError("unknown or duplicate reference case")
    case = cases[0]
    origin = c.utc(case["origin_time_utc"])
    interval = protocol["routing_output_interval_seconds"]
    steps = case["provider_hours"] * 3600 // interval
    root = Path(output_root)
    files = sorted((root / "troute").glob("*.nc"))
    if len(files) != 1:
        raise c.ReferenceError("one complete NetCDF routing output is required")
    path = files[0]
    raw_binding = c.binding(path, 128 * 1024 * 1024)
    features = protocol["routing_feature_ids"]
    units = {"flow": "m3 s-1", "velocity": "m/s", "depth": "m"}
    metadata = {}
    result = {}
    with netCDF4.Dataset(path, "r") as nc:
        if len(nc.dimensions["feature_id"]) != len(features) or len(nc.dimensions["time"]) != steps:
            raise c.ReferenceError("routing NetCDF dimensions differ")
        tv = nc.variables["time"]
        if tv.dimensions != ("time",) or tv.units != "seconds since " + origin.strftime("%Y-%m-%d %H:%M:%S"):
            raise c.ReferenceError("routing NetCDF time coordinate contract differs")
        time = tv[:]
        if np.ma.getmaskarray(time).any() or not np.array_equal(np.asarray(time), np.arange(1, steps + 1) * interval):
            raise c.ReferenceError("routing NetCDF missing, ragged or shifted time axis")
        iv = nc.variables["feature_id"]
        types = nc.variables["type"][:]
        ids = iv[:]
        if iv.dimensions != ("feature_id",) or np.ma.getmaskarray(ids).any():
            raise c.ReferenceError("routing feature coordinate contract differs")
        keys = []
        for typ, identity in zip(types, ids):
            if isinstance(typ, bytes):
                typ = typ.decode("ascii")
            typ = str(typ)
            if typ != "wb" or int(identity) != identity:
                raise c.ReferenceError("routing feature type or integer identity differs")
            keys.append(typ + "-" + str(int(identity)))
        if len(set(keys)) != len(keys) or sorted(keys) != features:
            raise c.ReferenceError("routing reach axis differs from complete frozen domain")
        arrays = []
        for name in ("flow", "velocity", "depth"):
            var = nc.variables[name]
            if var.dimensions != ("feature_id", "time") or var.units != units[name] or str(var.dtype) != "float32":
                raise c.ReferenceError("routing variable shape, units or precision differs")
            values = var[:]
            if np.ma.getmaskarray(values).any() or not np.isfinite(values).all() or (values < 0).any():
                raise c.ReferenceError("routing variable contains missing/nonfinite/negative values")
            arrays.append(values)
            metadata[name] = {"units": var.units, "dtype": str(var.dtype), "dimensions": list(var.dimensions)}
        for i, key in enumerate(keys):
            result[key] = [[float(a[i, j]) for a in arrays] for j in range(steps)]
    if c.binding(path, 128 * 1024 * 1024) != raw_binding:
        raise c.ReferenceError("raw routing source changed during normalization")
    destination = Path(destination)
    destination.mkdir(exist_ok=False, parents=True)
    csv_path = destination / "routing.csv"
    with csv_path.open("x", newline="", encoding="ascii") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["feature_id", "valid_time_utc", "flow_m3_s", "velocity_m_s", "depth_m"])
        for feature in features:
            for j, values in enumerate(result[feature]):
                stamp = (origin + timedelta(seconds=(j + 1) * interval)).strftime("%Y-%m-%dT%H:%M:%SZ")
                writer.writerow([feature, stamp, *(format(v, ".17g") for v in values)])
    report = c.seal({"schema_version": "routing-normalization/0.1", "case_id": case_id,
                     "protocol_identity_sha256": protocol["protocol_identity_sha256"],
                     "raw_sources": [{"path": path.relative_to(root).as_posix(), **raw_binding}],
                     "normalizer": c.binding(Path(__file__)), "netCDF4_version": netCDF4.__version__,
                     "numpy_version": np.__version__, "variables": metadata,
                     "complete_feature_count": len(features), "complete_time_steps": steps,
                     "interval_seconds": interval, "normalized_csv": c.binding(csv_path, 128 * 1024 * 1024),
                     "native_model_invocations": 0}, "normalization_identity_sha256")
    c.write_new(destination / "NORMALIZATION.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "case_id", "output_root", "destination"):
        parser.add_argument(name)
    a = parser.parse_args()
    print(normalize(a.protocol, a.case_id, a.output_root, a.destination)["normalization_identity_sha256"])


if __name__ == "__main__":
    main()
