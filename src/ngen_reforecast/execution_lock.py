"""Admission for one pinned diagnostic; planning locks never authorize execution."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
from importlib import resources
import json
import os
from pathlib import Path

from .campaign import normalize_campaign, _open_resident, _AssetRefusal
from . import __version__
from ._reference.common import canonical, load, relative, seal, verify, inventory

PROFILE = "watauga-v2-independent-serial"
PROTOCOL_ID = "0c6a5c8c063343c3a02659298a273200d851252d63f84d7ffcd0fa6027361b94"
ADMISSION_ID = "f06fba943e9128f9a8ec56d7f7b80e3fe2f8b38cca5348cba0eff4eda7389146"
RUNTIME_ID = "9f3a32d9bb9cf5214b99bf84e40230a2d83deeeb6c27430bd37f00a9ca02578d"
REFERENCE_ID = "3ac59c420b3b96a5c45f2dea53dc149524e496a5063356944246cf08c25963d2"
MAX_METADATA_BYTES = 4 * 1024 * 1024


class ExecutionLockError(ValueError):
    pass


def payload_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _binding_bytes(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _profile() -> dict:
    value = load(Path(str(resources.files("ngen_reforecast").joinpath("_profiles/watauga-v2.json"))), MAX_METADATA_BYTES)
    for key, field, identity in (
        ("protocol", "protocol_identity_sha256", PROTOCOL_ID),
        ("admission", "admission_identity_sha256", ADMISSION_ID),
        ("runtime", "runtime_identity_sha256", RUNTIME_ID),
        ("reference_set", "reference_set_identity_sha256", REFERENCE_ID),
    ):
        verify(value[key], field)
        if value[key][field] != identity:
            raise ExecutionLockError("Installed diagnostic profile identity differs")
    return value


def _paths(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != {"fixture_root", "reference_root", "runtime_tar"}:
        raise ExecutionLockError("bundle_paths must bind fixture_root, reference_root and runtime_tar")
    result = {key: relative(path) for key, path in value.items()}
    paths = list(result.values())
    if any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
           for i, a in enumerate(paths) for b in paths[i + 1:]):
        raise ExecutionLockError("Bundle namespaces must be separate")
    return result


def _supported_campaign(campaign: dict) -> dict:
    c = normalize_campaign(campaign)
    p = _profile()["protocol"]
    if (c["origin_time_utc"] != p["cases"][0]["origin_time_utc"]
        or c["history"] != {"start_time_utc": p["cases"][0]["origin_time_utc"],
                            "stop_time_utc": p["cases"][0]["stop_time_utc_exclusive"]}
        or c["issue_times_utc"] != [case["issue_time_utc"] for case in p["cases"][1:]]
        or c["domains"] != [{"domain_id": "watauga", "locations": [{"location_id": "03479000", "reach_id": "1017693"}], "assets": []}]):
        raise ExecutionLockError("Only the exact Watauga v2 domain, cold origin and two 18-hour issues are admitted; supply assets in the execution bundle")
    r = c["resources"]
    if any(r[k] != v for k, v in {"host_cpus": 2, "parent_cpus": 1, "cpus_per_branch": 1,
                                 "max_concurrent_branches": 1, "wall_time_seconds": 1800}.items()):
        raise ExecutionLockError("Diagnostic execution requires the declared serial 2-CPU/1800-second resource profile")
    return c


def _reference_files(profile: dict) -> list[dict]:
    records = []
    for item in profile["reference_set"]["references"]:
        for key, name in (("reference_report", "REFERENCE.json"), ("arrays", "arrays.json"),
                          ("lead_reference", "lead_reference.json")):
            records.append({"path": item["case_id"] + "/" + name, **item[key]})
    records.append({"path": "set/REFERENCE_SET.json", **profile["reference_set_file"]})
    records.append({"path": "set/lead_reference.json", **profile["reference_set"]["lead_reference"]})
    return sorted(records, key=lambda item: item["path"])


def _implementation() -> dict:
    root = resources.files("ngen_reforecast")
    files = [{"path": p.name, **_file_binding(Path(str(p)), 16 * 1024 * 1024)}
             for p in root.iterdir() if p.name.endswith(".py")]
    files.append({"path": "_profiles/watauga-v2.json", **_file_binding(Path(str(root.joinpath("_profiles/watauga-v2.json"))), MAX_METADATA_BYTES)})
    return seal({"package_version": __version__, "files": sorted(files, key=lambda r: r["path"])}, "implementation_identity_sha256")


def _construct(campaign: dict, bundle_paths: dict) -> dict:
    c = _supported_campaign(campaign)
    p = _profile()
    # Namespace identity includes the requested export projection but never changes inputs.
    implementation = _implementation()
    run_id = c["campaign_id"] + "-" + hashlib.sha256(canonical({"campaign": c, "implementation": implementation})).hexdigest()[:16]
    protocol = deepcopy(p["protocol"])
    protocol.pop("protocol_identity_sha256")
    protocol.update(experiment_id=run_id,
                    authorization="Owner-authorized public campaign implementation and separately bounded diagnostic replay.",
                    scope="Public packaged executor diagnostic replay of unchanged Watauga v2 inputs against sealed references",
                    reference_protocol_identity_sha256=PROTOCOL_ID,
                    reference_set_identity_sha256=REFERENCE_ID,
                    campaign_identity_sha256=hashlib.sha256(canonical(c)).hexdigest())
    protocol["bounds"].pop("aggregate_actual_model_processes_including_prior_phase_maximum", None)
    protocol = seal(protocol, "protocol_identity_sha256")
    admission = deepcopy(p["admission"])
    admission.pop("admission_identity_sha256")
    admission.update(experiment_id=run_id, protocol_identity_sha256=protocol["protocol_identity_sha256"],
                     reference_admission_identity_sha256=ADMISSION_ID)
    admission = seal(admission, "admission_identity_sha256")
    value = {
        "schema_version": "diagnostic-execution-lock/0.1", "kind": PROFILE, "run_id": run_id,
        "fixture_id": protocol["fixture_id"], "campaign": c,
        "implementation": implementation,
        "scientific_configuration_identity_sha256": protocol["scientific_configuration_identity_sha256"],
        "runtime_identity_sha256": RUNTIME_ID, "assembly_identity_sha256": admission["assembly_identity_sha256"],
        "protocol_identity_sha256": protocol["protocol_identity_sha256"],
        "reference_set_identity_sha256": REFERENCE_ID,
        "protocol": protocol, "admission": admission,
        "protocol_file": _binding_bytes(payload_bytes(protocol)),
        "admission_file": _binding_bytes(payload_bytes(admission)),
        "bundle_paths": _paths(bundle_paths), "reference_files": _reference_files(p),
        "bounds": protocol["bounds"], "source_tools": protocol["tools"],
        "native_warning_policy": p["native_warning_policy"],
        "diagnostic_execution_admitted": True, "release_qualified": False,
        "interpretation_limits": admission["interpretation_limits"],
    }
    return seal(value, "execution_lock_sha256")


def validate_execution_lock(lock: dict) -> dict:
    verify(lock, "execution_lock_sha256")
    if lock != _construct(lock.get("campaign", {}), lock.get("bundle_paths", {})):
        raise ExecutionLockError("Execution lock differs from the installed pinned diagnostic contract")
    return lock


def load_execution_lock(path: Path) -> dict:
    return validate_execution_lock(load(path, MAX_METADATA_BYTES))


def _file_binding(path: Path, maximum: int) -> dict:
    try:
        fd, before = _open_resident(path, maximum)
    except _AssetRefusal as exc:
        raise ExecutionLockError(str(exc)) from exc
    try:
        h = hashlib.sha256()
        total = 0
        while block := os.read(fd, 1024 * 1024):
            total += len(block)
            if total > maximum:
                raise ExecutionLockError("Source grew beyond bound")
            h.update(block)
        after = os.fstat(fd)
        if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ExecutionLockError("Source changed during verification")
        return {"bytes": total, "sha256": h.hexdigest()}
    finally:
        os.close(fd)


def verify_execution_assets(lock: dict, asset_root: Path) -> dict:
    validate_execution_lock(lock)
    root = Path(asset_root).absolute()
    count = total = 0
    for case, records in lock["admission"]["case_inputs"].items():
        folder = root / lock["bundle_paths"]["fixture_root"] / case
        # Reject unbound extras as well as missing, corrupt and nonresident files.
        observed = inventory(folder, lock["bounds"]["fixture_preparation_bytes"], hash_files=False)
        if [(x["path"], x["bytes"]) for x in observed] != [(x["path"], x["bytes"]) for x in records]:
            raise ExecutionLockError("Fixture inventory differs: " + case)
        for record in records:
            if _file_binding(folder / relative(record["path"]), lock["campaign"]["resources"]["max_asset_bytes"]) != {k: record[k] for k in ("bytes", "sha256")}:
                raise ExecutionLockError("Fixture bytes differ: " + record["path"])
            count += 1; total += record["bytes"]
    for record in lock["reference_files"]:
        if _file_binding(root / lock["bundle_paths"]["reference_root"] / relative(record["path"]), min(lock["bounds"]["reference_arrays_bytes"], lock["campaign"]["resources"]["max_asset_bytes"])) != {k: record[k] for k in ("bytes", "sha256")}:
            raise ExecutionLockError("Sealed reference bytes differ: " + record["path"])
        count += 1; total += record["bytes"]
    runtime = _file_binding(root / lock["bundle_paths"]["runtime_tar"], min(64 * 1024 * 1024, lock["campaign"]["resources"]["max_asset_bytes"]))
    if runtime != lock["admission"]["runtime_transfer_payload"]:
        raise ExecutionLockError("Runtime transfer bytes differ")
    count += 1; total += runtime["bytes"]
    if total > lock["campaign"]["resources"]["max_total_asset_bytes"]:
        raise ExecutionLockError("Source assets exceed the campaign total byte allowance")
    tools = resources.files("ngen_reforecast").joinpath("_reference")
    for record in lock["source_tools"]:
        if _file_binding(Path(str(tools.joinpath(Path(record["path"]).name))), 16 * 1024 * 1024) != {k: record[k] for k in ("bytes", "sha256")}:
            raise ExecutionLockError("Installed frozen reference tool bytes differ")
    return {"verified": True, "source_assets": count, "source_bytes": total}


def prepare_execution(campaign: dict, bundle_file: Path) -> dict:
    bundle = load(bundle_file, MAX_METADATA_BYTES)
    if set(bundle) != {"schema_version", "bundle_paths"} or bundle["schema_version"] != "watauga-v2-execution-bundle/0.1":
        raise ExecutionLockError("Unsupported execution bundle")
    lock = _construct(campaign, bundle["bundle_paths"])
    verify_execution_assets(lock, bundle_file.parent)
    return lock


def verify_native_warnings(lock: dict, case_id: str, native_receipt_root: Path) -> dict:
    validate_execution_lock(lock)
    case = next((c for c in lock["protocol"]["cases"] if c["case_id"] == case_id), None)
    if case is None:
        raise ExecutionLockError("Unknown case")
    receipt = load(Path(native_receipt_root) / "RECEIPT.json", MAX_METADATA_BYTES)
    verify(receipt, "process_receipt_identity_sha256")
    if (receipt["returncode"] != 0 or receipt["reservation"]["case_id"] != case_id
        or receipt["reservation"]["protocol_identity_sha256"] != lock["protocol_identity_sha256"]
        or receipt["reservation"]["admission_identity_sha256"] != lock["admission"]["admission_identity_sha256"]):
        raise ExecutionLockError("Native receipt failed or belongs to another case")
    logs = {}
    for name in ("stdout", "stderr"):
        path = Path(native_receipt_root) / (name + ".log")
        if _file_binding(path, 128 * 1024 * 1024) != receipt[name]:
            raise ExecutionLockError("Native log bytes differ from receipt")
        # Bound resident read after byte identity check; logs are captured, never rewritten.
        from ._reference.common import read
        logs[name] = read(path, 128 * 1024 * 1024).decode("utf-8", errors="strict")
    if any(token in text.upper() for text in logs.values() for token in ("FATAL ERROR", "SEGMENTATION FAULT")):
        raise ExecutionLockError("Fatal native log detected")
    policy = lock["native_warning_policy"]
    expected = Counter(policy["once_per_process"])
    n = len(lock["protocol"]["catchment_ids"]) * case["provider_hours"]
    expected.update({text: multiplier * n for text, multiplier in policy["per_catchment_interval"].items()})
    if Counter(logs["stderr"].splitlines()) != expected:
        raise ExecutionLockError("Native diagnostic warning inventory differs; routing refused")
    if "UNIT CONVERSION" in logs["stdout"].upper() or "WARN:" in logs["stdout"].upper():
        raise ExecutionLockError("Unexpected native stdout warning")
    return {"verified": True, "policy": policy["schema_version"], "catchment_intervals": n,
            "warning_lines": sum(expected.values()), "unit_fallbacks_fixed": False}
