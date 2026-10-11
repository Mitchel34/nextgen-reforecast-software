"""Independently review preserved diagnostic runs; never execute a model.

This reviewer deliberately does not import the physical-reference executor,
normalizer, or auditor. h5py independently reads the preserved NetCDF/HDF5 arrays.
All writes are limited to one new sanitized review receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import stat
import tarfile


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def binding(path, limit=128 * 1024 * 1024):
    path = Path(path).absolute()
    for parent in [*reversed(path.parents), path]:
        s = parent.lstat()
        assert not stat.S_ISLNK(s.st_mode) and not getattr(s, "st_flags", 0) & 0x40000000, "nonresident/symlink evidence"
    before = path.stat()
    assert stat.S_ISREG(before.st_mode) and before.st_size <= limit, "nonregular/oversized evidence"
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    after = path.stat()
    assert (before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns), "evidence changed"
    return {"bytes": before.st_size, "sha256": h.hexdigest()}


def load(path, identity):
    binding(path, 16 * 1024 * 1024)
    def pairs(values):
        d = {}
        for k, v in values:
            assert k not in d, "duplicate key"
            d[k] = v
        return d
    d = json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                   parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    copy = dict(d)
    expected = copy.pop(identity)
    assert digest(copy) == expected, "invalid sealed identity: " + str(path)
    return d


def inventory(root):
    return [{"path": p.relative_to(root).as_posix(), **binding(p)} for p in sorted(root.rglob("*")) if p.is_file()]


def native_check(root, protocol, case):
    fields = protocol["catchment_output_variables"]
    origin = datetime.fromisoformat(case["origin_time_utc"].replace("Z", "+00:00"))
    stamps = [(origin + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S") for i in range(case["provider_hours"])]
    assert sorted(p.stem for p in root.glob("cat-*.csv")) == protocol["catchment_ids"]
    assert sorted(p.name.removesuffix("_output.csv") for p in root.glob("nex-*_output.csv")) == protocol["nexus_ids"]
    ranges = {v: [math.inf, -math.inf] for v in fields}
    for cat in protocol["catchment_ids"]:
        with (root / (cat + ".csv")).open() as stream:
            rows = csv.reader(stream)
            assert next(rows) == ["Time Step", "Time", *fields]
            n = 0
            for i, row in enumerate(rows):
                assert i < len(stamps) and len(row) == 17 and row[:2] == [str(i), stamps[i]]
                values = [float(v) for v in row[2:]]
                assert all(math.isfinite(v) for v in values) and values[fields.index("Q_OUT")] >= 0
                assert values[fields.index("SURF_RUNOFF_SCHEME")] == 1
                for key, v in zip(fields, values):
                    ranges[key][0] = min(ranges[key][0], v)
                    ranges[key][1] = max(ranges[key][1], v)
                n += 1
            assert n == len(stamps)
    nexus_rows = 0
    for nex in protocol["nexus_ids"]:
        with (root / (nex + "_output.csv")).open() as stream:
            rows = csv.reader(stream, skipinitialspace=True)
            n = 0
            for i, row in enumerate(rows):
                assert i < len(stamps) and len(row) == 3 and [v.strip() for v in row[:2]] == [str(i), stamps[i]]
                v = float(row[2]); assert math.isfinite(v) and v >= 0
                n += 1
            assert n == len(stamps)
            nexus_rows += n
    return {"catchment_files": len(protocol["catchment_ids"]), "nexus_files": len(protocol["nexus_ids"]),
            "catchment_rows": len(protocol["catchment_ids"]) * len(stamps), "nexus_rows": nexus_rows,
            "fields_per_catchment_row": len(fields), "full_interval_start_axes_verified": True,
            "all_values_finite": True, "runoff_and_nexus_nonnegative": True, "variable_min_max": ranges}


def routing_check(raw, csv_path, protocol, case):
    import h5py
    import numpy as np
    origin = datetime.fromisoformat(case["origin_time_utc"].replace("Z", "+00:00"))
    count = case["routing_steps"]
    interval = protocol["routing_output_interval_seconds"]
    stamps = [(origin + timedelta(seconds=(i + 1) * interval)).strftime("%Y-%m-%dT%H:%M:%SZ") for i in range(count)]
    units = {"flow": "m3 s-1", "velocity": "m/s", "depth": "m"}
    before = binding(raw)
    with h5py.File(raw, "r") as h:
        assert np.array_equal(h["time"][:], np.arange(1, count + 1) * interval)
        assert h["time"].attrs["units"].decode() == "seconds since " + origin.strftime("%Y-%m-%d %H:%M:%S")
        keys = [typ.decode() + "-" + str(int(number)) for typ, number in zip(h["type"][:], h["feature_id"][:])]
        assert len(keys) == len(set(keys)) == 31 and sorted(keys) == protocol["routing_feature_ids"]
        index = {key: i for i, key in enumerate(keys)}
        arrays = {name: h[name][:] for name in units}
        for name, array in arrays.items():
            assert array.shape == (31, count) and array.dtype == np.dtype("float32")
            assert h[name].attrs["units"].decode() == units[name]
            assert np.isfinite(array).all() and (array >= 0).all()
            assert not (array == h[name].attrs["_FillValue"][0]).any()
        with csv_path.open() as stream:
            rows = csv.reader(stream)
            assert next(rows) == ["feature_id", "valid_time_utc", "flow_m3_s", "velocity_m_s", "depth_m"]
            total = 0
            for feature in protocol["routing_feature_ids"]:
                for i in range(count):
                    row = next(rows)
                    assert len(row) == 5 and row[:2] == [feature, stamps[i]]
                    assert [float(v) for v in row[2:]] == [float(arrays[name][index[feature], i]) for name in units]
                    total += 1
            assert next(rows, None) is None
        mins = {name: [float(a.min()), float(a.max())] for name, a in arrays.items()}
    assert binding(raw) == before
    return {"features": 31, "steps_per_feature": count, "rows": total, "interval_seconds": interval,
            "interval_end_axis_verified": True, "raw_csv_numeric_mismatches": 0,
            "raw_dtype": "float32", "variables_units": units, "variable_min_max": mins,
            "independent_reader": {"h5py": h5py.__version__, "numpy": np.__version__, "HDF5": h5py.version.hdf5_version}}


def source_trace(repo):
    base = repo / ".local/runtime-closure-20261010"
    files = ["src/realizations/catchment/Bmi_Module_Formulation.cpp", "src/realizations/catchment/Bmi_Multi_Formulation.cpp", "include/realizations/catchment/Bmi_Multi_Formulation.hpp"]
    ngen = base / "sources/framework/ngen-9175b640a4e6f1d90e58e0a65662174d08f052ef"
    result = [{"component": "ngen", "commit": "9175b640a4e6f1d90e58e0a65662174d08f052ef", "path": f, **binding(ngen / f)} for f in files]
    for name, ending, commit in [("CFE", "/src/bmi_cfe.c", "a349a953ef239ae7470a8365cf614283d7e6ca80"),
                                 ("SLOTH", "/src/sloth.cpp", "48cd8082878fdb8a6f0e2337a5b375be5b71384c"),
                                 ("NoahOWP", "/bmi/bmi_noahowp.f90", "0abb891b48b043cc626c4e4bbd0efe54ad357fe1")]:
        archive = base / "downloads" / (name + "-" + commit + ".tar.gz")
        with tarfile.open(archive, "r:gz") as tar:
            member = next(m for m in tar if m.name.endswith(ending))
            data = tar.extractfile(member).read()
        result.append({"component": name, "commit": commit, "path": ending.lstrip("/"), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return result


def review(repo, experiment, inputs, destination):
    frozen = experiment / "frozen"
    protocol = load(frozen / "PROTOCOL.json", "protocol_identity_sha256")
    admission = load(frozen / "ADMISSION.json", "admission_identity_sha256")
    freeze = load(frozen / "FREEZE.json", "freeze_identity_sha256")
    assert binding(frozen / "PROTOCOL.json") == freeze["protocol_file"]
    assert binding(frozen / "ADMISSION.json") == freeze["admission_file"]
    assert binding(experiment / "run_isolated_job.py") == freeze["host_orchestrator"]
    for source in freeze["source_tools"]:
        assert binding(repo / source["path"]) == {k: source[k] for k in ("bytes", "sha256")}
    assert binding(repo / "docs/evidence/linux-diagnostic-admission-20261010.json") == admission["runtime_qualification_receipt"]
    assert binding(inputs / "ADMISSION.json") == admission["input_contract_receipt"]
    ledger = [load(p, "reservation_identity_sha256") for p in sorted((experiment / "ledger").glob("PROCESS-*.json"))]
    assert [r["process_number"] for r in ledger] == list(range(1, 7))
    assert all(r["protocol_identity_sha256"] == protocol["protocol_identity_sha256"] for r in ledger)
    records = []
    for case in protocol["cases"]:
        case_id = case["case_id"]
        attempt = experiment / "attempts" / (case_id + "-a1")
        host = load(attempt / "HOST_EXECUTION.json", "host_execution_identity_sha256")
        assert host["status"] == "both_stages_zero_exit" and host["case_id"] == case_id
        assert host["protocol_identity_sha256"] == protocol["protocol_identity_sha256"] and host["admission_identity_sha256"] == admission["admission_identity_sha256"]
        image = host["container_inspection"]
        hc = image["HostConfig"]
        assert image["Image"] == "sha256:" + admission["image_manifest_sha256"]
        assert image["ImageManifestDescriptor"]["platform"] == {"architecture": "arm64", "os": "linux"}
        assert hc["NetworkMode"] == "none" and hc["ReadonlyRootfs"] is True and not hc["Privileged"]
        assert not hc["Binds"] and not hc["VolumesFrom"] and not image["Mounts"] and not hc["CapAdd"]
        assert hc["CapDrop"] == ["ALL"] and hc["SecurityOpt"] == ["no-new-privileges"]
        assert hc["Memory"] == hc["MemorySwap"] == 8 * 1024**3 and hc["NanoCpus"] == 2 * 10**9 and hc["PidsLimit"] == 256
        assert hc["Tmpfs"] == {"/tmp": "rw,exec,size=64m", "/work": "rw,noexec,size=128m", "/work/job/outputs": "rw,noexec,size=1g"}
        env = dict(v.split("=", 1) for v in image["Config"]["Env"])
        assert env["LD_LIBRARY_PATH"] == admission["native_ld_library_path"]
        assert all(env[name] == "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "PYTHONDONTWRITEBYTECODE")) and env["TZ"] == "UTC"
        for key in ["cgroup_before", "cgroup_after_native", "cgroup_after_routing"]:
            cg = host[key]
            assert cg["cpu.max"].strip() == "200000 100000" and int(cg["memory.max"]) == 8 * 1024**3 and int(cg["pids.max"]) == 256
            assert int(cg["memory.peak"]) < 8 * 1024**3 and int(cg["pids.peak"]) <= 256
            events = dict(line.split() for line in cg["memory.events"].splitlines())
            assert all(int(v) == 0 for v in events.values())
        assert host["whole_job_model_elapsed_seconds"] < 1800 and host["host_free_bytes_after"] >= 8 * 1024**3
        for key in ["storage_before", "storage_after"]:
            storage = host[key]
            assert storage["runtime_allocated_bytes"] <= 12 * 1024**3 and storage["fixture_allocated_bytes"] <= 2 * 1024**3
            assert storage["generated_allocated_bytes"] <= 4 * 1024**3 and storage["host_free_bytes"] >= 8 * 1024**3
        assert host["cleanup"] == [{"action": "stop", "status": "completed"}, {"action": "rm", "status": "completed"}]
        input_rows = admission["case_inputs"][case_id]
        assert inventory(inputs / case_id) == sorted(input_rows, key=lambda r: r["path"])
        input_id = digest({"case_id": case_id, "files": input_rows})
        receipts = []
        for stage in ["native", "routing"]:
            r = load(attempt / stage / "RECEIPT.json", "process_receipt_identity_sha256")
            res = r["reservation"]
            assert ledger[res["process_number"] - 1] == res and res["case_id"] == case_id and res["stage"] == stage
            assert res["admission_identity_sha256"] == admission["admission_identity_sha256"] and res["admission_file_sha256"] == freeze["admission_file"]["sha256"]
            assert res["runtime_identity_sha256"] == admission["runtime_identity_sha256"] and res["assembly_identity_sha256"] == admission["assembly_identity_sha256"]
            assert r["case_input_identity_sha256_after"] == res["case_input_identity_sha256"] == input_id
            assert res["argv"] == protocol[stage + "_argv"]
            assert r["executor"] == binding(repo / "scripts/physical_reference_v2/execute_stage.py")
            assert r["returncode"] == 0 and r["termination_reason"] is None and r["post_launch_verification_error"] is None
            for log in ["stdout", "stderr"]:
                assert binding(attempt / stage / (log + ".log")) == r[log]
            if stage == "native":
                assert r["native_output_contract"]["native_output_contract_complete"] is True
            receipts.append(r)
        raw_inventory = inventory(attempt / "outputs")
        assert raw_inventory == receipts[1]["outputs_after"]
        indexed = {r["path"]: r for r in raw_inventory}
        assert all(indexed[row["path"]] == row for row in receipts[0]["outputs_after"])
        native = native_check(attempt / "outputs/ngen", protocol, case)
        norm = load(attempt / "normalized/NORMALIZATION.json", "normalization_identity_sha256")
        assert norm["normalizer"] == binding(repo / "scripts/physical_reference_v2/normalize_routing.py")
        assert norm["netCDF4_version"] == "1.6.3" and norm["numpy_version"] == "1.26.4"
        assert binding(attempt / "normalized/routing.csv") == norm["normalized_csv"]
        assert norm["raw_sources"] == [row for row in raw_inventory if row["path"].startswith("troute/")]
        route = routing_check(attempt / "outputs" / norm["raw_sources"][0]["path"], attempt / "normalized/routing.csv", protocol, case)
        warnings = Counter()
        with (attempt / "native/stderr.log").open() as stream:
            for line in stream:
                warnings[line.strip()] += 1
        conversions = {k: v for k, v in warnings.items() if k.startswith("WARN: Unit conversion")}
        count = native["catchment_rows"]
        expected = {'WARN: Unit conversion unsuccessful - Returning unconverted value! ("Unable to convert m to 1")': 14 * count,
                    'WARN: Unit conversion unsuccessful - Returning unconverted value! ("Unable to parse out_units value none")': 2 * count,
                    'WARN: Unit conversion unsuccessful - Returning unconverted value! ("Unable to parse in_units value none")': count}
        assert conversions == expected and len(warnings) == 12
        assert all(k.startswith("Definition of ") or k in conversions for k in warnings)
        sloth = json.loads((inputs / case_id / "config/realization.json").read_text())["global"]["formulations"][0]["params"]["modules"][0]["params"]
        assert sloth["model_params"] == {"sloth_ice_fraction_schaake(1,double,m,node)": 0.0, "sloth_ice_fraction_xinanjiang(1,double,1,node)": 0.0, "sloth_soil_moisture_profile(1,double,1,node)": 0.0}
        records.append({"case_id": case_id, "host_receipt": {**binding(attempt / "HOST_EXECUTION.json"), "identity_sha256": host["host_execution_identity_sha256"]},
                        "input_identity_sha256": input_id, "input_files_checked": len(input_rows),
                        "process_receipt_identities": [r["process_receipt_identity_sha256"] for r in receipts],
                        "process_numbers": [r["reservation"]["process_number"] for r in receipts],
                        "executor_source": receipts[0]["executor"], "normalizer_source": norm["normalizer"],
                        "in_image_normalization_packages": {"netCDF4": norm["netCDF4_version"], "numpy": norm["numpy_version"]},
                        "normalization_identity_sha256": norm["normalization_identity_sha256"],
                        "raw_inventory_identity_sha256": digest(raw_inventory), "raw_files_checked": len(raw_inventory),
                        "raw_output_bytes": sum(r["bytes"] for r in raw_inventory), "routing_raw_binding": norm["raw_sources"][0],
                        "normalized_csv": norm["normalized_csv"], "native": native, "routing": route,
                        "warnings": {"native_stderr": receipts[0]["stderr"], "distinct_conversion_messages": conversions,
                                     "other_distinct_messages": len(warnings) - len(conversions), "all_other_messages_are_XML_definition_overrides": True,
                                     "fully_accounted_conversion_warnings": True},
                        "observed_model_resource_peaks": {"memory_bytes": int(host["cgroup_after_routing"]["memory.peak"]), "pids": int(host["cgroup_after_routing"]["pids.peak"]), "logical_job_wall_seconds": host["whole_job_model_elapsed_seconds"]},
                        "container_and_cgroup_limits_verified": True, "cleanup_receipt_verified": True,
                        "no_observed_OOM_or_memory_limit_events": True})
    report = {"schema_version": "public-watauga-independent-runtime-output-review/0.1", "reviewed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "experiment_id": protocol["experiment_id"], "fixture_id": protocol["fixture_id"],
              "protocol_identity_sha256": protocol["protocol_identity_sha256"], "admission_identity_sha256": admission["admission_identity_sha256"],
              "runtime_identity_sha256": admission["runtime_identity_sha256"], "freeze_identity_sha256": freeze["freeze_identity_sha256"],
              "reviewer": {"source_path": "scripts/runtime/review_physical_outputs.py", **binding(Path(__file__))},
              "independent_from_executor_and_auditor": True, "new_model_invocations": 0, "cases": records,
              "source_trace_bindings": source_trace(repo), "model_processes_verified": len(ledger),
              "disposition": "diagnostic_output_integrity_verified_with_explained_unit_interface_warnings",
              "release_qualified": False, "scientific_validation_claimed": False,
              "warning_interpretation": {"output_serialization": "NGen multi-output scalar access requests units1 for14 CFE meter outputs and SURF_RUNOFF_SCHEME none; failed conversions preserve original BMI scalars.14 m-to1 and1 parse-in-none per row exactly match logs.",
                                         "input_edges": "The two parse-out-none warnings are SLOTH unit1 to CFE none for ice_fraction_xinanjiang and soil_moisture_profile. Both are configured0.0, without aliases or inputs; SLOTH UpdateUntil only advances time. Values remain exact zero by source trace; they are not directly instrumented at runtime.",
                                         "schaake_edge": "SLOTH ice_fraction_schaake and CFE ice_fraction_schaake both declare m. The m-to1 warnings do not indicate a mismatch on this edge.",
                                         "physical_flux_edges": "No QINSUR m/s-to-mm h-1 or EVAPOTRANS m/s-to-m s-1 failure appears. Separate inert pinned UDUNITS probe proves conversion factor3.6e6 and identity respectively; logs alone do not independently measure every flux conversion.",
                                         "upstream_repair_required": "Replace literal1 output units and invalid none unit labels with consistent variable metadata before a release; any changed experiment must receive a new identity."},
              "limits": ["Output completeness, preservation and units provenance are verified; drainage/terrain candidates, radiation convention, cold-state convergence and interior-gauge reach approximation retain their frozen limitations.",
                         "No shared-history branching, full land checkpoint, forecast skill, scientific equivalence to historical E03, clean-build release or redistribution qualification is established.",
                         "Recorded cgroup peaks are after native/routing stages, before normalization; immutable container limits also cover normalization but its peak is not separately recorded.",
                         "The independent HDF5 reader checks every routed value and clock through a different library; it does not re-execute routing or the land model."]}
    report["review_identity_sha256"] = digest(report)
    with destination.open("x") as output:
        output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ["repository", "experiment", "inputs", "destination"]:
        p.add_argument(arg, type=Path)
    a = p.parse_args()
    result = review(a.repository.absolute(), a.experiment.absolute(), a.inputs.absolute(), a.destination)
    print(result["review_identity_sha256"])
