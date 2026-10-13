"""Shared UI/backend requests and complete offline planning; no native runs."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from ngen_reforecast.campaign import normalize_campaign, plan_campaign
from ngen_reforecast.execution_lock import ExecutionLockError, _supported_campaign
from ngen_reforecast.preparation import (
    RequestPreparationError, normalize_request, policy_sha256, request_policy,
    translate_request, validate_request,
)


ROOT = Path(__file__).absolute().parents[1]
BASE = {"identifier_type": "usgs", "identifier": "03479000", "mode": "reforecast",
        "start_date": "2022-01-01", "end_date": "2022-01-02", "max_lead_hours": "6"}


def descriptor(request=None):
    """Declared metadata only; no source lookup, asset check or admission."""
    example = json.loads((ROOT / "examples/watauga/campaign-execution-v2.json").read_text())
    location = (request or normalize_request(BASE))["location"]
    return {"evidence_class": "server_owned_preparation_descriptor",
            "origin_time_utc": example["origin_time_utc"],
            "domains": example["domains"], "resources": example["resources"],
            "location_binding": {"identifier_type": location["identifier_type"],
                                 "submitted_identifier": location["submitted_identifier"],
                                 "status": "declared_candidate"}}


class RequestPreparationTests(unittest.TestCase):
    def raw(self, **changes):
        return {**BASE, **changes}

    def request(self, **changes):
        return normalize_request(self.raw(**changes))

    def assert_error(self, call, code=None, field=None):
        with self.assertRaises(RequestPreparationError) as caught:
            call()
        if code:
            self.assertEqual(caught.exception.code, code)
        if field:
            self.assertEqual(caught.exception.field, field)
        return caught.exception

    def test_packaged_and_browser_policy_bytes_are_identical_and_detached(self):
        raw = (ROOT / "web/request-policy.json").read_bytes()
        self.assertEqual(policy_sha256(), hashlib.sha256(raw).hexdigest())
        policy = request_policy()
        self.assertEqual(policy, json.loads(raw))
        self.assertEqual(policy["request_schema_version"], "0.2")
        policy["retained_leads"]["max"] = 999
        self.assertEqual(request_policy()["retained_leads"]["max"], 18)

    def test_whole_days_preserve_all_48_issues_and_counts(self):
        request = self.request()
        self.assertEqual(request["request_schema_version"], "0.2")
        self.assertEqual(request["study"]["first_issue_hour_utc"], 0)
        self.assertEqual(request["study"]["last_issue_hour_utc"], 23)
        self.assertEqual(request["study"]["date_semantics"], "inclusive_utc_issue_window_proposal")
        self.assertEqual(request["preview"]["issue_count"], 48)
        self.assertEqual(request["preview"]["generated_rows_per_location"], 864)
        self.assertEqual(request["preview"]["retained_rows_per_location"], 288)
        self.assertEqual(request["preview"]["last_physical_valid_time_utc"], "2022-01-03T17:00:00Z")
        self.assertFalse(request["execution_ready"])
        self.assertFalse(request["location"]["demonstration"]["is_live_resolution"])

    def test_two_hour_selection_matches_existing_executor_structural_envelope(self):
        request = self.request(start_hour_utc="23", end_hour_utc="00")
        self.assertEqual(request["preview"]["issue_count"], 2)
        self.assertEqual(request["preview"]["generated_rows_per_location"], 36)
        self.assertEqual(request["preview"]["retained_rows_per_location"], 12)
        campaign = translate_request(request, descriptor(request), campaign_id="explicit-two-issue-window")
        self.assertEqual(campaign["issue_times_utc"], ["2022-01-01T23:00:00Z", "2022-01-02T00:00:00Z"])
        self.assertEqual(campaign["history"]["stop_time_utc"], "2022-01-02T18:00:00Z")
        # This checks packaged declared profile metadata, never the bundle or
        # source files. Passing structural checks is not fresh execution admission.
        self.assertEqual(_supported_campaign(campaign), campaign)
        self.assertFalse(request["execution_ready"])

    def test_full_48_issue_translation_never_uses_diagnostic_history_endpoint(self):
        request = self.request()
        campaign = translate_request(request, descriptor(request), campaign_id="full-request-preserved")
        self.assertNotIn("issue_schedule", campaign)
        self.assertEqual(len(campaign["issue_times_utc"]), 48)
        self.assertEqual(campaign["issue_times_utc"][0], "2022-01-01T00:00:00Z")
        self.assertEqual(campaign["issue_times_utc"][-1], "2022-01-02T23:00:00Z")
        self.assertEqual(campaign["history"]["stop_time_utc"], "2022-01-03T17:00:00Z")
        plan = plan_campaign(campaign, ROOT, check_assets=False)
        self.assertEqual(plan["totals"]["issue_count"], 48)
        self.assertEqual(plan["totals"]["generated_forecast_rows"], 864)
        self.assertEqual(plan["totals"]["retained_forecast_rows"], 288)
        self.assertEqual(plan["totals"]["history_hours_per_domain"], 809)
        self.assertEqual(plan["totals"]["hashed_bytes"], 0)
        self.assertFalse(plan["execution_ready"])
        with self.assertRaises(ExecutionLockError):
            _supported_campaign(campaign)

    def test_one_issue_and_hour_window_are_continuous_not_daily_hour_filters(self):
        single = self.request(start_date="2022-01-01", end_date="2022-01-01",
                              start_hour_utc=10, end_hour_utc=10)
        self.assertEqual(single["preview"]["issue_count"], 1)
        self.assertEqual(single["preview"]["last_physical_valid_time_utc"], "2022-01-02T04:00:00Z")
        window = self.request(start_hour_utc=22, end_hour_utc=2)
        self.assertEqual(window["preview"]["issue_count"], 5)
        translated = translate_request(window, descriptor(window), campaign_id="overnight-hours")
        self.assertEqual(translated["issue_times_utc"], ["2022-01-01T22:00:00Z", "2022-01-01T23:00:00Z",
                                                      "2022-01-02T00:00:00Z", "2022-01-02T01:00:00Z",
                                                      "2022-01-02T02:00:00Z"])

    def test_inputs_outputs_and_preparation_are_not_mutated(self):
        raw = self.raw(start_hour_utc=23, end_hour_utc=0)
        original_raw = deepcopy(raw)
        request = normalize_request(raw)
        original_request = deepcopy(request)
        prep = descriptor(request)
        original_prep = deepcopy(prep)
        validated = validate_request(request)
        campaign = translate_request(request, prep, campaign_id="detached-plan")
        validated["location"]["submitted_identifier"] = "other"
        campaign["domains"][0]["locations"][0]["reach_id"] = "1"
        self.assertEqual(raw, original_raw)
        self.assertEqual(request, original_request)
        self.assertEqual(prep, original_prep)

    def test_lead_retention_preserves_full_integration_horizon(self):
        for lead in (1, 6, 18, 18.0, "0006"):
            with self.subTest(lead=lead):
                request = self.request(max_lead_hours=lead)
                expected = int(lead)
                self.assertEqual(request["preview"]["generated_rows_per_location"], 864)
                self.assertEqual(request["preview"]["retained_rows_per_location"], 48 * expected)
                self.assertEqual(request["campaign_translation_proposal"]["horizon_hours"], 18)
                self.assertEqual(validate_request(request), request)
        for lead in (0, 19, 1.5, True, None, "", "6 hours", "1e1", " 6 ", [], {}):
            with self.subTest(lead=lead):
                self.assert_error(lambda: self.request(max_lead_hours=lead), "INVALID_STUDY", "max_lead_hours")

    def test_hour_validation_rejects_boolean_fraction_out_of_range_and_reversal(self):
        for field in ("start_hour_utc", "end_hour_utc"):
            for hour in (True, False, None, -1, 24, 0.5, float("inf"), float("nan"), "24", "000", " 1 ", "1e1", [], {}):
                with self.subTest(field=field, hour=hour):
                    self.assert_error(lambda: self.request(**{field: hour}), "INVALID_STUDY", field)
        self.assert_error(lambda: self.request(start_date="2022-01-01", end_date="2022-01-01",
                                              start_hour_utc=23, end_hour_utc=0), "INVALID_STUDY", "end_hour_utc")

    def test_calendar_boundaries_real_leap_dates_and_utc_hours(self):
        for date in ("2023-02-29", "2024-02-30", "2024-04-31", "2024-13-01", "2024-01-00", "", "0000-01-01", "1-01-01"):
            with self.subTest(date=date):
                self.assert_error(lambda: self.request(start_date=date), "INVALID_STUDY", "start_date")
        self.assertEqual(self.request(start_date="2024-02-28", end_date="2024-03-01")["preview"]["issue_count"], 72)
        for first, last in (("2024-03-09", "2024-03-11"), ("2024-11-02", "2024-11-04")):
            self.assertEqual(self.request(start_date=first, end_date=last)["preview"]["issue_count"], 72)
        ancient = self.request(start_date="0001-01-01", end_date="0001-01-01", start_hour_utc=1)
        self.assertEqual(ancient["study"]["first_issue_time_utc"], "0001-01-01T01:00:00Z")
        self.assert_error(lambda: self.request(start_date="0001-01-01", end_date="0001-01-01"), "INVALID_STUDY", "start_date")
        upper = self.request(start_date="9999-12-31", end_date="9999-12-31", start_hour_utc=5, end_hour_utc=5)
        self.assertEqual(upper["preview"]["last_physical_valid_time_utc"], "9999-12-31T23:00:00Z")
        self.assert_error(lambda: self.request(start_date="9999-12-31", end_date="9999-12-31", start_hour_utc=6, end_hour_utc=6), "INVALID_STUDY", "end_date")

    def test_exact_offline_size_limit_includes_initialization_and_full_horizon(self):
        first = datetime(2000, 1, 1, tzinfo=timezone.utc)
        last = first + timedelta(hours=99_981)
        request = self.request(start_date="2000-01-01", end_date=last.strftime("%Y-%m-%d"), end_hour_utc=last.hour)
        self.assertEqual(request["preview"]["issue_count"], 99_982)
        prep = descriptor(request)
        prep["origin_time_utc"] = "1999-12-31T23:00:00Z"
        campaign = translate_request(request, prep, campaign_id="bounded-full-schedule")
        self.assertEqual(len(campaign["issue_times_utc"]), 99_982)
        self.assertEqual(campaign["history"]["start_time_utc"], "1999-12-31T23:00:00Z")
        last += timedelta(hours=1)
        self.assert_error(lambda: self.request(start_date="2000-01-01", end_date=last.strftime("%Y-%m-%d"), end_hour_utc=last.hour), "INVALID_STUDY", "end_date")

    def test_identifier_normalization_matches_js_and_does_not_assert_resolution(self):
        self.assertEqual(self.request(identifier="\ufeff 03479000 \u00a0")["location"]["submitted_identifier"], "03479000")
        self.assert_error(lambda: self.request(identifier="\u008503479000"), "INVALID_STUDY", "identifier")
        for identifier in ("", "gauge 03479000", "0" * 121, True, None):
            self.assert_error(lambda: self.request(identifier=identifier), "INVALID_STUDY", "identifier")
        self.assertEqual(self.request(identifier_type="watershed", identifier="🌊" * 60)["location"]["submitted_identifier"], "🌊" * 60)
        self.assert_error(lambda: self.request(identifier_type="watershed", identifier="🌊" * 61), "INVALID_STUDY", "identifier")
        for kind, identifier in (("nwm", "1017693"), ("usgs", "00000000"), ("watershed", "Watauga")):
            location = self.request(identifier_type=kind, identifier=identifier)["location"]
            self.assertEqual(location["resolution_status"], "unresolved")
            self.assertIsNone(location["demonstration"])

    def test_continuous_mode_remains_explicitly_unimplemented(self):
        request = self.request(mode="continuous_simulation", max_lead_hours=None)
        self.assertIsNone(request["preview"])
        self.assertIsNone(request["campaign_translation_proposal"])
        for key in ("requested_max_lead_hours", "first_issue_hour_utc", "last_issue_hour_utc", "first_issue_time_utc", "last_issue_time_utc"):
            self.assertIsNone(request["study"][key])
        self.assertEqual(validate_request(request), request)
        self.assert_error(lambda: translate_request(request, descriptor(request), campaign_id="no-continuous-run"), "MODE_NOT_IMPLEMENTED")

    def test_serialized_preview_clock_and_readiness_forgery_are_rejected(self):
        paths = [("preview", "issue_count", 2), ("preview", "generated_rows_per_location", 36),
                 ("preview", "issue_count", True), ("study", "last_issue_time_utc", "2022-01-02T00:00:00Z"),
                 ("study", "date_semantics", "inclusive_utc_issue_dates_proposal"),
                 ("location", "resolution_status", "verified")]
        for parent, name, value in paths:
            with self.subTest(parent=parent, name=name):
                forged = self.request()
                forged[parent][name] = value
                self.assert_error(lambda: validate_request(forged), "INCONSISTENT_REQUEST")
        for value in (True, 1, 0):
            forged = self.request()
            forged["execution_ready"] = value
            self.assert_error(lambda: validate_request(forged), "INCONSISTENT_REQUEST")
        forged = self.request()
        forged["preparation"]["worker_socket"] = "/untrusted/socket"
        self.assert_error(lambda: validate_request(forged), "INCONSISTENT_REQUEST")

    def test_old_schema_requires_explicit_rebuild_without_mutating_stored_data(self):
        old = self.request()
        old["request_schema_version"] = "0.1"
        before = deepcopy(old)
        self.assert_error(lambda: validate_request(old), "REQUEST_SCHEMA_MIGRATION_REQUIRED")
        self.assertEqual(old, before)
        for version in (None, "0.3", True):
            invalid = self.request()
            invalid["request_schema_version"] = version
            self.assert_error(lambda: validate_request(invalid), "UNSUPPORTED_REQUEST_SCHEMA")

    def test_non_json_cycles_depth_and_byte_limits_fail_before_translation(self):
        class CustomDict(dict):
            pass
        for malformed in (None, [], CustomDict(), {1: "bad"}, {"__proto__": {}}, {"x": object()}, {"x": float("inf")}, {"x": 10**1000}):
            with self.subTest(kind=type(malformed).__name__):
                self.assert_error(lambda: validate_request(malformed))
        cycle = {}
        cycle["cycle"] = cycle
        self.assert_error(lambda: validate_request(cycle), "MALFORMED_REQUEST")
        depth = {}
        for _ in range(18):
            depth = {"child": depth}
        self.assert_error(lambda: validate_request(depth), "REQUEST_LIMIT_EXCEEDED")
        self.assert_error(lambda: validate_request({"many": [None] * 4097}), "REQUEST_LIMIT_EXCEEDED")
        self.assert_error(lambda: validate_request({"too_big": "🌊" * 20_000}), "REQUEST_LIMIT_EXCEEDED")

    def test_descriptor_is_required_and_must_bind_the_submitted_location(self):
        request = self.request()
        self.assert_error(lambda: translate_request(request, {}, campaign_id="no-descriptor"), "PREPARATION_DESCRIPTOR_INVALID")
        prep = descriptor(request)
        prep["location_binding"]["submitted_identifier"] = "00000000"
        self.assert_error(lambda: translate_request(request, prep, campaign_id="no-substitution"), "PREPARATION_LOCATION_MISMATCH")
        prep = descriptor(request)
        prep["location_binding"]["status"] = "unresolved"
        self.assert_error(lambda: translate_request(request, prep, campaign_id="invalid-binding-status"), "PREPARATION_LOCATION_MISMATCH")
        prep = descriptor(request)
        prep["evidence_class"] = "client_assertion"
        self.assert_error(lambda: translate_request(request, prep, campaign_id="no-client-evidence"), "PREPARATION_DESCRIPTOR_INVALID")

    def test_unsupported_descriptor_origin_and_resources_do_not_rewrite_the_request(self):
        request = self.request()
        before = deepcopy(request)
        for name, value in (("origin_time_utc", "2022-01-01T00:00:00Z"),
                            ("origin_time_utc", "2022-01-01T00:30:00Z"),
                            ("resources", {**descriptor()["resources"], "host_cpus": 1})):
            with self.subTest(name=name, value=value):
                prep = descriptor(request)
                prep[name] = value
                self.assert_error(lambda: translate_request(request, prep, campaign_id="invalid-descriptor"), "CAMPAIGN_TRANSLATION_UNSUPPORTED")
                self.assertEqual(request, before)
        future = self.request(start_date="2100-01-01", end_date="2100-01-02")
        self.assert_error(lambda: translate_request(future, descriptor(future), campaign_id="history-bound-exceeded"), "CAMPAIGN_TRANSLATION_UNSUPPORTED")
        self.assertEqual(future["preview"]["issue_count"], 48)

    def test_preparation_does_not_call_execution_asset_or_campaign_jobs(self):
        with patch("ngen_reforecast.execution.execute_campaign", side_effect=AssertionError("model execution called")), \
                patch("ngen_reforecast.execution_lock.prepare_execution", side_effect=AssertionError("fresh admission called")), \
                patch("ngen_reforecast.campaign._open_resident", side_effect=AssertionError("input asset read")):
            request = self.request()
            validated = validate_request(request)
            campaign = translate_request(validated, descriptor(request), campaign_id="offline-only")
            self.assertEqual(len(normalize_campaign(campaign)["issue_times_utc"]), 48)

    def test_python_and_js_share_canonical_valid_outputs_and_invalid_fields(self):
        valid = [self.raw(), self.raw(start_hour_utc="23", end_hour_utc="00"),
                 self.raw(start_date="2022-01-01", end_date="2022-01-01", start_hour_utc=10, end_hour_utc=10),
                 self.raw(start_date="2024-02-28", end_date="2024-03-01", max_lead_hours=18),
                 self.raw(start_date="0099-12-31", end_date="0100-01-01"),
                 self.raw(start_date="0001-01-01", end_date="0001-01-01", start_hour_utc=1),
                 self.raw(start_date="9999-12-31", end_date="9999-12-31", start_hour_utc=5, end_hour_utc=5),
                 self.raw(identifier="\ufeff 03479000 \u00a0"),
                 self.raw(identifier_type="watershed", identifier="🌊" * 60),
                 self.raw(identifier_type="watershed", identifier="Unicode \u2028name"),
                 self.raw(identifier_type="nwm", identifier="1017693"),
                 self.raw(max_lead_hours="0006", start_hour_utc=23.0, end_hour_utc=0.0),
                 self.raw(mode="continuous_simulation", max_lead_hours=None)]
        invalid = [self.raw(start_hour_utc=hour) for hour in (None, True, "000", "24", " 1 ", 0.5)]
        invalid += [self.raw(max_lead_hours=lead) for lead in (True, "1e1", 0, 19)]
        invalid += [self.raw(start_date="2023-02-29"), self.raw(start_date="0001-01-01", end_date="0001-01-01"),
                    self.raw(start_date="9999-12-31", end_date="9999-12-31"),
                    self.raw(start_date="2000-01-01", end_date="2020-01-01"),
                    self.raw(start_date="2022-01-01", end_date="2022-01-01", start_hour_utc=23, end_hour_utc=0),
                    self.raw(identifier_type="watershed", identifier="🌊" * 61), self.raw(identifier="\u008503479000")]
        script = """import { buildRequest } from './web/request.mjs';
let text = ''; for await (const chunk of process.stdin) text += chunk;
const cases = JSON.parse(text);
console.log(JSON.stringify(cases.map(input => { try { return { value: buildRequest(input) }; }
catch (error) { return { field: error.field }; } })));
"""
        result = subprocess.run(["node", "--input-type=module", "-e", script],
                                input=json.dumps(valid + invalid), text=True, capture_output=True,
                                cwd=ROOT, timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        javascript = json.loads(result.stdout)
        self.assertEqual(len(javascript), len(valid) + len(invalid))
        for raw, expected in zip(valid, javascript[:len(valid)]):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_request(raw), expected["value"])
                self.assertEqual(validate_request(expected["value"]), expected["value"])
        for raw, expected in zip(invalid, javascript[len(valid):]):
            with self.subTest(raw=raw):
                self.assert_error(lambda: normalize_request(raw), "INVALID_STUDY", expected["field"])


if __name__ == "__main__":
    unittest.main()
