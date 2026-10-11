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
from ngen_reforecast.campaign import (
    CampaignError, iter_expected_rows, iter_ledger, load_campaign,
    normalize_campaign, plan_campaign,
)


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

    def version11(self, minimum=1, maximum=18):
        spec = deepcopy(self.spec)
        spec["schema_version"] = "1.1"
        spec["retained_leads"] = {
            "min_lead_hours": minimum, "max_lead_hours": maximum, "projection": "export",
        }
        return spec

    def with_schedule(self, start="2022-01-01T23:00:00Z", stop="2022-01-02T01:00:00Z", cadence=1):
        spec = self.version11()
        del spec["issue_times_utc"]
        spec["issue_schedule"] = {
            "start_time_utc": start, "stop_time_utc_exclusive": stop, "cadence_hours": cadence,
        }
        return spec

    def test_schema10_example_shape_and_identities_are_unchanged(self):
        # Recorded from the public 1.0 implementation before this extension.
        plan = plan_campaign(self.spec, self.base, check_assets=False)
        self.assertEqual(plan["specification_sha256"], "3ea062cdbdf92eef5bbe716d67215c4ee5d29b7ffcf8e290b712415baa30f849")
        self.assertEqual(plan["plan_id"], "75b88ee5faae67724883a8e3f925cc02869e7365e04bc2ba8be499431335d65a")
        self.assertEqual(normalize_campaign(self.spec), self.spec)
        self.assertNotIn("retained_leads", plan)
        self.assertNotIn("generated_forecast_rows", plan["totals"])
        self.assertEqual(list(iter_ledger(self.spec)), list(iter_expected_rows(self.spec, "retained")))
        extended = self.version11()
        extended["schema_version"] = "1.0"
        self.assert_invalid(extended)
        schedule = self.with_schedule()
        schedule["schema_version"] = "1.0"
        del schedule["retained_leads"]
        self.assert_invalid(schedule)

    def test_retained_intervals_preserve_all_generated_rows_and_actual_lead_keys(self):
        old_rows = list(iter_ledger(self.spec))
        for minimum, maximum, retained_count in ((1, 18, 36), (1, 6, 12), (6, 6, 2)):
            with self.subTest(minimum=minimum, maximum=maximum):
                spec = self.version11(minimum, maximum)
                plan = plan_campaign(spec, self.base, check_assets=False)
                self.assertEqual(plan["totals"]["generated_forecast_rows"], 36)
                self.assertEqual(plan["totals"]["expected_forecast_rows"], 36)
                self.assertEqual(plan["totals"]["retained_forecast_rows"], retained_count)
                self.assertEqual(plan["totals"]["history_hours_per_domain"], 786)
                self.assertEqual(plan["time_contract"]["execution_horizon_hours"], 18)
                self.assertEqual(plan["time_contract"]["required_source_lead_hours"], {"min": 1, "max": 18})
                self.assertEqual(plan["time_contract"]["antecedent_history_hours_at_first_issue"], 767)
                self.assertEqual(plan["retained_leads"]["projection"], "export")
                self.assertFalse(plan["execution_ready"])
                self.assertEqual(list(iter_ledger(spec)), old_rows)
                self.assertEqual(list(iter_expected_rows(spec, "generated")), old_rows)
                retained = list(iter_expected_rows(spec, "retained"))
                self.assertEqual(retained, [row for row in old_rows if minimum <= row["lead_hour"] <= maximum])
                self.assertEqual(len(retained), retained_count)
        self.assertEqual(list(iter_expected_rows(self.version11(6, 6), "retained"))[0]["valid_time_utc"],
                         "2022-01-02T05:00:00Z")

    def test_retention_changes_product_identity_but_not_domain_input_identity(self):
        all_leads = plan_campaign(self.version11(), self.base, check_assets=False)
        subset = plan_campaign(self.version11(1, 6), self.base, check_assets=False)
        self.assertNotEqual(all_leads["specification_sha256"], subset["specification_sha256"])
        self.assertNotEqual(all_leads["plan_id"], subset["plan_id"])
        self.assertEqual(all_leads["domain_states"], subset["domain_states"])
        self.assertEqual(all_leads["resources"], subset["resources"])
        old = plan_campaign(self.spec, self.base, check_assets=False)
        self.assertNotEqual(old["specification_sha256"], all_leads["specification_sha256"])

    def test_retained_selection_cannot_shorten_horizon_or_history_coverage(self):
        for field in ("horizon", "history"):
            with self.subTest(field=field):
                spec = self.version11(1, 6)
                if field == "horizon":
                    spec["horizon_hours"] = 6
                else:
                    spec["history"]["stop_time_utc"] = "2022-01-02T06:00:00Z"
                self.assert_invalid(spec)

    def test_invalid_retention_limits_shapes_and_projection_are_rejected(self):
        for minimum, maximum in ((0, 6), (1, 19), (6, 5), (True, 6), (1, False),
                                 (1.0, 6), (1, 6.0), (None, 6), (1, "6")):
            with self.subTest(minimum=minimum, maximum=maximum):
                self.assert_invalid(self.version11(minimum, maximum))
        for retained in (None, [1, 3, 6], {},
                         {"min_lead_hours": 1, "max_lead_hours": 6},
                         {"min_lead_hours": 1, "max_lead_hours": 6, "projection": "commit"},
                         {"min_lead_hours": 1, "max_lead_hours": 6, "projection": True},
                         {"min_lead_hours": 1, "max_lead_hours": 6, "projection": "export", "extra": 1}):
            with self.subTest(retained=retained):
                spec = self.version11()
                spec["retained_leads"] = retained
                self.assert_invalid(spec)
        for kind in ("export", "", None, True, ["retained"]):
            with self.subTest(kind=kind), self.assertRaises(CampaignError):
                list(iter_expected_rows(self.version11(), kind))

    def test_nested_locations_and_domains_have_distinct_generated_and_retained_totals(self):
        spec = self.version11(6, 6)
        spec["domains"][0]["locations"].append({"location_id": "nested", "reach_id": "999"})
        spec["domains"].append({"domain_id": "second", "locations": [{"location_id": "other", "reach_id": "1"}], "assets": []})
        plan = plan_campaign(spec, self.base, check_assets=False)
        self.assertEqual(plan["totals"]["branch_count"], 4)
        self.assertEqual(plan["totals"]["location_count"], 3)
        self.assertEqual(plan["totals"]["total_parent_history_hours"], 1572)
        self.assertEqual(plan["totals"]["generated_forecast_rows"], 108)
        self.assertEqual(plan["totals"]["retained_forecast_rows"], 6)
        self.assertEqual(len(list(iter_expected_rows(spec, "retained"))), 6)

    def test_cadence_uses_inclusive_start_and_exclusive_stop(self):
        cases = (
            ("2022-01-01T22:00:00Z", "2022-01-02T00:00:00Z", 1,
             ["2022-01-01T22:00:00Z", "2022-01-01T23:00:00Z"]),
            ("2022-01-01T16:00:00Z", "2022-01-02T00:00:00Z", 3,
             ["2022-01-01T16:00:00Z", "2022-01-01T19:00:00Z", "2022-01-01T22:00:00Z"]),
            ("2021-12-30T00:00:00Z", "2022-01-02T00:00:00Z", 24,
             ["2021-12-30T00:00:00Z", "2021-12-31T00:00:00Z", "2022-01-01T00:00:00Z"]),
        )
        for start, stop, cadence, expected in cases:
            with self.subTest(cadence=cadence):
                spec = self.with_schedule(start, stop, cadence)
                normalized = normalize_campaign(spec)
                self.assertEqual(normalized["issue_times_utc"], expected)
                self.assertNotIn("issue_schedule", normalized)
                plan = plan_campaign(spec, self.base, check_assets=False)
                self.assertEqual(plan["totals"]["issue_count"], len(expected))
                self.assertEqual(plan["totals"]["generated_forecast_rows"], 18 * len(expected))
                self.assertEqual(plan["totals"]["history_hours_per_domain"], 786)

    def test_schedule_list_and_file_normalize_to_identical_detached_campaigns(self):
        scheduled = self.with_schedule()
        before = deepcopy(scheduled)
        normalized = normalize_campaign(scheduled)
        self.assertEqual(scheduled, before)
        self.assertEqual(normalized, self.version11())
        self.assertEqual(normalize_campaign(normalized), normalized)
        self.assertEqual(plan_campaign(scheduled, self.base, False), plan_campaign(normalized, self.base, False))
        self.assertEqual(list(iter_expected_rows(scheduled)), list(iter_expected_rows(normalized)))
        path = self.write("scheduled.json", json.dumps(scheduled).encode())
        self.assertEqual(load_campaign(path), normalized)
        normalized["history"]["stop_time_utc"] = "2022-01-02T20:00:00Z"
        normalized["domains"][0]["locations"][0]["location_id"] = "changed"
        self.assertEqual(scheduled, before)

    def test_irregular_issues_preserve_continuous_history_and_true_issue_targets(self):
        spec = self.version11(6, 6)
        spec["issue_times_utc"] = ["2021-12-30T13:00:00Z", "2022-01-01T02:00:00Z", "2022-01-02T00:00:00Z"]
        plan = plan_campaign(spec, self.base, False)
        self.assertEqual(plan["totals"]["branch_count"], 3)
        self.assertEqual(plan["totals"]["history_hours_per_domain"], 786)
        self.assertEqual(plan["totals"]["retained_forecast_rows"], 3)
        self.assertEqual([row["valid_time_utc"] for row in iter_expected_rows(spec, "retained")],
                         ["2021-12-30T19:00:00Z", "2022-01-01T08:00:00Z", "2022-01-02T06:00:00Z"])

    def test_invalid_schedule_clocks_endpoints_cadences_and_fields(self):
        for field, value in (
            ("start_time_utc", "2022-01-01T23:30:00Z"),
            ("start_time_utc", "2022-01-01T23:00:00+00:00"),
            ("stop_time_utc_exclusive", "2022-02-29T01:00:00Z"),
            ("stop_time_utc_exclusive", "2022-01-01T23:00:00Z"),
            ("stop_time_utc_exclusive", "2022-01-01T22:00:00Z"),
            ("cadence_hours", True), ("cadence_hours", 0), ("cadence_hours", -1),
            ("cadence_hours", 1.0), ("cadence_hours", "1"), ("cadence_hours", 100001),
            ("extra", "ignored?"),
        ):
            with self.subTest(field=field, value=value):
                spec = self.with_schedule()
                spec["issue_schedule"][field] = value
                self.assert_invalid(spec)
        for schedule in (None, [], {}):
            spec = self.with_schedule()
            spec["issue_schedule"] = schedule
            self.assert_invalid(spec)
        spec = self.with_schedule()
        spec["issue_times_utc"] = self.spec["issue_times_utc"]
        self.assert_invalid(spec)
        del spec["issue_times_utc"]
        del spec["issue_schedule"]
        self.assert_invalid(spec)

    def test_schedule_expansion_is_bounded_before_allocating_and_after_normalization(self):
        spec = self.with_schedule("2020-01-01T00:00:00Z", "2040-01-01T00:00:00Z", 1)
        with patch.object(campaign, "_format_time", side_effect=AssertionError("unbounded expansion")):
            with self.assertRaisesRegex(CampaignError, "expanded issue count"):
                normalize_campaign(spec)
        spec = self.with_schedule("2021-12-01T01:00:00Z", "2022-01-02T01:00:00Z", 1)
        compact_size = len(campaign._canonical(spec))
        with patch.object(campaign, "MAX_SPEC_BYTES", compact_size):
            with self.assertRaisesRegex(CampaignError, "4 MiB"):
                normalize_campaign(spec)

    def test_schedule_enforces_origin_and_full_forecast_coverage(self):
        self.assert_invalid(self.with_schedule("2021-12-01T00:00:00Z", "2021-12-01T01:00:00Z", 1))
        self.assert_invalid(self.with_schedule("2022-01-02T01:00:00Z", "2022-01-02T02:00:00Z", 1))
        spec = self.with_schedule("2022-01-01T23:00:00Z", "2022-01-02T02:00:00Z", 1)
        spec["retained_leads"]["max_lead_hours"] = 6
        self.assert_invalid(spec)

    def test_leap_day_and_supported_calendar_edges(self):
        spec = self.with_schedule("2024-02-28T23:00:00Z", "2024-03-01T01:00:00Z", 24)
        spec["origin_time_utc"] = "2024-02-28T00:00:00Z"
        spec["history"] = {"start_time_utc": spec["origin_time_utc"], "stop_time_utc": "2024-03-01T18:00:00Z"}
        self.assertEqual(normalize_campaign(spec)["issue_times_utc"],
                         ["2024-02-28T23:00:00Z", "2024-02-29T23:00:00Z"])
        spec = self.with_schedule("9999-12-31T01:00:00Z", "9999-12-31T23:00:00Z", 100000)
        spec["origin_time_utc"] = "9999-12-30T00:00:00Z"
        spec["history"] = {"start_time_utc": spec["origin_time_utc"], "stop_time_utc": "9999-12-31T23:00:00Z"}
        self.assertEqual(normalize_campaign(spec)["issue_times_utc"], ["9999-12-31T01:00:00Z"])
        spec["issue_schedule"]["start_time_utc"] = "9999-12-31T22:00:00Z"
        with self.assertRaisesRegex(CampaignError, "forecast target"):
            normalize_campaign(spec)
        spec = self.with_schedule("0001-01-01T01:00:00Z", "0001-01-01T02:00:00Z")
        spec["origin_time_utc"] = "0001-01-01T00:00:00Z"
        spec["history"] = {"start_time_utc": spec["origin_time_utc"], "stop_time_utc": "0001-01-01T19:00:00Z"}
        self.assertEqual(list(iter_expected_rows(spec))[-1]["valid_time_utc"], "0001-01-01T19:00:00Z")

    def test_schema11_example_and_structural_contract(self):
        example = load_campaign(EXAMPLE.parent / "campaign-retained.json")
        plan = plan_campaign(example, self.base, False)
        self.assertEqual(plan["totals"]["generated_forecast_rows"], 36)
        self.assertEqual(plan["totals"]["retained_forecast_rows"], 12)
        schema = json.loads((ROOT / "schemas/campaign-1.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.1")
        self.assertEqual(set(schema["required"]) | {"issue_times_utc"}, set(example))
        self.assertEqual(schema["oneOf"], [{"required": ["issue_times_utc"]}, {"required": ["issue_schedule"]}])


if __name__ == "__main__":
    unittest.main()
