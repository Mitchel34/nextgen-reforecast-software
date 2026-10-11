"""Verified, publish-once diagnostic campaign results.

Captured model stages are attempts. Only a fully audited immutable commit with
an atomically published CURRENT pointer is a completed archived result. This
module neither launches a model nor infers scientific qualification from files.
"""
from __future__ import annotations

import csv
from collections import Counter
import ctypes
import errno
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import sys
import uuid
from typing import Any

from .campaign import CampaignError, _canonical, _nonfinite, _pairs, iter_expected_rows
from . import runtime as resident

MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_ARRAY_BYTES = 128 * 1024 * 1024
MAX_FILE_BYTES = 1024 ** 3
MAX_ARCHIVE_BYTES = 4 * 1024 ** 3
MAX_FILES = 4096
MAX_DIRECTORIES = 4096
MAX_DEPTH = 16


class ArchiveError(CampaignError):
    """An attempt, result identity, transaction, or archived payload failed."""


def _seal(value: dict, field: str) -> dict:
    if field in value:
        raise ArchiveError("Identity field is already present")
    return {**value, field: hashlib.sha256(_canonical(value)).hexdigest()}


def _verify_seal(value: dict, field: str) -> dict:
    if not isinstance(value, dict):
        raise ArchiveError("Sealed metadata must be an object")
    payload = dict(value)
    expected = payload.pop(field, None)
    if not isinstance(expected, str) or expected != hashlib.sha256(_canonical(payload)).hexdigest():
        raise ArchiveError(f"{field} differs from its metadata")
    return value


def _directory(path: Path) -> int:
    try:
        return resident._open_directory(Path(path))
    except (OSError, resident._InspectionFailure) as exc:
        raise ArchiveError(f"Resident archive directory refused: {exc}") from exc


def _file(root: Path, relative: str, maximum: int) -> tuple[int, os.stat_result]:
    root_fd = _directory(root)
    try:
        descriptor = resident._open_asset(root_fd, relative)
        before = os.fstat(descriptor)
        if not 0 <= before.st_size <= maximum:
            os.close(descriptor)
            raise ArchiveError("Artifact exceeds its bounded read allowance")
        return descriptor, before
    except (OSError, resident._InspectionFailure) as exc:
        raise ArchiveError(f"Resident artifact refused: {exc}") from exc
    finally:
        os.close(root_fd)


def _binding(root: Path, relative: str, maximum: int = MAX_FILE_BYTES) -> dict:
    descriptor, before = _file(root, relative, maximum)
    try:
        digest, size = resident._read_bounded(descriptor, before.st_size, digest_only=True)
        if resident._snapshot(before) != resident._snapshot(os.fstat(descriptor)):
            raise ArchiveError("Artifact changed between safe open and completed hash")
        return {"bytes": size, "sha256": digest}
    except resident._InspectionFailure as exc:
        raise ArchiveError(f"Artifact changed while hashing: {exc}") from exc
    finally:
        os.close(descriptor)


def _load(root: Path, relative: str, maximum: int = MAX_METADATA_BYTES) -> Any:
    descriptor, before = _file(root, relative, maximum)
    try:
        raw, _ = resident._read_bounded(descriptor, before.st_size, digest_only=False)
        if resident._snapshot(before) != resident._snapshot(os.fstat(descriptor)):
            raise ArchiveError("Artifact changed between safe open and completed read")
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError, RecursionError, CampaignError, resident._InspectionFailure) as exc:
        raise ArchiveError(f"Bounded resident JSON refused: {exc}") from exc
    finally:
        os.close(descriptor)


def _inventory(root: Path, *, exclude: frozenset[str] = frozenset()) -> list[dict]:
    """Descriptor-relative traversal rejects links, placeholders, races and growth."""
    root_fd = _directory(root)
    files: list[dict] = []
    total = 0
    directory_count = 0

    def visit(descriptor: int, prefix: str, depth: int) -> None:
        nonlocal total, directory_count
        directory_count += 1
        if directory_count > MAX_DIRECTORIES or depth > MAX_DEPTH:
            raise ArchiveError("Archive directory count or nesting bound exceeded")
        before = os.fstat(descriptor)
        with os.scandir(descriptor) as entries:
            names = []
            for entry in entries:
                if len(names) >= MAX_FILES + MAX_DIRECTORIES:
                    raise ArchiveError("Archive directory entry bound exceeded")
                names.append(entry.name)
            names.sort()
        for name in names:
            relative = prefix + name
            info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if resident._is_dataless(info):
                raise ArchiveError("Dataless archive entry refused without hydration")
            is_directory = stat.S_ISDIR(info.st_mode)
            child = resident._open_child(descriptor, name, directory=is_directory)
            try:
                if resident._snapshot(info) != resident._snapshot(os.fstat(child)):
                    raise ArchiveError("Archive entry changed between inventory and safe open")
                if is_directory:
                    visit(child, relative + "/", depth + 1)
                else:
                    size = info.st_size
                    total += size
                    if size > MAX_FILE_BYTES or total > MAX_ARCHIVE_BYTES or len(files) >= MAX_FILES:
                        raise ArchiveError("Archive file count or byte bound exceeded")
                    digest, _ = resident._read_bounded(child, size, digest_only=True)
                    if resident._snapshot(info) != resident._snapshot(os.fstat(child)):
                        raise ArchiveError("Archive entry changed before completed inventory hash")
                    if relative not in exclude:
                        files.append({"path": relative, "bytes": size, "sha256": digest})
            finally:
                os.close(child)
        if resident._snapshot(before) != resident._snapshot(os.fstat(descriptor)):
            raise ArchiveError("Archive directory changed during inventory")

    try:
        visit(root_fd, "", 0)
    except (OSError, resident._InspectionFailure) as exc:
        raise ArchiveError(f"Archive inventory refused: {exc}") from exc
    finally:
        os.close(root_fd)
    return sorted(files, key=lambda item: item["path"])


def _new_file(root: Path, relative: str) -> tuple[int, int]:
    """Create descriptor-relative parents and an exclusive regular leaf."""
    descriptor = _directory(root)
    try:
        parts = resident._relative_parts(relative)
        for name in parts[:-1]:
            try:
                os.mkdir(name, 0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = resident._open_child(descriptor, name, directory=True)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = child
        output = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=descriptor)
        return output, descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _write(root: Path, relative: str, value: Any) -> None:
    raw = json.dumps(value, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    if len(raw) > MAX_METADATA_BYTES:
        raise ArchiveError("Archive metadata exceeds its bound")
    _write_bytes(root, relative, raw)


def _write_bytes(root: Path, relative: str, raw: bytes) -> None:
    output, parent = _new_file(root, relative)
    try:
        with os.fdopen(output, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(parent)
    finally:
        os.close(parent)


def _copy_file(source: Path, relative: str, destination: Path, target: str, expected: dict) -> None:
    descriptor, before = _file(source, relative, MAX_FILE_BYTES)
    output = parent = None
    digest = hashlib.sha256()
    try:
        output, parent = _new_file(destination, target)
        with os.fdopen(output, "wb") as handle:
            output = None
            total = 0
            while total < before.st_size:
                block = os.read(descriptor, min(1024 * 1024, before.st_size - total))
                if not block:
                    raise ArchiveError("Artifact ended early during bounded copy")
                handle.write(block)
                digest.update(block)
                total += len(block)
            if resident._snapshot(before) != resident._snapshot(os.fstat(descriptor)):
                raise ArchiveError("Artifact changed during bounded copy")
            if {"bytes": total, "sha256": digest.hexdigest()} != expected:
                raise ArchiveError("Copied artifact differs from the admitted file binding")
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(parent)
    finally:
        os.close(descriptor)
        if output is not None:
            os.close(output)
        if parent is not None:
            os.close(parent)


def _copy_inventory(source: Path, destination: Path, files: list[dict], prefix: str = "") -> None:
    for item in files:
        _copy_file(source, item["path"], destination, prefix + item["path"],
                   {key: item[key] for key in ("bytes", "sha256")})


def _fsync_tree(root: Path) -> None:
    """Flush reference-tool outputs, which were written before final publication."""
    for item in _inventory(root):
        descriptor, _ = _file(root, item["path"], MAX_FILE_BYTES)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    for folder, _, _ in os.walk(root, topdown=False, followlinks=False):
        descriptor = _directory(Path(folder))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


NAMESPACE_FIELDS = (
    "execution_lock_sha256", "run_id", "fixture_id",
    "scientific_configuration_identity_sha256", "runtime_identity_sha256",
    "assembly_identity_sha256", "protocol_identity_sha256", "reference_set_identity_sha256",
)
PRODUCT_FIELDS = (
    "domain_id", "location_id", "reach_id", "routing_feature_id", "issue_time_utc", "lead_hour", "valid_time_utc",
    "flow_m3_s", "flow_units", "quality_mask", *NAMESPACE_FIELDS,
)


def _lock(value: dict) -> dict:
    from .execution_lock import validate_execution_lock
    validate_execution_lock(value)
    return value


def _namespace(lock: dict) -> dict:
    return {field: lock[field] for field in NAMESPACE_FIELDS}


def _same_namespace(value: dict, lock: dict) -> None:
    if any(value.get(field) != lock[field] for field in NAMESPACE_FIELDS):
        raise ArchiveError("Scientific/runtime/reference/run namespace differs")


def _capture(root: Path, lock: dict) -> dict:
    capture = _verify_seal(_load(root, "CAPTURE.json"), "capture_identity_sha256")
    if (capture.get("schema_version") != "campaign-execution-capture/0.1"
            or capture.get("terminal_status") != "captured"
            or capture.get("execution_lock_sha256") != lock["execution_lock_sha256"]
            or capture.get("run_id") != lock["run_id"]):
        raise ArchiveError("An incomplete or foreign captured attempt cannot be committed")
    for field in NAMESPACE_FIELDS:
        if field in capture and capture[field] != lock[field]:
            raise ArchiveError("Capture identity differs from its execution lock")
    files = capture.get("files")
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise ArchiveError("Capture inventory is absent or exceeds its bound")
    seen = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
            raise ArchiveError("Capture file binding differs from the schema")
        try:
            resident._relative_parts(item["path"])
        except (TypeError, resident._InspectionFailure) as exc:
            raise ArchiveError("Unsafe capture artifact path") from exc
        if (item["path"] == "CAPTURE.json" or item["path"] in seen
                or type(item["bytes"]) is not int or not 0 <= item["bytes"] <= MAX_FILE_BYTES
                or not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise ArchiveError("Capture inventory contains duplicate, unbounded, or malformed bindings")
        seen.add(item["path"])
    if _inventory(root, exclude=frozenset({"CAPTURE.json"})) != files:
        raise ArchiveError("Captured artifacts are missing, changed, or unlisted")
    for name in ("PROTOCOL", "ADMISSION"):
        if _load(root, f"frozen/{name}.json") != lock[name.lower()]:
            raise ArchiveError("Captured frozen protocol/admission differs from its execution lock")
    return capture


def _host_case(capture_root: Path, case_id: str, lock: dict) -> None:
    host = _verify_seal(_load(capture_root, f"attempts/{case_id}/HOST_EXECUTION.json"), "host_execution_identity_sha256")
    if (host.get("case_id") != case_id
            or host.get("protocol_identity_sha256") != lock["protocol_identity_sha256"]
            or host.get("admission_identity_sha256") != lock["admission"]["admission_identity_sha256"]
            or host.get("run_id") != lock["run_id"]
            or host.get("execution_lock_sha256") != lock["execution_lock_sha256"]
            or host.get("status") != "both_stages_zero_exit"):
        raise ArchiveError("Host execution does not bind both completed case stages")
    stages = host.get("stages", [])
    if ([stage.get("stage") for stage in stages] != ["native", "routing"]
            or any(stage.get("docker_exec_exit_code") != 0 or stage.get("stop_reason") is not None for stage in stages)):
        raise ArchiveError("Host stage exit or stop reason does not prove successful completion")
    inspection = host.get("container_inspection", {})
    limits = inspection.get("HostConfig", {})
    bounds = lock["protocol"]["bounds"]
    if (limits.get("Memory") != bounds["memory_bytes"]
            or limits.get("MemorySwap") != bounds["memory_bytes"]
            or limits.get("NanoCpus") != bounds["cpus"] * 1_000_000_000
            or limits.get("PidsLimit") != bounds["pids"]
            or limits.get("NetworkMode") != "none"
            or limits.get("ReadonlyRootfs") is not True
            or limits.get("Privileged") is not False
            or limits.get("Binds") not in (None, [])
            or limits.get("VolumesFrom") not in (None, [])
            or inspection.get("Mounts") not in (None, [])
            or limits.get("CapAdd") not in (None, [])
            or limits.get("CapDrop") != ["ALL"]
            or limits.get("SecurityOpt") != ["no-new-privileges"]
            or limits.get("PidMode", "") not in ("", "private")
            or limits.get("IpcMode") != "private"
            or limits.get("Tmpfs") != {"/tmp": "rw,exec,size=64m", "/work": "rw,noexec,size=128m", "/work/job/outputs": "rw,noexec,size=1g"}
            or inspection.get("State", {}).get("OOMKilled") is not False):
        raise ArchiveError("Actual container isolation or resource limits differ from admission")
    image = "sha256:" + lock["admission"]["image_manifest_sha256"]
    if inspection.get("Image") != image or inspection.get("Config", {}).get("Image") != image:
        raise ArchiveError("Actual container image differs from admitted immutable image")
    if inspection.get("ImageManifestDescriptor", {}).get("platform") != {"architecture": "arm64", "os": "linux"}:
        raise ArchiveError("Actual container platform differs from Linux ARM64")
    config = inspection["Config"]
    entries = config.get("Env", [])
    if not isinstance(entries, list) or any(not isinstance(entry, str) or "=" not in entry for entry in entries):
        raise ArchiveError("Container environment metadata is malformed")
    env = dict(entry.split("=", 1) for entry in entries)
    if len(env) != len(entries):
        raise ArchiveError("Duplicate container environment names")
    expected_env = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                    "NUMEXPR_NUM_THREADS": "1", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1",
                    "LD_LIBRARY_PATH": lock["admission"]["native_ld_library_path"]}
    labels = config.get("Labels", {})
    if (any(env.get(key) != value for key, value in expected_env.items())
            or labels.get("ngen-reforecast.execution-lock") != lock["execution_lock_sha256"]
            or labels.get("ngen-reforecast.run-id") != lock["run_id"]):
        raise ArchiveError("Container loader, thread or run namespace differs")
    for name in ("cgroup_before", "cgroup_after_native", "cgroup_after_routing"):
        group = host.get(name, {})
        try:
            events = dict(line.split() for line in group["memory.events"].splitlines())
            if (group["cpu.max"].strip() != "200000 100000" or int(group["memory.max"]) != bounds["memory_bytes"]
                    or int(group["pids.max"]) != bounds["pids"]
                    or not 0 <= int(group["memory.peak"]) <= bounds["memory_bytes"]
                    or not 0 <= int(group["pids.peak"]) <= bounds["pids"]
                    or any(int(value) != 0 for value in events.values())):
                raise ArchiveError("Observed cgroup resource bounds or OOM events failed")
        except (KeyError, TypeError, ValueError) as exc:
            raise ArchiveError("Cgroup completion evidence is absent or invalid") from exc
    if host.get("cleanup") != [{"action": "stop", "status": "completed"}, {"action": "rm", "status": "completed"}]:
        raise ArchiveError("Disposable container cleanup was not completed")


def _warning_policy(lock: dict, capture_root: Path, case: dict) -> None:
    policy = lock["native_warning_policy"]
    rows = len(lock["protocol"]["catchment_ids"]) * case["provider_hours"]
    expected = Counter(policy["once_per_process"])
    expected.update({line: count * rows for line, count in policy["per_catchment_interval"].items()})
    path = f'attempts/{case["case_id"]}/native/stderr.log'
    descriptor, before = _file(capture_root, path, MAX_ARRAY_BYTES)
    counts = Counter()
    try:
        with os.fdopen(os.dup(descriptor), "rb") as handle:
            while line := handle.readline(4097):
                if len(line) > 4096:
                    raise ArchiveError("Native diagnostic line exceeds its bound")
                try:
                    value = line.decode("ascii").rstrip("\r\n")
                except UnicodeError as exc:
                    raise ArchiveError("Native diagnostic is not the admitted warning text") from exc
                if value not in expected:
                    raise ArchiveError("Unexpected native unit warning or diagnostic text")
                counts[value] += 1
                if counts[value] > expected[value]:
                    raise ArchiveError("Native warning count exceeds its admitted exact policy")
        if counts != expected or resident._snapshot(before) != resident._snapshot(os.fstat(descriptor)):
            raise ArchiveError("Native warning counts differ or log changed while reading")
    finally:
        os.close(descriptor)


def _audit_capture(lock: dict, staging: Path) -> list[dict]:
    """Use the immutable admitted tools against newly captured model evidence."""
    from ._reference import audit_outputs, seal_execution
    source = staging / "capture"
    protocol_path = source / "frozen/PROTOCOL.json"
    admission_path = source / "frozen/ADMISSION.json"
    admission_sha = _binding(source, "frozen/ADMISSION.json")["sha256"]
    reports = []
    verification = staging / "verification"
    verification.mkdir()
    for case in lock["protocol"]["cases"]:
        case_id = case["case_id"]
        _host_case(source, case_id, lock)
        _warning_policy(lock, source, case)
        attempt = source / "attempts" / case_id
        execution = verification / f"EXECUTION-{case_id}.json"
        seal_execution.seal_execution(protocol_path, admission_path, admission_sha,
                                      attempt / "native/RECEIPT.json", attempt / "routing/RECEIPT.json",
                                      source / "ledger", attempt / "outputs", execution)
        report = audit_outputs.audit(protocol_path, case_id, attempt / "outputs",
                                     attempt / "normalized/routing.csv", attempt / "normalized/NORMALIZATION.json",
                                     execution, admission_path, verification / case_id)
        reports.append(report)
    return reports


def _compare_references(lock: dict, staging: Path, *, publish: bool = True) -> list[dict]:
    expected_root = staging / "expected_references"
    reference_set = _verify_seal(_load(expected_root, "set/REFERENCE_SET.json"), "reference_set_identity_sha256")
    if (reference_set["reference_set_identity_sha256"] != lock["reference_set_identity_sha256"]
            or reference_set["fixture_id"] != lock["fixture_id"]):
        raise ArchiveError("Sealed reference set identity or fixture differs")
    bindings = {row["case_id"]: row for row in reference_set["references"]}
    cases = lock["protocol"]["cases"]
    if set(bindings) != {case["case_id"] for case in cases}:
        raise ArchiveError("Reference case axis differs from the complete campaign")
    all_leads = []
    comparison = []
    for case in cases:
        case_id = case["case_id"]
        fresh = _verify_seal(_load(staging, f"verification/{case_id}/REFERENCE.json"), "reference_identity_sha256")
        _host_case(staging / "capture", case_id, lock)
        _warning_policy(lock, staging / "capture", case)
        if (fresh.get("case_id") != case_id or fresh.get("protocol_identity_sha256") != lock["protocol_identity_sha256"]
                or fresh.get("admission_identity_sha256") != lock["admission"]["admission_identity_sha256"]
                or any(fresh.get(field) != lock[field] for field in ("runtime_identity_sha256", "assembly_identity_sha256", "fixture_id"))
                or fresh.get("raw_outputs") != _inventory(staging / "capture" / "attempts" / case_id / "outputs")):
            raise ArchiveError("New audited case namespace or complete raw-output binding differs")
        if (_binding(staging, f"verification/{case_id}/arrays.json") != fresh["arrays"]
                or _binding(staging, f"verification/{case_id}/lead_reference.json") != fresh["lead_reference"]):
            raise ArchiveError("New audited arrays or lead extraction changed")
        old = _verify_seal(_load(expected_root, f"{case_id}/REFERENCE.json"), "reference_identity_sha256")
        if (old["reference_identity_sha256"] != bindings[case_id]["reference_identity_sha256"]
                or old["protocol_identity_sha256"] != reference_set["protocol_identity_sha256"]
                or any(old[field] != lock[field] for field in ("runtime_identity_sha256", "assembly_identity_sha256", "fixture_id"))):
            raise ArchiveError("Reference scientific/runtime/case identity differs")
        for filename, field in (("REFERENCE.json", "reference_report"), ("arrays.json", "arrays"), ("lead_reference.json", "lead_reference")):
            if _binding(expected_root, f"{case_id}/{filename}") != bindings[case_id][field]:
                raise ArchiveError("Reference report, complete arrays, or lead payload changed")
        expected = _load(expected_root, f"{case_id}/arrays.json", MAX_ARRAY_BYTES)
        actual = _load(staging, f"verification/{case_id}/arrays.json", MAX_ARRAY_BYTES)
        # Only the prospective run's protocol identifier may differ in this
        # envelope. Every other field, unit, axis, clock and numeric value is exact.
        expected.pop("protocol_identity_sha256", None)
        actual.pop("protocol_identity_sha256", None)
        if actual != expected:
            raise ArchiveError("Complete physical output arrays differ from the sealed reference")
        del expected, actual
        leads = _load(staging, f"verification/{case_id}/lead_reference.json")
        if leads != _load(expected_root, f"{case_id}/lead_reference.json"):
            raise ArchiveError("Independent complete lead extraction differs from the reference")
        all_leads.extend(leads)
        comparison.append({"case_id": case_id, "all_arrays_exactly_equal": True,
                           "reference_identity_sha256": old["reference_identity_sha256"],
                           "generated_issue_lead_rows": len(leads)})
    if all_leads != _load(expected_root, "set/lead_reference.json"):
        raise ArchiveError("Complete set lead extraction differs")
    report = {"schema_version": "campaign-reference-comparison/0.1", **_namespace(lock), "cases": comparison,
              "all_complete_arrays_exactly_equal": True,
              "comparison": "exact serialized values; only protocol envelope identity may differ"}
    if publish:
        _write(staging, "comparison.json", report)
    elif _load(staging, "comparison.json") != report:
        raise ArchiveError("Stored comparison differs from the freshly verified full arrays")
    return all_leads


def _products(lock: dict, all_leads: list[dict]) -> tuple[list[dict], list[dict]]:
    """Build keys independently from the campaign before retained projection."""
    expected = list(iter_expected_rows(lock["campaign"], "generated"))
    selected_feature = lock["protocol"]["selected_routing_feature_id"]
    if any(selected_feature != "wb-" + row["reach_id"] for row in expected):
        raise ArchiveError("Campaign reach does not map exactly to the locked routed feature")
    indexed = {}
    for row in all_leads:
        key = (row.get("issue_time_utc"), row.get("lead_hours"), row.get("valid_time_utc"), row.get("routing_feature_id"))
        if key in indexed:
            raise ArchiveError("Duplicate generated issue/lead/valid-time key")
        indexed[key] = row
    expected_keys = {(row["issue_time_utc"], row["lead_hour"], row["valid_time_utc"], selected_feature) for row in expected}
    if set(indexed) != expected_keys or len(all_leads) != len(expected) or len(expected) != 36:
        raise ArchiveError("All36 independently expected issue/lead keys are required before projection")
    generated = []
    for row in expected:
        raw = indexed[(row["issue_time_utc"], row["lead_hour"], row["valid_time_utc"], selected_feature)]
        value = raw["flow_m3_s"]
        if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
            raise ArchiveError("Generated routed flow is nonfinite or negative")
        generated.append({**row, "routing_feature_id": selected_feature,
                          "flow_m3_s": value, "flow_units": "m3 s-1", "quality_mask": "unqualified_diagnostic",
                          **_namespace(lock)})
    retained_keys = {(row["issue_time_utc"], row["lead_hour"], row["valid_time_utc"], row["reach_id"])
                     for row in iter_expected_rows(lock["campaign"], "retained")}
    retained = [row for row in generated if (row["issue_time_utc"], row["lead_hour"], row["valid_time_utc"], row["reach_id"]) in retained_keys]
    return generated, retained


def _csv(rows: list[dict], *, result_identity: str | None = None) -> bytes:
    stream = io.StringIO(newline="")
    fields = [*PRODUCT_FIELDS, *(["result_identity_sha256"] if result_identity is not None else [])]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, **({"result_identity_sha256": result_identity} if result_identity is not None else {})})
    return stream.getvalue().encode("ascii")


def _pointer(root: Path, commit_name: str, manifest: dict) -> dict:
    directory = root / "commits" / commit_name
    pointer = _seal({"schema_version": "campaign-result-current/0.1", "commit": f"commits/{commit_name}",
                     "result_identity_sha256": manifest["result_identity_sha256"],
                     "manifest": _binding(directory, "MANIFEST.json")}, "pointer_identity_sha256")
    # Exclusive hard-link publication is atomic and never overwrites an
    # existing pointer. The temporary inode and directory are flushed first.
    temporary = f".CURRENT-{uuid.uuid4().hex}.json"
    _write(root, temporary, pointer)
    descriptor = _directory(root)
    try:
        os.link(temporary, "CURRENT.json", src_dir_fd=descriptor, dst_dir_fd=descriptor, follow_symlinks=False)
        os.fsync(descriptor)
    finally:
        os.unlink(temporary, dir_fd=descriptor)
        os.close(descriptor)
    return pointer


def _rename_no_replace(source: str, destination: str, source_fd: int, destination_fd: int) -> None:
    """Publish a whole directory atomically without replacing even an empty one."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = getattr(library, "renameatx_np", None)
        flag = 4  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        function = getattr(library, "renameat2", None)
        flag = 1  # RENAME_NOREPLACE
    else:
        function = None
        flag = 0
    if function is None:
        raise ArchiveError("This platform lacks atomic directory publication without replacement")
    function.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    function.restype = ctypes.c_int
    if function(source_fd, os.fsencode(source), destination_fd, os.fsencode(destination), flag) != 0:
        code = ctypes.get_errno()
        if code in (errno.EEXIST, errno.ENOTEMPTY):
            raise ArchiveError("Publication destination already exists; it was not overwritten")
        raise ArchiveError(f"Atomic directory publication failed: {os.strerror(code)}")


def _preflight_publication(destination: Path, minimum_host_free_bytes: int = 8 * 1024 ** 3) -> None:
    if os.path.lexists(destination):
        raise ArchiveError("Publication destination exists; overwrite is unsupported")
    descriptor = _directory(destination.parent)
    try:
        space = os.fstatvfs(descriptor)
        if space.f_bavail * space.f_frsize < minimum_host_free_bytes:
            raise ArchiveError("Host free-space floor prevents archive/export publication")
    finally:
        os.close(descriptor)
    library = ctypes.CDLL(None, use_errno=True)
    symbol = "renameatx_np" if sys.platform == "darwin" else "renameat2" if sys.platform.startswith("linux") else ""
    if not symbol or not hasattr(library, symbol):
        raise ArchiveError("This platform lacks atomic directory publication without replacement")


def preflight_archive_destination(execution_root: Path, archive_root: Path, asset_root: Path) -> dict:
    """Check archival viability read-only, before any model process is launched."""
    execution_root, archive_root, asset_root = map(lambda path: Path(path).absolute(), (execution_root, archive_root, asset_root))
    for source in (execution_root, asset_root):
        if archive_root == source or source in archive_root.parents or archive_root in source.parents:
            raise ArchiveError("Capture, input assets and archive directories must be separate")
    _preflight_publication(archive_root)
    return {"archive_destination_verified": True, "new_model_invocations": 0, "destination_created": False}


def commit_result(lock: dict, execution_root: Path, archive_root: Path, asset_root: Path) -> dict:
    """Audit fresh captured stages, compare full references, and publish once.

    Failed/incomplete attempts remain untouched. An interrupted staging tree
    does not establish completion. Publication never replaces another commit.
    """
    from .execution_lock import verify_execution_assets
    _lock(lock)
    verified_assets = verify_execution_assets(lock, Path(asset_root))
    if verified_assets.get("verified") is not True:
        raise ArchiveError("Execution/reference asset verification did not pass")
    execution_root, archive_root, asset_root = map(lambda p: Path(p).absolute(), (execution_root, archive_root, asset_root))
    capture = _capture(execution_root, lock)
    for source in (execution_root, asset_root):
        if archive_root == source or source in archive_root.parents or archive_root in source.parents:
            raise ArchiveError("Capture, input assets and archive directories must be separate")
    if not archive_root.exists():
        _preflight_publication(archive_root)
        parent = _directory(archive_root.parent)
        try:
            os.mkdir(archive_root.name, 0o700, dir_fd=parent)
            os.fsync(parent)
        finally:
            os.close(parent)
    root_fd = _directory(archive_root)
    os.close(root_fd)
    if (archive_root / "CURRENT.json").exists():
        existing = verify_result(archive_root, lock)
        if existing["capture_identity_sha256"] != capture["capture_identity_sha256"]:
            raise ArchiveError("Another captured execution is already committed in this archive")
        return existing
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=archive_root))
    # Staging is intentionally retained on every failure for diagnosis. It is
    # never exposed through CURRENT or described as a committed product.
    _write(staging, "LOCK.json", lock)
    _copy_inventory(execution_root, staging, _inventory(execution_root), "capture/")
    _capture(staging / "capture", lock)
    reference_root = asset_root / lock["bundle_paths"]["reference_root"]
    _copy_inventory(reference_root, staging, lock["reference_files"], "expected_references/")
    _audit_capture(lock, staging)
    generated, retained = _products(lock, _compare_references(lock, staging))
    _write(staging, "generated.json", generated)
    _write(staging, "retained.json", retained)
    _write_bytes(staging, "generated.csv", _csv(generated))
    _write_bytes(staging, "retained.csv", _csv(retained))
    _fsync_tree(staging)
    manifest = _seal({"schema_version": "campaign-result-commit/0.1", **_namespace(lock),
                      "capture_identity_sha256": capture["capture_identity_sha256"],
                      "files": _inventory(staging), "generated_rows": len(generated), "retained_rows": len(retained),
                      "complete_case_count": 3, "all_complete_arrays_exactly_equal": True,
                      "completion": "verified_diagnostic_result", "scientific_validation_claimed": False,
                      "release_qualified": False}, "result_identity_sha256")
    _write(staging, "MANIFEST.json", manifest)
    _write(staging, "COMMITTED.json", {"schema_version": "campaign-result-marker/0.1",
                                       "result_identity_sha256": manifest["result_identity_sha256"],
                                       "manifest": _binding(staging, "MANIFEST.json")})
    _fsync_tree(staging)
    root_fd = _directory(archive_root)
    try:
        try:
            os.mkdir("commits", 0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        commits_fd = resident._open_child(root_fd, "commits", directory=True)
        try:
            name = manifest["result_identity_sha256"]
            # Result identities are content-addressed. A matching orphan from
            # interrupted pointer publication is freshly verified before reuse.
            destination = archive_root / "commits" / name
            if destination.exists():
                _verify_commit(destination, lock)
                if _load(destination, "MANIFEST.json") != manifest:
                    raise ArchiveError("An incompatible commit already exists")
            else:
                _rename_no_replace(staging.name, name, root_fd, commits_fd)
                os.fsync(commits_fd)
                os.fsync(root_fd)
        finally:
            os.close(commits_fd)
    finally:
        os.close(root_fd)
    _pointer(archive_root, manifest["result_identity_sha256"], manifest)
    return verify_result(archive_root, lock)


def _verify_commit(root: Path, expected_lock: dict | None) -> tuple[dict, dict]:
    manifest = _verify_seal(_load(root, "MANIFEST.json"), "result_identity_sha256")
    if manifest.get("schema_version") != "campaign-result-commit/0.1" or manifest.get("completion") != "verified_diagnostic_result":
        raise ArchiveError("Commit metadata does not describe a completed diagnostic result")
    lock = _lock(_load(root, "LOCK.json"))
    _same_namespace(manifest, lock)
    if expected_lock is not None:
        _lock(expected_lock)
        _same_namespace(manifest, expected_lock)
    marker = _load(root, "COMMITTED.json")
    if marker != {"schema_version": "campaign-result-marker/0.1", "result_identity_sha256": manifest["result_identity_sha256"],
                  "manifest": _binding(root, "MANIFEST.json")}:
        raise ArchiveError("Commit marker or manifest file changed")
    if _inventory(root, exclude=frozenset({"MANIFEST.json", "COMMITTED.json"})) != manifest["files"]:
        raise ArchiveError("Committed payload is missing, corrupt, unlisted, or linked")
    capture = _capture(root / "capture", lock)
    if manifest["capture_identity_sha256"] != capture["capture_identity_sha256"]:
        raise ArchiveError("Commit capture identity differs")
    for item in lock["reference_files"]:
        if _binding(root / "expected_references", item["path"]) != {key: item[key] for key in ("bytes", "sha256")}:
            raise ArchiveError("Bound reference files changed in the archive")
    # These rechecks are independent of the stored row counts and CSV keys.
    generated, retained = _products(lock, _compare_references(lock, root, publish=False))
    if (_load(root, "generated.json") != generated or _load(root, "retained.json") != retained
            or _binding(root, "generated.csv") != {"bytes": len(_csv(generated)), "sha256": hashlib.sha256(_csv(generated)).hexdigest()}
            or _binding(root, "retained.csv") != {"bytes": len(_csv(retained)), "sha256": hashlib.sha256(_csv(retained)).hexdigest()}
            or manifest["generated_rows"] != len(generated) or manifest["retained_rows"] != len(retained)):
        raise ArchiveError("Generated/retained products differ from independent complete keys")
    return manifest, lock


def verify_result(archive_root: Path, expected_lock: dict | None = None) -> dict:
    """Freshly verify every committed payload; metadata is not a signature."""
    root = Path(archive_root).absolute()
    pointer = _verify_seal(_load(root, "CURRENT.json"), "pointer_identity_sha256")
    identity = pointer.get("result_identity_sha256")
    if (pointer.get("schema_version") != "campaign-result-current/0.1" or not isinstance(identity, str)
            or not re.fullmatch(r"[0-9a-f]{64}", identity) or pointer.get("commit") != f"commits/{identity}"):
        raise ArchiveError("Current pointer path or identity differs")
    commit = root / "commits" / identity
    if _binding(commit, "MANIFEST.json") != pointer.get("manifest"):
        raise ArchiveError("Current manifest differs from its atomic pointer")
    manifest, _ = _verify_commit(commit, expected_lock)
    if manifest["result_identity_sha256"] != identity:
        raise ArchiveError("Current pointer and verified commit identities differ")
    return {"schema_version": "campaign-result-verification/0.1", **_namespace(manifest),
            "result_identity_sha256": identity, "capture_identity_sha256": manifest["capture_identity_sha256"],
            "status": "verified", "completed": True, "generated_rows": manifest["generated_rows"],
            "retained_rows": manifest["retained_rows"], "files_verified": len(manifest["files"]),
            "scientific_validation_claimed": False, "release_qualified": False,
            "scope": "Local bytes and receipt consistency; no authenticity signature or hydrologic skill claim."}


def archive_status(archive_root: Path, expected_lock: dict | None = None) -> dict:
    """Read-only status never calls a captured or interrupted attempt complete."""
    root = Path(archive_root).absolute()
    if not root.exists():
        return {"schema_version": "campaign-result-status/0.1", "status": "absent", "completed": False}
    descriptor = _directory(root)
    try:
        names = os.listdir(descriptor)
        if "CURRENT.json" not in names:
            return {"schema_version": "campaign-result-status/0.1", "status": "incomplete", "completed": False,
                    "staging_transactions": sum(name.startswith(".staging-") for name in names)}
    finally:
        os.close(descriptor)
    return verify_result(root, expected_lock)


def export_result(archive_root: Path, destination: Path, expected_lock: dict | None = None) -> dict:
    """Publish a new verified directory with full evidence and retained CSV."""
    verified = verify_result(archive_root, expected_lock)
    source = Path(archive_root).absolute() / "commits" / verified["result_identity_sha256"]
    destination = Path(destination).absolute()
    archive_root = Path(archive_root).absolute()
    if archive_root == destination or archive_root in destination.parents or destination in archive_root.parents:
        raise ArchiveError("Export must not overlap its immutable archive")
    _preflight_publication(destination)
    temporary = Path(tempfile.mkdtemp(prefix=".export-", dir=destination.parent))
    _copy_inventory(source, temporary, _inventory(source), "result/")
    manifest, lock = _verify_commit(temporary / "result", expected_lock)
    rows = _load(temporary / "result", "retained.json")
    _write_bytes(temporary, "forecast.csv", _csv(rows, result_identity=manifest["result_identity_sha256"]))
    report = _seal({"schema_version": "campaign-result-export/0.1", **_namespace(lock),
                    "result_identity_sha256": manifest["result_identity_sha256"],
                    "generated_rows_verified": manifest["generated_rows"], "retained_rows": len(rows),
                    "files": _inventory(temporary), "scientific_validation_claimed": False}, "export_identity_sha256")
    _write(temporary, "EXPORT.json", report)
    _fsync_tree(temporary)
    parent = _directory(destination.parent)
    try:
        _rename_no_replace(temporary.name, destination.name, parent, parent)
        os.fsync(parent)
    finally:
        os.close(parent)
    return report
