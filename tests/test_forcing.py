"""Adversarial decoded-weather contracts; synthetic values only, no model runs."""
from copy import deepcopy
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ngen_reforecast import campaign, forcing
from ngen_reforecast.campaign import CampaignError
from ngen_reforecast.forcing import (
    ForcingError, evaluate_gap_policy, load_forcing_manifest,
    validate_forecast_issue, validate_history,
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


class ForcingTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).parents[1] / ".local/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.start = datetime(2022, 1, 1, tzinfo=timezone.utc)
        self.axis = ["cat-1", "cat-2"]

    def label(self, offset):
        return (self.start + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def fixture(self, role="history"):
        forecast = role == "forecast"
        mapping = forcing.FORECAST_VARIABLES if forecast else forcing.HISTORY_VARIABLES
        count = 18 if forecast else 3
        values = [3.6 if forecast else 3600, 280, 0.005, 1, -2, 95000, 200, 300]
        rows = []
        for catchment in self.axis:
            for hour in range(count):
                rows.append(dict(zip([*forcing.TIME_COLUMNS, *mapping], [
                    catchment, self.label(hour), self.label(hour + 1),
                    self.label(hour + 1 if forecast else hour),
                    self.label(0) if forecast else "", str(hour + 1) if forecast else "", *values,
                ])))
        manifest = {
            "schema_version": "forcing-manifest/0.1", "evidence_class": "synthetic",
            "role": role, "payload": {"path": f"{role}.csv", "sha256": "0" * 64, "size_bytes": 1},
            "catchment_ids": list(self.axis), "start_time_utc": self.label(0),
            "stop_time_utc_exclusive": self.label(count),
            "units": deepcopy(forcing.FORECAST_UNITS if forecast else forcing.HISTORY_UNITS),
            "source": {"kind": "issue_forecast" if forecast else "historical_analysis",
                       "product": "synthetic-contract-example", "issue_time_utc": self.label(0) if forecast else None,
                       "objects": [{"object_key": "synthetic/weather", "generation": "fixture-v1", "size_bytes": 123,
                                    "sha256": hashlib.sha256(b"synthetic source declaration, no archive object").hexdigest()}],
                       "decoder_sha256": hashlib.sha256(b"synthetic decoder declaration").hexdigest(),
                       "grid_sha256": hashlib.sha256(b"synthetic grid declaration").hexdigest()},
            "transformation": deepcopy(forcing.FORECAST_TRANSFORMATION if forecast else forcing.HISTORY_TRANSFORMATION),
        }
        self.write(manifest, rows)
        return manifest, rows

    def write(self, manifest, rows, header=None):
        mapping = forcing.FORECAST_VARIABLES if manifest["role"] == "forecast" else forcing.HISTORY_VARIABLES
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=header or [*forcing.TIME_COLUMNS, *mapping])
        writer.writeheader()
        writer.writerows(rows)
        raw = output.getvalue().encode()
        path = self.root / manifest["payload"]["path"]
        path.write_bytes(raw)
        manifest["payload"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

    def validate(self, manifest):
        if manifest["role"] == "forecast":
            return validate_forecast_issue(manifest, self.root, expected_catchment_ids=self.axis, issue_time_utc=self.label(0))
        return validate_history(manifest, self.root, expected_catchment_ids=self.axis,
                                start_time_utc=self.label(0), stop_time_utc_exclusive=self.label(3))

    def codes(self, report):
        return {item["code"] for item in report["blockers"]}

    def test_history_converts_accumulation_exactly_once_and_preserves_boundary(self):
        manifest, rows = self.fixture()
        report = self.validate(manifest)
        expected = [{"catchment_id": row["catchment_id"], "provider_time_utc": row["provider_time_utc"],
                     "values": {"precip_rate": 1.0, "TMP_2maboveground": 280.0, "SPFH_2maboveground": 0.005,
                                "UGRD_10maboveground": 1.0, "VGRD_10maboveground": -2.0,
                                "PRES_surface": 95000.0, "DSWRF_surface": 200.0, "DLWRF_surface": 300.0}}
                    for row in rows]
        self.assertEqual(report["normalized_payload_sha256"], digest(expected))
        self.assertTrue(report["content_valid"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["source_truth_verified"])
        self.assertEqual(report["source_metadata_status"], "declared_unverified")
        self.assertFalse(report["operational_availability_verified"])
        self.assertEqual(self.validate(deepcopy(manifest)), report)
        self.assertEqual(evaluate_gap_policy(report)["decision"], "accept_content")
        self.assertTrue(report["qualification_blockers"])

    def test_forecast_rate_is_never_divided_again_and_all_leads_required(self):
        manifest, rows = self.fixture("forecast")
        report = self.validate(manifest)
        expected = [{"catchment_id": row["catchment_id"], "provider_time_utc": row["provider_time_utc"],
                     "values": {"precip_rate": 3.6, "TMP_2maboveground": 280.0, "SPFH_2maboveground": 0.005,
                                "UGRD_10maboveground": 1.0, "VGRD_10maboveground": -2.0,
                                "PRES_surface": 95000.0, "DSWRF_surface": 200.0, "DLWRF_surface": 300.0}}
                    for row in rows]
        self.assertEqual(report["normalized_payload_sha256"], digest(expected))
        self.assertEqual(report["expected_rows"], 36)
        self.assertTrue(report["content_valid"])
        self.write(manifest, [row for row in rows if int(row["lead_hour"]) <= 6])
        self.assertIn("missing_rows", self.codes(self.validate(manifest)))

    def test_hash_match_does_not_hide_one_hour_provider_shift(self):
        for role in ("history", "forecast"):
            manifest, rows = self.fixture(role)
            for row in rows:
                for field in ("provider_time_utc", "precip_source_time_utc", "other_source_time_utc"):
                    parsed = datetime.strptime(row[field], "%Y-%m-%dT%H:%M:%SZ")
                    row[field] = (parsed + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.write(manifest, rows)
            report = self.validate(manifest)
            self.assertEqual(report["payload_sha256"], manifest["payload"]["sha256"])
            self.assertIn("extra_rows", self.codes(report))
            self.assertIn("missing_rows", self.codes(report))
            self.assertIsNone(report["normalized_payload_sha256"])

    def test_source_time_clocks_fail_independently_of_provider_clock(self):
        for role in ("history", "forecast"):
            for field, expected in (("precip_source_time_utc", "precipitation_clock"),
                                    ("other_source_time_utc", "other_fields_clock")):
                manifest, rows = self.fixture(role)
                rows[0][field] = self.label(2)
                self.write(manifest, rows)
                self.assertIn(expected, self.codes(self.validate(manifest)))

    def test_self_consistent_manifest_cannot_shorten_or_shift_external_contract(self):
        manifest, _ = self.fixture()
        for field, value in (("start_time_utc", self.label(1)), ("stop_time_utc_exclusive", self.label(2))):
            changed = deepcopy(manifest)
            changed[field] = value
            self.assertIn("contract_mismatch", self.codes(self.validate(changed)))
        changed = deepcopy(manifest)
        changed["catchment_ids"] = ["cat-1"]
        self.assertIn("catchment_axis_mismatch", self.codes(self.validate(changed)))

    def test_wrong_units_and_double_conversion_fail(self):
        for role in ("history", "forecast"):
            manifest, _ = self.fixture(role)
            changed = deepcopy(manifest)
            precip = "RAINRATE" if role == "forecast" else "APCP"
            changed["units"][precip] = "mm h-1"
            self.assertIn("units_mismatch", self.codes(self.validate(changed)))
            changed = deepcopy(manifest)
            changed["transformation"]["precipitation"]["divisor"] = 3600 if role == "forecast" else 3600 * 3600
            self.assertIn("transformation_mismatch", self.codes(self.validate(changed)))
            changed = deepcopy(manifest)
            changed["units"].pop(precip)
            self.assertIn("units_mismatch", self.codes(self.validate(changed)))

    def test_nonfinite_empty_and_negative_precipitation_are_rejected(self):
        for value, code in (("NaN", "nonfinite_value"), ("inf", "nonfinite_value"), ("-inf", "nonfinite_value"),
                            ("1e9999", "nonfinite_value"), ("", "invalid_value"), ("-0.1", "negative_precipitation")):
            manifest, rows = self.fixture()
            rows[0]["APCP"] = value
            self.write(manifest, rows)
            report = self.validate(manifest)
            self.assertIn(code, self.codes(report))
            self.assertEqual(report["payload_sha256"], manifest["payload"]["sha256"])

    def test_nonfinite_nonprecipitation_field_is_rejected(self):
        manifest, rows = self.fixture("forecast")
        rows[0]["SWDOWN"] = "nan"
        self.write(manifest, rows)
        self.assertIn("nonfinite_value", self.codes(self.validate(manifest)))

    def test_numeric_grammar_and_underflow_cannot_hide_changed_weather(self):
        for role in ("history", "forecast"):
            precip = "APCP" if role == "history" else "RAINRATE"
            for value in ("1_000", "１２", "١٢", " 1", "1 ", "1e-999", "-1e-999"):
                with self.subTest(role=role, value=value):
                    manifest, rows = self.fixture(role)
                    rows[0][precip] = value
                    self.write(manifest, rows)
                    report = self.validate(manifest)
                    self.assertFalse(report["content_valid"])
                    self.assertEqual(report["payload_sha256"], manifest["payload"]["sha256"])
            manifest, rows = self.fixture(role)
            variable = "TMP_2maboveground" if role == "history" else "T2D"
            rows[0][variable] = "1e-999"
            self.write(manifest, rows)
            self.assertIn("numeric_underflow", self.codes(self.validate(manifest)))
        manifest, rows = self.fixture()
        rows[0]["APCP"] = "1e-323"
        self.write(manifest, rows)
        self.assertIn("numeric_underflow", self.codes(self.validate(manifest)))

    def test_duplicate_missing_extra_catchment_and_time_rows(self):
        for mutation, code in (("duplicate", "duplicate_rows"), ("missing", "missing_rows"),
                                ("catchment", "extra_rows"), ("time", "extra_rows")):
            manifest, rows = self.fixture()
            if mutation == "duplicate":
                rows.append(deepcopy(rows[0]))
            elif mutation == "missing":
                rows.pop(0)
            elif mutation == "catchment":
                rows[0]["catchment_id"] = "cat-unexpected"
            else:
                rows[0]["provider_time_utc"] = self.label(3)
            self.write(manifest, rows)
            self.assertIn(code, self.codes(self.validate(manifest)))

    def test_analysis_source_and_wrong_source_issue_cannot_be_forecast(self):
        manifest, _ = self.fixture("forecast")
        for field, value, code in (("kind", "historical_analysis", "source_kind_mismatch"),
                                    ("issue_time_utc", self.label(1), "source_issue_mismatch"),
                                    ("issue_time_utc", None, "source_issue_mismatch")):
            changed = deepcopy(manifest)
            changed["source"][field] = value
            self.assertIn(code, self.codes(self.validate(changed)))

    def test_row_issue_lead_and_history_issue_labels(self):
        for field, value in (("issue_time_utc", self.label(1)), ("lead_hour", "2"), ("lead_hour", "01")):
            manifest, rows = self.fixture("forecast")
            rows[0][field] = value
            self.write(manifest, rows)
            self.assertIn("forecast_issue_lead", self.codes(self.validate(manifest)))
        manifest, rows = self.fixture()
        rows[0]["issue_time_utc"] = self.label(0)
        self.write(manifest, rows)
        self.assertIn("history_issue_label", self.codes(self.validate(manifest)))

    def test_non_hourly_or_noncanonical_clock_is_rejected(self):
        for value in ("2022-01-01T00:30:00Z", "2022-01-01T00:00:00+00:00", "2022-02-30T00:00:00Z"):
            manifest, rows = self.fixture()
            rows[0]["provider_time_utc"] = value
            self.write(manifest, rows)
            self.assertIn("invalid_clock", self.codes(self.validate(manifest)))

    def test_missing_forecast_only_can_be_explicitly_excluded(self):
        for role in ("history", "forecast"):
            manifest, rows = self.fixture(role)
            rows.pop()
            self.write(manifest, rows)
            report = self.validate(manifest)
            self.assertEqual(evaluate_gap_policy(report)["decision"], "fail")
            decision = evaluate_gap_policy(report, "exclude_issue")
            self.assertEqual(decision["decision"], "exclude_issue" if role == "forecast" else "fail")
            self.assertFalse(decision["execution_ready"])
            self.assertFalse(decision["imputation_applied"])
            if role == "forecast":
                self.assertEqual(decision["excluded_generated_rows"], 36)
                self.assertEqual(decision["excluded_issue_time_utc"], self.label(0))
                self.assertTrue(decision["retained_population_requires_recalculation"])

    def test_exclusion_cannot_hide_corrupt_or_shifted_forecast(self):
        manifest, rows = self.fixture("forecast")
        rows.pop()
        rows[0]["RAINRATE"] = "NaN"
        self.write(manifest, rows)
        report = self.validate(manifest)
        self.assertEqual(evaluate_gap_policy(report, "exclude_issue")["decision"], "fail")
        with self.assertRaises(ForcingError):
            evaluate_gap_policy(report, "approved_imputation")
        changed = deepcopy(report)
        changed["content_valid"] = True
        with self.assertRaises(ForcingError):
            evaluate_gap_policy(changed)

    def test_source_payload_transformation_identities_are_separate(self):
        manifest, _ = self.fixture()
        original = self.validate(manifest)
        changed = deepcopy(manifest)
        changed["source"]["objects"][0]["generation"] = "new-generation"
        newer = self.validate(changed)
        self.assertEqual(original["payload_sha256"], newer["payload_sha256"])
        self.assertEqual(original["normalized_payload_sha256"], newer["normalized_payload_sha256"])
        self.assertEqual(original["transformation_sha256"], newer["transformation_sha256"])
        self.assertNotEqual(original["source_metadata_sha256"], newer["source_metadata_sha256"])
        self.assertNotEqual(original["validation_identity_sha256"], newer["validation_identity_sha256"])
        changed["transformation"]["version"] = "2"
        treatment = self.validate(changed)
        self.assertNotEqual(treatment["transformation_sha256"], newer["transformation_sha256"])

    def test_byte_corruption_and_declared_size_mismatch(self):
        manifest, _ = self.fixture()
        changed = deepcopy(manifest)
        changed["payload"]["sha256"] = "f" * 64
        self.assertIn("payload_hash_mismatch", self.codes(self.validate(changed)))
        changed = deepcopy(manifest)
        changed["payload"]["size_bytes"] += 1
        self.assertIn("payload_size_mismatch", self.codes(self.validate(changed)))

    def test_missing_duplicate_extra_headers_and_bad_row_shape(self):
        manifest, rows = self.fixture()
        original_header = [*forcing.TIME_COLUMNS, *forcing.HISTORY_VARIABLES]
        for header in (original_header[:-1], original_header + ["extra"], original_header + ["APCP"]):
            path = self.root / manifest["payload"]["path"]
            path.write_text(",".join(header) + "\n")
            manifest["payload"].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size_bytes=path.stat().st_size)
            self.assertIn("columns_mismatch", self.codes(self.validate(manifest)))
        self.write(manifest, rows)
        path = self.root / manifest["payload"]["path"]
        path.write_bytes(path.read_bytes() + b"cat-1,2022-01-01T00:00:00Z\n")
        self.assertIn("row_shape", self.codes(self.validate(manifest)))

    def test_manifest_load_safe_round_trip_and_strict_json(self):
        manifest, _ = self.fixture()
        path = self.root / "manifest.json"
        path.write_text(json.dumps(manifest))
        self.assertEqual(load_forcing_manifest(path), manifest)
        for text in ('{"schema_version":"x","schema_version":"y"}', '{"value":NaN}', "{"):
            path.write_text(text)
            with self.assertRaises(CampaignError):
                load_forcing_manifest(path)

    def test_symlink_payload_parent_and_manifest_are_refused(self):
        manifest, _ = self.fixture()
        path = self.root / manifest["payload"]["path"]
        real = self.root / "real.csv"
        path.rename(real)
        path.symlink_to(real)
        with self.assertRaises(ForcingError):
            self.validate(manifest)
        directory = self.root / "link"
        directory.symlink_to(self.root, target_is_directory=True)
        manifest["payload"]["path"] = "link/real.csv"
        with self.assertRaises(ForcingError):
            self.validate(manifest)
        with self.assertRaises(ForcingError):
            load_forcing_manifest(path)

    def test_dataless_file_refused_without_byte_read(self):
        manifest, _ = self.fixture()
        actual_stat = os.stat

        def flagged(path, *args, **kwargs):
            info = actual_stat(path, *args, **kwargs)
            if os.fspath(path) == "history.csv":
                class Flagged:
                    st_flags = campaign._DATALESS
                return Flagged()
            return info

        with patch.object(campaign.os, "stat", side_effect=flagged), \
                patch.object(campaign.os, "read", side_effect=AssertionError("placeholder bytes read")):
            with self.assertRaises(ForcingError):
                self.validate(manifest)

    def test_bounds_paths_unknown_fields_and_invalid_axes_fail_before_expansion(self):
        manifest, _ = self.fixture()
        for field, value in (("path", "../escape.csv"), ("size_bytes", forcing.MAX_CSV_BYTES + 1),
                             ("sha256", None)):
            changed = deepcopy(manifest)
            changed["payload"][field] = value
            with self.assertRaises(CampaignError):
                self.validate(changed)
        for axis in ([], ["cat-1", "cat-1"], ["bad/id"]):
            with self.assertRaises(CampaignError):
                validate_history(manifest, self.root, expected_catchment_ids=axis,
                                 start_time_utc=self.label(0), stop_time_utc_exclusive=self.label(3))
        with self.assertRaises(ForcingError):
            validate_history(manifest, self.root, expected_catchment_ids=self.axis,
                             start_time_utc=self.label(0), stop_time_utc_exclusive=self.label(50_001))
        with patch.object(forcing, "MAX_ROWS", 5), self.assertRaises(ForcingError):
            self.validate(manifest)
        with patch.object(forcing, "MAX_MANIFEST_BYTES", 4), self.assertRaises(ForcingError):
            self.validate(manifest)
        changed = deepcopy(manifest)
        changed["unknown"] = "unsupported"
        with self.assertRaises(CampaignError):
            self.validate(changed)

    def test_row_read_bound_and_source_object_identity_bounds(self):
        manifest, rows = self.fixture()
        self.write(manifest, rows + rows)
        with patch.object(forcing, "MAX_ROWS", 6), self.assertRaises(ForcingError):
            self.validate(manifest)
        changed = deepcopy(manifest)
        changed["source"]["objects"].append(deepcopy(changed["source"]["objects"][0]))
        with self.assertRaises(ForcingError):
            self.validate(changed)

    def test_source_declared_evidence_does_not_claim_qualification(self):
        manifest, _ = self.fixture()
        manifest["evidence_class"] = "source_declared"
        report = self.validate(manifest)
        self.assertTrue(report["content_valid"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["physical_qualification"])
        self.assertEqual({item["code"] for item in report["qualification_blockers"]}, {
            "source_truth_unverified", "source_version_unqualified", "source_availability_unknown",
            "shortwave_interpretation_unqualified",
        })

    def test_history_cannot_consume_forecast_manifest(self):
        manifest, _ = self.fixture("forecast")
        report = validate_history(manifest, self.root, expected_catchment_ids=self.axis,
                                  start_time_utc=self.label(0), stop_time_utc_exclusive=self.label(3))
        self.assertFalse(report["content_valid"])
        self.assertIn("source_kind_mismatch", self.codes(report))

    def test_changed_during_read_and_oversized_resident_payload_are_refused(self):
        manifest, _ = self.fixture()
        path = self.root / manifest["payload"]["path"]
        original_read = os.read

        def append_during_read(fd, size):
            value = original_read(fd, size)
            with path.open("ab") as handle:
                handle.write(b"changed\n")
            return value

        with patch.object(campaign.os, "read", side_effect=append_during_read), self.assertRaises(ForcingError):
            self.validate(manifest)
        with path.open("wb") as handle:
            handle.truncate(forcing.MAX_CSV_BYTES + 1)
        with patch.object(campaign.os, "read", side_effect=AssertionError("oversized bytes read")), \
                self.assertRaises(ForcingError):
            self.validate(manifest)

    def test_checked_in_synthetic_examples_match_independent_contract(self):
        base = Path(__file__).parents[1] / "examples/validation"
        history = validate_history(load_forcing_manifest(base / "history.manifest.json"), base,
                                   expected_catchment_ids=["cat-1", "cat-2"],
                                   start_time_utc=self.label(0), stop_time_utc_exclusive=self.label(3))
        forecast = validate_forecast_issue(load_forcing_manifest(base / "forecast.manifest.json"), base,
                                          expected_catchment_ids=["cat-1", "cat-2"], issue_time_utc=self.label(0))
        self.assertTrue(history["content_valid"])
        self.assertTrue(forecast["content_valid"])
        self.assertFalse(history["execution_ready"])
        self.assertFalse(forecast["execution_ready"])


if __name__ == "__main__":
    unittest.main()
