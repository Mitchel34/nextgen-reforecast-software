"""Archive mechanics use synthetic artifacts, never model execution."""
import hashlib
import json
import os
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ngen_reforecast import archive
from ngen_reforecast.campaign import iter_expected_rows
from ngen_reforecast.execution_lock import _construct


ROOT = Path(__file__).resolve().parents[1]


class ResidentArchivePrimitives(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".local/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.destination = self.root / "destination"
        self.source.mkdir()
        self.destination.mkdir()

    def test_empty_logs_copy_without_overwrite_and_hash_verification(self):
        (self.source / "stderr.log").write_bytes(b"")
        binding = archive._binding(self.source, "stderr.log")
        self.assertEqual(binding, {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()})
        archive._copy_file(self.source, "stderr.log", self.destination, "logs/stderr.log", binding)
        self.assertEqual(archive._binding(self.destination, "logs/stderr.log"), binding)
        with self.assertRaises(FileExistsError):
            archive._copy_file(self.source, "stderr.log", self.destination, "logs/stderr.log", binding)

    def test_symlink_leaf_parent_and_special_file_refused(self):
        (self.source / "real").write_bytes(b"secret")
        (self.source / "link").symlink_to("real")
        with self.assertRaises(archive.ArchiveError):
            archive._binding(self.source, "link")
        parent_link = self.root / "linked-source"
        parent_link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(archive.ArchiveError):
            archive._binding(parent_link, "real")
        with self.assertRaises(archive.ArchiveError):
            archive._inventory(self.source)
        (self.source / "link").unlink()
        os.mkfifo(self.source / "fifo")
        with self.assertRaises(archive.ArchiveError):
            archive._inventory(self.source)

    def test_read_and_inventory_byte_bounds_are_enforced(self):
        (self.source / "data").write_bytes(b"12345")
        with self.assertRaises(archive.ArchiveError):
            archive._binding(self.source, "data", 4)
        with patch.object(archive, "MAX_ARCHIVE_BYTES", 4), self.assertRaises(archive.ArchiveError):
            archive._inventory(self.source)

    def test_copy_refuses_changed_source_and_wrong_expected_digest(self):
        p = self.source / "data"
        p.write_bytes(b"unchanged")
        binding = archive._binding(self.source, "data")
        p.write_bytes(b"corrupted")
        with self.assertRaises(archive.ArchiveError):
            archive._copy_file(self.source, "data", self.destination, "bad", binding)
        binding = archive._binding(self.source, "data")
        original_read = archive.os.read
        changed = False
        def growing_read(descriptor, length):
            nonlocal changed
            block = original_read(descriptor, length)
            if not changed:
                changed = True
                with p.open("ab") as handle:
                    handle.write(b"extra")
            return block
        with patch.object(archive.os, "read", side_effect=growing_read), self.assertRaises(archive.ArchiveError):
            archive._copy_file(self.source, "data", self.destination, "grew", binding)

    def test_json_duplicate_nonfinite_and_traversal_refused(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'not-json'):
            (self.source / "bad.json").write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(archive.ArchiveError):
                archive._load(self.source, "bad.json")
        with self.assertRaises(archive.ArchiveError):
            archive._binding(self.source, "../source/bad.json")

    def test_atomic_directory_publication_never_replaces_existing_empty_directory(self):
        (self.source / "staged").mkdir()
        (self.source / "staged/data").write_text("complete")
        (self.source / "target").mkdir()
        descriptor = archive._directory(self.source)
        try:
            with self.assertRaises(archive.ArchiveError):
                archive._rename_no_replace("staged", "target", descriptor, descriptor)
            self.assertTrue((self.source / "staged/data").exists())
            self.assertEqual(list((self.source / "target").iterdir()), [])
            (self.source / "target").rmdir()
            archive._rename_no_replace("staged", "target", descriptor, descriptor)
            self.assertEqual((self.source / "target/data").read_text(), "complete")
        finally:
            os.close(descriptor)

    def test_growth_between_safe_open_and_reader_snapshot_refused(self):
        p = self.source / "data.json"
        p.write_bytes(b'{"a":1}')
        original = archive.resident._read_bounded
        def grow_before_snapshot(*args, **kwargs):
            with p.open("ab") as handle:
                handle.write(b" ")
            return original(*args, **kwargs)
        with patch.object(archive.resident, "_read_bounded", side_effect=grow_before_snapshot):
            with self.assertRaises(archive.ArchiveError): archive._binding(self.source, "data.json")
            with self.assertRaises(archive.ArchiveError): archive._load(self.source, "data.json")
            with self.assertRaises(archive.ArchiveError): archive._inventory(self.source)

    def test_destination_preflight_is_read_only_and_refuses_overlap_or_bad_parent(self):
        destination = self.root / "archive"
        result = archive.preflight_archive_destination(self.source, destination, self.destination)
        self.assertEqual(result["new_model_invocations"], 0)
        self.assertFalse(destination.exists())
        for path in (self.source / "archive", self.destination, self.root / "missing/archive"):
            with self.subTest(path=path), self.assertRaises(archive.ArchiveError):
                archive.preflight_archive_destination(self.source, path, self.destination)
        (self.root / "linked-parent").symlink_to(self.destination, target_is_directory=True)
        with self.assertRaises(archive.ArchiveError):
            archive.preflight_archive_destination(self.source, self.root / "linked-parent/archive", self.destination)
        space = os.statvfs(self.root)
        class TooLittleSpace:
            f_bavail = 1
            f_frsize = 4096
        with patch.object(archive.os, "fstatvfs", return_value=TooLittleSpace()), self.assertRaises(archive.ArchiveError):
            archive.preflight_archive_destination(self.source, destination, self.destination)


class SyntheticResultTransactions(unittest.TestCase):
    """Mock model auditing and pinned-asset admission to isolate transactions.

    The immutable native auditor, pinned lock, and Linux executor have separate
    contract tests. These synthetic arrays establish archive mechanics only.
    No test imports prior process receipts or produces physical-run evidence.
    """

    def setUp(self):
        scratch = ROOT / ".local/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / "assets"
        self.capture = self.root / "capture"
        self.archive = self.root / "archive"
        self.assets.mkdir(); self.capture.mkdir()
        campaign = json.loads((ROOT / "examples/watauga/campaign-execution-v2.json").read_text())
        self.lock = _construct(campaign, {"fixture_root": "fixture", "reference_root": "references", "runtime_tar": "runtime.tar"})
        self.lock["native_warning_policy"] = {"once_per_process": {"synthetic admitted diagnostic": 1}, "per_catchment_interval": {}}
        self.cases = self.lock["protocol"]["cases"]
        self.case_leads = {case["case_id"]: [] for case in self.cases}
        for row in iter_expected_rows(self.lock["campaign"]):
            case_id = next(case["case_id"] for case in self.cases if case["issue_time_utc"] == row["issue_time_utc"])
            self.case_leads[case_id].append({"issue_time_utc": row["issue_time_utc"], "lead_hours": row["lead_hour"],
                                            "valid_time_utc": row["valid_time_utc"], "routing_feature_id": "wb-" + row["reach_id"],
                                            "flow_m3_s": float(row["lead_hour"]), "catchment_q_out_m": {"cat-test": 1.0}})
        self.arrays = {case["case_id"]: {"case_id": case["case_id"], "values": [[1.0, 2.0], [3.0, 4.0]], "units": ["m", "m3 s-1"]} for case in self.cases}
        self.make_references()
        self.make_capture()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(archive, "_lock", side_effect=lambda lock: lock))
        stack.enter_context(patch("ngen_reforecast.execution_lock.verify_execution_assets", return_value={"verified": True}))
        self.audit_mock = stack.enter_context(patch.object(archive, "_audit_capture", side_effect=self.fake_audit))

    def write(self, root, path, value):
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, indent=2) + "\n")

    def make_references(self):
        references = self.assets / "references"
        bindings = []
        all_leads = []
        for case in self.cases:
            case_id = case["case_id"]
            self.write(references, f"{case_id}/arrays.json", self.arrays[case_id])
            self.write(references, f"{case_id}/lead_reference.json", self.case_leads[case_id])
            report = archive._seal({"case_id": case_id, "fixture_id": self.lock["fixture_id"],
                "protocol_identity_sha256": self.lock["protocol"]["reference_protocol_identity_sha256"],
                "runtime_identity_sha256": self.lock["runtime_identity_sha256"],
                "assembly_identity_sha256": self.lock["assembly_identity_sha256"]}, "reference_identity_sha256")
            self.write(references, f"{case_id}/REFERENCE.json", report)
            bindings.append({"case_id": case_id, "reference_identity_sha256": report["reference_identity_sha256"],
                             "reference_report": archive._binding(references, f"{case_id}/REFERENCE.json"),
                             "arrays": archive._binding(references, f"{case_id}/arrays.json"),
                             "lead_reference": archive._binding(references, f"{case_id}/lead_reference.json")})
            all_leads.extend(self.case_leads[case_id])
        self.write(references, "set/lead_reference.json", all_leads)
        receipt = archive._seal({"fixture_id": self.lock["fixture_id"],
                 "protocol_identity_sha256": self.lock["protocol"]["reference_protocol_identity_sha256"],
                 "references": bindings}, "reference_set_identity_sha256")
        self.write(references, "set/REFERENCE_SET.json", receipt)
        self.lock["reference_set_identity_sha256"] = receipt["reference_set_identity_sha256"]
        self.lock["reference_files"] = archive._inventory(references)

    def host(self, case_id):
        bounds = self.lock["bounds"]
        image = "sha256:" + self.lock["admission"]["image_manifest_sha256"]
        group = {"cpu.max": "200000 100000", "memory.max": str(bounds["memory_bytes"]), "pids.max": "256",
                 "memory.peak": "1000", "pids.peak": "10", "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n"}
        value = {"case_id": case_id, "run_id": self.lock["run_id"], "execution_lock_sha256": self.lock["execution_lock_sha256"],
            "protocol_identity_sha256": self.lock["protocol_identity_sha256"],
            "admission_identity_sha256": self.lock["admission"]["admission_identity_sha256"],
            "status": "both_stages_zero_exit",
            "stages": [{"stage": name, "docker_exec_exit_code": 0, "stop_reason": None} for name in ("native", "routing")],
            "container_inspection": {"Image": image, "State": {"OOMKilled": False}, "Mounts": [],
                "ImageManifestDescriptor": {"platform": {"architecture": "arm64", "os": "linux"}},
                "Config": {"Image": image, "Labels": {"ngen-reforecast.execution-lock": self.lock["execution_lock_sha256"], "ngen-reforecast.run-id": self.lock["run_id"]},
                           "Env": ["OMP_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1", "MKL_NUM_THREADS=1", "NUMEXPR_NUM_THREADS=1", "TZ=UTC", "PYTHONDONTWRITEBYTECODE=1", "LD_LIBRARY_PATH=" + self.lock["admission"]["native_ld_library_path"]]},
                "HostConfig": {"Memory": bounds["memory_bytes"], "MemorySwap": bounds["memory_bytes"], "NanoCpus": 2_000_000_000, "PidsLimit": 256,
                    "NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False, "Binds": [], "VolumesFrom": [], "CapAdd": [], "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"],
                    "PidMode": "", "IpcMode": "private", "Tmpfs": {"/tmp": "rw,exec,size=64m", "/work": "rw,noexec,size=128m", "/work/job/outputs": "rw,noexec,size=1g"}}},
            "cleanup": [{"action": "stop", "status": "completed"}, {"action": "rm", "status": "completed"}],
            **{name: deepcopy(group) for name in ("cgroup_before", "cgroup_after_native", "cgroup_after_routing")}}
        return archive._seal(value, "host_execution_identity_sha256")

    def make_capture(self):
        self.write(self.capture, "frozen/PROTOCOL.json", self.lock["protocol"])
        self.write(self.capture, "frozen/ADMISSION.json", self.lock["admission"])
        for case in self.cases:
            cid = case["case_id"]
            self.write(self.capture, f"attempts/{cid}/HOST_EXECUTION.json", self.host(cid))
            for name in ("native", "routing"):
                self.write(self.capture, f"attempts/{cid}/{name}/RECEIPT.json", {"synthetic": True})
            p = self.capture / f"attempts/{cid}/native/stderr.log"
            p.write_text("synthetic admitted diagnostic\n")
            p = self.capture / f"attempts/{cid}/outputs/raw.csv"
            p.parent.mkdir(); p.write_text("synthetic data\n")
        self.reseal_capture()

    def reseal_capture(self, status="captured"):
        value = archive._seal({"schema_version": "campaign-execution-capture/0.1",
                    "execution_lock_sha256": self.lock["execution_lock_sha256"], "run_id": self.lock["run_id"],
                    "terminal_status": status, "files": archive._inventory(self.capture, exclude=frozenset({"CAPTURE.json"}))}, "capture_identity_sha256")
        self.write(self.capture, "CAPTURE.json", value)

    def fake_audit(self, lock, staging):
        for case in self.cases:
            cid = case["case_id"]
            self.write(staging, f"verification/{cid}/arrays.json", self.arrays[cid])
            self.write(staging, f"verification/{cid}/lead_reference.json", self.case_leads[cid])
            value = archive._seal({"case_id": cid, "fixture_id": lock["fixture_id"],
                "protocol_identity_sha256": lock["protocol_identity_sha256"], "admission_identity_sha256": lock["admission"]["admission_identity_sha256"],
                "runtime_identity_sha256": lock["runtime_identity_sha256"], "assembly_identity_sha256": lock["assembly_identity_sha256"],
                "raw_outputs": archive._inventory(staging / "capture" / "attempts" / cid / "outputs"),
                "arrays": archive._binding(staging, f"verification/{cid}/arrays.json"),
                "lead_reference": archive._binding(staging, f"verification/{cid}/lead_reference.json")}, "reference_identity_sha256")
            self.write(staging, f"verification/{cid}/REFERENCE.json", value)

    def commit(self):
        return archive.commit_result(self.lock, self.capture, self.archive, self.assets)

    def test_complete_commit_export_round_trip_and_fresh_reuse(self):
        result = self.commit()
        self.assertTrue(result["completed"])
        self.assertEqual((result["generated_rows"], result["retained_rows"]), (36, 12))
        self.assertEqual(archive.archive_status(self.archive, self.lock)["status"], "verified")
        self.assertEqual(self.commit()["result_identity_sha256"], result["result_identity_sha256"])
        self.assertEqual(self.audit_mock.call_count, 1)
        destination = self.root / "export"
        exported = archive.export_result(self.archive, destination, self.lock)
        self.assertEqual(exported["retained_rows"], 12)
        import csv
        with (destination / "forecast.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 12)
        self.assertEqual({int(row["lead_hour"]) for row in rows}, set(range(1, 7)))
        self.assertEqual({row["result_identity_sha256"] for row in rows}, {result["result_identity_sha256"]})
        for row in rows:
            self.assertEqual(row["quality_mask"], "unqualified_diagnostic")
            self.assertEqual(row["scientific_configuration_identity_sha256"], self.lock["scientific_configuration_identity_sha256"])
            self.assertEqual((row["reach_id"], row["routing_feature_id"]), ("1017693", "wb-1017693"))
        self.assertEqual(archive._verify_commit(destination / "result", self.lock)[0]["result_identity_sha256"], result["result_identity_sha256"])
        with self.assertRaises(archive.ArchiveError):
            archive.export_result(self.archive, destination, self.lock)

    def test_incomplete_capture_and_missing_nonretained_lead_never_commit(self):
        self.reseal_capture("failed")
        with self.assertRaises(archive.ArchiveError):
            self.commit()
        self.assertFalse(self.archive.exists())
        self.reseal_capture()
        cid = self.cases[1]["case_id"]
        self.case_leads[cid].pop()  # lead18 lies outside retained1..6
        with self.assertRaises(archive.ArchiveError):
            self.commit()
        self.assertEqual(archive.archive_status(self.archive)["status"], "incomplete")
        self.assertFalse((self.archive / "CURRENT.json").exists())

    def test_changed_full_array_or_corrupt_reference_is_refused(self):
        self.arrays[self.cases[0]["case_id"]]["values"][-1][-1] = 999.0
        with self.assertRaises(archive.ArchiveError):
            self.commit()
        self.assertFalse((self.archive / "CURRENT.json").exists())
        self.arrays[self.cases[0]["case_id"]]["values"][-1][-1] = 4.0
        p = self.assets / "references" / self.cases[1]["case_id"] / "arrays.json"
        p.write_text("{}\n")
        with self.assertRaises(archive.ArchiveError):
            self.commit()

    def test_changed_capture_log_raw_data_host_seal_and_namespace_are_refused(self):
        cid = self.cases[0]["case_id"]
        p = self.capture / f"attempts/{cid}/native/stderr.log"
        good = p.read_bytes()
        p.write_bytes(b"changed\n")
        with self.assertRaises(archive.ArchiveError): self.commit()
        p.write_bytes(good)
        p = self.capture / f"attempts/{cid}/outputs/raw.csv"
        good = p.read_bytes(); p.write_bytes(b"changed\n")
        with self.assertRaises(archive.ArchiveError): self.commit()
        p.write_bytes(good)
        p = self.capture / f"attempts/{cid}/HOST_EXECUTION.json"
        host = json.loads(p.read_text()); host["container_inspection"]["HostConfig"]["PidMode"] = "host"
        self.write(self.capture, p.relative_to(self.capture), host); self.reseal_capture()
        with self.assertRaises(archive.ArchiveError): self.commit()  # invalid hostseal
        host.pop("host_execution_identity_sha256"); host = archive._seal(host, "host_execution_identity_sha256")
        self.write(self.capture, p.relative_to(self.capture), host); self.reseal_capture()
        with self.assertRaises(archive.ArchiveError): self.commit()  # unsafe but resealed host

    def test_stored_payload_corruption_and_foreign_lock_refuse_verification(self):
        result = self.commit()
        with self.assertRaises(archive.ArchiveError):
            archive.verify_result(self.archive, {**self.lock, "run_id": "foreign"})
        data = self.archive / "commits" / result["result_identity_sha256"] / "capture" / "attempts" / self.cases[0]["case_id"] / "outputs/raw.csv"
        data.write_text("corrupted\n")
        with self.assertRaises(archive.ArchiveError): archive.verify_result(self.archive, self.lock)
        with self.assertRaises(archive.ArchiveError): archive.archive_status(self.archive, self.lock)
        with self.assertRaises(archive.ArchiveError): archive.export_result(self.archive, self.root / "bad-export", self.lock)
        self.assertFalse((self.root / "bad-export").exists())

    def test_interruption_before_and_after_commit_directory_publication(self):
        with patch.object(archive, "_audit_capture", side_effect=RuntimeError("interrupted after copy")):
            with self.assertRaises(RuntimeError): self.commit()
        self.assertEqual(archive.archive_status(self.archive)["status"], "incomplete")
        with patch.object(archive, "_pointer", side_effect=RuntimeError("interrupted before pointer")):
            with self.assertRaises(RuntimeError): self.commit()
        self.assertEqual(archive.archive_status(self.archive)["status"], "incomplete")
        self.assertEqual(len(list((self.archive / "commits").iterdir())), 1)
        result = self.commit()
        self.assertTrue(result["completed"])
        self.assertEqual(len(list((self.archive / "commits").iterdir())), 1)

    def test_export_race_does_not_overwrite_concurrently_created_empty_destination(self):
        self.commit()
        destination = self.root / "export-race"
        rename = archive._rename_no_replace
        def race(source, target, source_fd, destination_fd):
            destination.mkdir()
            return rename(source, target, source_fd, destination_fd)
        with patch.object(archive, "_rename_no_replace", side_effect=race), self.assertRaises(archive.ArchiveError):
            archive.export_result(self.archive, destination, self.lock)
        self.assertEqual(list(destination.iterdir()), [])

    def test_nan_wrong_reach_and_duplicate_nonretained_keys_refuse(self):
        leads = [deepcopy(row) for case in self.cases for row in self.case_leads[case["case_id"]]]
        for mutate in (lambda rows: rows[-1].update(flow_m3_s=float("nan")),
                       lambda rows: rows[-1].update(routing_feature_id="1017693"),
                       lambda rows: rows.__setitem__(-1, deepcopy(rows[-2]))):
            candidate = deepcopy(leads)
            mutate(candidate)
            with self.subTest(mutate=mutate), self.assertRaises(archive.ArchiveError):
                archive._products(self.lock, candidate)

    def test_interrupted_pointer_temporary_does_not_block_verified_orphan_retry(self):
        def interrupted(*args, **kwargs):
            raise RuntimeError("interrupted after durable pointer file")
        with patch.object(archive.os, "link", side_effect=interrupted), self.assertRaises(RuntimeError):
            self.commit()
        self.assertFalse((self.archive / "CURRENT.json").exists())
        self.assertTrue(self.commit()["completed"])

    def test_metadata_write_failures_never_publish_partial_commit(self):
        original_write = archive._write
        for filename in ("MANIFEST.json", "COMMITTED.json"):
            def fail(root, relative, value):
                if relative == filename:
                    raise RuntimeError("interrupted metadata write")
                return original_write(root, relative, value)
            with self.subTest(filename=filename), patch.object(archive, "_write", side_effect=fail), self.assertRaises(RuntimeError):
                self.commit()
            self.assertFalse((self.archive / "CURRENT.json").exists())


if __name__ == "__main__":
    unittest.main()
