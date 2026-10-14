"""Synthetic preparation receipts only; no scientific inputs or model runs."""

from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ngen_reforecast.preparation import RequestPreparationError, normalize_request
from ngen_reforecast.preparation.readiness import (
    CHECK_IDS, RECEIPT_VERSION, assess_preparation, preparation_binding,
)


BASE = {"identifier_type": "usgs", "identifier": "03479000", "mode": "reforecast",
        "start_date": "2022-01-01", "end_date": "2022-01-02", "max_lead_hours": 6}
ORIGIN = "2021-12-01T00:00:00Z"
ROOT = Path(__file__).absolute().parents[1]


def request(**changes):
    return normalize_request({**BASE, **changes})


def receipt(check, status="passed", *, study=None, origin=ORIGIN,
            evidence_class="synthetic"):
    bound = preparation_binding(study or request(), origin_time_utc=origin)
    return {
        "receipt_schema_version": RECEIPT_VERSION, "check_id": check,
        "status": status,
        "binding": {key: bound[key] for key in ("request_sha256", "scope_sha256")},
        "evidence": None if status == "unknown" else {
            "artifact_sha256": hashlib.sha256(b"inert synthetic receipt").hexdigest(),
            "verifier": "unit-test-fake", "evidence_class": evidence_class,
            "detail": "Synthetic outcome; no physical artifact has been inspected.",
        },
    }


class PreparationReadinessTests(unittest.TestCase):
    def report(self, **kwargs):
        return assess_preparation(request(), origin_time_utc=kwargs.pop("origin_time_utc", ORIGIN), **kwargs)

    def assert_error(self, call, code):
        with self.assertRaises(RequestPreparationError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        self.assertTrue(caught.exception.field)

    def test_no_receipts_means_unknown_not_missing_or_failed(self):
        report = assess_preparation(request())
        self.assertEqual([item["status"] for item in report["checks"]], ["unknown"] * 7)
        self.assertIsNone(report["preparation_binding"]["scope"]["required_history_interval"])
        codes = {item["code"] for item in report["blockers"]}
        self.assertIn("INITIALIZATION_NOT_SELECTED", codes)
        self.assertIn("SOURCE_COVERAGE_UNKNOWN", codes)
        self.assertNotIn("SOURCE_COVERAGE_MISSING", codes)
        self.assertNotIn("SOURCE_COVERAGE_FAILED", codes)
        for item in report["blockers"]:
            self.assertTrue(item["requirement"] and item["next_option"])
        self.assertFalse(report["execution_ready"])

    def test_missing_failed_unknown_and_passed_have_distinct_actionable_results(self):
        items = [receipt("source_coverage", "failed"),
                 receipt("input_bundle", "missing"), receipt("runtime_identity", "unknown"),
                 receipt("location_resolution")]
        report = self.report(check_receipts=items)
        states = {item["check_id"]: item["status"] for item in report["checks"]}
        self.assertEqual(states["source_coverage"], "failed")
        self.assertEqual(states["input_bundle"], "missing")
        self.assertEqual(states["runtime_identity"], "unknown")
        self.assertEqual(states["location_resolution"], "passed")
        failures = {item["code"]: item for item in report["blockers"]}
        self.assertEqual(failures["SOURCE_COVERAGE_FAILED"]["evidence"], items[0]["evidence"])
        self.assertIn("full 18-hour", failures["SOURCE_COVERAGE_FAILED"]["next_option"])
        self.assertIn("INPUT_BUNDLE_MISSING", failures)
        self.assertIn("RUNTIME_IDENTITY_UNKNOWN", failures)
        self.assertNotIn("LOCATION_RESOLUTION_UNKNOWN", failures)

    def test_all_passed_receipts_never_grant_execution_or_scientific_qualification(self):
        for evidence_class in ("synthetic", "declared_metadata", "verification_receipt"):
            with self.subTest(evidence_class=evidence_class):
                report = self.report(check_receipts=[receipt(check, evidence_class=evidence_class) for check in CHECK_IDS])
                self.assertEqual(report["preparation_checks_status"], "all_reported_passed")
                self.assertEqual(report["status"], "blocked")
                self.assertFalse(report["execution_ready"] or report["release_qualified"])
                self.assertEqual([item["code"] for item in report["blockers"]],
                                 ["CAMPAIGN_PROTOCOL_NOT_ADMITTED", "EXECUTION_SERVICE_UNAVAILABLE"])
                self.assertFalse(report["evidence_boundary"]["freshness_established"])
                self.assertFalse(report["evidence_boundary"]["scientific_qualification_established"])
                self.assertTrue(all(not item["artifact_verified_by_this_interface"] for item in report["checks"]))

    def test_reported_initialization_pass_cannot_select_an_origin(self):
        study = request()
        report = assess_preparation(study, check_receipts=[receipt(check, study=study, origin=None) for check in CHECK_IDS])
        self.assertEqual(report["preparation_checks_status"], "incomplete")
        self.assertIn("INITIALIZATION_NOT_SELECTED", {item["code"] for item in report["blockers"]})

    def test_two_issue_receipt_cannot_shrink_a_whole_day_request(self):
        small = request(start_hour_utc=23, end_hour_utc=0)
        report = self.report(check_receipts=[receipt("source_coverage", study=small)])
        self.assertEqual(report["requested_population"]["preview"]["issue_count"], 48)
        self.assertEqual(len(report["requested_population"]["issues_utc"]), 48)
        self.assertEqual(report["checks"][2]["status"], "evidence_mismatch")
        self.assertIn("PREPARATION_EVIDENCE_BINDING_MISMATCH", {item["code"] for item in report["blockers"]})

    def test_changed_site_origin_policy_and_scope_receipts_are_unusable(self):
        candidates = [receipt("source_coverage", study=request(identifier="99999999")),
                      receipt("source_coverage", origin="2021-12-02T00:00:00Z")]
        short_scope = receipt("source_coverage")
        short_scope["binding"]["scope_sha256"] = "0" * 64
        candidates.append(short_scope)
        for item in candidates:
            with self.subTest(binding=item["binding"]):
                report = self.report(check_receipts=[item])
                self.assertEqual(report["checks"][2]["reported_status"], "passed")
                self.assertEqual(report["checks"][2]["status"], "evidence_mismatch")
                self.assertEqual(report["requested_request"], request())

    def test_origin_is_explicit_exact_hourly_utc_and_before_first_issue(self):
        invalid = ["2022-01-01T00:00:00Z", "2022-01-01T01:00:00Z", "2021-12-01T00:30:00Z",
                   "2021-12-01T00:00:00+00:00", "2021-02-29T00:00:00Z", "2021-12-01", 1]
        for origin in invalid:
            with self.subTest(origin=origin):
                self.assert_error(lambda: self.report(origin_time_utc=origin), "INVALID_INITIALIZATION_ORIGIN")

    def test_selected_history_bound_cannot_silently_shorten_initialization(self):
        self.assert_error(lambda: preparation_binding(request(), origin_time_utc="2000-01-01T00:00:00Z"),
                          "PREPARATION_SCOPE_LIMIT_EXCEEDED")
        early = request(start_date="0001-01-01", end_date="0001-01-01", start_hour_utc=1, end_hour_utc=1)
        report = assess_preparation(early, origin_time_utc="0001-01-01T00:00:00Z")
        self.assertEqual(report["requested_population"]["issues_utc"], ["0001-01-01T01:00:00Z"])

    def test_retained_leads_never_shorten_the_physical_preparation_scope(self):
        scopes = []
        for lead in (1, 6, 18):
            report = assess_preparation(request(max_lead_hours=lead), origin_time_utc=ORIGIN)
            scope = report["preparation_binding"]["scope"]
            scopes.append(scope)
            self.assertEqual(scope["required_source_leads"], {"min": 1, "max": 18})
            self.assertEqual(scope["required_history_interval"]["stop_time_utc_exclusive"], "2022-01-03T17:00:00Z")
            self.assertEqual(scope["required_history_interval"]["provider_label"], "interval_start")
            self.assertEqual(report["requested_population"]["preview"]["generated_rows_per_location"], 864)
            self.assertEqual(report["requested_population"]["preview"]["retained_rows_per_location"], 48 * lead)
        self.assertEqual(len({item["request_sha256"] for item in scopes}), 3)

    def test_twelve_month_single_site_population_is_complete_without_forecasts(self):
        report = assess_preparation(request(start_date="2022-01-01", end_date="2022-12-31"), origin_time_utc=ORIGIN)
        population = report["requested_population"]
        self.assertEqual(len(population["issues_utc"]), 8760)
        self.assertEqual(population["issues_utc"][0], "2022-01-01T00:00:00Z")
        self.assertEqual(population["issues_utc"][-1], "2022-12-31T23:00:00Z")
        self.assertEqual(population["preview"]["generated_rows_per_location"], 157680)
        self.assertEqual(population["preview"]["retained_rows_per_location"], 52560)
        self.assertEqual(population["preview"]["last_physical_valid_time_utc"], "2023-01-01T17:00:00Z")
        self.assertFalse(report["execution_ready"])

    def test_continuous_mode_does_not_manufacture_a_forecast_population(self):
        study = request(mode="continuous_simulation")
        report = assess_preparation(study)
        self.assertFalse(report["planning_supported"])
        self.assertIsNone(report["requested_population"]["issues_utc"])
        self.assertIsNone(report["preparation_binding"]["scope"]["issue_count"])
        self.assertIn("MODE_NOT_IMPLEMENTED", {item["code"] for item in report["blockers"]})
        self.assert_error(lambda: preparation_binding(study, origin_time_utc=ORIGIN), "MODE_NOT_IMPLEMENTED")

    def test_request_assertions_are_revalidated_and_receipts_cannot_live_in_request(self):
        for field, value in (("execution_ready", True), ("check_receipts", [])):
            study = request()
            study[field] = value
            self.assert_error(lambda: assess_preparation(study), "INCONSISTENT_REQUEST")

    def test_receipt_schema_refuses_unknown_extra_missing_and_duplicate_checks(self):
        good = receipt("source_coverage")
        candidates = []
        for key, value in (("receipt_schema_version", "future"), ("status", "ready"),
                           ("check_id", "worker_launch"), ("extra", True)):
            item = deepcopy(good)
            item[key] = value
            candidates.append([item])
        missing = deepcopy(good)
        del missing["binding"]
        candidates.extend([[missing], [good, deepcopy(good)], {}, [good] * 8])
        for items in candidates:
            with self.subTest(items=items):
                self.assert_error(lambda: self.report(check_receipts=items), "INVALID_PREPARATION_RECEIPT")

    def test_observed_outcomes_require_complete_evidence_and_binding(self):
        good = receipt("source_coverage")
        changes = [("evidence", None), ("binding", {"request_sha256": "A" * 64, "scope_sha256": "b" * 64})]
        for field, value in changes:
            item = deepcopy(good)
            item[field] = value
            self.assert_error(lambda: self.report(check_receipts=[item]), "INVALID_PREPARATION_RECEIPT")
        for field, value in (("verifier", ""), ("detail", "x" * 2049),
                             ("artifact_sha256", "short"), ("evidence_class", "qualified_physical")):
            item = deepcopy(good)
            item["evidence"][field] = value
            self.assert_error(lambda: self.report(check_receipts=[item]), "INVALID_PREPARATION_RECEIPT")
        item = receipt("source_coverage", "unknown")
        item["evidence"] = good["evidence"]
        self.assert_error(lambda: self.report(check_receipts=[item]), "INVALID_PREPARATION_RECEIPT")

    def test_receipt_input_is_bounded_plain_json(self):
        cycle = []
        cycle.append(cycle)
        self.assert_error(lambda: self.report(check_receipts=cycle), "MALFORMED_REQUEST")
        self.assert_error(lambda: self.report(check_receipts=[object()]), "MALFORMED_REQUEST")
        item = receipt("source_coverage")
        item["evidence"]["detail"] = "x" * 65537
        self.assert_error(lambda: self.report(check_receipts=[item]), "REQUEST_LIMIT_EXCEEDED")

    def test_report_is_detached_deterministic_and_identity_bound(self):
        study = request()
        items = [receipt(check) for check in CHECK_IDS]
        report = assess_preparation(study, origin_time_utc=ORIGIN, check_receipts=items)
        baseline = deepcopy(report)
        self.assertEqual(report, assess_preparation(study, origin_time_utc=ORIGIN, check_receipts=list(reversed(items))))
        study["location"]["submitted_identifier"] = "1"
        items[0]["evidence"]["detail"] = "mutated"
        self.assertEqual(report, baseline)
        content = deepcopy(report)
        identities = content.pop("identities")
        raw = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        self.assertEqual(identities["report_sha256"], hashlib.sha256(raw).hexdigest())
        changed = self.report(check_receipts=[receipt("source_coverage", "failed")])
        self.assertNotEqual(report["identities"]["report_sha256"], changed["identities"]["report_sha256"])

    def test_numerically_equivalent_json_has_the_same_request_identity(self):
        study = request()
        first = preparation_binding(study)
        report = assess_preparation(study)
        study["preview"]["issue_count"] = 48.0
        self.assertEqual(first, preparation_binding(study))
        self.assertEqual(report, assess_preparation(study))

    def test_zero_asset_acquisition_admission_worker_archive_and_process_calls(self):
        # Resolve mocks before the guard so imports are outside the assessed call.
        targets = ["ngen_reforecast.execution.execute_campaign", "ngen_reforecast.execution.preflight_execution",
                   "ngen_reforecast.execution_lock.prepare_execution", "ngen_reforecast.execution_lock.verify_execution_assets",
                   "ngen_reforecast.archive.verify_result", "ngen_reforecast.archive.export_result",
                   "subprocess.Popen", "subprocess.run", "socket.create_connection", "urllib.request.urlopen"]
        policy = ROOT / "src/ngen_reforecast/preparation/request-policy.json"
        original_open = Path.open
        opened = []

        def policy_only(path, *args, **kwargs):
            self.assertEqual(path, policy, "Only the packaged policy can be read")
            opened.append(path)
            return original_open(path, *args, **kwargs)

        study = request()
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(target, side_effect=AssertionError(target))) for target in targets]
            stack.enter_context(patch.object(Path, "open", new=policy_only))
            report = assess_preparation(study, origin_time_utc=ORIGIN)
            self.assertFalse(report["execution_ready"])
            for mock in mocks:
                mock.assert_not_called()
        self.assertGreater(len(opened), 0)


if __name__ == "__main__":
    unittest.main()
