"""Bounded resident bundle inspection and private staging, never model admission.

Callers choose every source root/candidate explicitly. Expected identities must
come from a trusted manifest; newly calculated hashes cannot establish them.
No discovery, hydration, network request, inherited import or subprocess occurs.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from .runtime import (
    _InspectionFailure, _open_asset, _open_child, _open_directory,
    _read_bounded, _relative_parts, _unique_object,
)

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ASSETS = 2048
MAX_CANDIDATES = 8192
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")


class BundleError(ValueError):
    """Bundle declarations are malformed or a staging destination is unsafe."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _assets(values: list[dict]) -> list[dict]:
    if not isinstance(values, list) or not 0 < len(values) <= MAX_ASSETS:
        raise BundleError("Declare between one and 2048 assets.")
    result = []
    seen = set()
    for value in values:
        if not isinstance(value, dict):
            raise BundleError("Each asset must be an object.")
        path, digest, size = (value.get(key) for key in ("path", "sha256", "bytes"))
        try:
            if not isinstance(path, str) or path == ".":
                raise BundleError("Each asset needs a relative path.")
            _relative_parts(path)
        except _InspectionFailure as exc:
            raise BundleError(exc.message) from exc
        if path in seen:
            raise BundleError("Duplicate asset paths are not admitted.")
        if digest is not None and (not isinstance(digest, str) or not _SHA.fullmatch(digest)):
            raise BundleError("Expected SHA-256 must be lowercase hexadecimal or null.")
        if size is not None and (type(size) is not int or size < 0):
            raise BundleError("Expected bytes must be a nonnegative integer or null.")
        seen.add(path)
        result.append({"path": path, "sha256": digest, "bytes": size})
    return result


def bind_fixture_contract(raw: bytes, historical_assets: list[dict]) -> dict:
    """Resolve fixture identities only through its already-pinned CONTRACT hash.

    The returned supplement leaves the historical manifest unchanged. It binds
    file identities, not scientific validity, residency or redistribution rights.
    """
    assets = _assets(historical_assets)
    contract_asset = next((a for a in assets if a["path"] == "fixture/CONTRACT.json"), None)
    if contract_asset is None or contract_asset["sha256"] is None:
        raise BundleError("A pre-existing CONTRACT.json identity is required.")
    if not isinstance(raw, bytes) or len(raw) > MAX_FILE_BYTES:
        raise BundleError("Contract must be bounded bytes.")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != contract_asset["sha256"] or (
        contract_asset["bytes"] is not None and len(raw) != contract_asset["bytes"]
    ):
        raise BundleError("Contract does not match its pre-existing identity.")
    try:
        contract = json.loads(raw, object_pairs_hook=_unique_object,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, TypeError, RecursionError) as exc:
        raise BundleError("Contract is not strict JSON.") from exc
    if not isinstance(contract, dict) or contract.get("schema") != "nextgen-real-day-custody-qualification/v3":
        raise BundleError("Unsupported fixture contract schema.")
    files = contract.get("files")
    if not isinstance(files, dict) or not files:
        raise BundleError("Contract must contain file bindings.")
    if any(not isinstance(name, str) or not isinstance(value, dict)
           or set(value) != {"bytes", "sha256"} for name, value in files.items()):
        raise BundleError("Contract members must contain only bytes and sha256.")
    declared = _assets([{"path": "fixture/" + name, **value} for name, value in files.items()])
    if len(declared) != len(files) or any(a["sha256"] is None or a["bytes"] is None for a in declared):
        raise BundleError("Every contract member needs complete size and hash bindings.")
    by_path = {a["path"]: a for a in declared}
    if set(by_path) - {a["path"] for a in assets}:
        raise BundleError("Contract contains members absent from the historical inventory.")
    resolved = 0
    output = []
    for asset in assets:
        item = dict(asset)
        if asset["path"] in by_path:
            bound = by_path[asset["path"]]
            for key in ("sha256", "bytes"):
                if asset[key] is not None and asset[key] != bound[key]:
                    raise BundleError("Contract conflicts with a historical member binding.")
            resolved += asset["sha256"] is None
            item.update(bound, identity_basis="pinned_contract_member")
        else:
            item["identity_basis"] = "historical_manifest"
        output.append(item)
    payload = {
        "schema_version": "fixture-identity-supplement/0.1",
        "contract_sha256": digest,
        "historical_assets_sha256": hashlib.sha256(_canonical(assets)).hexdigest(),
        "resolved_unknown_hashes": resolved,
        "unresolved_hashes": sum(a["sha256"] is None for a in output),
        "assets": output,
        "input_bytes_verified": False,
        "scientific_semantics_verified": False,
        "execution_ready": False,
    }
    return {**payload, "supplement_sha256": hashlib.sha256(_canonical(payload)).hexdigest()}


def _write_member(destination_fd: int, path: str, raw: bytes) -> None:
    """Write a fresh private file, then verify the written bytes; never hardlink."""
    parts = _relative_parts(path)
    parent_fd = os.dup(destination_fd)
    fd = None
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=parent_fd)
            except FileExistsError:
                pass
            child = _open_child(parent_fd, part, directory=True)
            os.close(parent_fd)
            parent_fd = child
        fd = os.open(parts[-1], os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent_fd)
        remaining = memoryview(raw)
        while remaining:
            count = os.write(fd, remaining)
            if count <= 0:
                raise BundleError("Private staging write did not complete.")
            remaining = remaining[count:]
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        observed, _ = _read_bounded(fd, len(raw), digest_only=True)
        if observed != hashlib.sha256(raw).hexdigest():
            raise BundleError("Private staged bytes failed verification.")
        os.fchmod(fd, 0o400)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent_fd)


def _inspect(assets: list[dict], source_roots: Mapping[str, Path],
             candidates: Mapping[str, list[dict]] | None, *,
             max_file_bytes: int, max_total_bytes: int, destination_fd: int | None) -> dict:
    assets = _assets(assets)
    if (type(max_file_bytes) is not int or type(max_total_bytes) is not int
            or not 0 < max_file_bytes <= MAX_FILE_BYTES
            or not 0 < max_total_bytes <= MAX_TOTAL_BYTES):
        raise BundleError("Inspection limits must be positive and within 16 MiB/file and 128 MiB total.")
    if not source_roots or len(source_roots) > 32 or any(not isinstance(k, str) or not _ALIAS.fullmatch(k) for k in source_roots):
        raise BundleError("Provide one to 32 short source aliases.")
    paths = {a["path"] for a in assets}
    candidates = candidates if candidates is not None else {
        a["path"]: [{"root": alias, "path": a["path"]} for alias in source_roots] for a in assets
    }
    if not isinstance(candidates, Mapping) or set(candidates) - paths:
        raise BundleError("Candidate mappings must refer to declared asset paths.")
    if any(not isinstance(rows, list) for rows in candidates.values()):
        raise BundleError("Candidate lists are required.")
    if sum(len(rows) for rows in candidates.values()) > MAX_CANDIDATES:
        raise BundleError("Candidate count exceeds 8192.")
    for rows in candidates.values():
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"root", "path"} or row["root"] not in source_roots:
                raise BundleError("Each candidate needs a declared source alias and relative path.")
            try:
                if not isinstance(row["path"], str) or row["path"] == ".":
                    raise TypeError
                _relative_parts(row["path"])
            except (TypeError, _InspectionFailure) as exc:
                raise BundleError("Candidate paths must be normalized relative paths.") from exc
    root_fds, root_errors = {}, {}
    rows = []
    read_budget = 0
    try:
        for alias, path in source_roots.items():
            try:
                root_fds[alias] = _open_directory(Path(path))
            except FileNotFoundError:
                root_errors[alias] = "ASSET_MISSING"
            except _InspectionFailure as exc:
                root_errors[alias] = exc.code
            except OSError:
                root_errors[alias] = "SOURCE_ROOT_UNAVAILABLE"
        for asset in assets:
            item = {**asset, "status": "missing", "code": "ASSET_MISSING", "attempts": [], "staged": False}
            for candidate in candidates.get(asset["path"], []):
                attempt = {"source_alias": candidate["root"], "source_relative_path": candidate["path"], "read_bytes_or_reserved": 0}
                item["attempts"].append(attempt)
                fd = None
                try:
                    if candidate["root"] in root_errors:
                        raise _InspectionFailure(root_errors[candidate["root"]], "Source root unavailable.")
                    fd = _open_asset(root_fds[candidate["root"]], candidate["path"])
                    size = os.fstat(fd).st_size
                    attempt["observed_bytes"] = size
                    if size > max_file_bytes:
                        raise _InspectionFailure("FILE_HASH_BOUND_EXCEEDED", "File bound exceeded.")
                    if asset["bytes"] is not None and size != asset["bytes"]:
                        raise _InspectionFailure("ASSET_SIZE_MISMATCH", "Size mismatch.")
                    if size > max_total_bytes - read_budget:
                        raise _InspectionFailure("TOTAL_HASH_BOUND_EXCEEDED", "Total bound exceeded.")
                    read_budget += size
                    attempt["read_bytes_or_reserved"] = size
                    raw, _ = _read_bounded(fd, size, digest_only=False)
                    digest = hashlib.sha256(raw).hexdigest()
                    attempt["observed_sha256"] = digest
                    if asset["sha256"] is None:
                        raise _InspectionFailure("ASSET_IDENTITY_UNRESOLVED", "No expected identity.")
                    if digest != asset["sha256"]:
                        raise _InspectionFailure("ASSET_HASH_MISMATCH", "Hash mismatch.")
                    if destination_fd is not None:
                        _write_member(destination_fd, asset["path"], raw)
                    attempt["code"] = "ASSET_HASH_VERIFIED"
                    item.update(status="verified", code="ASSET_HASH_VERIFIED",
                                observed_sha256=digest, source_alias=candidate["root"],
                                source_relative_path=candidate["path"])
                    if destination_fd is not None:
                        item["staged"] = True
                    break
                except FileNotFoundError:
                    attempt["code"] = "ASSET_MISSING"
                except _InspectionFailure as exc:
                    attempt["code"] = exc.code
                except OSError:
                    attempt["code"] = "ASSET_READ_OR_STAGE_FAILED"
                finally:
                    if fd is not None:
                        os.close(fd)
            if item["status"] != "verified":
                codes = [a["code"] for a in item["attempts"]]
                code = next((c for c in codes if c != "ASSET_MISSING"), "ASSET_MISSING")
                item.update(code=code, status={
                    "ASSET_MISSING": "missing", "DATALESS_REJECTED": "dataless",
                    "ASSET_HASH_MISMATCH": "hash_mismatch", "ASSET_SIZE_MISMATCH": "size_mismatch",
                    "ASSET_IDENTITY_UNRESOLVED": "unbound",
                }.get(code, "refused"))
            rows.append(item)
    finally:
        for fd in root_fds.values():
            os.close(fd)
    verified = sum(r["status"] == "verified" for r in rows)
    staged = sum(r["staged"] for r in rows)
    complete = verified == len(assets) and (destination_fd is None or staged == len(assets))
    return {
        "schema_version": "resident-bundle-inspection/0.1",
        "manifest_sha256": hashlib.sha256(_canonical(assets)).hexdigest(),
        "status": "byte_complete" if complete else "incomplete",
        "input_bytes_verified": complete,
        "scientific_semantics_verified": False,
        "execution_ready": False,
        "summary": {"expected_assets": len(assets), "verified_assets": verified,
                    "staged_assets": staged, "unresolved_expected_hashes": sum(a["sha256"] is None for a in assets),
                    "source_bytes_read_or_reserved": read_budget, "status_counts": dict(sorted(Counter(r["status"] for r in rows).items()))},
        "limits": {"max_file_bytes": max_file_bytes, "max_total_bytes": max_total_bytes},
        "assets": rows,
        "limitations": ["Matching bytes do not establish scientific correctness, source authenticity or redistribution rights.",
                        "A complete byte inventory does not admit physical execution."],
    }


def inventory_bundle(assets: list[dict], source_roots: Mapping[str, Path],
                     candidates: Mapping[str, list[dict]] | None = None, *,
                     max_file_bytes: int = MAX_FILE_BYTES, max_total_bytes: int = MAX_TOTAL_BYTES) -> dict:
    """Inspect explicit resident candidates without modifying sources or outputs."""
    return _inspect(assets, source_roots, candidates, max_file_bytes=max_file_bytes,
                    max_total_bytes=max_total_bytes, destination_fd=None)


def stage_bundle(assets: list[dict], source_roots: Mapping[str, Path], destination: Path,
                 candidates: Mapping[str, list[dict]] | None = None, *,
                 max_file_bytes: int = MAX_FILE_BYTES, max_total_bytes: int = MAX_TOTAL_BYTES) -> dict:
    """Stage only verified bytes into a fresh private directory; never overwrite.

    Partial staging is retained and explicitly incomplete. Callers must keep
    inherited material outside publication paths until its rights are resolved.
    The destination parent must already exist and be symlink-free/resident.
    """
    destination = Path(destination).absolute()
    for root in source_roots.values():
        if destination.is_relative_to(Path(root).absolute()):
            raise BundleError("Staging destinations cannot be inside a source root.")
    parent_fd = fd = None
    try:
        _relative_parts(destination.name)
        parent_fd = _open_directory(destination.parent)
        os.mkdir(destination.name, mode=0o700, dir_fd=parent_fd)
        fd = _open_child(parent_fd, destination.name, directory=True)
        return _inspect(assets, source_roots, candidates, max_file_bytes=max_file_bytes,
                        max_total_bytes=max_total_bytes, destination_fd=fd)
    except (OSError, _InspectionFailure) as exc:
        raise BundleError("Private destination must be a new directory under a safe existing parent.") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if parent_fd is not None:
            os.close(parent_fd)
