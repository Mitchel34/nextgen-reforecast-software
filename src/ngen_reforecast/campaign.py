"""Strict, offline campaign planning. This module never launches a model.

Times label hourly interval starts. A branch issued at I uses provider rows
I..I+17h and produces targets I+1h..I+18h. No state is reconstructed here.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any


class CampaignError(ValueError):
    """The campaign specification is malformed or outside the supported scope."""


SCHEMA_VERSION = "1.0"
MAX_SPEC_BYTES = 4 * 1024 * 1024
MAX_ASSETS = 4096
MAX_LOCATIONS = 1024
MAX_HISTORY_HOURS = 100_000
MAX_ASSET_BYTES = 1024**3
MAX_TOTAL_ASSET_BYTES = 4 * 1024**3
ASSET_ROLES = frozenset({
    "hydrofabric", "realization", "parameters", "historical_forcing",
    "forecast_forcing", "routing_configuration",
})
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:00:00Z\Z")
_REACH = re.compile(r"[1-9][0-9]{0,19}\Z")
_DATALESS = getattr(stat, "UF_DATALESS", 0x40000000)
_HOUR = timedelta(hours=1)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise CampaignError("Campaign must contain only finite JSON values") from exc


def _object(value: Any, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise CampaignError(f"{where} must be an object")
    if set(value) != keys:
        missing = sorted(keys - set(value))
        unexpected = sorted(str(key) for key in set(value) - keys)
        raise CampaignError(f"{where} keys differ: missing={missing}, unexpected={unexpected}")
    return value


def _integer(value: Any, low: int, high: int, where: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise CampaignError(f"{where} must be an integer in [{low}, {high}]")
    return value


def _identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise CampaignError(f"{where} must be a 1..64 character ASCII identifier")
    return value


def _time(value: Any, where: str) -> datetime:
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        raise CampaignError(f"{where} must be canonical hourly UTC YYYY-MM-DDTHH:00:00Z")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise CampaignError(f"{where} is not a valid calendar hour") from exc


def _format_time(value: datetime) -> str:
    # strftime's year width differs across platforms for years before 1000.
    return f"{value.year:04d}-{value.month:02d}-{value.day:02d}T{value.hour:02d}:00:00Z"


def _asset_path(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise CampaignError(f"{where} must be a nonempty relative POSIX path of at most 1024 characters")
    if ("\\" in value or "\x00" in value or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))
            or PurePosixPath(value).is_absolute()):
        raise CampaignError(f"{where} must stay under the campaign directory without dot segments")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise CampaignError(f"{where} cannot contain control characters")
    return value


def _validate(spec: dict) -> dict:
    """Validate structural and cross-field contracts without reading asset bytes."""
    if len(_canonical(spec)) > MAX_SPEC_BYTES:
        raise CampaignError("Campaign exceeds the 4 MiB specification bound")
    _object(spec, {"schema_version", "campaign_id", "profile", "origin_time_utc",
                   "history", "issue_times_utc", "horizon_hours", "domains",
                   "resources"}, "campaign")
    if spec["schema_version"] != SCHEMA_VERSION:
        raise CampaignError("Unsupported schema_version; expected '1.0'")
    _identifier(spec["campaign_id"], "campaign_id")
    if spec["profile"] != "hourly18h":
        raise CampaignError("Only the hourly18h planning profile is supported")
    _integer(spec["horizon_hours"], 18, 18, "horizon_hours")
    origin = _time(spec["origin_time_utc"], "origin_time_utc")
    history = _object(spec["history"], {"start_time_utc", "stop_time_utc"}, "history")
    history_start = _time(history["start_time_utc"], "history.start_time_utc")
    history_stop = _time(history["stop_time_utc"], "history.stop_time_utc")
    if history_start != origin:
        raise CampaignError("history.start_time_utc must equal the unchanged original origin")
    history_hours = (history_stop - origin) // _HOUR
    _integer(history_hours, 1, MAX_HISTORY_HOURS, "historical interval count")
    issues = spec["issue_times_utc"]
    if not isinstance(issues, list) or not 1 <= len(issues) <= 100_000:
        raise CampaignError("issue_times_utc must contain 1..100000 hourly issues")
    parsed_issues = [_time(value, f"issue_times_utc[{i}]") for i, value in enumerate(issues)]
    if any(left >= right for left, right in zip(parsed_issues, parsed_issues[1:])):
        raise CampaignError("issue_times_utc must be strictly increasing without duplicates")
    if parsed_issues[0] <= origin:
        raise CampaignError("An issue must follow the original history origin by at least one hour; a cold-state branch is unsupported")
    try:
        last_target = parsed_issues[-1] + 18 * _HOUR
    except OverflowError as exc:
        raise CampaignError("Final forecast target exceeds the supported calendar") from exc
    if history_stop < last_target:
        raise CampaignError("history.stop_time_utc must cover the final issue plus 18 hours")
    resources = _object(spec["resources"], {
        "host_cpus", "parent_cpus", "cpus_per_branch", "max_concurrent_branches",
        "wall_time_seconds", "max_asset_bytes", "max_total_asset_bytes",
    }, "resources")
    for name in ("host_cpus", "parent_cpus", "cpus_per_branch"):
        _integer(resources[name], 1, 1024, f"resources.{name}")
    _integer(resources["max_concurrent_branches"], 1, 32, "resources.max_concurrent_branches")
    _integer(resources["wall_time_seconds"], 1, 604800, "resources.wall_time_seconds")
    _integer(resources["max_asset_bytes"], 1, MAX_ASSET_BYTES, "resources.max_asset_bytes")
    _integer(resources["max_total_asset_bytes"], 1, MAX_TOTAL_ASSET_BYTES, "resources.max_total_asset_bytes")
    if resources["max_asset_bytes"] > resources["max_total_asset_bytes"]:
        raise CampaignError("max_asset_bytes cannot exceed max_total_asset_bytes")
    cpu_reservation = (resources["parent_cpus"] + resources["cpus_per_branch"]
                       * resources["max_concurrent_branches"])
    if cpu_reservation > resources["host_cpus"]:
        raise CampaignError("Parent plus concurrent branch CPU reservations exceed host_cpus")
    domains = spec["domains"]
    if not isinstance(domains, list) or not 1 <= len(domains) <= 32:
        raise CampaignError("domains must contain 1..32 independently configured domains")
    domain_ids: set[str] = set()
    location_ids: set[str] = set()
    path_bindings: dict[str, tuple] = {}
    asset_count = 0
    for d, domain in enumerate(domains):
        prefix = f"domains[{d}]"
        _object(domain, {"domain_id", "locations", "assets"}, prefix)
        domain_id = _identifier(domain["domain_id"], f"{prefix}.domain_id")
        if domain_id in domain_ids:
            raise CampaignError("domain_id must be unique")
        domain_ids.add(domain_id)
        locations = domain["locations"]
        if not isinstance(locations, list) or not 1 <= len(locations) <= MAX_LOCATIONS:
            raise CampaignError(f"{prefix}.locations must contain 1..1024 output locations")
        reach_ids: set[str] = set()
        for loc in locations:
            _object(loc, {"location_id", "reach_id"}, f"{prefix}.location")
            location_id = _identifier(loc["location_id"], "location_id")
            if location_id in location_ids:
                raise CampaignError("location_id must be unique across the campaign")
            location_ids.add(location_id)
            if not isinstance(loc["reach_id"], str) or not _REACH.fullmatch(loc["reach_id"]):
                raise CampaignError("reach_id must be a positive decimal string of at most 20 digits")
            if loc["reach_id"] in reach_ids:
                raise CampaignError("Each reach_id may appear only once within a domain")
            reach_ids.add(loc["reach_id"])
        assets = domain["assets"]
        if not isinstance(assets, list) or len(assets) > MAX_ASSETS:
            raise CampaignError(f"{prefix}.assets must be an array with at most {MAX_ASSETS} entries")
        asset_count += len(assets)
        seen_paths: set[str] = set()
        for asset in assets:
            _object(asset, {"role", "path", "sha256", "size_bytes"}, f"{prefix}.asset")
            if not isinstance(asset["role"], str) or asset["role"] not in ASSET_ROLES:
                raise CampaignError(f"asset.role must be one of {sorted(ASSET_ROLES)}")
            path = _asset_path(asset["path"], "asset.path")
            if path in seen_paths:
                raise CampaignError("An asset path may appear only once within a domain")
            seen_paths.add(path)
            if asset["sha256"] is not None and (not isinstance(asset["sha256"], str)
                                                  or not _SHA256.fullmatch(asset["sha256"])):
                raise CampaignError("asset.sha256 must be null or 64 lowercase hexadecimal characters")
            if asset["size_bytes"] is not None:
                _integer(asset["size_bytes"], 1, resources["max_asset_bytes"], "asset.size_bytes")
            binding = (asset["role"], asset["sha256"], asset["size_bytes"])
            if path in path_bindings and path_bindings[path] != binding:
                raise CampaignError("A reused asset path must have an identical role, hash and size binding")
            path_bindings[path] = binding
    if len(location_ids) > MAX_LOCATIONS or asset_count > MAX_ASSETS:
        raise CampaignError("Campaign exceeds the 1024-location or 4096-asset inventory bound")
    bound_bytes = sum(binding[2] or 0 for binding in path_bindings.values())
    if bound_bytes > resources["max_total_asset_bytes"]:
        raise CampaignError("Declared unique asset sizes exceed max_total_asset_bytes")
    return {"origin": origin, "history_stop": history_stop, "history_hours": history_hours,
            "issues": parsed_issues, "location_count": len(location_ids),
            "cpu_reservation": cpu_reservation}


class _AssetRefusal(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _resident(metadata: os.stat_result) -> None:
    if getattr(metadata, "st_flags", 0) & _DATALESS:
        raise _AssetRefusal("asset_dataless", "Dataless placeholders are refused without hydration")


def _open_resident(path: Path, maximum: int) -> tuple[int, os.stat_result]:
    """Open a bounded regular file without following any symlink component.

    Walk using directory descriptors, check placeholder flags before opening
    the leaf and again before reading it, and bind the opened inode to lstat.
    Callers own the returned descriptor. No file bytes are read here.
    """
    absolute = Path(os.path.abspath(os.fspath(path)))
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None or os.open not in os.supports_dir_fd:
        raise _AssetRefusal("safe_open_unsupported", "Platform lacks required no-follow directory-descriptor opens")
    current = os.open(absolute.anchor, os.O_RDONLY | directory | nofollow)
    leaf_fd = None
    try:
        for part in absolute.parts[1:-1]:
            info = os.stat(part, dir_fd=current, follow_symlinks=False)
            _resident(info)
            if stat.S_ISLNK(info.st_mode):
                raise _AssetRefusal("asset_symlink", "Symlink path components are refused")
            if not stat.S_ISDIR(info.st_mode):
                raise _AssetRefusal("asset_not_regular", "An asset parent is not a directory")
            following = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=current)
            os.close(current)
            current = following
        before = os.stat(absolute.name, dir_fd=current, follow_symlinks=False)
        _resident(before)
        if stat.S_ISLNK(before.st_mode):
            raise _AssetRefusal("asset_symlink", "Symlink files are refused")
        if not stat.S_ISREG(before.st_mode):
            raise _AssetRefusal("asset_not_regular", "Asset must be a resident regular file")
        if before.st_size <= 0 or before.st_size > maximum:
            raise _AssetRefusal("asset_size_bound", "Asset is empty or exceeds its declared read bound")
        leaf_fd = os.open(absolute.name, os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0), dir_fd=current)
        after = os.fstat(leaf_fd)
        _resident(after)
        if (not stat.S_ISREG(after.st_mode)
                or (before.st_dev, before.st_ino, before.st_size) != (after.st_dev, after.st_ino, after.st_size)):
            raise _AssetRefusal("asset_changed", "Asset identity changed during safe open")
        result = leaf_fd
        leaf_fd = None
        return result, after
    finally:
        os.close(current)
        if leaf_fd is not None:
            os.close(leaf_fd)


def _read_bounded(fd: int, admitted_size: int) -> bytes:
    """Read exactly the admitted stat size without a beyond-budget sentinel."""
    chunks = []
    total = 0
    while total < admitted_size:
        _resident(os.fstat(fd))
        chunk = os.read(fd, min(1024 * 1024, admitted_size - total))
        if not chunk:
            raise _AssetRefusal("asset_changed", "File ended before its admitted size was read")
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CampaignError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise CampaignError(f"Nonfinite JSON number is forbidden: {value}")


def load_campaign(path: Path) -> dict:
    """Load a <=4 MiB resident JSON file and validate its exact specification."""
    try:
        fd, before = _open_resident(Path(path), MAX_SPEC_BYTES)
        try:
            data = _read_bounded(fd, before.st_size)
            after = os.fstat(fd)
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise CampaignError("Campaign changed during read")
        finally:
            os.close(fd)
        spec = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, _AssetRefusal) as exc:
        raise CampaignError(f"Cannot load campaign: {exc}") from exc
    _validate(spec)
    return spec


def _inspect_asset(asset: dict, base_dir: Path, maximum: int) -> tuple[dict, list[dict], int]:
    result = {**asset, "status": "unverified"}
    problems = []
    for field in ("sha256", "size_bytes"):
        if asset[field] is None:
            problems.append({"code": f"asset_{field}_unknown", "message": f"Expected {field} is unknown"})
    fd = None
    consumed = 0
    try:
        fd, before = _open_resident(base_dir / asset["path"], maximum)
        result["observed_size_bytes"] = before.st_size
        if asset["size_bytes"] is not None and before.st_size != asset["size_bytes"]:
            result["status"] = "mismatch"
            problems.append({"code": "asset_size_mismatch", "message": "Resident size differs from the bound size"})
        elif not problems:
            digest = hashlib.sha256()
            while consumed < before.st_size:
                _resident(os.fstat(fd))
                chunk = os.read(fd, min(1024 * 1024, before.st_size - consumed))
                if not chunk:
                    raise _AssetRefusal("asset_changed", "Asset ended before its admitted size was read")
                consumed += len(chunk)
                digest.update(chunk)
            after = os.fstat(fd)
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns) or consumed != before.st_size:
                raise _AssetRefusal("asset_changed", "Asset changed while its hash was read")
            result["observed_sha256"] = digest.hexdigest()
            if result["observed_sha256"] != asset["sha256"]:
                result["status"] = "mismatch"
                problems.append({"code": "asset_hash_mismatch", "message": "Resident SHA-256 differs from the bound identity"})
            else:
                result["status"] = "verified"
    except FileNotFoundError:
        result["status"] = "missing"
        problems.append({"code": "asset_missing", "message": "Expected resident asset is missing"})
    except _AssetRefusal as exc:
        result["status"] = "rejected"
        problems.append({"code": exc.code, "message": str(exc)})
    except OSError as exc:
        result["status"] = "rejected"
        problems.append({"code": "asset_unreadable", "message": f"Asset metadata/open/read failed (errno={exc.errno})"})
    finally:
        if fd is not None:
            os.close(fd)
    return result, problems, consumed


def plan_campaign(spec: dict, base_dir: Path, check_assets: bool = True) -> dict:
    """Return a deterministic bounded plan, including all observed blockers.

    Missing inputs do not invalidate a structurally valid plan. Asset checks
    prove only resident bytes/identities, never physical coverage or numerical
    qualification. Execution remains unavailable even if every asset hashes.
    """
    parsed = _validate(spec)
    if type(check_assets) is not bool:
        raise CampaignError("check_assets must be a boolean")
    blockers = [{"code": "runtime_not_qualified", "message": "Physical runtime execution has not been qualified by this planner"}]
    warnings = ["Asset hashes do not establish forcing units, spatial or temporal coverage, redistribution rights, or numerical equivalence.",
                "CPU reservations describe one domain at a time; concurrent domain scheduling is not implemented."]
    if not check_assets:
        blockers.append({"code": "asset_checks_disabled", "message": "Resident input identities were not checked"})
    assets = []
    cache: dict[str, tuple[dict, list[dict], int]] = {}
    consumed = 0
    domain_states = []
    for domain in spec["domains"]:
        present_roles = {asset["role"] for asset in domain["assets"]}
        for role in sorted(ASSET_ROLES - present_roles):
            blockers.append({"code": "asset_role_missing", "message": f"Required {role} assets have not been declared", "domain_id": domain["domain_id"]})
        for asset in domain["assets"]:
            if asset["path"] not in cache:
                if check_assets:
                    remaining = spec["resources"]["max_total_asset_bytes"] - consumed
                    maximum = min(spec["resources"]["max_asset_bytes"], remaining)
                    result, problems, read_bytes = _inspect_asset(asset, Path(base_dir), maximum)
                    consumed += read_bytes
                    cache[asset["path"]] = result, problems, read_bytes
                else:
                    problems = [{"code": f"asset_{field}_unknown", "message": f"Expected {field} is unknown"}
                                for field in ("sha256", "size_bytes") if asset[field] is None]
                    cache[asset["path"]] = {**asset, "status": "not_checked"}, problems, 0
            result, problems, _ = cache[asset["path"]]
            assets.append({"domain_id": domain["domain_id"], **result})
            blockers.extend({**problem, "domain_id": domain["domain_id"], "path": asset["path"]} for problem in problems)
        identity = {"profile": spec["profile"], "origin_time_utc": spec["origin_time_utc"],
                    "assets": sorted(domain["assets"], key=lambda a: (a["role"], a["path"]))}
        domain_states.append({"domain_id": domain["domain_id"],
                              "input_identity_sha256": hashlib.sha256(_canonical(identity)).hexdigest(),
                              "identity_complete": present_roles == ASSET_ROLES and all(
                                  asset["sha256"] is not None and asset["size_bytes"] is not None
                                  for asset in domain["assets"]),
                              "physical_state_verified": False})
    issue_count = len(spec["issue_times_utc"])
    domain_count = len(spec["domains"])
    result = {
        "schema_version": SCHEMA_VERSION, "campaign_id": spec["campaign_id"],
        "specification_sha256": hashlib.sha256(_canonical(spec)).hexdigest(),
        "profile": spec["profile"], "execution_ready": False,
        "totals": {"issue_count": issue_count, "domain_count": domain_count,
                   "location_count": parsed["location_count"], "branch_count": issue_count * domain_count,
                   "expected_forecast_rows": issue_count * parsed["location_count"] * 18,
                   "history_hours_per_domain": parsed["history_hours"],
                   "total_parent_history_hours": parsed["history_hours"] * domain_count,
                   "asset_count": len(assets), "unique_asset_count": len(cache), "hashed_bytes": consumed},
        "time_contract": {"origin_time_utc": spec["origin_time_utc"],
                          "history_stop_time_utc_exclusive": spec["history"]["stop_time_utc"],
                          "first_issue_time_utc": spec["issue_times_utc"][0],
                          "last_issue_time_utc": spec["issue_times_utc"][-1], "horizon_hours": 18,
                          "provider_label": "interval_start", "forecast_target": "issue_plus_lead_hour"},
        "resources": {**spec["resources"], "peak_reserved_cpus_per_domain": parsed["cpu_reservation"]},
        "domain_states": domain_states, "blockers": blockers, "warnings": warnings, "assets": assets,
    }
    result["plan_id"] = hashlib.sha256(_canonical(result)).hexdigest()
    return result


def iter_ledger(spec: dict) -> Iterator[dict]:
    """Stream declared output keys, in domain/issue/location/lead order.

    This is an expectation ledger, not a completed-output or model-run receipt.
    No asset is read. Callers must bound how much of the stream they export.
    """
    parsed = _validate(spec)
    for domain in spec["domains"]:
        for issue in parsed["issues"]:
            for location in domain["locations"]:
                for lead in range(1, 19):
                    yield {"domain_id": domain["domain_id"], **location,
                           "issue_time_utc": _format_time(issue), "lead_hour": lead,
                           "valid_time_utc": _format_time(issue + lead * _HOUR)}
