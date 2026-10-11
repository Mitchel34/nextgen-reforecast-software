"""Synthetic contract fixtures test reference admission, clocks and receipt binding.

These tests execute no native or routing model and establish no physical result.
"""
from datetime import datetime, timedelta, timezone
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts/physical_reference"
sys.path.insert(0, str(SCRIPTS))
import common as common
import audit_outputs as audit
import execute_stage as execute
import seal_execution as execution
import compare_reference_set as comparison


class ReferenceContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".local")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.origin = datetime(2021, 12, 1, tzinfo=timezone.utc)
        self.protocol = common.seal({"schema_version": "public-physical-reference-protocol/0.1",
            "experiment_id": "synthetic-contract-test", "fixture_id": "synthetic-no-model-test",
            "catchment_ids": ["cat-1"], "nexus_ids": ["nex-2"], "routing_feature_ids": ["wb-1"],
            "selected_routing_feature_id": "wb-1", "routing_output_interval_seconds": 300,
            "cases": [{"case_id": "history", "origin_time_utc": "2021-12-01T00:00:00Z",
                       "stop_time_utc_exclusive": "2021-12-01T01:00:00Z", "provider_hours": 1,
                       "issue_time_utc": None}],
            "bounds": {"job_output_bytes": 1024 * 1024, "model_process_allowance": 9,
                       "logical_job_wall_seconds": 1800}}, "protocol_identity_sha256")
        self.protocol_path = self.base / "protocol.json"
        common.write_new(self.protocol_path, self.protocol)
        self.job = self.base / "job"
        (self.job / "config").mkdir(parents=True)
        (self.job / "outputs/ngen").mkdir(parents=True)
        (self.job / "outputs/troute").mkdir()
        (self.job / "config/realization.json").write_text("{}\n")
        self.admitted = common.seal({"schema_version": "public-physical-reference-admission/0.1",
            "diagnostic_execution_admitted": True,
            "protocol_identity_sha256": self.protocol["protocol_identity_sha256"],
            "assembly_identity_sha256": "a" * 64, "runtime_identity_sha256": "b" * 64,
            "native_executable": "/tmp/runtime/ngen-shared", "native_executable_sha256": "c" * 64,
            "native_ld_library_path": "/tmp/runtime:/dmod/shared_libs:/usr/local/lib:/usr/lib64",
            "routing_python": "/ngen/.venv/bin/python",
            "case_inputs": {"history": [{"path": "config/realization.json", **common.binding(self.job / "config/realization.json")}]}
        }, "admission_identity_sha256")
        self.admission_path = self.base / "admission.json"
        common.write_new(self.admission_path, self.admitted)
        self.admission_sha = common.binding(self.admission_path)["sha256"]

    def native_csv(self, hours=1, fields=None, value="1"):
        fields = fields or audit.CFE_FIELDS
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["Time Step", "Time", *fields])
        for i in range(hours):
            writer.writerow([i, (self.origin + i * timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"), *([value] * len(fields))])
        return output.getvalue()

    def routing_csv(self, steps=12):
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(audit.ROUTE_FIELDS)
        for i in range(steps):
            writer.writerow(["wb-1", (self.origin + (i + 1) * timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"), 1, 2, 3])
        return output.getvalue()

    def test_complete_native_clock_is_interval_start(self):
        path = self.base / "native.csv"
        path.write_text(self.native_csv(hours=2))
        self.assertEqual(len(audit.native_csv(path, self.origin, 2, audit.CFE_FIELDS)), 2)

    def test_native_missing_extra_duplicate_and_shifted_clock_refused(self):
        good = self.native_csv(hours=2)
        variants = [self.native_csv(hours=1), self.native_csv(hours=3),
                    good.replace("1,2021-12-01 01:00:00", "0,2021-12-01 00:00:00"),
                    good.replace("2021-12-01 00:00:00", "2021-12-01 01:00:00")]
        for raw in variants:
            path = self.base / "bad.csv"
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(common.ReferenceError):
                audit.native_csv(path, self.origin, 2, audit.CFE_FIELDS)

    def test_ragged_nonfinite_and_negative_runoff_refused(self):
        for raw in [self.native_csv(value="nan"), self.native_csv(value="-1"),
                    self.native_csv().replace(",1,1\n", ",1\n")]:
            path = self.base / "bad.csv"
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(common.ReferenceError):
                audit.native_csv(path, self.origin, 1, audit.CFE_FIELDS)

    def test_signed_storage_change_is_admitted(self):
        values = ["1"] * len(audit.CFE_FIELDS)
        values[audit.CFE_FIELDS.index("SOIL_STORAGE_CHANGE")] = "-0.1"
        path = self.base / "signed.csv"
        path.write_text(",".join(["Time Step", "Time", *audit.CFE_FIELDS]) + "\n" +
                        ",".join(["0", "2021-12-01 00:00:00", *values]) + "\n")
        self.assertEqual(audit.native_csv(path, self.origin, 1, audit.CFE_FIELDS)[0][-3], -0.1)

    def test_full_five_minute_routing_before_lead_extraction(self):
        path = self.base / "routing.csv"
        path.write_text(self.routing_csv())
        self.assertEqual(len(audit.routing_csv(path, self.origin, 1, ["wb-1"])["wb-1"]), 12)
        for raw in [self.routing_csv(11), self.routing_csv(13), self.routing_csv().replace("wb-1", "wb-9"),
                    self.routing_csv().replace("00:10:00Z", "00:05:00Z"),
                    self.routing_csv().replace(",1,2,3", ",nan,2,3"),
                    self.routing_csv().replace(",1,2,3", ",-1,2,3")]:
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(common.ReferenceError):
                audit.routing_csv(path, self.origin, 1, ["wb-1"])

    def test_external_admission_sha_and_seal_both_required(self):
        execute.admission(self.protocol_path, self.admission_path, self.admission_sha)
        with self.assertRaises(common.ReferenceError):
            execute.admission(self.protocol_path, self.admission_path, "d" * 64)
        changed = dict(self.admitted)
        changed["diagnostic_execution_admitted"] = False
        self.admission_path.write_text(json.dumps(changed))
        with self.assertRaises(common.ReferenceError):
            execute.admission(self.protocol_path, self.admission_path, common.binding(self.admission_path)["sha256"])

    def test_input_mutation_and_unbound_file_refused(self):
        execute.check_inputs(self.admitted, "history", self.job)
        (self.job / "unbound.txt").write_text("unbound")
        with self.assertRaises(common.ReferenceError):
            execute.check_inputs(self.admitted, "history", self.job)
        (self.job / "unbound.txt").unlink()
        (self.job / "config/realization.json").write_text('{"changed":true}\n')
        with self.assertRaises(common.ReferenceError):
            execute.check_inputs(self.admitted, "history", self.job)

    def test_every_reservation_consumes_allowance_even_without_completion(self):
        ledger = self.base / "ledger"
        for i in range(9):
            execute.reserve(self.protocol_path, self.admission_path, self.admission_sha,
                            "history", "native", ledger, "synthetic-%d" % i)
        self.assertEqual(len(list(ledger.glob("PROCESS-*.json"))), 9)
        with self.assertRaises(common.ReferenceError):
            execute.reserve(self.protocol_path, self.admission_path, self.admission_sha,
                            "history", "routing", ledger, "synthetic-excess")

    def test_missing_launch_number_and_changed_command_refused(self):
        ledger = self.base / "ledger"
        execute.reserve(self.protocol_path, self.admission_path, self.admission_sha, "history", "native", ledger, "test")
        (ledger / "PROCESS-01.json").rename(ledger / "PROCESS-02.json")
        with self.assertRaises(common.ReferenceError):
            execute.reserve(self.protocol_path, self.admission_path, self.admission_sha, "history", "routing", ledger, "test2")
        changed = dict(self.admitted)
        changed["native_executable"] = "/bin/true"
        with self.assertRaises(common.ReferenceError):
            execute.argv_for(changed, "native")

    def test_metadata_only_live_scan_does_not_hash_active_outputs(self):
        path = self.job / "outputs/growing.log"
        path.write_text("active output")
        with patch.object(common, "binding", side_effect=AssertionError("active payload must not be hashed")):
            result = common.inventory(self.job / "outputs", 1024, hash_files=False)
        self.assertEqual(result[0]["bytes"], 13)

    def test_resident_symlink_and_byte_bounds_refused(self):
        real = self.base / "real.txt"
        real.write_text("1234")
        link = self.base / "link.txt"
        link.symlink_to(real)
        with self.assertRaises(common.ReferenceError):
            common.read(link)
        with self.assertRaises(common.ReferenceError):
            common.read(real, 3)
        with self.assertRaises(common.ReferenceError):
            common.inventory(self.base, 1, hash_files=False)

    def test_reference_cannot_seal_csv_without_execution_receipts(self):
        path = self.base / "no-execution.json"
        common.write_new(path, common.seal({"schema_version": "physical-job-execution/0.1",
                                           "case_id": "history"}, "execution_identity_sha256"))
        with self.assertRaises((common.ReferenceError, KeyError)):
            audit.audit(self.protocol_path, "history", self.job / "outputs", self.base / "routing.csv",
                        self.base / "normalization.json", path, self.admission_path, self.base / "reference")
        self.assertFalse((self.base / "reference").exists())

    def complete_synthetic_execution(self):
        outputs = self.job / "outputs"
        (outputs / "ngen/cat-1.csv").write_text(self.native_csv())
        (outputs / "ngen/nex-2_output.csv").write_text("0, 2021-12-01 00:00:00, 1\n")
        ledger = self.base / "ledger"
        receipts = []
        for i, stage in enumerate(("native", "routing")):
            reservation = execute.reserve(self.protocol_path, self.admission_path, self.admission_sha,
                                          "history", stage, ledger, "synthetic-" + stage)
            if stage == "routing":
                (outputs / "troute/synthetic.nc").write_bytes(b"Synthetic source binding only; not valid NetCDF or model output.")
            folder = self.base / (stage + "-receipt")
            folder.mkdir()
            for name in ("stdout", "stderr"):
                (folder / (name + ".log")).write_text("Synthetic test log; no model was executed.\n")
            receipt = common.seal({"schema_version": "physical-process-receipt/0.1", "reservation": reservation,
                "case_input_identity_sha256_after": reservation["case_input_identity_sha256"],
                "started_at_utc": "2026-10-10T00:00:00Z", "elapsed_seconds": 1.0,
                "returncode": 0, "termination_reason": None, "post_launch_verification_error": None,
                "stdout": common.binding(folder / "stdout.log"), "stderr": common.binding(folder / "stderr.log"),
                "outputs_after": common.inventory(outputs, 1024 * 1024),
                "executor": common.binding(SCRIPTS / "execute_stage.py"),
                "native_main_invoked": stage == "native", "routing_main_invoked": stage == "routing"}, "process_receipt_identity_sha256")
            path = folder / "RECEIPT.json"
            common.write_new(path, receipt)
            receipts.append(path)
        execution_path = self.base / "EXECUTION.json"
        execution.seal_execution(self.protocol_path, self.admission_path, self.admission_sha,
                                 *receipts, ledger, outputs, execution_path)
        routing = self.base / "routing.csv"
        routing.write_text(self.routing_csv())
        normal = common.seal({"schema_version": "routing-normalization/0.1", "case_id": "history",
            "protocol_identity_sha256": self.protocol["protocol_identity_sha256"],
            "normalized_csv": common.binding(routing),
            "raw_sources": [{"path": "troute/synthetic.nc", **common.binding(outputs / "troute/synthetic.nc")}]
        }, "normalization_identity_sha256")
        norm_path = self.base / "NORMALIZATION.json"
        common.write_new(norm_path, normal)
        return execution_path, routing, norm_path, receipts, ledger

    def test_complete_arrays_sealed_only_with_bound_successful_execution(self):
        ep, route, norm, _, _ = self.complete_synthetic_execution()
        result = audit.audit(self.protocol_path, "history", self.job / "outputs", route, norm,
                             ep, self.admission_path, self.base / "reference")
        self.assertEqual((result["complete_catchment_rows"], result["complete_nexus_rows"], result["complete_routing_rows"]), (1, 1, 12))
        self.assertFalse(result["forecast_skill_validated"])
        arrays = common.load(self.base / "reference/arrays.json")
        self.assertEqual(arrays["valid_time_utc"], ["2021-12-01T01:00:00Z"])
        self.assertEqual(arrays["routing_valid_time_utc"][-1], "2021-12-01T01:00:00Z")

    def test_failed_stage_log_mutation_and_raw_output_mutation_cannot_seal(self):
        ep, route, norm, receipts, ledger = self.complete_synthetic_execution()
        failed = common.load(receipts[1])
        failed.pop("process_receipt_identity_sha256")
        failed["returncode"] = 1
        receipts[1].write_text(json.dumps(common.seal(failed, "process_receipt_identity_sha256")))
        with self.assertRaises(common.ReferenceError):
            execution.seal_execution(self.protocol_path, self.admission_path, self.admission_sha,
                                     *receipts, ledger, self.job / "outputs", self.base / "failed.json")
        (self.job / "outputs/troute/synthetic.nc").write_bytes(b"Changed raw source")
        with self.assertRaises(common.ReferenceError):
            audit.audit(self.protocol_path, "history", self.job / "outputs", route, norm,
                        ep, self.admission_path, self.base / "bad-reference")

    def test_prefix_consistency_checks_full_five_minute_routing(self):
        full = {"catchment_values": {"cat-1": [[1], [2]]}, "nexus_values": {"nex-2": [[1], [2]]},
                "routing_values": {"wb-1": [[1]] * 24}}
        changed = json.loads(json.dumps(full))
        changed["routing_values"]["wb-1"][5] = [2]
        counts, examples = comparison.prefix_differences(full, changed, 1, 300)
        self.assertEqual(counts["routing_values"], 1)
        self.assertEqual(examples[0]["step_index"], 5)
        self.assertEqual(comparison.prefix_differences(full, full, 1, 300)[0]["routing_values"], 0)


if __name__ == "__main__":
    unittest.main()
