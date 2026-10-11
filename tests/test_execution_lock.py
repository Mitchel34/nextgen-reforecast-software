"""Identity and unsupported-science failures must precede any worker launch."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ngen_reforecast.execution_lock import (
    ExecutionLockError, _construct, _profile, payload_bytes,
    prepare_execution, validate_execution_lock, verify_execution_assets,
)
from ngen_reforecast._reference.common import seal

ROOT = Path(__file__).resolve().parents[1]
PATHS = {"fixture_root": "fixture", "reference_root": "references", "runtime_tar": "runtime/export-runtime.tar"}


class ExecutionLockTests(unittest.TestCase):
    def setUp(self):
        self.campaign = json.loads((ROOT / "examples/watauga/campaign-execution-v2.json").read_text())

    def test_fresh_identity_preserves_science_and_uses_separate_allowance(self):
        lock = _construct(self.campaign, PATHS)
        baseline = _profile()
        self.assertEqual(validate_execution_lock(lock), lock)
        self.assertNotEqual(lock["protocol_identity_sha256"], baseline["protocol"]["protocol_identity_sha256"])
        self.assertEqual(lock["admission"]["case_inputs"], baseline["admission"]["case_inputs"])
        self.assertEqual(lock["protocol"]["cases"], baseline["protocol"]["cases"])
        self.assertEqual(lock["bounds"]["model_process_allowance"], 9)
        self.assertEqual(lock["bounds"]["planned_model_processes"], 6)
        self.assertFalse(lock["release_qualified"])
        self.assertEqual(len(lock["reference_files"]), 11)

    def test_resealed_scientific_or_runtime_tamper_is_refused(self):
        for field, value in (("native_argv", ["changed"]), ("bounds", {"model_process_allowance": 99})):
            lock = _construct(self.campaign, PATHS)
            lock["protocol"][field] = value
            lock.pop("execution_lock_sha256")
            lock = seal(lock, "execution_lock_sha256")
            with self.assertRaises(ExecutionLockError):
                validate_execution_lock(lock)

    def test_retention_is_projection_only_and_has_distinct_lock(self):
        short = _construct(self.campaign, PATHS)
        full_spec = deepcopy(self.campaign)
        full_spec["retained_leads"]["max_lead_hours"] = 18
        full = _construct(full_spec, PATHS)
        self.assertNotEqual(short["execution_lock_sha256"], full["execution_lock_sha256"])
        self.assertEqual(short["admission"]["case_inputs"], full["admission"]["case_inputs"])
        self.assertEqual(short["protocol"]["cases"], full["protocol"]["cases"])

    def test_unsupported_dates_domain_or_resources_refuse(self):
        changes = [lambda c: c.update(origin_time_utc="2021-11-01T00:00:00Z"),
                   lambda c: c["domains"][0]["locations"][0].update(reach_id="1"),
                   lambda c: c["resources"].update(wall_time_seconds=2000),
                   lambda c: c["issue_schedule"].update(cadence_hours=2)]
        for change in changes:
            c = deepcopy(self.campaign); change(c)
            with self.assertRaises(ValueError):
                _construct(c, PATHS)

    def test_bundle_path_escape_and_overlap_refuse(self):
        for path in ("../original", "/original", "fixture/../original", "fixture", "fixture/subdir"):
            paths = dict(PATHS, reference_root=path)
            with self.assertRaises(ValueError):
                _construct(self.campaign, paths)

    def test_prepare_cannot_skip_asset_validation(self):
        from ngen_reforecast.execution_lock import load
        def load_bundle(path, maximum):
            if Path(path).name == "BUNDLE.json":
                return {"schema_version": "watauga-v2-execution-bundle/0.1", "bundle_paths": PATHS}
            return load(path, maximum)
        with patch("ngen_reforecast.execution_lock.load", side_effect=load_bundle), \
             patch("ngen_reforecast.execution_lock.verify_execution_assets", side_effect=ExecutionLockError("corrupt reference")) as check:
            with self.assertRaisesRegex(ExecutionLockError, "corrupt reference"):
                prepare_execution(self.campaign, ROOT / "BUNDLE.json")
            check.assert_called_once()

    def test_missing_source_refuses_without_worker(self):
        with self.assertRaises((ValueError, OSError)):
            verify_execution_assets(_construct(self.campaign, PATHS), ROOT / "nonexistent-bundle")

    def test_frozen_payload_is_deterministic_and_identity_bound(self):
        lock = _construct(self.campaign, PATHS)
        self.assertEqual(payload_bytes(lock), payload_bytes(json.loads(payload_bytes(lock))))


if __name__ == "__main__":
    unittest.main()
