"""Failure-boundary tests; synthetic files are never hydrologic evidence."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from ngen_reforecast import runtime


REPO = Path(__file__).absolute().parents[1]
PROFILE = REPO / "profiles" / "nextgen-arm64-v3.json"


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary_root = REPO / ".local" / "tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_root)
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def codes(self, report):
        return {item["code"] for item in report["blockers"]}

    def asset(self, path="resident.bin", content=b"resident", expected=None):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return {"path": path, "role": "test_fixture", "bytes": len(content), "sha256": expected if expected is not None else hashlib.sha256(content).hexdigest()}

    def inspect_asset(self, asset, remaining=1000, per_file=1000):
        root_fd = runtime._open_directory(self.root)
        try:
            return runtime._inspect_asset(root_fd, asset, remaining, per_file)
        finally:
            os.close(root_fd)

    def test_default_never_activates_and_requests_explicit_root(self):
        report = runtime.inspect_runtime(PROFILE)
        self.assertFalse(report["execution_ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertIn("ASSET_ROOT_REQUIRED", self.codes(report))
        self.assertIn("NATIVE_BUILD_UNQUALIFIED", self.codes(report))
        self.assertEqual(report["summary"]["assets_checked"], 0)
        self.assertNotIn(str(REPO), json.dumps(report))

    def test_exact_profile_mismatch_is_rejected(self):
        profile = json.loads(PROFILE.read_text())
        for mutate in (
            lambda p: p["runtime"].update(native_sha256="0" * 64),
            lambda p: p["sources"].update(ngen_commit="0" * 40),
            lambda p: p.update(qualification_status="qualified"),
            lambda p: p["assets"][0].update(path="../outside"),
        ):
            altered = json.loads(json.dumps(profile))
            mutate(altered)
            local_profile = self.root / "profile.json"
            local_profile.write_text(json.dumps(altered))
            with self.assertRaises(runtime.RuntimeProfileError):
                runtime.inspect_runtime(local_profile)

    def test_whitespace_and_key_order_do_not_change_profile_identity(self):
        local_profile = self.root / "profile.json"
        local_profile.write_text(json.dumps(json.loads(PROFILE.read_text()), sort_keys=True))
        self.assertEqual(runtime.inspect_runtime(local_profile)["profile_sha256"], runtime.inspect_runtime(PROFILE)["profile_sha256"])

    def test_duplicate_profile_keys_rejected(self):
        path = self.root / "duplicate.json"
        path.write_text('{"a": 1, "a": 2}')
        with self.assertRaisesRegex(runtime.RuntimeProfileError, "Duplicate"):
            runtime.inspect_runtime(path)

    def test_profile_size_bound(self):
        path = self.root / "oversized.json"
        with path.open("wb") as stream:
            stream.truncate(runtime._MAX_PROFILE_BYTES + 1)
        with self.assertRaisesRegex(runtime.RuntimeProfileError, "1 MiB"):
            runtime.inspect_runtime(path)

    def test_empty_root_exposes_missing_native_and_fixture(self):
        report = runtime.inspect_runtime(PROFILE, self.root)
        missing = [c["path"] for c in report["checks"] if c["code"] == "ASSET_MISSING"]
        self.assertIn("runtime/bin/ngen-shared", missing)
        self.assertIn("fixture/CONTRACT.json", missing)
        self.assertEqual(len(missing), report["summary"]["assets_expected"])
        self.assertEqual(report["summary"]["hashed_bytes_or_reserved_after_read_failure"], 0)
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_supplied_native_with_wrong_bytes_is_not_qualified(self):
        binary = self.root / "runtime" / "bin" / "ngen-shared"
        binary.parent.mkdir(parents=True)
        with binary.open("wb") as stream:
            stream.truncate(3_813_528)
        report = runtime.inspect_runtime(PROFILE, self.root)
        native = next(c for c in report["checks"] if c.get("path") == "runtime/bin/ngen-shared")
        self.assertEqual(native["code"], "ASSET_HASH_MISMATCH")
        self.assertEqual(native["hashed_bytes"], 3_813_528)
        self.assertFalse(report["execution_ready"])

    def test_platform_match_is_not_qualification(self):
        with mock.patch.object(runtime.platform, "system", return_value="Linux"), mock.patch.object(runtime.platform, "machine", return_value="aarch64"):
            report = runtime.inspect_runtime(PROFILE)
        self.assertNotIn("UNSUPPORTED_NATIVE_PLATFORM", self.codes(report))
        self.assertFalse(report["execution_ready"])

    def test_unsupported_native_platform_is_explicit(self):
        with mock.patch.object(runtime.platform, "system", return_value="Darwin"), mock.patch.object(runtime.platform, "machine", return_value="arm64"):
            report = runtime.inspect_runtime(PROFILE)
        self.assertIn("UNSUPPORTED_NATIVE_PLATFORM", self.codes(report))

    def test_symlink_root_is_rejected(self):
        link = self.root / "alias"
        link.symlink_to(self.root, target_is_directory=True)
        report = runtime.inspect_runtime(PROFILE, link)
        self.assertIn("SYMLINK_REJECTED", self.codes(report))

    def test_symlink_directory_and_leaf_are_never_read(self):
        real = self.root / "real"
        real.mkdir()
        (real / "secret").write_bytes(b"private")
        (self.root / "escape").symlink_to(real, target_is_directory=True)
        (self.root / "leaf").symlink_to(real / "secret")
        with mock.patch.object(runtime.os, "read", side_effect=AssertionError("A symlink must never be read")):
            for path in ("escape/secret", "leaf"):
                check = self.inspect_asset({"path": path, "role": "test", "bytes": None, "sha256": None})
                self.assertEqual(check["code"], "SYMLINK_REJECTED")

    def test_parent_traversal_and_absolute_asset_paths_rejected(self):
        for path in ("../outside", "/outside", "nested/../../outside", "nested\\outside", "nested//outside"):
            check = self.inspect_asset({"path": path, "role": "test", "bytes": None, "sha256": None})
            self.assertEqual(check["code"], "PATH_ESCAPE_REJECTED")

    def test_dataless_leaf_is_rejected_before_open(self):
        asset = self.asset()
        root_fd = runtime._open_directory(self.root)
        try:
            with mock.patch.object(runtime, "_is_dataless", return_value=True), mock.patch.object(runtime.os, "open", side_effect=AssertionError("Dataless input must not be opened")):
                check = runtime._inspect_asset(root_fd, asset, 1000, 1000)
            self.assertEqual(check["code"], "DATALESS_REJECTED")
        finally:
            os.close(root_fd)

    def test_dataless_stat_flag_is_recognized(self):
        info = mock.Mock(st_flags=runtime._DATALESS_FLAG, st_file_attributes=0)
        self.assertTrue(runtime._is_dataless(info))

    def test_hash_limits_prevent_content_reads(self):
        asset = self.asset(content=b"12345")
        with mock.patch.object(runtime.os, "read", side_effect=AssertionError("No bounded-out file read")):
            self.assertEqual(self.inspect_asset(asset, per_file=4)["code"], "FILE_HASH_BOUND_EXCEEDED")
            self.assertEqual(self.inspect_asset(asset, remaining=4)["code"], "TOTAL_HASH_BOUND_EXCEEDED")
        self.assertEqual(self.inspect_asset(asset, per_file=5, remaining=5)["code"], "ASSET_HASH_VERIFIED")

    def test_unknown_identity_reports_observed_hash_without_verification(self):
        asset = self.asset()
        asset["sha256"] = None
        check = self.inspect_asset(asset)
        self.assertEqual(check["code"], "ASSET_IDENTITY_UNRESOLVED")
        self.assertEqual(check["observed_sha256"], hashlib.sha256(b"resident").hexdigest())
        self.assertEqual(check["status"], "blocked")

    def test_size_mismatch_is_rejected_before_read(self):
        asset = self.asset()
        asset["bytes"] += 1
        with mock.patch.object(runtime.os, "read", side_effect=AssertionError("Size mismatch must not be read")):
            self.assertEqual(self.inspect_asset(asset)["code"], "ASSET_SIZE_MISMATCH")

    def test_fifo_is_rejected_without_blocking(self):
        os.mkfifo(self.root / "pipe")
        check = self.inspect_asset({"path": "pipe", "role": "test", "bytes": None, "sha256": None})
        self.assertEqual(check["code"], "REGULAR_FILE_REQUIRED")


if __name__ == "__main__":
    unittest.main()
