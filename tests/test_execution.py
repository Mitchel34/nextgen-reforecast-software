"""Executor failure boundaries use synthetic bytes and mocked Docker only."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from ngen_reforecast import execution as e
from ngen_reforecast import execution_lock as el
from ngen_reforecast.campaign import load_campaign

REPO = Path(__file__).absolute().parents[1]


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = REPO / ".local/tmp"
        temporary.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.assets = self.base / "assets"
        self.assets.mkdir()
        spec = load_campaign(REPO / "examples/watauga/campaign.json")
        spec["domains"][0]["assets"] = []
        spec["resources"].update(host_cpus=2, parent_cpus=1, cpus_per_branch=1,
                                 max_concurrent_branches=1, wall_time_seconds=1800)
        self.lock = el._construct(spec, {"fixture_root": "fixture", "reference_root": "references", "runtime_tar": "runtime.tar"})
        self.output = self.base / "run"
        self.endpoint = "unix:///synthetic-dedicated/docker.sock"

    def verification(self):
        return mock.patch.object(el, "verify_execution_assets", return_value={"verified": True, "source_assets": 0, "source_bytes": 0})

    def invoke(self, lock=None, output=None):
        return e.execute_campaign(lock or self.lock, asset_root=self.assets,
                                  output_root=output or self.output, docker_host=self.endpoint)

    def test_planning_lock_and_resealed_changed_runtime_refused_before_any_docker(self):
        values = [{"schema_version": "planning-lock/0.1", "execution_ready": False}]
        changed = deepcopy(self.lock)
        changed["runtime_identity_sha256"] = "0" * 64
        changed.pop("execution_lock_sha256")
        values.append(e._seal(changed, "execution_lock_sha256"))
        with mock.patch.object(e, "_Docker") as docker:
            for lock in values:
                with self.subTest(lock=lock.get("schema_version")), self.assertRaises(ValueError):
                    self.invoke(lock)
            docker.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.assets / ".execution-claims").exists())

    def test_missing_inputs_refused_before_any_subprocess_or_claim(self):
        with mock.patch.object(e.subprocess, "Popen") as launch, self.assertRaises(e.ExecutionError):
            self.invoke()
        launch.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.assets / ".execution-claims").exists())

    def test_resident_asset_refusal_has_public_error_type(self):
        with mock.patch.object(el, "verify_execution_assets", side_effect=e._AssetRefusal("REJECTED", "resident asset rejected")), mock.patch.object(e.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(e.ExecutionError, "resident asset rejected"):
                self.invoke()
        launch.assert_not_called()

    def test_unsafe_endpoints_refused_before_input_reads(self):
        for endpoint in ["tcp://127.0.0.1:2375", "ssh://host", "", "unix://relative", "unix:///a/../docker.sock", "unix:///a//docker.sock", "unix:///a?context=x"]:
            with self.subTest(endpoint=endpoint), mock.patch.object(el, "verify_execution_assets") as reads, self.assertRaises(e.ExecutionError):
                e.execute_campaign(self.lock, asset_root=self.assets, output_root=self.output, docker_host=endpoint)
            reads.assert_not_called()

    def test_changed_packaged_tool_refused_before_claim(self):
        real = e._binding
        def binding(path, *args):
            result = real(path, *args)
            if Path(path).name == "execute_stage.py":
                result["sha256"] = "0" * 64
            return result
        with self.verification(), mock.patch.object(e, "_binding", side_effect=binding), mock.patch.object(e, "_Docker") as docker, self.assertRaises(e.ExecutionError):
            self.invoke()
        docker.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_persistent_claim_prevents_reset_through_a_second_output_root(self):
        class WrongImage:
            def __init__(self, *args): pass
            def command(self, *args, **kwargs):
                return json.dumps([{"Architecture": "amd64", "Os": "linux"}]).encode()
        with self.verification(), mock.patch.object(e, "_Docker", WrongImage):
            first = self.invoke()
            self.assertEqual(first["terminal_status"], "failed")
            claim = self.assets / ".execution-claims" / (self.lock["execution_lock_sha256"] + ".json")
            self.assertTrue(claim.exists())
            original = claim.read_bytes()
            with self.assertRaisesRegex(e.ExecutionError, "already claimed"):
                self.invoke(output=self.base / "different-run")
            self.assertEqual(claim.read_bytes(), original)
        self.assertFalse((self.base / "different-run").exists())
        self.assertEqual(first["model_processes_reserved"], 0)

    def test_source_overlap_and_symlink_output_parent_refused(self):
        fixture = self.assets / "fixture"
        fixture.mkdir()
        alias = self.base / "alias"
        alias.symlink_to(self.base, target_is_directory=True)
        with self.verification(), mock.patch.object(e, "_Docker") as docker:
            for path in [fixture / "run", alias / "run"]:
                with self.subTest(path=path), self.assertRaises(e.ExecutionError):
                    self.invoke(output=path)
        docker.assert_not_called()
        self.assertFalse((self.assets / ".execution-claims").exists())

    def test_claim_directory_symlink_is_not_followed(self):
        (self.assets / ".execution-claims").symlink_to(self.base, target_is_directory=True)
        with self.verification(), mock.patch.object(e, "_Docker") as docker, self.assertRaises(e.ExecutionError):
            self.invoke()
        docker.assert_not_called()
        self.assertFalse((self.base / (self.lock["execution_lock_sha256"] + ".json")).exists())

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep"
        marker.write_bytes(b"preserved")
        with self.verification(), mock.patch.object(e, "_Docker") as docker, self.assertRaises(e.ExecutionError):
            self.invoke()
        docker.assert_not_called()
        self.assertEqual(marker.read_bytes(), b"preserved")
        self.assertFalse((self.assets / ".execution-claims").exists())

    def image(self):
        return {"Image": "sha256:" + self.lock["admission"]["image_manifest_sha256"], "Mounts": [],
                "ImageManifestDescriptor": {"platform": {"architecture": "arm64", "os": "linux"}},
                "Config": {"Image": "sha256:" + self.lock["admission"]["image_manifest_sha256"],
                           "Env": [k + "=" + v for k, v in {**e.THREAD_ENV, "LD_LIBRARY_PATH": self.lock["admission"]["native_ld_library_path"]}.items()]},
                "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                               "Memory": 8 * 1024**3, "MemorySwap": 8 * 1024**3, "NanoCpus": 2 * 10**9,
                               "PidsLimit": 256, "Binds": [], "VolumesFrom": [], "CapAdd": [], "CapDrop": ["ALL"],
                               "SecurityOpt": ["no-new-privileges"], "PidMode": "", "IpcMode": "private",
                               "Tmpfs": {"/tmp": "rw,exec,size=64m", "/work": "rw,noexec,size=128m", "/work/job/outputs": "rw,noexec,size=1g"}}}

    def cgroup(self):
        return {"cpu.max": "200000 100000\n", "memory.max": "8589934592\n", "pids.max": "256\n",
                "memory.peak": "1024\n", "pids.peak": "8\n", "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n"}

    def test_actual_isolation_mismatches_rejected(self):
        e._check_container(self.lock, self.image())
        for key, value in [("NetworkMode", "bridge"), ("ReadonlyRootfs", False), ("MemorySwap", 16 * 1024**3),
                           ("PidsLimit", 512), ("NanoCpus", 3 * 10**9), ("Binds", ["/host:/work"]),
                           ("CapDrop", []), ("PidMode", "host")]:
            changed = self.image()
            changed["HostConfig"][key] = value
            with self.subTest(key=key), self.assertRaises(e.ExecutionError):
                e._check_container(self.lock, changed)
        for key, value in [("cpu.max", "max 100000"), ("memory.events", "oom 1\n"), ("pids.peak", "257")]:
            changed = self.cgroup(); changed[key] = value
            with self.subTest(key=key), self.assertRaises(e.ExecutionError):
                e._check_cgroup(changed)

    def prepare_internal_namespace(self):
        self.output.mkdir()
        for d in ["frozen", "attempts", "ledger"]:
            (self.output / d).mkdir()
        e._json_new(self.output / "frozen/PROTOCOL.json", self.lock["protocol"])
        e._json_new(self.output / "frozen/ADMISSION.json", self.lock["admission"])
        (self.assets / "runtime.tar").write_bytes(b"synthetic-runtime-transfer")

    def test_zero_exit_incomplete_native_blocks_router_and_preserves_failed_capture(self):
        self.prepare_internal_namespace()
        outer = self
        calls = []
        durable_order = []
        class FakeDocker:
            def command(self, args, **kwargs):
                calls.append(args)
                if b"PROCESS-01.json" in kwargs.get("data", b""):
                    durable_order.append("reservation_transfer")
                if args[0] == "inspect": return json.dumps([outer.image()]).encode()
                return b""
            def accounting(self, name): return outer.cgroup()
            def quiesce(self, name): return {"pid1_kept_alive": True, "errors": []}
            def model(self, args, log, seconds, name):
                # This assertion checks reservation persistence before launch.
                outer.assertTrue((outer.output / "ledger/PROCESS-01.json").is_file())
                durable_order.append("model_launch")
                outer.assertEqual(durable_order, ["ledger_directory_fsync", "reservation_transfer", "model_launch"])
                calls.append(["synthetic-model", "native"])
                log.write_bytes(b"synthetic wrapper\n")
                return {"docker_exec_exit_code": 0, "host_elapsed_seconds": .01, "stop_reason": None, "wrapper_log": e._binding(log)}
        def export(docker, name, remote, target, maximum):
            target.mkdir()
            if remote.endswith("/native"):
                for log, data in [("stdout", b"FATAL ERROR\nSTOP\n"), ("stderr", b"")]:
                    (target / (log + ".log")).write_bytes(data)
                reservation = e._load(outer.output / "ledger/PROCESS-01.json", "reservation_identity_sha256")
                source = next(x for x in outer.lock["source_tools"] if Path(x["path"]).name == "execute_stage.py")
                receipt = e._seal({"reservation": reservation, "returncode": 0, "termination_reason": None,
                                  "post_launch_verification_error": "incomplete output", "case_input_identity_sha256_after": reservation["case_input_identity_sha256"],
                                  "executor": {k: source[k] for k in ["bytes", "sha256"]},
                                  "stdout": e._binding(target / "stdout.log"), "stderr": e._binding(target / "stderr.log"),
                                  "native_output_contract": {"native_output_contract_complete": False}}, "process_receipt_identity_sha256")
                e._json_new(target / "RECEIPT.json", receipt)
            else:
                (target / "partial").write_bytes(b"unverified synthetic diagnostic")
            return {"bytes": 1, "sha256": "0" * 64}
        original = e._binding
        def binding(path, *args):
            if Path(path) == self.assets / "runtime.tar": return self.lock["admission"]["runtime_transfer_payload"]
            return original(path, *args)
        flush = e._fsync_directory
        def flushing(path):
            flush(path)
            if Path(path) == self.output / "ledger":
                durable_order.append("ledger_directory_fsync")
        with mock.patch.object(e, "_payload", return_value=b"synthetic-input-transfer"), mock.patch.object(e, "_capture_tree", side_effect=export), mock.patch.object(e, "_binding", side_effect=binding), mock.patch.object(e, "_fsync_directory", side_effect=flushing):
            report = e._run_case(self.lock, self.assets, self.output, FakeDocker(), "history")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(len(list((self.output / "ledger").glob("PROCESS-*.json"))), 1)
        self.assertEqual([a for a in calls if a[0] == "synthetic-model"], [["synthetic-model", "native"]])
        self.assertTrue((self.output / "attempts/history/native/RECEIPT.json").is_file())
        self.assertTrue((self.output / "attempts/history/failed-outputs/partial").is_file())
        self.assertEqual([a[0] for a in calls if a[0] in ["stop", "rm"]], ["stop", "rm"])

    def test_changed_warning_policy_receipt_blocks_routing(self):
        folder = self.base / "native"; folder.mkdir()
        for name, data in [("stdout", b"synthetic clean output\n"), ("stderr", b"unexpected physical unit warning\n")]:
            (folder / (name + ".log")).write_bytes(data)
        source = next(x for x in self.lock["source_tools"] if Path(x["path"]).name == "execute_stage.py")
        reservation = {"case_input_identity_sha256": "a" * 64, "case_id": "history", "stage": "native",
                       "protocol_identity_sha256": self.lock["protocol_identity_sha256"],
                       "admission_identity_sha256": self.lock["admission"]["admission_identity_sha256"]}
        receipt = e._seal({"reservation": reservation, "returncode": 0, "termination_reason": None,
                          "post_launch_verification_error": None, "case_input_identity_sha256_after": "a" * 64,
                          "executor": {k: source[k] for k in ["bytes", "sha256"]},
                          "stdout": e._binding(folder / "stdout.log"), "stderr": e._binding(folder / "stderr.log"),
                          "native_output_contract": {"native_output_contract_complete": True}}, "process_receipt_identity_sha256")
        e._json_new(folder / "RECEIPT.json", receipt)
        with self.assertRaises(e.ExecutionError):
            e._verify_stage(self.lock, "history", "native", folder, reservation)

        with mock.patch.object(el, "verify_native_warnings", side_effect=el.ExecutionLockError("unexpected native warning inventory")):
            with self.assertRaisesRegex(e.ExecutionError, "unexpected native warning inventory"):
                e._verify_stage(self.lock, "history", "native", folder, reservation)

    def tar(self, members):
        path = self.base / "export.tar"
        with tarfile.open(path, "w") as archive:
            for name, data, kind in members:
                item = tarfile.TarInfo(name)
                item.type = kind; item.size = len(data) if kind == tarfile.REGTYPE else 0
                if kind == tarfile.SYMTYPE: item.linkname = "../../outside"
                archive.addfile(item, io.BytesIO(data) if kind == tarfile.REGTYPE else None)
        return path

    def test_tar_escape_links_duplicate_and_oversize_refused(self):
        for i, rows in enumerate([
            [("outputs/../../outside", b"x", tarfile.REGTYPE)],
            [("outputs/link", b"", tarfile.SYMTYPE)],
            [("outputs/a", b"x", tarfile.REGTYPE), ("outputs/a", b"y", tarfile.REGTYPE)],
            [("outputs/a", b"12345", tarfile.REGTYPE)],
        ]):
            with self.subTest(rows=rows), self.assertRaises((ValueError, OSError)):
                e._extract_tar(self.tar(rows), self.base / ("target%d" % i), "outputs", 4)
        self.assertFalse((self.base / "outside").exists())

    def test_valid_tar_roundtrip_and_existing_file_refusal(self):
        path = self.tar([("outputs/a", b"1234", tarfile.REGTYPE)])
        target = self.base / "target"
        e._extract_tar(path, target, "outputs", 4)
        self.assertEqual((target / "a").read_bytes(), b"1234")
        with self.assertRaises(FileExistsError):
            e._extract_tar(path, target, "outputs", 4)
        self.assertEqual((target / "a").read_bytes(), b"1234")

    def test_export_refuses_existing_symlink_parent(self):
        target = self.base / "target"; target.mkdir()
        outside = self.base / "outside"; outside.mkdir()
        (target / "nested").symlink_to(outside, target_is_directory=True)
        path = self.tar([("outputs/nested/a", b"1234", tarfile.REGTYPE)])
        with self.assertRaises(e.ExecutionError):
            e._extract_tar(path, target, "outputs", 4)
        self.assertFalse((outside / "a").exists())

    def test_quiescence_bypasses_storage_guard_without_bypassing_byte_bounds(self):
        docker = e._Docker(self.endpoint, self.base, self.lock["bounds"], None)
        with mock.patch.object(docker, "command", return_value=b'{"pid1_kept_alive":true,"errors":[]}') as command:
            docker.quiesce("synthetic")
        self.assertIs(command.call_args.kwargs["guard_storage"], False)

    def test_utility_bytes_bounded_and_critical_cleanup_works_when_storage_guard_fails(self):
        docker = e._Docker(self.endpoint, self.base, self.lock["bounds"], None)
        class Process:
            def poll(self): return 0
            def wait(self, timeout=None): return 0
        def launch(*args, **kwargs):
            if kwargs["stdout"] != e.subprocess.DEVNULL:
                kwargs["stdout"].write(b"x" * 128)
                kwargs["stdout"].flush()
            return Process()
        with mock.patch.object(e.subprocess, "Popen", side_effect=launch):
            with self.assertRaisesRegex(e.ExecutionError, "output byte"):
                docker.command(["synthetic"], maximum=4)
            with mock.patch.object(e, "_storage", side_effect=AssertionError("cleanup must not use storage guard")), mock.patch.object(e.tempfile, "TemporaryFile", side_effect=AssertionError("cleanup must not allocate spool files")):
                self.assertEqual(docker.command(["stop", "synthetic"], critical=True), b"")


if __name__ == "__main__":
    unittest.main()
