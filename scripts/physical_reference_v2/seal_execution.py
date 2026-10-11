"""Bind two successful model stages and the durable launch ledger to a job."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __package__:
    from . import common as c
else:
    import common as c
if __package__:
    from . import execute_stage as e
else:
    import execute_stage as e


def seal_execution(protocol_path, admission_path, admission_sha, native_receipt, routing_receipt, ledger_root, output_root, destination):
    protocol, admitted = e.admission(protocol_path, admission_path, admission_sha)
    ledger = [c.verify(c.load(path), "reservation_identity_sha256") for path in sorted(Path(ledger_root).glob("PROCESS-*.json"))]
    if not 1 <= len(ledger) <= protocol["bounds"]["model_process_allowance"] or [r["process_number"] for r in ledger] != list(range(1, len(ledger) + 1)):
        raise c.ReferenceError("durable ledger is incomplete or exceeds allowance")
    if any(r["protocol_identity_sha256"] != protocol["protocol_identity_sha256"] for r in ledger):
        raise c.ReferenceError("foreign protocol in launch ledger")
    receipts = []
    for stage, path in (("native", Path(native_receipt)), ("routing", Path(routing_receipt))):
        receipt = c.verify(c.load(path), "process_receipt_identity_sha256")
        reservation = c.verify(receipt["reservation"], "reservation_identity_sha256")
        if receipt["returncode"] != 0 or receipt["termination_reason"] is not None or receipt.get("post_launch_verification_error") is not None or reservation["stage"] != stage:
            raise c.ReferenceError("two successful separately ledgered model stages are required")
        if stage == "native" and receipt.get("native_output_contract", {}).get("native_output_contract_complete") is not True:
            raise c.ReferenceError("native zero exit cannot replace complete land/nexus output admission")
        if ledger[reservation["process_number"] - 1] != reservation or reservation["admission_file_sha256"] != admission_sha or reservation["argv"] != e.argv_for(admitted, stage):
            raise c.ReferenceError("model stage is not bound to frozen admission and launch ledger")
        if reservation["case_input_identity_sha256"] != receipt["case_input_identity_sha256_after"]:
            raise c.ReferenceError("input assets changed during model execution")
        for name in ("stdout", "stderr"):
            if c.binding(path.parent / (name + ".log"), 128 * 1024 * 1024) != receipt[name]:
                raise c.ReferenceError("model process log differs from receipt")
        receipts.append(receipt)
    native, routing = receipts
    nr, rr = native["reservation"], routing["reservation"]
    if nr["case_id"] != rr["case_id"] or nr["process_number"] >= rr["process_number"] or nr["case_input_identity_sha256"] != rr["case_input_identity_sha256"]:
        raise c.ReferenceError("land and routing stages do not belong to one ordered independent job")
    if native["elapsed_seconds"] + routing["elapsed_seconds"] > protocol["bounds"]["logical_job_wall_seconds"]:
        raise c.ReferenceError("logical job exceeds combined wall allowance")
    raw = c.inventory(output_root, protocol["bounds"]["job_output_bytes"])
    if raw != routing["outputs_after"]:
        raise c.ReferenceError("raw outputs changed since successful routing receipt")
    indexed = {r["path"]: r for r in raw}
    if any(indexed.get(r["path"]) != r for r in native["outputs_after"]):
        raise c.ReferenceError("land/nexus outputs changed during routing")
    result = c.seal({"schema_version": "physical-job-execution/0.1", "case_id": nr["case_id"],
                     "protocol_identity_sha256": protocol["protocol_identity_sha256"],
                     "admission_file_sha256": admission_sha, "admission_identity_sha256": admitted["admission_identity_sha256"],
                     "assembly_identity_sha256": admitted["assembly_identity_sha256"],
                     "runtime_identity_sha256": admitted["runtime_identity_sha256"],
                     "case_input_identity_sha256": nr["case_input_identity_sha256"],
                     "process_receipts": receipts, "reservation_ledger": ledger, "raw_outputs": raw,
                     "model_processes_this_job": 2, "global_reserved_processes_at_seal": len(ledger)}, "execution_identity_sha256")
    c.write_new(destination, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "admission", "admission_sha256", "native_receipt", "routing_receipt", "ledger_root", "output_root", "destination"):
        p.add_argument(name)
    a = p.parse_args()
    print(seal_execution(a.protocol, a.admission, a.admission_sha256, a.native_receipt, a.routing_receipt, a.ledger_root, a.output_root, a.destination)["execution_identity_sha256"])


if __name__ == "__main__":
    main()
