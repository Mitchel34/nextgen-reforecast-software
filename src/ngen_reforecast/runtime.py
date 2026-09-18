"""Offline inspection of the one historical runtime reference; never a launcher.

Only the exact reviewed profile is admitted. Its identity binds metadata, not a
qualified public distribution. All native and fixture reads require an explicit
local root and a bounded, symlink-free, resident regular file.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
from typing import Any


class RuntimeProfileError(ValueError):
    """An unsupported, modified, unreadable or unsafe profile was supplied."""


_PROFILE_SHA256 = "1b89d80a6e64088c96ef47e2aaead969528fc63039cc260e9d6392e44a3e66a8"
_MAX_PROFILE_BYTES = 1_048_576
_CHUNK_BYTES = 65_536
_DATALESS_FLAG = getattr(stat, "UF_DATALESS", 0x40000000)


class _InspectionFailure(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _is_dataless(info: os.stat_result) -> bool:
    # Windows offline/recall flags are conservative additional rejection flags.
    return bool(getattr(info, "st_flags", 0) & _DATALESS_FLAG) or bool(
        getattr(info, "st_file_attributes", 0) & (0x1000 | 0x40000 | 0x400000)
    )


def _snapshot(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _flags(directory: bool = False) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise _InspectionFailure(
            "SAFE_INSPECTION_UNAVAILABLE",
            "This host does not provide the required no-follow directory inspection API.",
        )
    return os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_DIRECTORY if directory else 0)


def _open_child(parent_fd: int, name: str, *, directory: bool) -> int:
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode):
        raise _InspectionFailure("SYMLINK_REJECTED", "Symbolic links are not admitted in an inspection path.")
    if _is_dataless(before):
        raise _InspectionFailure("DATALESS_REJECTED", "A dataless or offline entry was not opened; restore it separately.")
    if directory and not stat.S_ISDIR(before.st_mode):
        raise _InspectionFailure("DIRECTORY_REQUIRED", "An inspection path component is not a directory.")
    if not directory and not stat.S_ISREG(before.st_mode):
        raise _InspectionFailure("REGULAR_FILE_REQUIRED", "Only resident regular files can be inspected.")
    descriptor = os.open(name, _flags(directory), dir_fd=parent_fd)
    try:
        after = os.fstat(descriptor)
        if _is_dataless(after):
            raise _InspectionFailure("DATALESS_REJECTED", "An offline entry changed during inspection and was not read.")
        if _snapshot(before) != _snapshot(after):
            raise _InspectionFailure("FILE_CHANGED", "An entry changed during inspection; rerun against stable assets.")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_directory(path: Path) -> int:
    absolute = path.absolute()
    if ".." in absolute.parts:
        raise _InspectionFailure("PATH_ESCAPE_REJECTED", "Parent traversal is not admitted in an inspection path.")
    descriptor = os.open(absolute.anchor, _flags(directory=True))
    try:
        for name in absolute.parts[1:]:
            next_fd = _open_child(descriptor, name, directory=True)
            os.close(descriptor)
            descriptor = next_fd
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _relative_parts(relative: str) -> tuple[str, ...]:
    path = PurePosixPath(relative)
    if (
        not relative or path.is_absolute() or ".." in path.parts
        or "\\" in relative or str(path) != relative or ":" in relative
    ):
        raise _InspectionFailure("PATH_ESCAPE_REJECTED", "Asset paths must be normalized relative POSIX paths.")
    return path.parts


def _open_asset(root_fd: int, relative: str) -> int:
    parts = _relative_parts(relative)
    parent_fd = os.dup(root_fd)
    try:
        for name in parts[:-1]:
            next_fd = _open_child(parent_fd, name, directory=True)
            os.close(parent_fd)
            parent_fd = next_fd
        return _open_child(parent_fd, parts[-1], directory=False)
    finally:
        os.close(parent_fd)


def _read_bounded(descriptor: int, size: int, *, digest_only: bool) -> tuple[str | bytes, int]:
    """Read at most the admitted stat size, and reject races and early EOF."""
    before = os.fstat(descriptor)
    hasher = hashlib.sha256()
    chunks = []
    read_bytes = 0
    while read_bytes < size:
        chunk = os.read(descriptor, min(_CHUNK_BYTES, size - read_bytes))
        if not chunk:
            break
        read_bytes += len(chunk)
        hasher.update(chunk)
        if not digest_only:
            chunks.append(chunk)
    after = os.fstat(descriptor)
    if read_bytes != size or _snapshot(before) != _snapshot(after):
        raise _InspectionFailure("FILE_CHANGED", "An asset changed while reading; its hash is not accepted.")
    return (hasher.hexdigest() if digest_only else b"".join(chunks), read_bytes)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise RuntimeProfileError("Duplicate JSON object keys are not admitted in a runtime profile.")
        obj[key] = value
    return obj


def _load_profile(path: Path) -> dict[str, Any]:
    root_fd = None
    descriptor = None
    try:
        root_fd = _open_directory(path.parent)
        descriptor = _open_asset(root_fd, path.name)
        size = os.fstat(descriptor).st_size
        if size > _MAX_PROFILE_BYTES:
            raise RuntimeProfileError("Runtime profile exceeds the 1 MiB admission bound.")
        raw, _ = _read_bounded(descriptor, size, digest_only=False)
        profile = json.loads(raw, object_pairs_hook=_unique_object)
        canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
        if hashlib.sha256(canonical).hexdigest() != _PROFILE_SHA256:
            raise RuntimeProfileError(
                "Unsupported or modified runtime profile. Use the exact nextgen-arm64-v3 historical profile; "
                "changes to its identities or qualification status require a reviewed new implementation."
            )
        return profile
    except RuntimeProfileError:
        raise
    except _InspectionFailure as exc:
        raise RuntimeProfileError(f"Runtime profile rejected: {exc.code}: {exc.message}") from exc
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        # Never surface host paths from OSError in a public report.
        raise RuntimeProfileError("Runtime profile could not be read as a safe, bounded JSON object.") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if root_fd is not None:
            os.close(root_fd)


def _inspect_asset(root_fd: int, asset: dict[str, Any], remaining: int, per_file: int) -> dict[str, Any]:
    check: dict[str, Any] = {"code": "ASSET", "path": asset["path"], "role": asset["role"], "status": "blocked", "hashed_bytes": 0}
    descriptor = None
    admitted = 0
    try:
        descriptor = _open_asset(root_fd, asset["path"])
        size = os.fstat(descriptor).st_size
        check["observed_bytes"] = size
        if size > per_file:
            raise _InspectionFailure("FILE_HASH_BOUND_EXCEEDED", "File exceeds the admitted per-file hash bound; no content was read.")
        if asset["bytes"] is not None and size != asset["bytes"]:
            raise _InspectionFailure("ASSET_SIZE_MISMATCH", "File size does not match the historical reference; no content was read.")
        if size > remaining:
            raise _InspectionFailure("TOTAL_HASH_BOUND_EXCEEDED", "The remaining aggregate hash budget cannot cover this file; no content was read.")
        admitted = size
        observed, read_bytes = _read_bounded(descriptor, size, digest_only=True)
        check.update(observed_sha256=observed, hashed_bytes=read_bytes)
        if asset["sha256"] is None:
            raise _InspectionFailure("ASSET_IDENTITY_UNRESOLVED", "Content was hashed, but the historical manifest supplies no expected hash; this is not identity verification.")
        check["expected_sha256"] = asset["sha256"]
        if observed != asset["sha256"]:
            raise _InspectionFailure("ASSET_HASH_MISMATCH", "Content does not match the pinned historical SHA-256 identity.")
        check.update(status="passed", code="ASSET_HASH_VERIFIED", message="Resident bytes match the pinned historical identity.")
    except FileNotFoundError:
        check.update(code="ASSET_MISSING", message="Required staged asset is absent; restore the exact authorized bytes separately.")
    except _InspectionFailure as exc:
        check.update(code=exc.code, message=exc.message)
        if admitted and not check["hashed_bytes"]:
            # Reserve the full admitted size after a failed/raced read. This
            # conservative accounting keeps the whole inspection bounded.
            check["hashed_bytes"] = admitted
    except OSError:
        check.update(code="ASSET_READ_FAILED", message="The staged asset could not be inspected safely.")
        check["hashed_bytes"] = admitted
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return check


def inspect_runtime(profile_path: Path, asset_root: Path | None = None) -> dict[str, Any]:
    """Return an offline, non-executable closure report for the exact V3 profile.

    No implicit source/cache discovery, network, subprocess, container inspection
    or model activity occurs. Local root paths are never included in the report.
    A matching historical binary cannot turn ``execution_ready`` true.
    """
    profile = _load_profile(Path(profile_path))
    checks: list[dict[str, Any]] = [{"code": "PROFILE_IDENTITY_VERIFIED", "status": "passed", "message": "Exact supported historical profile metadata was verified."}]
    blockers = [{"code": "RUNTIME_UNQUALIFIED", "message": "This profile is a historical reference; no public runtime has been qualified by this package."}]
    observed_system, observed_machine = platform.system(), platform.machine().lower()
    normalized_machine = "aarch64" if observed_machine in {"aarch64", "arm64"} else observed_machine
    platform_matches = observed_system == "Linux" and normalized_machine == "aarch64"
    platform_message = "Host platform matches Linux ARM64; native execution is still unqualified." if platform_matches else "Native execution requires Linux ARM64; this host may still use the offline planner."
    checks.append({"code": "NATIVE_PLATFORM", "status": "passed" if platform_matches else "blocked", "message": platform_message, "observed_system": observed_system, "observed_machine": observed_machine, "required": "linux/arm64"})
    if not platform_matches:
        blockers.append({"code": "UNSUPPORTED_NATIVE_PLATFORM", "message": platform_message})
    checks.append({"code": "ENVIRONMENT_NOT_ACTIVATED", "status": "not_checked", "message": "Container availability, dynamic loading and physical model behavior are not checked by this offline command."})
    limits = profile["inspection_limits"]
    hashed_bytes = 0
    if asset_root is None:
        blockers.append({"code": "ASSET_ROOT_REQUIRED", "message": "Supply an explicit local asset root using the documented staging layout to inspect resident bytes; no source cache is searched."})
    else:
        root_fd = None
        try:
            root_fd = _open_directory(Path(asset_root))
            for asset in profile["assets"][:limits["max_files"]]:
                check = _inspect_asset(root_fd, asset, limits["max_total_hash_bytes"] - hashed_bytes, limits["max_file_bytes"])
                checks.append(check)
                hashed_bytes += check["hashed_bytes"]
                if check["status"] != "passed":
                    blockers.append({"code": check["code"], "message": f"{asset['path']}: {check['message']}"})
        except _InspectionFailure as exc:
            blockers.append({"code": exc.code, "message": exc.message})
        except OSError:
            blockers.append({"code": "ASSET_ROOT_UNAVAILABLE", "message": "The explicit asset root is absent or cannot be opened safely."})
        finally:
            if root_fd is not None:
                os.close(root_fd)
    blockers.extend(profile["qualification_requirements"])
    return {
        "schema_version": "ngen-reforecast-runtime-inspection/v1",
        "profile_id": profile["profile_id"],
        "profile_sha256": _PROFILE_SHA256,
        "status": "blocked",
        "execution_ready": False,
        "evidence_class": "offline_metadata_and_resident_asset_inspection",
        "checks": checks,
        "blockers": blockers,
        "summary": {"assets_expected": len(profile["assets"]), "assets_checked": sum("path" in c for c in checks), "assets_verified": sum(c["code"] == "ASSET_HASH_VERIFIED" for c in checks), "hashed_bytes_or_reserved_after_read_failure": hashed_bytes, "limits": dict(limits)},
        "limitations": ["Matching hashes establish byte identity, not scientific correctness or redistribution rights.", "No build, middleware-load, simulation or failure/replay qualification was executed.", "Routing state alone cannot restore land/coupler/provider state."],
    }
