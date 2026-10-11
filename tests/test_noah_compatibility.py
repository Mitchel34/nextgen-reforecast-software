"""Strict pinned Noah option checks use synthetic input and execute no models."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repair_noah_compatibility", ROOT / "scripts/public_fixture/repair_noah_compatibility.py")
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


class NoahCompatibilityTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="noah-option-test-", dir=ROOT / ".local")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.valid = {name: bounds[0] for name, bounds in compat.RANGES.items()}

    def input(self, values=None):
        values = self.valid if values is None else values
        return ("&model_options\n" + "\n".join(f"  {name} = {value} ! test option" for name, value in values.items()) + "\n/\n").encode()

    def test_all_seventeen_option_ranges_and_implementation_exclusions(self):
        self.assertEqual(len(compat.validate_noah_options(self.input())), 17)
        for name, (lower, upper) in compat.RANGES.items():
            for value in (lower - 1, upper + 1):
                with self.subTest(name=name, value=value), self.assertRaises(compat.domain.PreparationError):
                    compat.validate_noah_options(self.input({**self.valid, name: value}))
        with self.assertRaises(compat.domain.PreparationError):
            compat.validate_noah_options(self.input({**self.valid, "subsurface_option": 3}))

    def test_both_actual_incompatible_template_values_refused_independently(self):
        for name, value in [("stomatal_resistance_option", 4), ("evap_srfc_resistance_option", 5)]:
            with self.subTest(name=name), self.assertRaises(compat.domain.PreparationError):
                compat.validate_noah_options(self.input({**self.valid, name: value}))

    def test_missing_duplicate_unknown_and_noninteger_options_refused(self):
        raw = self.input()
        variants = [raw.replace(b"  crop_model_option = 0 ! test option\n", b""),
                    raw.replace(b"\n/\n", b"\n  crop_model_option = 0\n/\n"),
                    raw.replace(b"\n/\n", b"\n  mystery_option = 1\n/\n"),
                    raw.replace(b"crop_model_option = 0", b"crop_model_option = 0.0"),
                    raw + raw]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(compat.domain.PreparationError):
                compat.validate_noah_options(variant)

    def test_two_explicit_supported_defaults_preserve_other_options(self):
        old = {**self.valid, "stomatal_resistance_option": 4, "evap_srfc_resistance_option": 5, "subsurface_option": 2}
        raw = self.input(old) + b"! Unchanged scientific location and state content\n"
        result, before, after = compat.repair_options(raw)
        self.assertEqual(before, old)
        self.assertEqual(after, {**old, "stomatal_resistance_option": 1, "evap_srfc_resistance_option": 1})
        self.assertTrue(result.endswith(b"! Unchanged scientific location and state content\n"))
        with self.assertRaises(compat.domain.PreparationError):
            compat.repair_options(self.input())

    def test_changed_source_archive_refused(self):
        runtime = self.base / "runtime"
        (runtime / "downloads").mkdir(parents=True)
        (runtime / "downloads" / compat.NOAH_ARCHIVE).write_bytes(b"changed source archive")
        with self.assertRaises(compat.domain.PreparationError):
            compat.default_source(runtime)

    def bundle(self):
        parent = self.base / "parent"
        target = parent / "history/config/cat_config/NOAH-OWP-M/cat-1.input"
        target.parent.mkdir(parents=True)
        target.write_bytes(self.input({**self.valid, "stomatal_resistance_option": 4, "evap_srfc_resistance_option": 5}))
        cfe = parent / "history/config/cat_config/CFE/cat-1.ini"
        cfe.parent.mkdir(parents=True)
        cfe.write_bytes(b"soil_params.slop=0.043414704501628876[m/m]\n")
        report = {"schema_version": "public-diagnostic-input-admission/0.1", "fixture_id": "watauga-public-rebuild-v1",
                  "catchment_ids": ["cat-1"], "jobs": [{"path": "history"}], "source_contracts": [],
                  "files": [{"path": str(path.relative_to(parent)), **compat.domain.binding(path)} for path in sorted(parent.rglob("*")) if path.is_file()]}
        report["admission_identity_sha256"] = hashlib.sha256(compat.domain.canonical(report)).hexdigest()
        (parent / "ADMISSION.json").write_text(json.dumps(report))
        recipe = {"fixture_id": "watauga-public-rebuild-v2", "parent_fixture_id": report["fixture_id"],
                  "parent_admission_identity_sha256": report["admission_identity_sha256"],
                  "domain": {"catchment_ids": ["cat-1"]}, "configuration": {"noah_model_option_changes": {
                      name: {"previous": old, "new": new} for name, (old, new) in compat.REPLACEMENTS.items()}}}
        recipe_path = self.base / "recipe.json"
        recipe_path.write_text(json.dumps(recipe))
        return parent, recipe_path

    def test_separate_scientific_identity_preserves_parent_and_cfe_bytes(self):
        parent, recipe = self.bundle()
        before = {str(path.relative_to(parent)): path.read_bytes() for path in parent.rglob("*") if path.is_file()}
        with patch.object(compat, "default_source", return_value=([{"synthetic": True}], self.valid)):
            result = compat.repair(parent, self.base / "runtime", recipe, self.base / "v2")
        self.assertEqual(before, {str(path.relative_to(parent)): path.read_bytes() for path in parent.rglob("*") if path.is_file()})
        self.assertEqual(result["fixture_id"], "watauga-public-rebuild-v2")
        self.assertEqual(result["noah_model_option_fields_checked"], 17)
        self.assertEqual(result["noah_option_guard_count"], 16)
        self.assertFalse(result["physical_reference_validated"])
        self.assertEqual(result["native_model_invocations"], 0)
        self.assertEqual((self.base / "v2/history/config/cat_config/CFE/cat-1.ini").read_bytes(), before["history/config/cat_config/CFE/cat-1.ini"])
        self.assertNotEqual(result["admission_identity_sha256"], result["parent_admission_identity_sha256"])

    def test_parent_corruption_recipe_change_and_existing_destination_refused(self):
        parent, recipe = self.bundle()
        destination = self.base / "exists"
        destination.mkdir()
        with patch.object(compat, "default_source", return_value=([], self.valid)), self.assertRaises(FileExistsError):
            compat.repair(parent, self.base / "runtime", recipe, destination)
        document = json.loads(recipe.read_text())
        document["configuration"]["noah_model_option_changes"]["stomatal_resistance_option"]["new"] = 2
        recipe.write_text(json.dumps(document))
        with patch.object(compat, "default_source", return_value=([], self.valid)), self.assertRaises(compat.domain.PreparationError):
            compat.repair(parent, self.base / "runtime", recipe, self.base / "v2")
        (parent / "history/config/cat_config/CFE/cat-1.ini").write_bytes(b"changed scientific parameter")
        with self.assertRaises(compat.domain.PreparationError):
            compat.sealed_input(parent)
        self.assertFalse((self.base / "v2").exists())


if __name__ == "__main__":
    unittest.main()
