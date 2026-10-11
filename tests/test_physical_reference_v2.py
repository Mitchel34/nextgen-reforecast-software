"""Fortran zero-exit STOP regressions use mocked processes and synthetic bytes."""
from datetime import datetime, timedelta, timezone
import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts/physical_reference_v2"
from scripts.physical_reference_v2 import native_outputs as native
from scripts.physical_reference_v2 import execute_stage as executor
c = executor.c


class CompleteNativeBeforeRouting(unittest.TestCase):
    def test_exact_v2_module_namespace_is_used(self):
        self.assertEqual(Path(executor.__file__).parent, SCRIPTS)
        self.assertEqual(Path(executor.native_outputs.__file__).parent, SCRIPTS)
        self.assertEqual(Path(executor.c.__file__).parent, SCRIPTS)
        self.assertEqual(executor.__name__, "scripts.physical_reference_v2.execute_stage")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".local")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.job = self.base / "job"
        (self.job / "config").mkdir(parents=True)
        (self.job / "outputs/ngen").mkdir(parents=True)
        (self.job / "outputs/troute").mkdir()
        (self.job / "config/realization.json").write_text("{}\n")
        self.protocol = c.seal({"schema_version": "public-physical-reference-protocol/0.1",
            "catchment_ids": ["cat-1"], "nexus_ids": ["nex-2"],
            "cases": [{"case_id": "history", "provider_hours": 2,
                       "origin_time_utc": "2021-12-01T00:00:00Z"}],
            "bounds": {"model_process_allowance": 9, "logical_job_wall_seconds": 1800,
                       "job_output_bytes": 1024 * 1024}}, "protocol_identity_sha256")
        self.protocol_path = self.base / "PROTOCOL.json"
        c.write_new(self.protocol_path, self.protocol)
        self.admitted = c.seal({"schema_version": "public-physical-reference-admission/0.1",
            "diagnostic_execution_admitted": True,
            "protocol_identity_sha256": self.protocol["protocol_identity_sha256"],
            "assembly_identity_sha256": "a" * 64, "runtime_identity_sha256": "b" * 64,
            "native_executable": "/tmp/runtime/ngen-shared", "native_executable_sha256": "c" * 64,
            "native_ld_library_path": "/tmp/runtime:/dmod/shared_libs:/usr/local/lib:/usr/lib64",
            "routing_python": "/ngen/.venv/bin/python",
            "case_inputs": {"history": [{"path": "config/realization.json", **c.binding(self.job / "config/realization.json")}]}
        }, "admission_identity_sha256")
        self.admission_path = self.base / "ADMISSION.json"
        c.write_new(self.admission_path, self.admitted)
        self.admission_sha = c.binding(self.admission_path)["sha256"]
        self.good_outputs()

    def good_outputs(self):
        origin = datetime(2021, 12, 1, tzinfo=timezone.utc)
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["Time Step", "Time", *native.FIELDS])
        writer.writerows([[i, (origin + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S"), *([1] * len(native.FIELDS))] for i in range(2)])
        (self.job / "outputs/ngen/cat-1.csv").write_text(out.getvalue())
        (self.job / "outputs/ngen/nex-2_output.csv").write_text("0, 2021-12-01 00:00:00, 1\n1, 2021-12-01 01:00:00, 1\n")

    def binding_patch(self):
        old = c.binding
        def binding(path, *args, **kwargs):
            if str(path) == "/tmp/runtime/ngen-shared":
                return {"bytes": 1, "sha256": "c" * 64}
            return old(path, *args, **kwargs)
        return patch.object(c, "binding", side_effect=binding)

    def reservation(self, stage):
        value = executor.reserve(self.protocol_path, self.admission_path, self.admission_sha,
                                 "history", stage, self.base / "ledger", "synthetic-" + stage)
        return self.base / "ledger" / ("PROCESS-%02d.json" % value["process_number"])

    def test_complete_contract_admits_full_land_and_nexus_rows(self):
        report = native.validate(self.protocol, "history", self.job / "outputs")
        self.assertTrue(report["native_output_contract_complete"])
        self.assertEqual(report["complete_catchment_rows"], 2)
        self.assertEqual(report["complete_nexus_rows"], 2)

    def test_header_only_missing_nexus_ragged_and_shifted_clock_refused(self):
        path = self.job / "outputs/ngen/cat-1.csv"
        good = path.read_text()
        cases = [good.splitlines()[0] + "\n", good.replace("2021-12-01 01:00:00", "2021-12-01 00:00:00"),
                 good.replace(",1,1\n", ",1\n"), good.replace(",1,1\n", ",1,nan\n")]
        for raw in cases:
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(c.ReferenceError):
                native.validate(self.protocol, "history", self.job / "outputs")
        path.write_text(good)
        (self.job / "outputs/ngen/nex-2_output.csv").unlink()
        with self.assertRaises(c.ReferenceError):
            native.validate(self.protocol, "history", self.job / "outputs")

    def test_fatal_log_cannot_be_admitted_even_with_complete_csv(self):
        log = self.base / "fatal.log"
        log.write_text("FATAL ERROR model options incompatible\nSTOP\n")
        with self.assertRaises(c.ReferenceError):
            native.validate(self.protocol, "history", self.job / "outputs", log)

    def test_zero_exit_stop_is_preserved_as_failed_native_receipt(self):
        class Process:
            def poll(self): return 0
            def wait(self, timeout=None): return 0
        def fake_launch(*args, **kwargs):
            kwargs["stdout"].write(b"FATAL ERROR model options incompatible\n")
            return Process()
        reservation = self.reservation("native")
        with self.binding_patch(), patch.object(executor.subprocess, "Popen", side_effect=fake_launch):
            report = executor.run(self.protocol_path, self.admission_path, self.admission_sha,
                                  reservation, self.job, self.base / "receipts/native")
        self.assertEqual(report["returncode"], 0)
        self.assertFalse(report["native_output_contract"]["native_output_contract_complete"])
        self.assertIsNotNone(report["post_launch_verification_error"])
        self.assertTrue((self.base / "receipts/native/RECEIPT.json").exists())

    def test_incomplete_zero_exit_receipt_blocks_router_before_popen(self):
        native_reservation = self.reservation("native")
        reservation = self.reservation("routing")
        folder = self.base / "receipts/native"
        folder.mkdir(parents=True)
        c.write_new(folder / "RECEIPT.json", c.seal({"returncode": 0, "termination_reason": None,
            "native_output_contract": {"native_output_contract_complete": False},
            "reservation": c.load(native_reservation)}, "process_receipt_identity_sha256"))
        with self.binding_patch(), patch.object(executor.subprocess, "Popen") as launch:
            with self.assertRaises(c.ReferenceError):
                executor.run(self.protocol_path, self.admission_path, self.admission_sha,
                             reservation, self.job, self.base / "receipts/routing")
            launch.assert_not_called()
        self.assertFalse((self.base / "receipts/routing").exists())


if __name__ == "__main__":
    unittest.main()
