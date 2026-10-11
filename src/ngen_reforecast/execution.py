"""Bounded serial execution of an explicitly admitted diagnostic campaign.

This adapter controls only disposable containers on an explicit local Docker
endpoint. It never starts a worker, downloads/builds an image, changes inputs,
or claims recovery, shared history, scientific validation, or completion of an
archive. Byte-identical reference tools implement the admitted model stages.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import tarfile
import tempfile
import time
from typing import Any

from .campaign import CampaignError, _AssetRefusal, _canonical, _open_resident, _pairs, _nonfinite
from . import runtime
from . import execution_lock
from ._reference import common as reference
from ._reference import execute_stage


class ExecutionError(CampaignError):
    """Execution admission, isolation, transfer or stage verification failed."""


MAX_METADATA = 16 * 1024**2
MAX_TRANSFER = 32 * 1024**2
MAX_LOG = 128 * 1024**2
MAX_FILES = 8192
THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
              "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
              "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1"}
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _seal(value: dict, field: str) -> dict:
    if field in value:
        raise ExecutionError("An identity cannot be overwritten")
    return {**value, field: hashlib.sha256(_canonical(value)).hexdigest()}


def _write_new(path: Path, data: bytes) -> None:
    # Namespace parents are exclusively created by this adapter. O_NOFOLLOW
    # also rejects a replaced leaf; immutable receipts are never overwritten.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def _json_new(path: Path, value: dict) -> None:
    _write_new(path, execution_lock.payload_bytes(value))


def _read(path: Path, maximum: int, *, empty: bool = False) -> bytes:
    if empty:
        # Stage logs can legitimately be empty. The reference helper supports
        # zero-sized files while retaining no-follow/residency/race checks.
        try:
            return reference.read(path, maximum)
        except (OSError, ValueError) as exc:
            raise ExecutionError("Unsafe, changed or oversized execution evidence") from exc
    try:
        fd, before = _open_resident(path, maximum)
        try:
            parts = []
            total = 0
            while total < before.st_size:
                chunk = os.read(fd, min(65536, before.st_size - total))
                if not chunk:
                    raise ExecutionError("Evidence ended before its admitted byte length")
                total += len(chunk)
                parts.append(chunk)
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ExecutionError("Evidence changed during bounded read")
            return b"".join(parts)
        finally:
            os.close(fd)
    except (OSError, ValueError, _AssetRefusal) as exc:
        raise ExecutionError("Unsafe, missing, changed or oversized execution asset") from exc


def _binding(path: Path, maximum=MAX_LOG) -> dict:
    try:
        return reference.binding(path, maximum)
    except (OSError, ValueError) as exc:
        raise ExecutionError("Unsafe, missing, changed or oversized bound evidence") from exc


def _load(path: Path, field: str) -> dict:
    try:
        value = json.loads(_read(path, MAX_METADATA), object_pairs_hook=_pairs, parse_constant=_nonfinite)
        return reference.verify(value, field)
    except (OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        raise ExecutionError("Invalid sealed execution receipt") from exc


def _safe_directory(path: Path) -> None:
    fd = None
    try:
        fd = runtime._open_directory(path)
    except (OSError, runtime._InspectionFailure) as exc:
        raise ExecutionError("A directory must be resident and have no symbolic-link components") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = None
    try:
        fd = runtime._open_directory(path)
        os.fsync(fd)
    except (OSError, runtime._InspectionFailure) as exc:
        raise ExecutionError("Execution directory could not be durably flushed") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _new_namespace(path: Path, protected: list[Path]) -> None:
    path = path.absolute()
    for root in protected:
        root = root.absolute()
        if path == root or path in root.parents or root in path.parents:
            raise ExecutionError("Execution outputs must be separate from every input/runtime source tree")
    parent = None
    try:
        parent = runtime._open_directory(path.parent)
        os.mkdir(path.name, mode=0o700, dir_fd=parent)
        os.fsync(parent)
    except FileExistsError as exc:
        raise ExecutionError("Execution namespace already exists; resume and overwrite are unsupported") from exc
    except (OSError, runtime._InspectionFailure) as exc:
        raise ExecutionError("Execution namespace requires a resident, writable existing parent") from exc
    finally:
        if parent is not None:
            os.close(parent)


def _claim(lock: dict, asset_root: Path, output_root: Path) -> dict:
    """Publish a durable per-lock claim, including after a failed launch.

    Different output paths cannot reset a campaign's process allowance. Claims
    live separately from fixture/reference/runtime assets and are never removed
    automatically. A later supported resume would need a separate design.
    """
    root_fd = claims_fd = None
    try:
        root_fd = runtime._open_directory(asset_root)
        try:
            os.mkdir(".execution-claims", mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        os.fsync(root_fd)
        claims_fd = runtime._open_child(root_fd, ".execution-claims", directory=True)
        value = _seal({"schema_version": "campaign-execution-claim/0.1", "run_id": lock["run_id"],
                       "execution_lock_sha256": lock["execution_lock_sha256"],
                       "output_namespace_sha256": hashlib.sha256(str(output_root.absolute()).encode()).hexdigest(),
                       "claimed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "automatic_retry_or_resume": False}, "claim_identity_sha256")
        filename = lock["execution_lock_sha256"] + ".json"
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=claims_fd)
        try:
            raw = execution_lock.payload_bytes(value)
            while raw:
                n = os.write(fd, raw)
                if n <= 0:
                    raise ExecutionError("Execution claim could not be durably written")
                raw = raw[n:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(claims_fd)
        return value
    except FileExistsError as exc:
        raise ExecutionError("This execution lock was already claimed; duplicate launch and automatic resume are refused") from exc
    except (OSError, runtime._InspectionFailure) as exc:
        raise ExecutionError("Persistent execution claim could not be created safely") from exc
    finally:
        for fd in (claims_fd, root_fd):
            if fd is not None:
                os.close(fd)


def _endpoint(value: str) -> str:
    if not isinstance(value, str) or not value.startswith("unix:///") or any(c in value for c in "\x00\r\n?#"):
        raise ExecutionError("An explicit absolute local Unix Docker endpoint is required")
    path = value.removeprefix("unix://")
    if len(value) > 1024 or ".." in Path(path).parts or "//" in path or path.endswith("/"):
        raise ExecutionError("Docker endpoint must be a normalized absolute socket path")
    return value


def _inventory(root: Path, maximum: int) -> list[dict]:
    try:
        return reference.inventory(root, maximum, maximum_files=MAX_FILES)
    except (OSError, ValueError) as exc:
        raise ExecutionError("Execution inventory exceeds its bound or contains unsafe entries") from exc


def _storage(root: Path, bounds: dict) -> dict:
    allocated = 0
    seen = set()
    for path in root.rglob("*"):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ExecutionError("Symbolic links are forbidden in an execution namespace")
        if stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) not in seen:
            seen.add((info.st_dev, info.st_ino))
            allocated += info.st_blocks * 512
        elif not stat.S_ISREG(info.st_mode) and not stat.S_ISDIR(info.st_mode):
            raise ExecutionError("Special files are forbidden in an execution namespace")
    free = shutil.disk_usage(root).free
    if allocated > bounds["aggregate_output_bytes"] or free < bounds["minimum_host_free_bytes"]:
        raise ExecutionError("Execution storage budget or host free-space floor was crossed")
    return {"execution_namespace_allocated_bytes": allocated, "host_free_bytes": free,
            "scope": "Owned execution namespace; external runtime storage remains separately admitted"}


class _Docker:
    """Pipe utilities through bounded local spool files; never use a shell."""
    def __init__(self, endpoint: str, output_root: Path, bounds: dict, docker_config: Path | None):
        self.argv = ["docker", "--host", _endpoint(endpoint)]
        self.root = output_root
        self.bounds = bounds
        self.env = os.environ.copy()
        for name in ["DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH", "DOCKER_API_VERSION"]:
            self.env.pop(name, None)
        self.env.update(THREAD_ENV)
        if docker_config is not None:
            _safe_directory(docker_config)
            self.env["DOCKER_CONFIG"] = str(docker_config.absolute())

    def command(self, args: list[str], *, data: bytes | None = None, timeout: float = 60,
                maximum: int = 1024**2, destination: Path | None = None,
                permit_failure: bool = False, critical: bool = False,
                guard_storage: bool = True) -> bytes | int:
        if critical:
            # Cleanup must remain possible when the host has crossed its disk
            # floor. It neither allocates spool files nor applies storage guards.
            process = subprocess.Popen(self.argv + args, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       env=self.env, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
                if code:
                    raise ExecutionError("Critical Docker cleanup failed (exit %d)" % code)
                return b""
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=15)
        if data is not None and len(data) > MAX_TRANSFER:
            raise ExecutionError("Docker stdin transfer exceeds its admitted bound")
        with ExitStack() as stack:
            stdin = stack.enter_context(tempfile.TemporaryFile(dir=self.root)) if data is not None else subprocess.DEVNULL
            if data is not None:
                stdin.write(data); stdin.seek(0)
            if destination is None:
                stdout = stack.enter_context(tempfile.TemporaryFile(dir=self.root))
            else:
                stdout = stack.enter_context(destination.open("xb"))
            stderr = stack.enter_context(tempfile.TemporaryFile(dir=self.root))
            process = subprocess.Popen(self.argv + args, stdin=stdin, stdout=stdout, stderr=stderr,
                                       env=self.env, start_new_session=True)
            begin = time.monotonic()
            try:
                while process.poll() is None:
                    if time.monotonic() - begin > timeout:
                        raise ExecutionError("Docker utility exceeded its deadline")
                    if os.fstat(stdout.fileno()).st_size > maximum or os.fstat(stderr.fileno()).st_size > 1024**2:
                        raise ExecutionError("Docker utility exceeded its output byte bound")
                    if guard_storage:
                        _storage(self.root, self.bounds)
                    time.sleep(0.05)
                code = process.wait()
                if os.fstat(stdout.fileno()).st_size > maximum or os.fstat(stderr.fileno()).st_size > 1024**2:
                    raise ExecutionError("Docker utility exceeded its output byte bound")
                if code and not permit_failure:
                    raise ExecutionError("Docker utility failed (exit %d)" % code)
                if destination is not None:
                    return code
                stdout.seek(0)
                return stdout.read(maximum)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=15)

    def accounting(self, name: str) -> dict:
        code = 'import json,pathlib; r=pathlib.Path("/sys/fs/cgroup"); print(json.dumps({n:(r/n).read_text() for n in ["cpu.max","cpu.stat","memory.max","memory.peak","memory.events","pids.max","pids.peak"]}))'
        return json.loads(self.command(["exec", name, "/ngen/.venv/bin/python", "-c", code], timeout=15))

    def quiesce(self, name: str) -> dict:
        # Repeat scans to reap descendants that fork during the first scan. PID1
        # remains alive until tar export finishes, preserving mounted tmpfs data.
        code = 'import os,signal,json,time; own=os.getpid(); killed=[]; errors=[]\nfor scan in range(3):\n for n in os.listdir("/proc"):\n  if n.isdigit() and int(n)>1 and int(n)!=own:\n   try: os.kill(int(n),signal.SIGKILL);killed.append(int(n))\n   except ProcessLookupError: pass\n   except Exception as e: errors.append([int(n),type(e).__name__])\n time.sleep(.05)\nprint(json.dumps({"killed_container_pids":killed,"errors":errors,"pid1_kept_alive":True}))'
        return json.loads(self.command(["exec", name, "/ngen/.venv/bin/python", "-c", code], timeout=15, guard_storage=False))

    def model(self, args: list[str], log: Path, seconds: float, name: str) -> dict:
        begin = time.monotonic()
        reason = None
        with log.open("xb") as output:
            process = subprocess.Popen(self.argv + args, env=self.env, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while process.poll() is None:
                    if time.monotonic() - begin > seconds + 5:
                        reason = "host_logical_job_deadline"
                    if os.fstat(output.fileno()).st_size > 1024**2:
                        reason = "host_wrapper_log_bound"
                    try:
                        _storage(self.root, self.bounds)
                    except ExecutionError:
                        reason = "host_storage_bound"
                    if reason:
                        try:
                            self.quiesce(name)
                        finally:
                            if process.poll() is None:
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait(timeout=15)
                        break
                    time.sleep(0.1)
                code = process.wait()
            finally:
                if process.poll() is None:
                    try:
                        self.quiesce(name)
                    finally:
                        if process.poll() is None:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(timeout=15)
        return {"docker_exec_exit_code": code, "host_elapsed_seconds": time.monotonic() - begin,
                "stop_reason": reason, "wrapper_log": _binding(log, 1024**2)}


def _tar(entries: list[tuple[str, bytes, int]]) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as archive:
        for name, raw, mode in entries:
            reference.relative(name)
            if len(raw) > MAX_METADATA:
                raise ExecutionError("A transferred file exceeds the admitted per-file bound")
            info = tarfile.TarInfo(name)
            info.size = len(raw); info.mode = mode
            archive.addfile(info, io.BytesIO(raw))
    result = out.getvalue()
    if len(result) > MAX_TRANSFER:
        raise ExecutionError("Input transfer exceeds its admitted bound")
    return result


def _extract_tar(path: Path, destination: Path, leaf: str, maximum: int) -> None:
    """Never extract links, special files, duplicates, escapes or sparse files."""
    try:
        _extract_tar_members(path, destination, leaf, maximum)
    except runtime._InspectionFailure as exc:
        raise ExecutionError("Export directories must be resident and have no symbolic links") from exc


def _extract_tar_members(path: Path, destination: Path, leaf: str, maximum: int) -> None:
    total = 0
    names = set()
    with tarfile.open(path, mode="r:") as archive:
        for member in archive:
            name = member.name.rstrip("/")
            reference.relative(name)
            if name in names or name.split("/")[0] != leaf or not (member.isfile() or member.isdir()) or member.issparse():
                raise ExecutionError("Unsafe, duplicate or unbound tar member")
            names.add(name); total += member.size
            if len(names) > MAX_FILES or total > maximum or member.size < 0:
                raise ExecutionError("Export tar exceeds its file/byte allowance")
            # Resolve every directory relative to a no-follow descriptor. A
            # replaced parent cannot redirect exported bytes outside this tree.
            with ExitStack() as descriptors:
                parent = runtime._open_directory(destination.parent)
                descriptors.callback(os.close, parent)
                try:
                    os.mkdir(destination.name, mode=0o700, dir_fd=parent)
                except FileExistsError:
                    pass
                current = runtime._open_child(parent, destination.name, directory=True)
                descriptors.callback(os.close, current)
                parts = [] if name == leaf else name[len(leaf) + 1:].split("/")
                if not parts and not member.isdir():
                    raise ExecutionError("Export root must be a directory")
                directories = parts if member.isdir() else parts[:-1]
                for component in directories:
                    try:
                        os.mkdir(component, mode=0o700, dir_fd=current)
                    except FileExistsError:
                        pass
                    current = runtime._open_child(current, component, directory=True)
                    descriptors.callback(os.close, current)
                if member.isfile():
                    fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=current)
                    try:
                        source = archive.extractfile(member)
                        if source is None:
                            raise ExecutionError("Export tar has no regular-file data")
                        with source, os.fdopen(fd, "wb", closefd=False) as output:
                            shutil.copyfileobj(source, output, 65536)
                    finally:
                        os.close(fd)


def _capture_tree(docker: _Docker, name: str, remote: str, destination: Path, maximum: int) -> dict:
    parent, leaf = remote.rsplit("/", 1)
    path = destination.parent / (".transfer-" + destination.name + ".tar")
    # Include tar framing overhead in the streaming bound. The parsed payload
    # is separately limited before each file is created.
    docker.command(["exec", name, "/bin/tar", "-cf", "-", "-C", parent, leaf],
                   timeout=120, maximum=maximum + 8 * 1024**2, destination=path)
    result = _binding(path, maximum + 8 * 1024**2)
    _extract_tar(path, destination, leaf, maximum)
    path.unlink()
    return result


def _container_args(lock: dict, name: str) -> list[str]:
    return ["create", "--name", name, "--pull", "never", "--network", "none", "--read-only",
            "--label", "ngen-reforecast.execution-lock=" + lock["execution_lock_sha256"],
            "--label", "ngen-reforecast.run-id=" + lock["run_id"],
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "256",
            "--memory", "8g", "--memory-swap", "8g", "--cpus", "2",
            "--tmpfs", "/tmp:rw,exec,size=64m", "--tmpfs", "/work:rw,noexec,size=128m",
            "--tmpfs", "/work/job/outputs:rw,noexec,size=1g",
            "--env", "LD_LIBRARY_PATH=" + lock["admission"]["native_ld_library_path"],
            *[arg for key, value in THREAD_ENV.items() for arg in ("--env", key + "=" + value)],
            "--entrypoint", "/bin/sleep", "sha256:" + lock["admission"]["image_manifest_sha256"], "infinity"]


def _check_container(lock: dict, inspection: dict) -> None:
    h = inspection["HostConfig"]
    digest = "sha256:" + lock["admission"]["image_manifest_sha256"]
    if (h["NetworkMode"] != "none" or not h["ReadonlyRootfs"] or h["Privileged"]
            or h["Memory"] != 8 * 1024**3 or h["MemorySwap"] != 8 * 1024**3
            or h["NanoCpus"] != 2 * 10**9 or h["PidsLimit"] != 256
            or h["Binds"] or h["VolumesFrom"] or inspection["Mounts"]
            or h.get("PidMode", "") not in ("", "private") or h.get("IpcMode", "private") != "private"
            or h["CapAdd"] or h["CapDrop"] != ["ALL"] or h["SecurityOpt"] != ["no-new-privileges"]
            or h["Tmpfs"] != {"/tmp": "rw,exec,size=64m", "/work": "rw,noexec,size=128m", "/work/job/outputs": "rw,noexec,size=1g"}
            or inspection["Image"] != digest or inspection["Config"]["Image"] != digest):
        raise ExecutionError("Actual container identity or isolation limits differ from admission")
    if inspection["ImageManifestDescriptor"]["platform"] != {"architecture": "arm64", "os": "linux"}:
        raise ExecutionError("Actual runtime container is not Linux ARM64")
    env = dict(value.split("=", 1) for value in inspection["Config"]["Env"])
    if any(env.get(key) != value for key, value in THREAD_ENV.items()) or env.get("LD_LIBRARY_PATH") != lock["admission"]["native_ld_library_path"]:
        raise ExecutionError("Actual model thread/loader environment differs from admission")


def _check_cgroup(value: dict) -> None:
    if value["cpu.max"].strip() != "200000 100000" or int(value["memory.max"]) != 8 * 1024**3 or int(value["pids.max"]) != 256:
        raise ExecutionError("Linux cgroup limits differ from admission")
    events = dict(line.split() for line in value["memory.events"].splitlines())
    if any(int(v) for v in events.values()) or int(value["memory.peak"]) > 8 * 1024**3 or int(value["pids.peak"]) > 256:
        raise ExecutionError("Linux cgroup memory/PID limit or OOM event was observed")


def _payload(lock: dict, asset_root: Path, case: str, frozen: Path) -> bytes:
    fixture = asset_root / lock["bundle_paths"]["fixture_root"] / case
    entries = []
    for row in lock["admission"]["case_inputs"][case]:
        path = fixture / reference.relative(row["path"])
        raw = _read(path, MAX_METADATA)
        if {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} != {k: row[k] for k in ("bytes", "sha256")}:
            raise ExecutionError("Case input changed before container transfer")
        entries.append(("job/" + row["path"], raw, 0o400))
    entries += [(name, _read(frozen / name, MAX_METADATA), 0o400) for name in ("PROTOCOL.json", "ADMISSION.json")]
    tools = Path(reference.__file__).parent
    for row in lock["source_tools"]:
        name = Path(row["path"]).name
        raw = _read(tools / name, MAX_METADATA)
        if {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} != {k: row[k] for k in ("bytes", "sha256")}:
            raise ExecutionError("Packaged execution tool differs from the source lock")
        entries.append(("tools/" + name, raw, 0o400))
    return _tar(entries)


def _verify_stage(lock: dict, case: str, stage: str, directory: Path, reservation: dict) -> dict:
    receipt = _load(directory / "RECEIPT.json", "process_receipt_identity_sha256")
    if receipt["reservation"] != reservation or receipt["returncode"] != 0 or receipt["termination_reason"] is not None or receipt["post_launch_verification_error"] is not None:
        raise ExecutionError("Stage was not successful under its reserved identities")
    if receipt["case_input_identity_sha256_after"] != reservation["case_input_identity_sha256"]:
        raise ExecutionError("Case inputs changed during a model stage")
    expected = next(row for row in lock["source_tools"] if Path(row["path"]).name == "execute_stage.py")
    if receipt["executor"] != {k: expected[k] for k in ("bytes", "sha256")}:
        raise ExecutionError("Actual stage executor differs from frozen source")
    for name in ("stdout", "stderr"):
        if _binding(directory / (name + ".log")) != receipt[name]:
            raise ExecutionError("Stage log differs from its actual process receipt")
    if stage == "native":
        if receipt.get("native_output_contract", {}).get("native_output_contract_complete") is not True:
            raise ExecutionError("Native output completion is required; zero exit is insufficient")
        try:
            execution_lock.verify_native_warnings(lock, case, directory)
        except (OSError, ValueError, _AssetRefusal) as exc:
            raise ExecutionError(str(exc)) from exc
    return receipt


def _run_case(lock: dict, asset_root: Path, output_root: Path, docker: _Docker, case: str) -> dict:
    attempt = output_root / "attempts" / case
    attempt.mkdir(mode=0o700)
    _fsync_directory(attempt.parent)
    name = "nrf-campaign-" + lock["run_id"].lower() + "-" + case.lower()
    frozen = output_root / "frozen"
    payload = _payload(lock, asset_root, case, frozen)
    capture = {"case_id": case, "run_id": lock["run_id"], "execution_lock_sha256": lock["execution_lock_sha256"],
               "protocol_identity_sha256": lock["protocol_identity_sha256"], "admission_identity_sha256": lock["admission"]["admission_identity_sha256"],
               "create_argv": _container_args(lock, name), "transfer_payload": {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()},
               "stages": [], "status": "setting_up", "storage_before": _storage(output_root, lock["bounds"])}
    create_attempted = False
    created = False
    isolation_verified = False
    model_invoked = False
    begin = None
    try:
        create_attempted = True
        docker.command(capture["create_argv"]); created = True
        docker.command(["start", name])
        inspection = json.loads(docker.command(["inspect", name]))[0]
        _check_container(lock, inspection)
        isolation_verified = True
        capture["container_inspection"] = inspection
        docker.command(["exec", "-i", name, "/bin/tar", "-xf", "-", "-C", "/work"], data=payload)
        runtime_tar = asset_root / lock["bundle_paths"]["runtime_tar"]
        if _binding(runtime_tar) != lock["admission"]["runtime_transfer_payload"]:
            raise ExecutionError("Runtime export transfer changed")
        docker.command(["exec", "-i", name, "/bin/tar", "-xf", "-", "-C", "/tmp"], data=_read(runtime_tar, MAX_METADATA))
        docker.command(["exec", name, "/bin/mkdir", "-p", "/work/job/outputs/ngen", "/work/job/outputs/troute"])
        capture["cgroup_before"] = docker.accounting(name)
        _check_cgroup(capture["cgroup_before"])
        begin = time.monotonic()
        for stage in ["native", "routing"]:
            remaining = lock["bounds"]["logical_job_wall_seconds"] - (time.monotonic() - begin)
            if remaining <= 0:
                raise ExecutionError("Logical job deadline expired before next model reservation")
            reservation = execute_stage.reserve(frozen / "PROTOCOL.json", frozen / "ADMISSION.json", lock["admission_file"]["sha256"],
                                                case, stage, output_root / "ledger", case + "-" + stage, remaining)
            rp = output_root / "ledger" / ("PROCESS-%02d.json" % reservation["process_number"])
            # Reservation reaches durable host storage before any model launch.
            fd = os.open(rp, os.O_RDONLY | os.O_NOFOLLOW)
            try: os.fsync(fd)
            finally: os.close(fd)
            _fsync_directory(output_root / "ledger")
            docker.command(["exec", "-i", name, "/bin/tar", "-xf", "-", "-C", "/work"], data=_tar([(rp.name, _read(rp, MAX_METADATA), 0o400)]))
            args = ["exec", name, "/ngen/.venv/bin/python", "/work/tools/execute_stage.py", "run", "/work/PROTOCOL.json", "/work/ADMISSION.json",
                    lock["admission_file"]["sha256"], "/work/" + rp.name, "/work/job", "/work/receipts/" + stage]
            model_invoked = True
            result = docker.model(args, attempt / (stage + "-wrapper.log"), remaining, name)
            capture["stages"].append({"stage": stage, "process_number": reservation["process_number"], **result})
            capture["cgroup_after_" + stage] = docker.accounting(name)
            _check_cgroup(capture["cgroup_after_" + stage])
            capture["stages"][-1]["receipt_transfer"] = _capture_tree(docker, name, "/work/receipts/" + stage, attempt / stage, MAX_LOG)
            if result["docker_exec_exit_code"] != 0 or result["stop_reason"] is not None:
                raise ExecutionError("Model stage failed; its diagnostic evidence was preserved")
            _verify_stage(lock, case, stage, attempt / stage, reservation)
        capture["status"] = "both_stages_zero_exit"
        value = docker.command(["exec", name, "/ngen/.venv/bin/python", "/work/tools/normalize_routing.py", "/work/PROTOCOL.json", case,
                                "/work/job/outputs", "/work/normalized"], timeout=120)
        capture["normalizer_stdout"] = value.decode("ascii")
        capture["normalizer_transfer"] = _capture_tree(docker, name, "/work/normalized", attempt / "normalized", MAX_LOG)
        capture["output_transfer"] = _capture_tree(docker, name, "/work/job/outputs", attempt / "outputs", lock["bounds"]["job_output_bytes"])
        norm = _load(attempt / "normalized/NORMALIZATION.json", "normalization_identity_sha256")
        norm_source = next(row for row in lock["source_tools"] if Path(row["path"]).name == "normalize_routing.py")
        if norm["case_id"] != case or norm["protocol_identity_sha256"] != lock["protocol_identity_sha256"] or norm["normalizer"] != {k: norm_source[k] for k in ("bytes", "sha256")}:
            raise ExecutionError("Actual normalization source or case identity differs")
        if norm["netCDF4_version"] != "1.6.3" or norm["numpy_version"] != "1.26.4" or _binding(attempt / "normalized/routing.csv") != norm["normalized_csv"]:
            raise ExecutionError("Normalization packages or preserved CSV bytes differ")
        routed = _load(attempt / "routing/RECEIPT.json", "process_receipt_identity_sha256")
        raw = _inventory(attempt / "outputs", lock["bounds"]["job_output_bytes"])
        if raw != routed["outputs_after"] or [row for row in raw if row["path"].startswith("troute/")] != norm["raw_sources"]:
            raise ExecutionError("Captured raw outputs differ from actual routing/normalization receipt")
        capture["whole_job_model_elapsed_seconds"] = time.monotonic() - begin
        if capture["whole_job_model_elapsed_seconds"] > lock["bounds"]["logical_job_wall_seconds"]:
            raise ExecutionError("Logical job deadline was exceeded before capture verification")
        capture["host_free_bytes_after"] = shutil.disk_usage(output_root).free
        capture["storage_after"] = _storage(output_root, lock["bounds"])
    except BaseException as error:
        capture["status"] = "failed"
        capture["error"] = {"type": type(error).__name__, "message": str(error) if isinstance(error, ExecutionError) else "Execution utility or evidence operation failed"}
        if created and isolation_verified and model_invoked:
            try:
                capture["exception_quiescence"] = docker.quiesce(name)
            except BaseException as stopped:
                capture["quiescence_error"] = type(stopped).__name__
                # Without proven quiescence we stop immediately; writing model
                # processes must not race a partial-output capture.
                try: docker.command(["stop", "--time", "5", name], timeout=30, critical=True)
                except BaseException: pass
            else:
                try:
                    capture["failed_receipt_transfer"] = _capture_tree(docker, name, "/work/receipts", attempt / "failed-receipts", MAX_LOG)
                except BaseException as failed_receipts:
                    capture["failed_receipt_capture_error"] = type(failed_receipts).__name__
                try:
                    capture["failed_output_transfer"] = _capture_tree(docker, name, "/work/job/outputs", attempt / "failed-outputs", lock["bounds"]["job_output_bytes"])
                except BaseException as failed_capture:
                    capture["failed_output_capture_error"] = type(failed_capture).__name__
        if begin is not None:
            capture["whole_job_model_elapsed_seconds"] = time.monotonic() - begin
    finally:
        capture["cleanup"] = []
        owned = created
        if create_attempted and not owned:
            try:
                uncertain = json.loads(docker.command(["inspect", name], guard_storage=False))[0]
                labels = uncertain["Config"].get("Labels") or {}
                owned = (labels.get("ngen-reforecast.execution-lock") == lock["execution_lock_sha256"]
                         and labels.get("ngen-reforecast.run-id") == lock["run_id"])
            except BaseException:
                owned = False
            capture["uncertain_create_ownership_verified"] = owned
        if owned:
            # Also remove after a timed-out create: Docker may have created the
            # container even when its client never returned a success response.
            for action in [["stop", "--time", "5", name], ["rm", "--force", name]]:
                try:
                    docker.command(action, timeout=30, critical=True)
                    capture["cleanup"].append({"action": action[0], "status": "completed"})
                except BaseException as error:
                    capture["cleanup"].append({"action": action[0], "error": type(error).__name__})
                    capture["status"] = "failed"
        capture = _seal(capture, "host_execution_identity_sha256")
        _json_new(attempt / "HOST_EXECUTION.json", capture)
    return capture


def preflight_execution(lock: dict, *, asset_root: Path) -> dict:
    """Refuse changed/unadmitted inputs without Docker, model or worker calls."""
    try:
        execution_lock.validate_execution_lock(lock)
        report = execution_lock.verify_execution_assets(lock, asset_root)
    except (OSError, ValueError, _AssetRefusal) as exc:
        raise ExecutionError(str(exc)) from exc
    if report.get("verified") is not True:
        raise ExecutionError("Execution asset verification did not pass")
    for case in lock["protocol"]["cases"]:
        if not _IDENTIFIER.fullmatch(case["case_id"]):
            raise ExecutionError("Unsupported case identifier")
    if not _IDENTIFIER.fullmatch(lock["run_id"]):
        raise ExecutionError("Unsupported execution run identifier")
    tools = Path(reference.__file__).parent
    actual = {p.name for p in tools.glob("*.py")}
    expected = {Path(row["path"]).name for row in lock["source_tools"]}
    if actual != expected or len(expected) != 7:
        raise ExecutionError("Packaged execution-tool axis differs from the execution lock")
    for row in lock["source_tools"]:
        if _binding(tools / Path(row["path"]).name) != {k: row[k] for k in ("bytes", "sha256")}:
            raise ExecutionError("Packaged execution-tool bytes differ from the execution lock")
    for name, key in [("PROTOCOL.json", "protocol"), ("ADMISSION.json", "admission")]:
        data = execution_lock.payload_bytes(lock[key])
        if {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} != lock[key + "_file"]:
            raise ExecutionError("Execution metadata serialization differs from the lock")
    return {"verified": True, "execution_lock_sha256": lock["execution_lock_sha256"], "assets": report,
            "new_model_invocations": 0, "worker_started": False}


def execute_campaign(lock: dict, *, asset_root: Path, output_root: Path,
                     docker_host: str, docker_config: Path | None = None) -> dict:
    """Capture three new serial jobs under a fresh execution namespace.

    Captured means fresh process/normalization evidence exists. The archive layer
    must independently audit all outputs and reference agreement before commit.
    A planning lock is never accepted as execution admission. There is no retry
    or resume; failures and occupied reservations remain visible.
    """
    _endpoint(docker_host)
    preflight_execution(lock, asset_root=asset_root)
    asset_root = asset_root.absolute(); output_root = output_root.absolute()
    protected = [asset_root / lock["bundle_paths"][key] for key in ["fixture_root", "reference_root"]]
    protected += [asset_root / lock["bundle_paths"]["runtime_tar"], Path(reference.__file__).parent]
    if docker_config is not None:
        _safe_directory(docker_config)
        protected.append(docker_config.absolute())
    if shutil.disk_usage(output_root.parent).free < lock["bounds"]["minimum_host_free_bytes"]:
        raise ExecutionError("Host free-space floor prevents execution namespace creation")
    # Validate separation and an absent target before consuming a per-lock claim.
    _safe_directory(output_root.parent)
    if output_root.exists() or output_root.is_symlink():
        raise ExecutionError("Execution namespace already exists; resume and overwrite are unsupported")
    if any(output_root == p or output_root in p.parents or p in output_root.parents for p in protected):
        raise ExecutionError("Execution outputs must be separate from every input/runtime source tree")
    claim = _claim(lock, asset_root, output_root)
    _new_namespace(output_root, protected)
    capture = {"schema_version": "campaign-execution-capture/0.1", "run_id": lock["run_id"],
               "execution_lock_sha256": lock["execution_lock_sha256"], "fixture_id": lock["fixture_id"],
               "protocol_identity_sha256": lock["protocol_identity_sha256"], "runtime_identity_sha256": lock["runtime_identity_sha256"],
               "assembly_identity_sha256": lock["assembly_identity_sha256"], "reference_set_identity_sha256": lock["reference_set_identity_sha256"],
               "terminal_status": "failed", "cases": [], "resume_supported": False,
               "worker_started": False, "archive_committed": False, "release_qualified": False,
               "persistent_execution_claim": claim}
    try:
        frozen = output_root / "frozen"
        frozen.mkdir(mode=0o700)
        (output_root / "attempts").mkdir(mode=0o700)
        (output_root / "ledger").mkdir(mode=0o700)
        _fsync_directory(output_root)
        _json_new(frozen / "PROTOCOL.json", lock["protocol"])
        _json_new(frozen / "ADMISSION.json", lock["admission"])
        _fsync_directory(frozen)
        docker = _Docker(docker_host, output_root, lock["bounds"], docker_config)
        # Inspect only the locked local image. No implicit pull, build, mutable
        # tag, alternate image, context or profile selection is attempted.
        info = json.loads(docker.command(["image", "inspect", "sha256:" + lock["admission"]["image_manifest_sha256"]]))[0]
        if info["Architecture"] != "arm64" or info["Os"] != "linux":
            raise ExecutionError("Locked local runtime image is not Linux ARM64")
        capture["local_image"] = {"id": info["Id"], "architecture": info["Architecture"], "os": info["Os"], "size_bytes": info["Size"]}
        if info["Id"] != "sha256:" + lock["admission"]["image_manifest_sha256"] or info["Size"] > lock["bounds"]["runtime_and_staging_bytes"]:
            raise ExecutionError("Locked local image identity or declared image size differs")
        for row in lock["protocol"]["cases"]:
            result = _run_case(lock, asset_root, output_root, docker, row["case_id"])
            capture["cases"].append({"case_id": row["case_id"], "status": result["status"],
                                     "host_execution_identity_sha256": result["host_execution_identity_sha256"],
                                     "host_receipt": _binding(output_root / "attempts" / row["case_id"] / "HOST_EXECUTION.json")})
            if result["status"] != "both_stages_zero_exit":
                raise ExecutionError("A case failed; subsequent cases were not launched")
        ledger = [_load(path, "reservation_identity_sha256") for path in sorted((output_root / "ledger").glob("PROCESS-*.json"))]
        if [r["process_number"] for r in ledger] != list(range(1, 7)):
            raise ExecutionError("Successful capture requires exactly six ordered new stage reservations")
        capture["model_processes_reserved"] = len(ledger)
        capture["terminal_status"] = "captured"
        capture["storage_after"] = _storage(output_root, lock["bounds"])
    except BaseException as error:
        capture["terminal_status"] = "failed"
        capture["error"] = {"type": type(error).__name__, "message": str(error) if isinstance(error, ExecutionError) else "Campaign utility or evidence operation failed"}
        capture["model_processes_reserved"] = len(list((output_root / "ledger").glob("PROCESS-*.json")))
    finally:
        try:
            capture["files"] = _inventory(output_root, lock["bounds"]["aggregate_output_bytes"])
        except BaseException as error:
            capture["terminal_status"] = "failed"
            capture["files"] = []
            capture["inventory_error"] = type(error).__name__
        capture = _seal(capture, "capture_identity_sha256")
        _json_new(output_root / "CAPTURE.json", capture)
    return capture
