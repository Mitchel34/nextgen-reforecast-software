#!/usr/bin/env python3
"""Inspect the immutable export/image diagnostic lane without invoking models.

This utility does not build native code or qualify a release profile. It accepts
only the preserved export hashes and component image, imports the routing module
without calling its entry point, and inspects ELF dependencies with loader --list.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import time
import uuid

IMAGE = "sha256:2e75ab75ad1ce8de7755b84b1428ace2b99b8a51a2bb07b0b8970f4ddfd62bff"
EXPORTS = {
    "ngen-shared": "ee65c7748c4d2a7e9f3900fc3a5e8c16c045db90eb34a9b877b7bcc5dc942132",
    "libiso_c_bmi.so": "09b65b5c2a76df4e8e9b334b9d3c56f39c327955306085cae692484742dcc162",
}
COMPONENTS = {
    "libcfebmi.so.1.0.0": "f54e29c81e2b86c0233f2530e929e18fe9226c421225b90263fa8128ec4ae56a",
    "libsurfacebmi.so": "6e17db8089cfa99e140fb7152c3dbec260c9a38f3bd7d6512e7dd063bec5dc74",
    "libslothmodel.so.1.0.0": "39884bb6370071c04d318c6563315237e982ec3d8f165e8e2df6db89251d5a42",
}
TABLES = {
    "GENPARM.TBL": "f9e821ee1928f3ce121c3e3453e79c16e7c311fb07ad0b3c5925001a60a3d0d3",
    "MPTABLE.TBL": "3a285fef1e4b6c6f144025f4a416bc0dced61d672af3210b93270a940e7cfeeb",
    "SOILPARM.TBL": "1e2275a32d8cd3b48ca693d22c0816df0013f83b6594ac632716361db337d58f",
}
ROUTING = {
    "__main__.py": "ed26526a77faa467404ef9898490c1dd84debaa04645317e8c97f74bbd3417a2",
    "output.py": "dda9dc57d912c6b019568128618ad6b6398f9a4a482da4a565daba9d93080be3",
}


def resident_bytes(path: Path, maximum: int = 16 * 1024**2) -> bytes:
    """Read an explicit resident leaf; refuse symlink parents and changing files."""
    absolute = path.absolute()
    for parent in (*absolute.parents, absolute):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_flags", 0) & 0x40000000:
            raise ValueError("symlink or dataless input")
    before = absolute.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
        raise ValueError("input is not a bounded regular file")
    descriptor = os.open(absolute, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("input identity changed before read")
        data = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    if len(data) > maximum or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_size, after.st_mtime_ns, after.st_ctime_ns
    ):
        raise ValueError("input changed during read")
    return data


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def qualify(docker_host: str, exports: Path, source_locks: Path, build_evidence: Path, output: Path) -> dict:
    if not docker_host.startswith("unix://"):
        raise ValueError("the diagnostic lane requires an explicit local Unix endpoint")
    output.mkdir(parents=True, exist_ok=False)
    blob = io.BytesIO()
    export_inventory = []
    with tarfile.open(fileobj=blob, mode="w") as archive:
        for name, expected in EXPORTS.items():
            data = resident_bytes(exports / name)
            observed = hashlib.sha256(data).hexdigest()
            if observed != expected:
                raise ValueError("export hash mismatch: " + name)
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode = len(data), 0o500
            archive.addfile(entry, io.BytesIO(data))
            export_inventory.append({"path": name, "bytes": len(data), "sha256": observed})

    locks = {}
    for name in ("NoahOWP", "troute"):
        raw = resident_bytes(source_locks / (name + "-archive-lock.json"), 2 * 1024**2)
        locks[name] = json.loads(raw)
        expected_commit = {"NoahOWP": "0abb891b48b043cc626c4e4bbd0efe54ad357fe1",
                           "troute": "533fbd98362efdafae62392308727de4f0d4cc20"}[name]
        if locks[name]["commit"] != expected_commit:
            raise ValueError("source lock commit mismatch: " + name)
    build_files = {}
    for name, expected in {
        "BUILD_EXPORT.json": "5ecfed96cffddad645ff2e4a9d1b4aaea2892176798f092ac2ed2c55f42b3746",
        "build/CMakeCache.txt": "88060947d4ecb0fd522833680ce1258db9f96ea566b0e4a44d8e81098b6be67d",
    }.items():
        raw = resident_bytes(build_evidence / name)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("historical export evidence hash mismatch")
        build_files[name] = {"bytes": len(raw), "sha256": expected}
        if name == "BUILD_EXPORT.json":
            build_export = json.loads(raw)
            if build_export["native_binary"]["sha256"] != EXPORTS["ngen-shared"]:
                raise ValueError("historical build export does not bind executable")
        else:
            for option in ("NGEN_WITH_MPI:BOOL=OFF", "NGEN_WITH_PYTHON:BOOL=OFF", "NGEN_WITH_ROUTING:INTERNAL=OFF"):
                if option.encode() not in raw.splitlines():
                    raise ValueError("historical native feature evidence mismatch")
    noah_files = {row["path"]: row["sha256"] for row in locks["NoahOWP"]["files"]}
    route_files = {row["path"]: row["sha256"] for row in locks["troute"]["files"]}
    for name, digest in TABLES.items():
        if noah_files.get("parameters/" + name) != digest:
            raise ValueError("Noah source table lock mismatch")
    for name, digest in ROUTING.items():
        if route_files.get("src/troute-nwm/src/nwm_routing/" + name) != digest:
            raise ValueError("routing source lock mismatch")

    base = ["docker", "--host", docker_host, "run", "--pull", "never", "--rm",
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "256",
            "--memory", "8g", "--cpus", "2", "--tmpfs", "/tmp:rw,exec,size=64m",
            "--tmpfs", "/work:rw,noexec,size=128m", "--tmpfs", "/work/job/outputs:rw,noexec,size=1g",
            "-e", "LD_LIBRARY_PATH=/tmp/runtime:/dmod/shared_libs:/usr/local/lib:/usr/lib64",
            "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OMP_NUM_THREADS=1",
            "-e", "OPENBLAS_NUM_THREADS=1", "-e", "MKL_NUM_THREADS=1"]
    records = []

    def probe(name, arguments, data=None):
        start = time.monotonic()
        container_name = "nrf-qualification-" + uuid.uuid4().hex
        try:
            process = subprocess.run(base + ["--name", container_name] + arguments,
                                     input=data, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "--host", docker_host, "rm", "--force", container_name],
                           capture_output=True, timeout=10, check=False)
            raise
        combined = process.stdout + process.stderr
        if len(combined) > 8 * 1024**2:
            raise ValueError("probe output exceeds bound")
        (output / (name + ".stdout")).write_bytes(process.stdout)
        (output / (name + ".stderr")).write_bytes(process.stderr)
        records.append({"name": name, "exit_code": process.returncode,
                        "elapsed_seconds": round(time.monotonic() - start, 6),
                        "stdout_sha256": hashlib.sha256(process.stdout).hexdigest(),
                        "stderr_sha256": hashlib.sha256(process.stderr).hexdigest()})
        if process.returncode:
            raise ValueError("inert probe failed: " + name)
        return process.stdout

    loader = """set -eu
mkdir /tmp/runtime
tar -xf - -C /tmp/runtime
for f in /tmp/runtime/ngen-shared /tmp/runtime/libiso_c_bmi.so /dmod/shared_libs/libcfebmi.so.1.0.0 /dmod/shared_libs/libsurfacebmi.so /dmod/shared_libs/libslothmodel.so.1.0.0; do
  echo "Inspecting $f"
  readelf -d "$f"
  /lib/ld-linux-aarch64.so.1 --library-path /tmp/runtime:/dmod/shared_libs:/usr/local/lib:/usr/lib64 --list "$f"
done
"""
    loaded = probe("loader", ["-i", "--entrypoint", "/bin/sh", IMAGE, "-c", loader], blob.getvalue())
    if loaded.count(b"libiso_c_bmi.so => /tmp/runtime/libiso_c_bmi.so") != 2:
        raise ValueError("export and Noah must both resolve the exact exported middleware")
    if b"not found" in loaded:
        raise ValueError("unresolved dynamic dependency")

    inventory_script = r'''
import hashlib,json,pathlib,platform,sys,importlib.metadata
import nwm_routing.__main__,nwm_routing.output
def digest(path):
    path=pathlib.Path(path)
    return {"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
components={name:digest('/dmod/shared_libs/'+name) for name in ['libcfebmi.so.1.0.0','libsurfacebmi.so','libslothmodel.so.1.0.0']}
tables={name:digest('/dmod/datasets/static/'+name) for name in ['GENPARM.TBL','MPTABLE.TBL','SOILPARM.TBL']}
route={name:digest('/ngen/.venv/lib64/python3.9/site-packages/nwm_routing/'+name) for name in ['__main__.py','output.py']}
site=pathlib.Path('/ngen/.venv/lib64/python3.9/site-packages')
route_tree={str(p.relative_to(site)):digest(p) for package in ['troute','nwm_routing'] for p in (site/package).rglob('*.py')}
if len(route_tree)>1024 or sum(item['bytes'] for item in route_tree.values())>128*1024**2:
    raise ValueError('routing source tree exceeds inventory bounds')
print(json.dumps({'platform':platform.platform(),'architecture':platform.machine(),'python':sys.version,'components':components,'tables':tables,'routing_source_files':route,'routing_installed_python':route_tree,'routing_module_imported':True,'routing_entrypoint_called':False,'packages':sorted(set((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),'limits':{k:pathlib.Path('/sys/fs/cgroup/'+k).read_text().strip() for k in ['cpu.max','memory.max','pids.max']},'component_aliases':{name:str(pathlib.Path('/dmod/shared_libs/'+name).readlink()) for name in ['libslothmodel.so','libcfebmi.so']},'native_source_commit':pathlib.Path('/ngen/ngen_url').read_text().strip(),'routing_source_commit':pathlib.Path('/ngen/troute_url').read_text().strip()},sort_keys=True))
'''
    inventory = json.loads(probe("inventory", ["--entrypoint", "/ngen/.venv/bin/python", IMAGE,
                                                "-c", inventory_script]))
    for field, expected in (("components", COMPONENTS), ("tables", TABLES), ("routing_source_files", ROUTING)):
        for name, digest in expected.items():
            if inventory[field][name]["sha256"] != digest:
                raise ValueError("image file hash mismatch: " + name)
    checked_routing = []
    for path, item in inventory["routing_installed_python"].items():
        matches = [source for source in route_files if source.endswith("/" + path)]
        if len(matches) != 1 or route_files[matches[0]] != item["sha256"]:
            raise ValueError("installed routing source differs from pinned source: " + path)
        checked_routing.append({"installed_path": path, "source_path": matches[0], "sha256": item["sha256"]})
    if inventory["architecture"] != "aarch64" or inventory["limits"] != {
        "cpu.max": "200000 100000", "memory.max": "8589934592", "pids.max": "256"
    }:
        raise ValueError("runtime architecture or enforced limits mismatch")
    if inventory["routing_source_commit"] != "https://github.com/CIROH-UA/t-route/tree/" + locks["troute"]["commit"]:
        raise ValueError("image routing source declaration differs from lock")
    receipt = {
        "schema_version": "ngen-reforecast-linux-diagnostic-admission/1.0",
        "runtime_id": "linux-arm64-export-image-diagnostic-v1",
        "status": "admitted_for_separately_frozen_diagnostic_references",
        "release_qualified": False, "clean_build_performed": False,
        "model_process_invocations": 0, "native_main_invoked": False,
        "image_manifest_sha256": IMAGE.removeprefix("sha256:"),
        "exports": export_inventory, "image_inventory": inventory, "probes": records,
        "historical_build_evidence": build_files,
        "routing_python_source_verification": checked_routing,
        "qualifier_sha256": hashlib.sha256(resident_bytes(Path(__file__))).hexdigest(),
        "source_commits": {"NoahOWP": locks["NoahOWP"]["commit"], "troute": locks["troute"]["commit"]},
        "native_features": {"MPI": False, "Python": False, "integrated_routing": False},
        "native_argument_vector": ["/tmp/runtime/ngen-shared", "config/public-watauga.gpkg", "all",
                                   "config/public-watauga.gpkg", "all", "config/realization.json"],
        "routing_argument_vector": ["/ngen/.venv/bin/python", "-m", "nwm_routing", "-f", "config/troute.yaml"],
        "native_environment": {"LD_LIBRARY_PATH": "/tmp/runtime:/dmod/shared_libs:/usr/local/lib:/usr/lib64",
                               "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                               "PYTHONDONTWRITEBYTECODE": "1"},
        "bounds": {"probe_wall_seconds": 60, "runtime_tmpfs_bytes": 64 * 1024**2,
                   "job_input_tmpfs_bytes": 128 * 1024**2, "job_output_tmpfs_bytes": 1024**3,
                   "memory_bytes": 8 * 1024**3, "cpus": 2, "pids": 256,
                   "network": "none", "root_filesystem": "read_only", "host_mounts": False},
        "limitations": ["Component source/toolchain/binary build attestations remain incomplete.",
                        "This is immutable export/image execution provenance, not a new clean build.",
                        "Integrated routing is disabled in the export; each logical reference needs a separate t-route process.",
                        "Input and diagnostic scientific admission plus a frozen invocation allowance remain required.",
                        "Rights, reproducible clean builder, physical equivalence and researcher reproduction remain release gates."]
    }
    receipt["runtime_identity_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    (output / "ADMISSION.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker-host", required=True)
    parser.add_argument("--export-root", required=True, type=Path)
    parser.add_argument("--source-lock-root", required=True, type=Path)
    parser.add_argument("--build-evidence-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    receipt = qualify(args.docker_host, args.export_root, args.source_lock_root, args.build_evidence_root, args.output_root)
    print(json.dumps({"status": receipt["status"], "runtime_identity_sha256": receipt["runtime_identity_sha256"],
                      "model_process_invocations": 0, "release_qualified": False}))


if __name__ == "__main__":
    main()
