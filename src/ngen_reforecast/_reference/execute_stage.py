"""Reserve every model process before launch and run one fixed isolated stage.

The host must first enforce the admitted immutable image, CPU/memory/pid/tmpfs,
read-only root and no-network settings. This script does not create a worker.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __package__:
    from . import common as c
else:
    import common as c
if __package__:
    from . import native_outputs
else:
    import native_outputs


def admission(protocol_path, admission_path, expected_sha):
    protocol = c.verify(c.load(protocol_path), "protocol_identity_sha256")
    if c.binding(admission_path)["sha256"] != expected_sha:
        raise c.ReferenceError("external frozen admission SHA differs")
    admitted = c.verify(c.load(admission_path), "admission_identity_sha256")
    if admitted["schema_version"] != "public-physical-reference-admission/0.1" or admitted["diagnostic_execution_admitted"] is not True:
        raise c.ReferenceError("diagnostic model execution is not admitted")
    if admitted["protocol_identity_sha256"] != protocol["protocol_identity_sha256"]:
        raise c.ReferenceError("admission does not bind this protocol")
    if not c.SHA.fullmatch(admitted["assembly_identity_sha256"]) or not c.SHA.fullmatch(admitted["runtime_identity_sha256"]):
        raise c.ReferenceError("admission requires sealed input/runtime identities")
    if protocol["bounds"]["model_process_allowance"] != 9:
        raise c.ReferenceError("separate nine-process reference allowance required")
    return protocol, admitted


def argv_for(admitted, stage):
    if stage == "native":
        if admitted["native_executable"] != "/tmp/runtime/ngen-shared":
            raise c.ReferenceError("unadmitted native executable path")
        return [admitted["native_executable"], "config/public-watauga.gpkg", "all",
                "config/public-watauga.gpkg", "all", "config/realization.json"]
    if stage == "routing":
        if admitted["routing_python"] != "/ngen/.venv/bin/python":
            raise c.ReferenceError("unadmitted routing interpreter")
        return [admitted["routing_python"], "-m", "nwm_routing", "-f", "config/troute.yaml"]
    raise c.ReferenceError("only native or routing stages are admitted")


def check_inputs(admitted, case_id, job_root):
    rows = admitted["case_inputs"][case_id]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1024:
        raise c.ReferenceError("bounded case input inventory required")
    seen = set()
    for row in rows:
        path = c.relative(row["path"])
        if path in seen or path.startswith("outputs/"):
            raise c.ReferenceError("duplicate or output path in case input inventory")
        seen.add(path)
        if c.binding(Path(job_root) / path, 16 * 1024 * 1024) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            raise c.ReferenceError("admitted case input bytes differ")
    actual = {row["path"] for row in c.inventory(job_root, 1024 * 1024 * 1024) if not row["path"].startswith("outputs/")}
    if seen != actual:
        raise c.ReferenceError("unbound input file or missing admitted case file")
    return c.seal({"case_id": case_id, "files": rows}, "case_input_identity_sha256")["case_input_identity_sha256"]


def reserve(protocol_path, admission_path, expected_sha, case_id, stage, ledger_root, attempt_id, remaining_seconds=1800):
    protocol, admitted = admission(protocol_path, admission_path, expected_sha)
    cases = [case for case in protocol["cases"] if case["case_id"] == case_id]
    if len(cases) != 1 or case_id not in admitted["case_inputs"]:
        raise c.ReferenceError("case absent from protocol/admission")
    if not 0 < remaining_seconds <= protocol["bounds"]["logical_job_wall_seconds"]:
        raise c.ReferenceError("remaining logical job deadline exceeds allowance")
    if not isinstance(attempt_id, str) or not __import__("re").fullmatch(r"[a-zA-Z0-9-]{1,80}", attempt_id):
        raise c.ReferenceError("bounded safe attempt identity required")
    root = Path(ledger_root)
    root.mkdir(exist_ok=True, parents=True)
    existing = sorted(root.glob("PROCESS-*.json"))
    if len(existing) >= protocol["bounds"]["model_process_allowance"]:
        raise c.ReferenceError("global model process allowance exhausted")
    for i, path in enumerate(existing, 1):
        r = c.verify(c.load(path), "reservation_identity_sha256")
        if path.name != "PROCESS-%02d.json" % i or r["process_number"] != i or r["protocol_identity_sha256"] != protocol["protocol_identity_sha256"]:
            raise c.ReferenceError("global launch ledger has missing, duplicate or foreign records")
    number = len(existing) + 1
    result = c.seal({"schema_version": "physical-process-reservation/0.1", "process_number": number,
                     "attempt_id": attempt_id, "case_id": case_id, "stage": stage,
                     "protocol_identity_sha256": protocol["protocol_identity_sha256"],
                     "admission_identity_sha256": admitted["admission_identity_sha256"],
                     "admission_file_sha256": expected_sha, "assembly_identity_sha256": admitted["assembly_identity_sha256"],
                     "runtime_identity_sha256": admitted["runtime_identity_sha256"],
                     "case_input_identity_sha256": c.seal({"case_id": case_id, "files": admitted["case_inputs"][case_id]}, "case_input_identity_sha256")["case_input_identity_sha256"],
                     "argv": argv_for(admitted, stage), "remaining_job_wall_seconds": remaining_seconds,
                     "reserved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, "reservation_identity_sha256")
    c.write_new(root / ("PROCESS-%02d.json" % number), result)
    return result


def run(protocol_path, admission_path, expected_sha, reservation_path, job_root, receipt_root):
    protocol, admitted = admission(protocol_path, admission_path, expected_sha)
    reservation = c.verify(c.load(reservation_path), "reservation_identity_sha256")
    case_id, stage = reservation["case_id"], reservation["stage"]
    if reservation["protocol_identity_sha256"] != protocol["protocol_identity_sha256"] or reservation["admission_file_sha256"] != expected_sha:
        raise c.ReferenceError("reservation is not for this frozen admission/protocol")
    if reservation["admission_identity_sha256"] != admitted["admission_identity_sha256"] or not 1 <= reservation["process_number"] <= 9:
        raise c.ReferenceError("reservation admission or process allowance differs")
    argv = argv_for(admitted, stage)
    if argv != reservation["argv"]:
        raise c.ReferenceError("reservation process argv differs")
    input_identity = check_inputs(admitted, case_id, job_root)
    if input_identity != reservation["case_input_identity_sha256"]:
        raise c.ReferenceError("case input identity differs from launch reservation")
    if c.binding(admitted["native_executable"])["sha256"] != admitted["native_executable_sha256"]:
        raise c.ReferenceError("native executable bytes differ before model launch")
    if stage == "routing":
        # A zero-exit Fortran STOP can leave empty/incomplete files. Validate the
        # full land/nexus contract before creating a routing process at all.
        native_outputs.validate(protocol, case_id, Path(job_root) / "outputs")
        prior_path = Path(receipt_root).parent / "native" / "RECEIPT.json"
        prior = c.verify(c.load(prior_path), "process_receipt_identity_sha256")
        if prior["returncode"] != 0 or prior["termination_reason"] is not None or prior.get("native_output_contract", {}).get("native_output_contract_complete") is not True:
            raise c.ReferenceError("routing requires a successful complete native-output receipt")
        prior_reservation = c.verify(prior["reservation"], "reservation_identity_sha256")
        if prior_reservation["case_id"] != case_id or prior_reservation["admission_file_sha256"] != expected_sha or prior_reservation["process_number"] >= reservation["process_number"]:
            raise c.ReferenceError("routing native-stage provenance differs")
    receipt_root = Path(receipt_root)
    receipt_root.mkdir(exist_ok=False, parents=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    begin = time.monotonic()
    environment = dict(os.environ)
    environment.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       NUMEXPR_NUM_THREADS="1", TZ="UTC", PYTHONDONTWRITEBYTECODE="1")
    environment["LD_LIBRARY_PATH"] = admitted["native_ld_library_path"]
    reason = None
    with (receipt_root / "stdout.log").open("xb") as stdout, (receipt_root / "stderr.log").open("xb") as stderr:
        process = subprocess.Popen(argv, cwd=job_root, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
        while process.poll() is None:
            elapsed = time.monotonic() - begin
            if elapsed > reservation["remaining_job_wall_seconds"]:
                reason = "logical_job_wall_limit"
            try:
                c.inventory(Path(job_root) / "outputs", protocol["bounds"]["job_output_bytes"], hash_files=False)
                c.inventory(receipt_root, 128 * 1024 * 1024, hash_files=False)
            except c.ReferenceError:
                reason = "output_or_log_byte_limit"
            if reason:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                break
            time.sleep(0.25)
        code = process.wait()
    elapsed = time.monotonic() - begin
    verification_error = None
    native_contract = None
    if stage == "native":
        try:
            native_contract = native_outputs.validate(protocol, case_id, Path(job_root) / "outputs",
                                                       receipt_root / "stdout.log", receipt_root / "stderr.log")
        except (c.ReferenceError, OSError, UnicodeError) as error:
            native_contract = {"native_output_contract_complete": False, "error": type(error).__name__ + ": " + str(error)}
            verification_error = native_contract["error"]
    try:
        after = check_inputs(admitted, case_id, job_root)
    except (c.ReferenceError, OSError) as error:
        after = None
        verification_error = (verification_error or "") + type(error).__name__ + ": " + str(error)
    try:
        outputs = c.inventory(Path(job_root) / "outputs", protocol["bounds"]["job_output_bytes"])
    except (c.ReferenceError, OSError) as error:
        outputs = None
        verification_error = (verification_error or "") + type(error).__name__ + ": " + str(error)
    report = c.seal({"schema_version": "physical-process-receipt/0.1", "reservation": reservation,
                     "case_input_identity_sha256_after": after, "started_at_utc": started,
                     "elapsed_seconds": elapsed, "returncode": code, "termination_reason": reason,
                     "stdout": c.binding(receipt_root / "stdout.log", protocol["bounds"]["job_output_bytes"]),
                     "stderr": c.binding(receipt_root / "stderr.log", protocol["bounds"]["job_output_bytes"]),
                     "outputs_after": outputs, "post_launch_verification_error": verification_error,
                     "native_output_contract": native_contract,
                     "executor": c.binding(Path(__file__)), "native_main_invoked": stage == "native",
                     "routing_main_invoked": stage == "routing"}, "process_receipt_identity_sha256")
    c.write_new(receipt_root / "RECEIPT.json", report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("reserve")
    b = sub.add_parser("run")
    for parser in (a, b):
        for name in ("protocol", "admission", "admission_sha256"):
            parser.add_argument(name)
    for name in ("case_id", "stage", "ledger_root", "attempt_id"):
        a.add_argument(name)
    a.add_argument("--remaining-seconds", type=float, default=1800)
    for name in ("reservation", "job_root", "receipt_root"):
        b.add_argument(name)
    v = p.parse_args()
    if v.action == "reserve":
        result = reserve(v.protocol, v.admission, v.admission_sha256, v.case_id, v.stage,
                         v.ledger_root, v.attempt_id, v.remaining_seconds)
        print(result["reservation_identity_sha256"])
    else:
        result = run(v.protocol, v.admission, v.admission_sha256, v.reservation, v.job_root, v.receipt_root)
        print(result["process_receipt_identity_sha256"])
        if result["returncode"] != 0 or result["post_launch_verification_error"] is not None:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
