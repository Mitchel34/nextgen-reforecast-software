"""Adversarial CFE drainage mapping audits; no native code or model execution."""
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ngen_reforecast import campaign, configuration
from ngen_reforecast.configuration import load_configuration_manifest, validate_configuration
from ngen_reforecast.cli import main


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).parents[1] / ".local/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.axis = ["cat-1", "cat-2"]

    def asset(self, path, text):
        raw = text.encode() if isinstance(text, str) else text
        (self.root / path).write_bytes(raw)
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}

    def fixture(self, variant="candidate_1km"):
        values = ("12", "30") if variant == "inherited_diagnostic" else ("0.25", "0.5")
        return {
            "schema_version": "cfe-mapping-manifest/0.1", "evidence_class": "synthetic", "variant": variant,
            "catchment_ids": list(self.axis),
            "attributes": self.asset("attributes.csv", "catchment_id,mean.slope,mean.slope_1km\ncat-1,12,0.25\ncat-2,30,0.5\n"),
            "source": {"hydrofabric_sha256": hashlib.sha256(b"synthetic hydrofabric declaration").hexdigest(),
                       "field_units": {"mean.slope": "degrees", "mean.slope_1km": "1"},
                       "field_meanings": {"mean.slope": "terrain_slope", "mean.slope_1km": "bottom_drainage_modifier"}},
            "mapping": {"source_field": "mean.slope" if variant == "inherited_diagnostic" else "mean.slope_1km",
                        "target_parameter": "soil_params.slop", "purpose": "cfe_bottom_drainage",
                        "transformation": "identity", "target_units": "1"},
            "generator": {"revision": "a" * 40, "configuration_family": "synthetic-test-only"},
            "cfe_library": self.asset("synthetic-library.bin", b"Synthetic bytes, not an ELF library or executable.\n"),
            "configurations": [{"catchment_id": cid, "asset": self.asset(f"{cid}.txt", f"soil_params.slop={value}[1]\n")}
                               for cid, value in zip(self.axis, values)],
        }

    def validate(self, manifest):
        return validate_configuration(manifest, self.root, expected_catchment_ids=self.axis)

    def config(self, manifest, text, index=0):
        item = manifest["configurations"][index]
        item["asset"] = self.asset(item["asset"]["path"], text)

    def table(self, manifest, text):
        manifest["attributes"] = self.asset(manifest["attributes"]["path"], text)

    def codes(self, report):
        return {item["code"] for item in report["blockers"]}

    def test_candidate_mapping_checks_bytes_without_qualifying_whole_configuration(self):
        manifest = self.fixture()
        report = self.validate(manifest)
        self.assertTrue(report["content_valid"])
        self.assertFalse(report["execution_ready"])
        self.assertFalse(report["complete_configuration_validated"])
        self.assertFalse(report["loaded_library_attested"])
        self.assertEqual(report["source_metadata_status"], "declared_unverified")
        self.assertEqual(len(report["observed_assets"]), 4)
        self.assertEqual([pair["source_decimal"] for pair in report["parameter_pairs"]], ["0.25", "0.5"])
        self.assertEqual(self.validate(deepcopy(manifest)), report)
        self.assertIn("source_attribute_units_and_derivation_unverified", report["qualification_blockers"])
        self.assertIn("coupled_candidate_history_and_response_unqualified", report["qualification_blockers"])

    def test_inherited_baseline_remains_diagnostic_and_unclipped(self):
        manifest = self.fixture("inherited_diagnostic")
        report = self.validate(manifest)
        self.assertTrue(report["content_valid"])
        self.assertEqual([pair["configuration_decimal"] for pair in report["parameter_pairs"]], ["12", "30"])
        self.assertEqual({item["code"] for item in report["warnings"]}, {"inherited_mapping_concern", "inherited_out_of_range"})
        self.assertIn("inherited_mean_slope_mapping_known_concern", report["qualification_blockers"])
        self.assertFalse(report["execution_ready"])
        self.assertEqual((self.root / "cat-1.txt").read_text(), "soil_params.slop=12[1]\n")

    def test_matching_hash_does_not_hide_wrong_parameter_source(self):
        manifest = self.fixture()
        self.config(manifest, "soil_params.slop=12[1]\n")
        report = self.validate(manifest)
        self.assertIn("drainage_value_mismatch", self.codes(report))
        self.assertIn("candidate_out_of_range", self.codes(report))
        actual = next(item for item in report["observed_assets"] if item["path"] == "cat-1.txt")
        self.assertEqual(actual["sha256"], manifest["configurations"][0]["asset"]["sha256"])

    def test_cfe_aliases_are_accepted_individually_but_never_twice(self):
        for key in ("soil_params.slop", "soil_params.slope"):
            manifest = self.fixture()
            self.config(manifest, f"{key}=.25[m/m]\n")
            self.assertTrue(self.validate(manifest)["content_valid"])
        for second in ("soil_params.slop", "soil_params.slope"):
            manifest = self.fixture()
            self.config(manifest, f"soil_params.slop=0.25[1]\n{second}=0.25[1]\n")
            self.assertIn("configuration_invalid", self.codes(self.validate(manifest)))

    def test_noah_or_routing_slope_does_not_substitute_for_cfe_drainage(self):
        manifest = self.fixture()
        for text in ("slope=0.25[1]\n", "noah.slope=0.25[1]\n", "routing.slope=0.25[1]\n", "# soil_params.slop=0.25[1]\n"):
            self.config(manifest, text)
            self.assertIn("configuration_invalid", self.codes(self.validate(manifest)))
        self.config(manifest, "soil_params.slop=0.25[1]\nnoah.slope=99[degree]\nrouting.slope=-123[unknown]\n")
        report = self.validate(manifest)
        self.assertTrue(report["content_valid"])
        self.assertFalse(report["complete_configuration_validated"])

    def test_exact_mapping_disallows_angle_conversion_clipping_or_other_targets(self):
        for field, value in (("source_field", "mean.slope"), ("target_parameter", "noah.slope"),
                             ("purpose", "terrain_slope"), ("transformation", "divide_by_360"),
                             ("transformation", "clip_0_1"), ("target_units", "degrees")):
            manifest = self.fixture()
            manifest["mapping"][field] = value
            self.assertIn("mapping_mismatch", self.codes(self.validate(manifest)))

    def test_candidate_source_units_and_meaning_must_be_declared_without_certifying_them(self):
        for field, value in (("field_units", "degrees"), ("field_meanings", "terrain_slope")):
            manifest = self.fixture()
            manifest["source"][field]["mean.slope_1km"] = value
            self.assertIn("source_metadata_mismatch", self.codes(self.validate(manifest)))
        manifest = self.fixture()
        manifest["evidence_class"] = "source_declared"
        report = self.validate(manifest)
        self.assertTrue(report["content_valid"])
        self.assertEqual(report["source_metadata_status"], "declared_unverified")
        self.assertFalse(report["execution_ready"])

    def test_candidate_range_endpoints_and_out_of_range_values(self):
        for value in ("0", "1", "-0.01", "1.01"):
            manifest = self.fixture()
            self.table(manifest, f"catchment_id,mean.slope,mean.slope_1km\ncat-1,12,{value}\ncat-2,30,0.5\n")
            self.config(manifest, f"soil_params.slop={value}[1]\n")
            report = self.validate(manifest)
            self.assertEqual(report["content_valid"], value in ("0", "1"))
            if value not in ("0", "1"):
                self.assertIn("candidate_out_of_range", self.codes(report))

    def test_strict_assignment_units_numeric_syntax_and_trailing_junk(self):
        for value in ("NaN[1]", "Infinity[1]", "0.25", "0.25[degrees]", "0.25[1]junk", "0.25[1] # comment",
                      "0.25[1][1]", "0x1p-2[1]", "0_25[1]", "0.25junk[1]", "０.２５[1]", "٠.٢٥[1]"):
            with self.subTest(value=value):
                manifest = self.fixture()
                self.config(manifest, f"soil_params.slop={value}\n")
                self.assertIn("configuration_invalid", self.codes(self.validate(manifest)))

    def test_numeric_source_grammar_rejects_underscores_unicode_and_hidden_whitespace(self):
        for value in ("NaN", "Infinity", "0_25", "０.２５", "٠.٢٥", " 0.25", "0.25 ", ""):
            with self.subTest(value=value):
                manifest = self.fixture()
                self.table(manifest, f"catchment_id,mean.slope,mean.slope_1km\ncat-1,12,{value}\ncat-2,30,0.5\n")
                self.assertIn("attribute_table_invalid", self.codes(self.validate(manifest)))

    def test_config_key_whitespace_and_non_line_separators_cannot_mimic_native_keys(self):
        for text in (" soil_params.slop=0.25[1]\n", "soil_params.slop =0.25[1]\n",
                     "ignored=1\vsoil_params.slop=0.25[1]\n", "ignored=1\fsoil_params.slop=0.25[1]\n",
                     "ignored=1\rsoil_params.slop=0.25[1]\n", "ignored=1\u2028soil_params.slop=0.25[1]\n",
                     "ignored=1\x00\nsoil_params.slop=0.25[1]\n"):
            with self.subTest(text=repr(text)):
                manifest = self.fixture()
                self.config(manifest, text)
                self.assertIn("configuration_invalid", self.codes(self.validate(manifest)))

    def test_nonrepresentable_native_double_cannot_pass_exact_decimal_comparison(self):
        for variant, field in (("candidate_1km", "mean.slope_1km"), ("inherited_diagnostic", "mean.slope")):
            for value in ("1e9999", "1e-9999"):
                with self.subTest(variant=variant, value=value):
                    manifest = self.fixture(variant)
                    first = f"{value},0.25" if field == "mean.slope" else f"12,{value}"
                    self.table(manifest, f"catchment_id,mean.slope,mean.slope_1km\ncat-1,{first}\ncat-2,30,0.5\n")
                    self.config(manifest, f"soil_params.slop={value}[1]\n")
                    report = self.validate(manifest)
                    self.assertFalse(report["content_valid"])
                    self.assertTrue(self.codes(report) & {"attribute_table_invalid", "configuration_invalid"})

    def test_equivalent_ascii_scientific_notation_and_crlf(self):
        manifest = self.fixture()
        self.table(manifest, "catchment_id,mean.slope,mean.slope_1km\r\ncat-1,+1.2e1,2.5E-1\r\ncat-2,30,.5\r\n")
        self.config(manifest, "# a diagnostic comment\r\nsoil_params.slope=+2.50e-1[m/m]\r\n")
        self.assertTrue(self.validate(manifest)["content_valid"])

    def test_source_table_duplicate_missing_extra_axes_and_row_width(self):
        cases = [
            ("cat-1,12,0.25\ncat-1,30,0.5\n", "attribute_table_invalid"),
            ("cat-1,12,0.25\n", "attribute_axis_mismatch"),
            ("cat-1,12,0.25\ncat-2,30,0.5\ncat-3,20,0.2\n", "attribute_axis_mismatch"),
            ("cat-1,12\ncat-2,30,0.5\n", "attribute_table_invalid"),
            ("cat-1,12,0.25,extra\ncat-2,30,0.5\n", "attribute_table_invalid"),
        ]
        for rows, code in cases:
            manifest = self.fixture()
            self.table(manifest, "catchment_id,mean.slope,mean.slope_1km\n" + rows)
            self.assertIn(code, self.codes(self.validate(manifest)))

    def test_exact_header_rejects_duplicate_missing_extra_or_reordered_attributes(self):
        for header in ("catchment_id,mean.slope,mean.slope", "catchment_id,mean.slope",
                       "catchment_id,mean.slope_1km,mean.slope", "catchment_id,mean.slope,mean.slope_1km,other"):
            manifest = self.fixture()
            self.table(manifest, header + "\ncat-1,12,0.25\n")
            self.assertIn("attribute_table_invalid", self.codes(self.validate(manifest)))

    def test_manifest_axis_and_configuration_axes_are_independently_checked(self):
        manifest = self.fixture()
        manifest["catchment_ids"] = ["cat-1"]
        self.assertIn("catchment_axis_mismatch", self.codes(self.validate(manifest)))
        manifest = self.fixture()
        manifest["configurations"].pop()
        self.assertIn("configuration_axis_mismatch", self.codes(self.validate(manifest)))
        manifest = self.fixture()
        manifest["configurations"][1]["catchment_id"] = "cat-1"
        self.assertIn("configuration_axis_mismatch", self.codes(self.validate(manifest)))

    def test_stale_hash_and_missing_assets_never_produce_accepted_content(self):
        for key in ("attributes", "cfe_library"):
            manifest = self.fixture()
            asset = manifest[key]
            (self.root / asset["path"]).write_bytes(b"x" * asset["size_bytes"])
            self.assertIn("asset_identity_mismatch", self.codes(self.validate(manifest)))
            (self.root / asset["path"]).unlink()
            self.assertIn("asset_unavailable", self.codes(self.validate(manifest)))
        manifest = self.fixture()
        manifest["configurations"][0]["asset"]["sha256"] = "f" * 64
        self.assertIn("asset_identity_mismatch", self.codes(self.validate(manifest)))

    def test_bound_library_bytes_are_not_loaded_elf_identity(self):
        manifest = self.fixture()
        with patch("ctypes.CDLL", side_effect=AssertionError("native library must never be loaded")):
            report = self.validate(manifest)
        self.assertTrue(report["content_valid"])
        self.assertFalse(report["loaded_library_attested"])
        manifest["cfe_library"] = self.asset("synthetic-library.bin", b"different synthetic non-ELF bytes\n")
        changed = self.validate(manifest)
        self.assertTrue(changed["content_valid"])
        self.assertNotEqual(changed["validation_identity_sha256"], report["validation_identity_sha256"])
        self.assertFalse(changed["loaded_library_attested"])

    def test_metadata_generator_and_variant_changes_change_validation_identity(self):
        manifest = self.fixture()
        original = self.validate(manifest)
        for field in ("source", "generator"):
            changed = deepcopy(manifest)
            if field == "source":
                changed[field]["hydrofabric_sha256"] = "f" * 64
            else:
                changed[field]["revision"] = "b" * 40
            report = self.validate(changed)
            self.assertEqual(report["parameter_pairs"], original["parameter_pairs"])
            self.assertNotEqual(report["validation_identity_sha256"], original["validation_identity_sha256"])
            self.assertFalse(report["execution_ready"])
        inherited = self.validate(self.fixture("inherited_diagnostic"))
        self.assertNotEqual(inherited["mapping_sha256"], original["mapping_sha256"])

    def test_symlinks_and_dataless_library_refused_without_hydration(self):
        manifest = self.fixture()
        path = self.root / manifest["cfe_library"]["path"]
        real = self.root / "real-library.bin"
        path.rename(real)
        path.symlink_to(real)
        self.assertIn("asset_unavailable", self.codes(self.validate(manifest)))
        path.unlink()
        real.rename(path)
        actual_stat = os.stat

        def flagged(name, *args, **kwargs):
            info = actual_stat(name, *args, **kwargs)
            if os.fspath(name) == path.name:
                class Flagged:
                    st_flags = campaign._DATALESS
                return Flagged()
            return info

        with patch.object(campaign.os, "stat", side_effect=flagged):
            self.assertIn("asset_unavailable", self.codes(self.validate(manifest)))

    def test_declared_size_limits_read_before_bytes_to_preserve_aggregate_bound(self):
        manifest = self.fixture()
        item = manifest["configurations"][0]["asset"]
        item["size_bytes"] = 1
        target_inode = (self.root / item["path"]).stat().st_ino
        original_read = os.read

        def refuse_oversized(fd, size):
            if os.fstat(fd).st_ino == target_inode:
                raise AssertionError("file larger than declared admission bound was read")
            return original_read(fd, size)

        with patch.object(campaign.os, "read", side_effect=refuse_oversized):
            report = self.validate(manifest)
        self.assertIn("asset_unavailable", self.codes(report))

    def test_manifest_json_bounds_paths_types_and_revision_are_strict(self):
        manifest = self.fixture()
        path = self.root / "configuration.json"
        path.write_text(json.dumps(manifest))
        self.assertEqual(load_configuration_manifest(path), manifest)
        for text in ('{"x":1,"x":2}', '{"x":NaN}', "{"):
            path.write_text(text)
            with self.assertRaises(ValueError):
                load_configuration_manifest(path)
        for value in (None, [], {}, "unknown"):
            changed = deepcopy(manifest)
            changed["variant"] = value
            with self.assertRaises(ValueError):
                self.validate(changed)
        for value in ("main", "A" * 40, "a" * 39, [], {}, 123, True):
            changed = deepcopy(manifest)
            changed["generator"]["revision"] = value
            with self.assertRaises(ValueError):
                self.validate(changed)
        for field, value in (("path", "../external"), ("sha256", "unknown"),
                             ("size_bytes", configuration.MAX_LIBRARY_BYTES + 1)):
            changed = deepcopy(manifest)
            changed["cfe_library"][field] = value
            with self.assertRaises(ValueError):
                self.validate(changed)
        with patch.object(configuration, "MAX_MANIFEST_BYTES", 1), self.assertRaises(ValueError):
            self.validate(manifest)

    def test_duplicate_paths_and_aggregate_config_budget_are_rejected_before_reads(self):
        manifest = self.fixture()
        manifest["configurations"][1]["asset"] = deepcopy(manifest["configurations"][0]["asset"])
        with self.assertRaises(ValueError):
            self.validate(manifest)
        manifest = self.fixture()
        manifest["configurations"] = [
            {"catchment_id": f"cat-{i}", "asset": {"path": f"{i}.txt", "sha256": "a" * 64,
                                                   "size_bytes": configuration.MAX_CONFIG_BYTES}}
            for i in range(65)
        ]
        with patch.object(configuration, "_resident_bytes", side_effect=AssertionError("over-budget manifest read")), \
                self.assertRaises(ValueError):
            self.validate(manifest)

    def test_unknown_generator_revision_preserves_gap_without_preventing_byte_audit(self):
        manifest = self.fixture("inherited_diagnostic")
        original = self.validate(manifest)
        manifest["generator"]["revision"] = None
        report = self.validate(manifest)
        self.assertTrue(report["content_valid"])
        self.assertEqual(report["generator_status"], "unknown")
        self.assertEqual(original["generator_status"], "declared_unverified")
        self.assertFalse(report["execution_ready"])
        self.assertIn("generator_execution_unattested", report["qualification_blockers"])
        self.assertNotEqual(report["validation_identity_sha256"], original["validation_identity_sha256"])

    def test_cli_content_success_failure_and_malformed_contract_are_distinct(self):
        manifest = self.fixture()
        path = self.root / "configuration.json"

        def call():
            path.write_text(json.dumps(manifest))
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["validate-cfe", str(path), "--catchment", "cat-1", "--catchment", "cat-2"])
            return code, out.getvalue(), err.getvalue()

        code, out, err = call()
        self.assertEqual(code, 0, err)
        self.assertTrue(json.loads(out)["content_valid"])
        self.assertFalse(json.loads(out)["execution_ready"])
        self.config(manifest, "soil_params.slop=0.9[1]\n")
        code, out, err = call()
        self.assertEqual(code, 2, err)
        self.assertIn("drainage_value_mismatch", self.codes(json.loads(out)))
        manifest["variant"] = []
        code, out, err = call()
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Unknown CFE mapping variant", json.loads(err)["message"])


if __name__ == "__main__":
    unittest.main()
