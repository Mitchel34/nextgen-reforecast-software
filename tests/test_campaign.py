"""Adversarial specification/asset tests; temporary writes stay in the repository."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from ngen_reforecast import campaign
from ngen_reforecast.campaign import CampaignError, iter_ledger, load_campaign, plan_campaign


ROOT = Path(__file__).absolute().parents[1]
EXAMPLE = ROOT / "examples/watauga/campaign.json"


class CampaignTests(unittest.TestCase):
    def setUp(self):
        local_tmp = ROOT / ".local/tmp"
        local_tmp.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=local_tmp)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.spec = load_campaign(EXAMPLE)

    def write(self, name, content):
        target = self.base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def asset(self, path="inputs/test.dat", role="hydrofabric", content=b"original input\n"):
        self.write(path, content)
        asset = {"role": role, "path": path, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}
        self.spec["domains"][0]["assets"].append(asset)
        return asset

    def codes(self, plan):
        return {problem["code"] for problem in plan["blockers"]}

    def assert_invalid(self, spec):
        with self.assertRaises(CampaignError):
            plan_campaign(spec, self.base)

    def test_example_is_explicitly_blocked_and_counts_expected_rows(self):
        plan = plan_campaign(self.spec, EXAMPLE.parent)
        self.assertFalse(plan["execution_ready"])
        self.assertEqual(plan["totals"]["issue_count"], 2)
        self.assertEqual(plan["totals"]["domain_count"], 1)
        self.assertEqual(plan["totals"]["location_count"], 1)
        self.assertEqual(plan["totals"]["expected_forecast_rows"], 36)
        self.assertEqual(plan["totals"]["history_hours_per_domain"], 786)
        self.assertEqual(sum(b["code"] == "asset_role_missing" for b in plan["blockers"]), 6)

    def test_exact_hourly_ledger_and_cross_year_target_clock(self):
        rows = list(iter_ledger(self.spec))
        self.assertEqual(len(rows), 36)
        self.assertEqual(rows[0], {"domain_id": "watauga", "location_id": "03479000", "reach_id": "1017693",
                                   "issue_time_utc": "2022-01-01T23:00:00Z", "lead_hour": 1,
                                   "valid_time_utc": "2022-01-02T00:00:00Z"})
        self.assertEqual(rows[17]["valid_time_utc"], "2022-01-02T17:00:00Z")
        self.assertEqual(rows[-1]["valid_time_utc"], "2022-01-02T18:00:00Z")
        self.assertEqual({r["lead_hour"] for r in rows}, set(range(1, 19)))

    def test_nested_locations_increase_outputs_without_duplicate_history(self):
        self.spec["domains"][0]["locations"].append({"location_id": "nested_test", "reach_id": "999"})
        plan = plan_campaign(self.spec, self.base)
        self.assertEqual(plan["totals"]["domain_count"], 1)
        self.assertEqual(plan["totals"]["location_count"], 2)
        self.assertEqual(plan["totals"]["branch_count"], 2)
        self.assertEqual(plan["totals"]["total_parent_history_hours"], 786)
        self.assertEqual(len(list(iter_ledger(self.spec))), 72)

    def test_invalid_canonical_times_and_calendar_hours(self):
        bad = ["2022-01-01T23:30:00Z", "2022-01-01T23:00:01Z", "2022-01-01T23:00:00+00:00",
               "2022-01-01T23:00:00.000Z", "2022-01-01T23:00:00", "2022-02-29T00:00:00Z",
               "2022-01-01T24:00:00Z", "2022-01-01 23:00:00Z", True, 1, None]
        for value in bad:
            with self.subTest(value=value):
                spec = deepcopy(self.spec)
                spec["issue_times_utc"][0] = value
                self.assert_invalid(spec)

    def test_history_origin_and_end_coverage_are_not_silently_repaired(self):
        for mutation in ("origin", "stop", "before", "cold", "reverse", "duplicate"):
            with self.subTest(mutation=mutation):
                spec = deepcopy(self.spec)
                if mutation == "origin":
                    spec["history"]["start_time_utc"] = "2021-12-02T00:00:00Z"
                elif mutation == "stop":
                    spec["history"]["stop_time_utc"] = "2022-01-02T17:00:00Z"
                elif mutation == "before":
                    spec["issue_times_utc"][0] = "2021-11-30T23:00:00Z"
                elif mutation == "cold":
                    spec["issue_times_utc"][0] = spec["origin_time_utc"]
                elif mutation == "reverse":
                    spec["issue_times_utc"].reverse()
                else:
                    spec["issue_times_utc"][1] = spec["issue_times_utc"][0]
                self.assert_invalid(spec)

    def test_unsupported_profile_horizon_and_unknown_fields(self):
        for key, value in (("profile", "generic"), ("horizon_hours", 24), ("horizon_hours", True),
                           ("schema_version", "2.0"), ("extra", "ignored?")):
            with self.subTest(key=key, value=value):
                spec = deepcopy(self.spec)
                spec[key] = value
                self.assert_invalid(spec)
        self.spec["domains"][0]["extra"] = 1
        self.assert_invalid(self.spec)

    def test_resources_refuse_boolean_zero_fraction_nonfinite_and_oversubscription(self):
        for value in (True, False, 0, -1, 1.5, float("inf"), float("nan"), "4", 1025):
            with self.subTest(value=value):
                spec = deepcopy(self.spec)
                spec["resources"]["host_cpus"] = value
                self.assert_invalid(spec)
        self.spec["resources"]["host_cpus"] = 3
        self.assert_invalid(self.spec)

    def test_duplicate_json_keys_and_nonfinite_literals(self):
        for source in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', '{"a":1e999}'):
            with self.subTest(source=source):
                path = self.write("invalid.json", source.encode())
                with self.assertRaises(CampaignError):
                    load_campaign(path)

    def test_duplicate_nested_key_rejected_before_schema_validation(self):
        text = json.dumps(self.spec).replace('"host_cpus": 4', '"host_cpus": 4, "host_cpus": 8')
        with self.assertRaisesRegex(CampaignError, "Duplicate JSON"):
            load_campaign(self.write("nested-duplicate.json", text.encode()))

    def test_campaign_file_is_bounded_and_cannot_be_symlink(self):
        path = self.write("oversize.json", b" " * (campaign.MAX_SPEC_BYTES + 1))
        with patch.object(campaign.os, "read", side_effect=AssertionError("unsafe read")):
            with self.assertRaises(CampaignError):
                load_campaign(path)
        link = self.base / "campaign-link.json"
        link.symlink_to(EXAMPLE)
        with self.assertRaises(CampaignError):
            load_campaign(link)

    def test_missing_corrupt_and_size_mismatched_assets_are_blockers(self):
        asset = self.asset()
        self.assertEqual(plan_campaign(self.spec, self.base)["assets"][0]["status"], "verified")
        target = self.base / asset["path"]
        target.write_bytes(b"corrupted data\n")
        self.assertIn("asset_hash_mismatch", self.codes(plan_campaign(self.spec, self.base)))
        target.write_bytes(b"short")
        self.assertIn("asset_size_mismatch", self.codes(plan_campaign(self.spec, self.base)))
        target.unlink()
        self.assertIn("asset_missing", self.codes(plan_campaign(self.spec, self.base)))

    def test_unknown_identity_is_explicit_and_does_not_read_file(self):
        asset = self.asset()
        asset["sha256"] = None
        asset["size_bytes"] = None
        with patch.object(campaign.os, "read", side_effect=AssertionError("unknown-identity file was read")):
            plan = plan_campaign(self.spec, self.base)
        self.assertTrue({"asset_sha256_unknown", "asset_size_bytes_unknown"} <= self.codes(plan))
        self.assertEqual(plan["assets"][0]["status"], "unverified")

    def test_verified_asset_hashes_never_authorize_execution(self):
        for role in sorted(campaign.ASSET_ROLES):
            self.asset(path=f"inputs/{role}.dat", role=role)
        plan = plan_campaign(self.spec, self.base)
        self.assertTrue(all(asset["status"] == "verified" for asset in plan["assets"]))
        self.assertEqual(self.codes(plan), {"runtime_not_qualified"})
        self.assertFalse(plan["execution_ready"])
        self.assertFalse(plan["domain_states"][0]["physical_state_verified"])

    def test_unsafe_paths_and_bad_role_hash_size_are_invalid(self):
        for path in ("../elsewhere", "/etc/passwd", "a/../b", "./a", "a//b", "a/", "a\\b", "bad\x00name", "a\nb"):
            with self.subTest(path=path):
                spec = deepcopy(self.spec)
                spec["domains"][0]["assets"] = [{"role": "hydrofabric", "path": path, "sha256": None, "size_bytes": None}]
                self.assert_invalid(spec)
        asset = self.asset()
        for key, value in (("role", "weather-ish"), ("sha256", "A" * 64), ("sha256", "0" * 63),
                           ("size_bytes", True), ("size_bytes", 0)):
            with self.subTest(key=key, value=value):
                spec = deepcopy(self.spec)
                spec["domains"][0]["assets"][0][key] = value
                self.assert_invalid(spec)

    def test_symlink_leaf_and_parent_refused_without_reading(self):
        asset = self.asset()
        original = self.base / asset["path"]
        original.unlink()
        original.symlink_to(EXAMPLE)
        with patch.object(campaign.os, "read", side_effect=AssertionError("symlink read")):
            self.assertIn("asset_symlink", self.codes(plan_campaign(self.spec, self.base)))
        original.unlink()
        original.parent.rmdir()
        original.parent.symlink_to(EXAMPLE.parent, target_is_directory=True)
        with patch.object(campaign.os, "read", side_effect=AssertionError("symlink parent read")):
            self.assertIn("asset_symlink", self.codes(plan_campaign(self.spec, self.base)))

    def test_dataless_leaf_refused_before_open_or_read(self):
        asset = self.asset()
        real_stat = os.stat
        real_open = os.open
        def flagged(path, *args, **kwargs):
            info = real_stat(path, *args, **kwargs)
            if path == "test.dat":
                return SimpleNamespace(st_flags=campaign._DATALESS)
            return info
        def no_leaf_open(path, *args, **kwargs):
            if path == "test.dat":
                raise AssertionError("dataless leaf opened")
            return real_open(path, *args, **kwargs)
        # Preserve the capability check while wrapping os.open for the probe.
        with patch.object(campaign.os, "stat", side_effect=flagged), \
                patch.object(campaign.os, "open", side_effect=no_leaf_open) as wrapped, \
                patch.object(campaign.os, "supports_dir_fd", os.supports_dir_fd | {wrapped}), \
                patch.object(campaign.os, "read", side_effect=AssertionError("dataless read")):
            self.assertIn("asset_dataless", self.codes(plan_campaign(self.spec, self.base)))

    def test_nonregular_and_empty_files_are_not_opened_for_content(self):
        asset = self.asset()
        target = self.base / asset["path"]
        target.unlink()
        target.mkdir()
        self.assertIn("asset_not_regular", self.codes(plan_campaign(self.spec, self.base)))
        target.rmdir()
        target.touch()
        self.assertIn("asset_size_bound", self.codes(plan_campaign(self.spec, self.base)))
        if hasattr(os, "mkfifo"):
            target.unlink()
            os.mkfifo(target)
            self.assertIn("asset_not_regular", self.codes(plan_campaign(self.spec, self.base)))

    def test_declared_total_and_actual_read_bounds(self):
        self.asset(content=b"abcdef")
        self.spec["resources"]["max_asset_bytes"] = 5
        self.assert_invalid(self.spec)
        self.spec["domains"][0]["assets"][0]["size_bytes"] = None
        self.assertIn("asset_size_bound", self.codes(plan_campaign(self.spec, self.base)))
        self.spec["resources"]["max_asset_bytes"] = 6
        self.spec["resources"]["max_total_asset_bytes"] = 6
        self.spec["domains"][0]["assets"][0]["size_bytes"] = 6
        self.asset("inputs/other.dat", role="parameters", content=b"1")
        self.assert_invalid(self.spec)

    def test_appended_asset_never_reads_beyond_per_file_or_total_cap(self):
        asset = self.asset(content=b"a")
        target = self.base / asset["path"]
        self.spec["resources"]["max_asset_bytes"] = 1
        self.spec["resources"]["max_total_asset_bytes"] = 1
        real_read = os.read
        bytes_read = []
        def append_during_read(fd, size):
            if not bytes_read:
                with target.open("ab") as handle:
                    handle.write(b"b")
            data = real_read(fd, size)
            bytes_read.append(len(data))
            return data
        with patch.object(campaign.os, "read", side_effect=append_during_read):
            plan = plan_campaign(self.spec, self.base)
        self.assertEqual(sum(bytes_read), 1)
        self.assertEqual(plan["totals"]["hashed_bytes"], 1)
        self.assertIn("asset_changed", self.codes(plan))
        self.assertEqual(plan["assets"][0]["status"], "rejected")

    def test_truncated_asset_early_eof_is_refused(self):
        asset = self.asset(content=b"a")
        target = self.base / asset["path"]
        real_read = os.read
        def truncate_during_read(fd, size):
            target.write_bytes(b"")
            return real_read(fd, size)
        with patch.object(campaign.os, "read", side_effect=truncate_during_read):
            plan = plan_campaign(self.spec, self.base)
        self.assertIn("asset_changed", self.codes(plan))
        self.assertEqual(plan["totals"]["hashed_bytes"], 0)
        self.assertEqual(plan["assets"][0]["status"], "rejected")

    def test_appended_campaign_never_reads_beyond_admitted_size(self):
        content = json.dumps(self.spec).encode()
        target = self.write("growing-campaign.json", content)
        real_read = os.read
        bytes_read = []
        def append_during_read(fd, size):
            if not bytes_read:
                with target.open("ab") as handle:
                    handle.write(b" ")
            data = real_read(fd, size)
            bytes_read.append(len(data))
            return data
        with patch.object(campaign, "MAX_SPEC_BYTES", len(content)), \
                patch.object(campaign.os, "read", side_effect=append_during_read):
            with self.assertRaisesRegex(CampaignError, "changed during read"):
                load_campaign(target)
        self.assertEqual(sum(bytes_read), len(content))

    def test_truncated_campaign_early_eof_is_refused(self):
        target = self.write("shrinking-campaign.json", json.dumps(self.spec).encode())
        real_read = os.read
        def truncate_during_read(fd, size):
            target.write_bytes(b"")
            return real_read(fd, size)
        with patch.object(campaign.os, "read", side_effect=truncate_during_read):
            with self.assertRaisesRegex(CampaignError, "ended before its admitted size"):
                load_campaign(target)

    def test_deterministic_plan_and_identity_change(self):
        self.asset()
        first = plan_campaign(self.spec, self.base)
        second = plan_campaign(deepcopy(self.spec), self.base)
        self.assertEqual(first, second)
        spec = deepcopy(self.spec)
        spec["campaign_id"] += "-changed"
        self.assertNotEqual(first["plan_id"], plan_campaign(spec, self.base)["plan_id"])

    def test_disabled_asset_checks_cannot_appear_verified(self):
        self.asset()
        with patch.object(campaign.os, "open", side_effect=AssertionError("disabled checks opened file")):
            plan = plan_campaign(self.spec, self.base, check_assets=False)
        self.assertIn("asset_checks_disabled", self.codes(plan))
        self.assertEqual(plan["assets"][0]["status"], "not_checked")
        self.assertFalse(plan["execution_ready"])

    def test_plan_size_does_not_materialize_issue_ledger(self):
        origin = datetime(2021, 12, 1, tzinfo=timezone.utc)
        self.spec["issue_times_utc"] = [(origin + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00Z") for i in range(1, 5001)]
        self.spec["history"]["stop_time_utc"] = (origin + timedelta(hours=5018)).strftime("%Y-%m-%dT%H:00:00Z")
        plan = plan_campaign(self.spec, self.base)
        self.assertEqual(plan["totals"]["expected_forecast_rows"], 90_000)
        self.assertLess(len(json.dumps(plan)), 10_000)
        self.assertNotIsInstance(iter_ledger(self.spec), list)

    def test_duplicate_domains_locations_reaches_and_asset_paths(self):
        variants = []
        spec = deepcopy(self.spec)
        spec["domains"].append(deepcopy(spec["domains"][0]))
        variants.append(spec)
        spec = deepcopy(self.spec)
        spec["domains"][0]["locations"].append(deepcopy(spec["domains"][0]["locations"][0]))
        variants.append(spec)
        spec = deepcopy(self.spec)
        spec["domains"][0]["locations"].append({"location_id": "other", "reach_id": "1017693"})
        variants.append(spec)
        self.asset()
        spec = deepcopy(self.spec)
        spec["domains"][0]["assets"].append(deepcopy(spec["domains"][0]["assets"][0]))
        variants.append(spec)
        for spec in variants:
            self.assert_invalid(spec)

    def test_schema_exact_fields_and_path_pattern_match_validator(self):
        schema = json.loads((ROOT / "schemas/campaign.schema.json").read_text())
        self.assertEqual(set(schema["required"]), set(self.spec))
        path_pattern = re.compile(schema["$defs"]["asset"]["properties"]["path"]["pattern"])
        for path in ("a", "inputs/a.csv", "one.two/three-four"):
            self.assertIsNotNone(path_pattern.fullmatch(path), path)
        for path in (".", "..", "/a", "a/../b", "a\\b", "a//b", "a/", "a\nb"):
            self.assertIsNone(path_pattern.fullmatch(path), path)


if __name__ == "__main__":
    unittest.main()
