"""Actual resident decoded-byte checks over tiny synthetic files only."""

from contextlib import ExitStack
from copy import deepcopy
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ngen_reforecast import forcing
from ngen_reforecast.preparation import RequestPreparationError, normalize_request
from ngen_reforecast.preparation.readiness import preparation_binding
from ngen_reforecast.preparation.forcing_adapter import check_forcing_preparation, MAX_PAYLOAD_BYTES


ROOT = Path(__file__).absolute().parents[1]
ORIGIN = "2022-01-01T00:00:00Z"


class ForcingPreparationAdapterTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".local/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.request = normalize_request({"identifier_type": "usgs", "identifier": "03479000",
                                          "mode": "reforecast", "start_date": "2022-01-01",
                                          "end_date": "2022-01-01", "start_hour_utc": 1,
                                          "end_hour_utc": 2, "max_lead_hours": 6})
        self.axis = ["cat-2", "cat-1"]
        self.history = self.fixture("history", ORIGIN, 20)
        self.forecasts = {issue: self.fixture("forecast", issue, 18)
                          for issue in ("2022-01-01T01:00:00Z", "2022-01-01T02:00:00Z")}

    def descriptor(self, request=None, axis=None):
        binding = preparation_binding(request or self.request, origin_time_utc=ORIGIN)
        return {"evidence_class": "caller_owned_domain_descriptor",
                "binding": {key: binding[key] for key in ("request_sha256", "scope_sha256")},
                "catchment_ids": axis or self.axis,
                "domain_identity_sha256": hashlib.sha256(b"synthetic domain descriptor, not location resolution").hexdigest()}

    def fixture(self, role, start, hours):
        forecast = role == "forecast"
        instant = datetime.fromisoformat(start.replace("Z", "+00:00"))
        utc = lambda h: (instant + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
        mapping = forcing.FORECAST_VARIABLES if forecast else forcing.HISTORY_VARIABLES
        name = role + "-" + str(instant.hour)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow([*forcing.TIME_COLUMNS, *mapping])
        for catchment in self.axis:
            for hour in range(hours):
                writer.writerow([catchment, utc(hour), utc(hour + 1), utc(hour + 1 if forecast else hour),
                                 start if forecast else "", hour + 1 if forecast else "",
                                 3.6 if forecast else 3600, 280, 0.005, 1, -2, 95000, 200, 300])
        raw = output.getvalue().encode()
        (self.root / (name + ".csv")).write_bytes(raw)
        manifest = {
            "schema_version": "forcing-manifest/0.1", "evidence_class": "synthetic", "role": role,
            "payload": {"path": name + ".csv", "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
            "catchment_ids": self.axis, "start_time_utc": start, "stop_time_utc_exclusive": utc(hours),
            "units": deepcopy(forcing.FORECAST_UNITS if forecast else forcing.HISTORY_UNITS),
            "source": {"kind": "issue_forecast" if forecast else "historical_analysis", "product": "synthetic",
                       "issue_time_utc": start if forecast else None,
                       "objects": [{"object_key": "synthetic/" + name, "generation": "v1", "size_bytes": 123, "sha256": "a" * 64}],
                       "decoder_sha256": "b" * 64, "grid_sha256": "c" * 64},
            "transformation": deepcopy(forcing.FORECAST_TRANSFORMATION if forecast else forcing.HISTORY_TRANSFORMATION),
        }
        path = self.root / (name + ".json")
        path.write_text(json.dumps(manifest))
        return path

    def call(self, **changes):
        params = {"serialized_request": self.request, "origin_time_utc": ORIGIN,
                  "domain_descriptor": self.descriptor(), "history_manifest_path": self.history,
                  "forecast_manifest_paths": self.forecasts, "base_dir": self.root}
        return check_forcing_preparation(**{**params, **changes})

    def codes(self, result):
        return {item["code"] for item in result["adapter_evidence"]["diagnostics"]}

    def test_real_decoded_checks_pass_but_all_qualification_limits_remain(self):
        result = self.call()
        evidence = result["adapter_evidence"]
        report = result["readiness_report"]
        self.assertEqual(evidence["checks_performed"], 3)
        self.assertTrue(evidence["decoded_content_valid"])
        self.assertFalse(evidence["source_coverage_qualified"])
        self.assertEqual(evidence["validations"][0]["expected_contract"]["stop_time_utc_exclusive"], "2022-01-01T20:00:00Z")
        self.assertEqual(evidence["validations"][0]["expected_contract"]["catchment_ids"], ["cat-1", "cat-2"])
        for validation in evidence["validations"]:
            self.assertTrue(validation["qualification_blockers"])
            self.assertFalse(validation["execution_ready"])
        self.assertEqual(report["checks"][2]["status"], "failed")
        self.assertIn("decoded_content_valid=True", report["checks"][2]["evidence"]["detail"])
        self.assertIn("source_availability_unknown", report["checks"][2]["evidence"]["detail"])
        self.assertEqual(report["checks"][2]["evidence"]["artifact_sha256"], evidence["adapter_identity_sha256"])
        self.assertFalse(report["execution_ready"])
        self.assertEqual(len(report["requested_population"]["issues_utc"]), 2)

    def test_corrupt_current_bytes_are_measured_not_accepted_from_manifest(self):
        manifest = json.loads(self.history.read_text())
        path = self.root / manifest["payload"]["path"]
        path.write_bytes(path.read_bytes().replace(b"280", b"281", 1))
        result = self.call()
        self.assertFalse(result["adapter_evidence"]["decoded_content_valid"])
        self.assertIn("payload_hash_mismatch", {item["code"] for item in result["adapter_evidence"]["validations"][0]["blockers"]})
        self.assertTrue(self.codes(result) & {"FORCING_CONTENT_CHECK_FAILED", "FORCING_INPUT_REFUSED"})

    def test_manifest_axis_is_not_allowed_to_define_the_expected_domain(self):
        result = self.call(domain_descriptor=self.descriptor(axis=["cat-other"]))
        self.assertFalse(result["adapter_evidence"]["decoded_content_valid"])
        self.assertTrue(all(any(item["code"] == "catchment_axis_mismatch" for item in validation["blockers"])
                            for validation in result["adapter_evidence"]["validations"]))

    def test_missing_manifest_does_not_read_a_partial_study(self):
        for changes in ({"history_manifest_path": None}, {"forecast_manifest_paths": {}},
                        {"forecast_manifest_paths": {next(iter(self.forecasts)): self.history}}):
            with self.subTest(changes=changes), patch("ngen_reforecast.preparation.forcing_adapter.load_forcing_manifest", side_effect=AssertionError("read")):
                result = self.call(**changes)
                self.assertEqual(result["adapter_evidence"]["checks_performed"], 0)
                self.assertEqual(result["readiness_report"]["checks"][2]["status"], "missing")
                self.assertIn("MANIFEST_NOT_SUPPLIED", self.codes(result))

    def test_absent_selected_local_file_is_missing_without_claiming_archive_absence(self):
        self.history.unlink()
        result = self.call()
        self.assertEqual(result["readiness_report"]["checks"][2]["status"], "missing")
        self.assertIn("RESIDENT_INPUT_MISSING", self.codes(result))
        self.assertEqual(result["adapter_evidence"]["checks_performed"], 0)

    def test_twelve_month_limit_preserves_all_8760_issues_without_reads(self):
        study = normalize_request({"identifier_type": "usgs", "identifier": "03479000", "mode": "reforecast",
                                   "start_date": "2022-01-01", "end_date": "2022-12-31", "max_lead_hours": 6})
        with patch("ngen_reforecast.preparation.forcing_adapter.load_forcing_manifest", side_effect=AssertionError("read")):
            result = self.call(serialized_request=study, domain_descriptor=None, origin_time_utc="2021-12-31T23:00:00Z")
        self.assertIn("ADAPTER_SCOPE_LIMIT_EXCEEDED", self.codes(result))
        self.assertEqual(len(result["readiness_report"]["requested_population"]["issues_utc"]), 8760)
        self.assertEqual(result["readiness_report"]["requested_population"]["preview"]["generated_rows_per_location"], 157680)
        self.assertFalse(result["adapter_evidence"]["population_shortened"])

    def test_mismatched_domain_receipt_is_refused_before_any_file(self):
        domain = self.descriptor()
        domain["binding"]["request_sha256"] = "0" * 64
        with patch("ngen_reforecast.preparation.forcing_adapter.load_forcing_manifest", side_effect=AssertionError("read")):
            result = self.call(domain_descriptor=domain)
        self.assertIn("DOMAIN_BINDING_MISMATCH", self.codes(result))
        self.assertEqual(result["adapter_evidence"]["checks_performed"], 0)

    def test_lead_selection_never_shortens_required_forecast_content(self):
        for lead in (1, 6, 18):
            study = deepcopy(self.request)
            raw = {"identifier_type": "usgs", "identifier": "03479000", "mode": "reforecast", "start_date": "2022-01-01", "end_date": "2022-01-01", "start_hour_utc": 1, "end_hour_utc": 2, "max_lead_hours": lead}
            study = normalize_request(raw)
            result = self.call(serialized_request=study, domain_descriptor=self.descriptor(study))
            self.assertTrue(result["adapter_evidence"]["decoded_content_valid"])
            self.assertEqual([v["expected_rows"] for v in result["adapter_evidence"]["validations"][1:]], [36, 36])
            self.assertEqual(result["readiness_report"]["requested_population"]["preview"]["retained_rows_per_location"], 2 * lead)

    def test_unknown_origin_and_continuous_mode_do_not_acquire_or_invent_inputs(self):
        result = self.call(origin_time_utc=None)
        self.assertEqual(result["readiness_report"]["checks"][2]["status"], "unknown")
        self.assertIn("INITIALIZATION_NOT_SELECTED", self.codes(result))
        study = normalize_request({"identifier_type": "watershed", "identifier": "synthetic", "mode": "continuous_simulation", "start_date": "2022-01-01", "end_date": "2022-01-02"})
        result = self.call(serialized_request=study, origin_time_utc=None)
        self.assertIsNone(result["readiness_report"]["requested_population"]["issues_utc"])
        self.assertIn("MODE_NOT_IMPLEMENTED", self.codes(result))

    def test_unsupported_descriptor_and_forecast_map_raise_contract_errors(self):
        for changes in ({"domain_descriptor": {}}, {"forecast_manifest_paths": {"2022-01-01T03:00:00Z": self.history}}):
            with self.subTest(changes=changes), self.assertRaises(RequestPreparationError):
                self.call(**changes)

    def test_symlink_inputs_are_refused_before_following_or_loading(self):
        link = self.root / "alias.json"
        link.symlink_to(self.history)
        with patch("ngen_reforecast.preparation.forcing_adapter.load_forcing_manifest", side_effect=AssertionError("loaded symlink")):
            result = self.call(history_manifest_path=link)
        self.assertIn("FORCING_INPUT_REFUSED", self.codes(result))
        self.assertEqual(result["adapter_evidence"]["checks_performed"], 0)

    def test_oversized_resident_payload_is_refused_at_preflight(self):
        manifest = json.loads(self.history.read_text())
        with (self.root / manifest["payload"]["path"]).open("r+b") as stream:
            stream.truncate(MAX_PAYLOAD_BYTES + 1)
        result = self.call()
        self.assertIn("FORCING_INPUT_REFUSED", self.codes(result))
        self.assertEqual(result["adapter_evidence"]["checks_performed"], 0)

    def test_cooperative_deadline_refuses_further_calls(self):
        with patch("ngen_reforecast.preparation.forcing_adapter.time.monotonic", side_effect=[0, 6]), patch("ngen_reforecast.preparation.forcing_adapter.load_forcing_manifest", side_effect=AssertionError("read")):
            result = self.call()
        self.assertIn("FORCING_INPUT_REFUSED", self.codes(result))
        self.assertFalse(result["adapter_evidence"]["decoded_content_valid"])

    def test_file_disappearing_after_validators_cannot_claim_complete_content(self):
        original = forcing.validate_forecast_issue
        calls = []
        def validate(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(result)
            if len(calls) == 2:
                self.history.unlink()
            return result
        with patch("ngen_reforecast.preparation.forcing_adapter.validate_forecast_issue", side_effect=validate):
            result = self.call()
        self.assertIn("RESIDENT_INPUT_MISSING", self.codes(result))
        self.assertFalse(result["adapter_evidence"]["complete_check_run"])
        self.assertFalse(result["adapter_evidence"]["decoded_content_valid"])
        self.assertEqual(result["readiness_report"]["checks"][2]["status"], "missing")

    def test_guarded_zero_network_model_admission_and_process_calls(self):
        targets = ["ngen_reforecast.execution.execute_campaign", "ngen_reforecast.execution_lock.prepare_execution",
                   "ngen_reforecast.execution_lock.verify_execution_assets", "ngen_reforecast.archive.export_result",
                   "subprocess.Popen", "subprocess.run", "socket.create_connection", "urllib.request.urlopen"]
        with ExitStack() as stack:
            mocks = [stack.enter_context(patch(name, side_effect=AssertionError(name))) for name in targets]
            result = self.call()
            self.assertFalse(result["readiness_report"]["execution_ready"])
            for mock in mocks:
                mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
